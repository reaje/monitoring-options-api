"""Equity positions routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.database.repositories.equity import EquityRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.assets import AssetsRepository
from app.database.models import EquityPositionCreate, EquityPositionUpdate
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


equity_bp = Blueprint("equity", url_prefix="/api/equity")


@equity_bp.get("/")
@openapi.tag("Equity")
@openapi.summary("List equity positions")
@openapi.description("Get all equity (stock) positions for user's accounts with optional filters")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.parameter("asset_id", str, "query", required=False, description="Filter by asset UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of equity positions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account/asset")
@require_auth
async def get_equities(request: Request):
    user = request.ctx.user
    user_id = UUID(user["id"])

    account_id_param = request.args.get("account_id")
    asset_id_param = request.args.get("asset_id")

    positions = []

    if account_id_param:
        account_uuid = UUID(account_id_param)
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")
        positions = await EquityRepository.get_by_account_id(account_uuid, auth_user_id=user_id)
    elif asset_id_param:
        asset_uuid = UUID(asset_id_param)
        if not await AssetsRepository.user_owns_asset(asset_uuid, user_id):
            raise AuthorizationError("Not authorized to access this asset")
        positions = await EquityRepository.get_by_asset_id(asset_uuid, auth_user_id=user_id)
    else:
        accounts = await AccountsRepository.get_by_user_id(user_id)
        for account in accounts:
            account_positions = await EquityRepository.get_by_account_id(UUID(account["id"]), auth_user_id=user_id)
            positions.extend(account_positions)

    logger.info("Retrieved user equity positions", user_id=str(user_id), count=len(positions))
    return response.json({"positions": positions, "total": len(positions)}, status=200)


@equity_bp.post("/")
@openapi.tag("Equity")
@openapi.summary("Create equity position")
@openapi.description("Create or upsert an equity position (shares)")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": EquityPositionCreate})
@openapi.response(201, description="Equity position created successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to create positions in this account")
@openapi.response(422, description="Validation error")
@require_auth
async def create_equity(request: Request):
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        data = EquityPositionCreate(**request.json)

        if not await AccountsRepository.user_owns_account(data.account_id, user_id):
            raise AuthorizationError("Not authorized to create positions in this account")
        if not await AssetsRepository.user_owns_asset(data.asset_id, user_id):
            raise AuthorizationError("Not authorized to use this asset")

        position = await EquityRepository.create(data.model_dump(), auth_user_id=user_id)
        logger.info("Equity position created", user_id=str(user_id), position_id=position["id"]) 
        return response.json({"message": "Equity position created successfully", "position": position}, status=201)
    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create equity position", error=str(e))
        raise ValidationError(f"Failed to create equity position: {str(e)}")


@equity_bp.get("/<equity_id:uuid>")
@openapi.tag("Equity")
@openapi.summary("Get equity position by ID")
@openapi.description("Retrieve details of a specific equity position")
@openapi.parameter("equity_id", str, "path", description="Equity UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Equity details")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Equity not found")
@require_auth
async def get_equity(request: Request, equity_id: str):
    user = request.ctx.user
    user_id = UUID(user["id"])
    eq_uuid = UUID(equity_id)

    position = await EquityRepository.get_user_equity(eq_uuid, user_id)
    if not position:
        raise NotFoundError("Equity", equity_id)
    return response.json({"position": position}, status=200)


@equity_bp.put("/<equity_id:uuid>")
@openapi.tag("Equity")
@openapi.summary("Update equity position")
@openapi.description("Update equity position fields (quantity, avg_price)")
@openapi.parameter("equity_id", str, "path", description="Equity UUID")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": EquityPositionUpdate})
@openapi.response(200, description="Equity updated successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Equity not found")
@openapi.response(422, description="Validation error")
@require_auth
async def update_equity(request: Request, equity_id: str):
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        eq_uuid = UUID(equity_id)

        existing = await EquityRepository.get_user_equity(eq_uuid, user_id)
        if not existing:
            raise NotFoundError("Equity", equity_id)

        data = EquityPositionUpdate(**request.json)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields to update")

        position = await EquityRepository.update(eq_uuid, update_data, auth_user_id=user_id)
        logger.info("Equity updated", user_id=str(user_id), equity_id=equity_id)
        return response.json({"message": "Equity updated successfully", "position": position}, status=200)
    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update equity", error=str(e))
        raise ValidationError(f"Failed to update equity: {str(e)}")


@equity_bp.delete("/<equity_id:uuid>")
@openapi.tag("Equity")
@openapi.summary("Delete equity position")
@openapi.description("Delete an equity position")
@openapi.parameter("equity_id", str, "path", description="Equity UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Equity deleted successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Equity not found")
@require_auth
async def delete_equity(request: Request, equity_id: str):
    user = request.ctx.user
    user_id = UUID(user["id"])
    eq_uuid = UUID(equity_id)

    existing = await EquityRepository.get_user_equity(eq_uuid, user_id)
    if not existing:
        raise NotFoundError("Equity", equity_id)

    await EquityRepository.delete(eq_uuid, auth_user_id=user_id)
    logger.info("Equity deleted", user_id=str(user_id), equity_id=equity_id)
    return response.json({"message": "Equity deleted successfully"}, status=200)

