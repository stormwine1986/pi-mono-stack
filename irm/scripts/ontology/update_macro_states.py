import os
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse
from falkordb import FalkorDB
from openbb import obb
import pandas as pd
import redis

# 初始化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MacroStateUpdater:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        
        # 获取 FRED API KEY
        self.fred_api_key = os.getenv("FRED_API_KEY")
        if self.fred_api_key:
            logger.info("FRED_API_KEY detected in environment.")
        
        try:
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
            logger.info(f"Connected to FalkorDB at {host}:{port}")

            # 初始化 Redis 用于读取配置
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            logger.info(f"Connected to Redis for configuration: {host}:{port}")
        except Exception as e:
            logger.error(f"Initialization Failed: {e}")
            self.graph = None
            self.redis_client = None

    def get_macro_config(self):
        """从 Redis 获取宏观资产配置"""
        if not self.redis_client:
            return {}
        
        try:
            assets = self.redis_client.hgetall("irm:config:sources")
            config = {}
            for ticker, data_str in assets.items():
                config[ticker] = json.loads(data_str)
            return config
        except Exception as e:
            logger.error(f"Failed to load macro config from Redis: {e}")
            return {}

    def query_falkor(self, cypher):
        if not self.graph:
            return None
        try:
            return self.graph.query(cypher)
        except Exception as e:
            logger.error(f"Cypher Query Error: {e}")
            return None

    def get_macro_assets(self, tickers):
        """获取图中的宏观资产节点"""
        cypher = f"MATCH (a:Asset) WHERE a.ticker IN {json.dumps(tickers)} RETURN a.ticker"
        result = self.query_falkor(cypher)
        assets = []
        if not result or not result.result_set:
            return assets
        for row in result.result_set:
            assets.append(row[0])
        return assets

    def calculate_macro_percentile(self, asset_ticker, config):
        """计算宏观资产的历史分位点"""
        asset_config = config.get(asset_ticker)
        if not asset_config:
            logger.warning(f"No config found for {asset_ticker}")
            return None

        symbol = asset_config['symbol']
        provider = asset_config['provider']

        try:
            # 拉取 3 年历史数据用于计算分位
            start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
            
            if provider == 'yfinance':
                res = obb.equity.price.historical(symbol=symbol, provider='yfinance', start_date=start_date)
            elif provider == 'fred':
                if not self.fred_api_key:
                    logger.error(f"Cannot fetch {asset_ticker} from fred: Missing FRED_API_KEY")
                    return None
                # 使用 fred_api_key 参数传入
                res = obb.economy.fred_series(symbol=symbol, provider='fred', start_date=start_date, api_key=self.fred_api_key)
            else:
                logger.error(f"Unsupported provider: {provider}")
                return None

            df = res.to_dataframe()
            
            # 自动探测数值列 (FRED 通常返回 symbol 本身作为列名)
            if provider == 'yfinance':
                value_col = 'close'
            else:
                # 排除可能存在的 date 列，取第一个数值列
                cols = [c for c in df.columns if c.lower() not in ['date', 'index']]
                value_col = cols[0] if cols else None
            
            if df.empty or not value_col or value_col not in df.columns:
                logger.warning(f"No valid data column for {symbol} ({provider}). Columns: {df.columns.tolist()}")
                return None
            
            # 计算分位点
            current_value = df[value_col].iloc[-1]
            percentile = df[value_col].rank(pct=True).iloc[-1]
            
            logger.info(f"Asset {asset_ticker} ({symbol} via {provider}) Value: {current_value:.4f}, Percentile: {percentile:.4f}")
            return percentile
        except Exception as e:
            logger.error(f"Failed to calculate percentile for {asset_ticker} via {provider}: {e}")
            return None

    def update_node_percentile(self, ticker, percentile):
        """同步回 FalkorDB"""
        cypher = f"MATCH (a:Asset {{ticker: '{ticker}'}}) SET a.percentile = {percentile:.4f}"
        self.query_falkor(cypher)

    def run(self):
        if not self.graph:
            return
        
        # 1. 从 Redis 加载配置
        config = self.get_macro_config()
        if not config:
            logger.warning("No macro assets configured in Redis. Skipping update.")
            return

        # 2. 交叉验证图中存在的资产
        macro_tickers = self.get_macro_assets(list(config.keys()))
        logger.info(f"Found macro assets in DB to update: {macro_tickers}")
        
        # 3. 逐个更新
        for ticker in macro_tickers:
            percentile = self.calculate_macro_percentile(ticker, config)
            if percentile is not None:
                self.update_node_percentile(ticker, percentile)
                logger.info(f"Successfully updated {ticker} percentile in DB.")

if __name__ == "__main__":
    updater = MacroStateUpdater()
    updater.run()
