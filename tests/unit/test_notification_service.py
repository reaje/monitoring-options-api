"""Unit tests for notification service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from app.services.notification_service import NotificationService


@pytest.fixture
def notification_service():
    """Create notification service instance."""
    return NotificationService()


@pytest.fixture
def sample_alert():
    """Create sample alert data."""
    return {
        "id": str(uuid4()),
        "account_id": str(uuid4()),
        "reason": "roll_trigger",
        "payload": {
            "ticker": "PETR4",
            "dte": 3,
            "delta": 0.75,
            "channels": ["whatsapp"]
        },
        "status": "PENDING"
    }


@pytest.fixture
def sample_account():
    """Create sample account data."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "name": "Test Account",
        "phone": "+5511999999999",
        "email": "test@example.com"
    }


class TestMessageBuilding:
    """Test message building methods."""

    def test_build_roll_trigger_message(self, notification_service):
        """Test building roll trigger message."""
        payload = {
            "ticker": "PETR4",
            "dte": 3,
            "delta": 0.75
        }

        message = notification_service._build_roll_trigger_message(payload)

        assert "Rolagem" in message
        assert "PETR4" in message
        assert "3" in message
        assert "0.75" in message

    def test_build_expiration_warning_message(self, notification_service):
        """Test building expiration warning message."""
        payload = {
            "ticker": "VALE3",
            "days_to_expiration": 5
        }

        message = notification_service._build_expiration_warning_message(payload)

        assert "Vencimento" in message
        assert "VALE3" in message
        assert "5" in message

    def test_build_delta_threshold_message(self, notification_service):
        """Test building delta threshold message."""
        payload = {
            "ticker": "BBAS3",
            "delta": 0.85,
            "threshold": 0.80
        }

        message = notification_service._build_delta_threshold_message(payload)

        assert "Delta" in message
        assert "BBAS3" in message
        assert "0.85" in message
        assert "0.80" in message

    def test_build_message_with_custom_message(self, notification_service):
        """Test building message with custom message in payload."""
        alert = {
            "reason": "custom",
            "payload": {
                "message": "Custom notification text"
            }
        }

        message = notification_service._build_message(alert)

        assert message == "Custom notification text"

    def test_build_message_with_unknown_reason(self, notification_service):
        """Test building message with unknown reason."""
        alert = {
            "reason": "unknown_reason",
            "payload": {}
        }

        message = notification_service._build_message(alert)

        assert "unknown_reason" in message


