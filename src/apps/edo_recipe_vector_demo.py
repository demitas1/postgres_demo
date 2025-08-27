#!/usr/bin/env python3
"""江戸料理ベクター検索デモアプリケーション

PostgreSQLのpg_vector拡張とOpenAI埋め込みを使用した
意味的レシピ検索システムのデモンストレーション。

Usage:
    python edo_recipe_vector_demo.py
"""

import sys
from pathlib import Path

# Add embedding modules to path
sys.path.insert(0, str(Path(__file__).parent))

from common.database_config import DatabaseConfig
from common.edo_recipe_manager import EdoRecipeManager
from common.edo_recipe_vector_manager import EdoRecipeVectorManager
from common.json_recipe_loader import JsonRecipeLoader
from common.recipe_vector_search_service import RecipeVectorSearchService

from embedding.config.embedding_config import EmbeddingConfig
from embedding.client.openai_client import OpenAIEmbeddingClient
from embedding.processor.text_processor import RecipeTextProcessor
from embedding.processor.batch_processor import EmbeddingBatchProcessor


def get_json_file_path() -> str:
    """江戸料理JSONファイルのパスを取得"""
    json_path = "/app/src/test_data/edo_ryori/edo_recipes_all.json"
    return str(json_path)


def setup_base_recipe_data(manager: EdoRecipeManager) -> bool:
    """基本レシピデータのセットアップ
    
    Args:
        manager: EdoRecipeManagerインスタンス
        
    Returns:
        成功時True、失敗時False
    """
    print("=== 基本レシピデータセットアップ ===")
    
    # テーブル作成
    if not manager.tables_exist():
        print("基本レシピテーブル作成中...")
        if not manager.create_tables():
            return False
        print()
    else:
        print("✓ 基本レシピテーブルは既に存在します")
        print()
    
    # 既存データ確認
    existing_count = manager.get_total_recipes_count()
    if existing_count > 0:
        print(f"既に{existing_count}件のレシピが登録されています。")
        return True
    
    # JSONデータロード
    print("江戸料理レシピデータを読み込み中...")
    json_path = get_json_file_path()
    
    try:
        all_recipes = JsonRecipeLoader.load_edo_recipes_json(json_path)
        valid_recipes = JsonRecipeLoader.filter_valid_recipes(all_recipes)
        print(f"✓ {len(valid_recipes)}件の有効なレシピを検出しました")
        
        # データベースに挿入
        print("\nデータベースに挿入中...")
        success_count = 0
        
        for recipe in valid_recipes:
            recipe_data = JsonRecipeLoader.extract_recipe_data(recipe)
            
            if JsonRecipeLoader.validate_recipe_data(recipe_data):
                if manager.insert_recipe(recipe_data):
                    success_count += 1
        
        print(f"✓ {success_count}件のレシピを登録しました\n")
        return True
        
    except (FileNotFoundError, ValueError) as e:
        print(f"データ読み込みエラー: {e}")
        return False


