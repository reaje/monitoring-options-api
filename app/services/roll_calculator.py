"""Roll calculator service for generating roll suggestions."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from app.database.repositories.options import OptionsRepository
from app.database.repositories.rules import RulesRepository
from app.core.logger import logger


class RollCalculator:
    """Service for calculating roll suggestions."""

    def __init__(self):
        """Initialize roll calculator."""
        pass

    async def get_roll_preview(
        self,
        position_id: UUID,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate roll preview with suggestions for a position.

        Args:
            position_id: Position UUID
            market_data: Optional market data (if None, uses mock data)

        Returns:
            Preview dict with current position and suggestions
        """
        # Get current position
        position = await OptionsRepository.get_by_id(position_id)

        if not position:
            raise ValueError("Position not found")

        # Get account rules
        account_id = UUID(position["account_id"])
        rules = await RulesRepository.get_active_rules(account_id)

        # Use first rule or defaults
        rule = rules[0] if rules else self._get_default_rule()

        # Get current market data (or mock)
        if market_data is None:
            market_data = self._get_mock_market_data(position)

        # Generate suggestions
        suggestions = await self._generate_suggestions(
            position,
            rule,
            market_data
        )

        # Calculate current position metrics
        current_metrics = self._calculate_position_metrics(
            position,
            market_data
        )

        logger.info(
            "Roll preview generated",
            position_id=str(position_id),
            suggestions_count=len(suggestions)
        )

        return {
            "current_position": {
                **position,
                **current_metrics
            },
            "suggestions": suggestions,
            "market_data": market_data,
            "rule_used": rule
        }

    async def _generate_suggestions(
        self,
        position: Dict[str, Any],
        rule: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate roll suggestions based on rules and market data.

        Args:
            position: Current position
            rule: Roll rule configuration
            market_data: Market data

        Returns:
            List of roll suggestions sorted by score
        """
        suggestions = []

        current_price = market_data.get("current_price", 0)
        current_strike = float(position.get("strike", 0))
        side = position.get("side", "CALL")

        # Get target OTM percentages from rule
        otm_low = float(rule.get("target_otm_pct_low", 0.03))
        otm_high = float(rule.get("target_otm_pct_high", 0.08))

        # Get DTE range from rule
        dte_min = rule.get("dte_min", 21)
        dte_max = rule.get("dte_max", 45)

        # Calculate target strike range
        if side == "CALL":
            # For CALL, OTM means above current price
            strike_low = current_price * (1 + otm_low)
            strike_high = current_price * (1 + otm_high)
        else:  # PUT
            # For PUT, OTM means below current price
            strike_low = current_price * (1 - otm_high)
            strike_high = current_price * (1 - otm_low)

        # Generate suggestion grid
        # In production, this would fetch real options chain
        strike_increments = [0.03, 0.05, 0.08, 0.10, 0.12]
        dte_options = [21, 30, 45, 60]

        for dte in dte_options:
            if dte < dte_min or dte > dte_max:
                continue

            expiration = (date.today() + timedelta(days=dte)).isoformat()

            for increment in strike_increments:
                if side == "CALL":
                    new_strike = current_price * (1 + increment)
                else:
                    new_strike = current_price * (1 - increment)

                # Check if strike is in target range
                if not (strike_low <= new_strike <= strike_high):
                    continue

                # Calculate OTM percentage
                otm_pct = abs(new_strike - current_price) / current_price

                # Mock option data (in production, fetch from market)
                premium = self._estimate_premium(
                    current_price,
                    new_strike,
                    dte,
                    side
                )

                # Calculate net credit (new premium - buyback cost)
                # Assuming buyback at current premium estimate
                buyback_cost = self._estimate_premium(
                    current_price,
                    current_strike,
                    self._calculate_dte(position.get("expiration")),
                    side
                )

                net_credit = premium - buyback_cost

                # Calculate score
                score = self._calculate_suggestion_score(
                    otm_pct,
                    net_credit,
                    dte,
                    rule
                )

                suggestion = {
                    "strike": round(new_strike, 2),
                    "expiration": expiration,
                    "dte": dte,
                    "otm_pct": round(otm_pct * 100, 2),
                    "premium": round(premium, 2),
                    "net_credit": round(net_credit, 2),
                    "spread": 0.02,  # Mock 2% spread
                    "volume": 5000,  # Mock volume
                    "oi": 10000,  # Mock open interest
                    "score": round(score, 2)
                }

                suggestions.append(suggestion)

        # Sort by score (highest first)
        suggestions.sort(key=lambda x: x["score"], reverse=True)

        # Return top 5 suggestions
        return suggestions[:5]

    def _calculate_suggestion_score(
        self,
        otm_pct: float,
        net_credit: float,
        dte: int,
        rule: Dict[str, Any]
    ) -> float:
        """
        Calculate score for a roll suggestion.

        Higher score = better suggestion

        Args:
            otm_pct: Out-of-money percentage
            net_credit: Net credit of the roll
            dte: Days to expiration
            rule: Roll rule

        Returns:
            Score (0-100)
        """
        score = 0.0

        # Reward net credit (40 points max)
        if net_credit > 0:
            # More credit = higher score
            score += min(net_credit * 10, 40)

        # Reward OTM in target range (30 points max)
        target_otm_low = rule.get("target_otm_pct_low", 0.03)
        target_otm_high = rule.get("target_otm_pct_high", 0.08)
        target_otm = (target_otm_low + target_otm_high) / 2

        otm_distance = abs(otm_pct - target_otm)
        otm_score = max(0, 30 - (otm_distance * 300))
        score += otm_score

        # Reward DTE in target range (20 points max)
        dte_min = rule.get("dte_min", 21)
        dte_max = rule.get("dte_max", 45)
        target_dte = (dte_min + dte_max) / 2

        dte_distance = abs(dte - target_dte)
        dte_score = max(0, 20 - (dte_distance / 2))
        score += dte_score

        # Bonus for liquidity (10 points max) - currently mock
        score += 10

        return score

    def _estimate_premium(
        self,
        current_price: float,
        strike: float,
        dte: int,
        side: str
    ) -> float:
        """
        Estimate option premium (mock calculation).

        In production, this would use Black-Scholes or fetch from market.

        Args:
            current_price: Current underlying price
            strike: Strike price
            dte: Days to expiration
            side: CALL or PUT

        Returns:
            Estimated premium
        """
        # Very simplified mock calculation
        # Real implementation would use Black-Scholes or market data

        # Calculate intrinsic value
        if side == "CALL":
            intrinsic = max(0, current_price - strike)
        else:
            intrinsic = max(0, strike - current_price)

        # Estimate time value (very simplified)
        time_value = current_price * 0.02 * (dte / 30) * 0.3

        # Add some randomness for OTM options
        if intrinsic == 0:
            # OTM option - mainly time value
            otm_distance = abs(strike - current_price) / current_price
            time_value *= (1 - otm_distance)

        premium = intrinsic + time_value

        return max(premium, 0.01)  # Minimum 0.01

    def _calculate_position_metrics(
        self,
        position: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate metrics for current position.

        Args:
            position: Position dict
            market_data: Market data

        Returns:
            Metrics dict
        """
        current_price = market_data.get("current_price", 0)
        strike = float(position.get("strike", 0))
        side = position.get("side", "CALL")

        # Calculate DTE
        dte = self._calculate_dte(position.get("expiration"))

        # Calculate OTM percentage
        otm_pct = abs(strike - current_price) / current_price * 100

        # Determine if ITM or OTM
        if side == "CALL":
            is_itm = current_price > strike
        else:
            is_itm = current_price < strike

        # Calculate P&L
        avg_premium = float(position.get("avg_premium", 0))
        quantity = int(position.get("quantity", 0))

        # Current value (estimated)
        current_premium = self._estimate_premium(
            current_price,
            strike,
            dte,
            side
        )

        # P&L = (premium received - current value) * quantity * 100
        pnl = (avg_premium - current_premium) * quantity * 100

        return {
            "dte": dte,
            "otm_pct": round(otm_pct, 2),
            "is_itm": is_itm,
            "current_premium": round(current_premium, 2),
            "pnl": round(pnl, 2),
            "current_price": current_price
        }

    def _calculate_dte(self, expiration) -> int:
        """Calculate days to expiration."""
        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration).date()
        elif isinstance(expiration, datetime):
            expiration = expiration.date()

        today = date.today()
        return (expiration - today).days

    def _get_mock_market_data(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get mock market data for testing.

        Args:
            position: Position dict

        Returns:
            Mock market data
        """
        strike = float(position.get("strike", 100))

        # Mock current price near strike
        current_price = strike * 0.98  # Slightly below strike for CALL

        return {
            "ticker": position.get("ticker", "MOCK"),
            "current_price": round(current_price, 2),
            "bid": round(current_price * 0.999, 2),
            "ask": round(current_price * 1.001, 2),
            "volume": 1500000,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _get_default_rule(self) -> Dict[str, Any]:
        """Get default rule configuration."""
        return {
            "delta_threshold": 0.60,
            "dte_min": 21,
            "dte_max": 45,
            "target_otm_pct_low": 0.03,
            "target_otm_pct_high": 0.08,
            "min_volume": 1000,
            "max_spread": 0.05,
            "min_oi": 5000
        }


# Singleton instance
roll_calculator = RollCalculator()
