"""Security utilities for authentication and password hashing."""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.config import settings
from app.core.exceptions import AuthenticationError


class SecurityManager:
    """Manager for security operations (JWT, password hashing)."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False

    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID
            email: User email
            expires_delta: Token expiration time (default: from settings)

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.SESSION_TIMEOUT)

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
            "type": "access",
        }

        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        return token

    @staticmethod
    def create_refresh_token(user_id: str, email: str) -> str:
        """
        Create a JWT refresh token (longer expiration).

        Args:
            user_id: User ID
            email: User email

        Returns:
            JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=30)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        return token

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=["HS256"],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    @staticmethod
    def get_user_id_from_token(token: str) -> str:
        """
        Extract user ID from token.

        Args:
            token: JWT token string

        Returns:
            User ID string

        Raises:
            AuthenticationError: If token is invalid
        """
        payload = SecurityManager.decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("Invalid token payload")

        return user_id


# Convenience instances
security = SecurityManager()
