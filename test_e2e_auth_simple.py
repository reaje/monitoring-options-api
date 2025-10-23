"""
Simple direct E2E test for authentication
"""

import asyncio
import time
from playwright.async_api import async_playwright


async def test_auth_flow():
    """Test basic authentication flow"""
    print("\n" + "="*60)
    print("TESTING AUTHENTICATION FLOW")
    print("="*60)

    async with async_playwright() as p:
        # Create API request context
        context = await p.request.new_context(
            base_url="http://localhost:8000",
            ignore_https_errors=True,
            extra_http_headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        try:
            # Generate unique test email
            test_email = f"e2e_test_{int(time.time())}@example.com"
            test_password = "TestPassword123!"
            test_name = "E2E Test User"

            print(f"\n1. REGISTER USER")
            print(f"   Email: {test_email}")

            # Register user
            register_response = await context.post(
                "/auth/register",
                data={
                    "email": test_email,
                    "password": test_password,
                    "name": test_name
                }
            )

            print(f"   Status: {register_response.status}")

            if register_response.status == 201 or register_response.status == 200:
                register_data = await register_response.json()
                print(f"   [SUCCESS] User registered: {register_data.get('email')}")
                user_id = register_data.get("id")
            else:
                error_data = await register_response.text()
                print(f"   [FAIL] Registration failed: {error_data}")
                return False

            # Login
            print(f"\n2. LOGIN")
            login_response = await context.post(
                "/auth/login",
                data={
                    "email": test_email,
                    "password": test_password
                }
            )

            print(f"   Status: {login_response.status}")

            if login_response.status == 200:
                login_data = await login_response.json()
                print(f"   [SUCCESS] Login successful")
                access_token = login_data.get("access_token")
                print(f"   Token: {access_token[:20]}...")
            else:
                error_data = await login_response.text()
                print(f"   [FAIL] Login failed: {error_data}")
                return False

            # Get user info with token
            print(f"\n3. GET USER INFO")
            user_response = await context.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )

            print(f"   Status: {user_response.status}")

            if user_response.status == 200:
                user_data = await user_response.json()
                print(f"   [SUCCESS] User info retrieved")
                print(f"   User ID: {user_data.get('id')}")
                print(f"   Email: {user_data.get('email')}")
                print(f"   Name: {user_data.get('name')}")
            else:
                error_data = await user_response.text()
                print(f"   [FAIL] Failed to get user info: {error_data}")
                return False

            # Logout
            print(f"\n4. LOGOUT")
            logout_response = await context.post(
                "/auth/logout",
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )

            print(f"   Status: {logout_response.status}")

            if logout_response.status == 200:
                print(f"   [SUCCESS] Logout successful")
            else:
                print(f"   [WARNING] Logout status: {logout_response.status}")

            # Verify cannot access protected endpoint after logout
            print(f"\n5. VERIFY LOGOUT")
            verify_response = await context.get(
                "/auth/me",
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )

            print(f"   Status: {verify_response.status}")

            if verify_response.status == 401:
                print(f"   [SUCCESS] Access denied after logout (as expected)")
            else:
                print(f"   [FAIL] Unexpected status: {verify_response.status}")
                return False

            print("\n" + "="*60)
            print("[SUCCESS] AUTHENTICATION FLOW TEST PASSED!")
            print("="*60)
            return True

        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            return False

        finally:
            await context.dispose()


async def main():
    """Run the test"""
    success = await test_auth_flow()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)