"""Mock market data provider for testing and development."""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from app.services.market_data.base_provider import MarketDataProvider
from app.core.logger import logger


class MockMarketDataProvider(MarketDataProvider):
    """Mock implementation of market data provider."""

    def __init__(self):
        """Initialize mock provider."""
        self.base_prices = {
            "PETR4": 28.50,
            "VALE3": 65.80,
            "BBAS3": 45.20,
            "ITUB4": 32.40,
            "B3SA3": 12.90,
            "BBDC4": 15.60,
            "WEGE3": 42.30,
            "RENT3": 56.70,
            "MGLU3": 4.20,
            "LREN3": 18.40,
        }

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get mock quote for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quote dict
        """
        base_price = self.base_prices.get(ticker, 50.00)

        # Add some random variation (-2% to +2%)
        variation = random.uniform(-0.02, 0.02)
        current_price = base_price * (1 + variation)

        # Calculate bid/ask spread (0.1% to 0.3%)
        spread_pct = random.uniform(0.001, 0.003)
        bid = current_price * (1 - spread_pct / 2)
        ask = current_price * (1 + spread_pct / 2)

        # Previous close
        prev_close = base_price

        # Change
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100

        quote = {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "bid": round(bid, 2),
            "ask": round(ask, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "volume": random.randint(500000, 5000000),
            "high": round(current_price * 1.015, 2),
            "low": round(current_price * 0.985, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "market_status": "open"
        }

        logger.debug("Mock quote generated", ticker=ticker, price=quote["current_price"])

        return quote

    async def get_option_chain(
        self,
        ticker: str,
        expiration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get mock option chain.

        Args:
            ticker: Stock ticker
            expiration: Optional expiration filter

        Returns:
            Option chain dict
        """
        # Get current price
        quote = await self.get_quote(ticker)
        current_price = quote["current_price"]

        # Generate expirations (monthly, next 6 months)
        expirations = self._generate_expirations()

        # Filter by expiration if provided
        if expiration:
            expirations = [exp for exp in expirations if exp == expiration]

        # Generate strikes around current price
        strikes = self._generate_strikes(current_price)

        # Build chain
        calls = []
        puts = []

        for exp in expirations:
            dte = self._calculate_dte(exp)

            for strike in strikes:
                # Generate call
                call = await self._generate_option(
                    ticker, strike, exp, "CALL", current_price, dte
                )
                calls.append(call)

                # Generate put
                put = await self._generate_option(
                    ticker, strike, exp, "PUT", current_price, dte
                )
                puts.append(put)

        chain = {
            "ticker": ticker,
            "underlying_price": current_price,
            "expirations": expirations,
            "strikes": strikes,
            "calls": calls,
            "puts": puts,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        logger.debug(
            "Mock option chain generated",
            ticker=ticker,
            expirations_count=len(expirations),
            calls_count=len(calls),
            puts_count=len(puts)
        )

        return chain

    async def get_option_quote(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str
    ) -> Dict[str, Any]:
        """
        Get mock quote for specific option.

        Args:
            ticker: Underlying ticker
            strike: Strike price
            expiration: Expiration date
            option_type: 'CALL' or 'PUT'

        Returns:
            Option quote
        """
        # Get current price
        quote = await self.get_quote(ticker)
        current_price = quote["current_price"]

        # Calculate DTE
        dte = self._calculate_dte(expiration)

        # Generate option
        option = await self._generate_option(
            ticker, strike, expiration, option_type, current_price, dte
        )

        logger.debug(
            "Mock option quote generated",
            ticker=ticker,
            strike=strike,
            type=option_type,
            premium=option["premium"]
        )

        return option

    async def get_greeks(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str
    ) -> Dict[str, Any]:
        """
        Get mock greeks for option.

        Args:
            ticker: Underlying ticker
            strike: Strike price
            expiration: Expiration date
            option_type: 'CALL' or 'PUT'

        Returns:
            Greeks dict
        """
        # Get option quote (which includes greeks)
        option = await self.get_option_quote(ticker, strike, expiration, option_type)

        greeks = {
            "ticker": ticker,
            "strike": strike,
            "expiration": expiration,
            "option_type": option_type,
            "delta": option.get("delta"),
            "gamma": option.get("gamma"),
            "theta": option.get("theta"),
            "vega": option.get("vega"),
            "rho": option.get("rho"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return greeks

    async def health_check(self) -> bool:
        """Check if mock provider is healthy (always true)."""
        return True

    async def _generate_option(
        self,
        ticker: str,
        strike: float,
        expiration: str,
        option_type: str,
        current_price: float,
        dte: int
    ) -> Dict[str, Any]:
        """Generate mock option data."""
        # Calculate moneyness
        if option_type == "CALL":
            intrinsic = max(0, current_price - strike)
            otm_pct = (strike - current_price) / current_price
        else:  # PUT
            intrinsic = max(0, strike - current_price)
            otm_pct = (current_price - strike) / current_price

        # Calculate time value (simplified)
        # Time value decreases as we get closer to expiration
        time_value = current_price * 0.02 * (dte / 30) * 0.3

        # Adjust time value based on moneyness
        if intrinsic == 0:  # OTM
            time_value *= (1 - abs(otm_pct))

        # Total premium
        premium = intrinsic + time_value
        premium = max(premium, 0.01)  # Minimum 0.01

        # Mock greeks
        if option_type == "CALL":
            delta = 0.50 if abs(strike - current_price) < 1 else (
                0.70 if current_price > strike else 0.30
            )
        else:  # PUT
            delta = -0.50 if abs(strike - current_price) < 1 else (
                -0.70 if current_price < strike else -0.30
            )

        gamma = 0.05 * (30 / max(dte, 1))
        theta = -premium * 0.05
        vega = premium * 0.10
        rho = premium * 0.01 if option_type == "CALL" else -premium * 0.01

        # Mock bid/ask
        spread = max(premium * 0.02, 0.02)  # 2% spread, minimum 0.02
        bid = premium - spread / 2
        ask = premium + spread / 2

        # Mock volume and OI
        volume = random.randint(100, 10000)
        oi = random.randint(1000, 50000)

        return {
            "ticker": ticker,
            "strike": round(strike, 2),
            "expiration": expiration,
            "option_type": option_type,
            "premium": round(premium, 2),
            "bid": round(bid, 2),
            "ask": round(ask, 2),
            "intrinsic_value": round(intrinsic, 2),
            "time_value": round(time_value, 2),
            "delta": round(delta, 4),
            "gamma": round(gamma, 4),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
            "rho": round(rho, 4),
            "volume": volume,
            "open_interest": oi,
            "implied_volatility": round(random.uniform(0.20, 0.40), 4),
            "dte": dte
        }

    def _generate_expirations(self) -> List[str]:
        """Generate mock expiration dates (next 6 monthly expirations)."""
        expirations = []
        current = date.today()

        month_offset = 0
        while len(expirations) < 6:
            # Third Friday of the month
            exp_month = current.month + month_offset
            exp_year = current.year + (exp_month - 1) // 12
            exp_month = ((exp_month - 1) % 12) + 1

            # Find third Friday
            first_day = date(exp_year, exp_month, 1)
            first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
            third_friday = first_friday + timedelta(days=14)

            # Only add if in the future
            if third_friday > current:
                expirations.append(third_friday.isoformat())

            month_offset += 1

        return expirations

    def _generate_strikes(self, current_price: float) -> List[float]:
        """Generate strike prices around current price."""
        strikes = []

        # Determine strike increment based on price
        if current_price < 20:
            increment = 0.50
        elif current_price < 50:
            increment = 1.00
        elif current_price < 100:
            increment = 2.50
        else:
            increment = 5.00

        # Generate strikes from -20% to +20%
        min_strike = current_price * 0.80
        max_strike = current_price * 1.20

        strike = round(min_strike / increment) * increment
        while strike <= max_strike:
            strikes.append(strike)
            strike += increment

        return strikes

    def _calculate_dte(self, expiration: str) -> int:
        """Calculate days to expiration."""
        exp_date = datetime.fromisoformat(expiration).date()
        today = date.today()
        return (exp_date - today).days


# Singleton instance
mock_provider = MockMarketDataProvider()
