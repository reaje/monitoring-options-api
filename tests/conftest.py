"""Pytest configuration and fixtures."""

import pytest
import asyncio
from uuid import uuid4
from app.main import app
from app.database.supabase_client import supabase
from app.core.security import security
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.assets import AssetsRepository


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sanic_app():
    """Get Sanic app instance."""
    return app


@pytest.fixture
async def test_client(sanic_app):
    """Get test client for Sanic app."""
    return sanic_app.asgi_client


# =====================================
# USER FIXTURES
# =====================================


@pytest.fixture
async def test_user():
    """
    Create a test user and clean up after test.

    Returns:
        dict: User data with plain password
    """
    user_data = {
        "email": f"test_{uuid4()}@example.com",
        "password": security.hash_password("testpass123"),
        "name": "Test User",
    }

    # Create user
    result = supabase.table("users").insert(user_data).execute()
    user = result.data[0]

    # Add plain password for testing
    user["plain_password"] = "testpass123"

    yield user

    # Cleanup: Delete user (cascades to accounts, assets, etc)
    try:
        supabase.table("users").delete().eq("id", user["id"]).execute()
    except Exception:
        pass


@pytest.fixture
async def auth_token(test_user):
    """
    Create auth token for test user.

    Returns:
        str: JWT access token
    """
    token = security.create_access_token(
        user_id=test_user["id"],
        email=test_user["email"],
    )
    return token


@pytest.fixture
async def auth_headers(auth_token):
    """
    Create authorization headers.

    Returns:
        dict: Headers with Bearer token
    """
    return {"Authorization": f"Bearer {auth_token}"}


# =====================================
# ACCOUNT FIXTURES
# =====================================


@pytest.fixture
async def test_account(test_user):
    """
    Create a test account.

    Returns:
        dict: Account data
    """
    account_data = {
        "user_id": test_user["id"],
        "name": "Test Account",
    }

    account = await AccountsRepository.create(account_data)

    yield account

    # Cleanup
    try:
        await AccountsRepository.delete(account["id"])
    except Exception:
        pass


# =====================================
# ASSET FIXTURES
# =====================================


@pytest.fixture
async def test_asset(test_account):
    """
    Create a test asset.

    Returns:
        dict: Asset data
    """
    asset_data = {
        "account_id": test_account["id"],
        "ticker": "PETR4",
    }

    asset = await AssetsRepository.create(asset_data)

    yield asset

    # Cleanup
    try:
        await AssetsRepository.delete(asset["id"])
    except Exception:
        pass


# =====================================
# MULTIPLE FIXTURES
# =====================================


@pytest.fixture
async def multiple_accounts(test_user):
    """
    Create multiple test accounts.

    Returns:
        list: List of account dicts
    """
    accounts = []

    for i in range(3):
        account_data = {
            "user_id": test_user["id"],
            "name": f"Test Account {i+1}",
        }
        account = await AccountsRepository.create(account_data)
        accounts.append(account)

    yield accounts

    # Cleanup
    for account in accounts:
        try:
            await AccountsRepository.delete(account["id"])
        except Exception:
            pass


@pytest.fixture
async def multiple_assets(test_account):
    """
    Create multiple test assets.

    Returns:
        list: List of asset dicts
    """
    tickers = ["PETR4", "VALE3", "ITUB4"]
    assets = []

    for ticker in tickers:
        asset_data = {
            "account_id": test_account["id"],
            "ticker": ticker,
        }
        asset = await AssetsRepository.create(asset_data)
        assets.append(asset)

    yield assets

    # Cleanup
    for asset in assets:
        try:
            await AssetsRepository.delete(asset["id"])
        except Exception:
            pass
