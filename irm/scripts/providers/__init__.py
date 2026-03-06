"""
Providers Registry module for data source providers.
Allows dynamically obtaining provider implementations based on name.
"""
import logging
from .yfinance_provider import YFinanceProvider
from .fred_provider import FredProvider
from .akshare_fund_provider import AkShareFundProvider
from .akshare_bond_provider import AkShareBondProvider

logger = logging.getLogger(__name__)

# Registry for providers: provider name -> provider class
PROVIDER_REGISTRY = {
    "yfinance":      YFinanceProvider,
    "fred":          FredProvider,
    "akshare_fund":  AkShareFundProvider,   # 基金净值
    "akshare_bond":  AkShareBondProvider,   # 国债/宏观利率
}

def get_provider(name: str):
    """
    Returns an instance of the provider class with the given name.
    Raises ValueError if provider not found.
    """
    provider_cls = PROVIDER_REGISTRY.get(name.lower())
    if not provider_cls:
        raise ValueError(f"Unsupported provider: {name}. Available providers: {list(PROVIDER_REGISTRY.keys())}")
    
    try:
        return provider_cls()
    except (EnvironmentError, ImportError) as e:
        logger.error(f"Provider {name} could not be initialized: {e}")
        raise
