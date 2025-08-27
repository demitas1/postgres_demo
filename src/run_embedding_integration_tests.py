#!/usr/bin/env python3
"""Integration test runner for embedding module with real OpenAI API

⚠️  WARNING: These tests use real OpenAI API and will incur costs!
⚠️  警告: このテストは実際のOpenAI APIを使用し、料金が発生します！

Usage:
    python run_embedding_integration_tests.py
    python run_embedding_integration_tests.py --skip-confirmation  # Skip cost warning
    python run_embedding_integration_tests.py --estimate-only     # Show cost estimate only
"""

import sys
import os
import unittest
import argparse
from pathlib import Path
from typing import Dict, Any

# Add current directory to Python path for imports
sys_path = str(Path(__file__).parent)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

def estimate_test_costs() -> Dict[str, Any]:
    """Estimate the cost of running integration tests
    
    Returns:
        Dictionary with cost estimation details
    """
    # Estimated token usage for each test
    test_estimates = {
        "test_single_japanese_text_embedding": 25,
        "test_multiple_recipe_texts_embedding": 60,
        "test_embedding_similarity_calculation": 50,
        "test_long_text_handling": 200,  # Long text test
        "test_empty_and_edge_cases": 5,
        "test_model_consistency": 20,
        "test_batch_processing_performance": 100  # 20 texts
    }
    
    total_tokens = sum(test_estimates.values())
    cost_per_1k_tokens = 0.00002  # USD for text-embedding-3-small
    estimated_cost = total_tokens / 1000 * cost_per_1k_tokens
    
    return {
        "total_estimated_tokens": total_tokens,
        "cost_per_1k_tokens_usd": cost_per_1k_tokens,
        "estimated_cost_usd": estimated_cost,
        "test_breakdown": test_estimates
    }

def show_cost_warning() -> bool:
    """Show cost warning and get user confirmation
    
    Returns:
        True if user confirms, False otherwise
    """
    cost_info = estimate_test_costs()
    
    print("=" * 60)
    print("⚠️  OpenAI API統合テスト実行前の警告")
    print("=" * 60)
    print()
    print("このテストは実際のOpenAI APIを使用するため、料金が発生します：")
    print()
    print(f"📊 推定使用量:")
    print(f"   • 総トークン数: {cost_info['total_estimated_tokens']:,}")
    print(f"   • 料金レート: ${cost_info['cost_per_1k_tokens_usd']:.5f} USD / 1,000トークン")
    print(f"   • 推定コスト: ${cost_info['estimated_cost_usd']:.6f} USD")
    print(f"                (約{cost_info['estimated_cost_usd'] * 150:.4f}円 @ 150円/USD)")
    print()
    print("🧪 実行されるテスト:")
    for test_name, tokens in cost_info['test_breakdown'].items():
        print(f"   • {test_name}: ~{tokens}トークン")
    print()
    print("💡 注意事項:")
    print("   • 実際のコストは入力テキストの長さにより変動します")
    print("   • ネットワーク状況により予想より時間がかかる場合があります")
    print("   • APIエラーが発生した場合も一部料金が発生する可能性があります")
    print()
    
    # Check if API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ エラー: OPENAI_API_KEY環境変数が設定されていません")
        print("   統合テストを実行するにはAPIキーが必要です")
        return False
    elif not api_key.startswith('sk-'):
        print("❌ エラー: OPENAI_API_KEYの形式が正しくありません")
        print("   APIキーは'sk-'で始まる必要があります")
        return False
    else:
        print(f"✓ APIキー確認済み: {api_key[:10]}...{api_key[-4:]}")
    
    print()
    print("=" * 60)
    
    while True:
        response = input("テストを実行しますか？ (y/N): ").strip().lower()
        if response in ['y', 'yes', 'はい']:
            print("\n✓ テスト実行を開始します...\n")
            return True
        elif response in ['n', 'no', 'いいえ', '']:
            print("\n❌ テスト実行をキャンセルしました")
            return False
        else:
            print("'y' (はい) または 'n' (いいえ) で答えてください")

def run_integration_tests(skip_confirmation: bool = False, estimate_only: bool = False) -> bool:
    """Run integration tests with cost warnings
    
    Args:
        skip_confirmation: Skip cost confirmation dialog
        estimate_only: Show cost estimate only, don't run tests
        
    Returns:
        True if tests pass, False otherwise
    """
    if estimate_only:
        cost_info = estimate_test_costs()
        print("=== OpenAI API統合テスト コスト見積もり ===")
        print(f"推定総トークン数: {cost_info['total_estimated_tokens']:,}")
        print(f"推定コスト: ${cost_info['estimated_cost_usd']:.6f} USD")
        return True
    
    print("=== OpenAI API統合テスト ===\n")
    
    # Show cost warning unless skipped
    if not skip_confirmation:
        if not show_cost_warning():
            return False
    
    # Check API key availability
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY環境変数が設定されていません")
        print("統合テストをスキップします")
        return True  # Not a failure, just skipped
    
    try:
        # Discover and run integration tests
        loader = unittest.TestLoader()
        integration_test_file = Path(__file__).parent / 'tests' / 'embedding' / 'test_openai_integration.py'
        
        if not integration_test_file.exists():
            print(f"❌ 統合テストファイルが見つかりません: {integration_test_file}")
            return False
        
        suite = loader.loadTestsFromName('test_openai_integration', 
                                       module=None)
        
        # Import the module manually
        spec = __import__('tests.embedding.test_openai_integration', fromlist=[''])
        suite = loader.loadTestsFromModule(spec)
        
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)
        
        # Print results summary
        print(f"\n=== 統合テスト結果サマリー ===")
        print(f"実行テスト数: {result.testsRun}")
        print(f"失敗: {len(result.failures)}")
        print(f"エラー: {len(result.errors)}")
        print(f"スキップ: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
        
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        success = len(result.failures) == 0 and len(result.errors) == 0
        print(f"\n{'✓' if success else '✗'} 統合テスト{'成功' if success else '失敗'}")
        
        if success:
            print("\n💡 統合テストが正常に完了しました。")
            print("実際のOpenAI APIとの通信が確認できました。")
        
        return success
        
    except Exception as e:
        print(f"\n❌ 統合テスト実行中にエラーが発生しました: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="OpenAI API統合テスト実行ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python run_embedding_integration_tests.py                    # 通常実行（確認あり）
  python run_embedding_integration_tests.py --skip-confirmation # 確認スキップ
  python run_embedding_integration_tests.py --estimate-only    # 見積もりのみ表示
        """
    )
    
    parser.add_argument(
        '--skip-confirmation', 
        action='store_true',
        help='コスト確認ダイアログをスキップ'
    )
    
    parser.add_argument(
        '--estimate-only',
        action='store_true', 
        help='コスト見積もりのみ表示してテストは実行しない'
    )
    
    args = parser.parse_args()
    
    success = run_integration_tests(
        skip_confirmation=args.skip_confirmation,
        estimate_only=args.estimate_only
    )
    
    if not success:
        print("\n統合テストの実行に失敗しました。")
        sys.exit(1)

if __name__ == "__main__":
    main()