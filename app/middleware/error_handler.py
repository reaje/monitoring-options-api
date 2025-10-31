"""Global error handling middleware."""

from sanic import Sanic, response
from sanic.exceptions import SanicException
from pydantic import ValidationError
from app.core.exceptions import AppException
from app.core.logger import logger
from app.config import settings

from datetime import datetime


def setup_error_handlers(app: Sanic) -> None:
    """
    Setup global error handlers for the Sanic application.

    Args:
        app: Sanic application instance
    """

    @app.exception(AppException)
    async def handle_app_exception(request, exception: AppException):
        """Handle custom application exceptions."""
        logger.warning(
            "Application exception",
            code=exception.code,
            message=exception.message,
            path=request.path,
        )

        payload = {
            **exception.to_dict(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        # Always include minimal diagnostics to help QA/E2E without leaking secrets
        payload.setdefault("error", {}).setdefault("details", {})
        payload["error"]["details"].update({
            "exception": exception.__class__.__name__,
            "message": str(exception),
        })
        if settings.DEBUG:
            payload["debug"] = {
                "exception": exception.__class__.__name__,
                "message": str(exception),
            }
        return response.json(payload, status=exception.status_code)

    @app.exception(ValidationError)
    async def handle_validation_error(request, exception: ValidationError):
        """Handle Pydantic validation errors."""
        logger.warning(
            "Validation error",
            errors=exception.errors(),
            path=request.path,
        )

        payload = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dados inválidos",
                "details": exception.errors(),
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        # Also include summarized diagnostics to help QA
        payload["error"].setdefault("details", {})
        payload["error"]["details"].update({
            "exception": exception.__class__.__name__,
            "message": str(exception),
        })
        if settings.DEBUG:
            payload["debug"] = {
                "exception": exception.__class__.__name__,
                "message": str(exception),
            }
        return response.json(payload, status=422)

    @app.exception(SanicException)
    async def handle_sanic_exception(request, exception: SanicException):
        """Handle Sanic built-in exceptions."""
        logger.warning(
            "Sanic exception",
            exception=exception.__class__.__name__,
            message=str(exception),
            path=request.path,
        )

        payload = {
            "error": {
                "code": exception.__class__.__name__,
                "message": str(exception),
                "details": {
                    "exception": exception.__class__.__name__,
                    "message": str(exception),
                },
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if settings.DEBUG:
            payload["debug"] = {
                "exception": exception.__class__.__name__,
                "message": str(exception),
            }
        return response.json(payload, status=exception.status_code)

    @app.exception(Exception)
    async def handle_generic_exception(request, exception: Exception):
        """Handle any unhandled exceptions."""
        logger.error(
            "Unhandled exception",
            exception=exception.__class__.__name__,
            message=str(exception),
            path=request.path,
            exc_info=True,
        )

        payload = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Erro interno do servidor",
                "details": {
                    "exception": exception.__class__.__name__,
                    "message": str(exception),
                },
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if settings.DEBUG:
            payload["debug"] = {
                "exception": exception.__class__.__name__,
                "message": str(exception),
            }
        return response.json(payload, status=500)
