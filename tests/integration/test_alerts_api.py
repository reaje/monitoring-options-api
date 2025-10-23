"""Integration tests for alerts API."""

import pytest
from uuid import uuid4
from app.main import app
from app.database.supabase_client import supabase


@pytest.fixture
async def test_alert(test_account):
    """Create a test alert."""
    alert_data = {
        "account_id": test_account["id"],
        "reason": "test_alert",
        "payload": {"message": "Test alert message"},
        "status": "PENDING",
    }

    result = supabase.table("alert_queue").insert(alert_data).execute()
    alert = result.data[0]

    yield alert

    # Cleanup
    try:
        supabase.table("alert_queue").delete().eq("id", alert["id"]).execute()
    except Exception:
        pass


@pytest.fixture
async def multiple_alerts(test_account):
    """Create multiple test alerts."""
    alerts_data = [
        {
            "account_id": test_account["id"],
            "reason": "roll_trigger",
            "payload": {"position_id": str(uuid4())},
            "status": "PENDING",
        },
        {
            "account_id": test_account["id"],
            "reason": "expiration_warning",
            "payload": {"days_to_expiration": 3},
            "status": "SENT",
        },
        {
            "account_id": test_account["id"],
            "reason": "manual_alert",
            "payload": {"message": "Custom message"},
            "status": "FAILED",
        },
    ]

    result = supabase.table("alert_queue").insert(alerts_data).execute()
    alerts = result.data

    yield alerts

    # Cleanup
    try:
        for alert in alerts:
            supabase.table("alert_queue").delete().eq("id", alert["id"]).execute()
    except Exception:
        pass


@pytest.fixture
async def test_alert_log(test_alert):
    """Create a test alert log."""
    log_data = {
        "queue_id": test_alert["id"],
        "channel": "whatsapp",
        "target": "+5511999999999",
        "message": "Test notification",
        "status": "success",
        "provider_msg_id": "test_msg_123",
    }

    result = supabase.table("alert_logs").insert(log_data).execute()
    log = result.data[0]

    yield log

    # Cleanup
    try:
        supabase.table("alert_logs").delete().eq("id", log["id"]).execute()
    except Exception:
        pass


# =====================================
# GET /api/alerts - List Alerts
# =====================================


