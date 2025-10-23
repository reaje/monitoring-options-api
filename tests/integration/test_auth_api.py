"""Integration tests for authentication API."""

import pytest


@pytest.mark.asyncio
class TestAuthRegister:
    """Test user registration endpoint."""

    async def test_register_success(self, test_client):
        """Test successful user registration."""
        _, response = await test_client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User",
            },
        )

        assert response.status == 201
        data = response.json
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
        assert "password" not in data["user"]

    async def test_register_duplicate_email(self, test_client, test_user):
        """Test registration with duplicate email."""
        _, response = await test_client.post(
            "/auth/register",
            json={
                "email": test_user["email"],
                "password": "password123",
                "name": "Duplicate User",
            },
        )

        assert response.status == 409
        data = response.json
        assert "error" in data

    async def test_register_missing_email(self, test_client):
        """Test registration without email."""
        _, response = await test_client.post(
            "/auth/register",
            json={
                "password": "password123",
                "name": "No Email User",
            },
        )

        assert response.status == 422

    async def test_register_invalid_email(self, test_client):
        """Test registration with invalid email."""
        _, response = await test_client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": "password123",
                "name": "Invalid Email",
            },
        )

        assert response.status == 422

    async def test_register_short_password(self, test_client):
        """Test registration with short password."""
        _, response = await test_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "123",
                "name": "Short Pass",
            },
        )

        assert response.status == 422


@pytest.mark.asyncio
class TestAuthLogin:
    """Test user login endpoint."""

    async def test_login_success(self, test_client, test_user):
        """Test successful login."""
        _, response = await test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["plain_password"],
            },
        )

        assert response.status == 200
        data = response.json
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user["email"]

    async def test_login_wrong_password(self, test_client, test_user):
        """Test login with wrong password."""
        _, response = await test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "wrongpassword",
            },
        )

        assert response.status == 401
        data = response.json
        assert "error" in data

    async def test_login_nonexistent_user(self, test_client):
        """Test login with nonexistent user."""
        _, response = await test_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status == 401

    async def test_login_missing_credentials(self, test_client):
        """Test login without credentials."""
        _, response = await test_client.post(
            "/auth/login",
            json={},
        )

        assert response.status == 422


@pytest.mark.asyncio
class TestAuthMe:
    """Test get current user endpoint."""

    async def test_me_authenticated(self, test_client, auth_headers, test_user):
        """Test getting current user when authenticated."""
        _, response = await test_client.get(
            "/auth/me",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert "user" in data
        assert data["user"]["email"] == test_user["email"]

    async def test_me_unauthenticated(self, test_client):
        """Test getting current user without authentication."""
        _, response = await test_client.get("/auth/me")

        assert response.status == 401

    async def test_me_invalid_token(self, test_client):
        """Test getting current user with invalid token."""
        _, response = await test_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status == 401


@pytest.mark.asyncio
class TestAuthLogout:
    """Test logout endpoint."""

    async def test_logout_success(self, test_client, auth_headers):
        """Test successful logout."""
        _, response = await test_client.post(
            "/auth/logout",
            headers=auth_headers,
        )

        assert response.status == 200
        data = response.json
        assert data["message"] == "Logout successful"

    async def test_logout_unauthenticated(self, test_client):
        """Test logout without authentication."""
        _, response = await test_client.post("/auth/logout")

        assert response.status == 401


@pytest.mark.asyncio
class TestAuthRefresh:
    """Test token refresh endpoint."""

    async def test_refresh_success(self, test_client, test_user):
        """Test successful token refresh."""
        from app.core.security import security

        # Create refresh token
        refresh_token = security.create_refresh_token(
            test_user["id"],
            test_user["email"],
        )

        _, response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status == 200
        data = response.json
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_missing_token(self, test_client):
        """Test refresh without token."""
        _, response = await test_client.post(
            "/auth/refresh",
            json={},
        )

        assert response.status == 422

    async def test_refresh_invalid_token(self, test_client):
        """Test refresh with invalid token."""
        _, response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status == 401

    async def test_refresh_with_access_token(self, test_client, auth_token):
        """Test refresh with access token (should fail)."""
        _, response = await test_client.post(
            "/auth/refresh",
            json={"refresh_token": auth_token},
        )

        assert response.status == 401


@pytest.mark.asyncio
class TestAuthChangePassword:
    """Test password change endpoint."""

    async def test_change_password_success(
        self,
        test_client,
        auth_headers,
        test_user
    ):
        """Test successful password change."""
        _, response = await test_client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": test_user["plain_password"],
                "new_password": "newpassword123",
            },
        )

        assert response.status == 200
        data = response.json
        assert data["message"] == "Password changed successfully"

        # Verify can login with new password
        _, login_response = await test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "newpassword123",
            },
        )

        assert login_response.status == 200

    async def test_change_password_wrong_current(
        self,
        test_client,
        auth_headers
    ):
        """Test password change with wrong current password."""
        _, response = await test_client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
            },
        )

        assert response.status == 401

    async def test_change_password_short_new(self, test_client, auth_headers, test_user):
        """Test password change with too short new password."""
        _, response = await test_client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": test_user["plain_password"],
                "new_password": "123",
            },
        )

        assert response.status == 422

    async def test_change_password_unauthenticated(self, test_client):
        """Test password change without authentication."""
        _, response = await test_client.post(
            "/auth/change-password",
            json={
                "current_password": "oldpass",
                "new_password": "newpass123",
            },
        )

        assert response.status == 401
