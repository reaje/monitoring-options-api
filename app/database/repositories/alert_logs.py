"""Alert logs repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import asyncpg
from app.config import settings
from app.database.repositories.base import BaseRepository
from app.core.logger import logger

JWT_GUC = "request.jwt.claim.sub"


def _serialize_log_row(row: asyncpg.Record) -> Dict[str, Any]:
    if row is None:
        return None
    is_dict = isinstance(row, dict)
    sent = row.get("sent_at") if is_dict else row["sent_at"]

    def get_field(key):
        return row.get(key) if is_dict else row[key] if key in row.keys() else None

    return {
        "id": str(get_field("id")) if get_field("id") else None,
        "queue_id": str(get_field("queue_id")) if get_field("queue_id") else None,
        "channel": get_field("channel"),
        "target": get_field("target"),
        "message": get_field("message"),
        "status": get_field("status"),
        "sent_at": (sent.isoformat() + "Z") if sent else None,
        "provider_msg_id": get_field("provider_msg_id"),
    }




class AlertLogsRepository(BaseRepository):
    """Repository for alert_logs table."""

    table_name = "alert_logs"

    @classmethod
    async def get_by_queue_id(
        cls,
        queue_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all logs for a specific alert.

        Args:
            queue_id: Alert queue UUID

        Returns:
            List of alert logs ordered by sent_at
        """
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"SELECT id, queue_id, channel, target, message, status, sent_at, provider_msg_id FROM {settings.DB_SCHEMA}.alert_logs WHERE queue_id = $1 ORDER BY sent_at DESC",
                str(queue_id),
            )
            return [_serialize_log_row(r) for r in rows]
        finally:
            await conn.close()

    @staticmethod
    async def _get_conn(auth_user_id: Optional[str] = None):
        server_settings = {"search_path": settings.DB_SCHEMA}
        if auth_user_id:
            server_settings.update({
                JWT_GUC: str(auth_user_id),
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
    async def get_by_channel(
        cls,
        channel: str,
        hours: int = 24,
        limit: Optional[int] = 100,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get logs for a specific channel in the last N hours.

        Args:
            channel: Channel name (whatsapp, sms, email)
            hours: Number of hours to look back
            limit: Maximum number of logs to fetch

        Returns:
            List of logs
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            sql = (
                f"SELECT id, queue_id, channel, target, message, status, sent_at, provider_msg_id "
                f"FROM {settings.DB_SCHEMA}.alert_logs "
                f"WHERE channel = $1 AND sent_at >= $2 "
                f"ORDER BY sent_at DESC LIMIT $3"
            )
            rows = await conn.fetch(sql, channel, cutoff_time, limit)
            return [_serialize_log_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_failed_logs(
        cls,
        hours: int = 24,
        limit: Optional[int] = 100,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get failed notification logs.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of logs to fetch

        Returns:
            List of failed logs
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            sql = (
                f"SELECT id, queue_id, channel, target, message, status, sent_at, provider_msg_id "
                f"FROM {settings.DB_SCHEMA}.alert_logs "
                f"WHERE status = 'failed' AND sent_at >= $1 "
                f"ORDER BY sent_at DESC LIMIT $2"
            )
            rows = await conn.fetch(sql, cutoff_time, limit)
            return [_serialize_log_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def create_log(
        cls,
        queue_id: UUID,
        channel: str,
        target: str,
        message: str,
        status: str,
        provider_msg_id: Optional[str] = None,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Create a new alert log entry.

        Args:
            queue_id: Alert queue UUID
            channel: Channel used (whatsapp, sms, email)
            target: Target phone/email
            message: Message content
            status: Status (success, failed)
            provider_msg_id: Optional provider message ID

        Returns:
            Created log entry
        """
        sent_at = datetime.utcnow()
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"INSERT INTO {settings.DB_SCHEMA}.alert_logs (queue_id, channel, target, message, status, sent_at, provider_msg_id) "
                f"VALUES ($1, $2, $3, $4, $5, $6, $7) "
                f"RETURNING id, queue_id, channel, target, message, status, sent_at, provider_msg_id",
                str(queue_id), channel, target, message, status, sent_at, provider_msg_id,
            )
            return _serialize_log_row(row)
        finally:
            await conn.close()

    @classmethod
    async def get_statistics(
        cls,
        hours: int = 24,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get notification statistics.

        Args:
            hours: Number of hours to look back

        Returns:
            Statistics dict
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"SELECT id, queue_id, channel, target, message, status, sent_at, provider_msg_id "
                f"FROM {settings.DB_SCHEMA}.alert_logs WHERE sent_at >= $1",
                cutoff_time,
            )
            logs = [_serialize_log_row(r) for r in rows]
        finally:
            await conn.close()

        total = len(logs)
        success = len([log for log in logs if log["status"] == "success"]) if logs else 0
        failed = len([log for log in logs if log["status"] == "failed"]) if logs else 0

        channels: Dict[str, Dict[str, int]] = {}
        for log in logs:
            channel = log.get("channel", "unknown")
            if channel not in channels:
                channels[channel] = {"total": 0, "success": 0, "failed": 0}
            channels[channel]["total"] += 1
            if log["status"] == "success":
                channels[channel]["success"] += 1
            else:
                channels[channel]["failed"] += 1

        return {
            "period_hours": hours,
            "total_notifications": total,
            "successful": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
            "by_channel": channels,
        }

    @classmethod
    async def get_recent_for_target(
        cls,
        target: str,
        minutes: int = 5,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent logs for a specific target (phone/email).
        Useful for preventing spam.

        Args:
            target: Target phone/email
            minutes: Number of minutes to look back

        Returns:
            List of recent logs for target
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            sql = (
                f"SELECT id, queue_id, channel, target, message, status, sent_at, provider_msg_id "
                f"FROM {settings.DB_SCHEMA}.alert_logs "
                f"WHERE target = $1 AND sent_at >= $2 "
                f"ORDER BY sent_at DESC"
            )
            rows = await conn.fetch(sql, target, cutoff_time)
            return [_serialize_log_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def cleanup_old_logs(
        cls,
        days: int = 90,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> int:
        """
        Delete old successful logs (cleanup).

        Args:
            days: Delete logs older than this many days

        Returns:
            Number of deleted logs
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"DELETE FROM {settings.DB_SCHEMA}.alert_logs "
                f"WHERE status = 'success' AND sent_at < $1 "
                f"RETURNING id",
                cutoff_time,
            )
            deleted_count = len(rows)
        finally:
            await conn.close()

        logger.info(
            "Cleaned up old alert logs",
            extra={"deleted_count": deleted_count, "days": days}
        )

        return deleted_count
