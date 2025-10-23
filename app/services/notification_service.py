"""Notification service for sending alerts via multiple channels."""

from typing import Dict, Any, List, Optional
from uuid import UUID
import asyncio
from app.services.communications_client import comm_client
from app.database.repositories.alerts import AlertQueueRepository
from app.database.repositories.alert_logs import AlertLogsRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


class NotificationService:
    """Service for processing and sending notifications."""

    def __init__(self):
        """Initialize notification service."""
        self.comm_client = comm_client
        self.max_retries = 3
        self.retry_delay = 5  # seconds

    async def process_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Process a single alert and send notifications.

        Args:
            alert: Alert dict from alert_queue

        Returns:
            True if all notifications sent successfully
        """
        alert_id = UUID(alert["id"])
        account_id = UUID(alert["account_id"])

        try:
            # Mark as processing
            await AlertQueueRepository.mark_as_processing(alert_id)

            # Get account details
            account = await AccountsRepository.get_by_id(account_id)
            if not account:
                logger.error("Account not found", alert_id=str(alert_id))
                await AlertQueueRepository.mark_as_failed(alert_id, "Account not found")
                return False

            # Get notification channels and target from account or alert payload
            channels = alert.get("payload", {}).get("channels", ["whatsapp"])
            phone = account.get("phone") or alert.get("payload", {}).get("phone")
            email = account.get("email")

            # Build message
            message = self._build_message(alert)

            # Send notifications to each channel
            all_success = True
            for channel in channels:
                success = await self._send_to_channel(
                    alert_id,
                    channel,
                    phone,
                    email,
                    message
                )
                if not success:
                    all_success = False

            # Update alert status
            if all_success:
                await AlertQueueRepository.mark_as_sent(alert_id)
                logger.info("Alert processed successfully", alert_id=str(alert_id))
            else:
                await AlertQueueRepository.mark_as_failed(
                    alert_id,
                    "One or more channels failed"
                )

            return all_success

        except Exception as e:
            logger.error(
                "Failed to process alert",
                alert_id=str(alert_id),
                error=str(e)
            )
            await AlertQueueRepository.mark_as_failed(alert_id, str(e))
            return False

    async def _send_to_channel(
        self,
        alert_id: UUID,
        channel: str,
        phone: Optional[str],
        email: Optional[str],
        message: str
    ) -> bool:
        """
        Send notification to a specific channel with retry logic.

        Args:
            alert_id: Alert UUID
            channel: Channel name (whatsapp, sms, email)
            phone: Target phone number
            email: Target email
            message: Message content

        Returns:
            True if sent successfully
        """
        for attempt in range(self.max_retries):
            try:
                if channel == "whatsapp":
                    if not phone:
                        logger.warning("No phone number for WhatsApp", alert_id=str(alert_id))
                        return False

                    result = await self.comm_client.send_whatsapp(phone, message)
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel="whatsapp",
                        target=phone,
                        message=message,
                        status="success",
                        provider_msg_id=result.get("message_id")
                    )
                    return True

                elif channel == "sms":
                    if not phone:
                        logger.warning("No phone number for SMS", alert_id=str(alert_id))
                        return False

                    result = await self.comm_client.send_sms(phone, message)
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel="sms",
                        target=phone,
                        message=message,
                        status="success",
                        provider_msg_id=result.get("message_id")
                    )
                    return True

                elif channel == "email":
                    if not email:
                        logger.warning("No email address", alert_id=str(alert_id))
                        return False

                    result = await self.comm_client.send_email(
                        email=email,
                        subject="Alerta - Monitoring Options",
                        message=message
                    )
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel="email",
                        target=email,
                        message=message,
                        status="success",
                        provider_msg_id=result.get("message_id")
                    )
                    return True

                else:
                    logger.warning("Unknown channel", channel=channel)
                    return False

            except Exception as e:
                logger.warning(
                    "Failed to send notification, retrying",
                    alert_id=str(alert_id),
                    channel=channel,
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    # Final attempt failed, log it
                    target = phone if channel in ["whatsapp", "sms"] else email
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel=channel,
                        target=target or "unknown",
                        message=message,
                        status="failed"
                    )
                    return False

        return False

    def _build_message(self, alert: Dict[str, Any]) -> str:
        """
        Build notification message from alert data.

        Args:
            alert: Alert dict

        Returns:
            Formatted message string
        """
        reason = alert.get("reason", "notification")
        payload = alert.get("payload", {})

        # Check if custom message exists
        if "message" in payload:
            return payload["message"]

        # Build message based on reason
        if reason == "roll_trigger":
            return self._build_roll_trigger_message(payload)
        elif reason == "expiration_warning":
            return self._build_expiration_warning_message(payload)
        elif reason == "delta_threshold":
            return self._build_delta_threshold_message(payload)
        else:
            return f"Alerta: {reason}"

    def _build_roll_trigger_message(self, payload: Dict[str, Any]) -> str:
        """Build message for roll trigger alert."""
        ticker = payload.get("ticker", "N/A")
        dte = payload.get("dte", "N/A")
        delta = payload.get("delta", "N/A")

        return (
            f"🔄 Oportunidade de Rolagem Detectada!\n\n"
            f"Ativo: {ticker}\n"
            f"DTE: {dte} dias\n"
            f"Delta: {delta}\n\n"
            f"Acesse o sistema para ver as sugestões de rolagem."
        )

    def _build_expiration_warning_message(self, payload: Dict[str, Any]) -> str:
        """Build message for expiration warning."""
        ticker = payload.get("ticker", "N/A")
        days = payload.get("days_to_expiration", "N/A")

        return (
            f"⚠️ Aviso de Vencimento Próximo\n\n"
            f"Ativo: {ticker}\n"
            f"Vence em: {days} dias\n\n"
            f"Considere avaliar a necessidade de rolagem."
        )

    def _build_delta_threshold_message(self, payload: Dict[str, Any]) -> str:
        """Build message for delta threshold alert."""
        ticker = payload.get("ticker", "N/A")
        delta = payload.get("delta", "N/A")
        threshold = payload.get("threshold", "N/A")

        # Format numbers with 2 decimal places if they are floats
        if isinstance(delta, (int, float)):
            delta = f"{delta:.2f}"
        if isinstance(threshold, (int, float)):
            threshold = f"{threshold:.2f}"

        return (
            f"📊 Threshold de Delta Atingido\n\n"
            f"Ativo: {ticker}\n"
            f"Delta Atual: {delta}\n"
            f"Threshold: {threshold}\n\n"
            f"A opção está se aproximando do strike."
        )

    async def process_pending_alerts(self, limit: int = 100) -> Dict[str, int]:
        """
        Process batch of pending alerts.

        Args:
            limit: Maximum number of alerts to process

        Returns:
            Dict with processing statistics
        """
        # Get pending alerts
        pending_alerts = await AlertQueueRepository.get_pending_alerts(limit)

        if not pending_alerts:
            logger.debug("No pending alerts to process")
            return {"total": 0, "successful": 0, "failed": 0}

        logger.info("Processing pending alerts", count=len(pending_alerts))

        successful = 0
        failed = 0

        # Process alerts sequentially (can be parallelized if needed)
        for alert in pending_alerts:
            success = await self.process_alert(alert)
            if success:
                successful += 1
            else:
                failed += 1

        logger.info(
            "Finished processing alerts",
            total=len(pending_alerts),
            successful=successful,
            failed=failed
        )

        return {
            "total": len(pending_alerts),
            "successful": successful,
            "failed": failed
        }

    async def send_manual_notification(
        self,
        account_id: UUID,
        message: str,
        channels: List[str],
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send manual notification (bypass queue).

        Args:
            account_id: Account UUID
            message: Message content
            channels: List of channels to use
            phone: Optional phone override
            email: Optional email override

        Returns:
            Send result dict
        """
        # Get account details if phone/email not provided
        if not phone and not email:
            account = await AccountsRepository.get_by_id(account_id)
            if not account:
                raise ValueError("Account not found")

            phone = account.get("phone")
            email = account.get("email")

        results = {}

        for channel in channels:
            try:
                if channel == "whatsapp":
                    if not phone:
                        results[channel] = {"status": "failed", "error": "No phone number"}
                        continue

                    result = await self.comm_client.send_whatsapp(phone, message)
                    results[channel] = {
                        "status": "success",
                        "message_id": result.get("message_id")
                    }

                elif channel == "sms":
                    if not phone:
                        results[channel] = {"status": "failed", "error": "No phone number"}
                        continue

                    result = await self.comm_client.send_sms(phone, message)
                    results[channel] = {
                        "status": "success",
                        "message_id": result.get("message_id")
                    }

                elif channel == "email":
                    if not email:
                        results[channel] = {"status": "failed", "error": "No email address"}
                        continue

                    result = await self.comm_client.send_email(
                        email=email,
                        subject="Notificação Manual - Monitoring Options",
                        message=message
                    )
                    results[channel] = {
                        "status": "success",
                        "message_id": result.get("message_id")
                    }

            except Exception as e:
                logger.error(
                    "Failed to send manual notification",
                    channel=channel,
                    error=str(e)
                )
                results[channel] = {"status": "failed", "error": str(e)}

        return results


# Singleton instance
notification_service = NotificationService()
