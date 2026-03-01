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

    def update_all_portfolios(self):
        """Update total_value and weight_pct for all portfolios in the graph."""
        if not self.graph or not self.redis_client:
            return

        # 1. Fetch all portfolios
        portfolios_res = self.query_falkor("MATCH (p:Portfolio) RETURN p.owner, p.name")
        if not portfolios_res or not portfolios_res.result_set:
            logger.warning("No portfolios found in the graph.")
            return

        for p_row in portfolios_res.result_set:
            owner = p_row[0]
            p_name = p_row[1]
            logger.info(f"Updating portfolio for owner: {owner} ({p_name})")
            
            # 2. Fetch holdings and current prices from graph
            holdings_res = self.query_falkor(
                f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset) "
                f"RETURN a.ticker, a.value, id(r)"
            )
            
            if not holdings_res or not holdings_res.result_set:
                logger.warning(f"No holdings found for portfolio: {owner}")
                continue

            total_nav = 0.0
            holdings_data = []

            # 3. Calculate Market Value for each holding
            for h_row in holdings_res.result_set:
                ticker = h_row[0]
                price = float(h_row[1] or 0.0)
                rel_id = h_row[2]
                
                # Fetch shares from Redis
                redis_key = f"irm:portfolio:{owner}:holdings:{ticker}"
                redis_data = self.redis_client.hgetall(redis_key)
                shares = float(redis_data.get('shares', 0.0))
                
                market_value = price * shares
                total_nav += market_value
                holdings_data.append({
                    "ticker": ticker,
                    "rel_id": rel_id,
                    "market_value": market_value
                })

            if total_nav <= 0:
                logger.warning(f"Portfolio {owner} has zero or negative NAV. Skipping weight update.")
                continue

            logger.info(f"Portfolio {owner} Total NAV calculated: {total_nav:,.2f}")

            # 4. Update Portfolio Node and Edge weights
            # Update Portfolio total_value
            self.query_falkor(f"MATCH (p:Portfolio {{owner: '{owner}'}}) SET p.total_value = {total_nav:.2f}")

            # Update weight_pct on each HOLDS edge
            for h in holdings_data:
                weight = h['market_value'] / total_nav
                # Use relationship ID to update specifically
                # Note: falkordb-python doesn't expose relationship ID update easily via ID() in MATCH
                # We use properties to match the edge for safety if ID isn't enough, 
                # but standard Cypher: MATCH ()-[r]->() WHERE ID(r) = {rel_id} SET r.weight_pct = {weight}
                update_rel_cypher = (
                    f"MATCH (p:Portfolio {{owner: '{owner}'}})-[r:HOLDS]->(a:Asset {{ticker: '{h['ticker']}'}}) "
                    f"SET r.weight_pct = {weight:.6f}"
                )
                self.query_falkor(update_rel_cypher)
                logger.debug(f"Updated {h['ticker']} weight to {weight*100:.2f}%")

            logger.info(f"Successfully updated portfolio weights for {owner}.")

if __name__ == "__main__":
    updater = PortfolioWeightUpdater()
    updater.update_all_portfolios()
