"""Manual notification routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.services.notification_service import notification_service
from app.database.repositories.accounts import AccountsRepository
from app.database.models import NotificationRequest
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


notifications_bp = Blueprint("notifications", url_prefix="/api/notifications")


@notifications_bp.post("/send")
@openapi.tag("Notifications")
@openapi.summary("Send manual notification")
@openapi.description("Send manual notification to user's phone/email")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": NotificationRequest})
@openapi.response(200, description="Notification sent successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to send notifications for this account")
@openapi.response(422, description="Validation error")
@require_auth
async def send_notification(request: Request):
    """
    Send manual notification to user's phone/email.

    Request Body:
        {
            "account_id": "uuid",
            "message": "Custom notification message",
            "channels": ["whatsapp", "sms"],
            "phone": "+5511999999999"  // optional override
        }

    Returns:
        200: Notification sent
        401: Not authenticated
        403: Not authorized
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        # Validate request data
        data = NotificationRequest(**request.json)

        # Check account ownership
        if not await AccountsRepository.user_owns_account(data.account_id, user_id):
            raise AuthorizationError(
                "Not authorized to send notifications for this account"
            )

        # Send notification
        results = await notification_service.send_manual_notification(
            account_id=data.account_id,
            message=data.message,
            channels=data.channels,
            phone=data.phone
        )

        # Count successes
        successful = sum(1 for r in results.values() if r.get("status") == "success")
        total = len(results)

        logger.info(
            "Manual notification sent",
            user_id=str(user_id),
            account_id=str(data.account_id),
            successful=successful,
            total=total
        )

        return response.json(
            {
                "message": f"Notification sent to {successful}/{total} channels",
                "results": results,
            },
            status=200,
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to send notification", error=str(e))
        raise ValidationError(f"Failed to send notification: {str(e)}")


@notifications_bp.post("/test")
@openapi.tag("Notifications")
@openapi.summary("Send test notification")
@openapi.description("Send test notification to verify channel configuration")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Test notification sent successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error or unsupported channel")
@require_auth
async def test_notification(request: Request):
    """
    Send test notification.

    Request Body:
        {
            "channel": "whatsapp",
            "phone": "+5511999999999"
        }

    Returns:
        200: Test sent
        401: Not authenticated
        422: Validation error
    """
    try:
        data = request.json
        channel = data.get("channel", "whatsapp")
        phone = data.get("phone")

        if not phone:
            raise ValidationError("Phone number required")

        user = request.ctx.user
        message = f"🧪 Teste de notificação - Monitoring Options\n\nUsuário: {user.get('email')}\nCanal: {channel}"

        # Create a dummy account_id for the service
        # In a real scenario, we'd use the user's first account
        from app.services.communications_client import comm_client

        if channel == "whatsapp":
            result = await comm_client.send_whatsapp(phone, message)
        elif channel == "sms":
            result = await comm_client.send_sms(phone, message)
        else:
            raise ValidationError(f"Unsupported channel: {channel}")

        logger.info(
            "Test notification sent",
            user_id=user["id"],
            channel=channel,
            phone=phone
        )

        return response.json(
            {
                "message": "Test notification sent successfully",
                "result": result,
            },
            status=200,
        )

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to send test notification", error=str(e))
        raise ValidationError(f"Failed to send test notification: {str(e)}")


@notifications_bp.get("/status/<message_id>")
@openapi.tag("Notifications")
@openapi.summary("Get notification delivery status")
@openapi.description("Get notification delivery status from provider")
@openapi.parameter("message_id", str, "path", description="Message ID from provider")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Status retrieved successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(404, description="Message not found")
@require_auth
async def get_notification_status(request: Request, message_id: str):
    """
    Get notification delivery status from provider.

    Returns:
        200: Status retrieved
        401: Not authenticated
        404: Message not found
    """
    try:
        from app.services.communications_client import comm_client

        status_info = await comm_client.get_message_status(message_id)

        return response.json(
            {"status": status_info},
            status=200,
        )

    except Exception as e:
        logger.error(
            "Failed to get notification status",
            message_id=message_id,
            error=str(e)
        )
        raise NotFoundError("Message", message_id)


@notifications_bp.post("/process-queue")
@openapi.tag("Notifications")
@openapi.summary("Manually process pending alerts queue")
@openapi.description("Manually trigger processing of pending alerts queue (Admin/debug endpoint)")
@openapi.parameter("limit", int, "query", required=False, description="Max alerts to process (default: 100)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Queue processing completed")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Validation error")
@require_auth
async def process_queue_manually(request: Request):
    """
    Manually trigger processing of pending alerts queue.
    Admin/debug endpoint.

    Query Parameters:
        limit (optional): Max alerts to process (default: 100)

    Returns:
        200: Processing results
        401: Not authenticated
    """
    try:
        limit = int(request.args.get("limit", 100))

        results = await notification_service.process_pending_alerts(limit)

        logger.info(
            "Manually processed alert queue",
            user_id=request.ctx.user["id"],
            results=results
        )

        return response.json(
            {
                "message": "Queue processing completed",
                "results": results,
            },
            status=200,
        )

    except Exception as e:
        logger.error("Failed to process queue", error=str(e))
        raise ValidationError(f"Failed to process queue: {str(e)}")
