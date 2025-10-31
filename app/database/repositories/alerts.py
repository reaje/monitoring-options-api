"""Alerts queue repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone as _tz
import asyncpg
from app.config import settings
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.supabase_client import supabase
from app.core.logger import logger
from app.core.exceptions import NotFoundError, DatabaseError


JWT_GUC = "request.jwt.claim.sub"


def _serialize_alert_row(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert asyncpg row to JSON-serializable dict for AlertQueue."""
    if row is None:
        return None
    is_dict = isinstance(row, dict)
    created = row.get("created_at") if is_dict else row["created_at"]

    def get_field(key):
        return row.get(key) if is_dict else row[key] if key in row.keys() else None

    def _fmt_created(dt: datetime) -> Optional[str]:
        if not dt:
            return None
        try:
            # Ensure RFC3339 with trailing 'Z' and no '+00:00Z'
            if getattr(dt, "tzinfo", None) is None or dt.tzinfo.utcoffset(dt) is None:
                # Treat naive as UTC
                return dt.replace(tzinfo=_tz.utc).isoformat().replace("+00:00", "Z")
            return dt.astimezone(_tz.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            try:
                return dt.isoformat()
            except Exception:
                return None

    return {
        "id": str(get_field("id")),
        "account_id": str(get_field("account_id")) if get_field("account_id") else None,
        "option_position_id": str(get_field("option_position_id")) if get_field("option_position_id") else None,
        "reason": get_field("reason"),
        "payload": get_field("payload") or {},
        "status": get_field("status"),
        "created_at": _fmt_created(created),
    }


class AlertQueueRepository(BaseRepository):
    """Repository for alert_queue table."""

    table_name = "alert_queue"

    @staticmethod
    async def _get_conn(auth_user_id: Optional[str] = None):
        server_settings = {"search_path": settings.DB_SCHEMA}
        if auth_user_id:
            server_settings.update({
                JWT_GUC: str(auth_user_id),
                "request.jwt.claim.role": "authenticated",
            })
        # Use full DATABASE_URL to avoid DNS issues seen with separate host/port on some environments
        return await asyncpg.connect(settings.DATABASE_URL, server_settings=server_settings)

    @classmethod
    async def get_by_account_id(
        cls,
        account_id: UUID,
        status: Optional[str] = None,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all alerts for an account.

        Args:
            account_id: Account UUID
            status: Optional status filter (PENDING, PROCESSING, SENT, FAILED)

        Returns:
            List of alerts
        """
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            sql = f"SELECT id, account_id, option_position_id, reason, payload, status, created_at FROM {settings.DB_SCHEMA}.alert_queue WHERE account_id = $1"
            params = [str(account_id)]
            if status:
                sql += " AND status = $2"
                params.append(status)
            sql += " ORDER BY created_at DESC"
            rows = await conn.fetch(sql, *params)
            return [_serialize_alert_row(r) for r in rows]
        finally:
            await conn.close()

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
                f"SELECT id, account_id, option_position_id, reason, payload, status, created_at FROM {settings.DB_SCHEMA}.alert_queue WHERE id = $1",
                str(id),
            )
            return _serialize_alert_row(row) if row else None
        finally:
            await conn.close()
    @classmethod
    async def create(
        cls,
        data: Dict[str, Any],
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create a new alert in the queue using direct PG (RLS-aware via GUC)."""
        import json as _json
        account_id = str(data.get("account_id")) if data.get("account_id") else None
        option_position_id = str(data.get("option_position_id")) if data.get("option_position_id") else None
        reason = data.get("reason")
        payload = data.get("payload") or {}
        status = data.get("status") or "PENDING"

        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"INSERT INTO {settings.DB_SCHEMA}.alert_queue (account_id, option_position_id, reason, payload, status) "
                f"VALUES ($1, $2, $3, $4::jsonb, $5) "
                f"RETURNING id, account_id, option_position_id, reason, payload, status, created_at",
                account_id, option_position_id, reason, _json.dumps(payload), status,
            )
            return _serialize_alert_row(row)
        finally:
            await conn.close()

    @classmethod
    async def delete(
        cls,
        id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> bool:
        """Delete an alert by id using direct PG (respects RLS)."""
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"DELETE FROM {settings.DB_SCHEMA}.alert_queue WHERE id = $1 RETURNING id",
                str(id),
            )
            return bool(row)
        finally:
            await conn.close()


    @classmethod
    async def get_pending_alerts(
        cls,
        limit: Optional[int] = 100,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pending alerts for processing.

        Note: If auth_user_id is not provided, this method will attempt to use the
        Supabase service client to fetch globally pending alerts (for workers).
        For user-scoped queries, provide auth_user_id to respect RLS.
        """
        if auth_user_id:
            conn = await cls._get_conn(auth_user_id=str(auth_user_id))
            try:
                rows = await conn.fetch(
                    f"SELECT id, account_id, option_position_id, reason, payload, status, created_at "
                    f"FROM {settings.DB_SCHEMA}.alert_queue "
                    f"WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT $1",
                    limit or 100,
                )
                return [_serialize_alert_row(r) for r in rows]
            finally:
                await conn.close()
        else:
            # Fallback to Supabase service client for worker global visibility
            result = supabase.table(cls.table_name) \
                .select("*") \
                .eq("status", "PENDING") \
                .order("created_at") \
                .limit(limit) \
                .execute()
            return result.data

    @classmethod
    async def get_failed_alerts(
        cls,
        hours: int = 24,
        limit: Optional[int] = 100,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get failed alerts from the last N hours.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"SELECT id, account_id, option_position_id, reason, payload, status, created_at "
                f"FROM {settings.DB_SCHEMA}.alert_queue "
                f"WHERE status = 'FAILED' AND created_at >= $1 "
                f"ORDER BY created_at DESC LIMIT $2",
                cutoff_time, limit or 100,
            )
            return [_serialize_alert_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_user_alert(
        cls,
        alert_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get an alert if it belongs to a user's account.

        Args:
            alert_id: Alert UUID
            user_id: User UUID

        Returns:
            Alert dict or None if not found or doesn't belong to user
        """
        alert = await cls.get_by_id(alert_id, auth_user_id=user_id)

        if not alert:
            return None

        # Check if user owns the account
        account_id = alert.get("account_id")
        if not await AccountsRepository.user_owns_account(UUID(account_id), user_id):
            logger.warning(
                "User attempted to access alert they don't own",
                user_id=str(user_id),
                alert_id=str(alert_id),
            )
            return None

        return alert

    @classmethod
    async def update_status(
        cls,
        alert_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Update alert status.

        If auth_user_id is provided, uses direct PG with RLS; otherwise falls back to
        Supabase client (useful for background workers running with service key).
        """
        if auth_user_id:
            # Fetch existing to merge payload error message if needed
            existing = await cls.get_by_id(alert_id, auth_user_id=auth_user_id)
            if not existing:
                raise NotFoundError(cls.table_name, alert_id)
            payload = existing.get("payload", {}) or {}
            if error_message:
                payload["error"] = error_message

            conn = await cls._get_conn(auth_user_id=str(auth_user_id))
            try:
                import json as _json
                row = await conn.fetchrow(
                    f"UPDATE {settings.DB_SCHEMA}.alert_queue "
                    f"SET status = $2, payload = $3::jsonb "
                    f"WHERE id = $1 "
                    f"RETURNING id, account_id, option_position_id, reason, payload, status, created_at",
                    str(alert_id), status, _json.dumps(payload),
                )
                return _serialize_alert_row(row)
            finally:
                await conn.close()
        else:
            update_data: Dict[str, Any] = {"status": status}
            if error_message:
                # Fetch existing via asyncpg (no auth) just to merge payload; if RLS blocks it,
                # we skip merging and let the update proceed with status only via Supabase.
                try:
                    existing = await cls.get_by_id(alert_id)
                    if existing:
                        payload = existing.get("payload", {}) or {}
                        payload["error"] = error_message
                        update_data["payload"] = payload
                except Exception:
                    pass
            # Fallback to Supabase update
            result = supabase.table(cls.table_name) \
                .update(update_data) \
                .eq("id", str(alert_id)) \
                .execute()
            if not result.data:
                raise DatabaseError("Failed to update alert status")
            return result.data[0]

    @classmethod
    async def mark_as_processing(
        cls,
        alert_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Mark alert as processing."""
        return await cls.update_status(alert_id, "PROCESSING", auth_user_id=auth_user_id)

    @classmethod
    async def mark_as_sent(
        cls,
        alert_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Mark alert as sent."""
        return await cls.update_status(alert_id, "SENT", auth_user_id=auth_user_id)

    @classmethod
    async def mark_as_failed(
        cls,
        alert_id: UUID,
        error_message: str,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Mark alert as failed with error message."""
        return await cls.update_status(alert_id, "FAILED", error_message, auth_user_id=auth_user_id)

    @classmethod
    async def retry_failed_alert(
        cls,
        alert_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Reset a failed alert to pending for retry."""
        return await cls.update_status(alert_id, "PENDING", auth_user_id=auth_user_id)

    @classmethod
    async def get_statistics(
        cls,
        account_id: UUID,
        hours: int = 24,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get alert statistics for an account.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"SELECT id, reason, status FROM {settings.DB_SCHEMA}.alert_queue "
                f"WHERE account_id = $1 AND created_at >= $2",
                str(account_id), cutoff_time,
            )
        finally:
            await conn.close()

        alerts = [dict(r) for r in rows]
        total = len(alerts)
        pending = sum(1 for a in alerts if a.get("status") == "PENDING")
        processing = sum(1 for a in alerts if a.get("status") == "PROCESSING")
        sent = sum(1 for a in alerts if a.get("status") == "SENT")
        failed = sum(1 for a in alerts if a.get("status") == "FAILED")

        reasons: Dict[str, int] = {}
        for a in alerts:
            reason = a.get("reason", "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1

        return {
            "period_hours": hours,
            "total_alerts": total,
            "pending": pending,
            "processing": processing,
            "sent": sent,
            "failed": failed,
            "success_rate": round(sent / total * 100, 2) if total > 0 else 0,
            "reasons": reasons,
        }

    @classmethod
    async def cleanup_old_alerts(
        cls,
        days: int = 30,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> int:
        """Delete old sent alerts (cleanup)."""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"DELETE FROM {settings.DB_SCHEMA}.alert_queue "
                f"WHERE status = 'SENT' AND created_at < $1 "
                f"RETURNING id",
                cutoff_time,
            )
            deleted_count = len(rows)
        finally:
            await conn.close()

        logger.info(
            "Cleaned up old alerts",
            deleted_count=deleted_count,
            days=days,
        )
        return deleted_count
