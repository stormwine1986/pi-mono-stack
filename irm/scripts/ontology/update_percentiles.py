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

    def get_valuation_hubs(self):
        """获取所有 PE 枢纽节点及其自有的经验区间和 ERP 状态"""
        cypher = "MATCH (h:Hub:Valuation) RETURN h.target, id(h), h.name, h.pe_min, h.pe_max, h.erp_percentile"
        result = self.query_falkor(cypher)
        hubs = []
        if not result or not result.result_set:
            return hubs

        for row in result.result_set:
            hubs.append({
                "target": row[0],
                "node_id": row[1],
                "name": row[2],
                "pe_min": row[3],
                "pe_max": row[4],
                "erp_percentile": row[5]
            })
        return hubs

    def calculate_pe_percentile(self, ticker, val_min=None, val_max=None):
        """拉取实时 PE 并利用节点自带的估值带计算百分位"""
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
            
            # 优先使用传入的 Bands，如果没有则使用硬编码默认值
            if val_min is None or val_max is None:
                val_min, val_max = 10.0, 40.0
                logger.warning(f"No bands found on Hub node for {ticker}, using fallback defaults: [{val_min}, {val_max}]")
            else:
                logger.info(f"Using Graph-based Bands for {ticker}: [{val_min}, {val_max}]")

            # 线性映射 0.0 - 1.0 (带极值修剪)
            if current_pe <= val_min:
                percentile = 0.01
            elif current_pe >= val_max:
                percentile = 0.99
            else:
                percentile = (current_pe - val_min) / (val_max - val_min)
                
            return percentile, current_pe
            
        except Exception as e:
            logger.error(f"Failed to calculate percentile for {ticker}: {e}")
            return None, None

    def run(self):
        if not self.graph:
            return

        hubs = self.get_valuation_hubs()
        logger.info(f"Found {len(hubs)} Valuation Hubs to update.")

        for hub in hubs:
            target = hub['target']
            node_id = hub['node_id']
            pe_min = hub['pe_min']
            pe_max = hub['pe_max']
            erp_pct = hub['erp_percentile']
            
            # 1. 计算原始 PE 分位
            pe_percentile, current_pe = self.calculate_pe_percentile(target, pe_min, pe_max)
            
            if pe_percentile is not None:
                # 2. 引入复合逻辑: percentile = max(pe_percentile, 1.0 - erp_percentile)
                # erp_percentile 越低，代表性价比越差，压力越大 (1 - erp)
                erp_pressure = (1.0 - float(erp_pct)) if erp_pct is not None else 0.0
                composite_percentile = max(pe_percentile, erp_pressure)
                
                # 3. 更新节点
                cypher = (
                    f"MATCH (h:Hub) WHERE id(h) = {node_id} "
                    f"SET h.pe_percentile = {pe_percentile:.4f}, "
                    f"    h.percentile = {composite_percentile:.4f}, "
                    f"    h.value = {current_pe:.2f}"
                )
                self.query_falkor(cypher)
                logger.info(f"Updated {target}: PE_Pct={pe_percentile:.4f}, ERP_Pressure={erp_pressure:.4f}, Value={current_pe:.2f} -> Final_Pct={composite_percentile:.4f}")

if __name__ == "__main__":
    updater = PEPercentileUpdater()
    updater.run()
