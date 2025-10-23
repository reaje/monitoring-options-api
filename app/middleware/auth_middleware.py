"""Authentication middleware for JWT validation."""

from functools import wraps
from typing import Optional, Dict, Any
from sanic import Request
import asyncpg
from app.config import settings
from app.core.logger import logger
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import security


async def extract_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract and validate user from JWT token.

    Args:
        token: JWT token string

    Returns:
        User dict if token is valid, None otherwise

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        # Decode JWT token
        payload = security.decode_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise AuthenticationError("Invalid token payload")

        # Fetch user from database to ensure they still exist (direct PG, avoid supabase-py issues)
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            server_settings={'search_path': settings.DB_SCHEMA},
        )
        try:
            row = await conn.fetchrow(
                f'SELECT id, email, name, created_at FROM {settings.DB_SCHEMA}.users WHERE id = $1',
                user_id,
            )
        finally:
            await conn.close()

        if not row:
            raise AuthenticationError("User not found")

        user = {
            "id": str(row["id"]),
            "email": row["email"],
            "name": row["name"],
            "created_at": row["created_at"].isoformat() + "Z" if row["created_at"] else None,
        }

        logger.info(
            "User authenticated successfully",
            user_id=user["id"],
            email=user["email"],
        )

        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "created_at": user.get("created_at"),
        }

    except AuthenticationError:
        raise
    except Exception as e:
        logger.warning(
            "Token validation failed",
            error=str(e),
        )
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def extract_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract user from request Authorization header.

    Args:
        request: Sanic request object

    Returns:
        User dict if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    # Check if Bearer token
    if not auth_header.startswith("Bearer "):
        logger.warning("Invalid authorization header format")
        return None

    # Extract token
    token = auth_header.replace("Bearer ", "").strip()

    if not token:
        return None

    try:
        user = await extract_user_from_token(token)
        return user
    except AuthenticationError:
        return None


def require_auth(wrapped=None, *, optional: bool = False):
    """
    Decorator to require authentication for a route.

    Usage:
        @app.get("/protected")
        @require_auth
        async def protected_route(request):
            user = request.ctx.user
            return response.json({"user": user})

        # Optional auth (user may or may not be authenticated)
        @app.get("/optional-auth")
        @require_auth(optional=True)
        async def optional_auth_route(request):
            user = request.ctx.user  # May be None
            return response.json({"user": user})

    Args:
        wrapped: The function to wrap
        optional: If True, authentication is optional (user can be None)

    Returns:
        Decorated function

    Raises:
        AuthenticationError: If authentication fails and optional=False
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Extract user from token
            user = await extract_user(request)

            # If optional, allow None user
            if optional:
                request.ctx.user = user
                return await func(request, *args, **kwargs)

            # If not optional and no user, raise error
            if not user:
                logger.warning(
                    "Unauthorized access attempt",
                    path=request.path,
                    method=request.method,
                )
                raise AuthenticationError("Authentication required")

            # Attach user to request context
            request.ctx.user = user

            # Call the actual route handler
            return await func(request, *args, **kwargs)

        return wrapper

    # Handle both @require_auth and @require_auth()
    if wrapped is None:
        return decorator
    else:
        return decorator(wrapped)


def require_permission(permission: str):
    """
    Decorator to require specific permission for a route.

    Usage:
        @app.delete("/admin/users/{id}")
        @require_permission("admin")
        async def delete_user(request, id):
            return response.json({"message": "User deleted"})

    Args:
        permission: Permission string required

    Returns:
        Decorated function

    Raises:
        AuthorizationError: If user doesn't have permission
    """

    def decorator(func):
        @wraps(func)
        @require_auth
        async def wrapper(request: Request, *args, **kwargs):
            user = request.ctx.user

            # Check user permissions
            # For now, check if user has admin role or specific permission
            # This can be extended to check permissions table
            user_role = user.get("role", "user")

            if user_role != "admin" and user_role != permission:
                logger.warning(
                    "Permission denied",
                    user_id=user.get("id"),
                    required_permission=permission,
                    user_role=user_role,
                )
                raise AuthorizationError(
                    f"Permission '{permission}' required for this action"
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def setup_auth_middleware(app):
    """
    Setup authentication middleware for Sanic app.

    This middleware runs on every request and optionally extracts user info.
    Individual routes can use @require_auth to enforce authentication.

    Args:
        app: Sanic application instance
    """

    @app.middleware("request")
    async def add_user_to_context(request):
        """Add user to request context if authenticated."""
        # Initialize user as None
        request.ctx.user = None

        # Try to extract user (but don't fail if not authenticated)
        try:
            user = await extract_user(request)
            if user:
                request.ctx.user = user
        except Exception as e:
            # Log error but don't fail request
            logger.debug("Failed to extract user from token", error=str(e))

    logger.info("Authentication middleware configured")
