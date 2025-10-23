"""Integration tests for assets API."""

import pytest


@pytest.mark.asyncio
class TestAssetsList:
    """Test list assets endpoint."""

    async def test_list_assets_empty(self, test_client, auth_headers, test_account):
        """Test listing assets when none exist."""
        _, response = await test_client.get(
            f"/api/assets?account_id={test_account['id']}",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "assets" in data
        assert data["total"] == 0

    async def test_list_assets_multiple(
        self,
        test_client,
        auth_headers,
        multiple_assets
    ):
        """Test listing multiple assets."""
        _, response = await test_client.get(
            "/api/assets",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "assets" in data
        assert data["total"] == 3
        assert len(data["assets"]) == 3

    async def test_list_assets_by_account(
        self,
        test_client,
        auth_headers,
        test_account,
        multiple_assets
    ):
        """Test listing assets filtered by account."""
        account_id = test_account["id"]

        _, response = await test_client.get(
            f"/api/assets?account_id={account_id}",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "assets" in data
        assert data["total"] == 3
        # All assets should belong to this account
        for asset in data["assets"]:
            assert asset["account_id"] == account_id

    async def test_list_assets_unauthenticated(self, test_client):
        """Test listing assets without authentication."""
        _, response = await test_client.get("/api/assets")

        assert response.status == 401


@pytest.mark.asyncio
class TestAssetsCreate:
    """Test create asset endpoint."""

    async def test_create_asset_success(
        self,
        test_client,
        auth_headers,
        test_account
    ):
        """Test successful asset creation."""
        _, response = await test_client.post(
            "/api/assets",
            headers=auth_headers,
            json={
                "ticker": "PETR4",
                "account_id": test_account["id"],
            },
        )

        assert response.status == 201
        data = response.json
        assert "asset" in data
        assert data["asset"]["ticker"] == "PETR4"
        assert data["asset"]["account_id"] == test_account["id"]
        assert "id" in data["asset"]

    async def test_create_asset_duplicate_ticker(
        self,
        test_client,
        auth_headers,
        test_asset
    ):
        """Test creating asset with duplicate ticker in same account."""
        _, response = await test_client.post(
            "/api/assets",
            headers=auth_headers,
            json={
                "ticker": test_asset["ticker"],
                "account_id": test_asset["account_id"],
            },
        )

        assert response.status == 422
        data = response.json
        assert "error" in data

    async def test_create_asset_missing_ticker(
        self,
        test_client,
        auth_headers,
        test_account
    ):
        """Test creating asset without ticker."""
        _, response = await test_client.post(
            "/api/assets",
            headers=auth_headers,
            json={"account_id": test_account["id"]},
        )

        assert response.status == 422

    async def test_create_asset_unauthenticated(self, test_client, test_account):
        """Test creating asset without authentication."""
        _, response = await test_client.post(
            "/api/assets",
            json={
                "ticker": "VALE3",
                "account_id": test_account["id"],
            },
        )

        assert response.status == 401


@pytest.mark.asyncio
class TestAssetsGet:
    """Test get asset endpoint."""

    async def test_get_asset_success(
        self,
        test_client,
        auth_headers,
        test_asset
    ):
        """Test getting existing asset."""
        asset_id = test_asset["id"]

        _, response = await test_client.get(
            f"/api/assets/{asset_id}",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "asset" in data
        assert data["asset"]["id"] == asset_id
        assert data["asset"]["ticker"] == test_asset["ticker"]

    async def test_get_asset_not_found(self, test_client, auth_headers):
        """Test getting nonexistent asset."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"

        _, response = await test_client.get(
            f"/api/assets/{fake_id}",
            headers=auth_headers,
        )

        assert response.status == 404

    async def test_get_asset_unauthenticated(self, test_client, test_asset):
        """Test getting asset without authentication."""
        asset_id = test_asset["id"]

        _, response = await test_client.get(f"/api/assets/{asset_id}")

        assert response.status == 401


@pytest.mark.asyncio
class TestAssetsUpdate:
    """Test update asset endpoint."""

    async def test_update_asset_success(
        self,
        test_client,
        auth_headers,
        test_asset
    ):
        """Test successful asset update."""
        asset_id = test_asset["id"]

        _, response = await test_client.put(
            f"/api/assets/{asset_id}",
            headers=auth_headers,
            json={"ticker": "VALE3"},
        )

        assert response.status == 200
        data = response.json
        assert data["asset"]["ticker"] == "VALE3"
        assert data["asset"]["id"] == asset_id

    async def test_update_asset_duplicate_ticker(
        self,
        test_client,
        auth_headers,
        multiple_assets
    ):
        """Test updating asset to duplicate ticker."""
        # Try to update first asset to second asset's ticker
        asset_id = multiple_assets[0]["id"]
        duplicate_ticker = multiple_assets[1]["ticker"]

        _, response = await test_client.put(
            f"/api/assets/{asset_id}",
            headers=auth_headers,
            json={"ticker": duplicate_ticker},
        )

        assert response.status == 422

    async def test_update_asset_not_found(self, test_client, auth_headers):
        """Test updating nonexistent asset."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"

        _, response = await test_client.put(
            f"/api/assets/{fake_id}",
            headers=auth_headers,
            json={"ticker": "VALE3"},
        )

        assert response.status == 404

    async def test_update_asset_empty_data(
        self,
        test_client,
        auth_headers,
        test_asset
    ):
        """Test updating asset with no data."""
        asset_id = test_asset["id"]

        _, response = await test_client.put(
            f"/api/assets/{asset_id}",
            headers=auth_headers,
            json={},
        )

        assert response.status == 422

    async def test_update_asset_unauthenticated(self, test_client, test_asset):
        """Test updating asset without authentication."""
        asset_id = test_asset["id"]

        _, response = await test_client.put(
            f"/api/assets/{asset_id}",
            json={"ticker": "VALE3"},
        )

        assert response.status == 401


@pytest.mark.asyncio
class TestAssetsDelete:
    """Test delete asset endpoint."""

    async def test_delete_asset_success(
        self,
        test_client,
        auth_headers,
        test_asset
    ):
        """Test successful asset deletion."""
        asset_id = test_asset["id"]

        _, response = await test_client.delete(
            f"/api/assets/{asset_id}",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert data["message"] == "Asset deleted successfully"

        # Verify asset is deleted
        _, get_response = await test_client.get(
            f"/api/assets/{asset_id}",
            headers=auth_headers,
        )
        assert get_response.status == 404

    async def test_delete_asset_not_found(self, test_client, auth_headers):
        """Test deleting nonexistent asset."""
        fake_id = "123e4567-e89b-12d3-a456-426614174000"

        _, response = await test_client.delete(
            f"/api/assets/{fake_id}",
            headers=auth_headers,
        )

        assert response.status == 404

    async def test_delete_asset_unauthenticated(self, test_client, test_asset):
        """Test deleting asset without authentication."""
        asset_id = test_asset["id"]

        _, response = await test_client.delete(f"/api/assets/{asset_id}")

        assert response.status == 401
