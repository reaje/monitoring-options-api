#!/usr/bin/env python
"""
Script to run E2E tests with Playwright
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_command(command: list, description: str) -> int:
    """Execute a command and return the exit code"""
    print(f"\n>> {description}")
    print(f"   Command: {' '.join(command)}")
    print("-" * 60)

    result = subprocess.run(command, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"[OK] {description} completed successfully")
    else:
        print(f"[FAIL] {description} failed with exit code {result.returncode}")

    return result.returncode


def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")

    dependencies = [
        ("playwright", "playwright --version"),
        ("pytest", "pytest --version"),
        ("pytest-playwright", "python -c 'import pytest_playwright'")
    ]

    all_good = True
    for dep_name, check_cmd in dependencies:
        try:
            subprocess.run(check_cmd.split(), capture_output=True, check=True)
            print(f"  [OK] {dep_name} is installed")
        except:
            print(f"  [MISSING] {dep_name} is not installed")
            all_good = False

    if not all_good:
        print("\n[WARNING] Some dependencies are missing. Install them with:")
        print("   pip install playwright pytest-playwright")
        print("   playwright install chromium")
        return False

    return True


def ensure_server_running():
    """Check if the backend server is running"""
    import requests

    print("\nChecking if backend server is running...")

    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Backend server is running")
            return True
    except:
        pass

    print("  [WARNING] Backend server is not running!")
    print("  Please start the server with: python app/main.py")
    return False


def main():
    """Main function to run E2E tests"""
    parser = argparse.ArgumentParser(description="Run E2E tests with Playwright")
    parser.add_argument(
        "--test",
        type=str,
        help="Specific test file or pattern to run (e.g., test_auth_e2e.py)"
    )
    parser.add_argument(
        "--marker",
        type=str,
        help="Run tests with specific marker (e.g., smoke, auth, slow)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run tests in headed mode (show browser)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run tests in debug mode with verbose output"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML report after tests"
    )
    parser.add_argument(
        "--skip-server-check",
        action="store_true",
        help="Skip checking if backend server is running"
    )

    args = parser.parse_args()

    # Check dependencies
    if not check_dependencies():
        return 1

    # Check if server is running
    if not args.skip_server_check and not ensure_server_running():
        return 1

    # Build pytest command
    pytest_args = ["pytest", "tests_e2e"]

    # Add specific test file if provided
    if args.test:
        pytest_args = ["pytest", f"tests_e2e/{args.test}"]

    # Add common arguments
    pytest_args.extend([
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        f"-n={args.workers}",  # Number of workers for parallel execution
    ])

    # Add marker filter if provided
    if args.marker:
        pytest_args.extend(["-m", args.marker])

    # Add debug options
    if args.debug:
        pytest_args.extend([
            "-s",  # No capture, show print statements
            "--log-cli-level=DEBUG",
            "--tb=long"
        ])

    # Add headed mode for Playwright
    if args.headed:
        os.environ["HEADED"] = "1"

    # Add HTML report generation
    if args.report:
        pytest_args.extend([
            "--html=test-results/e2e_report.html",
            "--self-contained-html"
        ])

    # Create test results directory
    Path("test-results").mkdir(exist_ok=True)

    print("\n" + "=" * 60)
    print("RUNNING E2E TESTS WITH PLAYWRIGHT")
    print("=" * 60)

    # Run the tests
    exit_code = run_command(pytest_args, "Running E2E Tests")

    # Print summary
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("[SUCCESS] E2E TESTS PASSED!")
    else:
        print("[FAILURE] E2E TESTS FAILED!")
    print("=" * 60)

    if args.report and exit_code == 0:
        print("\nTest report generated at: test-results/e2e_report.html")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())