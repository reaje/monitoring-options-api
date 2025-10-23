"""Roll rules repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


class RulesRepository(BaseRepository):
    """Repository for roll_rules table."""

    table_name = "roll_rules"

    @classmethod
    async def get_by_account_id(cls, account_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all roll rules for an account.

        Args:
            account_id: Account UUID

        Returns:
            List of roll rules
        """
        return await cls.get_all(
            filters={"account_id": str(account_id)},
            order_by="created_at",
            order_desc=True
        )

    @classmethod
    async def get_active_rules(cls, account_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all active rules for an account.

        Args:
            account_id: Account UUID

        Returns:
            List of active roll rules
        """
        return await cls.get_all(
            filters={
                "account_id": str(account_id),
                "is_active": True
            },
            order_by="created_at",
            order_desc=True
        )

    @classmethod
    async def get_user_rule(
        cls,
        rule_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a rule if it belongs to a user's account.

        Args:
            rule_id: Rule UUID
            user_id: User UUID

        Returns:
            Rule dict or None if not found or doesn't belong to user
        """
        rule = await cls.get_by_id(rule_id)

        if not rule:
            return None

        # Check if user owns the account
        account_id = rule.get("account_id")
        if not await AccountsRepository.user_owns_account(UUID(account_id), user_id):
            logger.warning(
                "User attempted to access rule they don't own",
                user_id=str(user_id),
                rule_id=str(rule_id),
            )
            return None

        return rule

    @classmethod
    async def user_owns_rule(cls, rule_id: UUID, user_id: UUID) -> bool:
        """
        Check if a user owns a rule (through account ownership).

        Args:
            rule_id: Rule UUID
            user_id: User UUID

        Returns:
            True if user owns rule
        """
        rule = await cls.get_by_id(rule_id)

        if not rule:
            return False

        account_id = UUID(rule.get("account_id"))
        return await AccountsRepository.user_owns_account(account_id, user_id)

    @classmethod
    async def toggle_active(cls, rule_id: UUID) -> Dict[str, Any]:
        """
        Toggle the is_active status of a rule.

        Args:
            rule_id: Rule UUID

        Returns:
            Updated rule
        """
        rule = await cls.get_by_id(rule_id)
        if not rule:
            return None

        new_status = not rule.get("is_active", True)
        return await cls.update(rule_id, {"is_active": new_status})

    @classmethod
    async def evaluate_rule_for_position(
        cls,
        rule: Dict[str, Any],
        position: Dict[str, Any],
        current_delta: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> bool:
        """
        Evaluate if a rule is triggered for a specific position.

        Args:
            rule: Rule configuration
            position: Option position data
            current_delta: Current delta value (if available)
            current_price: Current underlying price (if available)

        Returns:
            True if rule is triggered
        """
        from datetime import datetime, date

        # Check if rule is active
        if not rule.get("is_active", True):
            return False

        # Calculate days to expiration (DTE)
        expiration = position.get("expiration")
        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration).date()
        elif isinstance(expiration, datetime):
            expiration = expiration.date()

        today = date.today()
        dte = (expiration - today).days

        # Check DTE threshold
        dte_min = rule.get("dte_min")
        dte_max = rule.get("dte_max")

        if dte_min is not None and dte < dte_min:
            logger.debug(
                "Rule DTE min not met",
                rule_id=rule["id"],
                dte=dte,
                dte_min=dte_min
            )
            return False

        if dte_max is not None and dte > dte_max:
            logger.debug(
                "Rule DTE max exceeded",
                rule_id=rule["id"],
                dte=dte,
                dte_max=dte_max
            )
            return False

        # Check delta threshold (if available)
        delta_threshold = rule.get("delta_threshold")
        if delta_threshold is not None and current_delta is not None:
            if abs(current_delta) < delta_threshold:
                logger.debug(
                    "Rule delta threshold not met",
                    rule_id=rule["id"],
                    current_delta=current_delta,
                    threshold=delta_threshold
                )
                return False

        # Check spread threshold (if available)
        spread_threshold = rule.get("spread_threshold")
        if spread_threshold is not None and current_price is not None:
            strike = float(position.get("strike", 0))
            if strike > 0:
                spread_percent = abs(current_price - strike) / strike * 100
                if spread_percent < spread_threshold:
                    logger.debug(
                        "Rule spread threshold not met",
                        rule_id=rule["id"],
                        spread_percent=spread_percent,
                        threshold=spread_threshold
                    )
                    return False

        # All conditions met
        logger.info(
            "Rule triggered for position",
            rule_id=rule["id"],
            position_id=position["id"],
            dte=dte
        )
        return True

    @classmethod
    async def get_triggered_rules(
        cls,
        account_id: UUID,
        position: Dict[str, Any],
        current_delta: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all active rules that are triggered for a position.

        Args:
            account_id: Account UUID
            position: Option position data
            current_delta: Current delta value
            current_price: Current underlying price

        Returns:
            List of triggered rules
        """
        active_rules = await cls.get_active_rules(account_id)
        triggered = []

        for rule in active_rules:
            if await cls.evaluate_rule_for_position(
                rule, position, current_delta, current_price
            ):
                triggered.append(rule)

        return triggered
