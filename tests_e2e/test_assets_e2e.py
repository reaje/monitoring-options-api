"""
End-to-End tests for asset management workflows
"""

import pytest
import asyncio
from typing import Dict, Any, List
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.mark.assets
@pytest.mark.e2e
class TestAssetManagementE2E:
    """E2E tests for complete asset management workflows"""

    @pytest.mark.smoke
    async def test_complete_asset_lifecycle(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test complete asset lifecycle: create -> read -> update -> delete"""
        # Step 1: Create a new asset
        asset_data = {
            "ticker": f"TEST{int(asyncio.get_event_loop().time()) % 10000}",
            "name": "E2E Test Asset",
            "type": "STOCK",
            "market": "BOVESPA",
            "sector": "Technology",
            "description": "Asset for E2E testing"
        }

        created_asset = await authenticated_client.create_asset(asset_data)

        # Validate creation response
        assert validator.validate_asset_response(created_asset)
        assert created_asset["ticker"] == asset_data["ticker"]
        assert created_asset["name"] == asset_data["name"]
        assert created_asset["type"] == asset_data["type"]
        asset_id = created_asset["id"]

        # Step 2: Read the asset
        fetched_asset = await authenticated_client.get_asset(asset_id)

        # Validate read response
        assert validator.validate_asset_response(fetched_asset)
        assert fetched_asset["id"] == asset_id
        assert fetched_asset["ticker"] == asset_data["ticker"]
        assert fetched_asset["name"] == asset_data["name"]

        # Step 3: Update the asset
        update_data = {
            "name": "Updated E2E Asset",
            "sector": "Finance",
            "description": "Updated description"
        }

        updated_asset = await authenticated_client.update_asset(asset_id, update_data)

        # Validate update response
        assert validator.validate_asset_response(updated_asset)
        assert updated_asset["id"] == asset_id
        assert updated_asset["name"] == update_data["name"]
        # Ticker should remain unchanged
        assert updated_asset["ticker"] == asset_data["ticker"]
        assert updated_asset["type"] == asset_data["type"]

        # Step 4: Verify update persisted
        verify_asset = await authenticated_client.get_asset(asset_id)
        assert verify_asset["name"] == update_data["name"]

        # Step 5: Delete the asset
        delete_response = await authenticated_client.delete_asset(asset_id)
        assert validator.validate_success_message(delete_response)

        # Step 6: Verify asset is deleted
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.get_asset(asset_id)
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    async def test_multiple_asset_types(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test creating and managing different asset types"""
        asset_types = [
            {
                "ticker": f"STK{int(asyncio.get_event_loop().time()) % 1000}",
                "name": "Test Stock",
                "type": "STOCK",
                "market": "BOVESPA"
            },
            {
                "ticker": f"ETF{int(asyncio.get_event_loop().time()) % 1000}",
                "name": "Test ETF",
                "type": "ETF",
                "market": "B3"
            },
            {
                "ticker": f"FII{int(asyncio.get_event_loop().time()) % 1000}",
                "name": "Test Real Estate Fund",
                "type": "FII",
                "market": "B3"
            },
            {
                "ticker": f"BDR{int(asyncio.get_event_loop().time()) % 1000}",
                "name": "Test BDR",
                "type": "BDR",
                "market": "B3"
            }
        ]

        created_assets = []

        # Create assets of different types
        for asset_data in asset_types:
            asset = await authenticated_client.create_asset(asset_data)
            assert validator.validate_asset_response(asset)
            assert asset["type"] == asset_data["type"]
            created_assets.append(asset)

        # Get all assets
        all_assets = await authenticated_client.get_assets()
        assert isinstance(all_assets, list)

        # Verify all types are represented
        created_ids = {asset["id"] for asset in created_assets}
        fetched_assets = [a for a in all_assets if a["id"] in created_ids]
        assert len(fetched_assets) == len(created_assets)

        fetched_types = {asset["type"] for asset in fetched_assets}
        expected_types = {"STOCK", "ETF", "FII", "BDR"}
        assert fetched_types == expected_types

        # Clean up
        for asset in created_assets:
            await authenticated_client.delete_asset(asset["id"])

    async def test_asset_ticker_validation(self, authenticated_client: APIClient):
        """Test asset ticker validation rules"""
        # Test with empty ticker
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_asset({
                "ticker": "",
                "name": "Empty Ticker Asset",
                "type": "STOCK"
            })
        assert "ticker" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

        # Test with duplicate ticker
        unique_ticker = f"DUP{int(asyncio.get_event_loop().time())}"
        first_asset = await authenticated_client.create_asset({
            "ticker": unique_ticker,
            "name": "First Asset",
            "type": "STOCK"
        })

        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_asset({
                "ticker": unique_ticker,
                "name": "Second Asset",
                "type": "STOCK"
            })
        assert "exists" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

        # Clean up
        await authenticated_client.delete_asset(first_asset["id"])

        # Test with special characters in ticker
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_asset({
                "ticker": "TEST@#$",
                "name": "Invalid Ticker",
                "type": "STOCK"
            })
        assert "invalid" in str(exc_info.value).lower() or "ticker" in str(exc_info.value).lower()

        # Test with very long ticker
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_asset({
                "ticker": "A" * 50,
                "name": "Long Ticker",
                "type": "STOCK"
            })
        assert "too long" in str(exc_info.value).lower() or "length" in str(exc_info.value).lower()

    async def test_asset_search_and_filtering(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test searching and filtering assets"""
        # Create assets with different characteristics
        test_assets = [
            {
                "ticker": f"PETR{int(asyncio.get_event_loop().time()) % 100}",
                "name": "Petrobras Test",
                "type": "STOCK",
                "market": "BOVESPA",
                "sector": "Energy"
            },
            {
                "ticker": f"VALE{int(asyncio.get_event_loop().time()) % 100}",
                "name": "Vale Test",
                "type": "STOCK",
                "market": "BOVESPA",
                "sector": "Mining"
            },
            {
                "ticker": f"ITUB{int(asyncio.get_event_loop().time()) % 100}",
                "name": "Itau Test",
                "type": "STOCK",
                "market": "BOVESPA",
                "sector": "Finance"
            },
            {
                "ticker": f"BOVA{int(asyncio.get_event_loop().time()) % 100}",
                "name": "Bovespa Index",
                "type": "ETF",
                "market": "B3",
                "sector": "Index"
            }
        ]

        created_assets = []
        for asset_data in test_assets:
            asset = await authenticated_client.create_asset(asset_data)
            created_assets.append(asset)

        # Get all assets
        all_assets = await authenticated_client.get_assets()

        # Filter our test assets
        test_asset_ids = {a["id"] for a in created_assets}
        filtered_assets = [a for a in all_assets if a["id"] in test_asset_ids]

        # Verify we can find our assets
        assert len(filtered_assets) == len(created_assets)

        # Verify different asset types
        stocks = [a for a in filtered_assets if a["type"] == "STOCK"]
        etfs = [a for a in filtered_assets if a["type"] == "ETF"]
        assert len(stocks) == 3
        assert len(etfs) == 1

        # Clean up
        for asset in created_assets:
            await authenticated_client.delete_asset(asset["id"])

    @pytest.mark.slow
    async def test_bulk_asset_operations(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test bulk operations on assets"""
        num_assets = 20
        created_assets = []

        # Bulk create assets
        create_tasks = []
        for i in range(num_assets):
            asset_data = {
                "ticker": f"BULK{int(asyncio.get_event_loop().time())}_{i:02d}",
                "name": f"Bulk Asset {i:02d}",
                "type": "STOCK" if i % 2 == 0 else "ETF",
                "market": "TEST_MARKET"
            }
            create_tasks.append(authenticated_client.create_asset(asset_data))

        # Execute all creates concurrently
        created_assets = await asyncio.gather(*create_tasks)

        # Validate all were created successfully
        for asset in created_assets:
            assert validator.validate_asset_response(asset)

        # Get all assets to verify
        all_assets = await authenticated_client.get_assets()
        created_ids = {a["id"] for a in created_assets}
        fetched_ids = {a["id"] for a in all_assets}
        assert created_ids.issubset(fetched_ids)

        # Bulk update assets
        update_tasks = []
        for asset in created_assets[:10]:  # Update first half
            update_data = {"name": f"Updated {asset['name']}"}
            update_tasks.append(
                authenticated_client.update_asset(asset["id"], update_data)
            )

        updated_assets = await asyncio.gather(*update_tasks)
        for asset in updated_assets:
            assert "Updated" in asset["name"]

        # Bulk delete assets
        delete_tasks = []
        for asset in created_assets:
            delete_tasks.append(authenticated_client.delete_asset(asset["id"]))

        await asyncio.gather(*delete_tasks)

        # Verify all deleted
        remaining_assets = await authenticated_client.get_assets()
        remaining_ids = {a["id"] for a in remaining_assets}
        assert not created_ids.intersection(remaining_ids)

    async def test_asset_with_market_data_integration(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test asset integration with market data"""
        # Create a real-world like asset
        asset_data = {
            "ticker": f"MKTTEST{int(asyncio.get_event_loop().time())}",
            "name": "Market Test Asset",
            "type": "STOCK",
            "market": "BOVESPA",
            "sector": "Technology"
        }

        asset = await authenticated_client.create_asset(asset_data)
        assert validator.validate_asset_response(asset)

        # Try to get market quote for the asset (may fail if market data provider doesn't have it)
        try:
            quote = await authenticated_client.get_market_quote(asset["ticker"])
            # If successful, validate the response structure
            assert "price" in quote or "last" in quote
            assert "timestamp" in quote or "date" in quote
        except Exception as e:
            # Market data might not be available for test tickers
            print(f"Market data not available for test ticker: {e}")

        # Try to get market history
        try:
            history = await authenticated_client.get_market_history(asset["ticker"], days=7)
            if history:
                assert isinstance(history, list)
                for data_point in history[:1]:  # Check first data point
                    assert "date" in data_point or "timestamp" in data_point
                    assert "price" in data_point or "close" in data_point
        except Exception as e:
            print(f"Market history not available for test ticker: {e}")

        # Clean up
        await authenticated_client.delete_asset(asset["id"])

    async def test_asset_relationships(self, authenticated_client: APIClient, test_account_data: Dict, validator: ResponseValidator):
        """Test relationships between assets and other entities"""
        # Create an account
        account = await authenticated_client.create_account(test_account_data)

        # Create an asset
        asset_data = {
            "ticker": f"REL{int(asyncio.get_event_loop().time())}",
            "name": "Relationship Test Asset",
            "type": "STOCK",
            "market": "TEST"
        }
        asset = await authenticated_client.create_asset(asset_data)

        # Create an option position linked to the asset
        option_data = {
            "account_id": account["id"],
            "asset_id": asset["id"],
            "ticker": f"{asset['ticker']}A100",
            "strike": 100.00,
            "expiry": "2025-12-31",
            "side": "CALL",
            "strategy": "COVERED_CALL",
            "quantity": 10,
            "entry_price": 5.00
        }

        option = await authenticated_client.create_option(option_data)
        assert validator.validate_option_response(option)
        assert option["asset_id"] == asset["id"]

        # Try to delete asset with existing option position (should fail)
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.delete_asset(asset["id"])
        assert "constraint" in str(exc_info.value).lower() or "in use" in str(exc_info.value).lower()

        # Close the option position
        await authenticated_client.close_option(option["id"], exit_price=6.00)

        # Now should be able to delete the asset
        delete_response = await authenticated_client.delete_asset(asset["id"])
        assert validator.validate_success_message(delete_response)

        # Clean up
        await authenticated_client.delete_account(account["id"])

    async def test_asset_data_consistency(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test data consistency for asset operations"""
        # Create an asset
        asset_data = {
            "ticker": f"CONS{int(asyncio.get_event_loop().time())}",
            "name": "Consistency Test",
            "type": "STOCK",
            "market": "TEST",
            "sector": "Testing"
        }
        asset = await authenticated_client.create_asset(asset_data)

        # Perform multiple rapid updates
        updates = [
            {"name": "Update 1"},
            {"name": "Update 2"},
            {"name": "Update 3"},
            {"name": "Final Update"}
        ]

        for update_data in updates:
            updated = await authenticated_client.update_asset(asset["id"], update_data)
            assert updated["name"] == update_data["name"]

        # Verify final state
        final_asset = await authenticated_client.get_asset(asset["id"])
        assert final_asset["name"] == "Final Update"
        # Verify immutable fields haven't changed
        assert final_asset["ticker"] == asset_data["ticker"]
        assert final_asset["type"] == asset_data["type"]
        assert final_asset["id"] == asset["id"]

        # Clean up
        await authenticated_client.delete_asset(asset["id"])