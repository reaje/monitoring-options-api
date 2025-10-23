"""Unit tests for background workers."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, date, timedelta
from uuid import uuid4
from app.workers.monitor_worker import MonitorWorker
from app.workers.notifier_worker import NotifierWorker


class TestMonitorWorker:
    """Test MonitorWorker."""

    @pytest.fixture
    def monitor_worker(self):
        """Create monitor worker instance."""
        return MonitorWorker()

    @pytest.mark.asyncio
    @patch('app.workers.monitor_worker.AccountsRepository')
    @patch('app.workers.monitor_worker.RulesRepository')
    @patch('app.workers.monitor_worker.OptionsRepository')
    @patch('app.workers.monitor_worker.AlertQueueRepository')
    async def test_run_no_accounts(
        self,
        mock_alerts_repo,
        mock_options_repo,
        mock_rules_repo,
        mock_accounts_repo,
        monitor_worker
    ):
        """Test worker run with no accounts."""
        # Setup mocks
        monitor_worker._get_all_accounts = AsyncMock(return_value=[])

        # Execute
        result = await monitor_worker.run()

        # Assertions
        assert result["accounts_processed"] == 0
        assert result["positions_checked"] == 0
        assert result["alerts_created"] == 0

    @pytest.mark.asyncio
    @patch('app.workers.monitor_worker.RulesRepository')
    @patch('app.workers.monitor_worker.OptionsRepository')
    @patch('app.workers.monitor_worker.AlertQueueRepository')
    async def test_run_account_no_rules(
        self,
        mock_alerts_repo,
        mock_options_repo,
        mock_rules_repo,
        monitor_worker
    ):
        """Test worker run with account but no active rules."""
        # Setup mocks
        account = {"id": str(uuid4()), "name": "Test Account"}
        monitor_worker._get_all_accounts = AsyncMock(return_value=[account])
        mock_rules_repo.get_active_rules = AsyncMock(return_value=[])

        # Execute
        result = await monitor_worker.run()

        # Assertions
        assert result["accounts_processed"] == 0  # Skipped because no rules

    @pytest.mark.asyncio
    @patch('app.workers.monitor_worker.RulesRepository')
    @patch('app.workers.monitor_worker.OptionsRepository')
    @patch('app.workers.monitor_worker.AlertQueueRepository')
    async def test_check_expiration_warning_3_days(
        self,
        mock_alerts_repo,
        mock_options_repo,
        mock_rules_repo,
        monitor_worker
    ):
        """Test expiration warning for position 3 days from expiration."""
        # Setup position expiring in 3 days
        expiration = (date.today() + timedelta(days=3)).isoformat()
        position = {
            "id": str(uuid4()),
            "ticker": "PETR4",
            "expiration": expiration,
            "strike": 100.00,
            "side": "CALL"
        }
        account_id = uuid4()

        # Mock no existing alerts
        mock_alerts_repo.get_by_account_id = AsyncMock(return_value=[])
        mock_alerts_repo.create = AsyncMock()

        # Execute
        result = await monitor_worker._check_expiration_warning(position, account_id)

        # Assertions
        assert result is True
        mock_alerts_repo.create.assert_called_once()

        # Check alert data
        call_args = mock_alerts_repo.create.call_args[0][0]
        assert call_args["reason"] == "expiration_warning"
        assert call_args["payload"]["days_to_expiration"] == 3

    @pytest.mark.asyncio
    @patch('app.workers.monitor_worker.AlertQueueRepository')
    async def test_check_expiration_warning_already_alerted_today(
        self,
        mock_alerts_repo,
        monitor_worker
    ):
        """Test that expiration warning is not duplicated if already sent today."""
        # Setup position
        expiration = (date.today() + timedelta(days=2)).isoformat()
        position = {
            "id": str(uuid4()),
            "ticker": "PETR4",
            "expiration": expiration,
            "strike": 100.00,
            "side": "CALL"
        }
        account_id = uuid4()

        # Mock existing alert for today
        existing_alert = {
            "id": str(uuid4()),
            "option_position_id": position["id"],
            "reason": "expiration_warning",
            "created_at": datetime.now().isoformat()
        }
        mock_alerts_repo.get_by_account_id = AsyncMock(return_value=[existing_alert])

        # Execute
        result = await monitor_worker._check_expiration_warning(position, account_id)

        # Assertions
        assert result is False  # Should not create duplicate

    @pytest.mark.asyncio
    @patch('app.workers.monitor_worker.AlertQueueRepository')
    async def test_check_expiration_warning_no_alert_for_distant_expiration(
        self,
        mock_alerts_repo,
        monitor_worker
    ):
        """Test no alert for positions expiring more than 3 days away."""
        # Setup position expiring in 10 days
        expiration = (date.today() + timedelta(days=10)).isoformat()
        position = {
            "id": str(uuid4()),
            "ticker": "VALE3",
            "expiration": expiration
        }
        account_id = uuid4()

        mock_alerts_repo.get_by_account_id = AsyncMock(return_value=[])

        # Execute
        result = await monitor_worker._check_expiration_warning(position, account_id)

        # Assertions
        assert result is False

    def test_calculate_dte(self, monitor_worker):
        """Test DTE calculation."""
        # Test with string date
        future_date = (date.today() + timedelta(days=5)).isoformat()
        dte = monitor_worker._calculate_dte(future_date)
        assert dte == 5

        # Test with date object
        future_date = date.today() + timedelta(days=10)
        dte = monitor_worker._calculate_dte(future_date)
        assert dte == 10


class TestNotifierWorker:
    """Test NotifierWorker."""

    @pytest.fixture
    def notifier_worker(self):
        """Create notifier worker instance."""
        return NotifierWorker()

    @pytest.mark.asyncio
    @patch('app.workers.notifier_worker.notification_service')
    async def test_run_success(self, mock_notification_service, notifier_worker):
        """Test successful notifier worker run."""
        # Setup mock
        mock_notification_service.process_pending_alerts = AsyncMock(
            return_value={
                "total": 10,
                "successful": 9,
                "failed": 1
            }
        )

        # Execute
        result = await notifier_worker.run()

        # Assertions
        assert result["status"] == "success"
        assert result["total_processed"] == 10
        assert result["successful"] == 9
        assert result["failed"] == 1
        assert result["run_number"] == 1

    @pytest.mark.asyncio
    @patch('app.workers.notifier_worker.notification_service')
    async def test_run_no_alerts(self, mock_notification_service, notifier_worker):
        """Test notifier worker run with no pending alerts."""
        # Setup mock
        mock_notification_service.process_pending_alerts = AsyncMock(
            return_value={
                "total": 0,
                "successful": 0,
                "failed": 0
            }
        )

        # Execute
        result = await notifier_worker.run()

        # Assertions
        assert result["status"] == "success"
        assert result["total_processed"] == 0

    @pytest.mark.asyncio
    @patch('app.workers.notifier_worker.notification_service')
    async def test_run_failure(self, mock_notification_service, notifier_worker):
        """Test notifier worker run with error."""
        # Setup mock to raise exception
        mock_notification_service.process_pending_alerts = AsyncMock(
            side_effect=Exception("Processing error")
        )

        # Execute
        result = await notifier_worker.run()

        # Assertions
        assert result["status"] == "failed"
        assert "error" in result
        assert result["error"] == "Processing error"

    @pytest.mark.asyncio
    @patch('app.workers.notifier_worker.notification_service')
    async def test_run_increments_count(self, mock_notification_service, notifier_worker):
        """Test that run count increments."""
        mock_notification_service.process_pending_alerts = AsyncMock(
            return_value={"total": 0, "successful": 0, "failed": 0}
        )

        # Run multiple times
        result1 = await notifier_worker.run()
        result2 = await notifier_worker.run()
        result3 = await notifier_worker.run()

        # Assertions
        assert result1["run_number"] == 1
        assert result2["run_number"] == 2
        assert result3["run_number"] == 3
