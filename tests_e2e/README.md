# E2E Tests with Playwright

## Overview

This directory contains comprehensive End-to-End (E2E) tests for the Options Monitoring API using Playwright. These tests simulate real user scenarios and validate the complete system functionality.

## Test Structure

```
tests_e2e/
├── helpers/
│   ├── api_client.py        # API client wrapper with all endpoints
│   └── validators.py        # Response validation utilities
├── conftest.py              # Pytest fixtures and configuration
├── test_auth_e2e.py         # Authentication workflows
├── test_accounts_e2e.py     # Account management tests
├── test_assets_e2e.py       # Asset management tests
├── test_options_trading_e2e.py  # Options trading tests
├── test_alerts_rules_e2e.py     # Alert and rule tests
└── test_complete_journey_e2e.py # Complete user journey test
```

## Prerequisites

### 1. Install Dependencies

```bash
# Install Playwright and pytest-playwright
pip install playwright pytest-playwright

# Install Playwright browsers
playwright install chromium

# Install other test dependencies
pip install pytest-asyncio pytest-mock pytest-cov
```

### 2. Start Backend Server

The backend API must be running before executing E2E tests:

```bash
# Start the Sanic server
python app/main.py

# Or use the run script
python scripts/run_dev.py
```

### 3. Configure Environment

Create a `.env` file with test configuration:

```env
# E2E Test Configuration
E2E_BASE_URL=http://localhost:8000
E2E_LOG_LEVEL=INFO

# Use test database (optional)
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_db
```

## Running Tests

### Quick Start

```bash
# Run all E2E tests
python run_e2e_tests.py

# Run with visible browser (headed mode)
python run_e2e_tests.py --headed

# Run specific test file
python run_e2e_tests.py --test test_auth_e2e.py

# Run tests with specific marker
python run_e2e_tests.py --marker smoke

# Generate HTML report
python run_e2e_tests.py --report
```

### Using Pytest Directly

```bash
# Run all E2E tests
pytest tests_e2e/ -v

# Run specific test file
pytest tests_e2e/test_auth_e2e.py -v

# Run specific test class
pytest tests_e2e/test_auth_e2e.py::TestAuthenticationE2E -v

# Run specific test method
pytest tests_e2e/test_auth_e2e.py::TestAuthenticationE2E::test_complete_auth_flow -v

# Run with markers
pytest tests_e2e/ -m smoke       # Quick smoke tests
pytest tests_e2e/ -m "not slow"  # Skip slow tests
pytest tests_e2e/ -m auth        # Only auth tests

# Run with coverage
pytest tests_e2e/ --cov=app --cov-report=html

# Run in parallel
pytest tests_e2e/ -n 4  # Use 4 workers

# Debug mode (show print statements)
pytest tests_e2e/ -s --log-cli-level=DEBUG
```

## Test Markers

Tests are organized with markers for selective execution:

- `@pytest.mark.smoke` - Quick smoke tests for basic functionality
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.accounts` - Account management tests
- `@pytest.mark.assets` - Asset management tests
- `@pytest.mark.options` - Options trading tests
- `@pytest.mark.rules` - Alert rules tests
- `@pytest.mark.alerts` - Alert management tests
- `@pytest.mark.e2e` - Full E2E tests
- `@pytest.mark.slow` - Tests that take longer to execute

## Test Scenarios

### 1. Authentication Tests (`test_auth_e2e.py`)
- Complete authentication flow (register → login → logout)
- Token refresh workflow
- Password change flow
- Registration validation
- Concurrent authentication sessions
- Security headers validation

### 2. Account Management Tests (`test_accounts_e2e.py`)
- Complete account CRUD lifecycle
- Multiple accounts management
- Account validation rules
- Account isolation between users
- Bulk operations
- Special characters handling

### 3. Asset Management Tests (`test_assets_e2e.py`)
- Complete asset CRUD lifecycle
- Different asset types (STOCK, ETF, FII, BDR)
- Asset ticker validation
- Search and filtering
- Market data integration
- Asset relationships with options

### 4. Options Trading Tests (`test_options_trading_e2e.py`)
- Complete option lifecycle (open → monitor → close)
- Multiple option strategies (covered calls, puts, spreads)
- Option roll calculations
- Expiry handling
- Portfolio analysis
- Concurrent operations

### 5. Alerts & Rules Tests (`test_alerts_rules_e2e.py`)
- Complete rule lifecycle
- Different rule types and conditions
- Alert generation and acknowledgment
- Rule priorities and filtering
- Notification integration
- Bulk rule operations

### 6. Complete Journey Test (`test_complete_journey_e2e.py`)
- Full user journey from registration to trading
- Multi-phase workflow:
  1. User registration and setup
  2. Account configuration
  3. Asset management
  4. Opening positions
  5. Setting monitoring rules
  6. Position management
  7. Rolling options
  8. Closing positions
  9. Performance analysis
- Multi-user trading scenarios

## API Client Helper

The `APIClient` class in `helpers/api_client.py` provides methods for all API endpoints:

```python
# Authentication
await client.register_user(email, password, name)
await client.login(email, password)
await client.logout()
await client.refresh_access_token()

