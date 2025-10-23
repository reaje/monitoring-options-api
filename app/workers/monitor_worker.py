"""Monitor worker for checking option positions and triggering alerts."""

from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from app.database.repositories.options import OptionsRepository
from app.database.repositories.rules import RulesRepository
from app.database.repositories.alerts import AlertQueueRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


class MonitorWorker:
    """Worker for monitoring option positions and creating alerts."""

    def __init__(self):
        """Initialize monitor worker."""
        self.check_count = 0

    async def run(self) -> Dict[str, Any]:
        """
        Run monitoring check for all open positions.

        Returns:
            Statistics dict with monitoring results
        """
        self.check_count += 1

        logger.info(
            "Starting monitor worker run",
            check_number=self.check_count,
            timestamp=datetime.utcnow().isoformat()
        )

        try:
            # Get all accounts
            accounts = await self._get_all_accounts()

            total_positions_checked = 0
            total_alerts_created = 0
            accounts_processed = 0

            for account in accounts:
                account_id = UUID(account["id"])

                # Get active rules for account
                active_rules = await RulesRepository.get_active_rules(account_id)

                if not active_rules:
                    logger.debug(
                        "No active rules for account",
                        account_id=str(account_id)
                    )
                    continue

                # Get open positions for account
                open_positions = await OptionsRepository.get_open_positions(account_id)

                if not open_positions:
                    logger.debug(
                        "No open positions for account",
                        account_id=str(account_id)
                    )
                    continue

                # Check each position against rules
                for position in open_positions:
                    total_positions_checked += 1

                    # Check expiration warning
                    expiration_alert = await self._check_expiration_warning(
                        position,
                        account_id
                    )
                    if expiration_alert:
                        total_alerts_created += 1

                    # Check rules
                    for rule in active_rules:
                        triggered = await self._check_position_against_rule(
                            position,
                            rule,
                            account_id
                        )
                        if triggered:
                            total_alerts_created += 1

                accounts_processed += 1

            logger.info(
                "Monitor worker completed",
                check_number=self.check_count,
                accounts_processed=accounts_processed,
                positions_checked=total_positions_checked,
                alerts_created=total_alerts_created
            )

            return {
                "check_number": self.check_count,
                "timestamp": datetime.utcnow().isoformat(),
                "accounts_processed": accounts_processed,
                "positions_checked": total_positions_checked,
                "alerts_created": total_alerts_created
            }

        except Exception as e:
            logger.error(
                "Monitor worker failed",
                check_number=self.check_count,
                error=str(e)
            )
            return {
                "check_number": self.check_count,
                "error": str(e),
                "status": "failed"
            }

    async def _get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all accounts that have positions to monitor.

        Returns:
            List of account dicts
        """
        # This is a simplified version - in production you might want to
        # query only accounts with open positions
        from app.database.supabase_client import supabase

        result = supabase.table("accounts").select("*").execute()
        return result.data

    async def _check_expiration_warning(
        self,
        position: Dict[str, Any],
        account_id: UUID
    ) -> bool:
        """
        Check if position is close to expiration and create alert.

        Args:
            position: Position dict
            account_id: Account UUID

        Returns:
            True if alert was created
        """
        # Calculate days to expiration
        expiration = position.get("expiration")
        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration).date()
        elif isinstance(expiration, datetime):
            expiration = expiration.date()

        today = date.today()
        dte = (expiration - today).days

        # Create alert if 3 days or less to expiration
        if dte <= 3 and dte >= 0:
            # Check if we already created an alert for this position today
            existing_alerts = await AlertQueueRepository.get_by_account_id(
                account_id,
                status=None  # Get all statuses
            )

            # Check if there's already an expiration warning for this position today
            today_str = today.isoformat()
            for alert in existing_alerts:
                if (alert.get("option_position_id") == position["id"] and
                    alert.get("reason") == "expiration_warning" and
                    alert.get("created_at", "").startswith(today_str)):
                    return False  # Already alerted today

            # Create expiration warning alert
            alert_data = {
                "account_id": str(account_id),
                "option_position_id": position["id"],
                "reason": "expiration_warning",
                "payload": {
                    "ticker": position.get("ticker", "N/A"),
                    "days_to_expiration": dte,
                    "expiration": str(expiration),
                    "strike": float(position.get("strike", 0)),
                    "side": position.get("side")
                },
                "status": "PENDING"
            }

            await AlertQueueRepository.create(alert_data)

            logger.info(
                "Created expiration warning alert",
                position_id=position["id"],
                dte=dte
            )

            return True

        return False

    async def _check_position_against_rule(
        self,
        position: Dict[str, Any],
        rule: Dict[str, Any],
        account_id: UUID
    ) -> bool:
        """
        Check if position triggers a rule and create alert.

        Args:
            position: Position dict
            rule: Rule dict
            account_id: Account UUID

        Returns:
            True if alert was created
        """
        # Use the RulesRepository evaluation method
        # In a real implementation, we'd fetch current delta and price from market data
        current_delta = None  # TODO: Fetch from market data service
        current_price = None  # TODO: Fetch from market data service

        is_triggered = await RulesRepository.evaluate_rule_for_position(
            rule,
            position,
            current_delta,
            current_price
        )

        if is_triggered:
            # Check if we already created an alert for this rule+position today
            today = date.today().isoformat()
            existing_alerts = await AlertQueueRepository.get_by_account_id(
                account_id,
                status=None
            )

            for alert in existing_alerts:
                payload = alert.get("payload", {})
                if (alert.get("option_position_id") == position["id"] and
                    alert.get("reason") == "roll_trigger" and
                    payload.get("rule_id") == rule["id"] and
                    alert.get("created_at", "").startswith(today)):
                    return False  # Already alerted today

            # Create roll trigger alert
            alert_data = {
                "account_id": str(account_id),
                "option_position_id": position["id"],
                "reason": "roll_trigger",
                "payload": {
                    "rule_id": rule["id"],
                    "ticker": position.get("ticker", "N/A"),
                    "strike": float(position.get("strike", 0)),
                    "expiration": str(position.get("expiration")),
                    "side": position.get("side"),
                    "delta": current_delta,
                    "price": current_price,
                    "dte": self._calculate_dte(position.get("expiration"))
                },
                "status": "PENDING"
            }

            await AlertQueueRepository.create(alert_data)

            logger.info(
                "Created roll trigger alert",
                position_id=position["id"],
                rule_id=rule["id"]
            )

            return True

        return False

    def _calculate_dte(self, expiration) -> int:
        """Calculate days to expiration."""
        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration).date()
        elif isinstance(expiration, datetime):
            expiration = expiration.date()

        today = date.today()
        return (expiration - today).days


# Singleton instance
monitor_worker = MonitorWorker()
