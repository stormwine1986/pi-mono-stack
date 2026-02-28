import os
import json
import logging
import redis
from urllib.parse import urlparse
from falkordb import FalkorDB
from openbb import obb

# 初始化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PEPercentileUpdater:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        
        try:
            # 初始化数据库连接
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
            logger.info(f"Connected to FalkorDB at {host}:{port}")

            # 初始化 Redis 用于读取配置
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            logger.info(f"Connected to Redis for config at {host}:{port}")
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

    def get_valuation_hubs(self):
        """获取所有 PE 枢纽节点"""
        cypher = "MATCH (h:Hub:Valuation) RETURN h.target, id(h), h.name"
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

    def calculate_pe_percentile(self, ticker):
        """拉取实时 PE 并结合 Redis 估值带计算百分位"""
        try:
            logger.info(f"Fetching fundamental metrics for {ticker} via yfinance...")
            # 获取最新基本面指标
            fund_data = obb.equity.fundamental.metrics(ticker, provider="yfinance")
            df_metrics = fund_data.to_dataframe()
            
            if df_metrics.empty:
                logger.warning(f"No metrics data returned for {ticker}")
                return None
            
            # yfinance 的 metrics 返回通常包含 pe_ratio 列
            pe_col = [c for c in df_metrics.columns if 'pe' in c.lower() and 'ratio' in c.lower()]
            if not pe_col:
                logger.warning(f"PE ratio column not found for {ticker}")
                return None
                
            current_pe = float(df_metrics[pe_col[0]].iloc[-1])
            logger.info(f"Target {ticker} Current P/E: {current_pe:.2f}")
            
            # 从 Redis 获取 Bands
            val_min, val_max = 10.0, 40.0  # 默认宽带
            
            band_data = self.redis_client.hget("irm:config:pe_bands", ticker)
            if band_data:
                band = json.loads(band_data)
                val_min = float(band.get("min", val_min))
                val_max = float(band.get("max", val_max))
                logger.info(f"Using Redis Bands for {ticker}: [{val_min}, {val_max}]")
            else:
                logger.warning(f"No PE bands in Redis for {ticker}, using fallback defaults.")

            # 线性映射 0.0 - 1.0 (带极值修剪)
            if current_pe <= val_min:
                percentile = 0.01
            elif current_pe >= val_max:
                percentile = 0.99
            else:
                percentile = (current_pe - val_min) / (val_max - val_min)
                
            return percentile
            
        except Exception as e:
            logger.error(f"Failed to calculate percentile for {ticker}: {e}")
            return None

    def run(self):
        if not self.graph or not self.redis_client:
            return

        hubs = self.get_valuation_hubs()
        logger.info(f"Found {len(hubs)} Valuation Hubs to update.")

        for hub in hubs:
            target = hub['target']
            node_id = hub['node_id']
            
            percentile = self.calculate_pe_percentile(target)
            
            if percentile is not None:
                cypher = f"MATCH (h:Hub) WHERE id(h) = {node_id} SET h.percentile = {percentile:.4f}"
                self.query_falkor(cypher)
                logger.info(f"Successfully updated {target} P/E Percentile: {percentile:.4f}")

if __name__ == "__main__":
    updater = PEPercentileUpdater()
    updater.run()
