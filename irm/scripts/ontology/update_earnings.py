import os
import json
import logging
import redis
from urllib.parse import urlparse
from falkordb import FalkorDB
from openbb import obb

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EPSGrowthUpdater:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            # Initialize FalkorDB connection
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
            logger.info(f"Connected to FalkorDB at {host}:{port}")
        except Exception as e:
            logger.error(f"Initialization Failed: {e}")
            self.graph = None

    def query_falkor(self, cypher):
        if not self.graph:
            return None
        try:
            return self.graph.query(cypher)
        except Exception as e:
            logger.error(f"Cypher Query Error: {e}")
            return None

    def get_earnings_hubs(self):
        """Retrieve all Earnings Hub nodes with their bands"""
        cypher = "MATCH (h:Hub:Earnings) RETURN h.target, id(h), h.name, h.eps_min, h.eps_max"
        result = self.query_falkor(cypher)
        hubs = []
        if not result or not result.result_set:
            return hubs

        for row in result.result_set:
            hubs.append({
                "target": row[0],
                "node_id": row[1],
                "name": row[2],
                "eps_min": row[3],
                "eps_max": row[4]
            })
        return hubs

    def calculate_eps_percentile(self, ticker, val_min=None, val_max=None):
        """Fetch forward growth and map to 0.0 - 1.0 based on Graph bands"""
        try:
            logger.info(f"Fetching fundamental metrics for {ticker}...")
            # Fetch metrics via OpenBB (yfinance provider)
            data = obb.equity.fundamental.metrics(ticker, provider="yfinance")
            df = data.to_dataframe()
            
            if df.empty:
                logger.warning(f"No metrics data returned for {ticker}")
                return None
            
            # Use 'earnings_growth' as the primary forward-looking indicator
            if 'earnings_growth' not in df.columns:
                logger.warning(f"earnings_growth column not found for {ticker}")
                return None
                
            current_growth = float(df['earnings_growth'].iloc[0])
            logger.info(f"Target {ticker} Analyst Forward Earnings Growth: {current_growth:.2%}")
            
            # Use provided bands or defaults
            if val_min is None or val_max is None:
                val_min, val_max = 0.05, 0.40
                logger.warning(f"No bands found on Hub node for {ticker}, using fallback defaults: [{val_min:.2%}, {val_max:.2%}]")
            else:
                logger.info(f"Using Graph-based Growth Bands for {ticker}: [{val_min:.2%}, {val_max:.2%}]")

            # Linear mapping to 0.0 - 1.0 (with extreme value clipping)
            if current_growth <= val_min:
                percentile = 0.05 # Low expectation
            elif current_growth >= val_max:
                percentile = 0.99 # High expectation/Crowded
            else:
                percentile = (current_growth - val_min) / (val_max - val_min)
                
            return percentile, current_growth
            
        except Exception as e:
            logger.error(f"Failed to calculate EPS percentile for {ticker}: {e}")
            return None, None

    def run(self):
        if not self.graph:
            logger.error("Clients not initialized properly. Aborting.")
            return

        hubs = self.get_earnings_hubs()
        logger.info(f"Found {len(hubs)} Earnings Hubs to update.")

        for hub in hubs:
            target = hub['target']
            node_id = hub['node_id']
            eps_min = hub['eps_min']
            eps_max = hub['eps_max']
            
            percentile, current_growth = self.calculate_eps_percentile(target, eps_min, eps_max)
            
            if percentile is not None:
                # Update the hub node in FalkorDB
                cypher = f"MATCH (h:Hub) WHERE id(h) = {node_id} SET h.percentile = {percentile:.4f}, h.value = {current_growth:.4f}"
                self.query_falkor(cypher)
                logger.info(f"Successfully updated {target} EPS Percentile: {percentile:.4f} (Growth: {current_growth:.4f})")

if __name__ == "__main__":
    updater = EPSGrowthUpdater()
    updater.run()
