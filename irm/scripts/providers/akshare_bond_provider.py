import pandas as pd
import logging
from .base import BaseProvider

logger = logging.getLogger(__name__)

class AkShareBondProvider(BaseProvider):
    def fetch(self, symbol: str, start_date: str) -> pd.DataFrame:
        """
        Fetch historical bond yields from AkShare.
        Supports 'bond_zh_us_rate' based indices.
        """
        import akshare as ak
        try:
            # This returns a multi-column dataframe with CN/US rates
            df = ak.bond_zh_us_rate()
            
            if not df.empty:
                # Standardize to 'date' column
                df['日期'] = pd.to_datetime(df['日期'])
                start_dt = pd.to_datetime(start_date)
                df = df[df['日期'] >= start_dt]
                
                # Check if the requested symbol exists as a column
                if symbol not in df.columns:
                     # Check for partial matches if specific column names are hard to remember
                     matches = [c for c in df.columns if symbol in c]
                     if not matches:
                         logger.warning(f"Column '{symbol}' not found in bond_zh_us_rate data. Available: {df.columns.tolist()}")
            
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to fetch bond data from AkShare: {e}")

    def get_value_column(self, df: pd.DataFrame) -> str:
        """
        Return the first column that matches common yield patterns or if it was the symbol.
        In AkShare Bond data, columns are typically '中国国债收益率10年' etc.
        """
        # If the df was filtered for the specific symbol being present, it's safer to find it
        # We look for numeric columns that aren't '日期'
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # Priority 1: Match '10年' if that's what we usually look for
        for col in numeric_cols:
            if '10年' in col and '中国' in col:
                return col
        
        # Priority 2: Return first numeric column
        return numeric_cols[0] if numeric_cols else None
