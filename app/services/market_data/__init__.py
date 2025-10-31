"""Market data service factory."""

from app.config import settings
from app.services.market_data.base_provider import MarketDataProvider
from app.services.market_data.mock_provider import mock_provider
from app.services.market_data.brapi_provider import brapi_provider
from app.services.market_data.hybrid_provider import hybrid_provider
from app.services.market_data.mt5_provider import mt5_provider

from app.core.logger import logger


def get_market_data_provider() -> MarketDataProvider:
    """
    Get market data provider instance based on configuration.

    Returns:
        MarketDataProvider instance
    """
    provider_type = settings.MARKET_DATA_PROVIDER.lower()

    if provider_type == "mock":
        logger.info("Using mock market data provider")
        return mock_provider
    if provider_type == "brapi":
        logger.info("Using brapi.dev market data provider")
        return brapi_provider
    if provider_type == "hybrid":
        logger.info("Using hybrid (MT5 + fallback) market data provider")
        return hybrid_provider
    if provider_type == "mt5":
        logger.info("Using MT5 market data provider (strict)")
        return mt5_provider
    # Future: Add real providers here
    # elif provider_type == "yahoo":
    #     return yahoo_provider
    # elif provider_type == "alpha_vantage":
    #     return alpha_vantage_provider
    logger.warning(
        f"Unknown market data provider: {provider_type}, falling back to mock"
    )
    return mock_provider


# Export provider instance
market_data_provider = get_market_data_provider()