# Accounts
await client.create_account(account_data)
await client.get_accounts()
await client.update_account(id, data)
await client.delete_account(id)

# Assets
await client.create_asset(asset_data)
await client.get_assets()
await client.update_asset(id, data)
await client.delete_asset(id)

# Options
await client.create_option(option_data)
await client.get_options(account_id=None, asset_ticker=None)
await client.close_option(id, exit_price)

# Rules & Alerts
await client.create_rule(rule_data)
await client.get_rules()
await client.toggle_rule(id, is_active)
await client.get_alerts(status=None)
await client.acknowledge_alert(id)
```

## Response Validation

The `ResponseValidator` class provides validation methods for all response types:

```python
validator.validate_auth_token_response(response)
validator.validate_user_response(response)
validator.validate_account_response(response)
validator.validate_asset_response(response)
validator.validate_option_response(response)
validator.validate_rule_response(response)
validator.validate_alert_response(response)
validator.validate_error_response(response)
validator.validate_pagination_response(response)
```

## Test Data

Test data is configured in `playwright_config.py`:

- **Test Users**: Primary and secondary test users
- **Test Accounts**: Sample brokerage accounts
- **Test Assets**: Sample stocks and ETFs
- **Test Options**: Sample option positions
- **Test Rules**: Sample monitoring rules

## Debugging Tests

### View Test Output

```bash
# Show all print statements
pytest tests_e2e/ -s

# Increase verbosity
pytest tests_e2e/ -vv

# Show full traceback
pytest tests_e2e/ --tb=long
```

### Run in Headed Mode

```bash
# See browser actions
python run_e2e_tests.py --headed

# Or set environment variable
HEADED=1 pytest tests_e2e/
```

### Debug Specific Test

```bash
# Run single test with debugging
pytest tests_e2e/test_auth_e2e.py::TestAuthenticationE2E::test_complete_auth_flow -s --log-cli-level=DEBUG
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install playwright pytest-playwright
          playwright install chromium

      - name: Start backend server
        run: |
          python app/main.py &
          sleep 5  # Wait for server to start

      - name: Run E2E tests
        run: python run_e2e_tests.py --report

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: e2e-test-results
          path: test-results/
```

## Troubleshooting

### Common Issues

1. **Server not running**
   ```
   Error: Backend server is not running!
   Solution: Start the server with `python app/main.py`
   ```

2. **Playwright not installed**
   ```
   Error: playwright: command not found
   Solution: pip install playwright && playwright install chromium
   ```

3. **Database connection issues**
   ```
   Error: Cannot connect to database
   Solution: Check DATABASE_URL in .env file
   ```

4. **Port already in use**
   ```
   Error: Address already in use
   Solution: Kill existing process or change port in config
   ```

5. **Timeout errors**
   ```
   Error: Test timeout exceeded
   Solution: Increase timeout in playwright.config.py
   ```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Data Cleanup**: Tests clean up their data after execution
3. **Unique Data**: Use timestamps to ensure unique test data
4. **Error Handling**: Tests handle expected errors gracefully
5. **Assertions**: Validate all critical response fields
6. **Logging**: Use descriptive print statements for debugging
7. **Markers**: Use appropriate markers for test organization
8. **Parallel Execution**: Tests support parallel execution

## Performance Tips

- Run smoke tests first for quick validation
- Use parallel execution for faster test runs
- Skip slow tests during development with `-m "not slow"`
- Use fixtures to avoid repetitive setup
- Cache authentication tokens when possible

## Contributing

When adding new E2E tests:

1. Follow the existing test structure
2. Add appropriate markers
3. Use the APIClient helper for API calls
4. Validate responses with ResponseValidator
5. Clean up test data after execution
6. Document complex test scenarios
7. Add new endpoints to APIClient as needed

## License

See main project LICENSE file.