import os
import json
import logging
import warnings
from datetime import datetime, timedelta
from urllib.parse import urlparse
import pandas as pd
import numpy as np
from scipy import stats
from falkordb import FalkorDB
from openbb import obb
import redis

warnings.filterwarnings('ignore', category=FutureWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BetaCalculator:
    def __init__(self, graph_name="Graph-001"):
        self.graph_name = graph_name
        self.data_cache = {}
        
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        
        self.fred_api_key = os.getenv("FRED_API_KEY")
        
        try:
            self.db = FalkorDB(host=host, port=port)
            self.graph = self.db.select_graph(graph_name)
            logger.info(f"Connected to FalkorDB at {host}:{port}")

            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            logger.info("Connected to Redis for configuration.")
        except Exception as e:
            logger.error(f"Initialization Failed: {e}")
            self.graph = None
            self.redis_client = None

        self.asset_config = self._build_asset_config()

    def _build_asset_config(self):
        config = {}
        try:
            if self.redis_client:
                assets = self.redis_client.hgetall("irm:config:sources")
                for ticker, data_str in assets.items():
                    data = json.loads(data_str)
                    config[ticker] = {
                        'symbol': data.get('symbol'),
                        'provider': data.get('provider')
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch override config from Redis: {e}")
        return config

    def query_falkor(self, cypher):
        if not self.graph:
            return None
        return self.graph.query(cypher)

    def fetch_historical_data(self, ticker, metric_type):
        if ticker in self.data_cache:
            return self.data_cache[ticker]

        config = self.asset_config.get(ticker)
        if not config:
            logger.warning(f"No configuration found in Redis for {ticker}")
            return None

        symbol = config['symbol']
        provider = config['provider']
        asset_type = metric_type  # From Graph

        start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
        df = pd.DataFrame()

        try:
            logger.info(f"Fetching 3Y historical data for {ticker} ({symbol} via {provider})")
            if provider == 'yfinance':
                res = obb.equity.price.historical(symbol=symbol, provider='yfinance', start_date=start_date)
            elif provider == 'fred':
                if not self.fred_api_key:
                    logger.error(f"Missing FRED_API_KEY to fetch {ticker}")
                    return None
                res = obb.economy.fred_series(symbol=symbol, provider='fred', start_date=start_date, api_key=self.fred_api_key)
            else:
                return None

            df = res.to_dataframe()
            if df.empty:
                return None

            # 探测数值列
            if provider == 'yfinance':
                value_col = 'close'
            else:
                cols = [c for c in df.columns if c.lower() not in ['date', 'index']]
                value_col = cols[0] if cols else None

            if not value_col or value_col not in df.columns:
                return None

            # 清理和对齐索引为 DatetimeIndex
            series = df[[value_col]].copy()
            series.index = pd.to_datetime(series.index)
            # 降采样到周线周末收盘 (Weekly Returns)，平滑日常噪音
            weekly_series = series.resample('W-FRI').last()
            
            # 区分计算方式
            if asset_type in ['rate', 'volatility']:
                # 收益率本身就是百分比，不需要再算百分比，计算绝对增量
                returns = weekly_series[value_col].diff()
            else:
                # 股票/ETF/大宗/外汇 算对数收益率或百分比变化
                returns = weekly_series[value_col].pct_change() * 100.0

            returns = returns.dropna()
            self.data_cache[ticker] = returns
            return returns

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None

    def run(self):
        if not self.graph:
            return

        # 获取所有两端都是 Asset 且包含基准贝塔的宏观传导边
        cypher = """
        MATCH (a:Asset)-[r]->(b:Asset)
        WHERE type(r) IN ['PRICES', 'DRIVES', 'SPILLS_TO', 'CORRELATES_WITH'] 
          AND r.base_beta IS NOT NULL
        RETURN a.ticker, b.ticker, type(r), r.base_beta, a.metric_type, b.metric_type
        """
        res = self.query_falkor(cypher)
        if not res or not res.result_set:
            logger.info("No eligible edges found to calc beta.")
            return

        updates = []
        for row in res.result_set:
            source, target, rel_type, current_beta, source_type, target_type = row[0], row[1], row[2], row[3], row[4], row[5]

            # 读取时间序列
            x_series = self.fetch_historical_data(source, source_type)
            y_series = self.fetch_historical_data(target, target_type)

            if x_series is None or y_series is None:
                continue

            # 对齐数据（按日期交集）
            aligned_df = pd.concat([x_series, y_series], axis=1, join='inner').dropna()
            if len(aligned_df) < 50:  # 至少需要约1年的周线数据 (~50周)
                logger.warning(f"Not enough overlapping data points for {source} -> {target} ({len(aligned_df)})")
                continue

            # X 为自变量, Y 为因变量
            x_vals = aligned_df.iloc[:, 0].values
            y_vals = aligned_df.iloc[:, 1].values

            # 使用 scipy 计算线性回归 OLS 
            # Y = beta*X + alpha
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)

            # 更新策略
            # P值 < 0.1 代表统计学显著。如果完全不相关，这根边在宏观上可能没有纯线性意义，但可能存在非线性意义
            is_significant = p_value < 0.1
            
            logger.info(f"Edge: {source} -> {target} ({rel_type}) | Old Beta: {current_beta:.2f} | "
                        f"New Calc Beta: {slope:.3f} | R2: {r_value**2:.3f} | P-val: {p_value:.4f}")
            
            if is_significant:
                updates.append((source, target, rel_type, slope))
            else:
                logger.warning(f"  -> Skipping update for {source}->{target}: Regression not statistically significant (p={p_value:.4f})")

        # 批量写回核心数据库
        if updates:
            logger.info("Committing updated betas to FalkorDB...")
            for src, tgt, rtype, new_beta in updates:
                update_cypher = f"""
                MATCH (a:Asset {{ticker: '{src}'}})-[r:{rtype}]->(b:Asset {{ticker: '{tgt}'}})
                SET r.base_beta = {new_beta:.3f}
                """
                self.query_falkor(update_cypher)
            logger.info(f"Successfully updated {len(updates)} edge(s)!")

if __name__ == "__main__":
    calculator = BetaCalculator()
    calculator.run()
