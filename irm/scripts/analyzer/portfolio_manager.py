import argparse
import os
import redis
import logging
from urllib.parse import urlparse
from falkordb import FalkorDB
import sys
sys.path.append('/app')
from scripts.analyzer.update_weights import PortfolioWeightUpdater

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            logger.info(f"Connected to FalkorDB and Redis at {host}:{port}")
        except Exception as e:
            logger.error(f"Initialization Failed: {e}")
            self.graph = None
            self.redis_client = None

    def query_falkor(self, cypher):
        if not self.graph:
            return None
        try:
            return self.graph.query(cypher)
        except Exception as e:
            logger.error(f"Cypher Query Error: {e}")
            return None

    def _pad(self, text, width, align='left'):
        """Helper to pad strings based on visual width (handling CJK)."""
        text = str(text)
        # Simple heuristic: count chars > 127 as double-width
        visual_len = sum(2 if ord(c) > 127 else 1 for c in text)
        padding = max(0, width - visual_len)
        if align == 'left':
            return text + (' ' * padding)
        else:
            return (' ' * padding) + text

    def list_portfolio(self, owner="Admin"):
        """Fetch and display portfolio holdings, grouped by denomination slot."""
        # Query Portfolio node info
        port_cypher = f"MATCH (p:Portfolio {{owner: '{owner}'}}) RETURN p.name, p.strategy, p.total_value, p.currency"
        port_result = self.query_falkor(port_cypher)
        
        if not port_result or not port_result.result_set:
            print(f"[!] Portfolio for owner '{owner}' not found.")
            return

        p_name, p_strategy, p_total_value, p_currency = port_result.result_set[0]
        base_currency = p_currency or "USD"
        
        header_width = 92
        print("\n" + "=" * header_width)
        print(f" PORTFOLIO STATUS: {owner} (Base Currency: {base_currency})")
        print("=" * header_width)
        print(f" Name:     {p_name}")
        print(f" Strategy: {p_strategy}")
        print(f" Total NAV: {p_total_value:,.2f} {base_currency}")
        print("-" * header_width)
        
        # Query Holdings with denomination
        holdings_cypher = (
            f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset) "
            f"RETURN a.ticker, a.name, r.weight_pct, r.denomination"
        )
        holdings_result = self.query_falkor(holdings_cypher)
        
        if not holdings_result or not holdings_result.result_set:
            print(" No holdings found.")
        else:
            # Group holdings by denomination
            slots = {}  # { denomination: [ {ticker, name, weight, shares, avg_cost}, ... ] }
            
            for row in holdings_result.result_set:
                ticker = row[0]
                name = row[1]
                weight_pct = float(row[2] or 0.0)
                denomination = row[3] if len(row) > 3 and row[3] else base_currency
                
                # Fetch shares and avg_cost from Redis Hash
                redis_key = f"irm:portfolio:{owner}:holdings:{ticker}"
                redis_data = self.redis_client.hgetall(redis_key)
                shares = float(redis_data.get('shares', 0.0))
                avg_cost = float(redis_data.get('avg_cost', 0.0))
                
                slots.setdefault(denomination, []).append({
                    "ticker": ticker,
                    "name": name,
                    "weight_pct": weight_pct,
                    "shares": shares,
                    "avg_cost": avg_cost
                })
            
            # Render each denomination slot
            total_calc_weight = 0.0
            multi_currency = len(slots) > 1
            
            for denom in sorted(slots.keys(), key=lambda d: (d != base_currency, d)):
                holdings = slots[denom]
                slot_weight = sum(h["weight_pct"] for h in holdings)
                
                if multi_currency:
                    print(f"\n [{denom} Slot]")
                    print("-" * header_width)
                
                # Table Header
                ticker_h = self._pad("TICKER", 10)
                name_h   = self._pad("NAME", 28)
                shares_h = self._pad("SHARES", 12, 'right')
                cost_h   = self._pad(f"AVG COST", 12, 'right')
                weight_h = self._pad("WEIGHT (%)", 12, 'right')
                print(f"{ticker_h} | {name_h} | {shares_h} | {cost_h} | {weight_h}")
                print("-" * header_width)
                
                for h in holdings:
                    total_calc_weight += h["weight_pct"]
                    
                    r_ticker = self._pad(h["ticker"], 10)
                    r_name   = self._pad(h["name"][:28], 28)
                    r_shares = self._pad(f"{h['shares']:>12.2f}", 12, 'right')
                    r_cost   = self._pad(f"{h['avg_cost']:>12.2f}", 12, 'right')
                    r_weight = self._pad(f"{h['weight_pct']*100:>11.1f}%", 12, 'right')
                    print(f"{r_ticker} | {r_name} | {r_shares} | {r_cost} | {r_weight}")
                
                if multi_currency:
                    print("-" * header_width)
                    sub_label = self._pad(f"[{denom} Subtotal]", 10)
                    sub_weight = self._pad(f"{slot_weight*100:>11.1f}%", 12, 'right')
                    print(f"{sub_label} | {self._pad('', 28)} | {' '*12} | {' '*12} | {sub_weight}")
            
            print("-" * header_width)
            t_label  = self._pad("TOTAL", 10)
            t_empty  = self._pad("", 28)
            t_weight = self._pad(f"{total_calc_weight*100:>11.1f}%", 12, 'right')
            print(f"{t_label} | {t_empty} | {' '*12} | {' '*12} | {t_weight}")
        
        print("=" * header_width + "\n")

    def update_holding(self, owner, ticker, shares, avg_cost, denomination=None):
        """Update or create a holding in Redis and ensure the [:HOLDS] edge exists in FalkorDB.
        
        Args:
            denomination: Currency denomination for this holding (e.g. 'USD', 'CNY').
                          If None, falls back to the Portfolio node's base currency.
        """
        if not self.graph or not self.redis_client:
            return False

        # 1. Validate Asset exists in Graph
        asset_res = self.query_falkor(f"MATCH (a:Asset {{ticker: '{ticker}'}}) RETURN a.ticker")
        if not asset_res or not asset_res.result_set:
            logger.error(f"Asset with ticker '{ticker}' not found in ontology graph.")
            return False

        # Resolve denomination: explicit param > Portfolio base currency
        if denomination is None:
            port_res = self.query_falkor(f"MATCH (p:Portfolio {{owner: '{owner}'}}) RETURN p.currency")
            if port_res and port_res.result_set:
                denomination = port_res.result_set[0][0] or "USD"
            else:
                denomination = "USD"

        # 2. Redis & Graph Cleanup vs Update
        redis_key = f"irm:portfolio:{owner}:holdings:{ticker}"
        
        if shares <= 0:
            logger.info(f"Liquidating {owner}:{ticker} (shares <= 0). Cleaning up...")
            # Delete from Redis
            self.redis_client.delete(redis_key)
            # Delete edge from Graph
            delete_edge_cypher = (
                f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset {{ticker: '{ticker}'}}) "
                f"DELETE r"
            )
            self.query_falkor(delete_edge_cypher)
        else:
            # Update Redis Ledger (now includes denomination)
            self.redis_client.hset(redis_key, mapping={
                "shares": str(shares),
                "avg_cost": str(avg_cost),
                "denomination": denomination
            })
            logger.info(f"Updated Redis ledger for {owner}:{ticker} -> Shares: {shares}, AvgCost: {avg_cost}, Denom: {denomination}")

            # 3. Ensure [:HOLDS] edge exists in FalkorDB (Create if not present)
            edge_check_cypher = (
                f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset {{ticker: '{ticker}'}}) "
                f"RETURN r"
            )
            edge_res = self.query_falkor(edge_check_cypher)
            
            if not edge_res or not edge_res.result_set:
                logger.info(f"Creating missing [:HOLDS] edge for {owner} -> {ticker} (denom: {denomination})")
                create_edge_cypher = (
                    f"MATCH (p:Portfolio {{owner: '{owner}'}}), (a:Asset {{ticker: '{ticker}'}}) "
                    f"CREATE (p)-[:HOLDS {{id: 'edge_{owner}_{ticker}', weight_pct: 0.0, denomination: '{denomination}'}}]->(a)"
                )
                self.query_falkor(create_edge_cypher)
            else:
                # Edge exists — update denomination on it
                update_denom_cypher = (
                    f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset {{ticker: '{ticker}'}}) "
                    f"SET r.denomination = '{denomination}'"
                )
                self.query_falkor(update_denom_cypher)

        # 4. Trigger weights recalculation
        logger.info("Triggering weight recalculation...")
        weight_updater = PortfolioWeightUpdater(graph_name=self.graph_name)
        weight_updater.update_all_portfolios()
        
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Portfolio Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: list
    list_parser = subparsers.add_parser("list", help="List portfolio holdings")
    list_parser.add_argument("--owner", default="Admin", help="Portfolio owner")

    # Command: update
    update_parser = subparsers.add_parser("update", help="Update a specific holding")
    update_parser.add_argument("ticker", help="Asset ticker (e.g. NVDA)")
    update_parser.add_argument("shares", type=float, help="Number of shares")
    update_parser.add_argument("avg_cost", type=float, help="Average cost per share")
    update_parser.add_argument("--owner", default="Admin", help="Portfolio owner")
    update_parser.add_argument("--denom", default=None,
                               help="Currency denomination (e.g. USD, CNY, JPY). "
                                    "Defaults to portfolio's base currency if not specified.")
    
    args = parser.parse_args()
    
    mgr = PortfolioManager()
    if args.command == "update":
        success = mgr.update_holding(args.owner, args.ticker, args.shares, args.avg_cost, 
                                     denomination=args.denom)
        if success:
            print(f"[+] Successfully updated {args.ticker} for {args.owner}.")
        else:
            print(f"[!] Failed to update {args.ticker}. Please check logs.")
            exit(1)
    elif args.command == "list":
        mgr.list_portfolio(owner=args.owner)
    else:
        parser.print_help()
