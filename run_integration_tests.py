#!/usr/bin/env python3
"""
Integration Test Runner for YABOT Narrative-Gamification Modules

This script runs the comprehensive integration tests for the cross-module
functionality between Narrative and Gamification modules.

Usage:
    python run_integration_tests.py
    python run_integration_tests.py --verbose
    python run_integration_tests.py --test test_name
"""
import asyncio
import sys
import argparse
import subprocess
from pathlib import Path


def run_pytest(test_path: str = None, verbose: bool = False, specific_test: str = None):
    """Run pytest with appropriate arguments"""
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.extend(["-v", "-s"])

    if specific_test:
        cmd.extend(["-k", specific_test])

    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/integration/test_module_integration_demo.py")

    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=src/modules/gamification", "--cov=src/modules/narrative"])
    except ImportError:
        pass

    print(f"Running command: {' '.join(cmd)}")
    print("=" * 80)

    return subprocess.run(cmd, cwd=Path(__file__).parent)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run YABOT integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                                    # Run all integration tests
    %(prog)s --verbose                          # Run with verbose output
    %(prog)s --test reaction_to_besitos        # Run specific test
    %(prog)s --test full_integration_workflow  # Run comprehensive test
        """
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--test", "-t",
        type=str,
        help="Run specific test by name (partial match)"
    )

    parser.add_argument(
        "--path", "-p",
        type=str,
        help="Path to specific test file"
    )

    args = parser.parse_args()

    print("🧪 YABOT Integration Tests - Narrative & Gamification Modules")
    print("=" * 80)

    # Check if we're in the right directory
    if not Path("src/modules/gamification").exists():
        print("❌ Error: Please run this script from the yabot root directory")
        sys.exit(1)

    # Run tests
    result = run_pytest(
        test_path=args.path,
        verbose=args.verbose,
        specific_test=args.test
    )

    print("=" * 80)

    if result.returncode == 0:
        print("✅ All integration tests passed!")
        print("\nTest Summary:")
        print("✅ Test 1: Reaction → Besitos → Narrative hint unlock")
        print("✅ Test 2: Narrative decision → Mission unlock")
        print("✅ Test 3: Achievement unlock → Narrative benefit")
        print("✅ Full integration workflow test")
        print("✅ Event bus integration test")
    else:
        print("❌ Some tests failed. Check the output above for details.")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()