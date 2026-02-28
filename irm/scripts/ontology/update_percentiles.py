import os
import json
import logging
from urllib.parse import urlparse
from falkordb import FalkorDB
from openbb import obb

# 初始化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OntologyUpdater:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        
        try:
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
            logger.info(f"Connected to FalkorDB at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            self.graph = None

    def query_falkor(self, cypher):
        """执行 Cypher 查询"""
        if not self.graph:
            return None
        try:
            return self.graph.query(cypher)
        except Exception as e:
            logger.error(f"Cypher Query Error: {e}")
            return None

    def get_valuation_hubs(self):
        """获取所有 PE 枢纽节点"""
        cypher = "MATCH (h:Hub:Valuation) RETURN ID(h) as node_id, h.target as target, h.name as name"
        result = self.query_falkor(cypher)
        hubs = []
        if not result or not result.result_set:
            return hubs

        for row in result.result_set:
            try:
                hubs.append({
                    "node_id": row[0],
                    "target": row[1],
                    "name": row[2]
                })
            except (IndexError, TypeError):
                continue
        return hubs

    def calculate_percentile(self, ticker):
        """
        使用 OpenBB 拉取资产的真实 P/E（市盈率）数据，替代原来的单纯收盘价算估值水位。
        调用 openbb.equity.fundamental.metrics 获取当期的 PE Ratio。
        由于免费数据源 (yfinance) 可能无法提供长达数十年的每日【历史 PE 走势序列】，
        此处的简易方案使用当前最新 PE 与该资产硬编码或简单计算的历史 PE 经验带(Bands)做比较，
        映射出一个 0.0 到 1.0 的 percentile 估值水位。
        """
        try:
            # 获取最新基本面指标
            fund_data = obb.equity.fundamental.metrics(ticker, provider="yfinance")
            df_metrics = fund_data.to_dataframe()
            
            if df_metrics.empty or 'pe_ratio' not in df_metrics.columns:
                logger.warning(f"No P/E data found for {ticker}")
                return None
                
            current_pe = float(df_metrics['pe_ratio'].iloc[-1])
            logger.info(f"Target {ticker} Current P/E: {current_pe}")
            
            # --- 从 Redis 分布式配置中心读取历史 PE 经验带(Bands) ---
            # 存储结构为 Redis Hash: 
            #   Key: irm:config:pe_bands
            #   Field: <ticker> (e.g., "AAPL")
            #   Value: JSON {"min": 12.0, "max": 35.0}
            
            val_min, val_max = 10.0, 40.0  # 全局默认均值带
            
            if self.redis_client:
                band_data = self.redis_client.hget("irm:config:pe_bands", ticker)
                if band_data:
                    try:
                        band = json.loads(band_data)
                        val_min = float(band.get("min", val_min))
                        val_max = float(band.get("max", val_max))
                        logger.info(f"Loaded PE bands for {ticker} from Redis: [{val_min}, {val_max}]")
                    except Exception as e:
                        logger.error(f"Failed to parse PE band for {ticker} from Redis: {e}, falling back to defaults")
                else:
                    logger.warning(f"No PE band configured in Redis for {ticker} (Key: irm:config:pe_bands), using default [{val_min}, {val_max}]")

            # 线性插值计算当前水位
            if current_pe <= val_min:
                percentile = 0.01  # 极度低估 1%
            elif current_pe >= val_max:
                percentile = 0.99  # 极度高估 99%
            else:
                percentile = (current_pe - val_min) / (val_max - val_min)
                
            return percentile
            
        except Exception as e:
            logger.error(f"Failed to calculate fundamental percentile for {ticker}: {e}")
            return None

    def update_hub_percentile(self, node_id, new_percentile):
        """更新图谱中 Hub 节点的 percentile 属性"""
        cypher = f"MATCH (h:Hub:Valuation) WHERE ID(h) = {node_id} SET h.percentile = {new_percentile:.4f}"
        self.query_falkor(cypher)

    def run(self):
        if not self.graph:
            logger.error("Database connection missing. Exiting.")
            return

        hubs = self.get_valuation_hubs()
        logger.info(f"Found {len(hubs)} Valuation Hubs to update.")

        for hub in hubs:
            target = hub['target']
            node_id = hub['node_id']
            name = hub['name']
            
            logger.info(f"Processing target: {target} ({name}) ...")
            
            percentile = self.calculate_percentile(target)
            
            if percentile is not None:
                logger.info(f"  -> Calculated Percentile: {percentile:.4f}")
                self.update_hub_percentile(node_id, percentile)
                logger.info(f"  -> Successfully updated DB for {target}")
            else:
                logger.warning(f"  -> Skipping update for {target} due to calculation failure")

if __name__ == "__main__":
    updater = OntologyUpdater()
    updater.run()
