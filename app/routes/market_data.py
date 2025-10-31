"""Market data routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from app.services.market_data import market_data_provider
from app.core.logger import logger
from app.core.exceptions import ValidationError, AppException
from app.middleware.auth_middleware import require_auth


market_data_bp = Blueprint("market_data", url_prefix="/api/market")


@market_data_bp.get("/quote/<ticker>")
@openapi.tag("Market Data")
@openapi.summary("Get current quote for a ticker")
@openapi.description("Retrieve real-time quote data including price, bid, ask, volume, and market status")
@openapi.parameter("ticker", str, "path", description="Stock ticker symbol (e.g., PETR4, VALE3)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Quote data retrieved successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error")
@openapi.response(503, description="Market data unavailable (MT5 offline/stale)")
@require_auth
async def get_quote(request: Request, ticker: str):
    """
    Get current quote for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g., PETR4, VALE3)

    Returns:
        200: Quote data
        401: Not authenticated
        422: Validation error
    """
    try:
        ticker = ticker.upper()

        quote = await market_data_provider.get_quote(ticker)

        logger.info(
            "Quote retrieved",
            ticker=ticker,
            price=quote.get("current_price"),
            user_id=request.ctx.user["id"]
        )

        return response.json(quote, status=200)

    except AppException:
        # Deixe AppExceptions (inclui MarketDataUnavailableError=503) propagarem para o handler global
        raise
    except Exception as e:
        logger.error("Failed to get quote", ticker=ticker, error=str(e))
        raise ValidationError(f"Failed to get quote: {str(e)}")


@market_data_bp.get("/options/<ticker>")
@openapi.tag("Market Data")
@openapi.summary("Get option chain")
@openapi.description("Retrieve complete option chain for a ticker with calls and puts")
@openapi.parameter("ticker", str, "path", description="Stock ticker symbol")
@openapi.parameter("expiration", str, "query", required=False, description="Filter by expiration date (YYYY-MM-DD)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Option chain data")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error")
@require_auth
async def get_option_chain(request: Request, ticker: str):
    """
    Get option chain for a ticker.

    Query Parameters:
        expiration (optional): Filter by expiration date (YYYY-MM-DD)

    Returns:
        200: Option chain data
        401: Not authenticated
        422: Validation error
    """
    try:
        ticker = ticker.upper()
        expiration = request.args.get("expiration")

        chain = await market_data_provider.get_option_chain(ticker, expiration)

        logger.info(
            "Option chain retrieved",
            ticker=ticker,
            expiration_filter=expiration,
            calls_count=len(chain.get("calls", [])),
            puts_count=len(chain.get("puts", [])),
            user_id=request.ctx.user["id"]
        )

        return response.json(chain, status=200)

    except AppException:
        raise
    except Exception as e:
        logger.error("Failed to get option chain", ticker=ticker, error=str(e))
        raise ValidationError(f"Failed to get option chain: {str(e)}")


@market_data_bp.get("/options/<ticker>/quote")
@openapi.tag("Market Data")
@openapi.summary("Get option quote")
@openapi.description("Get quote for a specific option contract")
@openapi.parameter("ticker", str, "path", description="Stock ticker symbol")
@openapi.parameter("strike", float, "query", required=True, description="Strike price")
@openapi.parameter("expiration", str, "query", required=True, description="Expiration date (YYYY-MM-DD)")
@openapi.parameter("type", str, "query", required=True, description="Option type: CALL or PUT")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Option quote with premium and greeks")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error")
@require_auth
async def get_option_quote(request: Request, ticker: str):
    """
    Get quote for a specific option.

    Query Parameters:
        strike: Strike price (required)
        expiration: Expiration date YYYY-MM-DD (required)
        type: Option type CALL or PUT (required)

    Returns:
        200: Option quote
        401: Not authenticated
        422: Validation error
    """
    try:
        ticker = ticker.upper()
        strike = float(request.args.get("strike"))
        expiration = request.args.get("expiration")
        option_type = request.args.get("type", "CALL").upper()

        if not strike or not expiration:
            raise ValidationError("strike and expiration are required")

        if option_type not in ["CALL", "PUT"]:
            raise ValidationError("type must be CALL or PUT")

        option_quote = await market_data_provider.get_option_quote(
            ticker, strike, expiration, option_type
        )

        logger.info(
            "Option quote retrieved",
            ticker=ticker,
            strike=strike,
            type=option_type,
            premium=option_quote.get("premium"),
            user_id=request.ctx.user["id"]
        )

        return response.json(option_quote, status=200)

    except ValidationError:
        raise
    except AppException:
        raise
    except Exception as e:
        logger.error("Failed to get option quote", ticker=ticker, error=str(e))
        raise ValidationError(f"Failed to get option quote: {str(e)}")


@market_data_bp.get("/options/<ticker>/greeks")
@openapi.tag("Market Data")
@openapi.summary("Get option greeks")
@openapi.description("Calculate greeks (delta, gamma, theta, vega, rho) for a specific option")
@openapi.parameter("ticker", str, "path", description="Stock ticker symbol")
@openapi.parameter("strike", float, "query", required=True, description="Strike price")
@openapi.parameter("expiration", str, "query", required=True, description="Expiration date (YYYY-MM-DD)")
@openapi.parameter("type", str, "query", required=True, description="Option type: CALL or PUT")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Option greeks")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error")
@require_auth
async def get_greeks(request: Request, ticker: str):
    """
    Get greeks for a specific option.

    Query Parameters:
        strike: Strike price (required)
        expiration: Expiration date YYYY-MM-DD (required)
        type: Option type CALL or PUT (required)

    Returns:
        200: Greeks data
        401: Not authenticated
        422: Validation error
    """
    try:
        ticker = ticker.upper()
        strike = float(request.args.get("strike"))
        expiration = request.args.get("expiration")
        option_type = request.args.get("type", "CALL").upper()

        if not strike or not expiration:
            raise ValidationError("strike and expiration are required")

        if option_type not in ["CALL", "PUT"]:
            raise ValidationError("type must be CALL or PUT")

        greeks = await market_data_provider.get_greeks(
            ticker, strike, expiration, option_type
        )

        logger.info(
            "Greeks retrieved",
            ticker=ticker,
            strike=strike,
            type=option_type,
            delta=greeks.get("delta"),
            user_id=request.ctx.user["id"]
        )

        return response.json(greeks, status=200)

    except ValidationError:
        raise
    except AppException:
        raise
    except Exception as e:
        logger.error("Failed to get greeks", ticker=ticker, error=str(e))
        raise ValidationError(f"Failed to get greeks: {str(e)}")


@market_data_bp.get("/health")
@openapi.tag("Market Data")
@openapi.summary("Check market data provider health")
@openapi.description("Verify that the market data provider is functioning correctly")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Provider is healthy")
@openapi.response(401, description="Not authenticated")
@openapi.response(503, description="Provider is unhealthy")
@require_auth
async def market_data_health(request: Request):
    """
    Check market data provider health.

    Returns:
        200: Health status
        401: Not authenticated
    """
    try:
        is_healthy = await market_data_provider.health_check()

        return response.json(
            {
                "provider": "mock",  # or get from config
                "healthy": is_healthy,
                "timestamp": "timestamp"
            },
            status=200 if is_healthy else 503
        )

    except Exception as e:
        logger.error("Market data health check failed", error=str(e))
        return response.json(
            {
                "provider": "mock",
                "healthy": False,
                "error": str(e)
            },
            status=503
        )
