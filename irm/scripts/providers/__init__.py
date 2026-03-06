"""
Providers Registry module for data source providers.
Allows dynamically obtaining provider implementations based on name.
"""
import logging
from .yfinance_provider import YFinanceProvider
from .fred_provider import FredProvider
from .akshare_provider import AkShareProvider

logger = logging.getLogger(__name__)

# Registry for providers: provider name -> provider class
PROVIDER_REGISTRY = {
    "yfinance": YFinanceProvider,
    "fred": FredProvider,
    "akshare": AkShareProvider,
}

def get_provider(name: str):
    """
    Returns an instance of the provider class with the given name.
    Raises ValueError if provider not found.
    Raises EnvironmentError/ImportError during instantiation if provider dependencies missing.
    """
    provider_cls = PROVIDER_REGISTRY.get(name.lower())
    if not provider_cls:
        raise ValueError(f"Unsupported provider: {name}. Available providers: {list(PROVIDER_REGISTRY.keys())}")
    
    # Return initialized instance
    try:
        return provider_cls()
    except (EnvironmentError, ImportError) as e:
        logger.error(f"Provider {name} could not be initialized: {e}")
        # Re-raising for the caller to handle as fatal for that specific asset
        raise
