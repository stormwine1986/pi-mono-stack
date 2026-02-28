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

            # Initialize Redis for configuration
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            logger.info(f"Connected to Redis at {host}:{port}")
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

    def get_earnings_hubs(self):
        """Retrieve all Earnings Hub nodes"""
        cypher = "MATCH (h:Hub:Earnings) RETURN h.target, id(h), h.name"
        result = self.query_falkor(cypher)
        hubs = []
        if not result or not result.result_set:
            return hubs

        for row in result.result_set:
            hubs.append({
                "target": row[0],
                "node_id": row[1],
                "name": row[2]
            })
        return hubs

    def calculate_eps_percentile(self, ticker):
        """Fetch forward growth and map to 0.0 - 1.0 based on Redis bands"""
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
            
            # Fetch Bands from Redis
            # Default bands: [0.05, 0.40] for growth stocks
            val_min, val_max = 0.05, 0.40
            
            band_data = self.redis_client.hget("irm:config:eps_bands", ticker)
            if band_data:
                band = json.loads(band_data)
                val_min = float(band.get("min", val_min))
                val_max = float(band.get("max", val_max))
                logger.info(f"Using Redis Growth Bands for {ticker}: [{val_min:.2%}, {val_max:.2%}]")
            else:
                logger.warning(f"No EPS bands in Redis for {ticker}, using fallback defaults.")

            # Linear mapping to 0.0 - 1.0 (with extreme value clipping)
            if current_growth <= val_min:
                percentile = 0.05 # Low expectation
            elif current_growth >= val_max:
                percentile = 0.99 # High expectation/Crowded
            else:
                percentile = (current_growth - val_min) / (val_max - val_min)
                
            return percentile
            
        except Exception as e:
            logger.error(f"Failed to calculate EPS percentile for {ticker}: {e}")
            return None

    def run(self):
        if not self.graph or not self.redis_client:
            logger.error("Clients not initialized properly. Aborting.")
            return

        hubs = self.get_earnings_hubs()
        logger.info(f"Found {len(hubs)} Earnings Hubs to update.")

        for hub in hubs:
            target = hub['target']
            node_id = hub['node_id']
            
            percentile = self.calculate_eps_percentile(target)
            
            if percentile is not None:
                # Update the hub node in FalkorDB
                cypher = f"MATCH (h:Hub) WHERE id(h) = {node_id} SET h.percentile = {percentile:.4f}"
                self.query_falkor(cypher)
                logger.info(f"Successfully updated {target} EPS Percentile: {percentile:.4f}")

if __name__ == "__main__":
    updater = EPSGrowthUpdater()
    updater.run()
