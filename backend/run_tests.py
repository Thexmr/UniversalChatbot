#!/usr/bin/env python3
"""
Test Runner for UniversalChatbot Backend
Runs all unit and integration tests
"""
import unittest
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def run_tests():
    """Discover and run all tests"""
    # Discover tests in both unit and integration directories
    loader = unittest.TestLoader()
    
    # Find all test files
    test_dir = backend_dir / 'tests'
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)


def run_unit_tests():
    """Run only unit tests"""
    loader = unittest.TestLoader()
    unit_dir = backend_dir / 'tests' / 'unit'
    suite = loader.discover(str(unit_dir), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)


def run_integration_tests():
    """Run only integration tests"""
    loader = unittest.TestLoader()
    integration_dir = backend_dir / 'tests' / 'integration'
    suite = loader.discover(str(integration_dir), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run UniversalChatbot tests')
    parser.add_argument(
        '--unit', 
        action='store_true', 
        help='Run only unit tests'
    )
    parser.add_argument(
        '--integration', 
        action='store_true', 
        help='Run only integration tests'
    )
    
    args = parser.parse_args()
    
    if args.unit:
        run_unit_tests()
    elif args.integration:
        run_integration_tests()
    else:
        run_tests()
