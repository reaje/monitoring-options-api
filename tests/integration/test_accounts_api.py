"""Integration tests for accounts API."""

import pytest


@pytest.mark.asyncio
class TestAccountsList:
    """Test list accounts endpoint."""

    async def test_list_accounts_empty(self, test_client, auth_headers):
        """Test listing accounts when none exist."""
        _, response = await test_client.get(
            "/api/accounts",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "accounts" in data
        assert data["total"] == 0
        assert len(data["accounts"]) == 0

    async def test_list_accounts_multiple(
        self,
        test_client,
        auth_headers,
        multiple_accounts
    ):
        """Test listing multiple accounts."""
        _, response = await test_client.get(
            "/api/accounts",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "accounts" in data
        assert data["total"] == 3
        assert len(data["accounts"]) == 3

    async def test_list_accounts_unauthenticated(self, test_client):
        """Test listing accounts without authentication."""
        _, response = await test_client.get("/api/accounts")

        assert response.status == 401


@pytest.mark.asyncio
class TestAccountsCreate:
    """Test create account endpoint."""

    async def test_create_account_success(self, test_client, auth_headers):
        """Test successful account creation."""
        _, response = await test_client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "My New Account"},
        )

        assert response.status == 201
        data = response.json
        assert "account" in data
        assert data["account"]["name"] == "My New Account"
        assert "id" in data["account"]
        assert "user_id" in data["account"]

    async def test_create_account_missing_name(self, test_client, auth_headers):
        """Test account creation without name."""
        _, response = await test_client.post(
            "/api/accounts",
            headers=auth_headers,
            json={},
        )

        assert response.status == 422

    async def test_create_account_unauthenticated(self, test_client):
        """Test account creation without authentication."""
        _, response = await test_client.post(
            "/api/accounts",
            json={"name": "New Account"},
        )

        assert response.status == 401


@pytest.mark.asyncio
class TestAccountsGet:
    """Test get account endpoint."""

    async def test_get_account_success(
        self,
        test_client,
        auth_headers,
        test_account
    ):
        """Test getting existing account."""
        account_id = test_account["id"]

        _, response = await test_client.get(
            f"/api/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "account" in data
        assert data["account"]["id"] == account_id
        assert data["account"]["name"] == test_account["name"]

    async def test_get_account_not_found(self, test_client, auth_headers):
        """Test getting nonexistent account."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"

        _, response = await test_client.get(
            f"/api/accounts/{fake_id}",
            headers=auth_headers,
        )

        assert response.status == 404

    async def test_get_account_unauthenticated(self, test_client, test_account):
        """Test getting account without authentication."""
        account_id = test_account["id"]

        _, response = await test_client.get(f"/api/accounts/{account_id}")

        assert response.status == 401


@pytest.mark.asyncio
class TestAccountsUpdate:
    """Test update account endpoint."""

    async def test_update_account_success(
        self,
        test_client,
        auth_headers,
        test_account
    ):
        """Test successful account update."""
        account_id = test_account["id"]

        _, response = await test_client.put(
            f"/api/accounts/{account_id}",
            headers=auth_headers,
            json={"name": "Updated Account Name"},
        )

        assert response.status == 200
        data = response.json
        assert data["account"]["name"] == "Updated Account Name"
        assert data["account"]["id"] == account_id

    async def test_update_account_not_found(self, test_client, auth_headers):
        """Test updating nonexistent account."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"

        _, response = await test_client.put(
            f"/api/accounts/{fake_id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )

        assert response.status == 404

    async def test_update_account_empty_data(
        self,
        test_client,
        auth_headers,
        test_account
    ):
        """Test updating account with no data."""
        account_id = test_account["id"]

        _, response = await test_client.put(
            f"/api/accounts/{account_id}",
            headers=auth_headers,
            json={},
        )

        assert response.status == 422

    async def test_update_account_unauthenticated(self, test_client, test_account):
        """Test updating account without authentication."""
        account_id = test_account["id"]

        _, response = await test_client.put(
            f"/api/accounts/{account_id}",
            json={"name": "New Name"},
        )

        assert response.status == 401


@pytest.mark.asyncio
class TestAccountsDelete:
    """Test delete account endpoint."""

    async def test_delete_account_success(
        self,
        test_client,
        auth_headers,
        test_account
    ):
        """Test successful account deletion."""
        account_id = test_account["id"]

        _, response = await test_client.delete(
            f"/api/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert data["message"] == "Account deleted successfully"

        # Verify account is deleted
        _, get_response = await test_client.get(
            f"/api/accounts/{account_id}",
            headers=auth_headers,
        )
        assert get_response.status == 404

    async def test_delete_account_not_found(self, test_client, auth_headers):
        """Test deleting nonexistent account."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"

        _, response = await test_client.delete(
            f"/api/accounts/{fake_id}",
            headers=auth_headers,
        )

        assert response.status == 404

    async def test_delete_account_unauthenticated(self, test_client, test_account):
        """Test deleting account without authentication."""
        account_id = test_account["id"]

        _, response = await test_client.delete(f"/api/accounts/{account_id}")

        assert response.status == 401
