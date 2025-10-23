"""CommunicationsAPI client for WhatsApp and SMS notifications."""

import httpx
from typing import Dict, Any, Optional, List
from app.config import settings
from app.core.logger import logger


class CommunicationsAPIClient:
    """Client for CommunicationsAPI service."""

    def __init__(self):
        """Initialize communications client."""
        self.base_url = settings.COMM_API_URL
        self.api_key = settings.COMM_API_KEY
        self.timeout = 30.0

        # Default headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def send_whatsapp(
        self,
        phone: str,
        message: str,
        template: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message.

        Args:
            phone: Target phone number (e.g., +5511999999999)
            message: Message text
            template: Optional template name
            params: Optional template parameters

        Returns:
            Response dict with message_id and status

        Raises:
            httpx.HTTPError: On communication errors
        """
        endpoint = f"{self.base_url}/whatsapp/send"

        payload = {
            "phone": phone,
            "message": message,
        }

        if template:
            payload["template"] = template
            payload["params"] = params or {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "WhatsApp message sent",
                    phone=phone,
                    message_id=result.get("message_id"),
                    status=result.get("status")
                )

                return result

        except httpx.HTTPError as e:
            logger.error(
                "Failed to send WhatsApp message",
                phone=phone,
                error=str(e),
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            )
            raise

    async def send_sms(
        self,
        phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send SMS message.

        Args:
            phone: Target phone number (e.g., +5511999999999)
            message: Message text (max 160 chars recommended)

        Returns:
            Response dict with message_id and status

        Raises:
            httpx.HTTPError: On communication errors
        """
        endpoint = f"{self.base_url}/sms/send"

        payload = {
            "phone": phone,
            "message": message,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "SMS sent",
                    phone=phone,
                    message_id=result.get("message_id"),
                    status=result.get("status")
                )

                return result

        except httpx.HTTPError as e:
            logger.error(
                "Failed to send SMS",
                phone=phone,
                error=str(e),
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            )
            raise

    async def send_email(
        self,
        email: str,
        subject: str,
        message: str,
        html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email.

        Args:
            email: Target email address
            subject: Email subject
            message: Plain text message
            html: Optional HTML content

        Returns:
            Response dict with message_id and status

        Raises:
            httpx.HTTPError: On communication errors
        """
        endpoint = f"{self.base_url}/email/send"

        payload = {
            "email": email,
            "subject": subject,
            "message": message,
        }

        if html:
            payload["html"] = html

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "Email sent",
                    email=email,
                    message_id=result.get("message_id"),
                    status=result.get("status")
                )

                return result

        except httpx.HTTPError as e:
            logger.error(
                "Failed to send email",
                email=email,
                error=str(e),
                status_code=getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            )
            raise

    async def get_message_status(
        self,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Get message delivery status.

        Args:
            message_id: Message ID from send response

        Returns:
            Status dict

        Raises:
            httpx.HTTPError: On communication errors
        """
        endpoint = f"{self.base_url}/messages/{message_id}/status"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    endpoint,
                    headers=self.headers
                )
                response.raise_for_status()

                return response.json()

        except httpx.HTTPError as e:
            logger.error(
                "Failed to get message status",
                message_id=message_id,
                error=str(e)
            )
            raise

    async def send_bulk_whatsapp(
        self,
        recipients: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send bulk WhatsApp messages.

        Args:
            recipients: List of dicts with phone and message

        Returns:
            Bulk send result

        Raises:
            httpx.HTTPError: On communication errors
        """
        endpoint = f"{self.base_url}/whatsapp/send-bulk"

        payload = {
            "recipients": recipients
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for bulk
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "Bulk WhatsApp sent",
                    total=len(recipients),
                    successful=result.get("successful"),
                    failed=result.get("failed")
                )

                return result

        except httpx.HTTPError as e:
            logger.error(
                "Failed to send bulk WhatsApp",
                total=len(recipients),
                error=str(e)
            )
            raise

    async def health_check(self) -> bool:
        """
        Check if CommunicationsAPI is healthy.

        Returns:
            True if healthy, False otherwise
        """
        endpoint = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(endpoint)
                return response.status_code == 200

        except Exception as e:
            logger.warning(
                "CommunicationsAPI health check failed",
                error=str(e)
            )
            return False


# Singleton instance
comm_client = CommunicationsAPIClient()
