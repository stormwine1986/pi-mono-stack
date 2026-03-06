import os
import json
import redis
import logging
from urllib.parse import urlparse
from falkordb import FalkorDB

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PortfolioWeightUpdater:
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

    def _get_fx_rates(self, base_currency):
        """Fetch FX rates from graph (Asset:Macro:Currency nodes) relative to base_currency.
        
        Convention: A node like USDCNY with value=7.28 means 1 USD = 7.28 CNY.
        Returns a dict mapping denomination -> multiplier to convert TO base_currency.
        e.g. if base='USD': {'USD': 1.0, 'CNY': 0.1374, 'JPY': 0.0067, 'HKD': 0.128}
        """
        fx_rates = {base_currency: 1.0}
        
        # Common FX pair conventions: USD is usually the base in USDXXX pairs
        # We look for pairs where base_currency is involved
        fx_pairs = [
            # (ticker, from_ccy, to_ccy) - ticker value = how many to_ccy per 1 from_ccy
            ("USDCNY", "USD", "CNY"),
            ("USDJPY", "USD", "JPY"),
            ("USDHKD", "USD", "HKD"),
            ("USDKRW", "USD", "KRW"),
            ("USDGBP", "USD", "GBP"),
            ("USDEUR", "USD", "EUR"),
            ("EURUSD", "EUR", "USD"),
            ("GBPUSD", "GBP", "USD"),
        ]
        
        for ticker, from_ccy, to_ccy in fx_pairs:
            res = self.query_falkor(f"MATCH (fx:Asset {{ticker: '{ticker}'}}) RETURN fx.value")
            if res and res.result_set and res.result_set[0][0] is not None:
                rate = float(res.result_set[0][0])
                if rate <= 0:
                    continue
                # rate = how many to_ccy per 1 from_ccy
                if from_ccy == base_currency:
                    # to convert to_ccy -> base: divide by rate
                    fx_rates[to_ccy] = 1.0 / rate
                elif to_ccy == base_currency:
                    # to convert from_ccy -> base: multiply by rate
                    fx_rates[from_ccy] = rate
        
        return fx_rates

    def update_all_portfolios(self):
        """Update total_value and weight_pct for all portfolios in the graph.
        
        Multi-currency logic:
        1. Group holdings by denomination (from Redis or edge attribute)
        2. Calculate per-slot NAV in local currency
        3. Convert to base currency using FX rates from graph
        4. Compute global weight_pct in base currency terms
        """
        if not self.graph or not self.redis_client:
            return

        # 1. Fetch all portfolios
        portfolios_res = self.query_falkor("MATCH (p:Portfolio) RETURN p.owner, p.name, p.currency")
        if not portfolios_res or not portfolios_res.result_set:
            logger.warning("No portfolios found in the graph.")
            return

        for p_row in portfolios_res.result_set:
            owner = p_row[0]
            p_name = p_row[1]
            base_currency = p_row[2] or "USD"
            logger.info(f"Updating portfolio for owner: {owner} ({p_name}), base currency: {base_currency}")
            
            # 2. Fetch holdings and current prices from graph (including denomination on edge)
            holdings_res = self.query_falkor(
                f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset) "
                f"RETURN a.ticker, a.value, id(r), r.denomination"
            )
            
            if not holdings_res or not holdings_res.result_set:
                logger.warning(f"No holdings found for portfolio: {owner}")
                continue

            # 3. Build holdings data with denomination awareness
            holdings_data = []
            denominations_used = set()

            for h_row in holdings_res.result_set:
                ticker = h_row[0]
                price = float(h_row[1] or 0.0)
                rel_id = h_row[2]
                edge_denom = h_row[3] if len(h_row) > 3 and h_row[3] else None
                
                # Fetch shares and denomination from Redis
                redis_key = f"irm:portfolio:{owner}:holdings:{ticker}"
                redis_data = self.redis_client.hgetall(redis_key)
                shares = float(redis_data.get('shares', 0.0))
                # Denomination priority: edge attribute > Redis > base_currency fallback
                denomination = edge_denom or redis_data.get('denomination', base_currency)
                
                market_value = price * shares
                denominations_used.add(denomination)
                holdings_data.append({
                    "ticker": ticker,
                    "rel_id": rel_id,
                    "market_value": market_value,
                    "denomination": denomination
                })

            # 4. Fetch FX rates only if multi-currency
            if len(denominations_used) > 1 or (len(denominations_used) == 1 and base_currency not in denominations_used):
                fx_rates = self._get_fx_rates(base_currency)
                logger.info(f"FX Rates (to {base_currency}): {fx_rates}")
            else:
                fx_rates = {base_currency: 1.0}

            # 5. Calculate total NAV in base currency
            total_nav_base = 0.0
            slot_navs = {}  # { denomination: local_nav }
            
            for h in holdings_data:
                denom = h["denomination"]
                slot_navs[denom] = slot_navs.get(denom, 0.0) + h["market_value"]
            
            for denom, local_nav in slot_navs.items():
                fx = fx_rates.get(denom, 1.0)
                total_nav_base += local_nav * fx
                logger.info(f"  Slot [{denom}]: Local NAV = {local_nav:,.2f} {denom} "
                           f"(× {fx:.6f} = {local_nav * fx:,.2f} {base_currency})")

            if total_nav_base <= 0:
                logger.warning(f"Portfolio {owner} has zero or negative NAV. Skipping weight update.")
                continue

            logger.info(f"Portfolio {owner} Total NAV: {total_nav_base:,.2f} {base_currency}")

            # 6. Update Portfolio Node total_value (in base currency)
            self.query_falkor(f"MATCH (p:Portfolio {{owner: '{owner}'}}) SET p.total_value = {total_nav_base:.2f}")

            # 7. Update weight_pct on each HOLDS edge (global weight in base currency terms)
            for h in holdings_data:
                fx = fx_rates.get(h["denomination"], 1.0)
                global_weight = (h['market_value'] * fx) / total_nav_base
                
                update_rel_cypher = (
                    f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset {{ticker: '{h['ticker']}'}}) "
                    f"SET r.weight_pct = {global_weight:.6f}, r.denomination = '{h['denomination']}'"
                )
                self.query_falkor(update_rel_cypher)
                logger.debug(f"Updated {h['ticker']} weight to {global_weight*100:.2f}% (denom: {h['denomination']})")

            logger.info(f"Successfully updated portfolio weights for {owner}.")

if __name__ == "__main__":
    updater = PortfolioWeightUpdater()
    updater.update_all_portfolios()
