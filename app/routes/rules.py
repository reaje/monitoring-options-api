"""Roll rules routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.database.repositories.rules import RulesRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.models import RollRuleCreate, RollRuleUpdate
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


rules_bp = Blueprint("rules", url_prefix="/api/rules")


@rules_bp.get("/")
@openapi.tag("Rules")
@openapi.summary("List roll rules")
@openapi.description("Get all roll rules for user's accounts")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of roll rules")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_rules(request: Request):
    """
    Get all roll rules for user's accounts.

    Query Parameters:
        account_id (optional): Filter by account ID

    Returns:
        200: List of rules
        401: Not authenticated
    """
    user = request.ctx.user
    user_id = UUID(user["id"])

    # Get optional filters
    account_id_param = request.args.get("account_id")

    rules = []

    if account_id_param:
        # Get rules for specific account
        account_uuid = UUID(account_id_param)

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        rules = await RulesRepository.get_by_account_id(account_uuid)

    else:
        # Get all accounts for user
        accounts = await AccountsRepository.get_by_user_id(user_id)

        # Get rules for all user accounts
        for account in accounts:
            account_rules = await RulesRepository.get_by_account_id(
                UUID(account["id"])
            )
            rules.extend(account_rules)

    logger.info(
        "Retrieved user roll rules",
        user_id=str(user_id),
        count=len(rules),
    )

    return response.json(
        {
            "rules": rules,
            "total": len(rules),
        },
        status=200,
    )


@rules_bp.get("/active")
@require_auth
async def get_active_rules(request: Request):
    """
    Get all active roll rules for user.

    Query Parameters:
        account_id (optional): Filter by account ID

    Returns:
        200: List of active rules
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

        rules = await RulesRepository.get_active_rules(account_uuid)
    else:
        # Get all accounts and their active rules
        accounts = await AccountsRepository.get_by_user_id(user_id)
        rules = []

        for account in accounts:
            account_rules = await RulesRepository.get_active_rules(
                UUID(account["id"])
            )
            rules.extend(account_rules)

    return response.json(
        {
            "rules": rules,
            "total": len(rules),
        },
        status=200,
    )


@rules_bp.post("/")
@openapi.tag("Rules")
@openapi.summary("Create new roll rule")
@openapi.description("Create a new automated roll rule with thresholds and notification settings")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": RollRuleCreate})
@openapi.response(201, description="Rule created successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to create rules in this account")
@openapi.response(422, description="Validation error")
@require_auth
async def create_rule(request: Request):
    """
    Create a new roll rule.

    Request Body:
        {
            "account_id": "uuid",
            "delta_threshold": 0.60,
            "dte_min": 3,
            "dte_max": 5,
            "spread_threshold": 5.0,
            "price_to_strike_ratio": 0.98,
            "min_volume": 1000,
            "max_spread": 0.05,
            "min_oi": 5000,
            "target_otm_pct_low": 0.03,
            "target_otm_pct_high": 0.08,
            "notify_channels": ["whatsapp", "sms"],
            "is_active": true
        }

    Returns:
        201: Rule created
        401: Not authenticated
        403: Not authorized
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        # Validate request data
        data = RollRuleCreate(**request.json)

        # Check account ownership
        if not await AccountsRepository.user_owns_account(data.account_id, user_id):
            raise AuthorizationError(
                "Not authorized to create rules in this account"
            )

        # Create rule
        rule = await RulesRepository.create(data.model_dump())

        logger.info(
            "Roll rule created",
            user_id=str(user_id),
            rule_id=rule["id"],
            account_id=str(data.account_id),
        )

        return response.json(
            {
                "message": "Rule created successfully",
                "rule": rule,
            },
            status=201,
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create rule", error=str(e))
        raise ValidationError(f"Failed to create rule: {str(e)}")


@rules_bp.get("/<rule_id:uuid>")
@openapi.tag("Rules")
@openapi.summary("Get roll rule by ID")
@openapi.description("Retrieve details of a specific roll rule")
@openapi.parameter("rule_id", str, "path", description="Rule UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Rule details")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Rule not found")
@require_auth
async def get_rule(request: Request, rule_id: str):
    """
    Get roll rule details.

    Returns:
        200: Rule details
        401: Not authenticated
        403: Not authorized
        404: Rule not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    rule_uuid = UUID(rule_id)

    # Get rule with ownership check
    rule = await RulesRepository.get_user_rule(rule_uuid, user_id)

    if not rule:
        raise NotFoundError("Rule", rule_id)

    logger.info(
        "Retrieved rule details",
        user_id=str(user_id),
        rule_id=rule_id,
    )

    return response.json(
        {"rule": rule},
        status=200,
    )


