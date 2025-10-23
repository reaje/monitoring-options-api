"""Integration tests for roll rules API."""

import pytest
from uuid import uuid4
from app.main import app
from app.database.supabase_client import supabase


@pytest.fixture
async def test_rule(test_account):
    """Create a test rule."""
    rule_data = {
        "account_id": test_account["id"],
        "delta_threshold": 0.60,
        "dte_min": 3,
        "dte_max": 5,
        "spread_threshold": 5.0,
        "price_to_strike_ratio": 0.98,
        "min_volume": 1000,
        "max_spread": 0.05,
        "min_oi": 5000,
        "target_otm_pct_low": 0.03,
        "target_otm_pct_high": 0.08,
        "notify_channels": ["whatsapp", "sms"],
        "is_active": True,
    }

    result = supabase.table("roll_rules").insert(rule_data).execute()
    rule = result.data[0]

    yield rule

    # Cleanup
    try:
        supabase.table("roll_rules").delete().eq("id", rule["id"]).execute()
    except Exception:
        pass


@pytest.fixture
async def multiple_rules(test_account):
    """Create multiple test rules."""
    rules_data = [
        {
            "account_id": test_account["id"],
            "delta_threshold": 0.60,
            "dte_min": 3,
            "dte_max": 5,
            "is_active": True,
        },
        {
            "account_id": test_account["id"],
            "delta_threshold": 0.70,
            "dte_min": 5,
            "dte_max": 7,
            "is_active": False,
        },
        {
            "account_id": test_account["id"],
            "delta_threshold": 0.50,
            "dte_min": 1,
            "dte_max": 3,
            "is_active": True,
        },
    ]

    result = supabase.table("roll_rules").insert(rules_data).execute()
    rules = result.data

    yield rules

    # Cleanup
    try:
        for rule in rules:
            supabase.table("roll_rules").delete().eq("id", rule["id"]).execute()
    except Exception:
        pass


# =====================================
# GET /api/rules - List Rules
# =====================================


