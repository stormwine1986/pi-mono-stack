import pandas as pd
from .base import BaseProvider

class YFinanceProvider(BaseProvider):
    def fetch(self, symbol: str, start_date: str) -> pd.DataFrame:
        """Fetch historical data from yfinance via OpenBB."""
        from openbb import obb
        try:
            res = obb.equity.price.historical(symbol=symbol, provider='yfinance', start_date=start_date)
            return res.to_dataframe()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data from yfinance for symbol {symbol}: {e}")

    def get_value_column(self, df: pd.DataFrame) -> str:
        """yfinance (OpenBB) typically returns 'close' for historical prices."""
        return 'close'