@rules_bp.put("/<rule_id:uuid>")
@openapi.tag("Rules")
@openapi.summary("Update roll rule")
@openapi.description("Update roll rule configuration and thresholds")
@openapi.parameter("rule_id", str, "path", description="Rule UUID")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": RollRuleUpdate})
@openapi.response(200, description="Rule updated successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Rule not found")
@openapi.response(422, description="Validation error")
@require_auth
async def update_rule(request: Request, rule_id: str):
    """
    Update a roll rule.

    Request Body:
        {
            "delta_threshold": 0.65,
            "dte_min": 5,
            "dte_max": 7,
            "is_active": true
        }

    Returns:
        200: Rule updated
        401: Not authenticated
        403: Not authorized
        404: Rule not found
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        rule_uuid = UUID(rule_id)

        # Check ownership
        existing = await RulesRepository.get_user_rule(rule_uuid, user_id)
        if not existing:
            raise NotFoundError("Rule", rule_id)

        # Validate request data
        data = RollRuleUpdate(**request.json)

        # Only update provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise ValidationError("No fields to update")

        # Update rule
        rule = await RulesRepository.update(rule_uuid, update_data)

        logger.info(
            "Rule updated",
            user_id=str(user_id),
            rule_id=rule_id,
        )

        return response.json(
            {
                "message": "Rule updated successfully",
                "rule": rule,
            },
            status=200,
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to update rule", error=str(e))
        raise ValidationError(f"Failed to update rule: {str(e)}")


@rules_bp.delete("/<rule_id:uuid>")
@openapi.tag("Rules")
@openapi.summary("Delete roll rule")
@openapi.description("Delete a roll rule")
@openapi.parameter("rule_id", str, "path", description="Rule UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Rule deleted successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Rule not found")
@require_auth
async def delete_rule(request: Request, rule_id: str):
    """
    Delete a roll rule.

    Returns:
        200: Rule deleted
        401: Not authenticated
        403: Not authorized
        404: Rule not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    rule_uuid = UUID(rule_id)

    # Check ownership
    existing = await RulesRepository.get_user_rule(rule_uuid, user_id)
    if not existing:
        raise NotFoundError("Rule", rule_id)

    # Delete rule
    await RulesRepository.delete(rule_uuid)

    logger.info(
        "Rule deleted",
        user_id=str(user_id),
        rule_id=rule_id,
    )

    return response.json(
        {"message": "Rule deleted successfully"},
        status=200,
    )


@rules_bp.post("/<rule_id:uuid>/toggle")
@openapi.tag("Rules")
@openapi.summary("Toggle roll rule active status")
@openapi.description("Enable or disable a roll rule")
@openapi.parameter("rule_id", str, "path", description="Rule UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Rule toggled successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Rule not found")
@require_auth
async def toggle_rule(request: Request, rule_id: str):
    """
    Toggle rule active status.

    Returns:
        200: Rule toggled
        401: Not authenticated
        403: Not authorized
        404: Rule not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    rule_uuid = UUID(rule_id)

    # Check ownership
    existing = await RulesRepository.get_user_rule(rule_uuid, user_id)
    if not existing:
        raise NotFoundError("Rule", rule_id)

    # Toggle active status
    rule = await RulesRepository.toggle_active(rule_uuid)

    logger.info(
        "Rule toggled",
        user_id=str(user_id),
        rule_id=rule_id,
        is_active=rule["is_active"],
    )

    return response.json(
        {
            "message": "Rule toggled successfully",
            "rule": rule,
        },
        status=200,
    )
