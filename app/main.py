"""Main application entry point."""

from sanic import Sanic, response
from sanic_ext import Extend
from app.config import settings
from app.core.logger import setup_logger, logger
from app.middleware.error_handler import setup_error_handlers
from app.middleware.auth_middleware import setup_auth_middleware
from app.database.supabase_client import SupabaseClient
from app.routes.auth import auth_bp
from app.routes.accounts import accounts_bp
from app.routes.assets import assets_bp
from app.routes.options import options_bp
from app.routes.equity import equity_bp

from app.routes.rules import rules_bp
from app.routes.alerts import alerts_bp
from app.routes.notifications import notifications_bp
from app.routes.workers import workers_bp
from app.routes.rolls import rolls_bp
from app.routes.market_data import market_data_bp
from app.workers.scheduler import worker_scheduler
from datetime import datetime

# MT5 bridge blueprint (optional)
try:
    from MT5.bridge_blueprint import mt5_bridge_bp
    logger.info("MT5 bridge blueprint imported successfully")
except Exception as e:
    logger.warning(f"MT5 bridge blueprint not available: {e}")
    mt5_bridge_bp = None


# Create Sanic app
app = Sanic("monitoring_options_api")

# Configure CORS
app.config.CORS_ORIGINS = settings.cors_origins_list
app.config.CORS_SUPPORTS_CREDENTIALS = True
app.config.CORS_AUTOMATIC_OPTIONS = True
app.config.CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
app.config.CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "Accept"]

# Configure OpenAPI
app.config.OAS_UI_DEFAULT = None  # Disable default Swagger UI
app.config.OAS_URL_PREFIX = "/api/docs"
app.config.OAS_IGNORE_HEAD = True
app.config.OAS_IGNORE_OPTIONS = True

# Enable Sanic extensions (CORS, OpenAPI, etc)
Extend(
    app,
    config={
        "oas": True,
        "oas_ui_default": None,  # We'll use Scalar instead
        "cors": True,
        "cors_origins": settings.cors_origins_list,
        "cors_supports_credentials": True,
        "cors_automatic_options": True,
    },
)

# Setup logging
setup_logger(app)

# Setup error handlers
setup_error_handlers(app)

# Setup authentication middleware
setup_auth_middleware(app)

# Configure OpenAPI metadata
app.ext.openapi.describe(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
)
app.ext.openapi.add_security_scheme(
    "BearerAuth",
    "http",
    scheme="bearer",
    bearer_format="JWT",
)
app.ext.openapi.secured("BearerAuth")

# Register blueprints
app.blueprint(auth_bp)
app.blueprint(accounts_bp)
app.blueprint(assets_bp)
app.blueprint(options_bp)
app.blueprint(equity_bp)

app.blueprint(rules_bp)
app.blueprint(alerts_bp)
app.blueprint(notifications_bp)
app.blueprint(workers_bp)
app.blueprint(rolls_bp)
app.blueprint(market_data_bp)

# Optionally register MT5 bridge endpoints
if mt5_bridge_bp is not None:
    app.blueprint(mt5_bridge_bp)
    logger.info("MT5 bridge blueprint registered successfully")
else:
    logger.warning("MT5 bridge blueprint not registered (import failed)")


# =====================================
# LIFECYCLE HOOKS
# =====================================


@app.before_server_start
async def setup_db(app, loop):
    """Initialize database connections before server starts."""
    logger.info("Setting up database connections...")

    try:
        # Test Supabase connection
        if SupabaseClient.test_connection():
            logger.info("Database connection established successfully")
        else:
            logger.warning("Database connection test failed")
    except Exception as e:
        logger.error("Failed to setup database", error=str(e))
        raise


@app.after_server_start
async def notify_server_started(app, loop):
    """Log message after server starts."""
    logger.info(
        "Server started successfully",
        host=settings.HOST,
        port=settings.PORT,
        env=settings.ENV,
        debug=settings.DEBUG,
    )

    # Start background workers
    logger.info("Starting background workers...")
    worker_scheduler.start()
    logger.info("Background workers started")


@app.before_server_stop
async def notify_server_stopping(app, loop):
    """Log message before server stops."""
    logger.info("Server is shutting down...")

    # Stop background workers
    logger.info("Stopping background workers...")
    worker_scheduler.stop()
    logger.info("Background workers stopped")


# =====================================
# HEALTH CHECK ENDPOINT
# =====================================


@app.get("/health")
async def health_check(request):
    """
    Health check endpoint.

    Returns:
        JSON response with server status
    """
    # Test database connection
    db_healthy = SupabaseClient.test_connection()

    status = "healthy" if db_healthy else "degraded"
    status_code = 200 if db_healthy else 503

    return response.json(
        {
            "status": status,
            "version": settings.API_VERSION,
            "environment": settings.ENV,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {
                "database": "ok" if db_healthy else "failed",
            },
        },
        status=status_code,
    )


@app.get("/")
async def root(request):
    """
    Root endpoint with API information.

    Returns:
        JSON response with API information
    """
    return response.json(
        {
            "name": settings.API_TITLE,
            "version": settings.API_VERSION,
            "description": settings.API_DESCRIPTION,
            "docs_url": "/docs" if settings.ENABLE_DOCS else None,
            "scalar_docs": "/scalar" if settings.ENABLE_DOCS else None,
            "openapi_spec": "/api/docs/openapi.json",
            "health_check": "/health",
        }
    )


@app.get("/scalar")
async def scalar_docs(request):
    """
    Scalar API documentation interface.

    Returns:
        HTML page with Scalar documentation UI
    """
    if not settings.ENABLE_DOCS:
        return response.text("Documentation is disabled", status=404)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{settings.API_TITLE} - API Documentation</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <!-- Scalar API Reference -->
    <script
        id="api-reference"
        data-url="/api/docs/openapi.json"
    ></script>

    <!-- Latest Scalar version from CDN -->
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>

    <!-- Alternative: Specific version -->
    <!-- <script src="https://unpkg.com/@scalar/api-reference@latest"></script> -->

    <script>
        // Optional: Custom configuration
        const configuration = {{
            theme: 'purple',
            layout: 'modern',
            showSidebar: true,
            darkMode: true,
            searchHotKey: 'k',
            customCss: `
                body {{
                    margin: 0;
                    padding: 0;
                }}
            `
        }};

        // Apply configuration
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Scalar API Reference loaded');
        }});
    </script>
</body>
</html>"""
    return response.html(html_content)


# =====================================
# RUN APPLICATION
# =====================================


if __name__ == "__main__":
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG,
        auto_reload=settings.DEBUG,
        access_log=settings.DEBUG,
    )
