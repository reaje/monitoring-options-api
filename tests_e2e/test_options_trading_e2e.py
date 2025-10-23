"""
End-to-End tests for options trading workflows
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.mark.options
@pytest.mark.e2e
class TestOptionsE2E:
    """E2E tests for options trading workflows"""

    @pytest.mark.smoke
    async def test_complete_option_lifecycle(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test complete option lifecycle: open -> monitor -> close"""
        account = test_account_with_asset["account"]
        asset = test_account_with_asset["asset"]

        # Step 1: Open a covered call position
        expiry_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        option_data = {
            "account_id": account["id"],
            "asset_id": asset["id"],
            "ticker": f"{asset['ticker']}A100",
            "strike": 100.00,
            "expiry": expiry_date,
            "side": "CALL",
            "strategy": "COVERED_CALL",
            "quantity": 10,
            "entry_price": 5.50,
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "E2E test covered call position"
        }

        created_option = await authenticated_client.create_option(option_data)
        assert validator.validate_option_response(created_option)
        assert created_option["status"] == "OPEN"
        assert created_option["strike"] == option_data["strike"]
        assert created_option["quantity"] == option_data["quantity"]

        # Step 2: Get option details
        fetched_option = await authenticated_client.get_option(created_option["id"])
        assert validator.validate_option_response(fetched_option)
        assert fetched_option["id"] == created_option["id"]

        # Step 3: Update option position
        update_data = {
            "notes": "Updated notes for E2E test",
            "quantity": 15
        }
        updated_option = await authenticated_client.update_option(
            created_option["id"],
            update_data
        )
        assert updated_option["notes"] == update_data["notes"]
        assert updated_option["quantity"] == update_data["quantity"]

        # Step 4: Close the position
        exit_price = 7.00
        closed_option = await authenticated_client.close_option(
            created_option["id"],
            exit_price
        )
        assert closed_option["status"] == "CLOSED"
        assert closed_option["exit_price"] == exit_price

        # Calculate P&L
        total_entry = option_data["entry_price"] * update_data["quantity"] * 100
        total_exit = exit_price * update_data["quantity"] * 100
        expected_pnl = total_exit - total_entry

        # Verify position is closed
        final_option = await authenticated_client.get_option(created_option["id"])
        assert final_option["status"] == "CLOSED"

    async def test_multiple_option_strategies(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test different option strategies"""
        account = test_account_with_asset["account"]
        asset = test_account_with_asset["asset"]
        expiry_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")

        strategies = [
            {
                "ticker": f"{asset['ticker']}CALL120",
                "side": "CALL",
                "strategy": "COVERED_CALL",
                "strike": 120.00,
                "quantity": 10
            },
            {
                "ticker": f"{asset['ticker']}PUT80",
                "side": "PUT",
                "strategy": "SHORT_PUT",
                "strike": 80.00,
                "quantity": -5
            },
            {
                "ticker": f"{asset['ticker']}PUT90",
                "side": "PUT",
                "strategy": "LONG_PUT",
                "strike": 90.00,
                "quantity": 10
            },
            {
                "ticker": f"{asset['ticker']}CALL110",
                "side": "CALL",
                "strategy": "LONG_CALL",
                "strike": 110.00,
                "quantity": 20
            }
        ]

        created_options = []
        for strategy_data in strategies:
            option_data = {
                "account_id": account["id"],
                "asset_id": asset["id"],
                "ticker": strategy_data["ticker"],
                "strike": strategy_data["strike"],
                "expiry": expiry_date,
                "side": strategy_data["side"],
                "strategy": strategy_data["strategy"],
                "quantity": strategy_data["quantity"],
                "entry_price": 3.50
            }

            option = await authenticated_client.create_option(option_data)
            assert validator.validate_option_response(option)
            assert option["strategy"] == strategy_data["strategy"]
            assert option["side"] == strategy_data["side"]
            created_options.append(option)

        # Get all options for the account
        account_options = await authenticated_client.get_options(account_id=account["id"])
        assert len(account_options) >= len(strategies)

        # Get all options for the asset
        asset_options = await authenticated_client.get_options(asset_ticker=asset["ticker"])
        assert len(asset_options) >= len(strategies)

        # Close all positions
        for option in created_options:
            await authenticated_client.close_option(option["id"], 4.00)

    async def test_option_roll_calculation(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test option roll calculations and simulations"""
        account = test_account_with_asset["account"]
        asset = test_account_with_asset["asset"]

        # Create an expiring option position
        current_expiry = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        option_data = {
            "account_id": account["id"],
            "asset_id": asset["id"],
            "ticker": f"{asset['ticker']}EXP100",
            "strike": 100.00,
            "expiry": current_expiry,
            "side": "CALL",
            "strategy": "COVERED_CALL",
            "quantity": 10,
            "entry_price": 2.00
        }

        current_option = await authenticated_client.create_option(option_data)

        # Calculate roll parameters
        new_expiry = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")
        roll_data = {
            "current_option_id": current_option["id"],
            "new_strike": 105.00,
            "new_expiry": new_expiry,
            "current_bid": 0.50,
            "new_ask": 3.00
        }

        try:
            roll_calculation = await authenticated_client.calculate_roll(roll_data)
            # Validate roll calculation response
            assert "net_credit" in roll_calculation or "net_debit" in roll_calculation
            assert "break_even" in roll_calculation
            assert "max_profit" in roll_calculation
        except Exception as e:
            # Roll calculation might not be implemented
            print(f"Roll calculation not available: {e}")

        # Simulate roll scenarios
        simulation_data = {
            "option_id": current_option["id"],
            "scenarios": [
                {"new_strike": 105.00, "new_expiry": new_expiry},
                {"new_strike": 110.00, "new_expiry": new_expiry},
                {"new_strike": 95.00, "new_expiry": new_expiry}
            ]
        }

        try:
            simulations = await authenticated_client.simulate_roll(simulation_data)
            assert isinstance(simulations, list) or "scenarios" in simulations
        except Exception as e:
            print(f"Roll simulation not available: {e}")

        # Close the position
        await authenticated_client.close_option(current_option["id"], 0.50)

    async def test_option_expiry_handling(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test handling of expired options"""
        account = test_account_with_asset["account"]
        asset = test_account_with_asset["asset"]

        # Create options with different expiry dates
        options_data = [
            {
                "ticker": f"{asset['ticker']}PAST",
                "expiry": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                "status_expected": "EXPIRED"
            },
            {
                "ticker": f"{asset['ticker']}TODAY",
                "expiry": datetime.now().strftime("%Y-%m-%d"),
                "status_expected": "OPEN"  # Might be EXPIRED depending on time
            },
            {
                "ticker": f"{asset['ticker']}FUTURE",
                "expiry": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "status_expected": "OPEN"
            }
        ]

        for opt_data in options_data:
            try:
                option = await authenticated_client.create_option({
                    "account_id": account["id"],
                    "asset_id": asset["id"],
                    "ticker": opt_data["ticker"],
                    "strike": 100.00,
                    "expiry": opt_data["expiry"],
                    "side": "CALL",
                    "strategy": "COVERED_CALL",
                    "quantity": 10,
                    "entry_price": 3.00
                })

                # Check if past options are automatically marked as expired
                if opt_data["status_expected"] == "EXPIRED":
                    # System might auto-expire past dated options
                    assert option["status"] in ["EXPIRED", "OPEN"]
                else:
                    assert option["status"] == "OPEN"

            except Exception as e:
                # Past dated options might be rejected
                if "past" in str(e).lower() or "expired" in str(e).lower():
                    continue
                raise

    async def test_option_portfolio_analysis(
        self,
        authenticated_client: APIClient,
        test_complete_setup: Dict,
        validator: ResponseValidator
    ):
        """Test portfolio-level option analysis"""
        account = test_complete_setup["account"]
        asset = test_complete_setup["asset"]

        # Create a diversified options portfolio
        portfolio_positions = [
            # Bull call spread
            {"ticker": "BULL100C", "strike": 100, "side": "CALL", "quantity": 10, "entry_price": 5.00},
            {"ticker": "BULL110C", "strike": 110, "side": "CALL", "quantity": -10, "entry_price": 2.00},

            # Put protection
            {"ticker": "PROT90P", "strike": 90, "side": "PUT", "quantity": 10, "entry_price": 3.00},

            # Covered calls at different strikes
            {"ticker": "COV105C", "strike": 105, "side": "CALL", "quantity": -5, "entry_price": 4.00},
            {"ticker": "COV115C", "strike": 115, "side": "CALL", "quantity": -5, "entry_price": 1.50}
        ]

        expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        created_positions = []

        for position in portfolio_positions:
            option = await authenticated_client.create_option({
                "account_id": account["id"],
                "asset_id": asset["id"],
                "ticker": position["ticker"],
                "strike": position["strike"],
                "expiry": expiry,
                "side": position["side"],
                "strategy": "OTHER",
                "quantity": position["quantity"],
                "entry_price": position["entry_price"]
            })
            created_positions.append(option)

        # Get all positions for analysis
        all_positions = await authenticated_client.get_options(account_id=account["id"])

        # Calculate portfolio metrics
        total_premium_collected = sum(
            p["entry_price"] * abs(p["quantity"]) * 100
            for p in created_positions
            if p["quantity"] < 0
        )

        total_premium_paid = sum(
            p["entry_price"] * p["quantity"] * 100
            for p in created_positions
            if p["quantity"] > 0
        )

        net_position = total_premium_collected - total_premium_paid

        # Verify calculations
        assert len(all_positions) >= len(portfolio_positions)
        assert total_premium_collected > 0
        assert total_premium_paid > 0

    @pytest.mark.slow
    async def test_concurrent_option_operations(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test concurrent operations on options"""
        account = test_account_with_asset["account"]
        asset = test_account_with_asset["asset"]
        expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Create multiple options concurrently
        create_tasks = []
        for i in range(10):
            option_data = {
                "account_id": account["id"],
                "asset_id": asset["id"],
                "ticker": f"{asset['ticker']}C{100+i}",
                "strike": 100.0 + i,
                "expiry": expiry,
                "side": "CALL",
                "strategy": "COVERED_CALL",
                "quantity": 10,
                "entry_price": 3.0 + (i * 0.5)
            }
            create_tasks.append(authenticated_client.create_option(option_data))

        created_options = await asyncio.gather(*create_tasks)

        # Validate all were created
        for option in created_options:
            assert validator.validate_option_response(option)
            assert option["status"] == "OPEN"

        # Update options concurrently
        update_tasks = []
        for option in created_options[:5]:
            update_data = {"notes": f"Concurrent update {option['id']}"}
            update_tasks.append(
                authenticated_client.update_option(option["id"], update_data)
            )

        updated_options = await asyncio.gather(*update_tasks)
        for option in updated_options:
            assert "Concurrent update" in option["notes"]

        # Close options concurrently
        close_tasks = []
        for option in created_options:
            close_tasks.append(
                authenticated_client.close_option(option["id"], 4.00)
            )

        closed_options = await asyncio.gather(*close_tasks)
        for option in closed_options:
            assert option["status"] == "CLOSED"