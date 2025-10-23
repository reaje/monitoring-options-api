"""
End-to-End tests for authentication workflows
"""

import pytest
import asyncio
from typing import Dict, Any
from tests_e2e.helpers.api_client import APIClient
from tests_e2e.helpers.validators import ResponseValidator


@pytest.mark.auth
@pytest.mark.e2e
class TestAuthenticationE2E:
    """E2E tests for complete authentication workflows"""

    @pytest.mark.smoke
    async def test_complete_auth_flow(self, api_client: APIClient, validator: ResponseValidator):
        """Test complete authentication flow: register -> login -> get user info -> logout"""
        # Generate unique test email
        test_email = f"e2e_auth_test_{asyncio.get_event_loop().time()}@example.com"
        test_password = "SecurePass123!"
        test_name = "E2E Auth Test User"

        # Step 1: Register new user
        register_response = await api_client.register_user(
            email=test_email,
            password=test_password,
            name=test_name
        )

        # Validate registration response
        assert validator.validate_user_response(register_response)
        assert register_response["email"] == test_email
        assert register_response["name"] == test_name
        user_id = register_response["id"]

        # Step 2: Login with new credentials
        login_response = await api_client.login(test_email, test_password)

        # Validate login response
        assert validator.validate_auth_token_response(login_response)
        assert api_client.is_authenticated()

        # Step 3: Get user information
        user_info = await api_client.get_user_info()

        # Validate user info
        assert validator.validate_user_response(user_info)
        assert user_info["id"] == user_id
        assert user_info["email"] == test_email
        assert user_info["name"] == test_name

        # Step 4: Logout
        logout_response = await api_client.logout()
        assert validator.validate_success_message(logout_response)
        assert not api_client.is_authenticated()

        # Step 5: Verify cannot access protected endpoint after logout
        with pytest.raises(Exception) as exc_info:
            await api_client.get_user_info()
        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)

    async def test_token_refresh_flow(self, api_client: APIClient, validator: ResponseValidator):
        """Test token refresh workflow"""
        # Register and login
        test_email = f"e2e_refresh_test_{asyncio.get_event_loop().time()}@example.com"
        await api_client.register_user(
            email=test_email,
            password="RefreshTest123!",
            name="Refresh Test User"
        )
        login_response = await api_client.login(test_email, "RefreshTest123!")

        # Ensure we have a refresh token
        assert "refresh_token" in login_response
        original_access_token = api_client.auth_token

        # Wait a moment to ensure new token will be different
        await asyncio.sleep(1)

        # Refresh the token
        refresh_response = await api_client.refresh_access_token()

        # Validate refresh response
        assert validator.validate_auth_token_response(refresh_response)
        assert api_client.auth_token != original_access_token
        assert api_client.is_authenticated()

        # Verify new token works
        user_info = await api_client.get_user_info()
        assert user_info["email"] == test_email

    async def test_password_change_flow(self, api_client: APIClient, validator: ResponseValidator):
        """Test password change workflow"""
        # Register and login
        test_email = f"e2e_pwchange_test_{asyncio.get_event_loop().time()}@example.com"
        original_password = "Original123!"
        new_password = "NewSecure456!"

        await api_client.register_user(
            email=test_email,
            password=original_password,
            name="Password Change Test"
        )
        await api_client.login(test_email, original_password)

        # Change password
        change_response = await api_client.change_password(original_password, new_password)
        assert validator.validate_success_message(change_response)

        # Logout
        await api_client.logout()

        # Verify old password doesn't work
        with pytest.raises(Exception) as exc_info:
            await api_client.login(test_email, original_password)
        assert "401" in str(exc_info.value) or "Invalid" in str(exc_info.value)

        # Verify new password works
        login_response = await api_client.login(test_email, new_password)
        assert validator.validate_auth_token_response(login_response)
        assert api_client.is_authenticated()

    async def test_registration_validation(self, api_client: APIClient):
        """Test registration with various invalid inputs"""
        base_email = f"e2e_validation_{asyncio.get_event_loop().time()}"

        # Test invalid email format
        with pytest.raises(Exception) as exc_info:
            await api_client.register_user(
                email="invalid-email",
                password="ValidPass123!",
                name="Test User"
            )
        assert "email" in str(exc_info.value).lower()

        # Test weak password
        with pytest.raises(Exception) as exc_info:
            await api_client.register_user(
                email=f"{base_email}_weak@example.com",
                password="weak",
                name="Test User"
            )
        assert "password" in str(exc_info.value).lower()

        # Test missing required fields
        with pytest.raises(Exception) as exc_info:
            await api_client.register_user(
                email=f"{base_email}_missing@example.com",
                password="ValidPass123!",
                name=""
            )
        assert "name" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

        # Test duplicate email registration
        duplicate_email = f"{base_email}_dup@example.com"
        await api_client.register_user(
            email=duplicate_email,
            password="ValidPass123!",
            name="First User"
        )

        with pytest.raises(Exception) as exc_info:
            await api_client.register_user(
                email=duplicate_email,
                password="ValidPass123!",
                name="Second User"
            )
        assert "exists" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

    async def test_login_validation(self, api_client: APIClient):
        """Test login with invalid credentials"""
        # Test login with non-existent user
        with pytest.raises(Exception) as exc_info:
            await api_client.login(
                email="nonexistent@example.com",
                password="AnyPassword123!"
            )
        assert "401" in str(exc_info.value) or "Invalid" in str(exc_info.value)

        # Register a user for testing wrong password
        test_email = f"e2e_login_test_{asyncio.get_event_loop().time()}@example.com"
        correct_password = "Correct123!"

        await api_client.register_user(
            email=test_email,
            password=correct_password,
            name="Login Test User"
        )

        # Test login with wrong password
        with pytest.raises(Exception) as exc_info:
            await api_client.login(test_email, "Wrong123!")
        assert "401" in str(exc_info.value) or "Invalid" in str(exc_info.value)

        # Test login with correct credentials
        login_response = await api_client.login(test_email, correct_password)
        assert api_client.is_authenticated()

    @pytest.mark.slow
    async def test_concurrent_auth_sessions(self, api_request_context, validator: ResponseValidator):
        """Test multiple concurrent authentication sessions"""
        # Create multiple API clients
        clients = []
        for i in range(3):
            client = APIClient(api_request_context, "http://localhost:8000")
            clients.append(client)

        # Register and login with different users concurrently
        tasks = []
        for i, client in enumerate(clients):
            email = f"e2e_concurrent_{i}_{asyncio.get_event_loop().time()}@example.com"
            password = f"ConcurrentPass{i}123!"
            name = f"Concurrent User {i}"

            async def auth_flow(c, e, p, n):
                await c.register_user(email=e, password=p, name=n)
                return await c.login(e, p)

            tasks.append(auth_flow(client, email, password, name))

        # Execute all auth flows concurrently
        results = await asyncio.gather(*tasks)

        # Verify all clients are authenticated with different tokens
        tokens = set()
        for i, (client, result) in enumerate(zip(clients, results)):
            assert validator.validate_auth_token_response(result)
            assert client.is_authenticated()
            tokens.add(client.auth_token)

        # Ensure all tokens are unique
        assert len(tokens) == 3, "Each session should have a unique token"

        # Test each client can independently access their user info
        user_info_tasks = [client.get_user_info() for client in clients]
        user_infos = await asyncio.gather(*user_info_tasks)

        for i, user_info in enumerate(user_infos):
            assert validator.validate_user_response(user_info)
            assert f"Concurrent User {i}" in user_info["name"]

    async def test_auth_token_expiry_handling(self, api_client: APIClient, validator: ResponseValidator):
        """Test handling of expired authentication tokens"""
        # Register and login
        test_email = f"e2e_expiry_test_{asyncio.get_event_loop().time()}@example.com"
        await api_client.register_user(
            email=test_email,
            password="ExpiryTest123!",
            name="Expiry Test User"
        )
        login_response = await api_client.login(test_email, "ExpiryTest123!")

        # Save the current token
        valid_token = api_client.auth_token

        # Manually set an invalid/expired token
        api_client.auth_token = "invalid.expired.token"
        await api_client.context.set_extra_http_headers({
            "Authorization": f"Bearer {api_client.auth_token}"
        })

        # Try to access protected endpoint with invalid token
        with pytest.raises(Exception) as exc_info:
            await api_client.get_user_info()
        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)

        # Restore valid token and verify it still works
        api_client.auth_token = valid_token
        await api_client.context.set_extra_http_headers({
            "Authorization": f"Bearer {api_client.auth_token}"
        })

        user_info = await api_client.get_user_info()
        assert user_info["email"] == test_email

    async def test_security_headers_validation(self, api_client: APIClient):
        """Test that security headers are properly handled"""
        # Register and login
        test_email = f"e2e_security_test_{asyncio.get_event_loop().time()}@example.com"
        await api_client.register_user(
            email=test_email,
            password="Security123!",
            name="Security Test User"
        )
        await api_client.login(test_email, "Security123!")

        # Test request without Authorization header
        await api_client.context.set_extra_http_headers({})

        with pytest.raises(Exception) as exc_info:
            await api_client.get_user_info()
        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)

        # Test request with malformed Authorization header
        await api_client.context.set_extra_http_headers({
            "Authorization": "InvalidFormat token"
        })

        with pytest.raises(Exception) as exc_info:
            await api_client.get_user_info()
        assert "401" in str(exc_info.value) or "Unauthorized" in str(exc_info.value)

        # Test request with proper Bearer token format
        await api_client.context.set_extra_http_headers({
            "Authorization": f"Bearer {api_client.auth_token}"
        })

        user_info = await api_client.get_user_info()
        assert user_info["email"] == test_email