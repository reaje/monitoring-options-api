"""Alerts routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.database.repositories.alerts import AlertQueueRepository
from app.database.repositories.alert_logs import AlertLogsRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.models import AlertQueueCreate
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


alerts_bp = Blueprint("alerts", url_prefix="/api/alerts")


@alerts_bp.get("/")
@openapi.tag("Alerts")
@openapi.summary("List alerts")
@openapi.description("Get all alerts for user's accounts with optional filters")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.parameter("status", str, "query", required=False, description="Filter by status (PENDING, PROCESSING, SENT, FAILED)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of alerts")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_alerts(request: Request):
    """
    Get all alerts for user's accounts.

    Query Parameters:
        account_id (optional): Filter by account ID
        status (optional): Filter by status (PENDING, PROCESSING, SENT, FAILED)

    Returns:
        200: List of alerts
        401: Not authenticated
    """
    user = request.ctx.user
    user_id = UUID(user["id"])

    # Get optional filters
    account_id_param = request.args.get("account_id")
    status_param = request.args.get("status")

    alerts = []

    if account_id_param:
        # Get alerts for specific account
        account_uuid = UUID(account_id_param)

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        alerts = await AlertQueueRepository.get_by_account_id(
            account_uuid,
            status=status_param,
            auth_user_id=user_id,
        )

    else:
        # Get all accounts for user
        accounts = await AccountsRepository.get_by_user_id(user_id)

        # Get alerts for all user accounts
        for account in accounts:
            account_alerts = await AlertQueueRepository.get_by_account_id(
                UUID(account["id"]),
                status=status_param,
                auth_user_id=user_id,
            )
            alerts.extend(account_alerts)

    logger.info(
        "Retrieved user alerts",
        user_id=str(user_id),
        count=len(alerts),
    )

    return response.json(
        {
            "alerts": alerts,
            "total": len(alerts),
        },
        status=200,
    )


@alerts_bp.get("/pending")
@openapi.tag("Alerts")
@openapi.summary("List pending alerts")
@openapi.description("Get all pending alerts for user's accounts")
@openapi.parameter("account_id", str, "query", required=False, description="Filter by account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of pending alerts")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_pending_alerts(request: Request):
    """
    Get pending alerts for user's accounts.

    Query Parameters:
        account_id (optional): Filter by account ID

    Returns:
        200: List of pending alerts
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

        alerts = await AlertQueueRepository.get_by_account_id(
            account_uuid,
            status="PENDING",
            auth_user_id=user_id,
        )
    else:
        # Get all accounts and their pending alerts
        accounts = await AccountsRepository.get_by_user_id(user_id)
        alerts = []

        for account in accounts:
            account_alerts = await AlertQueueRepository.get_by_account_id(
                UUID(account["id"]),
                status="PENDING",
                auth_user_id=user_id,
            )
            alerts.extend(account_alerts)

    return response.json(
        {
            "alerts": alerts,
            "total": len(alerts),
        },
        status=200,
    )


@alerts_bp.post("/")
@openapi.tag("Alerts")
@openapi.summary("Create new alert")
@openapi.description("Create a new alert manually")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": AlertQueueCreate})
@openapi.response(201, description="Alert created successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to create alerts in this account")
@openapi.response(422, description="Validation error")
@require_auth
async def create_alert(request: Request):
    """
    Create a new alert manually.

    Request Body:
        {
            "account_id": "uuid",
            "option_position_id": "uuid",  // optional
            "reason": "Manual alert",
            "payload": {
                "message": "Custom message",
                "priority": "high"
            }
        }

    Returns:
        201: Alert created
        401: Not authenticated
        403: Not authorized
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        # Validate request data
        data = AlertQueueCreate(**request.json)

        # Check account ownership
        if not await AccountsRepository.user_owns_account(data.account_id, user_id):
            raise AuthorizationError(
                "Not authorized to create alerts in this account"
            )

        # Create alert (pass auth_user_id to satisfy RLS)
        alert = await AlertQueueRepository.create(data.model_dump(), auth_user_id=user_id)

        logger.info(
            "Alert created",
            user_id=str(user_id),
            alert_id=alert["id"],
            reason=data.reason,
        )

        return response.json(
            {
                "message": "Alert created successfully",
                "alert": alert,
            },
            status=201,
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to create alert", error=str(e))
        raise ValidationError(f"Failed to create alert: {str(e)}")


@alerts_bp.get("/<alert_id:uuid>")
@openapi.tag("Alerts")
@openapi.summary("Get alert by ID")
@openapi.description("Retrieve details of a specific alert")
@openapi.parameter("alert_id", str, "path", description="Alert UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Alert details")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Alert not found")
@require_auth
async def get_alert(request: Request, alert_id: str):
    """
    Get alert details.

    Returns:
        200: Alert details
        401: Not authenticated
        403: Not authorized
        404: Alert not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    alert_uuid = UUID(alert_id)

    # Get alert with ownership check
    alert = await AlertQueueRepository.get_user_alert(alert_uuid, user_id)

    if not alert:
        raise NotFoundError("Alert", alert_id)

    logger.info(
        "Retrieved alert details",
        user_id=str(user_id),
        alert_id=alert_id,
    )

    return response.json(
        {"alert": alert},
        status=200,
    )


