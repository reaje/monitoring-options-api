"""Roll rules repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger
from app.config import settings as app_settings
# Ensure legacy name 'settings' stays available (avoid NameError in runtime contexts)
settings = app_settings

import asyncpg  # type: ignore
import json


class RulesRepository(BaseRepository):
    """Repository for roll_rules table."""

    table_name = "roll_rules"


    # Direct asyncpg connection (hybrid RLS via _current_user_id())

    @staticmethod
    async def _get_conn(auth_user_id: Optional[str] = None):
        # Defensive: log minimal connection settings for diagnostics
        try:
            logger.bind(component="RulesRepository").info(
                "_get_conn",
                schema=getattr(settings, "DB_SCHEMA", None),
                has_settings=hasattr(settings, "DB_SCHEMA"),
                has_host=bool(getattr(settings, "DB_HOST", None)),
            )
        except Exception:
            pass
        server_settings = {"search_path": settings.DB_SCHEMA}
        if auth_user_id:
            server_settings.update({
                "request.jwt.claim.sub": str(auth_user_id),
                "request.jwt.claim.role": "authenticated",
            })
        return await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            server_settings=server_settings,
        )


    @classmethod
    async def get_by_id(
        cls,
        id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                SELECT id, account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                       price_to_strike_ratio, min_volume, max_spread, min_oi,
                       target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active, created_at
                FROM {settings.DB_SCHEMA}.roll_rules
                WHERE id = $1
                """,
                str(id),
            )
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "account_id": str(row["account_id"]),
                "delta_threshold": float(row["delta_threshold"]) if row["delta_threshold"] is not None else None,
                "dte_min": row["dte_min"],
                "dte_max": row["dte_max"],
                "spread_threshold": float(row["spread_threshold"]) if row["spread_threshold"] is not None else None,
                "price_to_strike_ratio": float(row["price_to_strike_ratio"]) if row["price_to_strike_ratio"] is not None else None,
                "min_volume": row["min_volume"],
                "max_spread": float(row["max_spread"]) if row["max_spread"] is not None else None,
                "min_oi": row["min_oi"],
                "target_otm_pct_low": float(row["target_otm_pct_low"]) if row["target_otm_pct_low"] is not None else None,
                "target_otm_pct_high": float(row["target_otm_pct_high"]) if row["target_otm_pct_high"] is not None else None,
                "premium_close_threshold": float(row["premium_close_threshold"]) if row["premium_close_threshold"] is not None else None,
                "notify_channels": row["notify_channels"],
                "is_active": row["is_active"],
                "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
            }
        finally:
            await conn.close()

    @classmethod
    async def get_by_account_id(
        cls,
        account_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"""
                SELECT id, account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                       price_to_strike_ratio, min_volume, max_spread, min_oi,
                       target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active, created_at
                FROM {settings.DB_SCHEMA}.roll_rules
                WHERE account_id = $1
                ORDER BY created_at DESC
                """,
                str(account_id),
            )
            result: List[Dict[str, Any]] = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "account_id": str(row["account_id"]),
                    "delta_threshold": float(row["delta_threshold"]) if row["delta_threshold"] is not None else None,
                    "dte_min": row["dte_min"],
                    "dte_max": row["dte_max"],
                    "spread_threshold": float(row["spread_threshold"]) if row["spread_threshold"] is not None else None,
                    "price_to_strike_ratio": float(row["price_to_strike_ratio"]) if row["price_to_strike_ratio"] is not None else None,
                    "min_volume": row["min_volume"],
                    "max_spread": float(row["max_spread"]) if row["max_spread"] is not None else None,
                    "min_oi": row["min_oi"],
                    "target_otm_pct_low": float(row["target_otm_pct_low"]) if row["target_otm_pct_low"] is not None else None,
                    "target_otm_pct_high": float(row["target_otm_pct_high"]) if row["target_otm_pct_high"] is not None else None,
                    "premium_close_threshold": float(row["premium_close_threshold"]) if row["premium_close_threshold"] is not None else None,
                    "notify_channels": row["notify_channels"],
                    "is_active": row["is_active"],
                    "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
                })
            return result
        finally:
            await conn.close()

    @classmethod
    async def get_active_rules(
        cls,
        account_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"""
                SELECT id, account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                       price_to_strike_ratio, min_volume, max_spread, min_oi,
                       target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active, created_at
                FROM {settings.DB_SCHEMA}.roll_rules
                WHERE account_id = $1 AND is_active = TRUE
                ORDER BY created_at DESC
                """,
                str(account_id),
            )
            result: List[Dict[str, Any]] = []
            for row in rows:
                result.append({
                    "id": str(row["id"]),
                    "account_id": str(row["account_id"]),
                    "delta_threshold": float(row["delta_threshold"]) if row["delta_threshold"] is not None else None,
                    "dte_min": row["dte_min"],
                    "dte_max": row["dte_max"],
                    "spread_threshold": float(row["spread_threshold"]) if row["spread_threshold"] is not None else None,
                    "price_to_strike_ratio": float(row["price_to_strike_ratio"]) if row["price_to_strike_ratio"] is not None else None,
                    "min_volume": row["min_volume"],
                    "max_spread": float(row["max_spread"]) if row["max_spread"] is not None else None,
                    "min_oi": row["min_oi"],
                    "target_otm_pct_low": float(row["target_otm_pct_low"]) if row["target_otm_pct_low"] is not None else None,
                    "target_otm_pct_high": float(row["target_otm_pct_high"]) if row["target_otm_pct_high"] is not None else None,
                    "premium_close_threshold": float(row["premium_close_threshold"]) if row["premium_close_threshold"] is not None else None,
                    "notify_channels": row["notify_channels"],
                    "is_active": row["is_active"],
                    "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
                })
            return result
        finally:
            await conn.close()


    @classmethod
    async def create(
        cls,
        data: Dict[str, Any],
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            # Ensure notify_channels is JSON text for JSONB parameter
            _channels = data.get("notify_channels")
            channels_json = None
            if _channels is not None:
                if isinstance(_channels, (list, dict)):
                    channels_json = json.dumps(_channels)
                else:
                    channels_json = _channels

            row = await conn.fetchrow(
                f"""
                INSERT INTO {settings.DB_SCHEMA}.roll_rules (
                    account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                    price_to_strike_ratio, min_volume, max_spread, min_oi,
                    target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active
                )
                VALUES (
                    $1,$2,$3,$4,$5,
                    $6,$7,$8,$9,
                    $10,$11,$12, COALESCE($13::jsonb, '[]'::jsonb), COALESCE($14, TRUE)
                )
                RETURNING id, account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                          price_to_strike_ratio, min_volume, max_spread, min_oi,
                          target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active, created_at
                """,
                str(data.get("account_id")),
                data.get("delta_threshold"),
                data.get("dte_min"),
                data.get("dte_max"),
                data.get("spread_threshold"),
                data.get("price_to_strike_ratio"),
                data.get("min_volume"),
                data.get("max_spread"),
                data.get("min_oi"),
                data.get("target_otm_pct_low"),
                data.get("target_otm_pct_high"),
                data.get("premium_close_threshold"),
                channels_json,
                data.get("is_active"),
            )
            return {
                "id": str(row["id"]),
                "account_id": str(row["account_id"]),
                "delta_threshold": float(row["delta_threshold"]) if row["delta_threshold"] is not None else None,
                "dte_min": row["dte_min"],
                "dte_max": row["dte_max"],
                "spread_threshold": float(row["spread_threshold"]) if row["spread_threshold"] is not None else None,
                "price_to_strike_ratio": float(row["price_to_strike_ratio"]) if row["price_to_strike_ratio"] is not None else None,
                "min_volume": row["min_volume"],
                "max_spread": float(row["max_spread"]) if row["max_spread"] is not None else None,
                "min_oi": row["min_oi"],
                "target_otm_pct_low": float(row["target_otm_pct_low"]) if row["target_otm_pct_low"] is not None else None,
                "target_otm_pct_high": float(row["target_otm_pct_high"]) if row["target_otm_pct_high"] is not None else None,
                "premium_close_threshold": float(row["premium_close_threshold"]) if row["premium_close_threshold"] is not None else None,
                "notify_channels": row["notify_channels"],
                "is_active": row["is_active"],
                "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
            }
        finally:
            await conn.close()

    @classmethod
    async def update(
        cls,
        id: UUID,
        data: Dict[str, Any],
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        if not data:
            existing = await cls.get_by_id(id, auth_user_id=auth_user_id)
            if not existing:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return existing
        field_names: List[str] = []
        values: List[Any] = []
        jsonb_keys = {"notify_channels"}
        for key in [
            "delta_threshold", "dte_min", "dte_max", "spread_threshold",
            "price_to_strike_ratio", "min_volume", "max_spread", "min_oi",
            "target_otm_pct_low", "target_otm_pct_high", "premium_close_threshold", "notify_channels", "is_active"
        ]:
            if key in data:
                field_names.append(key)
                if key == "notify_channels":
                    _v = data[key]
                    values.append(json.dumps(_v) if _v is not None and not isinstance(_v, str) else _v)
                else:
                    values.append(data[key])
        if not field_names:
            existing = await cls.get_by_id(id, auth_user_id=auth_user_id)
            if not existing:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return existing
        assignments = [
            f"{fname} = ${i+2}{'::jsonb' if fname in jsonb_keys else ''}"
            for i, fname in enumerate(field_names)
        ]
        set_clause = ", ".join(assignments)
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                UPDATE {settings.DB_SCHEMA}.roll_rules
                SET {set_clause}
                WHERE id = $1
                RETURNING id, account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                          price_to_strike_ratio, min_volume, max_spread, min_oi,
                          target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active, created_at
                """,
                str(id), *values,
            )
            if not row:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return {
                "id": str(row["id"]),
                "account_id": str(row["account_id"]),
                "delta_threshold": float(row["delta_threshold"]) if row["delta_threshold"] is not None else None,
                "dte_min": row["dte_min"],
                "dte_max": row["dte_max"],
                "spread_threshold": float(row["spread_threshold"]) if row["spread_threshold"] is not None else None,
                "price_to_strike_ratio": float(row["price_to_strike_ratio"]) if row["price_to_strike_ratio"] is not None else None,
                "min_volume": row["min_volume"],
                "max_spread": float(row["max_spread"]) if row["max_spread"] is not None else None,
                "min_oi": row["min_oi"],
                "target_otm_pct_low": float(row["target_otm_pct_low"]) if row["target_otm_pct_low"] is not None else None,
                "target_otm_pct_high": float(row["target_otm_pct_high"]) if row["target_otm_pct_high"] is not None else None,
                "premium_close_threshold": float(row["premium_close_threshold"]) if row["premium_close_threshold"] is not None else None,
                "notify_channels": row["notify_channels"],
                "is_active": row["is_active"],
                "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
            }
        finally:
            await conn.close()

    @classmethod
    async def delete(
        cls,
        id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> bool:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            res = await conn.execute(
                f"DELETE FROM {settings.DB_SCHEMA}.roll_rules WHERE id = $1",
                str(id),
            )
            return res.endswith(" 1")
        finally:
            await conn.close()

    @classmethod
    async def toggle_active(
        cls,
        rule_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        # We assume caller already checked ownership; still rely on RLS for safety
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                UPDATE {settings.DB_SCHEMA}.roll_rules
                SET is_active = NOT COALESCE(is_active, TRUE)
                WHERE id = $1
                RETURNING id, account_id, delta_threshold, dte_min, dte_max, spread_threshold,
                          price_to_strike_ratio, min_volume, max_spread, min_oi,
                          target_otm_pct_low, target_otm_pct_high, premium_close_threshold, notify_channels, is_active, created_at
                """,
                str(rule_id),
            )
            return None if not row else {
                "id": str(row["id"]),
                "account_id": str(row["account_id"]),
                "delta_threshold": float(row["delta_threshold"]) if row["delta_threshold"] is not None else None,
                "dte_min": row["dte_min"],
                "dte_max": row["dte_max"],
                "spread_threshold": float(row["spread_threshold"]) if row["spread_threshold"] is not None else None,
                "price_to_strike_ratio": float(row["price_to_strike_ratio"]) if row["price_to_strike_ratio"] is not None else None,
                "min_volume": row["min_volume"],
                "max_spread": float(row["max_spread"]) if row["max_spread"] is not None else None,
                "min_oi": row["min_oi"],
                "target_otm_pct_low": float(row["target_otm_pct_low"]) if row["target_otm_pct_low"] is not None else None,
                "target_otm_pct_high": float(row["target_otm_pct_high"]) if row["target_otm_pct_high"] is not None else None,
                "premium_close_threshold": float(row["premium_close_threshold"]) if row["premium_close_threshold"] is not None else None,
                "notify_channels": row["notify_channels"],
                "is_active": row["is_active"],
                "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
            }
        finally:
            await conn.close()


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
        rule = await cls.get_by_id(rule_id, auth_user_id=user_id)

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
        rule = await cls.get_by_id(rule_id, auth_user_id=user_id)

        if not rule:
            return False

        account_id = UUID(rule.get("account_id"))
        return await AccountsRepository.user_owns_account(account_id, user_id)


    @classmethod
    async def evaluate_rule_for_position(
        cls,
        rule: Dict[str, Any],
        position: Dict[str, Any],
        current_delta: Optional[float] = None,
        current_price: Optional[float] = None,
        current_premium: Optional[float] = None,
    ) -> bool:
        """
        Evaluate if a rule is triggered for a specific position.

        Args:
            rule: Rule configuration
            position: Option position data
            current_delta: Current delta value (if available)
            current_price: Current underlying price (if available)
            current_premium: Current option premium (if available)

        Returns:
            True if rule is triggered
        """
        from datetime import datetime, date

        # Check if rule is active
        if not rule.get("is_active", True):
            return False

        # Premium threshold override: trigger regardless of DTE if premium <= threshold
        premium_threshold = rule.get("premium_close_threshold")
        if premium_threshold is not None and current_premium is not None:
            try:
                if float(current_premium) <= float(premium_threshold):
                    logger.info(
                        "Rule triggered by premium threshold",
                        rule_id=rule.get("id"),
                        position_id=position.get("id"),
                        current_premium=current_premium,
                        threshold=premium_threshold,
                    )
                    return True
            except Exception:
                pass

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
        current_price: Optional[float] = None,
        current_premium: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all active rules that are triggered for a position.

        Args:
            account_id: Account UUID
            position: Option position data
            current_delta: Current delta value
            current_price: Current underlying price
            current_premium: Current option premium

        Returns:
            List of triggered rules
        """
        active_rules = await cls.get_active_rules(account_id)
        triggered = []

        for rule in active_rules:
            if await cls.evaluate_rule_for_position(
                rule, position, current_delta, current_price, current_premium
            ):
                triggered.append(rule)

        return triggered
