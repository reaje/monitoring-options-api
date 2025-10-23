# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Python backend API** for monitoring options trading operations, built with **Sanic** (async web framework) and **Supabase** (PostgreSQL). The system tracks accounts, assets, options positions, alerts, and provides rule-based monitoring with notifications.

## Running the Application

```bash
# Start the development server
python -m app.main

# The server runs on http://localhost:8000
```

## Testing

### Unit & Integration Tests (pytest)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only

# Run a specific test file
pytest tests/integration/test_auth_api.py

# Run a specific test class
pytest tests/integration/test_auth_api.py::TestAuthLogin

# Run a single test
pytest tests/integration/test_auth_api.py::TestAuthLogin::test_login_success
```

### E2E Tests (Playwright)

**Important:** Backend server must be running first!

```bash
# Quick verification that E2E setup works
python test_e2e_simple.py

# Run all E2E tests
python run_e2e_tests.py

# Run specific E2E test file
python run_e2e_tests.py --test test_auth_e2e.py

# Run only smoke tests (fast)
python run_e2e_tests.py --marker smoke

# Using pytest directly
pytest tests_e2e/ -v
pytest tests_e2e/test_auth_e2e.py::TestAuthenticationE2E::test_complete_auth_flow
```

E2E test markers available: `smoke`, `auth`, `accounts`, `assets`, `options`, `rules`, `alerts`, `e2e`, `slow`

## Code Quality Tools

```bash
# Format code with Black
black app/

# Lint with Flake8
flake8 app/

# Type checking with MyPy
mypy app/
```

## Architecture

### Layer Structure

The codebase follows a layered architecture:

```
Routes (app/routes/)
    ↓
Services (app/services/)
    ↓
Repositories (app/database/repositories/)
    ↓
Database (Supabase/PostgreSQL)
```

### Key Architectural Patterns

1. **Repository Pattern**: Database access is abstracted through repository classes in `app/database/repositories/`. Each repository inherits from `BaseRepository` and provides CRUD operations for a specific entity.

2. **Dependency Injection via Request Context**: The Sanic app instance is passed through request context (`request.app`) to access shared resources like:
   - `request.app.ctx.supabase` - Supabase client
   - `request.app.ctx.scheduler` - APScheduler instance

3. **Authentication Middleware**: JWT authentication is handled by middleware in `app/middleware/auth_middleware.py`. Protected routes automatically get `request.ctx.user` populated with the authenticated user.

4. **Async/Await Throughout**: All database operations, HTTP requests, and route handlers use async/await patterns.

### Database Access

**Always use repositories, never direct Supabase queries in routes.**

```python
# BAD - Direct Supabase call in route
result = await request.app.ctx.supabase.table("accounts").select("*").execute()

# GOOD - Use repository
from app.database.repositories.accounts import AccountsRepository
repo = AccountsRepository(request.app.ctx.supabase)
accounts = await repo.list_by_user(user_id)
```

### Background Workers

Background tasks are managed by APScheduler in `app/workers/scheduler.py`:
- **monitor_worker.py**: Monitors option positions every 5 minutes
- **notifier_worker.py**: Processes alert queue every 30 seconds
- Workers run automatically when the server starts

## Testing Patterns

### Integration Tests

Integration tests use fixtures from `tests/conftest.py`:

```python
async def test_example(test_client, auth_headers, test_account):
    # test_client: Sanic test client
    # auth_headers: {"Authorization": "Bearer <token>"}
    # test_account: Pre-created account for testing

    _, response = await test_client.get(
        "/api/accounts",
        headers=auth_headers
    )
    assert response.status == 200
```

Available fixtures: `test_user`, `auth_token`, `auth_headers`, `test_client`, `test_account`, `test_asset`, `multiple_accounts`, `multiple_assets`

### E2E Tests

E2E tests use Playwright's API request context via the `APIClient` helper in `tests_e2e/helpers/api_client.py`:

```python
async def test_flow(authenticated_client: APIClient, validator: ResponseValidator):
    # Create account
    account = await authenticated_client.create_account({
        "name": "Test Account",
        "broker": "Test Broker",
        "account_number": "ACC123"
    })

    # Validate response
    assert validator.validate_account_response(account)
