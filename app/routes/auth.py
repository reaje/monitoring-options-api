"""Authentication routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
import asyncpg
from app.config import settings
from app.database.models import UserRegister, UserLogin, TokenResponse, UserResponse
from app.core.logger import logger
from app.core.exceptions import AuthenticationError, ValidationError, ConflictError
from app.core.security import security
from app.database.supabase_client import supabase

from app.middleware.auth_middleware import require_auth
from datetime import datetime, timedelta


auth_bp = Blueprint("auth", url_prefix="/auth")


async def get_db_connection():
    """Get database connection."""
    return await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        server_settings={'search_path': settings.DB_SCHEMA}
    )


@auth_bp.post("/register")
@openapi.tag("Authentication")
@openapi.summary("Register a new user")
@openapi.description("Create a new user account with email and password")
@openapi.body({"application/json": UserRegister})
@openapi.response(201, {"application/json": UserResponse}, description="User created successfully")
@openapi.response(409, description="Email already registered")
@openapi.response(422, description="Validation error")
async def register(request: Request):
    """
    Register a new user.

    Request Body:
        {
            "email": "user@example.com",
            "password": "strongpassword",
            "name": "User Name" (optional)
        }

    Returns:
        201: User created successfully
        409: User already exists
        422: Validation error
    """
    conn = None
    try:
        # Validate request data
        data = UserRegister(**request.json)

        # Connect to database
        conn = await get_db_connection()

        # Check if user already exists
        existing_user = await conn.fetchrow(
            f'SELECT id FROM {settings.DB_SCHEMA}.users WHERE email = $1',
            data.email
        )

        if existing_user:
            raise ConflictError(
                "Email already registered",
                details={"email": data.email}
            )

        # Hash password
        hashed_password = security.hash_password(data.password)

        # Create user in database
        user = await conn.fetchrow(
            f'''
            INSERT INTO {settings.DB_SCHEMA}.users (email, password, name, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
            RETURNING id, email, name, created_at
            ''',
            data.email,
            hashed_password,
            data.name
        )

        logger.info(
            "User registered successfully",
            user_id=str(user["id"]),
            email=user["email"],
        )

        return response.json(
            {
                "message": "User registered successfully",
                "user": {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "name": user["name"],
                    "created_at": user["created_at"].isoformat() + "Z"
                },
            },
            status=201,
        )

    except (ConflictError, ValidationError):
        raise
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise ValidationError(f"Registration failed: {str(e)}")
    finally:
        if conn:
            await conn.close()


@auth_bp.post("/login")
@openapi.tag("Authentication")
@openapi.summary("Login with email and password")
@openapi.description("Authenticate user and receive access and refresh tokens")
@openapi.body({"application/json": UserLogin})
@openapi.response(200, {"application/json": TokenResponse}, description="Login successful")
@openapi.response(401, description="Invalid credentials")
@openapi.response(422, description="Validation error")
async def login(request: Request):
    """
    Login with email and password.

    Request Body:
        {
            "email": "user@example.com",
            "password": "password123"
        }

    Returns:
        200: Authentication successful with access token
        401: Invalid credentials
        422: Validation error
    """
    try:
        # Validate request data
        data = UserLogin(**request.json)

        # Connect to database directly (avoid supabase-py issues)
        conn = await get_db_connection()
        try:
            user = await conn.fetchrow(
                f'''
                SELECT id, email, password, name, created_at
                FROM {settings.DB_SCHEMA}.users
                WHERE email = $1
                ''',
                data.email,
            )

            if not user:
                raise AuthenticationError("Invalid email or password")

            # Verify password
            if not security.verify_password(data.password, user["password"]):
                logger.warning(
                    "Failed login attempt",
                    email=data.email,
                )
                raise AuthenticationError("Invalid email or password")

            # Create JWT tokens
            access_token = security.create_access_token(
                user_id=str(user["id"]),
                email=user["email"],
            )

            refresh_token = security.create_refresh_token(
                user_id=str(user["id"]),
                email=user["email"],
            )

            logger.info(
                "User logged in successfully",
                user_id=str(user["id"]),
                email=user["email"],
            )

            user_dict = {
                "id": str(user["id"]),
                "email": user["email"],
                "name": user["name"],
                "created_at": user["created_at"].isoformat() + "Z" if user["created_at"] else None,
            }

            return response.json(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": 3600,  # 1 hour
                    "user": user_dict,
                },
                status=200,
            )
        finally:
            await conn.close()

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise AuthenticationError(f"Login failed: {str(e)}")


@auth_bp.post("/refresh")
@openapi.tag("Authentication")
@openapi.summary("Refresh access token")
@openapi.description("Generate a new access token using a valid refresh token")
@openapi.body({"application/json": {"refresh_token": str}})
@openapi.response(200, {"application/json": TokenResponse}, description="New access token generated")
@openapi.response(401, description="Invalid or expired refresh token")
async def refresh_token(request: Request):
    """
    Refresh access token using refresh token.

    Request Body:
        {
            "refresh_token": "eyJ..."
        }

    Returns:
        200: New access token
        401: Invalid or expired refresh token
    """
    try:
        refresh_token_str = request.json.get("refresh_token")

        if not refresh_token_str:
            raise ValidationError("Refresh token is required")

        # Decode refresh token
        payload = security.decode_token(refresh_token_str)

        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        user_id = payload.get("sub")
        email = payload.get("email")

        # Create new access token
        new_access_token = security.create_access_token(
            user_id=user_id,
            email=email,
        )

        logger.info(
            "Token refreshed successfully",
            user_id=user_id,
        )

        return response.json(
            {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": 3600,
            },
            status=200,
        )

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise AuthenticationError("Failed to refresh token")


@auth_bp.post("/logout")
@openapi.tag("Authentication")
@openapi.summary("Logout user")
@openapi.description("Logout user (client-side token invalidation)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Logout successful")
@openapi.response(401, description="Not authenticated")
@require_auth
async def logout(request: Request):
    """
    Logout user (client-side token invalidation).

    Note: JWT tokens can't be invalidated server-side without a blacklist.
    This endpoint is mainly for logging purposes.

    Returns:
        200: Logout successful
    """
    user = request.ctx.user

    logger.info(
        "User logged out",
        user_id=user["id"],
        email=user["email"],
    )

    return response.json(
        {"message": "Logout successful"},
        status=200,
    )


@auth_bp.get("/me")
@openapi.tag("Authentication")
@openapi.summary("Get current user")
@openapi.description("Retrieve authenticated user information")
@openapi.secured("BearerAuth")
@openapi.response(200, {"application/json": UserResponse}, description="User information")
@openapi.response(401, description="Not authenticated")
@require_auth
async def get_current_user(request: Request):
    """
    Get current authenticated user information.

    Returns:
        200: User information
        401: Not authenticated
    """
    user = request.ctx.user

    return response.json(
        {"user": user},
        status=200,
    )


@auth_bp.post("/change-password")
@openapi.tag("Authentication")
@openapi.summary("Change password")
@openapi.description("Change authenticated user's password")
@openapi.secured("BearerAuth")
@openapi.body({"application/json": {"current_password": str, "new_password": str}})
@openapi.response(200, description="Password changed successfully")
@openapi.response(401, description="Current password incorrect or not authenticated")
@openapi.response(422, description="Validation error")
@require_auth
async def change_password(request: Request):
    """
    Change user password.

    Request Body:
        {
            "current_password": "oldpassword",
            "new_password": "newpassword"
        }

    Returns:
        200: Password changed successfully
        401: Current password incorrect
        422: Validation error
    """
    try:
        user = request.ctx.user
        current_password = request.json.get("current_password")
        new_password = request.json.get("new_password")

        if not current_password or not new_password:
            raise ValidationError("Both current and new passwords are required")

        if len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters")

        # Get user from database with password
        user_result = supabase.table("users") \
            .select("*") \
            .eq("id", user["id"]) \
            .single() \
            .execute()

        if not user_result.data:
            raise AuthenticationError("User not found")

        db_user = user_result.data

        # Verify current password
        if not security.verify_password(current_password, db_user["password"]):
            raise AuthenticationError("Current password is incorrect")

        # Hash new password
        new_hashed_password = security.hash_password(new_password)

        # Update password in database
        supabase.table("users") \
            .update({"password": new_hashed_password}) \
            .eq("id", user["id"]) \
            .execute()

        logger.info(
            "Password changed successfully",
            user_id=user["id"],
        )

        return response.json(
            {"message": "Password changed successfully"},
            status=200,
        )

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        logger.error("Password change failed", error=str(e))
        raise ValidationError("Failed to change password")
