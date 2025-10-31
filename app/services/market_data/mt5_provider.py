from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.logger import logger
from app.services.market_data.base_provider import MarketDataProvider
from app.config import settings
from app.core.exceptions import MarketDataUnavailableError



class MT5MarketDataProvider(MarketDataProvider):
    """Provider estrito que usa apenas dados do MT5 Bridge (sem fallback).

    - Retorna cotações somente se houver dados "frescos" no storage do MT5
    - Caso contrário, lança erro (as rotas atuais convertem em 422)
    - Fase 1: option chain/quotes não implementados
    """

    def __init__(self) -> None:
        self.quote_ttl = int(getattr(settings, "MT5_BRIDGE_QUOTE_TTL_SECONDS", 10))
        logger.info("MT5 market data provider enabled (strict)", ttl=self.quote_ttl)

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        symbol = (ticker or "").upper()
        # Lazy import para evitar dependência cíclica
        from MT5.storage import get_latest_quote

        q = get_latest_quote(symbol, ttl_seconds=self.quote_ttl)
        if not q:
            raise MarketDataUnavailableError(
                message=f"No fresh MT5 quote for {symbol}",
                details={"symbol": symbol, "reason": "NO_FRESH_MT5_TICK", "ttl_seconds": self.quote_ttl},
            )

        return {
            "symbol": q.get("symbol") or symbol,
            "current_price": q.get("last") or q.get("current_price") or q.get("bid") or q.get("ask"),
            "bid": q.get("bid"),
            "ask": q.get("ask"),
            "volume": q.get("volume"),
            "timestamp": q.get("ts"),
            "source": "mt5",
        }

    async def get_option_chain(self, ticker: str, expiration: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("MT5 option chain not implemented (Phase 1)")

    async def get_option_quote(self, ticker: str, strike: float, expiration: str, option_type: str) -> Dict[str, Any]:
        raise NotImplementedError("MT5 option quote not implemented (Phase 1)")

    async def get_greeks(self, ticker: str, strike: float, expiration: str, option_type: str) -> Dict[str, Any]:
        raise NotImplementedError("MT5 greeks not implemented (Phase 1)")

    async def health_check(self) -> bool:
        # Considera saudável quando o bridge está habilitado; no futuro, podemos checar heartbeat.
        return bool(settings.MT5_BRIDGE_ENABLED)


# Singleton
mt5_provider = MT5MarketDataProvider()

