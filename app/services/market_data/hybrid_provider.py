from __future__ import annotations

from app.config import settings
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from app.core.logger import logger
from app.services.market_data.base_provider import MarketDataProvider
from app.services.market_data.brapi_provider import brapi_provider
from app.services.market_data.mock_provider import mock_provider


def _parse_iso(ts: Optional[str]) -> datetime:
    """Parse ISO timestamp string to datetime object."""
    if not ts:
        return datetime.now(timezone.utc)
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


class HybridMarketDataProvider(MarketDataProvider):
    """Provider que prioriza dados recentes do MT5 Bridge e faz fallback.

    - Leitura de dados recente: MT5 (via storage em memória)
    - Fallback: brapi (padrão) ou mock (configurável via MARKET_DATA_HYBRID_FALLBACK)
    """

    def __init__(self, fallback: Optional[str] = None) -> None:
        fb = (fallback or settings.MARKET_DATA_HYBRID_FALLBACK).lower()
        self.fallback = brapi_provider if fb == "brapi" else mock_provider
        self.quote_ttl = int(getattr(settings, "MT5_BRIDGE_QUOTE_TTL_SECONDS", 10))
        logger.info("Hybrid market data provider enabled", fallback=fb, ttl=self.quote_ttl)

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        symbol = (ticker or "").upper()
        try:
            # Lazy import to avoid cyclic dependencies
            from MT5.storage import get_latest_quote

            q = get_latest_quote(symbol, ttl_seconds=self.quote_ttl)
            if q:
                # Normaliza para o contrato esperado pelos consumidores
                return {
                    "symbol": q.get("symbol") or symbol,
                    "current_price": q.get("last") or q.get("current_price") or q.get("bid") or q.get("ask"),
                    "bid": q.get("bid"),
                    "ask": q.get("ask"),
                    "volume": q.get("volume"),
                    "timestamp": q.get("ts"),
                    "source": "mt5",
                }
        except Exception as e:
            logger.warning("Hybrid get_quote MT5 path failed; falling back", ticker=symbol, error=str(e))

        r = await self.fallback.get_quote(symbol)
        r["source"] = "fallback"
        return r

    async def get_option_chain(self, ticker: str, expiration: Optional[str] = None) -> Dict[str, Any]:
        # Fase 1: delega completamente
        return await self.fallback.get_option_chain(ticker, expiration)

    async def get_option_quote(self, ticker: str, strike: float, expiration: str, option_type: str) -> Dict[str, Any]:
        """Get option quote with MT5 priority and intelligent fallback.

        Flow:
        1. Try MT5 cache first (if data exists and is within TTL)
        2. Fallback to brapi/mock if MT5 data not available
        3. Add source tracking for monitoring
        """
        symbol = (ticker or "").upper()

        try:
            from MT5.storage import get_latest_option_quote

            oq = get_latest_option_quote(symbol, strike, expiration, option_type, ttl_seconds=self.quote_ttl)
            if oq:
                logger.info(
                    "Option quote from MT5 cache",
                    ticker=symbol,
                    strike=strike,
                    option_type=option_type,
                    expiration=expiration,
                    mt5_symbol=oq.get("mt5_symbol"),
                    age_seconds=(datetime.now(timezone.utc) - _parse_iso(oq.get("ts"))).total_seconds() if oq.get("ts") else None,
                )
                # Normalize response format to match provider contract
                return {
                    "ticker": oq.get("ticker") or symbol,
                    "strike": oq.get("strike") or strike,
                    "expiration": oq.get("expiration") or expiration,
                    "option_type": oq.get("option_type") or option_type,
                    "bid": oq.get("bid"),
                    "ask": oq.get("ask"),
                    "last": oq.get("last"),
                    "volume": oq.get("volume"),
                    "timestamp": oq.get("ts"),
                    "mt5_symbol": oq.get("mt5_symbol"),
                    "source": "mt5",
                }
        except Exception as e:
            logger.warning(
                "Hybrid get_option_quote MT5 path failed; falling back",
                ticker=symbol,
                strike=strike,
                option_type=option_type,
                expiration=expiration,
                error=str(e),
            )

        # Fallback to external provider
        logger.info(
            "Option quote from fallback provider",
            ticker=symbol,
            strike=strike,
            option_type=option_type,
            expiration=expiration,
        )
        result = await self.fallback.get_option_quote(symbol, strike, expiration, option_type)
        result["source"] = "fallback"
        return result

    async def get_greeks(self, ticker: str, strike: float, expiration: str, option_type: str) -> Dict[str, Any]:
        # Fase 1: delega completamente para fallback
        return await self.fallback.get_greeks(ticker, strike, expiration, option_type)

    async def health_check(self) -> bool:
        # Consider healthy if the fallback is operational
        try:
            return await self.fallback.health_check()
        except Exception:
            return False


# Singleton
hybrid_provider = HybridMarketDataProvider()

