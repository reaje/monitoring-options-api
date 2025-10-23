"""
Pytest fixtures for E2E tests with Playwright
"""

import pytest
import asyncio
from typing import Dict, Any, AsyncGenerator
from playwright.async_api import async_playwright, APIRequestContext, Playwright
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration directly
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
TEST_USERS = {
    "primary": {
        "email": "e2e_test_user@example.com",
        "password": "TestPassword123!",
        "name": "E2E Test User"
    },
    "secondary": {
        "email": "e2e_test_user2@example.com",
        "password": "TestPassword456!",
        "name": "E2E Test User 2"
    }
}
TEST_DATA = {
    "accounts": [
        {
            "name": "Test Account 1",
            "broker": "Test Broker",
            "account_number": "TEST001",
            "is_active": True
        }
    ],
    "assets": [
        {
            "ticker": "TEST1",
            "name": "Test Asset 1",
            "type": "STOCK",
            "market": "BOVESPA"
        }
    ],
    "options": [
        {
            "ticker": "TESTA100",
            "asset_ticker": "TEST1",
            "strike": 100.00,
            "expiry": "2025-01-15",
            "side": "CALL",
            "strategy": "COVERED_CALL"
        }
    ],
    "rules": [
        {
            "name": "Test Rule 1",
            "description": "Alert when price drops below threshold",
            "asset_ticker": "TEST1",
            "condition_type": "PRICE_BELOW",
            "threshold": 95.00,
            "is_active": True
        }
    ]
}
CLEANUP_AFTER_TESTS = True
playwright_config = {}
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def playwright_instance() -> AsyncGenerator[Playwright, None]:
    """Create a Playwright instance for the test session"""
    async with async_playwright() as p:
        yield p


@pytest.fixture(scope="session")
async def api_request_context(playwright_instance: Playwright) -> AsyncGenerator[APIRequestContext, None]:
    """Create an API request context for the test session"""
    request_context = await playwright_instance.request.new_context(
        base_url=BASE_URL,
        ignore_https_errors=True,
        extra_http_headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )
    yield request_context
    await request_context.dispose()


@pytest.fixture
async def api_client(api_request_context: APIRequestContext) -> AsyncGenerator[APIClient, None]:
    """Create an API client for each test"""
    client = APIClient(api_request_context, BASE_URL)
    yield client

    # Cleanup if enabled
    if CLEANUP_AFTER_TESTS and client.is_authenticated():
        await client.cleanup_test_data()


@pytest.fixture
async def authenticated_client(api_client: APIClient) -> AsyncGenerator[APIClient, None]:
    """Create an authenticated API client with a test user"""
    # Register a new test user
    user_data = TEST_USERS["primary"]
    unique_email = f"test_{asyncio.get_event_loop().time()}@example.com"

    try:
        await api_client.register_user(
            email=unique_email,
            password=user_data["password"],
            name=user_data["name"]
        )
    except Exception:
        # User might already exist, try to login
        pass

    # Login with the test user
    await api_client.login(unique_email, user_data["password"])

    yield api_client

    # Logout after test
    try:
        await api_client.logout()
    except:
        pass


@pytest.fixture
async def secondary_authenticated_client(api_request_context: APIRequestContext) -> AsyncGenerator[APIClient, None]:
    """Create a second authenticated API client for multi-user tests"""
    client = APIClient(api_request_context, BASE_URL)

    # Register a secondary test user
    user_data = TEST_USERS["secondary"]
    unique_email = f"test2_{asyncio.get_event_loop().time()}@example.com"

    try:
        await client.register_user(
            email=unique_email,
            password=user_data["password"],
            name=user_data["name"]
        )
    except Exception:
        # User might already exist
        pass

    # Login with the secondary test user
    await client.login(unique_email, user_data["password"])

    yield client

    # Cleanup and logout
    if CLEANUP_AFTER_TESTS:
        await client.cleanup_test_data()
    try:
        await client.logout()
    except:
        pass


@pytest.fixture
def validator() -> ResponseValidator:
    """Get response validator instance"""
    return ResponseValidator()


@pytest.fixture
def test_account_data() -> Dict[str, Any]:
    """Get test account data"""
    return TEST_DATA["accounts"][0].copy()


@pytest.fixture
def test_asset_data() -> Dict[str, Any]:
    """Get test asset data"""
    return TEST_DATA["assets"][0].copy()


@pytest.fixture
def test_option_data() -> Dict[str, Any]:
    """Get test option data"""
    return TEST_DATA["options"][0].copy()


@pytest.fixture
def test_rule_data() -> Dict[str, Any]:
    """Get test rule data"""
    return TEST_DATA["rules"][0].copy()


@pytest.fixture
async def test_account_with_asset(authenticated_client: APIClient) -> Dict[str, Any]:
    """Create a test account with an asset for complex tests"""
    # Create account
    account_data = TEST_DATA["accounts"][0].copy()
    account = await authenticated_client.create_account(account_data)

    # Create asset
    asset_data = TEST_DATA["assets"][0].copy()
    asset = await authenticated_client.create_asset(asset_data)

    return {
        "account": account,
        "asset": asset
    }


@pytest.fixture
async def test_complete_setup(authenticated_client: APIClient) -> Dict[str, Any]:
    """Create a complete test setup with account, asset, option, and rule"""
    # Create account
    account_data = TEST_DATA["accounts"][0].copy()
    account = await authenticated_client.create_account(account_data)

    # Create asset
    asset_data = TEST_DATA["assets"][0].copy()
    asset = await authenticated_client.create_asset(asset_data)

    # Create option position
    option_data = TEST_DATA["options"][0].copy()
    option_data["account_id"] = account["id"]
    option_data["asset_id"] = asset["id"]
    option_data["quantity"] = 10
    option = await authenticated_client.create_option(option_data)

    # Create monitoring rule
    rule_data = TEST_DATA["rules"][0].copy()
    rule_data["asset_id"] = asset["id"]
    rule = await authenticated_client.create_rule(rule_data)

    return {
        "account": account,
        "asset": asset,
        "option": option,
        "rule": rule
    }


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "auth: Authentication tests"
    )
    config.addinivalue_line(
        "markers", "accounts: Account management tests"
    )
    config.addinivalue_line(
        "markers", "assets: Asset management tests"
    )
    config.addinivalue_line(
        "markers", "options: Options trading tests"
    )
    config.addinivalue_line(
        "markers", "rules: Alert rules tests"
    )
    config.addinivalue_line(
        "markers", "alerts: Alert management tests"
    )
    config.addinivalue_line(
        "markers", "market_data: Market data tests"
    )
    config.addinivalue_line(
        "markers", "notifications: Notification tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests for basic functionality"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer to execute"
    )