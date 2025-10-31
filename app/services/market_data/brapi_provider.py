from __future__ import annotations

import asyncio
import json
import math
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, Optional

from app.config import settings
from app.core.logger import logger
from app.services.market_data.base_provider import MarketDataProvider


class BrapiMarketDataProvider(MarketDataProvider):
    """Market data provider using brapi.dev.

    Note: brapi.dev does not expose B3 options chain endpoints. We approximate
    option premiums via Black–Scholes using the underlying quote from brapi
    and configurable defaults for r and sigma.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://brapi.dev/api") -> None:
        self.api_key = api_key or settings.MARKET_DATA_API_KEY
        self.base_url = base_url.rstrip("/")
        # Sensible defaults for Brazil (annualized)
        self.r_annual = 0.11  # 11% risk-free proxy
        self.sigma_annual = 0.35  # 35% vol proxy

    async def _fetch_json(self, url: str) -> Dict[str, Any]:
        def _do_request() -> Dict[str, Any]:
            req = urllib.request.Request(url)
            if self.api_key:
                req.add_header("Authorization", f"Bearer {self.api_key}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))

        return await asyncio.to_thread(_do_request)

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        symbol = (ticker or "").upper()
        url = f"{self.base_url}/quote/{urllib.parse.quote(symbol)}"
        try:
            payload = await self._fetch_json(url)
        except Exception as e:
            logger.warning("brapi.get_quote failed", ticker=symbol, error=str(e))
            return {"symbol": symbol, "current_price": None}

        results = payload.get("results") or payload.get("stocks") or []
        if not results:
            return {"symbol": symbol, "current_price": None}

        r = results[0]
        price = r.get("regularMarketPrice") or r.get("close") or r.get("price")
        try:
            price = float(price) if price is not None else None
        except Exception:
            price = None
        return {
            "symbol": r.get("symbol") or symbol,
            "current_price": price,
            "raw": r,
        }

    # Optional; unused for now
    async def get_option_chain(self, ticker: str, expiration: Optional[str] = None) -> Dict[str, Any]:
        return {"ticker": ticker.upper(), "expiration": expiration, "calls": [], "puts": []}

    async def get_option_quote(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str,
    ) -> Dict[str, Any]:
        """Estimate option premium via Black–Scholes using brapi underlying quote.

        Since brapi lacks B3 options, we compute a synthetic premium so that
        premium-based alerts (< R$ threshold) can operate end-to-end.
        """
        symbol = (ticker or "").upper()
        q = await self.get_quote(symbol)
        S = q.get("current_price")
        if S is None:
            # Cannot price option without underlying; return empty quote
            return {"symbol": symbol, "strike": float(strike), "expiration": expiration, "type": option_type, "premium": None}

        K = float(strike)
        T = self._years_to_expiration(expiration)
        r = self.r_annual
        sigma = self.sigma_annual
        opt_type = (option_type or "").upper()

        premium = None
        greeks: Dict[str, float] = {}
        try:
            premium, greeks = self._black_scholes(S, K, r, sigma, T, opt_type)
        except Exception as e:
            logger.warning("BS pricing failed", error=str(e))

        # Create a simple synthetic spread around premium
        bid = ask = None
        if premium is not None:
            # 2% half-spread, min 0.01
            half = max(0.01, 0.02 * premium)
            bid = max(0.0, premium - half)
            ask = premium + half

        return {
            "symbol": symbol,
            "strike": K,
            "expiration": expiration,
            "type": opt_type,
            "premium": None if premium is None else round(premium, 4),
            "bid": None if bid is None else round(bid, 4),
            "ask": None if ask is None else round(ask, 4),
            "underlying_price": S,
            "greeks": greeks,
            "ts": datetime.utcnow().isoformat() + "Z",
        }

    async def get_greeks(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str,
    ) -> Dict[str, Any]:
        """Return greeks by leveraging the pricing approximation."""
        q = await self.get_option_quote(ticker, strike, expiration, option_type)
        return q.get("greeks", {}) or {}

    async def health_check(self) -> bool:
        try:
            _ = await self.get_quote("BBAS3")
            return True
        except Exception:
            return False

    def _years_to_expiration(self, expiration: str) -> float:
        try:
            if isinstance(expiration, str):
                dt = datetime.fromisoformat(expiration).date()
            elif isinstance(expiration, datetime):
                dt = expiration.date()
            else:
                dt = expiration
            days = max(1, (dt - date.today()).days)
        except Exception:
            days = 30
        return days / 252.0  # trading days per year

    def _black_scholes(
        self,
        S: float,
        K: float,
        r: float,
        sigma: float,
        T: float,
        opt_type: str,
    ) -> tuple[float, Dict[str, float]]:
        # Handle edge cases
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return max(0.0, S - K) if opt_type == "CALL" else max(0.0, K - S), {}

        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        Nd1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2)))
        Nd2 = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2)))
        n_d1 = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)

        df = math.exp(-r * T)
        if opt_type == "CALL":
            price = S * Nd1 - K * df * Nd2
            delta = Nd1
        else:
            # PUT
            price = K * df * (1 - Nd2) - S * (1 - Nd1)
            delta = Nd1 - 1

        gamma = n_d1 / (S * sigma * math.sqrt(T))
        vega = S * n_d1 * math.sqrt(T) / 100.0  # per 1% change
        theta_call = (
            -(S * n_d1 * sigma) / (2 * math.sqrt(T)) - r * K * df * Nd2
        ) / 365.0
        theta_put = (
            -(S * n_d1 * sigma) / (2 * math.sqrt(T)) + r * K * df * (1 - Nd2)
        ) / 365.0
        theta = theta_call if opt_type == "CALL" else theta_put
        rho = (K * T * df * Nd2 / 100.0) if opt_type == "CALL" else (-K * T * df * (1 - Nd2) / 100.0)

        greeks = {
            "delta": float(delta),
            "gamma": float(gamma),
            "theta": float(theta),
            "vega": float(vega),
            "rho": float(rho),
        }
        return float(price), greeks


# Singleton
brapi_provider = BrapiMarketDataProvider()

