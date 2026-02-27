import argparse
import os
from urllib.parse import urlparse
from falkordb import FalkorDB

class IRMPortfolioViewer:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        # Priority: REDIS_URL env var > default
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
        except Exception as e:
            print(f"[!] Failed to connect to FalkorDB at {host}:{port}: {e}")
            self.graph = None

    def _query_falkor(self, cypher):
        """Execute Cypher query via falkordb-python."""
        if not self.graph:
            return None
        try:
            return self.graph.query(cypher)
        except Exception as e:
            print(f"[!] Query Error: {e}")
            return None

    def list_portfolio(self, owner="Admin"):
        """Fetch and display portfolio holdings for a specific owner."""
        # Query Portfolio node info
        port_cypher = f"MATCH (p:Portfolio {{owner: '{owner}'}}) RETURN p.name, p.strategy, p.total_value, p.currency"
        port_result = self._query_falkor(port_cypher)
        
        if not port_result or not port_result.result_set:
            print(f"[!] Portfolio for owner '{owner}' not found.")
            return

        p_name, p_strategy, p_total_value, p_currency = port_result.result_set[0]
        
        print("\n" + "="*80)
        print(f" PORTFOLIO STATUS: {owner}")
        print("="*80)
        print(f" Name:     {p_name}")
        print(f" Strategy: {p_strategy}")
        print(f" Value:    {p_total_value:,.2f} {p_currency}")
        print("-" * 80)
        
        # Query Holdings
        # Note: We join with Asset nodes to get the name/type
        holdings_cypher = (
            f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset) "
            f"RETURN a.ticker, a.name, r.shares, r.avg_cost, r.weight_pct, labels(a)[1]"
        )
        holdings_result = self._query_falkor(holdings_cypher)
        
        if not holdings_result or not holdings_result.result_set:
            print(" No holdings found.")
        else:
            print(f"{'TICKER':<10} | {'NAME':<25} | {'SHARES':>10} | {'AVG COST':>11} | {'WEIGHT (%)':>10}")
            print("-" * 80)
            
            total_calc_weight = 0.0
            for row in holdings_result.result_set:
                ticker = row[0]
                name = row[1]
                shares = float(row[2])
                avg_cost = float(row[3])
                weight_pct = float(row[4])
                # label = row[5] # e.g. Stock, Crypto, etc.
                
                total_calc_weight += weight_pct
                
                print(f"{ticker:<10} | {name[:25]:<25} | {shares:>10.2f} | {avg_cost:>11.2f} | {weight_pct*100:>10.1f}%")
            
            print("-" * 80)
            print(f"{'TOTAL':<10} | {'':<25} | {'':>10} | {'':>11} | {total_calc_weight*100:>10.1f}%")
        
        print("="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRM Portfolio Viewer")
    parser.add_argument("--owner", type=str, default="Admin", help="Portfolio Owner")
    
    args = parser.parse_args()
    
    viewer = IRMPortfolioViewer()
    viewer.list_portfolio(owner=args.owner)
