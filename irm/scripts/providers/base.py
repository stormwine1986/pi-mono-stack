from abc import ABC, abstractmethod
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BaseProvider(ABC):
    """Unified interface for all data source providers."""

    @abstractmethod
    def fetch(self, symbol: str, start_date: str) -> pd.DataFrame:
        """
        Fetch historical data and return a DataFrame with at least one numeric column.
        - The caller only cares about the returned DataFrame and value_column.
        - Authentication and column mapping differences are handled by each implementation.
        """
        pass

    @abstractmethod
    def get_value_column(self, df: pd.DataFrame) -> str:
        """Return the column name in the DataFrame that represents the 'price/value'."""
        pass
