"""Base interface for market data providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""

    @abstractmethod
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get current quote for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quote dict with price, bid, ask, volume, etc.
        """
        pass

    @abstractmethod
    async def get_option_chain(
        self,
        ticker: str,
        expiration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get option chain for a ticker.

        Args:
            ticker: Stock ticker symbol
            expiration: Optional expiration date filter (YYYY-MM-DD)

        Returns:
            Option chain dict with calls and puts
        """
        pass

    @abstractmethod
    async def get_option_quote(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str
    ) -> Dict[str, Any]:
        """
        Get quote for a specific option.

        Args:
            ticker: Underlying ticker
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            option_type: 'CALL' or 'PUT'

        Returns:
            Option quote dict
        """
        pass

    @abstractmethod
    async def get_greeks(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str
    ) -> Dict[str, Any]:
        """
        Get option greeks.

        Args:
            ticker: Underlying ticker
            strike: Strike price
            expiration: Expiration date
            option_type: 'CALL' or 'PUT'

        Returns:
            Greeks dict (delta, gamma, theta, vega, rho)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is healthy.

        Returns:
            True if healthy
        """
        pass
