"""Script to run tests with proper setup."""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_tests():
    """Run pytest with recommended options."""
    print("=" * 60)
    print("Running Backend Tests")
    print("=" * 60)

    # Change to backend directory
    backend_dir = Path(__file__).parent.parent

    # Run pytest
    cmd = [
        "pytest",
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    # Add coverage if requested
    if "--cov" in sys.argv:
        cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
        ])

    # Add specific test path if provided
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        cmd.append(sys.argv[1])

    result = subprocess.run(cmd, cwd=backend_dir)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ Some tests failed")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    try:
        run_tests()
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)