class TestRulesGetList:
    """Test GET /api/rules endpoint."""

    @pytest.mark.asyncio
    async def test_get_rules_empty(self, auth_headers, test_account):
        """Test getting rules when none exist."""
        request, response = await app.asgi_client.get(
            "/api/rules", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 0
        assert response.json["rules"] == []

    @pytest.mark.asyncio
    async def test_get_rules_with_data(self, auth_headers, multiple_rules):
        """Test getting rules with data."""
        request, response = await app.asgi_client.get(
            "/api/rules", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 3
        assert len(response.json["rules"]) == 3

    @pytest.mark.asyncio
    async def test_get_rules_filter_by_account(
        self, auth_headers, test_account, multiple_rules
    ):
        """Test filtering rules by account."""
        request, response = await app.asgi_client.get(
            f"/api/rules?account_id={test_account['id']}", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 3
        for rule in response.json["rules"]:
            assert rule["account_id"] == test_account["id"]

    @pytest.mark.asyncio
    async def test_get_rules_unauthorized(self):
        """Test getting rules without authentication."""
        request, response = await app.asgi_client.get("/api/rules")

        assert response.status == 401


# =====================================
# GET /api/rules/active - List Active Rules
# =====================================


class TestRulesGetActive:
    """Test GET /api/rules/active endpoint."""

    @pytest.mark.asyncio
    async def test_get_active_rules(self, auth_headers, multiple_rules):
        """Test getting only active rules."""
        request, response = await app.asgi_client.get(
            "/api/rules/active", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 2  # Only 2 active rules
        for rule in response.json["rules"]:
            assert rule["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_active_rules_empty(self, auth_headers, test_account):
        """Test getting active rules when none exist."""
        request, response = await app.asgi_client.get(
            "/api/rules/active", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["total"] == 0


# =====================================
# POST /api/rules - Create Rule
# =====================================


class TestRulesCreate:
    """Test POST /api/rules endpoint."""

    @pytest.mark.asyncio
    async def test_create_rule_success(self, auth_headers, test_account):
        """Test creating a rule successfully."""
        rule_data = {
            "account_id": str(test_account["id"]),
            "delta_threshold": 0.65,
            "dte_min": 5,
            "dte_max": 7,
            "spread_threshold": 3.5,
            "is_active": True,
        }

        request, response = await app.asgi_client.post(
            "/api/rules", json=rule_data, headers=auth_headers
        )

        assert response.status == 201
        assert response.json["message"] == "Rule created successfully"
        assert response.json["rule"]["delta_threshold"] == "0.6500"
        assert response.json["rule"]["dte_min"] == 5
        assert response.json["rule"]["dte_max"] == 7
        assert response.json["rule"]["is_active"] is True

        # Cleanup
        rule_id = response.json["rule"]["id"]
        supabase.table("roll_rules").delete().eq("id", rule_id).execute()

    @pytest.mark.asyncio
    async def test_create_rule_with_defaults(self, auth_headers, test_account):
        """Test creating a rule with default values."""
        rule_data = {
            "account_id": str(test_account["id"]),
        }

        request, response = await app.asgi_client.post(
            "/api/rules", json=rule_data, headers=auth_headers
        )

        assert response.status == 201
        assert response.json["rule"]["is_active"] is True
        assert response.json["rule"]["delta_threshold"] == "0.6000"

        # Cleanup
        rule_id = response.json["rule"]["id"]
        supabase.table("roll_rules").delete().eq("id", rule_id).execute()

    @pytest.mark.asyncio
    async def test_create_rule_invalid_delta(self, auth_headers, test_account):
        """Test creating a rule with invalid delta (> 1)."""
        rule_data = {
            "account_id": str(test_account["id"]),
            "delta_threshold": 1.5,  # Invalid > 1
        }

        request, response = await app.asgi_client.post(
            "/api/rules", json=rule_data, headers=auth_headers
        )

        assert response.status == 422

    @pytest.mark.asyncio
    async def test_create_rule_unauthorized_account(self, auth_headers):
        """Test creating a rule for account user doesn't own."""
        rule_data = {
            "account_id": str(uuid4()),  # Random UUID
            "delta_threshold": 0.60,
        }

        request, response = await app.asgi_client.post(
            "/api/rules", json=rule_data, headers=auth_headers
        )

        assert response.status == 403


# =====================================
# GET /api/rules/{id} - Get Rule Details
# =====================================


class TestRulesGetDetail:
    """Test GET /api/rules/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_rule_success(self, auth_headers, test_rule):
        """Test getting rule details successfully."""
        request, response = await app.asgi_client.get(
            f"/api/rules/{test_rule['id']}", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["rule"]["id"] == test_rule["id"]
        assert response.json["rule"]["delta_threshold"] == test_rule["delta_threshold"]

    @pytest.mark.asyncio
    async def test_get_rule_not_found(self, auth_headers):
        """Test getting non-existent rule."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.get(
            f"/api/rules/{fake_id}", headers=auth_headers
        )

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_get_rule_unauthorized(self):
        """Test getting rule without authentication."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.get(f"/api/rules/{fake_id}")

        assert response.status == 401


# =====================================
# PUT /api/rules/{id} - Update Rule
# =====================================


class TestRulesUpdate:
    """Test PUT /api/rules/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_rule_success(self, auth_headers, test_rule):
        """Test updating a rule successfully."""
        update_data = {
            "delta_threshold": 0.75,
            "dte_min": 7,
            "is_active": False,
        }

        request, response = await app.asgi_client.put(
            f"/api/rules/{test_rule['id']}", json=update_data, headers=auth_headers
        )

        assert response.status == 200
        assert response.json["message"] == "Rule updated successfully"
        assert response.json["rule"]["delta_threshold"] == "0.7500"
        assert response.json["rule"]["dte_min"] == 7
        assert response.json["rule"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_rule_partial(self, auth_headers, test_rule):
        """Test partial update of rule."""
        update_data = {"dte_max": 10}

        request, response = await app.asgi_client.put(
            f"/api/rules/{test_rule['id']}", json=update_data, headers=auth_headers
        )

        assert response.status == 200
        assert response.json["rule"]["dte_max"] == 10
        # Other fields unchanged
        assert response.json["rule"]["delta_threshold"] == test_rule["delta_threshold"]

    @pytest.mark.asyncio
    async def test_update_rule_not_found(self, auth_headers):
        """Test updating non-existent rule."""
        fake_id = str(uuid4())
        update_data = {"delta_threshold": 0.80}

        request, response = await app.asgi_client.put(
            f"/api/rules/{fake_id}", json=update_data, headers=auth_headers
        )

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_update_rule_empty_data(self, auth_headers, test_rule):
        """Test updating rule with no fields."""
        request, response = await app.asgi_client.put(
            f"/api/rules/{test_rule['id']}", json={}, headers=auth_headers
        )

        assert response.status == 422


# =====================================
# DELETE /api/rules/{id} - Delete Rule
# =====================================


class TestRulesDelete:
    """Test DELETE /api/rules/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_rule_success(self, auth_headers, test_account):
        """Test deleting a rule successfully."""
        # Create rule to delete
        rule_data = {
            "account_id": test_account["id"],
            "delta_threshold": 0.60,
            "is_active": True,
        }
        result = supabase.table("roll_rules").insert(rule_data).execute()
        rule_id = result.data[0]["id"]

        request, response = await app.asgi_client.delete(
            f"/api/rules/{rule_id}", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["message"] == "Rule deleted successfully"

        # Verify deletion
        result = supabase.table("roll_rules").select("*").eq("id", rule_id).execute()
        assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_delete_rule_not_found(self, auth_headers):
        """Test deleting non-existent rule."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.delete(
            f"/api/rules/{fake_id}", headers=auth_headers
        )

        assert response.status == 404


# =====================================
# POST /api/rules/{id}/toggle - Toggle Rule
# =====================================


class TestRulesToggle:
    """Test POST /api/rules/{id}/toggle endpoint."""

    @pytest.mark.asyncio
    async def test_toggle_rule_active_to_inactive(self, auth_headers, test_rule):
        """Test toggling rule from active to inactive."""
        # Ensure rule is active
        assert test_rule["is_active"] is True

        request, response = await app.asgi_client.post(
            f"/api/rules/{test_rule['id']}/toggle", headers=auth_headers
        )

        assert response.status == 200
        assert response.json["message"] == "Rule toggled successfully"
        assert response.json["rule"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_toggle_rule_twice(self, auth_headers, test_rule):
        """Test toggling rule twice returns to original state."""
        original_state = test_rule["is_active"]

        # First toggle
        request, response = await app.asgi_client.post(
            f"/api/rules/{test_rule['id']}/toggle", headers=auth_headers
        )
        assert response.json["rule"]["is_active"] is not original_state

        # Second toggle
        request, response = await app.asgi_client.post(
            f"/api/rules/{test_rule['id']}/toggle", headers=auth_headers
        )
        assert response.json["rule"]["is_active"] is original_state

    @pytest.mark.asyncio
    async def test_toggle_rule_not_found(self, auth_headers):
        """Test toggling non-existent rule."""
        fake_id = str(uuid4())
        request, response = await app.asgi_client.post(
            f"/api/rules/{fake_id}/toggle", headers=auth_headers
        )

        assert response.status == 404
