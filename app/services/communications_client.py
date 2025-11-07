"""CommunicationsAPI client for WhatsApp and SMS notifications."""

import httpx
from typing import Dict, Any, Optional, List
from app.config import settings
from app.core.logger import logger


class CommunicationsAPIClient:
    """Client for CommunicationsAPI service."""

    def __init__(self):
        """Initialize communications client."""
        self.base_url = settings.COMM_API_URL.rstrip("/")
        self.api_key = (settings.COMM_API_KEY or "").strip()
        self.client_id = getattr(settings, "COMM_CLIENT_ID", None)
        self.email = getattr(settings, "COMM_EMAIL", None)
        self.password = getattr(settings, "COMM_PASSWORD", None)
        self.timeout = 30.0
        self._auth_token: Optional[str] = self.api_key or None  # Prefer API key if provided

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize E.164 to only digits as required by CommunicationsAPI schemas (10-15 digits)."""
        return "".join(ch for ch in str(phone) if ch.isdigit())

    async def _login(self) -> None:
        """Authenticate against Communications API to obtain JWT when API key is not provided."""
        # If API key configured, skip login
        if self.api_key:
            self._auth_token = self.api_key
            return
        # Try client-login first (tenant-aware)
        login_payload_variants: List[Dict[str, Any]] = []
        if self.client_id and self.email and self.password:
            login_payload_variants.append({
                "clientId": self.client_id,
                "email": self.email,
                "password": self.password,
            })
        # Fallback to simple login without clientId
        if self.email and self.password:
            login_payload_variants.append({
                "email": self.email,
                "password": self.password,
            })
        if not login_payload_variants:
            logger.warning("CommunicationsAPI login skipped: missing credentials")
            self._auth_token = None
            return
        # Endpoints as per OpenAPI
        endpoints = [f"{self.base_url}/api/v1/Auth/client-login", f"{self.base_url}/api/v1/Auth/login"]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for ep in endpoints:
                for payload in login_payload_variants:
                    try:
                        resp = await client.post(ep, json=payload, headers={"Content-Type": "application/json"})
                        if resp.status_code >= 400:
                            continue
                        data = resp.json()
                        token = data.get("access_token") or data.get("accessToken") or data.get("token") or data.get("jwt")
                        if token:
                            self._auth_token = token
                            logger.info("CommunicationsAPI auth success", endpoint=ep)
                            return
                    except Exception as e:
                        logger.warning("CommunicationsAPI auth attempt failed", endpoint=ep, error=str(e))
        logger.warning("CommunicationsAPI auth failed: no token obtained")
        self._auth_token = None

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
        # Prefer Notification endpoint; fallback to generic Message endpoint
        norm = self._normalize_phone(phone)
        primary_payload = {"to": norm, "message": message}
        if template:
            meta: Dict[str, Any] = {"template": template}
            if params:
                meta.update(params)
            primary_payload["metadata"] = meta
        fallback_payload = {"to": norm, "content": message}
        endpoints = [
            (f"{self.base_url}/api/v1/Notification/whatsapp", primary_payload),
            (f"{self.base_url}/api/v1/Message/text", fallback_payload),
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Ensure auth token
            if not self._auth_token:
                await self._login()
            last_exc: Optional[Exception] = None
            for ep, payload in endpoints:
                for attempt in range(2):  # try once, on 401 re-login and retry
                    try:
                        resp = await client.post(ep, json=payload, headers=self._headers())
                        if resp.status_code == 401 and attempt == 0:
                            await self._login()
                            continue
                        resp.raise_for_status()
                        result = resp.json()
                        logger.debug("WhatsApp API response", endpoint=ep, response=result)
                        logger.info("WhatsApp message sent", phone=phone, endpoint=ep, status=result.get("status"), provider_msg_id=(result.get("message_id") or result.get("id") or result.get("externalId") or result.get("messageId")))
                        return result
                    except httpx.HTTPError as e:
                        last_exc = e
                        # Try next variant on 400/404/415
                        if getattr(e, "response", None) and e.response is not None and e.response.status_code in (400, 404, 415):
                            break
            logger.error("Failed to send WhatsApp message", phone=phone, error=str(last_exc) if last_exc else "unknown")
            if last_exc:
                raise last_exc
            raise RuntimeError("Unknown error sending WhatsApp message")

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
        norm = self._normalize_phone(phone)
        endpoints = [
            (f"{self.base_url}/api/v1/Notification/sms", {"to": norm, "message": message}),
            (f"{self.base_url}/api/v1/Message/text", {"to": norm, "content": message}),
        ]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if not self._auth_token:
                await self._login()
            last_exc: Optional[Exception] = None
            for ep, payload in endpoints:
                for attempt in range(2):
                    try:
                        resp = await client.post(ep, json=payload, headers=self._headers())
                        if resp.status_code == 401 and attempt == 0:
                            await self._login()
                            continue
                        resp.raise_for_status()
                        result = resp.json()
                        logger.debug("SMS API response", endpoint=ep, response=result)
                        logger.info("SMS sent", phone=phone, endpoint=ep, status=result.get("status"), provider_msg_id=(result.get("message_id") or result.get("id") or result.get("externalId") or result.get("messageId")))
                        return result
                    except httpx.HTTPError as e:
                        last_exc = e
                        if getattr(e, "response", None) and e.response is not None and e.response.status_code in (400, 404, 415):
                            break
            logger.error("Failed to send SMS", phone=phone, error=str(last_exc) if last_exc else "unknown")
            if last_exc:
                raise last_exc
            raise RuntimeError("Unknown error sending SMS")

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
        html_body = html if html is not None else message
        payload = {"to": email, "subject": subject, "htmlContent": html_body}
        if message and html_body != message:
            payload["textContent"] = message
        endpoints = [
            (f"{self.base_url}/api/v1/Notification/email", payload),
        ]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if not self._auth_token:
                await self._login()
            last_exc: Optional[Exception] = None
            for ep, payload in endpoints:
                for attempt in range(2):
                    try:
                        resp = await client.post(ep, json=payload, headers=self._headers())
                        if resp.status_code == 401 and attempt == 0:
                            await self._login()
                            continue
                        resp.raise_for_status()
                        result = resp.json()
                        logger.debug("Email API response", endpoint=ep, response=result)
                        logger.info("Email sent", email=email, endpoint=ep, status=result.get("status"), provider_msg_id=(result.get("message_id") or result.get("id") or result.get("externalId") or result.get("messageId")))
                        return result
                    except httpx.HTTPError as e:
                        last_exc = e
                        if getattr(e, "response", None) and e.response is not None and e.response.status_code in (400, 404, 415):
                            break
            logger.error("Failed to send email", email=email, error=str(last_exc) if last_exc else "unknown")
            if last_exc:
                raise last_exc
            raise RuntimeError("Unknown error sending email")

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
        # Try Notification then Message status endpoints
        endpoints = [
            f"{self.base_url}/api/v1/Notification/{message_id}",
            f"{self.base_url}/api/v1/Message/{message_id}/status",
        ]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if not self._auth_token:
                await self._login()
            last_exc: Optional[Exception] = None
            for ep in endpoints:
                for attempt in range(2):
                    try:
                        resp = await client.get(ep, headers=self._headers())
                        if resp.status_code == 401 and attempt == 0:
                            await self._login()
                            continue
                        resp.raise_for_status()
                        return resp.json()
                    except httpx.HTTPError as e:
                        last_exc = e
                        if getattr(e, "response", None) and e.response is not None and e.response.status_code in (400, 404, 415):
                            break
            logger.error("Failed to get message status", message_id=message_id, error=str(last_exc) if last_exc else "unknown")
            if last_exc:
                raise last_exc
            raise RuntimeError("Unknown error getting message status")

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
                    headers=self._headers()
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