class TestSendToChannel:
    """Test sending to different channels."""

    @pytest.mark.asyncio
    @patch('app.services.notification_service.comm_client')
    @patch('app.services.notification_service.AlertLogsRepository')
    async def test_send_whatsapp_success(
        self,
        mock_logs_repo,
        mock_comm_client,
        notification_service
    ):
        """Test successful WhatsApp send."""
        # Setup mocks
        mock_comm_client.send_whatsapp = AsyncMock(
            return_value={"message_id": "msg_123", "status": "sent"}
        )
        mock_logs_repo.create_log = AsyncMock()

        # Execute
        alert_id = uuid4()
        result = await notification_service._send_to_channel(
            alert_id=alert_id,
            channel="whatsapp",
            phone="+5511999999999",
            email=None,
            message="Test message"
        )

        # Assertions
        assert result is True
        mock_comm_client.send_whatsapp.assert_called_once_with(
            "+5511999999999",
            "Test message"
        )
        mock_logs_repo.create_log.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.notification_service.comm_client')
    @patch('app.services.notification_service.AlertLogsRepository')
    async def test_send_sms_success(
        self,
        mock_logs_repo,
        mock_comm_client,
        notification_service
    ):
        """Test successful SMS send."""
        # Setup mocks
        mock_comm_client.send_sms = AsyncMock(
            return_value={"message_id": "sms_456", "status": "sent"}
        )
        mock_logs_repo.create_log = AsyncMock()

        # Execute
        alert_id = uuid4()
        result = await notification_service._send_to_channel(
            alert_id=alert_id,
            channel="sms",
            phone="+5511999999999",
            email=None,
            message="Test SMS"
        )

        # Assertions
        assert result is True
        mock_comm_client.send_sms.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.notification_service.comm_client')
    @patch('app.services.notification_service.AlertLogsRepository')
    async def test_send_email_success(
        self,
        mock_logs_repo,
        mock_comm_client,
        notification_service
    ):
        """Test successful email send."""
        # Setup mocks
        mock_comm_client.send_email = AsyncMock(
            return_value={"message_id": "email_789", "status": "sent"}
        )
        mock_logs_repo.create_log = AsyncMock()

        # Execute
        alert_id = uuid4()
        result = await notification_service._send_to_channel(
            alert_id=alert_id,
            channel="email",
            phone=None,
            email="test@example.com",
            message="Test email"
        )

        # Assertions
        assert result is True
        mock_comm_client.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_whatsapp_no_phone(self, notification_service):
        """Test WhatsApp send without phone number."""
        alert_id = uuid4()
        result = await notification_service._send_to_channel(
            alert_id=alert_id,
            channel="whatsapp",
            phone=None,
            email=None,
            message="Test"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_unknown_channel(self, notification_service):
        """Test send with unknown channel."""
        alert_id = uuid4()
        result = await notification_service._send_to_channel(
            alert_id=alert_id,
            channel="telegram",  # Unsupported channel
            phone="+5511999999999",
            email=None,
            message="Test"
        )

        assert result is False

    @pytest.mark.asyncio
    @patch('app.services.notification_service.comm_client')
    @patch('app.services.notification_service.AlertLogsRepository')
    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_send_with_retry(
        self,
        mock_sleep,
        mock_logs_repo,
        mock_comm_client,
        notification_service
    ):
        """Test send with retry logic."""
        # Setup mocks - fail twice, succeed on third attempt
        mock_comm_client.send_whatsapp = AsyncMock(
            side_effect=[
                Exception("Network error"),
                Exception("Timeout"),
                {"message_id": "msg_123", "status": "sent"}
            ]
        )
        mock_logs_repo.create_log = AsyncMock()

        # Execute
        alert_id = uuid4()
        result = await notification_service._send_to_channel(
            alert_id=alert_id,
            channel="whatsapp",
            phone="+5511999999999",
            email=None,
            message="Test"
        )

        # Assertions
        assert result is True
        assert mock_comm_client.send_whatsapp.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries


class TestProcessAlert:
    """Test alert processing."""

    @pytest.mark.asyncio
    @patch('app.services.notification_service.AlertQueueRepository')
    @patch('app.services.notification_service.AccountsRepository')
    @patch('app.services.notification_service.comm_client')
    @patch('app.services.notification_service.AlertLogsRepository')
    async def test_process_alert_success(
        self,
        mock_logs_repo,
        mock_comm_client,
        mock_accounts_repo,
        mock_alerts_repo,
        notification_service,
        sample_alert,
        sample_account
    ):
        """Test successful alert processing."""
        # Setup mocks
        mock_alerts_repo.mark_as_processing = AsyncMock()
        mock_alerts_repo.mark_as_sent = AsyncMock()
        mock_accounts_repo.get_by_id = AsyncMock(return_value=sample_account)
        mock_comm_client.send_whatsapp = AsyncMock(
            return_value={"message_id": "msg_123"}
        )
        mock_logs_repo.create_log = AsyncMock()

        # Execute
        result = await notification_service.process_alert(sample_alert)

        # Assertions
        assert result is True
        mock_alerts_repo.mark_as_processing.assert_called_once()
        mock_alerts_repo.mark_as_sent.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.notification_service.AlertQueueRepository')
    @patch('app.services.notification_service.AccountsRepository')
    async def test_process_alert_account_not_found(
        self,
        mock_accounts_repo,
        mock_alerts_repo,
        notification_service,
        sample_alert
    ):
        """Test processing alert when account not found."""
        # Setup mocks
        mock_alerts_repo.mark_as_processing = AsyncMock()
        mock_alerts_repo.mark_as_failed = AsyncMock()
        mock_accounts_repo.get_by_id = AsyncMock(return_value=None)

        # Execute
        result = await notification_service.process_alert(sample_alert)

        # Assertions
        assert result is False
        mock_alerts_repo.mark_as_failed.assert_called_once()


class TestManualNotification:
    """Test manual notification sending."""

    @pytest.mark.asyncio
    @patch('app.services.notification_service.AccountsRepository')
    @patch('app.services.notification_service.comm_client')
    async def test_send_manual_notification_whatsapp(
        self,
        mock_comm_client,
        mock_accounts_repo,
        notification_service,
        sample_account
    ):
        """Test sending manual WhatsApp notification."""
        # Setup mocks
        mock_accounts_repo.get_by_id = AsyncMock(return_value=sample_account)
        mock_comm_client.send_whatsapp = AsyncMock(
            return_value={"message_id": "msg_123"}
        )

        # Execute
        account_id = uuid4()
        results = await notification_service.send_manual_notification(
            account_id=account_id,
            message="Manual test message",
            channels=["whatsapp"]
        )

        # Assertions
        assert "whatsapp" in results
        assert results["whatsapp"]["status"] == "success"

    @pytest.mark.asyncio
    @patch('app.services.notification_service.comm_client')
    async def test_send_manual_notification_with_override(
        self,
        mock_comm_client,
        notification_service
    ):
        """Test sending manual notification with phone override."""
        # Setup mocks
        mock_comm_client.send_sms = AsyncMock(
            return_value={"message_id": "sms_456"}
        )

        # Execute - with phone override, should not fetch account
        account_id = uuid4()
        results = await notification_service.send_manual_notification(
            account_id=account_id,
            message="Override test",
            channels=["sms"],
            phone="+5511888888888"
        )

        # Assertions
        assert "sms" in results
        assert results["sms"]["status"] == "success"
        mock_comm_client.send_sms.assert_called_once_with(
            "+5511888888888",
            "Override test"
        )
