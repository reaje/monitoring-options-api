"""
API Client helper for E2E tests using Playwright's request context
"""

from typing import Dict, Any, Optional, List
from playwright.async_api import APIRequestContext, APIResponse
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    """Helper class for making API requests in E2E tests"""

    def __init__(self, request_context: APIRequestContext, base_url: str):
        self.context = request_context
        self.base_url = base_url
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    async def register_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Register a new user"""
        response = await self.context.post(
            f"{self.base_url}/auth/register",
            data={
                "email": email,
                "password": password,
                "name": name
            }
        )
        return await self._handle_response(response, "User registration")

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login and store authentication tokens"""
        response = await self.context.post(
            f"{self.base_url}/auth/login",
            data={
                "email": email,
                "password": password
            }
        )
        result = await self._handle_response(response, "User login")

        # Store tokens for subsequent requests
        if "access_token" in result:
            self.auth_token = result["access_token"]
            self.refresh_token = result.get("refresh_token")
            # Update default headers with auth token
            await self.context.set_extra_http_headers({
                "Authorization": f"Bearer {self.auth_token}"
            })

        return result

    async def logout(self) -> Dict[str, Any]:
        """Logout the current user"""
        response = await self.context.post(f"{self.base_url}/auth/logout")
        result = await self._handle_response(response, "User logout")

        # Clear tokens
        self.auth_token = None
        self.refresh_token = None
        await self.context.set_extra_http_headers({})

        return result

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        response = await self.context.post(
            f"{self.base_url}/auth/refresh",
            headers={
                "Authorization": f"Bearer {self.refresh_token}"
            }
        )
        result = await self._handle_response(response, "Token refresh")

        if "access_token" in result:
            self.auth_token = result["access_token"]
            await self.context.set_extra_http_headers({
                "Authorization": f"Bearer {self.auth_token}"
            })

        return result

    async def get_user_info(self) -> Dict[str, Any]:
        """Get current user information"""
        response = await self.context.get(f"{self.base_url}/auth/me")
        return await self._handle_response(response, "Get user info")

    async def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change user password"""
        response = await self.context.put(
            f"{self.base_url}/auth/change-password",
            data={
                "current_password": current_password,
                "new_password": new_password
            }
        )
        return await self._handle_response(response, "Change password")

    # Account Management
    async def create_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new account"""
        response = await self.context.post(
            f"{self.base_url}/api/accounts",
            data=account_data
        )
        return await self._handle_response(response, "Create account")

    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts for the current user"""
        response = await self.context.get(f"{self.base_url}/api/accounts")
        return await self._handle_response(response, "Get accounts")

    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """Get a specific account by ID"""
        response = await self.context.get(f"{self.base_url}/api/accounts/{account_id}")
        return await self._handle_response(response, f"Get account {account_id}")

    async def update_account(self, account_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an account"""
        response = await self.context.put(
            f"{self.base_url}/api/accounts/{account_id}",
            data=update_data
        )
        return await self._handle_response(response, f"Update account {account_id}")

    async def delete_account(self, account_id: str) -> Dict[str, Any]:
        """Delete an account"""
        response = await self.context.delete(f"{self.base_url}/api/accounts/{account_id}")
        return await self._handle_response(response, f"Delete account {account_id}")

    # Asset Management
    async def create_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new asset"""
        response = await self.context.post(
            f"{self.base_url}/api/assets",
            data=asset_data
        )
        return await self._handle_response(response, "Create asset")

    async def get_assets(self) -> List[Dict[str, Any]]:
        """Get all assets"""
        response = await self.context.get(f"{self.base_url}/api/assets")
        return await self._handle_response(response, "Get assets")

    async def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Get a specific asset by ID"""
        response = await self.context.get(f"{self.base_url}/api/assets/{asset_id}")
        return await self._handle_response(response, f"Get asset {asset_id}")

    async def update_asset(self, asset_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an asset"""
        response = await self.context.put(
            f"{self.base_url}/api/assets/{asset_id}",
            data=update_data
        )
        return await self._handle_response(response, f"Update asset {asset_id}")

    async def delete_asset(self, asset_id: str) -> Dict[str, Any]:
        """Delete an asset"""
        response = await self.context.delete(f"{self.base_url}/api/assets/{asset_id}")
        return await self._handle_response(response, f"Delete asset {asset_id}")

    # Options Management
    async def create_option(self, option_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new option position"""
        response = await self.context.post(
            f"{self.base_url}/api/options",
            data=option_data
        )
        return await self._handle_response(response, "Create option")

    async def get_options(self, account_id: Optional[str] = None, asset_ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get options, optionally filtered by account or asset"""
        if account_id:
            url = f"{self.base_url}/api/options/account/{account_id}"
        elif asset_ticker:
            url = f"{self.base_url}/api/options/asset/{asset_ticker}"
        else:
            url = f"{self.base_url}/api/options"

        response = await self.context.get(url)
        return await self._handle_response(response, "Get options")

    async def get_option(self, option_id: str) -> Dict[str, Any]:
        """Get a specific option by ID"""
        response = await self.context.get(f"{self.base_url}/api/options/{option_id}")
        return await self._handle_response(response, f"Get option {option_id}")

    async def update_option(self, option_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an option position"""
        response = await self.context.put(
            f"{self.base_url}/api/options/{option_id}",
            data=update_data
        )
        return await self._handle_response(response, f"Update option {option_id}")

    async def close_option(self, option_id: str, exit_price: float) -> Dict[str, Any]:
        """Close an option position"""
        response = await self.context.post(
            f"{self.base_url}/api/options/{option_id}/close",
            data={"exit_price": exit_price}
        )
        return await self._handle_response(response, f"Close option {option_id}")

    # Rules Management
    async def create_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new monitoring rule"""
        response = await self.context.post(
            f"{self.base_url}/api/rules",
            data=rule_data
        )
        return await self._handle_response(response, "Create rule")

    async def get_rules(self, asset_ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get rules, optionally filtered by asset"""
        if asset_ticker:
            url = f"{self.base_url}/api/rules/asset/{asset_ticker}"
        else:
            url = f"{self.base_url}/api/rules"

        response = await self.context.get(url)
        return await self._handle_response(response, "Get rules")

    async def get_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get a specific rule by ID"""
        response = await self.context.get(f"{self.base_url}/api/rules/{rule_id}")
        return await self._handle_response(response, f"Get rule {rule_id}")

    async def update_rule(self, rule_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a rule"""
        response = await self.context.put(
            f"{self.base_url}/api/rules/{rule_id}",
            data=update_data
        )
        return await self._handle_response(response, f"Update rule {rule_id}")

    async def delete_rule(self, rule_id: str) -> Dict[str, Any]:
        """Delete a rule"""
        response = await self.context.delete(f"{self.base_url}/api/rules/{rule_id}")
        return await self._handle_response(response, f"Delete rule {rule_id}")

    async def toggle_rule(self, rule_id: str, is_active: bool) -> Dict[str, Any]:
        """Toggle a rule's active status"""
        response = await self.context.patch(
            f"{self.base_url}/api/rules/{rule_id}/toggle",
            data={"is_active": is_active}
        )
        return await self._handle_response(response, f"Toggle rule {rule_id}")

    # Alerts Management
    async def get_alerts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by status"""
        if status == "pending":
            url = f"{self.base_url}/api/alerts/pending"
        elif status == "history":
            url = f"{self.base_url}/api/alerts/history"
        else:
            url = f"{self.base_url}/api/alerts"

        response = await self.context.get(url)
        return await self._handle_response(response, "Get alerts")

    async def get_alert(self, alert_id: str) -> Dict[str, Any]:
        """Get a specific alert by ID"""
        response = await self.context.get(f"{self.base_url}/api/alerts/{alert_id}")
        return await self._handle_response(response, f"Get alert {alert_id}")

    async def acknowledge_alert(self, alert_id: str) -> Dict[str, Any]:
        """Acknowledge an alert"""
        response = await self.context.post(f"{self.base_url}/api/alerts/{alert_id}/acknowledge")
        return await self._handle_response(response, f"Acknowledge alert {alert_id}")

    # Market Data
    async def get_market_quote(self, ticker: str) -> Dict[str, Any]:
        """Get current market quote for a ticker"""
        response = await self.context.get(f"{self.base_url}/api/market-data/quote/{ticker}")
        return await self._handle_response(response, f"Get market quote for {ticker}")

    async def get_market_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get market history for a ticker"""
        response = await self.context.get(
            f"{self.base_url}/api/market-data/history/{ticker}",
            params={"days": days}
        )
        return await self._handle_response(response, f"Get market history for {ticker}")

    # Roll Calculations
    async def calculate_roll(self, roll_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate option roll parameters"""
        response = await self.context.post(
            f"{self.base_url}/api/rolls/calculate",
            data=roll_data
        )
        return await self._handle_response(response, "Calculate roll")

    async def simulate_roll(self, simulation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate option roll scenarios"""
        response = await self.context.post(
            f"{self.base_url}/api/rolls/simulate",
            data=simulation_data
        )
        return await self._handle_response(response, "Simulate roll")

    # Notifications
    async def send_notification(self, message: str, recipient: str) -> Dict[str, Any]:
        """Send a notification"""
        response = await self.context.post(
            f"{self.base_url}/api/notifications/send",
            data={
                "message": message,
                "recipient": recipient
            }
        )
        return await self._handle_response(response, "Send notification")

    async def test_notification(self) -> Dict[str, Any]:
        """Send a test notification"""
        response = await self.context.post(f"{self.base_url}/api/notifications/test")
        return await self._handle_response(response, "Test notification")

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        response = await self.context.get(f"{self.base_url}/health")
        return await self._handle_response(response, "Health check")

    async def get_api_info(self) -> Dict[str, Any]:
        """Get API information"""
        response = await self.context.get(f"{self.base_url}/")
        return await self._handle_response(response, "Get API info")

    # Helper Methods
    async def _handle_response(self, response: APIResponse, operation: str) -> Any:
        """Handle API response and log details"""
        status = response.status

        # Log request details
        logger.debug(f"{operation} - Status: {status}")

        # Parse response body
        try:
            body = await response.json()
        except:
            body = await response.text()

        if status >= 400:
            logger.error(f"{operation} failed - Status: {status}, Body: {body}")
            raise Exception(f"{operation} failed with status {status}: {body}")

        logger.info(f"{operation} successful")
        return body

    async def cleanup_test_data(self) -> None:
        """Clean up all test data created during tests"""
        logger.info("Starting test data cleanup...")

        try:
            # Delete all test options
            options = await self.get_options()
            for option in options:
                if option.get("ticker", "").startswith("TEST"):
                    await self.delete_option(option["id"])

            # Delete all test rules
            rules = await self.get_rules()
            for rule in rules:
                if rule.get("name", "").startswith("Test"):
                    await self.delete_rule(rule["id"])

            # Delete all test assets
            assets = await self.get_assets()
            for asset in assets:
                if asset.get("ticker", "").startswith("TEST"):
                    await self.delete_asset(asset["id"])

            # Delete all test accounts
            accounts = await self.get_accounts()
            for account in accounts:
                if account.get("name", "").startswith("Test"):
                    await self.delete_account(account["id"])

            logger.info("Test data cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def is_authenticated(self) -> bool:
        """Check if client has valid auth token"""
        return bool(self.auth_token)