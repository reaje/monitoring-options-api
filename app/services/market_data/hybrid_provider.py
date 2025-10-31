from __future__ import annotations

from app.config import settings
from typing import Any, Dict, Optional

from app.core.logger import logger
from app.services.market_data.base_provider import MarketDataProvider
from app.services.market_data.brapi_provider import brapi_provider
from app.services.market_data.mock_provider import mock_provider


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
        # Fase 1: tenta MT5 (sempre None) e cai para fallback
        try:
            from MT5.storage import get_latest_option_quote

            oq = get_latest_option_quote(ticker, strike, expiration, option_type, ttl_seconds=self.quote_ttl)
            if oq:
                return oq
        except Exception:
            pass
        return await self.fallback.get_option_quote(ticker, strike, expiration, option_type)

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

