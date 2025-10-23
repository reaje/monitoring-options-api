"""Assets routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.database.repositories.assets import AssetsRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.models import AssetCreate, AssetUpdate
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


assets_bp = Blueprint("assets", url_prefix="/api/assets")


@assets_bp.get("/")
@openapi.tag("Assets")
@openapi.summary("List user assets")
@openapi.description("Get all assets for user's accounts, optionally filtered by account")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of assets")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_assets(request: Request):
    """
    Get all assets for user's accounts.

    Query Parameters:
        account_id (optional): Filter by account ID

    Returns:
        200: List of assets
        401: Not authenticated
    """
    user = request.ctx.user
    user_id = UUID(user["id"])

    # Get optional account_id filter
    account_id_param = request.args.get("account_id")

    if account_id_param:
        # Get assets for specific account
        account_uuid = UUID(account_id_param)

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        assets = await AssetsRepository.get_by_account_id(account_uuid)
    else:
        # Get all accounts for user
        accounts = await AccountsRepository.get_by_user_id(user_id)

        # Get assets for all user accounts
        assets = []
        for account in accounts:
            account_assets = await AssetsRepository.get_by_account_id(
                UUID(account["id"])
            )
            assets.extend(account_assets)

    logger.info(
        "Retrieved user assets",
        user_id=str(user_id),
        count=len(assets),
    )

    return response.json(
        {
            "assets": assets,
            "total": len(assets),
        },
        status=200,
    )


@assets_bp.post("/")
@openapi.tag("Assets")
@openapi.summary("Create new asset")
@openapi.description("Create a new asset in an account")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": AssetCreate})
@openapi.response(201, description="Asset created successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to create assets in this account")
@openapi.response(422, description="Validation error or asset already exists")
@require_auth
async def create_asset(request: Request):
    """
    Create a new asset.

    Request Body:
        {
            "ticker": "PETR4",
            "account_id": "uuid"
        }

    Returns:
        201: Asset created
        401: Not authenticated
        403: Not authorized
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        # Validate request data
        data = AssetCreate(**request.json)

        # Check account ownership
        if not await AccountsRepository.user_owns_account(data.account_id, user_id):
            raise AuthorizationError("Not authorized to create assets in this account")

        # Check if asset already exists for this account
        existing = await AssetsRepository.get_by_ticker(
            data.account_id,
            data.ticker
        )
        if existing:
            raise ValidationError(
                f"Asset {data.ticker} already exists in this account"
            )

        # Create asset
        asset = await AssetsRepository.create(data.model_dump())

        logger.info(
            "Asset created",
            user_id=str(user_id),
            asset_id=asset["id"],
            ticker=asset["ticker"],
        )

        return response.json(
            {
                "message": "Asset created successfully",
                "asset": asset,
            },
            status=201,
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create asset", error=str(e))
        raise ValidationError(f"Failed to create asset: {str(e)}")


@assets_bp.get("/<asset_id:uuid>")
@openapi.tag("Assets")
@openapi.summary("Get asset by ID")
@openapi.description("Retrieve details of a specific asset")
@openapi.parameter("asset_id", str, "path", description="Asset UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Asset details")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Asset not found")
@require_auth
async def get_asset(request: Request, asset_id: str):
    """
    Get asset details.

    Returns:
        200: Asset details
        401: Not authenticated
        403: Not authorized
        404: Asset not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    asset_uuid = UUID(asset_id)

    # Get asset with ownership check
    asset = await AssetsRepository.get_user_asset(asset_uuid, user_id)

    if not asset:
        raise NotFoundError("Asset", asset_id)

    logger.info(
        "Retrieved asset details",
        user_id=str(user_id),
        asset_id=asset_id,
    )

    return response.json(
        {"asset": asset},
        status=200,
    )


@assets_bp.put("/<asset_id:uuid>")
@openapi.tag("Assets")
@openapi.summary("Update asset")
@openapi.description("Update asset information")
@openapi.parameter("asset_id", str, "path", description="Asset UUID")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": AssetUpdate})
@openapi.response(200, description="Asset updated successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Asset not found")
@openapi.response(422, description="Validation error")
@require_auth
async def update_asset(request: Request, asset_id: str):
    """
    Update an asset.

    Request Body:
        {
            "ticker": "PETR4"
        }

    Returns:
        200: Asset updated
        401: Not authenticated
        403: Not authorized
        404: Asset not found
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        asset_uuid = UUID(asset_id)

        # Check ownership
        existing = await AssetsRepository.get_user_asset(asset_uuid, user_id)
        if not existing:
            raise NotFoundError("Asset", asset_id)

        # Validate request data
        data = AssetUpdate(**request.json)

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields to update")

        # If updating ticker, check if new ticker already exists
        if "ticker" in update_data:
            account_id = UUID(existing["account_id"])
            ticker_exists = await AssetsRepository.get_by_ticker(
                account_id,
                update_data["ticker"]
            )
            if ticker_exists and ticker_exists["id"] != str(asset_uuid):
                raise ValidationError(
                    f"Asset {update_data['ticker']} already exists in this account"
                )

        # Update asset
        asset = await AssetsRepository.update(asset_uuid, update_data)

        logger.info(
            "Asset updated",
            user_id=str(user_id),
            asset_id=asset_id,
        )

        return response.json(
            {
                "message": "Asset updated successfully",
                "asset": asset,
            },
            status=200,
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update asset", error=str(e))
        raise ValidationError(f"Failed to update asset: {str(e)}")


@assets_bp.delete("/<asset_id:uuid>")
@openapi.tag("Assets")
@openapi.summary("Delete asset")
@openapi.description("Delete an asset")
@openapi.parameter("asset_id", str, "path", description="Asset UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Asset deleted successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Asset not found")
@require_auth
async def delete_asset(request: Request, asset_id: str):
    """
    Delete an asset.

    Returns:
        200: Asset deleted
        401: Not authenticated
        403: Not authorized
        404: Asset not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    asset_uuid = UUID(asset_id)

    # Check ownership
    existing = await AssetsRepository.get_user_asset(asset_uuid, user_id)
    if not existing:
        raise NotFoundError("Asset", asset_id)

    # Delete asset
    await AssetsRepository.delete(asset_uuid)

    logger.info(
        "Asset deleted",
        user_id=str(user_id),
        asset_id=asset_id,
    )

    return response.json(
        {"message": "Asset deleted successfully"},
        status=200,
    )
