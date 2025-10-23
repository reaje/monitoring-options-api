"""
End-to-End test for complete user journey through the system
"""

import pytest
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteUserJourney:
    """E2E test simulating a complete user journey through the options monitoring system"""

    async def test_complete_options_trader_journey(
        self,
        api_client: APIClient,
        validator: ResponseValidator
    ):
        """
        Complete journey of an options trader:
        1. Register and setup account
        2. Configure trading accounts and assets
        3. Enter option positions
        4. Set up monitoring rules
        5. Manage positions and alerts
        6. Roll options
        7. Close positions and analyze performance
        """

        # ============================================================
        # PHASE 1: User Registration and Initial Setup
        # ============================================================
        print("\n=== PHASE 1: User Registration and Setup ===")

        # Register new user
        user_email = f"trader_{asyncio.get_event_loop().time()}@example.com"
        user_data = {
            "email": user_email,
            "password": "SecureTrader123!",
            "name": "John Options Trader"
        }

        print(f"Registering user: {user_data['name']}")
        user = await api_client.register_user(**user_data)
        assert validator.validate_user_response(user)
        user_id = user["id"]

        # Login
        print("Logging in...")
        login_response = await api_client.login(user_email, user_data["password"])
        assert validator.validate_auth_token_response(login_response)
        assert api_client.is_authenticated()

        # ============================================================
        # PHASE 2: Set Up Trading Accounts
        # ============================================================
        print("\n=== PHASE 2: Setting Up Trading Accounts ===")

        # Create multiple brokerage accounts
        accounts_data = [
            {
                "name": "Main Trading Account",
                "broker": "Interactive Brokers",
                "account_number": f"IB{int(asyncio.get_event_loop().time())}",
                "is_active": True,
                "description": "Primary options trading account"
            },
            {
                "name": "Retirement Account",
                "broker": "TD Ameritrade",
                "account_number": f"TD{int(asyncio.get_event_loop().time())}",
                "is_active": True,
                "description": "IRA account for conservative strategies"
            }
        ]

        accounts = {}
        for acc_data in accounts_data:
            print(f"Creating account: {acc_data['name']}")
            account = await api_client.create_account(acc_data)
            assert validator.validate_account_response(account)
            accounts[acc_data["name"]] = account

        # ============================================================
        # PHASE 3: Configure Assets to Monitor
        # ============================================================
        print("\n=== PHASE 3: Configuring Assets ===")

        # Add popular stocks for options trading
        assets_data = [
            {
                "ticker": f"SPY{int(asyncio.get_event_loop().time()) % 100}",
                "name": "SPDR S&P 500 ETF",
                "type": "ETF",
                "market": "NYSE",
                "sector": "Index"
            },
            {
                "ticker": f"AAPL{int(asyncio.get_event_loop().time()) % 100}",
                "name": "Apple Inc.",
                "type": "STOCK",
                "market": "NASDAQ",
                "sector": "Technology"
            },
            {
                "ticker": f"TSLA{int(asyncio.get_event_loop().time()) % 100}",
                "name": "Tesla Inc.",
                "type": "STOCK",
                "market": "NASDAQ",
                "sector": "Automotive"
            }
        ]

        assets = {}
        for asset_data in assets_data:
            print(f"Adding asset: {asset_data['name']}")
            asset = await api_client.create_asset(asset_data)
            assert validator.validate_asset_response(asset)
            assets[asset_data["ticker"]] = asset

        # ============================================================
        # PHASE 4: Open Option Positions
        # ============================================================
        print("\n=== PHASE 4: Opening Option Positions ===")

        # Simulate realistic option positions
        spy_ticker = list(assets.keys())[0]
        aapl_ticker = list(assets.keys())[1]
        tsla_ticker = list(assets.keys())[2]

        positions = []

        # Strategy 1: Covered Calls on SPY (Main Account)
        print("Opening covered calls on SPY...")
        expiry_30d = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        spy_call = await api_client.create_option({
            "account_id": accounts["Main Trading Account"]["id"],
            "asset_id": assets[spy_ticker]["id"],
            "ticker": f"{spy_ticker}C440",
            "strike": 440.00,
            "expiry": expiry_30d,
            "side": "CALL",
            "strategy": "COVERED_CALL",
            "quantity": -10,  # Sold 10 contracts
            "entry_price": 5.25,
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Monthly income generation"
        })
        positions.append(spy_call)

        # Strategy 2: Cash Secured Put on AAPL (Main Account)
        print("Selling cash secured put on AAPL...")
        aapl_put = await api_client.create_option({
            "account_id": accounts["Main Trading Account"]["id"],
            "asset_id": assets[aapl_ticker]["id"],
            "ticker": f"{aapl_ticker}P170",
            "strike": 170.00,
            "expiry": expiry_30d,
            "side": "PUT",
            "strategy": "SHORT_PUT",
            "quantity": -5,
            "entry_price": 3.50,
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Willing to own AAPL at 170"
        })
        positions.append(aapl_put)

        # Strategy 3: Protective Put on TSLA (Retirement Account)
        print("Buying protective put on TSLA...")
        expiry_45d = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        tsla_put = await api_client.create_option({
            "account_id": accounts["Retirement Account"]["id"],
            "asset_id": assets[tsla_ticker]["id"],
            "ticker": f"{tsla_ticker}P200",
            "strike": 200.00,
            "expiry": expiry_45d,
            "side": "PUT",
            "strategy": "LONG_PUT",
            "quantity": 10,
            "entry_price": 8.00,
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Portfolio protection"
        })
        positions.append(tsla_put)

        print(f"Total positions opened: {len(positions)}")

        # ============================================================
        # PHASE 5: Set Up Monitoring Rules
        # ============================================================
        print("\n=== PHASE 5: Configuring Monitoring Rules ===")

        rules = []

        # Rule 1: Alert when SPY covered call is ITM
        print("Setting up ITM alert for SPY covered call...")
        spy_itm_rule = await api_client.create_rule({
            "name": "SPY Call ITM Alert",
            "description": "Alert when SPY price approaches strike",
            "asset_id": assets[spy_ticker]["id"],
            "asset_ticker": spy_ticker,
            "condition_type": "PRICE_ABOVE",
            "threshold": 435.00,  # Alert at $5 below strike
            "is_active": True,
            "notification_channels": ["email"]
        })
        rules.append(spy_itm_rule)

        # Rule 2: Alert for AAPL put assignment risk
        print("Setting up assignment risk alert for AAPL put...")
        aapl_assignment_rule = await api_client.create_rule({
            "name": "AAPL Put Assignment Risk",
            "description": "Alert when AAPL approaches put strike",
            "asset_id": assets[aapl_ticker]["id"],
            "asset_ticker": aapl_ticker,
            "condition_type": "PRICE_BELOW",
            "threshold": 175.00,  # Alert at $5 above strike
            "is_active": True,
            "notification_channels": ["email", "app"]
        })
        rules.append(aapl_assignment_rule)

        # Rule 3: Expiration reminder
        print("Setting up expiration reminders...")
        expiry_rule = await api_client.create_rule({
            "name": "Options Expiry Reminder",
            "description": "Alert 7 days before expiration",
            "asset_id": assets[spy_ticker]["id"],
            "asset_ticker": spy_ticker,
            "condition_type": "DAYS_TO_EXPIRY",
            "threshold": 7,
            "is_active": True,
            "notification_channels": ["email"]
        })
        rules.append(expiry_rule)

        print(f"Total monitoring rules created: {len(rules)}")

        # ============================================================
        # PHASE 6: Monitor and Manage Positions
        # ============================================================
        print("\n=== PHASE 6: Monitoring and Managing Positions ===")

        # Check current positions
        print("Checking all open positions...")
        all_positions = await api_client.get_options()
        open_positions = [p for p in all_positions if p["status"] == "OPEN"]
        print(f"Open positions: {len(open_positions)}")

        # Check for any alerts
        print("Checking for alerts...")
        try:
            pending_alerts = await api_client.get_alerts(status="pending")
            print(f"Pending alerts: {len(pending_alerts)}")

            # Acknowledge first alert if any
            if pending_alerts:
                alert = pending_alerts[0]
                print(f"Acknowledging alert: {alert.get('message', 'Alert')}")
                await api_client.acknowledge_alert(alert["id"])
        except:
            print("Alert system might not have generated alerts yet")

        # Update position notes (simulating position management)
        print("Updating position notes...")
        for position in positions[:1]:
            await api_client.update_option(
                position["id"],
                {"notes": "Position monitored - no action needed"}
            )

        # ============================================================
        # PHASE 7: Roll an Option Position
        # ============================================================
        print("\n=== PHASE 7: Rolling Option Position ===")

        # Simulate rolling the SPY covered call
        print("Rolling SPY covered call to next month...")

        # Close current position
        print(f"Closing current SPY call position...")
        closed_spy_call = await api_client.close_option(
            positions[0]["id"],
            exit_price=1.50  # Buying back at lower price
        )
        assert closed_spy_call["status"] == "CLOSED"

        # Calculate P&L for closed position
        entry_total = abs(positions[0]["entry_price"] * positions[0]["quantity"] * 100)
        exit_total = abs(1.50 * positions[0]["quantity"] * 100)
        pnl = entry_total - exit_total  # Profit from sold option
        print(f"P&L on closed position: ${pnl:.2f}")

        # Open new position (rolled)
        new_expiry = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        print(f"Opening new SPY call position (rolled)...")
        rolled_spy_call = await api_client.create_option({
            "account_id": accounts["Main Trading Account"]["id"],
            "asset_id": assets[spy_ticker]["id"],
            "ticker": f"{spy_ticker}C445",
            "strike": 445.00,  # Higher strike
            "expiry": new_expiry,  # Further expiration
            "side": "CALL",
            "strategy": "COVERED_CALL",
            "quantity": -10,
            "entry_price": 6.00,  # Collected more premium
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Rolled from previous month"
        })
        print(f"Roll completed - Net credit: ${(6.00 - 1.50) * 10 * 100:.2f}")

        # ============================================================
        # PHASE 8: Close Remaining Positions
        # ============================================================
        print("\n=== PHASE 8: Closing All Positions ===")

        # Close AAPL put (expired worthless - max profit)
        print("Closing AAPL put (expired worthless)...")
        await api_client.close_option(
            positions[1]["id"],
            exit_price=0.05
        )

        # Close TSLA protective put
        print("Closing TSLA protective put...")
        await api_client.close_option(
            positions[2]["id"],
            exit_price=3.00  # Lost value due to time decay
        )

        # Close the rolled SPY position
        print("Closing rolled SPY call...")
        await api_client.close_option(
            rolled_spy_call["id"],
            exit_price=2.00
        )

        # ============================================================
        # PHASE 9: Performance Analysis
        # ============================================================
        print("\n=== PHASE 9: Performance Analysis ===")

        # Get all positions (including closed)
        all_final_positions = await api_client.get_options()

        # Calculate total P&L
        total_pnl = 0
        for position in all_final_positions:
            if position.get("exit_price") is not None:
                entry = position["entry_price"] * abs(position["quantity"]) * 100
                exit = position.get("exit_price", 0) * abs(position["quantity"]) * 100

                if position["quantity"] < 0:  # Sold options
                    position_pnl = entry - exit
                else:  # Bought options
                    position_pnl = exit - entry

                total_pnl += position_pnl
                print(f"Position {position['ticker']}: ${position_pnl:.2f}")

        print(f"\nTotal P&L: ${total_pnl:.2f}")

        # ============================================================
        # PHASE 10: Cleanup and Report
        # ============================================================
        print("\n=== PHASE 10: Final Report and Cleanup ===")

        # Generate summary
        summary = {
            "user": user["name"],
            "accounts_created": len(accounts),
            "assets_monitored": len(assets),
            "total_positions": len(all_final_positions),
            "monitoring_rules": len(rules),
            "total_pnl": round(total_pnl, 2)
        }

        print("\n📊 JOURNEY SUMMARY:")
        print(f"User: {summary['user']}")
        print(f"Trading Accounts: {summary['accounts_created']}")
        print(f"Assets Monitored: {summary['assets_monitored']}")
        print(f"Option Positions: {summary['total_positions']}")
        print(f"Alert Rules: {summary['monitoring_rules']}")
        print(f"Total P&L: ${summary['total_pnl']}")

        # Cleanup (disable rules)
        print("\nDisabling monitoring rules...")
        for rule in rules:
            await api_client.toggle_rule(rule["id"], False)

        # Logout
        print("Logging out...")
        await api_client.logout()

        print("\n✅ Complete user journey test finished successfully!")

        # Final assertions
        assert summary["accounts_created"] == 2
        assert summary["assets_monitored"] == 3
        assert summary["total_positions"] >= 4
        assert summary["monitoring_rules"] == 3

    async def test_multi_user_trading_scenario(
        self,
        api_request_context,
        validator: ResponseValidator
    ):
        """Test scenario with multiple users trading simultaneously"""
        print("\n=== MULTI-USER TRADING SCENARIO ===")

        # Create multiple traders
        traders = []
        for i in range(3):
            client = APIClient(api_request_context, "http://localhost:8000")

            # Register each trader
            user_data = {
                "email": f"multitrader_{i}_{asyncio.get_event_loop().time()}@example.com",
                "password": "MultiTrader123!",
                "name": f"Trader {i + 1}"
            }

            print(f"\nSetting up {user_data['name']}...")
            await client.register_user(**user_data)
            await client.login(user_data["email"], user_data["password"])

            # Each trader creates an account
            account = await client.create_account({
                "name": f"Trading Account {i + 1}",
                "broker": f"Broker {chr(65 + i)}",
                "account_number": f"ACC{i}_{int(asyncio.get_event_loop().time())}",
                "is_active": True
            })

            # Each trader monitors different assets
            asset = await client.create_asset({
                "ticker": f"TRD{i}{int(asyncio.get_event_loop().time()) % 1000}",
                "name": f"Trader {i + 1} Asset",
                "type": "STOCK",
                "market": "TEST"
            })

            traders.append({
                "client": client,
                "user": user_data,
                "account": account,
                "asset": asset
            })

        # Simulate concurrent trading activity
        print("\nSimulating concurrent trading...")
        trading_tasks = []

        for trader in traders:
            async def trade(t):
                # Each trader opens a position
                option = await t["client"].create_option({
                    "account_id": t["account"]["id"],
                    "asset_id": t["asset"]["id"],
                    "ticker": f"{t['asset']['ticker']}OPT",
                    "strike": 100.00,
                    "expiry": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                    "side": "CALL",
                    "strategy": "COVERED_CALL",
                    "quantity": 10,
                    "entry_price": 5.00
                })
                return option

            trading_tasks.append(trade(trader))

        positions = await asyncio.gather(*trading_tasks)

        # Verify all traders successfully opened positions
        assert len(positions) == 3
        for position in positions:
            assert validator.validate_option_response(position)

        print(f"\nAll {len(traders)} traders successfully completed trades")

        # Cleanup
        for trader in traders:
            await trader["client"].logout()

        print("✅ Multi-user scenario completed successfully!")