```

## Important Implementation Details

### Authentication Flow

1. User registers via `/auth/register` → password is hashed with bcrypt
2. User logs in via `/auth/login` → JWT token returned
3. Protected routes require `Authorization: Bearer <token>` header
4. Middleware validates token and populates `request.ctx.user`
5. User can refresh token via `/auth/refresh` using refresh_token

### Database Schema

The database uses the `monitoring_options_operations` schema in Supabase. Key tables:
- `users` - User accounts
- `accounts` - Trading accounts (brokerage accounts)
- `assets` - Stocks/ETFs being tracked
- `options` - Options positions
- `rules` - Monitoring rules for alerts
- `alerts` - Generated alerts from rules
- `alert_logs` - History of alert processing

**Important:** All queries must specify the schema via Supabase client configuration or be executed against the correct schema.

### Model Definitions

All Pydantic models are in `app/database/models.py` (80+ models). When adding new endpoints:
1. Create request/response models in `models.py`
2. Use these models for validation in routes
3. Document models with docstrings for OpenAPI generation

### Error Handling

Custom exceptions are in `app/core/exceptions.py`. The error handler middleware (`app/middleware/error_handler.py`) catches these and returns appropriate HTTP responses:

```python
from app.core.exceptions import NotFoundError, ValidationError

# In route
if not account:
    raise NotFoundError("Account not found")
```

### OpenAPI Documentation

API documentation is available at:
- Interactive docs (Scalar): http://localhost:8000/scalar
- OpenAPI spec: http://localhost:8000/api/docs/openapi.json

Routes should include OpenAPI decorators for documentation:
```python
from sanic_ext import openapi

@bp.get("/api/accounts")
@openapi.summary("List all accounts")
@openapi.description("Returns all accounts for the authenticated user")
@openapi.response(200, {"application/json": list[AccountResponse]})
async def list_accounts(request):
    ...
```

## Common Gotchas

1. **Always use `python -m app.main`** to start the server, not `python app/main.py` (module import issues)

2. **Repository methods are async** - Always await them:
   ```python
   accounts = await repo.list_by_user(user_id)  # ✓ Correct
   accounts = repo.list_by_user(user_id)        # ✗ Wrong
   ```

3. **Test fixtures create real database records** - They include cleanup via `yield`, but may leave data if tests crash

4. **E2E tests require server running** - Start with `python -m app.main` in a separate terminal before running E2E tests

5. **Supabase client initialization** - There's a known warning about `http_client` parameter in `SyncPostgrestClient`. This is non-blocking and doesn't affect functionality.

6. **JWT tokens expire** - Default expiration is in settings. Integration tests create fresh tokens for each test.

## Environment Variables

Key variables in `.env` (see `.env.example` for full list):
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key
- `DATABASE_URL` - PostgreSQL connection string
- `DB_SCHEMA` - Database schema name (default: `monitoring_options_operations`)
- `ENV` - Environment (development/production)
- `DEBUG` - Enable debug mode (true/false)
- `COMM_API_URL` - WhatsApp communications API URL
- `COMM_CLIENT_ID`, `COMM_EMAIL`, `COMM_PASSWORD` - Communications API credentials

## Documentation Files

- `README.md` - Setup and quick start guide
- `DOCUMENTATION.md` - Complete API documentation guide
- `API_ENDPOINTS.md` - Detailed endpoint reference (58 endpoints)
- `TESTING.md` - Testing guide (unit + integration)
- `tests_e2e/README.md` - E2E testing guide with Playwright
- `TROUBLESHOOTING_SCALAR.md` - Scalar docs troubleshooting

## Git Workflow

The project uses conventional commits:
```bash
git commit -m "feat: Add new endpoint for X"
git commit -m "fix: Resolve issue with Y"
git commit -m "test: Add E2E tests for Z"
```

Always include co-author footer:
```
🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```