@alerts_bp.delete("/<alert_id:uuid>")
@openapi.tag("Alerts")
@openapi.summary("Delete alert")
@openapi.description("Delete an alert")
@openapi.parameter("alert_id", str, "path", description="Alert UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Alert deleted successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Alert not found")
@require_auth
async def delete_alert(request: Request, alert_id: str):
    """
    Delete an alert.

    Returns:
        200: Alert deleted
        401: Not authenticated
        403: Not authorized
        404: Alert not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    alert_uuid = UUID(alert_id)

    # Check ownership
    existing = await AlertQueueRepository.get_user_alert(alert_uuid, user_id)
    if not existing:
        raise NotFoundError("Alert", alert_id)

    # Delete alert (pass auth_user_id to satisfy RLS)
    await AlertQueueRepository.delete(alert_uuid, auth_user_id=user_id)

    logger.info(
        "Alert deleted",
        user_id=str(user_id),
        alert_id=alert_id,
    )

    return response.json(
        {"message": "Alert deleted successfully"},
        status=200,
    )


@alerts_bp.post("/<alert_id:uuid>/retry")
@openapi.tag("Alerts")
@openapi.summary("Retry failed alert")
@openapi.description("Mark a failed alert for retry")
@openapi.parameter("alert_id", str, "path", description="Alert UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Alert marked for retry")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Alert not found")
@require_auth
async def retry_alert(request: Request, alert_id: str):
    """
    Retry a failed alert.

    Returns:
        200: Alert marked for retry
        401: Not authenticated
        403: Not authorized
        404: Alert not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    alert_uuid = UUID(alert_id)

    # Check ownership
    existing = await AlertQueueRepository.get_user_alert(alert_uuid, user_id)
    if not existing:
        raise NotFoundError("Alert", alert_id)

    # Retry alert (pass auth_user_id to satisfy RLS)
    alert = await AlertQueueRepository.retry_failed_alert(alert_uuid, auth_user_id=user_id)

    logger.info(
        "Alert marked for retry",
        user_id=str(user_id),
        alert_id=alert_id,
    )

    return response.json(
        {
            "message": "Alert marked for retry",
            "alert": alert,
        },
        status=200,
    )


@alerts_bp.get("/statistics/<account_id:uuid>")
@openapi.tag("Alerts")
@openapi.summary("Get alert statistics")
@openapi.description("Get alert statistics for an account")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.parameter("hours", int, "query", required=False, description="Number of hours to look back (default: 24)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Alert statistics")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_alert_statistics(request: Request, account_id: str):
    """
    Get alert statistics for an account.

    Query Parameters:
        hours (optional): Number of hours to look back (default: 24)

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

    # Get hours parameter
    hours = int(request.args.get("hours", 24))

    # Get statistics
    stats = await AlertQueueRepository.get_statistics(account_uuid, hours, auth_user_id=user_id)

    return response.json(
        {"statistics": stats},
        status=200,
    )


@alerts_bp.get("/<alert_id:uuid>/logs")
@openapi.tag("Alerts")
@openapi.summary("Get alert notification logs")
@openapi.description("Get notification logs for a specific alert")
@openapi.parameter("alert_id", str, "path", description="Alert UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="List of notification logs")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Alert not found")
@require_auth
async def get_alert_logs(request: Request, alert_id: str):
    """
    Get notification logs for a specific alert.

    Returns:
        200: List of logs
        401: Not authenticated
        403: Not authorized
        404: Alert not found
    """
    user = request.ctx.user
    user_id = UUID(user["id"])
    alert_uuid = UUID(alert_id)

    # Check ownership
    existing = await AlertQueueRepository.get_user_alert(alert_uuid, user_id)
    if not existing:
        raise NotFoundError("Alert", alert_id)

    # Get logs
    logs = await AlertLogsRepository.get_by_queue_id(alert_uuid, auth_user_id=user_id)

    return response.json(
        {
            "logs": logs,
            "total": len(logs),
        },
        status=200,
    )


@alerts_bp.get("/logs/statistics")
@openapi.tag("Alerts")
@openapi.summary("Get notification logs statistics")
@openapi.description("Get overall notification logs statistics")
@openapi.parameter("hours", int, "query", required=False, description="Number of hours to look back (default: 24)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Notification logs statistics")
@openapi.response(401, description="Not authenticated")
@require_auth
async def get_logs_statistics(request: Request):
    """
    Get notification logs statistics.

    Query Parameters:
        hours (optional): Number of hours to look back (default: 24)

    Returns:
        200: Statistics
        401: Not authenticated
    """
    # Get hours parameter
    hours = int(request.args.get("hours", 24))

    # Get statistics
    stats = await AlertLogsRepository.get_statistics(hours, auth_user_id=UUID(request.ctx.user["id"]))

    return response.json(
        {"statistics": stats},
        status=200,
    )
