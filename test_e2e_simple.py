"""
Simple E2E test to verify the test setup is working
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright


async def test_api_health():
    """Test if API is accessible"""
    print("Starting simple E2E test...")

    async with async_playwright() as p:
        print("Creating API request context...")
        context = await p.request.new_context(
            base_url="http://localhost:8000",
            ignore_https_errors=True
        )

        try:
            # Test health endpoint
            print("Testing /health endpoint...")
            response = await context.get("/health")

            if response.status == 200:
                print(f"[SUCCESS] Health check passed! Status: {response.status}")
                body = await response.json()
                print(f"Response: {body}")
                return True
            else:
                print(f"[FAIL] Health check failed! Status: {response.status}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to connect to API: {str(e).replace('→', '->')}")
            print("\nMake sure the backend server is running:")
            print("  python app/main.py")
            return False

        finally:
            await context.dispose()


async def test_api_info():
    """Test root endpoint"""
    async with async_playwright() as p:
        context = await p.request.new_context(
            base_url="http://localhost:8000",
            ignore_https_errors=True
        )

        try:
            print("\nTesting / endpoint...")
            response = await context.get("/")

            if response.status == 200:
                print(f"[SUCCESS] Root endpoint accessible! Status: {response.status}")
                body = await response.json()
                print(f"API Info: {body}")
                return True
            else:
                print(f"[FAIL] Root endpoint failed! Status: {response.status}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to access root endpoint: {e}")
            return False

        finally:
            await context.dispose()


async def main():
    """Run simple E2E tests"""
    print("="*60)
    print("SIMPLE E2E TEST")
    print("="*60)

    # Run tests
    health_ok = await test_api_health()
    info_ok = await test_api_info()

    print("\n" + "="*60)
    if health_ok and info_ok:
        print("[SUCCESS] All tests passed!")
        print("\nYour E2E test environment is properly configured.")
        print("You can now run the full test suite with:")
        print("  pytest tests_e2e/")
    else:
        print("[FAILURE] Some tests failed!")
        print("\nPlease ensure:")
        print("1. The backend server is running (python app/main.py)")
        print("2. The server is accessible at http://localhost:8000")
        print("3. All dependencies are installed")
    print("="*60)

    return 0 if (health_ok and info_ok) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)