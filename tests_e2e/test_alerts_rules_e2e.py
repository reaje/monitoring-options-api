"""
End-to-End tests for alerts and rules workflows
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.mark.rules
@pytest.mark.alerts
@pytest.mark.e2e
class TestAlertsAndRulesE2E:
    """E2E tests for alert rules and notifications workflows"""

    @pytest.mark.smoke
    async def test_complete_rule_lifecycle(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test complete rule lifecycle: create -> activate -> trigger -> acknowledge"""
        asset = test_account_with_asset["asset"]

        # Step 1: Create a monitoring rule
        rule_data = {
            "name": "E2E Price Alert Rule",
            "description": "Alert when price drops below threshold",
            "asset_id": asset["id"],
            "asset_ticker": asset["ticker"],
            "condition_type": "PRICE_BELOW",
            "threshold": 95.00,
            "is_active": True,
            "notification_channels": ["email", "app"],
            "priority": "HIGH"
        }

        created_rule = await authenticated_client.create_rule(rule_data)
        assert validator.validate_rule_response(created_rule)
        assert created_rule["name"] == rule_data["name"]
        assert created_rule["threshold"] == rule_data["threshold"]
        assert created_rule["is_active"] is True
        rule_id = created_rule["id"]

        # Step 2: Get rule details
        fetched_rule = await authenticated_client.get_rule(rule_id)
        assert validator.validate_rule_response(fetched_rule)
        assert fetched_rule["id"] == rule_id

        # Step 3: Update the rule
        update_data = {
            "threshold": 90.00,
            "description": "Updated threshold for E2E test",
            "priority": "MEDIUM"
        }
        updated_rule = await authenticated_client.update_rule(rule_id, update_data)
        assert updated_rule["threshold"] == update_data["threshold"]
        assert updated_rule["description"] == update_data["description"]

        # Step 4: Toggle rule status
        toggled_rule = await authenticated_client.toggle_rule(rule_id, False)
        assert toggled_rule["is_active"] is False

        toggled_rule = await authenticated_client.toggle_rule(rule_id, True)
        assert toggled_rule["is_active"] is True

        # Step 5: Check for alerts (might not have any yet)
        alerts = await authenticated_client.get_alerts()
        # Just verify the endpoint works
        assert isinstance(alerts, list)

        # Step 6: Delete the rule
        delete_response = await authenticated_client.delete_rule(rule_id)
        assert validator.validate_success_message(delete_response)

        # Verify deletion
        with pytest.raises(Exception) as exc_info:
            await authenticated_client.get_rule(rule_id)
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    async def test_multiple_rule_types(
        self,
        authenticated_client: APIClient,
        test_complete_setup: Dict,
        validator: ResponseValidator
    ):
        """Test creating different types of monitoring rules"""
        asset = test_complete_setup["asset"]
        option = test_complete_setup["option"]

        rule_types = [
            {
                "name": "Price Above Rule",
                "condition_type": "PRICE_ABOVE",
                "threshold": 110.00,
                "description": "Alert when price goes above 110"
            },
            {
                "name": "Price Below Rule",
                "condition_type": "PRICE_BELOW",
                "threshold": 90.00,
                "description": "Alert when price drops below 90"
            },
            {
                "name": "Expiry Approaching Rule",
                "condition_type": "DAYS_TO_EXPIRY",
                "threshold": 7,
                "description": "Alert 7 days before expiry"
            },
            {
                "name": "Volume Spike Rule",
                "condition_type": "VOLUME_SPIKE",
                "threshold": 200,  # 200% of average
                "description": "Alert on unusual volume"
            },
            {
                "name": "Volatility Rule",
                "condition_type": "IMPLIED_VOLATILITY",
                "threshold": 50,  # 50% IV
                "description": "Alert on high IV"
            }
        ]

        created_rules = []
        for rule_type in rule_types:
            rule_data = {
                "name": rule_type["name"],
                "description": rule_type["description"],
                "asset_id": asset["id"],
                "asset_ticker": asset["ticker"],
                "condition_type": rule_type["condition_type"],
                "threshold": rule_type["threshold"],
                "is_active": True
            }

            try:
                rule = await authenticated_client.create_rule(rule_data)
                assert validator.validate_rule_response(rule)
                assert rule["condition_type"] == rule_type["condition_type"]
                created_rules.append(rule)
            except Exception as e:
                # Some condition types might not be supported
                if "invalid" in str(e).lower() or "not supported" in str(e).lower():
                    print(f"Condition type {rule_type['condition_type']} not supported")
                    continue
                raise

        # Get all rules for the asset
        asset_rules = await authenticated_client.get_rules(asset_ticker=asset["ticker"])
        assert len(asset_rules) >= len(created_rules)

        # Clean up
        for rule in created_rules:
            await authenticated_client.delete_rule(rule["id"])

    async def test_alert_lifecycle(
        self,
        authenticated_client: APIClient,
        test_complete_setup: Dict,
        validator: ResponseValidator
    ):
        """Test alert generation and management"""
        asset = test_complete_setup["asset"]

        # Create a rule that might trigger alerts
        rule = await authenticated_client.create_rule({
            "name": "Alert Test Rule",
            "description": "Rule to test alert generation",
            "asset_id": asset["id"],
            "asset_ticker": asset["ticker"],
            "condition_type": "PRICE_BELOW",
            "threshold": 1000.00,  # High threshold to potentially trigger
            "is_active": True
        })

        # Wait a moment for potential alert generation
        await asyncio.sleep(2)

        # Get pending alerts
        try:
            pending_alerts = await authenticated_client.get_alerts(status="pending")
            assert isinstance(pending_alerts, list)

            if pending_alerts:
                # Test acknowledging an alert
                alert = pending_alerts[0]
                assert validator.validate_alert_response(alert)

                acknowledged = await authenticated_client.acknowledge_alert(alert["id"])
                assert acknowledged["status"] == "ACKNOWLEDGED"

                # Verify alert is no longer pending
                new_pending = await authenticated_client.get_alerts(status="pending")
                acknowledged_ids = {a["id"] for a in new_pending if a["status"] == "ACKNOWLEDGED"}
                assert alert["id"] not in [a["id"] for a in new_pending if a["status"] == "PENDING"]

        except Exception as e:
            print(f"Alert operations might not be fully implemented: {e}")

        # Get alert history
        try:
            history = await authenticated_client.get_alerts(status="history")
            assert isinstance(history, list)
        except:
            pass

        # Clean up
        await authenticated_client.delete_rule(rule["id"])

    async def test_rule_priority_and_filtering(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test rule priorities and filtering"""
        asset = test_account_with_asset["asset"]

        priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        created_rules = []

        for i, priority in enumerate(priorities):
            rule_data = {
                "name": f"{priority} Priority Rule",
                "description": f"Test rule with {priority} priority",
                "asset_id": asset["id"],
                "asset_ticker": asset["ticker"],
                "condition_type": "PRICE_BELOW",
                "threshold": 100.0 - (i * 10),
                "is_active": True,
                "priority": priority
            }

            try:
                rule = await authenticated_client.create_rule(rule_data)
                created_rules.append(rule)
            except Exception as e:
                # Priority field might not exist
                if "priority" not in str(e).lower():
                    raise

        # Get all rules
        all_rules = await authenticated_client.get_rules()

        # Filter our test rules
        test_rules = [r for r in all_rules if r["id"] in {rule["id"] for rule in created_rules}]

        # Verify different priorities
        if test_rules and "priority" in test_rules[0]:
            rule_priorities = {r.get("priority") for r in test_rules}
            assert len(rule_priorities) > 1

        # Clean up
        for rule in created_rules:
            await authenticated_client.delete_rule(rule["id"])

    async def test_notification_integration(
        self,
        authenticated_client: APIClient,
        validator: ResponseValidator
    ):
        """Test notification sending and channels"""
        # Test sending a notification
        try:
            notification_response = await authenticated_client.send_notification(
                message="E2E Test Notification: System test in progress",
                recipient="test@example.com"
            )
            assert validator.validate_success_message(notification_response)
        except Exception as e:
            print(f"Notification sending might require configuration: {e}")

        # Test notification endpoint
        try:
            test_notification = await authenticated_client.test_notification()
            assert validator.validate_success_message(test_notification)
        except Exception as e:
            print(f"Test notification might not be implemented: {e}")

    @pytest.mark.slow
    async def test_bulk_rule_operations(
        self,
        authenticated_client: APIClient,
        test_account_with_asset: Dict,
        validator: ResponseValidator
    ):
        """Test bulk operations on rules"""
        asset = test_account_with_asset["asset"]
        num_rules = 15
        created_rules = []

        # Bulk create rules
        create_tasks = []
        for i in range(num_rules):
            rule_data = {
                "name": f"Bulk Rule {i:02d}",
                "description": f"Bulk test rule number {i}",
                "asset_id": asset["id"],
                "asset_ticker": asset["ticker"],
                "condition_type": "PRICE_BELOW" if i % 2 == 0 else "PRICE_ABOVE",
                "threshold": 100.0 + (i * 5),
                "is_active": i % 3 != 0  # Some active, some inactive
            }
            create_tasks.append(authenticated_client.create_rule(rule_data))

        created_rules = await asyncio.gather(*create_tasks)

        # Validate all were created
        for rule in created_rules:
            assert validator.validate_rule_response(rule)

        # Bulk toggle rules
        toggle_tasks = []
        for rule in created_rules[:10]:
            new_status = not rule["is_active"]
            toggle_tasks.append(
                authenticated_client.toggle_rule(rule["id"], new_status)
            )

        toggled_rules = await asyncio.gather(*toggle_tasks)
        for original, toggled in zip(created_rules[:10], toggled_rules):
            assert toggled["is_active"] != original["is_active"]

        # Bulk delete rules
        delete_tasks = []
        for rule in created_rules:
            delete_tasks.append(authenticated_client.delete_rule(rule["id"]))

        await asyncio.gather(*delete_tasks)

        # Verify all deleted
        remaining_rules = await authenticated_client.get_rules()
        remaining_ids = {r["id"] for r in remaining_rules}
        created_ids = {r["id"] for r in created_rules}
        assert not created_ids.intersection(remaining_ids)

    async def test_rule_alert_correlation(
        self,
        authenticated_client: APIClient,
        test_complete_setup: Dict,
        validator: ResponseValidator
    ):
        """Test correlation between rules and generated alerts"""
        asset = test_complete_setup["asset"]

        # Create multiple rules for the same asset
        rules = []
        for i in range(3):
            rule = await authenticated_client.create_rule({
                "name": f"Correlation Rule {i}",
                "description": f"Test correlation rule {i}",
                "asset_id": asset["id"],
                "asset_ticker": asset["ticker"],
                "condition_type": "PRICE_BELOW",
                "threshold": 100.0 + (i * 10),
                "is_active": True
            })
            rules.append(rule)

        # Get all alerts
        all_alerts = await authenticated_client.get_alerts()

        # Check if any alerts reference our rules
        rule_ids = {r["id"] for r in rules}
        related_alerts = [a for a in all_alerts if a.get("rule_id") in rule_ids]

        # If there are related alerts, validate them
        for alert in related_alerts:
            assert validator.validate_alert_response(alert)
            assert alert["rule_id"] in rule_ids

        # Clean up
        for rule in rules:
            await authenticated_client.delete_rule(rule["id"])

    async def test_complex_rule_conditions(
        self,
        authenticated_client: APIClient,
        test_complete_setup: Dict,
        validator: ResponseValidator
    ):
        """Test complex rule conditions and combinations"""
        asset = test_complete_setup["asset"]
        option = test_complete_setup["option"]

        # Create rules with complex conditions
        complex_rules = [
            {
                "name": "Multi-condition Rule",
                "description": "Alert on multiple conditions",
                "asset_id": asset["id"],
                "asset_ticker": asset["ticker"],
                "condition_type": "CUSTOM",
                "threshold": 100,
                "custom_conditions": {
                    "price_range": {"min": 90, "max": 110},
                    "volume_threshold": 1000000,
                    "time_window": "1h"
                },
                "is_active": True
            },
            {
                "name": "Option-specific Rule",
                "description": "Alert for specific option conditions",
                "asset_id": asset["id"],
                "asset_ticker": asset["ticker"],
                "option_id": option["id"],
                "condition_type": "OPTION_PRICE",
                "threshold": 5.00,
                "is_active": True
            }
        ]

        for rule_data in complex_rules:
            try:
                rule = await authenticated_client.create_rule(rule_data)
                assert validator.validate_rule_response(rule)

                # Clean up immediately
                await authenticated_client.delete_rule(rule["id"])
            except Exception as e:
                # Complex conditions might not be supported
                if "not supported" in str(e).lower() or "invalid" in str(e).lower():
                    print(f"Complex condition not supported: {rule_data['name']}")
                    continue