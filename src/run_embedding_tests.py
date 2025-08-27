#!/usr/bin/env python3
"""Test runner for embedding module

Usage:
    python run_embedding_tests.py
"""

import sys
import unittest
from pathlib import Path

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

def run_embedding_tests():
    """Run all embedding module tests"""
    print("=== 埋め込みモジュールテスト実行 ===\n")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / 'tests' / 'embedding'
    suite = loader.discover(str(start_dir), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print results summary
    print(f"\n=== テスト結果サマリー ===")
    print(f"実行テスト数: {result.testsRun}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\nエラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✓' if success else '✗'} テスト{'成功' if success else '失敗'}")
    
    return success

if __name__ == "__main__":
    success = run_embedding_tests()
    sys.exit(0 if success else 1)