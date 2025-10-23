"""Unit tests for roll calculator."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta
from uuid import uuid4
from app.services.roll_calculator import RollCalculator


class TestRollCalculator:
    """Test RollCalculator service."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return RollCalculator()

    @pytest.fixture
    def sample_position(self):
        """Create sample position."""
        return {
            "id": str(uuid4()),
            "account_id": str(uuid4()),
            "asset_id": str(uuid4()),
            "ticker": "PETR4",
            "side": "CALL",
            "strike": 100.00,
            "expiration": (date.today() + timedelta(days=5)).isoformat(),
            "quantity": 100,
            "avg_premium": 2.50
        }

    @pytest.fixture
    def sample_rule(self):
        """Create sample rule."""
        return {
            "id": str(uuid4()),
            "delta_threshold": 0.60,
            "dte_min": 21,
            "dte_max": 45,
            "target_otm_pct_low": 0.03,
            "target_otm_pct_high": 0.08,
            "min_volume": 1000,
            "max_spread": 0.05,
            "min_oi": 5000
        }

    def test_calculate_dte_with_string(self, calculator):
        """Test DTE calculation with string date."""
        future_date = (date.today() + timedelta(days=30)).isoformat()
        dte = calculator._calculate_dte(future_date)

        assert dte == 30

    def test_calculate_dte_with_date_object(self, calculator):
        """Test DTE calculation with date object."""
        future_date = date.today() + timedelta(days=15)
        dte = calculator._calculate_dte(future_date)

        assert dte == 15

    def test_estimate_premium_call_otm(self, calculator):
        """Test premium estimation for OTM CALL."""
        premium = calculator._estimate_premium(
            current_price=100.0,
            strike=105.0,  # OTM
            dte=30,
            side="CALL"
        )

        # Should be > 0 (time value only)
        assert premium > 0
        # Should be less than for ITM
        assert premium < 5.0

    def test_estimate_premium_call_itm(self, calculator):
        """Test premium estimation for ITM CALL."""
        premium = calculator._estimate_premium(
            current_price=105.0,
            strike=100.0,  # ITM
            dte=30,
            side="CALL"
        )

        # Should include intrinsic value (5.0) + time value
        assert premium >= 5.0

    def test_estimate_premium_put_otm(self, calculator):
        """Test premium estimation for OTM PUT."""
        premium = calculator._estimate_premium(
            current_price=105.0,
            strike=100.0,  # OTM
            dte=30,
            side="PUT"
        )

        # Should be > 0 (time value only)
        assert premium > 0
        assert premium < 5.0

    def test_estimate_premium_put_itm(self, calculator):
        """Test premium estimation for ITM PUT."""
        premium = calculator._estimate_premium(
            current_price=95.0,
            strike=100.0,  # ITM
            dte=30,
            side="PUT"
        )

        # Should include intrinsic value (5.0) + time value
        assert premium >= 5.0

    def test_calculate_position_metrics(self, calculator, sample_position):
        """Test calculation of position metrics."""
        market_data = {
            "current_price": 98.0,
            "bid": 97.95,
            "ask": 98.05
        }

        metrics = calculator._calculate_position_metrics(
            sample_position,
            market_data
        )

        assert "dte" in metrics
        assert "otm_pct" in metrics
        assert "is_itm" in metrics
        assert "current_premium" in metrics
        assert "pnl" in metrics
        assert "current_price" in metrics

        # For CALL at 100 strike with price at 98, should be OTM
        assert metrics["is_itm"] is False
        assert metrics["otm_pct"] > 0

    def test_calculate_suggestion_score_high_credit(self, calculator, sample_rule):
        """Test scoring with high net credit."""
        score = calculator._calculate_suggestion_score(
            otm_pct=0.05,  # 5% OTM (in target range)
            net_credit=5.0,  # Good credit
            dte=30,  # In DTE range
            rule=sample_rule
        )

        # Should be high score
        assert score > 50

    def test_calculate_suggestion_score_zero_credit(self, calculator, sample_rule):
        """Test scoring with zero net credit."""
        score = calculator._calculate_suggestion_score(
            otm_pct=0.05,
            net_credit=0.0,  # No credit
            dte=30,
            rule=sample_rule
        )

        # Should be lower than with good credit, but other factors still contribute
        # Credit is 40% of score, so max without credit is 60
        assert score < 60
        assert score > 0

    def test_calculate_suggestion_score_negative_credit(self, calculator, sample_rule):
        """Test scoring with negative net credit."""
        score = calculator._calculate_suggestion_score(
            otm_pct=0.05,
            net_credit=-2.0,  # Debit
            dte=30,
            rule=sample_rule
        )

        # Should be low score (negative credit gets 0 points)
        # Other factors can still contribute up to 60 points
        assert score < 60
        assert score >= 0

    def test_get_default_rule(self, calculator):
        """Test getting default rule."""
        rule = calculator._get_default_rule()

        assert rule["delta_threshold"] == 0.60
        assert rule["dte_min"] == 21
        assert rule["dte_max"] == 45
        assert rule["target_otm_pct_low"] == 0.03
        assert rule["target_otm_pct_high"] == 0.08

    def test_get_mock_market_data(self, calculator, sample_position):
        """Test getting mock market data."""
        market_data = calculator._get_mock_market_data(sample_position)

        assert "ticker" in market_data
        assert "current_price" in market_data
        assert "bid" in market_data
        assert "ask" in market_data
        assert "volume" in market_data

        # Current price should be near strike
        assert 95 <= market_data["current_price"] <= 105

    @pytest.mark.asyncio
    @patch('app.services.roll_calculator.OptionsRepository')
    @patch('app.services.roll_calculator.RulesRepository')
    async def test_generate_suggestions(
        self,
        mock_rules_repo,
        mock_options_repo,
        calculator,
        sample_position,
        sample_rule
    ):
        """Test generating roll suggestions."""
        market_data = {
            "current_price": 98.0,
            "bid": 97.95,
            "ask": 98.05
        }

        suggestions = await calculator._generate_suggestions(
            sample_position,
            sample_rule,
            market_data
        )

        # Should generate suggestions
        assert len(suggestions) > 0
        assert len(suggestions) <= 5  # Returns top 5

        # Check structure of first suggestion
        first = suggestions[0]
        assert "strike" in first
        assert "expiration" in first
        assert "dte" in first
        assert "otm_pct" in first
        assert "premium" in first
        assert "net_credit" in first
        assert "score" in first

        # Suggestions should be sorted by score (highest first)
        if len(suggestions) > 1:
            assert suggestions[0]["score"] >= suggestions[1]["score"]

    @pytest.mark.asyncio
    @patch('app.services.roll_calculator.OptionsRepository')
    @patch('app.services.roll_calculator.RulesRepository')
    async def test_get_roll_preview(
        self,
        mock_rules_repo,
        mock_options_repo,
        calculator,
        sample_position,
        sample_rule
    ):
        """Test getting full roll preview."""
        position_id = uuid4()

        # Setup mocks
        mock_options_repo.get_by_id = AsyncMock(return_value=sample_position)
        mock_rules_repo.get_active_rules = AsyncMock(return_value=[sample_rule])

        # Execute
        preview = await calculator.get_roll_preview(position_id)

        # Assertions
        assert "current_position" in preview
        assert "suggestions" in preview
        assert "market_data" in preview
        assert "rule_used" in preview

        # Current position should have metrics
        assert "dte" in preview["current_position"]
        assert "otm_pct" in preview["current_position"]
        assert "pnl" in preview["current_position"]

        # Should have suggestions
        assert len(preview["suggestions"]) > 0

    @pytest.mark.asyncio
    @patch('app.services.roll_calculator.OptionsRepository')
    async def test_get_roll_preview_position_not_found(
        self,
        mock_options_repo,
        calculator
    ):
        """Test roll preview with non-existent position."""
        position_id = uuid4()

        # Setup mock to return None
        mock_options_repo.get_by_id = AsyncMock(return_value=None)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Position not found"):
            await calculator.get_roll_preview(position_id)

    @pytest.mark.asyncio
    @patch('app.services.roll_calculator.OptionsRepository')
    @patch('app.services.roll_calculator.RulesRepository')
    async def test_get_roll_preview_uses_default_rule_if_no_active(
        self,
        mock_rules_repo,
        mock_options_repo,
        calculator,
        sample_position
    ):
        """Test that default rule is used when no active rules exist."""
        position_id = uuid4()

        # Setup mocks - no active rules
        mock_options_repo.get_by_id = AsyncMock(return_value=sample_position)
        mock_rules_repo.get_active_rules = AsyncMock(return_value=[])

        # Execute
        preview = await calculator.get_roll_preview(position_id)

        # Should still generate preview with default rule
        assert "suggestions" in preview
        assert preview["rule_used"]["dte_min"] == 21  # Default value
