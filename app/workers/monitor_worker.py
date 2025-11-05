"""Monitor worker for checking option positions and triggering alerts."""

from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from zoneinfo import ZoneInfo

import asyncio
from app.database.repositories.options import OptionsRepository
from app.database.repositories.rules import RulesRepository
from app.database.repositories.alerts import AlertQueueRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.assets import AssetsRepository
from app.services.market_data import market_data_provider
from app.core.logger import logger

from app.config import settings

# Checagem de pregão da B3 via configuração (.env)
# Usa time zone e janela configuráveis em app.config.Settings
def _is_b3_market_open():
    tz = settings.MARKET_SESSION_TZ or "America/Sao_Paulo"
    sp_now = datetime.now(ZoneInfo(tz))
    if sp_now.weekday() >= 5:  # 0=Seg, 6=Dom
        return False, sp_now
    open_hhmm = (int(settings.MARKET_OPEN_HOUR), int(settings.MARKET_OPEN_MINUTE))
    close_hhmm = (int(settings.MARKET_CLOSE_HOUR), int(settings.MARKET_CLOSE_MINUTE))
    hhmm = (sp_now.hour, sp_now.minute)
    if hhmm < open_hhmm or hhmm >= close_hhmm:
        return False, sp_now
    return True, sp_now



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


        # Pular execuções fora do horário de pregão da B3
        open_now, sp_now = _is_b3_market_open()
        if not open_now:
            logger.debug(
                "Monitor worker ignorado: mercado fechado (B3 10:00–18:00 America/Sao_Paulo)",
                sp_time=sp_now.isoformat(),
            )
            return {
                "check_number": self.check_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "skipped",
                "reason": "market_closed",
                "sp_time": sp_now.isoformat(),
            }

        try:
            # Get all accounts
            accounts = await self._get_all_accounts()

            total_positions_checked = 0
            total_alerts_created = 0
            accounts_processed = 0

            for account in accounts:
                account_id = UUID(account["id"])
                user_id = UUID(account.get("user_id")) if account.get("user_id") else None


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
                        account_id,
                        user_id
                    )
                    if expiration_alert:
                        total_alerts_created += 1

                    # Check rules
                    for rule in active_rules:
                        triggered = await self._check_position_against_rule(
                            position,
                            rule,
                            account_id,
                            user_id
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
        # Use direct DB repository to avoid SDK/version mismatches in workers
        for attempt in range(3):
            try:
                accounts = await AccountsRepository.get_all()
                return accounts
            except Exception as e:
                logger.error(
                    "Failed to fetch accounts via repository",
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))
                else:
                    return []

    async def _check_expiration_warning(
        self,
        position: Dict[str, Any],
        account_id: UUID,
        user_id: UUID
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
                status=None,  # Get all statuses
                auth_user_id=user_id
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

            await AlertQueueRepository.create(alert_data, auth_user_id=user_id)

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
        account_id: UUID,
        user_id: UUID
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
        # Fetch required market data
        current_delta = None  # Could be added from provider greeks in the future
        current_price = None
        current_premium = None

        # Derive underlying ticker from asset_id
        asset_id = position.get("asset_id")
        ticker = position.get("ticker")  # fallback if present
        try:
            if asset_id and not ticker:
                from uuid import UUID as _UUID
                asset = await AssetsRepository.get_by_id(_UUID(str(asset_id)))
                if asset:
                    ticker = asset.get("ticker")
        except Exception:
            pass

        try:
            if ticker:
                quote = await market_data_provider.get_quote(ticker)
                current_price = quote.get("current_price") if isinstance(quote, dict) else None
        except Exception as e:
            logger.warning("Failed to fetch underlying quote", ticker=ticker, error=str(e))

        try:
            if ticker and position.get("strike") and position.get("expiration") and position.get("side"):
                opt = await market_data_provider.get_option_quote(
                    ticker=str(ticker),
                    strike=float(position["strike"]),
                    expiration=str(position["expiration"]),
                    option_type=str(position["side"]).upper(),
                )
                # Prefer mid of bid/ask, fallback to premium/last
                bid = opt.get("bid") if isinstance(opt, dict) else None
                ask = opt.get("ask") if isinstance(opt, dict) else None
                if bid is not None and ask is not None and ask >= bid:
                    current_premium = round((float(bid) + float(ask)) / 2.0, 4)
                else:
                    current_premium = opt.get("premium") or opt.get("last")
                    if current_premium is not None:
                        current_premium = float(current_premium)
        except Exception as e:
            logger.warning("Failed to fetch option quote", ticker=ticker, error=str(e))

        is_triggered = await RulesRepository.evaluate_rule_for_position(
            rule,
            position,
            current_delta,
            current_price,
            current_premium,
        )

        if is_triggered:
            # Check if we already created an alert for this rule+position today
            today = date.today().isoformat()
            existing_alerts = await AlertQueueRepository.get_by_account_id(
                account_id,
                status=None,
                auth_user_id=user_id
            )

            for alert in existing_alerts:
                # Ensure alert is a dict (may be raw JSON string)
                if not isinstance(alert, dict):
                    try:
                        import json as _json
                        alert = _json.loads(alert)
                    except Exception:
                        continue
                payload = alert.get("payload", {})
                if isinstance(payload, str):
                    try:
                        import json as _json
                        payload = _json.loads(payload)
                    except Exception:
                        payload = {}
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
                    "ticker": ticker or position.get("ticker", "N/A"),
                    "strike": float(position.get("strike", 0)),
                    "expiration": str(position.get("expiration")),
                    "side": position.get("side"),
                    "delta": current_delta,
                    "price": current_price,
                    "premium": current_premium,
                    "dte": self._calculate_dte(position.get("expiration"))
                },
                "status": "PENDING"
            }

            await AlertQueueRepository.create(alert_data, auth_user_id=user_id)

            logger.info(
                "Created roll trigger alert",
                position_id=position["id"],
                rule_id=rule["id"],
                premium=current_premium,
                price=current_price,
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
