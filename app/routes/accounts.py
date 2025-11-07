"""Accounts routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.database.repositories.accounts import AccountsRepository
from app.database.models import AccountCreate, AccountUpdate
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


accounts_bp = Blueprint("accounts", url_prefix="/api/accounts")


@accounts_bp.get("/")
@openapi.tag("Accounts")
@openapi.summary("List user accounts")
@openapi.description("Get all accounts for the authenticated user")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of accounts")
@openapi.response(401, description="Not authenticated")
@require_auth
async def get_accounts(request: Request):
    """
    Get all accounts for the authenticated user.

    Returns:
        200: List of accounts
        401: Not authenticated
    """
    user = request.ctx.user
    user_id = UUID(user["id"])

    accounts = await AccountsRepository.get_by_user_id(user_id)

    logger.info(
        "Retrieved user accounts",
        user_id=str(user_id),
        count=len(accounts),
    )

    return response.json(
        {
            "accounts": accounts,
            "total": len(accounts),
        },
        status=200,
    )


@accounts_bp.post("/")
@openapi.tag("Accounts")
@openapi.summary("Create new account")
@openapi.description("Create a new trading account for the authenticated user")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": AccountCreate})
@openapi.response(201, description="Account created successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error")
@require_auth
async def create_account(request: Request):
    """
    Create a new account for the authenticated user.

    Request Body:
        {
            "name": "Account Name"
        }

    Returns:
        201: Account created
        401: Not authenticated
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        # Validate request data (but ignore user_id from request)
        data = request.json
        if not data.get("name"):
            raise ValidationError("Account name is required")

        # Create account data with authenticated user_id
        account_data = {
            "name": data["name"],
            "user_id": str(user_id),
            "broker": data.get("broker"),
            "account_number": data.get("account_number"),
            "phone": data.get("phone"),
            "email": data.get("email"),
        }

        # Validate with Pydantic
        validated = AccountCreate(**account_data)

        # Create account
        account = await AccountsRepository.create(validated.model_dump())

        logger.info(
            "Account created",
            user_id=str(user_id),
            account_id=account["id"],
            name=account["name"],
        )

        return response.json(
            {
                "message": "Account created successfully",
                "account": account,
            },
            status=201,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to create account", error=str(e))
        raise ValidationError(f"Failed to create account: {str(e)}")


@accounts_bp.get("/<account_id:uuid>")
@openapi.tag("Accounts")
@openapi.summary("Get account by ID")
@openapi.description("Retrieve details of a specific account")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Account details")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Account not found")
@require_auth
async def get_account(request: Request, account_id: str):
    """
    Get account details.

    Returns:
        200: Account details
        401: Not authenticated
        403: Not authorized
        404: Account not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    account_uuid = UUID(account_id)

    # Get account with ownership check
    account = await AccountsRepository.get_user_account(account_uuid, user_id)

    if not account:
        raise NotFoundError("Account", account_id)

    logger.info(
        "Retrieved account details",
        user_id=str(user_id),
        account_id=account_id,
    )

    return response.json(
        {"account": account},
        status=200,
    )


@accounts_bp.put("/<account_id:uuid>")
@openapi.tag("Accounts")
@openapi.summary("Update account")
@openapi.description("Update account information")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": AccountUpdate})
@openapi.response(200, description="Account updated successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(404, description="Account not found")
@openapi.response(422, description="Validation error")
@require_auth
async def update_account(request: Request, account_id: str):
    """
    Update an account.

    Request Body:
        {
            "name": "New Account Name"
        }

    Returns:
        200: Account updated
        401: Not authenticated
        403: Not authorized
        404: Account not found
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        account_uuid = UUID(account_id)

        # Check ownership
        existing = await AccountsRepository.get_user_account(account_uuid, user_id)
        if not existing:
            raise NotFoundError("Account", account_id)

        # Validate request data
        data = AccountUpdate(**request.json)

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields to update")

        # Update account
        account = await AccountsRepository.update(account_uuid, update_data, auth_user_id=user_id)

        logger.info(
            "Account updated",
            user_id=str(user_id),
            account_id=account_id,
        )

        return response.json(
            {
                "message": "Account updated successfully",
                "account": account,
            },
            status=200,
        )

    except (NotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error("Failed to update account", error=str(e))
        raise ValidationError(f"Failed to update account: {str(e)}")


@accounts_bp.delete("/<account_id:uuid>")
@openapi.tag("Accounts")
@openapi.summary("Delete account")
@openapi.description("Delete an account")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Account deleted successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(404, description="Account not found")
@require_auth
async def delete_account(request: Request, account_id: str):
    """
    Delete an account.

    Returns:
        200: Account deleted
        401: Not authenticated
        403: Not authorized
        404: Account not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    account_uuid = UUID(account_id)

    # Check ownership
    existing = await AccountsRepository.get_user_account(account_uuid, user_id)
    if not existing:
        raise NotFoundError("Account", account_id)

    # Delete account
    await AccountsRepository.delete(account_uuid, auth_user_id=user_id)

    logger.info(
        "Account deleted",
        user_id=str(user_id),
        account_id=account_id,
    )

    return response.json(
        {"message": "Account deleted successfully"},
        status=200,
    )
