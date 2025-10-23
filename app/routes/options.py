"""Options positions routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.database.repositories.options import OptionsRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.assets import AssetsRepository
from app.database.models import OptionPositionCreate, OptionPositionUpdate
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


options_bp = Blueprint("options", url_prefix="/api/options")


@options_bp.get("/")
@openapi.tag("Options")
@openapi.summary("List option positions")
@openapi.description("Get all option positions for user's accounts with optional filters")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.parameter("asset_id", str, "query", required=False, description="Filter by asset UUID")
@openapi.parameter("status", str, "query", required=False, description="Filter by status (OPEN, CLOSED, EXPIRED)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of option positions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account/asset")
@require_auth
async def get_options(request: Request):
    """
    Get all option positions for user's accounts.

    Query Parameters:
        account_id (optional): Filter by account ID
        asset_id (optional): Filter by asset ID
        status (optional): Filter by status (OPEN, CLOSED, EXPIRED)

    Returns:
        200: List of positions
        401: Not authenticated
    """
    user = request.ctx.user
    user_id = UUID(user["id"])

    # Get optional filters
    account_id_param = request.args.get("account_id")
    asset_id_param = request.args.get("asset_id")
    status_param = request.args.get("status")

    positions = []

    if account_id_param:
        # Get positions for specific account
        account_uuid = UUID(account_id_param)

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        positions = await OptionsRepository.get_by_account_id(
            account_uuid,
            status=status_param
        )

    elif asset_id_param:
        # Get positions for specific asset
        asset_uuid = UUID(asset_id_param)

        # Check ownership
        if not await AssetsRepository.user_owns_asset(asset_uuid, user_id):
            raise AuthorizationError("Not authorized to access this asset")

        positions = await OptionsRepository.get_by_asset_id(
            asset_uuid,
            status=status_param
        )

    else:
        # Get all accounts for user
        accounts = await AccountsRepository.get_by_user_id(user_id)

        # Get positions for all user accounts
        for account in accounts:
            account_positions = await OptionsRepository.get_by_account_id(
                UUID(account["id"]),
                status=status_param
            )
            positions.extend(account_positions)

    logger.info(
        "Retrieved user option positions",
        user_id=str(user_id),
        count=len(positions),
    )

    return response.json(
        {
            "positions": positions,
            "total": len(positions),
        },
        status=200,
    )


@options_bp.get("/active")
@openapi.tag("Options")
@openapi.summary("List active option positions")
@openapi.description("Get all active (OPEN) option positions for user")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of open positions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_active_options(request: Request):
    """
    Get all active (OPEN) option positions for user.

    Query Parameters:
        account_id (optional): Filter by account ID

    Returns:
        200: List of open positions
        401: Not authenticated
    """
    user = request.ctx.user
    user_id = UUID(user["id"])

    account_id_param = request.args.get("account_id")

    if account_id_param:
        account_uuid = UUID(account_id_param)

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        positions = await OptionsRepository.get_open_positions(account_uuid)
    else:
        # Get all accounts and their open positions
        accounts = await AccountsRepository.get_by_user_id(user_id)
        positions = []

        for account in accounts:
            account_positions = await OptionsRepository.get_open_positions(
                UUID(account["id"])
            )
            positions.extend(account_positions)

    return response.json(
        {
            "positions": positions,
            "total": len(positions),
        },
        status=200,
    )


@options_bp.post("/")
@openapi.tag("Options")
@openapi.summary("Create new option position")
@openapi.description("Create a new option position (covered call, short put, etc.)")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": OptionPositionCreate})
@openapi.response(201, description="Position created successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to create positions in this account")
@openapi.response(422, description="Validation error")
@require_auth
async def create_option(request: Request):
    """
    Create a new option position.

    Request Body:
        {
            "account_id": "uuid",
            "asset_id": "uuid",
            "side": "CALL" | "PUT",
            "strategy": "COVERED_CALL" | "SHORT_PUT" | "LONG_PUT" | "OTHER",
            "strike": 100.00,
            "expiration": "2025-03-15",
            "quantity": 100,
            "avg_premium": 2.50,
            "notes": "Optional notes"
        }

    Returns:
        201: Position created
        401: Not authenticated
        403: Not authorized
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        # Validate request data
        data = OptionPositionCreate(**request.json)

        # Check account ownership
        if not await AccountsRepository.user_owns_account(data.account_id, user_id):
            raise AuthorizationError(
                "Not authorized to create positions in this account"
            )

        # Check asset ownership
        if not await AssetsRepository.user_owns_asset(data.asset_id, user_id):
            raise AuthorizationError("Not authorized to use this asset")

        # Create position
        position = await OptionsRepository.create(data.model_dump())

        logger.info(
            "Option position created",
            user_id=str(user_id),
            position_id=position["id"],
            side=position["side"],
            strike=position["strike"],
        )

        return response.json(
            {
                "message": "Position created successfully",
                "position": position,
            },
            status=201,
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create position", error=str(e))
        raise ValidationError(f"Failed to create position: {str(e)}")


@options_bp.get("/<position_id:uuid>")
@openapi.tag("Options")
@openapi.summary("Get option position by ID")
@openapi.description("Retrieve details of a specific option position")
@openapi.parameter("position_id", str, "path", description="Position UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Position details")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@require_auth
async def get_option(request: Request, position_id: str):
    """
    Get option position details.

    Returns:
        200: Position details
        401: Not authenticated
        403: Not authorized
        404: Position not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    position_uuid = UUID(position_id)

    # Get position with ownership check
    position = await OptionsRepository.get_user_position(position_uuid, user_id)

    if not position:
        raise NotFoundError("Position", position_id)

    logger.info(
        "Retrieved position details",
        user_id=str(user_id),
        position_id=position_id,
    )

    return response.json(
        {"position": position},
        status=200,
    )


@options_bp.put("/<position_id:uuid>")
@openapi.tag("Options")
@openapi.summary("Update option position")
@openapi.description("Update option position information")
@openapi.parameter("position_id", str, "path", description="Position UUID")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": OptionPositionUpdate})
@openapi.response(200, description="Position updated successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@openapi.response(422, description="Validation error")
@require_auth
async def update_option(request: Request, position_id: str):
    """
    Update an option position.

    Request Body:
        {
            "strike": 105.00,
            "quantity": 200,
            "avg_premium": 3.00,
            "status": "CLOSED",
            "notes": "Updated notes"
        }

    Returns:
        200: Position updated
        401: Not authenticated
        403: Not authorized
        404: Position not found
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        position_uuid = UUID(position_id)

        # Check ownership
        existing = await OptionsRepository.get_user_position(position_uuid, user_id)
        if not existing:
            raise NotFoundError("Position", position_id)

        # Validate request data
        data = OptionPositionUpdate(**request.json)

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields to update")

        # Update position
        position = await OptionsRepository.update(position_uuid, update_data)

        logger.info(
            "Position updated",
            user_id=str(user_id),
            position_id=position_id,
        )

        return response.json(
            {
                "message": "Position updated successfully",
                "position": position,
            },
            status=200,
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update position", error=str(e))
        raise ValidationError(f"Failed to update position: {str(e)}")


@options_bp.delete("/<position_id:uuid>")
@openapi.tag("Options")
@openapi.summary("Delete option position")
@openapi.description("Delete an option position")
@openapi.parameter("position_id", str, "path", description="Position UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Position deleted successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@require_auth
async def delete_option(request: Request, position_id: str):
    """
    Delete an option position.

    Returns:
        200: Position deleted
        401: Not authenticated
        403: Not authorized
        404: Position not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    position_uuid = UUID(position_id)

    # Check ownership
    existing = await OptionsRepository.get_user_position(position_uuid, user_id)
    if not existing:
        raise NotFoundError("Position", position_id)

    # Delete position
    await OptionsRepository.delete(position_uuid)

    logger.info(
        "Position deleted",
        user_id=str(user_id),
        position_id=position_id,
    )

    return response.json(
        {"message": "Position deleted successfully"},
        status=200,
    )


@options_bp.post("/<position_id:uuid>/close")
@openapi.tag("Options")
@openapi.summary("Close option position")
@openapi.description("Close an option position (set status to CLOSED)")
@openapi.parameter("position_id", str, "path", description="Position UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Position closed successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@require_auth
async def close_option(request: Request, position_id: str):
    """
    Close an option position (set status to CLOSED).

    Returns:
        200: Position closed
        401: Not authenticated
        403: Not authorized
        404: Position not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    position_uuid = UUID(position_id)

    # Check ownership
    existing = await OptionsRepository.get_user_position(position_uuid, user_id)
    if not existing:
        raise NotFoundError("Position", position_id)

    # Close position
    position = await OptionsRepository.close_position(position_uuid)

    logger.info(
        "Position closed",
        user_id=str(user_id),
        position_id=position_id,
    )

    return response.json(
        {
            "message": "Position closed successfully",
            "position": position,
        },
        status=200,
    )


@options_bp.get("/statistics/<account_id:uuid>")
@openapi.tag("Options")
@openapi.summary("Get option statistics")
@openapi.description("Get statistics for account option positions")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Statistics for option positions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_statistics(request: Request, account_id: str):
    """
    Get statistics for account positions.

    Returns:
        200: Statistics
        401: Not authenticated
        403: Not authorized
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    account_uuid = UUID(account_id)

    # Check ownership
    if not await AccountsRepository.user_owns_account(account_uuid, user_id):
        raise AuthorizationError("Not authorized to access this account")

    # Get statistics
    stats = await OptionsRepository.get_statistics(account_uuid)

    return response.json(
        {"statistics": stats},
        status=200,
    )
