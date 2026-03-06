import os
import pandas as pd
import logging
from .base import BaseProvider

logger = logging.getLogger(__name__)

class FredProvider(BaseProvider):
    def __init__(self):
        # FRED provider requires an API key
        self.api_key = os.getenv("FRED_API_KEY")
        if not self.api_key:
            # We raise error here because the provider won't work without its key
            raise EnvironmentError("FRED_API_KEY not found in environment.")

    def fetch(self, symbol: str, start_date: str) -> pd.DataFrame:
        """Fetch historical data from FRED via OpenBB."""
        from openbb import obb
        try:
            # Use api_key passed to fred_series directly
            res = obb.economy.fred_series(symbol=symbol, provider='fred', start_date=start_date, api_key=self.api_key)
            return res.to_dataframe()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data from Fred for symbol {symbol}: {e}")

    def get_value_column(self, df: pd.DataFrame) -> str:
        """FRED (OpenBB) usually returns the symbol name as the value column."""
        # Excluding common non-numeric columns to find the first likely data column
        cols = [c for c in df.columns if c.lower() not in ['date', 'index', 'timestamp']]
        return cols[0] if cols else None