def setup_vector_database_and_generate_embeddings(vector_manager: EdoRecipeVectorManager,
                                                 embedding_client: OpenAIEmbeddingClient,
                                                 embedding_config: EmbeddingConfig) -> bool:
    """ベクターデータベースセットアップと埋め込み生成
    
    Args:
        vector_manager: ベクターマネージャー
        embedding_client: 埋め込みクライアント
        embedding_config: 埋め込み設定
        
    Returns:
        成功時True、失敗時False
    """
    print("=== ベクターデータベースセットアップ ===")
    
    # ベクターテーブル作成
    if not vector_manager.vector_tables_exist():
        print("ベクターテーブル作成中...")
        if not vector_manager.create_vector_tables():
            return False
        print()
    else:
        print("✓ ベクターテーブルは既に存在します")
        print()
    
    # 既存ベクターデータ確認
    existing_vector_count = vector_manager.get_total_vector_recipes_count()
    modern_recipes = vector_manager.get_recipes_with_modern_data()
    
    print(f"現代レシピデータ対象: {len(modern_recipes)}件")
    print(f"既存ベクターデータ: {existing_vector_count}件")
    
    if existing_vector_count >= len(modern_recipes):
        print("✓ すべてのレシピが既にベクター化されています\n")
        return True
    
    # 埋め込み生成の確認
    remaining_recipes = len(modern_recipes) - existing_vector_count
    if remaining_recipes > 0:
        print(f"\n⚠️  {remaining_recipes}件のレシピの埋め込み生成が必要です")
        
        # コスト警告
        batch_processor = EmbeddingBatchProcessor(embedding_client, embedding_config)
        cost_estimate = batch_processor.estimate_processing_time(remaining_recipes)
        
        print("💰 推定コスト:")
        print(f"   トークン数: {cost_estimate['estimated_tokens']:,}")
        print(f"   推定時間: {cost_estimate['estimated_time_minutes']:.1f}分")
        print(f"   推定コスト: ${cost_estimate['estimated_cost_usd']:.6f} USD")
        print(f"             (約{cost_estimate['estimated_cost_jpy']:.3f}円)")
        
        response = input("\n埋め込み生成を実行しますか？ (y/N): ").strip().lower()
        if response not in ['y', 'yes', 'はい']:
            print("埋め込み生成をスキップしました")
            return True
    
    # 埋め込み生成処理
    print("\n🔄 埋め込み生成を開始...")
    
    # テキスト処理器の準備
    text_processor = RecipeTextProcessor()
    
    # 未処理レシピのデータ準備
    recipes_to_process = []
    
    for recipe_id, recipe_name in modern_recipes:
        # 既存チェック
        vector_manager.cur.execute("""
            SELECT EXISTS (SELECT 1 FROM edo_recipe_vectors WHERE recipe_id = %s);
        """, (recipe_id,))
        
        if vector_manager.cur.fetchone()[0]:
            continue  # 既に処理済み
        
        # テキストデータ取得
        text_data = vector_manager.get_recipe_text_data(recipe_id)
        if text_data:
            recipes_to_process.append(text_data)
    
    if not recipes_to_process:
        print("✓ 処理が必要なレシピがありません")
        return True
    
    # バッチ埋め込み生成
    batch_processor = EmbeddingBatchProcessor(embedding_client, embedding_config)
    processed_recipes = batch_processor.process_recipe_batch_sync(recipes_to_process)
    
    # データベースに保存
    print(f"\n💾 {len(processed_recipes)}件のベクターデータを保存中...")
    save_count = 0
    
    for recipe_data in processed_recipes:
        if vector_manager.insert_recipe_vectors(recipe_data):
            save_count += 1
    
    print(f"✓ {save_count}件のベクターデータを保存しました\n")
    return True


def demo_semantic_search(search_service: RecipeVectorSearchService, 
                        embedding_client: OpenAIEmbeddingClient) -> None:
    """意味的レシピ検索デモ"""
    print("=== 意味的レシピ検索デモ ===")
    
    # 検索クエリ例
    search_queries = [
        "卵を使った甘い料理",
        "温かい冬の料理",
        "贅沢で特別な日のご馳走",
        "シンプルで作りやすい料理"
    ]
    
    for query in search_queries:
        print(f"\n🔍 クエリ: '{query}'")
        
        try:
            # クエリの埋め込み生成
            query_embedding = embedding_client.get_single_embedding(query)
            
            # 意味的検索実行
            results = search_service.semantic_search_recipes(
                query_embedding, 
                search_type='combined',
                limit=3,
                similarity_threshold=0.1
            )
            
            if results:
                for recipe_id, recipe_name, similarity, matched_text, description in results:
                    print(f"  • {recipe_name} (ID: {recipe_id})")
                    print(f"    類似度: {similarity:.4f}")
                    if description:
                        desc_preview = description[:50].replace('\n', ' ')
                        print(f"    説明: {desc_preview}{'...' if len(description) > 50 else ''}")
            else:
                print("  該当するレシピが見つかりませんでした")
                
        except Exception as e:
            print(f"  ❌ 検索エラー: {e}")


def demo_similar_recipe_finder(search_service: RecipeVectorSearchService) -> None:
    """類似レシピ発見デモ"""
    print("\n=== 類似レシピ発見デモ ===")
    
    # サンプルレシピIDで類似レシピを検索
    sample_recipe_ids = [1, 5, 10]  # 存在するレシピIDを想定
    
    for recipe_id in sample_recipe_ids:
        # レシピ詳細取得
        recipe_details = search_service.get_recipe_details_with_vectors(recipe_id)
        
        if not recipe_details:
            continue
        
        print(f"\n📋 基準レシピ: '{recipe_details['name']}' (ID: {recipe_id})")
        
        # 類似レシピ検索
        similar_recipes = search_service.find_similar_recipes(
            recipe_id, 
            search_type='combined',
            limit=3,
            exclude_self=True
        )
        
        if similar_recipes:
            print("  類似レシピ:")
            for sim_id, sim_name, similarity, matched_text in similar_recipes:
                print(f"    • {sim_name} (ID: {sim_id}) - 類似度: {similarity:.4f}")
        else:
            print("  類似レシピが見つかりませんでした")


