"""Alert logs repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.database.repositories.base import BaseRepository
from app.database.supabase_client import supabase
from app.core.logger import logger


class AlertLogsRepository(BaseRepository):
    """Repository for alert_logs table."""

    table_name = "alert_logs"

    @classmethod
    async def get_by_queue_id(cls, queue_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all logs for a specific alert.

        Args:
            queue_id: Alert queue UUID

        Returns:
            List of alert logs ordered by sent_at
        """
        return await cls.get_all(
            filters={"queue_id": str(queue_id)},
            order_by="sent_at",
            order_desc=True
        )

    @classmethod
    async def get_by_channel(
        cls,
        channel: str,
        hours: int = 24,
        limit: Optional[int] = 100
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

        result = supabase.table(cls.table_name) \
            .select("*") \
            .eq("channel", channel) \
            .gte("sent_at", cutoff_time.isoformat()) \
            .order("sent_at", desc=True) \
            .limit(limit) \
            .execute()

        return result.data

    @classmethod
    async def get_failed_logs(
        cls,
        hours: int = 24,
        limit: Optional[int] = 100
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

        result = supabase.table(cls.table_name) \
            .select("*") \
            .eq("status", "failed") \
            .gte("sent_at", cutoff_time.isoformat()) \
            .order("sent_at", desc=True) \
            .limit(limit) \
            .execute()

        return result.data

    @classmethod
    async def create_log(
        cls,
        queue_id: UUID,
        channel: str,
        target: str,
        message: str,
        status: str,
        provider_msg_id: Optional[str] = None
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
        log_data = {
            "queue_id": str(queue_id),
            "channel": channel,
            "target": target,
            "message": message,
            "status": status,
            "sent_at": datetime.utcnow().isoformat(),
        }

        if provider_msg_id:
            log_data["provider_msg_id"] = provider_msg_id

        return await cls.create(log_data)

    @classmethod
    async def get_statistics(
        cls,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get notification statistics.

        Args:
            hours: Number of hours to look back

        Returns:
            Statistics dict
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get all logs in time window
        result = supabase.table(cls.table_name) \
            .select("*") \
            .gte("sent_at", cutoff_time.isoformat()) \
            .execute()

        logs = result.data

        total = len(logs)
        success = len([log for log in logs if log["status"] == "success"])
        failed = len([log for log in logs if log["status"] == "failed"])

        # Group by channel
        channels = {}
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
        minutes: int = 5
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

        result = supabase.table(cls.table_name) \
            .select("*") \
            .eq("target", target) \
            .gte("sent_at", cutoff_time.isoformat()) \
            .order("sent_at", desc=True) \
            .execute()

        return result.data

    @classmethod
    async def cleanup_old_logs(cls, days: int = 90) -> int:
        """
        Delete old successful logs (cleanup).

        Args:
            days: Delete logs older than this many days

        Returns:
            Number of deleted logs
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        result = supabase.table(cls.table_name) \
            .delete() \
            .eq("status", "success") \
            .lt("sent_at", cutoff_time.isoformat()) \
            .execute()

        deleted_count = len(result.data) if result.data else 0

        logger.info(
            "Cleaned up old alert logs",
            deleted_count=deleted_count,
            days=days
        )

        return deleted_count
