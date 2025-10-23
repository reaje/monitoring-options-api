"""Unit tests for market data providers."""

import pytest
from datetime import date, timedelta
from app.services.market_data.mock_provider import MockMarketDataProvider


class TestMockMarketDataProvider:
    """Test MockMarketDataProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return MockMarketDataProvider()

    @pytest.mark.asyncio
    async def test_get_quote_petr4(self, provider):
        """Test getting quote for PETR4."""
        quote = await provider.get_quote("PETR4")

        assert quote["ticker"] == "PETR4"
        assert "current_price" in quote
        assert "bid" in quote
        assert "ask" in quote
        assert "volume" in quote
        assert "timestamp" in quote

        # Price should be near base price
        assert 25 <= quote["current_price"] <= 32

        # Bid should be less than ask
        assert quote["bid"] < quote["ask"]

    @pytest.mark.asyncio
    async def test_get_quote_unknown_ticker(self, provider):
        """Test getting quote for unknown ticker."""
        quote = await provider.get_quote("UNKNOWN")

        assert quote["ticker"] == "UNKNOWN"
        # Should use default price
        assert quote["current_price"] > 0

    @pytest.mark.asyncio
    async def test_get_option_chain(self, provider):
        """Test getting option chain."""
        chain = await provider.get_option_chain("PETR4")

        assert chain["ticker"] == "PETR4"
        assert "underlying_price" in chain
        assert "expirations" in chain
        assert "strikes" in chain
        assert "calls" in chain
        assert "puts" in chain

        # Should have multiple expirations
        assert len(chain["expirations"]) > 0

        # Should have calls and puts
        assert len(chain["calls"]) > 0
        assert len(chain["puts"]) > 0

    @pytest.mark.asyncio
    async def test_get_option_chain_with_expiration_filter(self, provider):
        """Test getting option chain with expiration filter."""
        # Get all expirations first
        chain_all = await provider.get_option_chain("PETR4")
        first_expiration = chain_all["expirations"][0]

        # Filter by first expiration
        chain_filtered = await provider.get_option_chain("PETR4", first_expiration)

        assert len(chain_filtered["expirations"]) == 1
        assert chain_filtered["expirations"][0] == first_expiration

        # All options should have this expiration
        for call in chain_filtered["calls"]:
            assert call["expiration"] == first_expiration

    @pytest.mark.asyncio
    async def test_get_option_quote_call(self, provider):
        """Test getting quote for CALL option."""
        option = await provider.get_option_quote(
            ticker="PETR4",
            strike=30.00,
            expiration=(date.today() + timedelta(days=30)).isoformat(),
            option_type="CALL"
        )

        assert option["ticker"] == "PETR4"
        assert option["strike"] == 30.00
        assert option["option_type"] == "CALL"
        assert "premium" in option
        assert "bid" in option
        assert "ask" in option
        assert "delta" in option
        assert "gamma" in option
        assert "theta" in option
        assert "vega" in option
        assert "volume" in option
        assert "open_interest" in option

        # Bid should be less than premium, premium less than ask
        assert option["bid"] < option["premium"] < option["ask"]

        # CALL delta should be positive
        assert option["delta"] > 0

    @pytest.mark.asyncio
    async def test_get_option_quote_put(self, provider):
        """Test getting quote for PUT option."""
        option = await provider.get_option_quote(
            ticker="VALE3",
            strike=65.00,
            expiration=(date.today() + timedelta(days=30)).isoformat(),
            option_type="PUT"
        )

        assert option["option_type"] == "PUT"
        assert "delta" in option

        # PUT delta should be negative
        assert option["delta"] < 0

    @pytest.mark.asyncio
    async def test_get_greeks(self, provider):
        """Test getting greeks."""
        greeks = await provider.get_greeks(
            ticker="BBAS3",
            strike=45.00,
            expiration=(date.today() + timedelta(days=30)).isoformat(),
            option_type="CALL"
        )

        assert greeks["ticker"] == "BBAS3"
        assert greeks["strike"] == 45.00
        assert greeks["option_type"] == "CALL"
        assert "delta" in greeks
        assert "gamma" in greeks
        assert "theta" in greeks
        assert "vega" in greeks
        assert "rho" in greeks
        assert "timestamp" in greeks

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Test health check."""
        is_healthy = await provider.health_check()

        assert is_healthy is True

    def test_generate_expirations(self, provider):
        """Test expiration generation."""
        expirations = provider._generate_expirations()

        # Should have 6 expirations
        assert len(expirations) == 6

        # All should be in the future
        today = date.today()
        for exp in expirations:
            exp_date = date.fromisoformat(exp)
            assert exp_date > today

    def test_generate_strikes(self, provider):
        """Test strike generation."""
        # Test with low price
        strikes_low = provider._generate_strikes(15.00)
        assert len(strikes_low) > 0
        # Increment should be 0.50
        if len(strikes_low) > 1:
            assert strikes_low[1] - strikes_low[0] == 0.50

        # Test with medium price
        strikes_med = provider._generate_strikes(35.00)
        assert len(strikes_med) > 0
        # Increment should be 1.00
        if len(strikes_med) > 1:
            assert strikes_med[1] - strikes_med[0] == 1.00

        # Test with high price
        strikes_high = provider._generate_strikes(75.00)
        assert len(strikes_high) > 0
        # Increment should be 2.50
        if len(strikes_high) > 1:
            assert strikes_high[1] - strikes_high[0] == 2.50

    def test_calculate_dte(self, provider):
        """Test DTE calculation."""
        future_date = (date.today() + timedelta(days=15)).isoformat()
        dte = provider._calculate_dte(future_date)

        assert dte == 15

    @pytest.mark.asyncio
    async def test_option_itm_vs_otm(self, provider):
        """Test that ITM options have higher premiums than OTM."""
        current_quote = await provider.get_quote("PETR4")
        current_price = current_quote["current_price"]

        expiration = (date.today() + timedelta(days=30)).isoformat()

        # ITM CALL (strike below current price)
        itm_call = await provider.get_option_quote(
            "PETR4",
            current_price - 5,
            expiration,
            "CALL"
        )

        # OTM CALL (strike above current price)
        otm_call = await provider.get_option_quote(
            "PETR4",
            current_price + 5,
            expiration,
            "CALL"
        )

        # ITM should have higher premium
        assert itm_call["premium"] > otm_call["premium"]

        # ITM should have intrinsic value
        assert itm_call["intrinsic_value"] > 0

        # OTM should have no intrinsic value
        assert otm_call["intrinsic_value"] == 0

    @pytest.mark.asyncio
    async def test_option_dte_effect(self, provider):
        """Test that longer DTE options have higher time value."""
        quote = await provider.get_quote("VALE3")
        current_price = quote["current_price"]

        # Use same OTM strike for both
        strike = current_price + 5

        # Short DTE
        short_exp = (date.today() + timedelta(days=7)).isoformat()
        short_option = await provider.get_option_quote(
            "VALE3",
            strike,
            short_exp,
            "CALL"
        )

        # Long DTE
        long_exp = (date.today() + timedelta(days=60)).isoformat()
        long_option = await provider.get_option_quote(
            "VALE3",
            strike,
            long_exp,
            "CALL"
        )

        # Longer DTE should have higher time value
        assert long_option["time_value"] > short_option["time_value"]
