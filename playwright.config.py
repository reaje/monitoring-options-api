"""
Playwright configuration for E2E testing
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base URL for API testing
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")

# Test timeout settings
DEFAULT_TIMEOUT = 30000  # 30 seconds
EXPECT_TIMEOUT = 10000   # 10 seconds
ACTION_TIMEOUT = 15000   # 15 seconds

# Playwright config
playwright_config: Dict[str, Any] = {
    "base_url": BASE_URL,
    "use": {
        # Browser context options
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "base_url": BASE_URL,

        # Timeout settings
        "action_timeout": ACTION_TIMEOUT,
        "navigation_timeout": DEFAULT_TIMEOUT,

        # Screenshots and videos
        "screenshot": "only-on-failure",
        "video": "retain-on-failure",
        "trace": "on-first-retry",

        # API testing specific
        "extra_http_headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    },

    # Test directory
    "test_dir": "./tests_e2e",

    # Test match patterns
    "test_match": ["test_*.py", "*_test.py"],

    # Number of workers for parallel execution
    "workers": 4,

    # Retries on failure
    "retries": 1,

    # Reporter configuration
    "reporter": "list",

    # Global timeout
    "timeout": 60000,  # 60 seconds per test

    # Output directory for artifacts
    "output_dir": "test-results",
}

# Test user credentials for E2E tests
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

# Test data for different entities
TEST_DATA = {
    "accounts": [
        {
            "name": "Test Account 1",
            "broker": "Test Broker",
            "account_number": "TEST001",
            "is_active": True
        },
        {
            "name": "Test Account 2",
            "broker": "Another Broker",
            "account_number": "TEST002",
            "is_active": True
        }
    ],
    "assets": [
        {
            "ticker": "TEST1",
            "name": "Test Asset 1",
            "type": "STOCK",
            "market": "BOVESPA"
        },
        {
            "ticker": "TEST2",
            "name": "Test Asset 2",
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
        },
        {
            "ticker": "TESTB50",
            "asset_ticker": "TEST2",
            "strike": 50.00,
            "expiry": "2025-01-15",
            "side": "PUT",
            "strategy": "SHORT_PUT"
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
        },
        {
            "name": "Test Rule 2",
            "description": "Alert on expiry approaching",
            "asset_ticker": "TEST2",
            "condition_type": "DAYS_TO_EXPIRY",
            "threshold": 7,
            "is_active": True
        }
    ]
}

# API Endpoints
API_ENDPOINTS = {
    # Auth endpoints
    "register": "/auth/register",
    "login": "/auth/login",
    "refresh": "/auth/refresh",
    "logout": "/auth/logout",
    "change_password": "/auth/change-password",
    "user_info": "/auth/me",

    # Account endpoints
    "accounts": "/api/accounts",
    "account_detail": "/api/accounts/{id}",

    # Asset endpoints
    "assets": "/api/assets",
    "asset_detail": "/api/assets/{id}",

    # Options endpoints
    "options": "/api/options",
    "option_detail": "/api/options/{id}",
    "options_by_account": "/api/options/account/{account_id}",
    "options_by_asset": "/api/options/asset/{asset_ticker}",

    # Rules endpoints
    "rules": "/api/rules",
    "rule_detail": "/api/rules/{id}",
    "rules_by_asset": "/api/rules/asset/{asset_ticker}",

    # Alerts endpoints
    "alerts": "/api/alerts",
    "alert_detail": "/api/alerts/{id}",
    "alerts_pending": "/api/alerts/pending",
    "alerts_history": "/api/alerts/history",

    # Market data endpoints
    "market_quote": "/api/market-data/quote/{ticker}",
    "market_history": "/api/market-data/history/{ticker}",

    # Roll calculation endpoints
    "roll_calculate": "/api/rolls/calculate",
    "roll_simulate": "/api/rolls/simulate",

    # Notification endpoints
    "notification_send": "/api/notifications/send",
    "notification_test": "/api/notifications/test",

    # Health check
    "health": "/health",
    "root": "/"
}

# Expected response structures for validation
EXPECTED_RESPONSES = {
    "auth_token": {
        "access_token": str,
        "token_type": str,
        "expires_in": int,
        "refresh_token": str
    },
    "user": {
        "id": str,
        "email": str,
        "name": str,
        "created_at": str,
        "updated_at": str
    },
    "account": {
        "id": str,
        "user_id": str,
        "name": str,
        "broker": str,
        "account_number": str,
        "is_active": bool,
        "created_at": str,
        "updated_at": str
    },
    "asset": {
        "id": str,
        "ticker": str,
        "name": str,
        "type": str,
        "market": str,
        "created_at": str,
        "updated_at": str
    },
    "option": {
        "id": str,
        "account_id": str,
        "asset_id": str,
        "ticker": str,
        "strike": float,
        "expiry": str,
        "side": str,
        "strategy": str,
        "quantity": int,
        "entry_price": float,
        "status": str,
        "created_at": str,
        "updated_at": str
    },
    "rule": {
        "id": str,
        "user_id": str,
        "name": str,
        "description": str,
        "asset_ticker": str,
        "condition_type": str,
        "threshold": float,
        "is_active": bool,
        "created_at": str,
        "updated_at": str
    },
    "alert": {
        "id": str,
        "rule_id": str,
        "triggered_at": str,
        "message": str,
        "status": str,
        "created_at": str
    }
}

# Cleanup configuration
CLEANUP_AFTER_TESTS = True  # Delete test data after tests
CLEANUP_TIMEOUT = 5000  # 5 seconds for cleanup operations

# Logging configuration for E2E tests
LOG_LEVEL = os.getenv("E2E_LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"