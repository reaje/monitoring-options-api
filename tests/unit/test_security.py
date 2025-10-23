"""Unit tests for security utilities."""

import pytest
from app.core.security import security
from app.core.exceptions import AuthenticationError


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = security.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert isinstance(hashed, str)

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = security.hash_password(password)

        assert security.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = security.hash_password(password)

        assert security.verify_password(wrong_password, hashed) is False

    def test_hash_different_each_time(self):
        """Test that hashing same password produces different hashes."""
        password = "testpassword123"
        hash1 = security.hash_password(password)
        hash2 = security.hash_password(password)

        assert hash1 != hash2
        assert security.verify_password(password, hash1) is True
        assert security.verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        token = security.create_access_token(user_id, email)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        token = security.create_refresh_token(user_id, email)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_valid(self):
        """Test decoding valid token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        token = security.create_access_token(user_id, email)
        payload = security.decode_token(token)

        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_token_invalid(self):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"

        with pytest.raises(AuthenticationError):
            security.decode_token(invalid_token)

    def test_get_user_id_from_token(self):
        """Test extracting user ID from token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        token = security.create_access_token(user_id, email)
        extracted_id = security.get_user_id_from_token(token)

        assert extracted_id == user_id

    def test_refresh_token_type(self):
        """Test refresh token has correct type."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        token = security.create_refresh_token(user_id, email)
        payload = security.decode_token(token)

        assert payload["type"] == "refresh"
