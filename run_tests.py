#!/usr/bin/env python3
"""
Test runner script for Multi-Model Prompt Engine.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Run the test suite."""
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print("🧪 Running Multi-Model Prompt Engine Tests")
    print("=" * 50)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return False


def run_specific_test(test_file):
    """Run a specific test file."""
    
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print(f"🧪 Running specific test: {test_file}")
    print("=" * 50)
    
    cmd = [sys.executable, "-m", "pytest", test_file, "-v"]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Test passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Test failed with exit code {e.returncode}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        success = run_specific_test(test_file)
    else:
        # Run all tests
        success = run_tests()
    
    sys.exit(0 if success else 1)