class TestAlertsGetList:
    """Test GET /api/alerts endpoint."""

    @pytest.mark.asyncio
    async def test_get_alerts_empty(self, auth_headers, test_account):
        """Test getting alerts when none exist."""
        request, response = await app.asgi_client.get(
            "/api/alerts", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 0
        assert response.json["alerts"] == []

    @pytest.mark.asyncio
    async def test_get_alerts_with_data(self, auth_headers, multiple_alerts):
        """Test getting alerts with data."""
        request, response = await app.asgi_client.get(
            "/api/alerts", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 3
        assert len(response.json["alerts"]) == 3

    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_account(
        self, auth_headers, test_account, multiple_alerts
    ):
        """Test filtering alerts by account."""
        request, response = await app.asgi_client.get(
            f"/api/alerts?account_id={test_account['id']}", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 3
        for alert in response.json["alerts"]:
            assert alert["account_id"] == test_account["id"]

    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_status(
        self, auth_headers, multiple_alerts
    ):
        """Test filtering alerts by status."""
        request, response = await app.asgi_client.get(
            "/api/alerts?status=PENDING", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 1
        assert response.json["alerts"][0]["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_get_alerts_unauthorized(self):
        """Test getting alerts without authentication."""
        request, response = await app.asgi_client.get("/api/alerts")

        assert response.status == 401


# =====================================
# GET /api/alerts/pending - List Pending Alerts
# =====================================


class TestAlertsGetPending:
    """Test GET /api/alerts/pending endpoint."""

    @pytest.mark.asyncio
    async def test_get_pending_alerts(self, auth_headers, multiple_alerts):
        """Test getting only pending alerts."""
        request, response = await app.asgi_client.get(
            "/api/alerts/pending", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 1
        assert response.json["alerts"][0]["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_get_pending_alerts_empty(self, auth_headers, test_account):
        """Test getting pending alerts when none exist."""
        request, response = await app.asgi_client.get(
            "/api/alerts/pending", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 0


# =====================================
# POST /api/alerts - Create Alert
# =====================================


class TestAlertsCreate:
    """Test POST /api/alerts endpoint."""

    @pytest.mark.asyncio
    async def test_create_alert_success(self, auth_headers, test_account):
        """Test creating an alert successfully."""
        alert_data = {
            "account_id": str(test_account["id"]),
            "reason": "manual_alert",
            "payload": {
                "message": "Custom notification",
                "priority": "high"
            },
        }

        request, response = await app.asgi_client.post(
            "/api/alerts", json=alert_data, headers=auth_headers
        )

        assert response.status == 201
        assert response.json["message"] == "Alert created successfully"
        assert response.json["alert"]["reason"] == "manual_alert"
        assert response.json["alert"]["status"] == "PENDING"

        # Cleanup
        alert_id = response.json["alert"]["id"]
        supabase.table("alert_queue").delete().eq("id", alert_id).execute()

    @pytest.mark.asyncio
    async def test_create_alert_with_position(
        self, auth_headers, test_account, test_asset
    ):
        """Test creating an alert with position reference."""
        # Create a position first
        position_data = {
            "account_id": test_account["id"],
            "asset_id": test_asset["id"],
            "side": "CALL",
            "strategy": "COVERED_CALL",
            "strike": 100.00,
            "expiration": "2025-03-15",
            "quantity": 100,
            "avg_premium": 2.50,
        }
        position_result = supabase.table("option_positions").insert(position_data).execute()
        position_id = position_result.data[0]["id"]

        alert_data = {
            "account_id": str(test_account["id"]),
            "option_position_id": position_id,
            "reason": "roll_trigger",
            "payload": {"delta": 0.75, "dte": 3},
        }

        request, response = await app.asgi_client.post(
            "/api/alerts", json=alert_data, headers=auth_headers
        )

        assert response.status == 201
        assert response.json["alert"]["option_position_id"] == position_id

        # Cleanup
        alert_id = response.json["alert"]["id"]
        supabase.table("alert_queue").delete().eq("id", alert_id).execute()
        supabase.table("option_positions").delete().eq("id", position_id).execute()

    @pytest.mark.asyncio
    async def test_create_alert_unauthorized_account(self, auth_headers):
        """Test creating an alert for account user doesn't own."""
        alert_data = {
            "account_id": str(uuid4()),
            "reason": "test",
            "payload": {},
        }

        request, response = await app.asgi_client.post(
            "/api/alerts", json=alert_data, headers=auth_headers
        )

        assert response.status == 403


# =====================================
# GET /api/alerts/{id} - Get Alert Details
# =====================================


class TestAlertsGetDetail:
    """Test GET /api/alerts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_alert_success(self, auth_headers, test_alert):
        """Test getting alert details successfully."""
        request, response = await app.asgi_client.get(
            f"/api/alerts/{test_alert['id']}", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["alert"]["id"] == test_alert["id"]
        assert response.json["alert"]["reason"] == test_alert["reason"]

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, auth_headers):
        """Test getting non-existent alert."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.get(
            f"/api/alerts/{fake_id}", headers=auth_headers
        )

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_get_alert_unauthorized(self):
        """Test getting alert without authentication."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.get(f"/api/alerts/{fake_id}")

        assert response.status == 401


# =====================================
# DELETE /api/alerts/{id} - Delete Alert
# =====================================


class TestAlertsDelete:
    """Test DELETE /api/alerts/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_alert_success(self, auth_headers, test_account):
        """Test deleting an alert successfully."""
        # Create alert to delete
        alert_data = {
            "account_id": test_account["id"],
            "reason": "test_delete",
            "payload": {},
        }
        result = supabase.table("alert_queue").insert(alert_data).execute()
        alert_id = result.data[0]["id"]

        request, response = await app.asgi_client.delete(
            f"/api/alerts/{alert_id}", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["message"] == "Alert deleted successfully"

        # Verify deletion
        result = supabase.table("alert_queue").select("*").eq("id", alert_id).execute()
        assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_delete_alert_not_found(self, auth_headers):
        """Test deleting non-existent alert."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.delete(
            f"/api/alerts/{fake_id}", headers=auth_headers
        )

        assert response.status == 404


# =====================================
# POST /api/alerts/{id}/retry - Retry Alert
# =====================================


class TestAlertsRetry:
    """Test POST /api/alerts/{id}/retry endpoint."""

    @pytest.mark.asyncio
    async def test_retry_failed_alert(self, auth_headers, test_account):
        """Test retrying a failed alert."""
        # Create failed alert
        alert_data = {
            "account_id": test_account["id"],
            "reason": "test_retry",
            "payload": {},
            "status": "FAILED",
        }
        result = supabase.table("alert_queue").insert(alert_data).execute()
        alert_id = result.data[0]["id"]

        request, response = await app.asgi_client.post(
            f"/api/alerts/{alert_id}/retry", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["message"] == "Alert marked for retry"
        assert response.json["alert"]["status"] == "PENDING"

        # Cleanup
        supabase.table("alert_queue").delete().eq("id", alert_id).execute()

    @pytest.mark.asyncio
    async def test_retry_alert_not_found(self, auth_headers):
        """Test retrying non-existent alert."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.post(
            f"/api/alerts/{fake_id}/retry", headers=auth_headers
        )

        assert response.status == 404


# =====================================
# GET /api/alerts/statistics/{account_id} - Get Statistics
# =====================================


class TestAlertsStatistics:
    """Test GET /api/alerts/statistics/{account_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, auth_headers, test_account, multiple_alerts):
        """Test getting alert statistics."""
        request, response = await app.asgi_client.get(
            f"/api/alerts/statistics/{test_account['id']}", headers=auth_headers
        )

        assert response.status == 200
        assert "statistics" in response.json
        stats = response.json["statistics"]
        assert stats["total_alerts"] == 3
        assert stats["pending"] == 1
        assert stats["sent"] == 1
        assert stats["failed"] == 1

    @pytest.mark.asyncio
    async def test_get_statistics_with_hours_param(
        self, auth_headers, test_account, multiple_alerts
    ):
        """Test getting statistics with custom hours parameter."""
        request, response = await app.asgi_client.get(
            f"/api/alerts/statistics/{test_account['id']}?hours=48",
            headers=auth_headers
        )

        assert response.status == 200
        assert response.json["statistics"]["period_hours"] == 48

    @pytest.mark.asyncio
    async def test_get_statistics_unauthorized_account(self, auth_headers):
        """Test getting statistics for account user doesn't own."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.get(
            f"/api/alerts/statistics/{fake_id}", headers=auth_headers
        )

        assert response.status == 403


# =====================================
# GET /api/alerts/{id}/logs - Get Alert Logs
# =====================================


class TestAlertsLogs:
    """Test GET /api/alerts/{id}/logs endpoint."""

    @pytest.mark.asyncio
    async def test_get_alert_logs(self, auth_headers, test_alert, test_alert_log):
        """Test getting logs for an alert."""
        request, response = await app.asgi_client.get(
            f"/api/alerts/{test_alert['id']}/logs", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 1
        assert len(response.json["logs"]) == 1
        assert response.json["logs"][0]["channel"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_get_alert_logs_empty(self, auth_headers, test_alert):
        """Test getting logs when none exist."""
        request, response = await app.asgi_client.get(
            f"/api/alerts/{test_alert['id']}/logs", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 0


# =====================================
# GET /api/alerts/logs/statistics - Get Logs Statistics
# =====================================


class TestLogsStatistics:
    """Test GET /api/alerts/logs/statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_logs_statistics(self, auth_headers):
        """Test getting logs statistics."""
        request, response = await app.asgi_client.get(
            "/api/alerts/logs/statistics", headers=auth_headers
        )

        assert response.status == 200
        assert "statistics" in response.json
        stats = response.json["statistics"]
        assert "total_notifications" in stats
        assert "success_rate" in stats
        assert "by_channel" in stats
