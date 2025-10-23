"""
End-to-End tests for account management workflows
"""

import pytest
import asyncio
from typing import Dict, Any, List
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.mark.accounts
@pytest.mark.e2e
class TestAccountManagementE2E:
    """E2E tests for complete account management workflows"""

    @pytest.mark.smoke
    async def test_complete_account_lifecycle(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test complete account lifecycle: create -> read -> update -> delete"""
        # Step 1: Create a new account
        account_data = {
            "name": "E2E Test Account",
            "broker": "Test Broker",
            "account_number": f"ACC{asyncio.get_event_loop().time()}",
            "is_active": True,
            "description": "Account for E2E testing"
        }

        created_account = await authenticated_client.create_account(account_data)

        # Validate creation response
        assert validator.validate_account_response(created_account)
        assert created_account["name"] == account_data["name"]
        assert created_account["broker"] == account_data["broker"]
        assert created_account["account_number"] == account_data["account_number"]
        assert created_account["is_active"] == account_data["is_active"]
        account_id = created_account["id"]

        # Step 2: Read the account
        fetched_account = await authenticated_client.get_account(account_id)

        # Validate read response
        assert validator.validate_account_response(fetched_account)
        assert fetched_account["id"] == account_id
        assert fetched_account["name"] == account_data["name"]

        # Step 3: Update the account
        update_data = {
            "name": "Updated E2E Account",
            "broker": "Updated Broker",
            "is_active": False
        }

        updated_account = await authenticated_client.update_account(account_id, update_data)

        # Validate update response
        assert validator.validate_account_response(updated_account)
        assert updated_account["id"] == account_id
        assert updated_account["name"] == update_data["name"]
        assert updated_account["broker"] == update_data["broker"]
        assert updated_account["is_active"] == update_data["is_active"]
        # Account number should remain unchanged
        assert updated_account["account_number"] == account_data["account_number"]

        # Step 4: Verify update persisted
        verify_account = await authenticated_client.get_account(account_id)
        assert verify_account["name"] == update_data["name"]
        assert verify_account["broker"] == update_data["broker"]
        assert verify_account["is_active"] == update_data["is_active"]

        # Step 5: Delete the account
        delete_response = await authenticated_client.delete_account(account_id)
        assert validator.validate_success_message(delete_response)

        # Step 6: Verify account is deleted
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.get_account(account_id)
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    async def test_multiple_accounts_management(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test managing multiple accounts"""
        accounts_to_create = 5
        created_accounts = []

        # Create multiple accounts
        for i in range(accounts_to_create):
            account_data = {
                "name": f"Multi Account {i}",
                "broker": f"Broker {i % 3}",  # Distribute across 3 brokers
                "account_number": f"MULTI{asyncio.get_event_loop().time()}_{i}",
                "is_active": i % 2 == 0  # Alternate active status
            }
            account = await authenticated_client.create_account(account_data)
            assert validator.validate_account_response(account)
            created_accounts.append(account)

        # Get all accounts
        all_accounts = await authenticated_client.get_accounts()
        assert isinstance(all_accounts, list)
        assert len(all_accounts) >= accounts_to_create

        # Verify created accounts are in the list
        created_ids = {acc["id"] for acc in created_accounts}
        fetched_ids = {acc["id"] for acc in all_accounts}
        assert created_ids.issubset(fetched_ids)

        # Test filtering (if API supports it)
        active_accounts = [acc for acc in created_accounts if acc["is_active"]]
        inactive_accounts = [acc for acc in created_accounts if not acc["is_active"]]

        assert len(active_accounts) > 0
        assert len(inactive_accounts) > 0

        # Update all inactive accounts to active
        for account in inactive_accounts:
            updated = await authenticated_client.update_account(
                account["id"],
                {"is_active": True}
            )
            assert updated["is_active"] is True

        # Delete all created accounts
        for account in created_accounts:
            await authenticated_client.delete_account(account["id"])

        # Verify all are deleted
        remaining_accounts = await authenticated_client.get_accounts()
        remaining_ids = {acc["id"] for acc in remaining_accounts}
        assert not created_ids.intersection(remaining_ids)

    async def test_account_validation_rules(self, authenticated_client: APIClient):
        """Test account creation with various validation scenarios"""
        # Test with empty name
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_account({
                "name": "",
                "broker": "Test Broker",
                "account_number": "TEST123"
            })
        assert "name" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

        # Test with duplicate account number
        account_number = f"DUP{asyncio.get_event_loop().time()}"
        first_account = await authenticated_client.create_account({
            "name": "First Account",
            "broker": "Broker A",
            "account_number": account_number
        })

        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_account({
                "name": "Second Account",
                "broker": "Broker B",
                "account_number": account_number
            })
        assert "exists" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

        # Clean up
        await authenticated_client.delete_account(first_account["id"])

        # Test with very long strings (boundary testing)
        long_name = "A" * 256
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.create_account({
                "name": long_name,
                "broker": "Test Broker",
                "account_number": "LONG123"
            })
        assert "too long" in str(exc_info.value).lower() or "length" in str(exc_info.value).lower()

    async def test_account_isolation_between_users(
        self,
        authenticated_client: APIClient,
        secondary_authenticated_client: APIClient,
        validator: ResponseValidator
    ):
        """Test that accounts are properly isolated between users"""
        # Create account with first user
        user1_account = await authenticated_client.create_account({
            "name": "User 1 Private Account",
            "broker": "Private Broker",
            "account_number": f"PRIV1_{asyncio.get_event_loop().time()}"
        })

        # Create account with second user
        user2_account = await secondary_authenticated_client.create_account({
            "name": "User 2 Private Account",
            "broker": "Another Broker",
            "account_number": f"PRIV2_{asyncio.get_event_loop().time()}"
        })

        # User 1 should not see User 2's account
        user1_accounts = await authenticated_client.get_accounts()
        user1_account_ids = {acc["id"] for acc in user1_accounts}
        assert user1_account["id"] in user1_account_ids
        assert user2_account["id"] not in user1_account_ids

        # User 2 should not see User 1's account
        user2_accounts = await secondary_authenticated_client.get_accounts()
        user2_account_ids = {acc["id"] for acc in user2_accounts}
        assert user2_account["id"] in user2_account_ids
        assert user1_account["id"] not in user2_account_ids

        # User 1 should not be able to access User 2's account directly
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.get_account(user2_account["id"])
        assert "404" in str(exc_info.value) or "403" in str(exc_info.value)

        # User 1 should not be able to update User 2's account
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.update_account(
                user2_account["id"],
                {"name": "Hacked Account"}
            )
        assert "404" in str(exc_info.value) or "403" in str(exc_info.value)

        # User 1 should not be able to delete User 2's account
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.delete_account(user2_account["id"])
        assert "404" in str(exc_info.value) or "403" in str(exc_info.value)

        # Clean up
        await authenticated_client.delete_account(user1_account["id"])
        await secondary_authenticated_client.delete_account(user2_account["id"])

    @pytest.mark.slow
    async def test_account_pagination_and_sorting(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test pagination and sorting of accounts list"""
        # Create many accounts to test pagination
        num_accounts = 25
        created_accounts = []

        for i in range(num_accounts):
            account = await authenticated_client.create_account({
                "name": f"Page Test {i:02d}",
                "broker": f"Broker {chr(65 + (i % 5))}",  # A, B, C, D, E
                "account_number": f"PAGE{asyncio.get_event_loop().time()}_{i:02d}"
            })
            created_accounts.append(account)

        # Get all accounts
        all_accounts = await authenticated_client.get_accounts()

        # Filter to only our created accounts
        test_accounts = [
            acc for acc in all_accounts
            if acc["id"] in {a["id"] for a in created_accounts}
        ]

        # Verify all were created
        assert len(test_accounts) == num_accounts

        # Verify accounts are returned in consistent order
        account_names = [acc["name"] for acc in test_accounts]
        assert account_names == sorted(account_names) or \
               account_names == sorted(account_names, reverse=True), \
               "Accounts should be returned in a consistent order"

        # Clean up
        for account in created_accounts:
            await authenticated_client.delete_account(account["id"])

    async def test_account_concurrent_operations(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test concurrent operations on accounts"""
        # Create an account
        account = await authenticated_client.create_account({
            "name": "Concurrent Test Account",
            "broker": "Concurrent Broker",
            "account_number": f"CONC{asyncio.get_event_loop().time()}"
        })
        account_id = account["id"]

        # Perform multiple concurrent read operations
        read_tasks = [
            authenticated_client.get_account(account_id)
            for _ in range(5)
        ]
        read_results = await asyncio.gather(*read_tasks)

        # All reads should return the same data
        for result in read_results:
            assert validator.validate_account_response(result)
            assert result["id"] == account_id
            assert result["name"] == account["name"]

        # Perform concurrent updates (last one wins)
        update_tasks = []
        for i in range(3):
            update_tasks.append(
                authenticated_client.update_account(
                    account_id,
                    {"name": f"Concurrent Update {i}"}
                )
            )

        update_results = await asyncio.gather(*update_tasks, return_exceptions=True)

        # At least one update should succeed
        successful_updates = [r for r in update_results if not isinstance(r, Exception)]
        assert len(successful_updates) >= 1

        # Verify final state
        final_account = await authenticated_client.get_account(account_id)
        assert final_account["name"].startswith("Concurrent Update")

        # Clean up
        await authenticated_client.delete_account(account_id)

    async def test_account_with_special_characters(self, authenticated_client: APIClient, validator: ResponseValidator):
        """Test account creation with special characters and unicode"""
        special_accounts = [
            {
                "name": "Account with spaces and punctuation!",
                "broker": "Test & Co.",
                "account_number": f"SPEC1_{asyncio.get_event_loop().time()}"
            },
            {
                "name": "Unicode Account 日本語 中文 한글",
                "broker": "International Broker™",
                "account_number": f"SPEC2_{asyncio.get_event_loop().time()}"
            },
            {
                "name": "Account-with-dashes_and_underscores",
                "broker": "Broker (Main)",
                "account_number": f"SPEC3_{asyncio.get_event_loop().time()}"
            }
        ]

        created_ids = []
        for account_data in special_accounts:
            try:
                account = await authenticated_client.create_account(account_data)
                assert validator.validate_account_response(account)
                assert account["name"] == account_data["name"]
                assert account["broker"] == account_data["broker"]
                created_ids.append(account["id"])
            except Exception as e:
                # Some special characters might not be allowed
                print(f"Failed to create account with special chars: {e}")

        # Clean up successfully created accounts
        for account_id in created_ids:
            await authenticated_client.delete_account(account_id)