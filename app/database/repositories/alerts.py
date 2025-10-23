"""Alerts queue repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.supabase_client import supabase
from app.core.logger import logger


class AlertQueueRepository(BaseRepository):
    """Repository for alert_queue table."""

    table_name = "alert_queue"

    @classmethod
    async def get_by_account_id(
        cls,
        account_id: UUID,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all alerts for an account.

        Args:
            account_id: Account UUID
            status: Optional status filter (PENDING, PROCESSING, SENT, FAILED)

        Returns:
            List of alerts
        """
        filters = {"account_id": str(account_id)}
        if status:
            filters["status"] = status

        return await cls.get_all(
            filters=filters,
            order_by="created_at",
            order_desc=True
        )

    @classmethod
    async def get_pending_alerts(cls, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """
        Get pending alerts for processing.

        Args:
            limit: Maximum number of alerts to fetch

        Returns:
            List of pending alerts ordered by created_at
        """
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
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """
        Get failed alerts from the last N hours.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of alerts to fetch

        Returns:
            List of failed alerts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        result = supabase.table(cls.table_name) \
            .select("*") \
            .eq("status", "FAILED") \
            .gte("created_at", cutoff_time.isoformat()) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return result.data

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
        alert = await cls.get_by_id(alert_id)

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
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update alert status.

        Args:
            alert_id: Alert UUID
            status: New status (PENDING, PROCESSING, SENT, FAILED)
            error_message: Optional error message for FAILED status

        Returns:
            Updated alert
        """
        update_data = {"status": status}

        if error_message:
            # Store error in payload
            alert = await cls.get_by_id(alert_id)
            if alert:
                payload = alert.get("payload", {})
                payload["error"] = error_message
                update_data["payload"] = payload

        return await cls.update(alert_id, update_data)

    @classmethod
    async def mark_as_processing(cls, alert_id: UUID) -> Dict[str, Any]:
        """
        Mark alert as processing.

        Args:
            alert_id: Alert UUID

        Returns:
            Updated alert
        """
        return await cls.update_status(alert_id, "PROCESSING")

    @classmethod
    async def mark_as_sent(cls, alert_id: UUID) -> Dict[str, Any]:
        """
        Mark alert as sent.

        Args:
            alert_id: Alert UUID

        Returns:
            Updated alert
        """
        return await cls.update_status(alert_id, "SENT")

    @classmethod
    async def mark_as_failed(
        cls,
        alert_id: UUID,
        error_message: str
    ) -> Dict[str, Any]:
        """
        Mark alert as failed with error message.

        Args:
            alert_id: Alert UUID
            error_message: Error description

        Returns:
            Updated alert
        """
        return await cls.update_status(alert_id, "FAILED", error_message)

    @classmethod
    async def retry_failed_alert(cls, alert_id: UUID) -> Dict[str, Any]:
        """
        Reset a failed alert to pending for retry.

        Args:
            alert_id: Alert UUID

        Returns:
            Updated alert
        """
        return await cls.update_status(alert_id, "PENDING")

    @classmethod
    async def get_statistics(
        cls,
        account_id: UUID,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get alert statistics for an account.

        Args:
            account_id: Account UUID
            hours: Number of hours to look back

        Returns:
            Statistics dict
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get all alerts for account in time window
        result = supabase.table(cls.table_name) \
            .select("*") \
            .eq("account_id", str(account_id)) \
            .gte("created_at", cutoff_time.isoformat()) \
            .execute()

        alerts = result.data

        total = len(alerts)
        pending = len([a for a in alerts if a["status"] == "PENDING"])
        processing = len([a for a in alerts if a["status"] == "PROCESSING"])
        sent = len([a for a in alerts if a["status"] == "SENT"])
        failed = len([a for a in alerts if a["status"] == "FAILED"])

        # Group by reason
        reasons = {}
        for alert in alerts:
            reason = alert.get("reason", "unknown")
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
    async def cleanup_old_alerts(cls, days: int = 30) -> int:
        """
        Delete old sent alerts (cleanup).

        Args:
            days: Delete alerts older than this many days

        Returns:
            Number of deleted alerts
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        result = supabase.table(cls.table_name) \
            .delete() \
            .eq("status", "SENT") \
            .lt("created_at", cutoff_time.isoformat()) \
            .execute()

        deleted_count = len(result.data) if result.data else 0

        logger.info(
            "Cleaned up old alerts",
            deleted_count=deleted_count,
            days=days
        )

        return deleted_count
