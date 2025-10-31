"""Roll preview and management routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.services.roll_calculator import roll_calculator
from app.database.repositories.options import OptionsRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


rolls_bp = Blueprint("rolls", url_prefix="/api/rolls")


@rolls_bp.post("/preview")
@openapi.tag("Rolls")
@openapi.summary("Get roll preview with suggestions")
@openapi.description("Get roll preview with suggestions for a position")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Roll preview with suggestions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@openapi.response(422, description="Validation error")
@require_auth
async def get_roll_preview(request: Request):
    """
    Get roll preview with suggestions for a position.

    Request Body:
        {
            "option_position_id": "uuid",
            "market_data": {  // optional
                "current_price": 98.50,
                "bid": 98.45,
                "ask": 98.55
            }
        }

    Returns:
        200: Roll preview with suggestions
        401: Not authenticated
        403: Not authorized
        404: Position not found
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        data = request.json
        position_id = UUID(data.get("option_position_id"))
        market_data = data.get("market_data")

        # Check ownership
        position = await OptionsRepository.get_user_position(position_id, user_id)
        if not position:
            raise NotFoundError("Position", str(position_id))

        # Generate roll preview
        preview = await roll_calculator.get_roll_preview(
            position_id,
            market_data,
            auth_user_id=user_id
        )

        logger.info(
            "Roll preview generated",
            user_id=str(user_id),
            position_id=str(position_id),
            suggestions=len(preview["suggestions"])
        )

        return response.json(preview, status=200)

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to generate roll preview", error=str(e))
        raise ValidationError(f"Failed to generate roll preview: {str(e)}")


@rolls_bp.get("/suggestions/<position_id:uuid>")
@openapi.tag("Rolls")
@openapi.summary("Get roll suggestions for position")
@openapi.description("Get roll suggestions for a position (simplified endpoint)")
@openapi.parameter("position_id", str, "path", description="Option position UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Roll suggestions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@require_auth
async def get_roll_suggestions(request: Request, position_id: UUID):
    """
    Get roll suggestions for a position (simplified endpoint).

    Returns:
        200: Roll suggestions
        401: Not authenticated
        403: Not authorized
        404: Position not found
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        position_uuid = position_id if isinstance(position_id, UUID) else UUID(str(position_id))

        # Check ownership
        position = await OptionsRepository.get_user_position(position_uuid, user_id)
        if not position:
            raise NotFoundError("Position", position_id)

        # Generate preview
        preview = await roll_calculator.get_roll_preview(position_uuid, auth_user_id=user_id)

        # Return only suggestions
        return response.json(
            {
                "position_id": str(position_uuid),
                "suggestions": preview["suggestions"],
                "current_metrics": {
                    "dte": preview["current_position"].get("dte"),
                    "otm_pct": preview["current_position"].get("otm_pct"),
                    "current_price": preview["current_position"].get("current_price")
                }
            },
            status=200
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get roll suggestions", error=str(e))
        raise ValidationError(f"Failed to get roll suggestions: {str(e)}")


@rolls_bp.get("/analysis/<account_id:uuid>")
@openapi.tag("Rolls")
@openapi.summary("Get account roll analysis")
@openapi.description("Get roll analysis for all open positions in an account")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Roll analysis for account")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_account_roll_analysis(request: Request, account_id: UUID):
    """
    Get roll analysis for all open positions in an account.

    Returns:
        200: Roll analysis for account
        401: Not authenticated
        403: Not authorized
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        account_uuid = account_id if isinstance(account_id, UUID) else UUID(str(account_id))

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        # Get all open positions
        open_positions = await OptionsRepository.get_open_positions(account_uuid, auth_user_id=user_id)

        analysis = []

        for position in open_positions:
            try:
                # Generate preview for each position
                preview = await roll_calculator.get_roll_preview(
                    UUID(position["id"]),
                    auth_user_id=user_id
                )

                # Get best suggestion
                best_suggestion = preview["suggestions"][0] if preview["suggestions"] else None

                analysis.append({
                    "position_id": position["id"],
                    "ticker": position.get("ticker"),
                    "strike": position.get("strike"),
                    "expiration": position.get("expiration"),
                    "side": position.get("side"),
                    "current_metrics": {
                        "dte": preview["current_position"].get("dte"),
                        "otm_pct": preview["current_position"].get("otm_pct"),
                        "pnl": preview["current_position"].get("pnl")
                    },
                    "best_suggestion": best_suggestion,
                    "total_suggestions": len(preview["suggestions"])
                })

            except Exception as e:
                logger.warning(
                    "Failed to analyze position",
                    position_id=position["id"],
                    error=str(e)
                )
                continue

        logger.info(
            "Account roll analysis completed",
            user_id=str(user_id),
            account_id=str(account_id),
            positions_analyzed=len(analysis)
        )

        return response.json(
            {
                "account_id": str(account_uuid),
                "positions": analysis,
                "total_positions": len(analysis)
            },
            status=200
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get account roll analysis", error=str(e))
        raise ValidationError(f"Failed to get account roll analysis: {str(e)}")