def demo_hybrid_search(search_service: RecipeVectorSearchService,
                      embedding_client: OpenAIEmbeddingClient) -> None:
    """ハイブリッド検索デモ"""
    print("\n=== ハイブリッド検索デモ（キーワード + ベクター） ===")
    
    hybrid_queries = [
        "卵",
        "醤油",
        "現代風"
    ]
    
    for query in hybrid_queries:
        print(f"\n🔄 ハイブリッド検索: '{query}'")
        
        try:
            # クエリの埋め込み生成
            query_embedding = embedding_client.get_single_embedding(query)
            
            # ハイブリッド検索実行
            results = search_service.hybrid_search(
                query, query_embedding,
                keyword_weight=0.4,
                vector_weight=0.6,
                limit=3
            )
            
            if results:
                for recipe_id, recipe_name, hybrid_score, keyword_score, vector_score in results:
                    print(f"  • {recipe_name} (ID: {recipe_id})")
                    print(f"    統合スコア: {hybrid_score:.4f}")
                    print(f"    (キーワード: {keyword_score:.4f}, ベクター: {vector_score:.4f})")
            else:
                print("  該当するレシピが見つかりませんでした")
                
        except Exception as e:
            print(f"  ❌ 検索エラー: {e}")


def demo_recipe_similarity_analysis(search_service: RecipeVectorSearchService) -> None:
    """レシピ類似性分析デモ"""
    print("\n=== レシピ類似性分析デモ ===")
    
    # 類似性の事前計算
    print("🔄 レシピ間類似性を計算中...")
    if search_service.calculate_recipe_similarities(limit_pairs=50):
        print("✓ 類似性計算完了")
        
        # 検索ログ表示
        logs = search_service.get_search_logs(limit=5)
        if logs:
            print("\n📊 最近の検索ログ:")
            for query_text, search_type, result_count, max_sim, avg_sim, exec_time, created_at in logs:
                print(f"  • {created_at}: '{query_text}' ({search_type})")
                print(f"    結果: {result_count}件, 最高類似度: {max_sim:.4f}, 実行時間: {exec_time:.1f}ms")
    else:
        print("⚠️  類似性計算に失敗しました")


def cleanup_vector_database(vector_manager: EdoRecipeVectorManager) -> bool:
    """ベクターデータベースクリーンアップ
    
    Args:
        vector_manager: ベクターマネージャー
        
    Returns:
        成功時True、失敗時False
    """
    print("\n=== ベクターデータベースクリーンアップ ===")
    
    response = input("ベクターテーブルを削除しますか？ (y/N): ").strip().lower()
    if response in ['y', 'yes', 'はい']:
        if vector_manager.drop_vector_tables():
            print("✓ ベクターテーブルを削除しました")
            return True
        else:
            print("✗ ベクターテーブル削除に失敗しました")
            return False
    else:
        print("クリーンアップをスキップしました")
        return True


def run_edo_recipe_vector_demo() -> bool:
    """江戸料理ベクター検索デモを実行
    
    Returns:
        実行成功時はTrue、失敗時はFalse
    """
    print("=== 江戸料理ベクター検索デモ ===\n")
    
    try:
        # 設定の取得
        db_config = DatabaseConfig.from_environment()
        embedding_config = EmbeddingConfig.from_environment()
        
        print(f"使用モデル: {embedding_config.embedding_model}")
        print(f"ベクター次元: {embedding_config.embedding_dimensions}\n")
        
    except ValueError as e:
        print(f"設定エラー: {e}")
        print("OpenAI APIキーが設定されているか確認してください")
        return False
    
    try:
        # 埋め込みクライアントの準備
        embedding_client = OpenAIEmbeddingClient(embedding_config)
        
        with EdoRecipeManager(db_config) as recipe_manager:
            # 1. 基本レシピデータセットアップ
            if not setup_base_recipe_data(recipe_manager):
                return False
            
            with EdoRecipeVectorManager(db_config) as vector_manager:
                # 2. ベクターデータベースセットアップと埋め込み生成
                if not setup_vector_database_and_generate_embeddings(
                    vector_manager, embedding_client, embedding_config):
                    return False
                
                # 3. ベクター検索デモ実行
                with RecipeVectorSearchService(db_config) as search_service:
                    demo_semantic_search(search_service, embedding_client)
                    demo_similar_recipe_finder(search_service)
                    demo_hybrid_search(search_service, embedding_client)
                    demo_recipe_similarity_analysis(search_service)
                
                # 4. クリーンアップ（オプション）
                if not cleanup_vector_database(vector_manager):
                    return False
        
        print(f"\n✓ 江戸料理ベクター検索デモ完了！")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    """メイン関数"""
    success = run_edo_recipe_vector_demo()
    
    if not success:
        print("\nデモの実行に失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()