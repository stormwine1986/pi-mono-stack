import pandas as pd
import logging
from .base import BaseProvider

logger = logging.getLogger(__name__)

class AkShareProvider(BaseProvider):
    def fetch(self, symbol: str, start_date: str) -> pd.DataFrame:
        """Fetch historical fund NAV from AkShare (currently supporting open funds)."""
        import akshare as ak
        try:
            # We use the fund_open_fund_info_em to get historical NAV
            # Indicator "单位净值走势" returns '净值日期' and '单位净值'
            df = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
            
            # Filter data based on start_date
            if not df.empty:
                # Ensure date format
                df['净值日期'] = pd.to_datetime(df['净值日期'])
                start_dt = pd.to_datetime(start_date)
                df = df[df['净值日期'] >= start_dt]
            
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data from AkShare for fund {symbol}: {e}")

    def get_value_column(self, df: pd.DataFrame) -> str:
        """The data from EM '单位净值走势' usually has '单位净值' column."""
        return '单位净值'
