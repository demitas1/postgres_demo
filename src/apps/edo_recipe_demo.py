#!/usr/bin/env python3
"""江戸料理レシピ検索デモアプリケーション

PostgreSQLデータベースに江戸料理レシピデータを登録し、
各種検索機能をデモンストレーションするプログラム。

Usage:
    python edo_recipe_demo.py
"""

import sys
from pathlib import Path

from common.database_config import DatabaseConfig
from common.edo_recipe_manager import EdoRecipeManager
from common.json_recipe_loader import JsonRecipeLoader
from common.recipe_search_service import RecipeSearchService


def get_json_file_path() -> str:
    """江戸料理JSONファイルのパスを取得"""
    #current_file = Path(__file__)
    #project_root = current_file.parent.parent.parent
    #json_path = project_root / "test_data" / "edo_ryori" / "edo_recipes_all.json"
    json_path = "/app/src/test_data/edo_ryori/edo_recipes_all.json"
    return str(json_path)


def setup_database_and_load_data(manager: EdoRecipeManager) -> bool:
    """データベースのセットアップとデータロード
    
    Args:
        manager: EdoRecipeManagerインスタンス
        
    Returns:
        成功時True、失敗時False
    """
    print("=== データベースセットアップ ===")
    
    # テーブル作成
    if not manager.tables_exist():
        print("テーブル作成中...")
        if not manager.create_tables():
            return False
        print()
    else:
        print("✓ テーブルは既に存在します")
        print()
    
    # 既存データ確認
    existing_count = manager.get_total_recipes_count()
    if existing_count > 0:
        print(f"既に{existing_count}件のレシピが登録されています。")
        print("データロードをスキップします。\n")
        return True
    
    # JSONデータロード
    print("江戸料理レシピデータを読み込み中...")
    json_path = get_json_file_path()
    
    try:
        # JSONファイル読み込み
        all_recipes = JsonRecipeLoader.load_edo_recipes_json(json_path)
        print(f"✓ {len(all_recipes)}件のレシピデータを読み込みました")
        
        # 有効なレシピのフィルタリング
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
            else:
                print(f"Warning: レシピID {recipe.get('id')} のバリデーションに失敗しました")
        
        print(f"✓ {success_count}件のレシピを登録しました\n")
        return True
        
    except (FileNotFoundError, ValueError) as e:
        print(f"データ読み込みエラー: {e}")
        return False


def demo_ingredient_search(search_service: RecipeSearchService) -> None:
    """材料での検索デモ"""
    print("=== 材料検索デモ ===")
    
    # いくつかの材料で検索
    search_ingredients = ["卵", "うに", "醤油"]
    
    for ingredient in search_ingredients:
        print(f"\n'{ingredient}' を使ったレシピを検索中...")
        results = search_service.search_by_ingredient(ingredient, 3)
        
        if results:
            for recipe_id, recipe_name, ingredients in results:
                print(f"  • {recipe_name} (ID: {recipe_id})")
                print(f"    材料: {', '.join(ingredients[:3])}{'...' if len(ingredients) > 3 else ''}")
        else:
            print(f"  '{ingredient}' を使ったレシピが見つかりませんでした")


def demo_fulltext_search(search_service: RecipeSearchService) -> None:
    """全文検索デモ"""
    print("\n=== 全文検索デモ ===")
    
    # いくつかのキーワードで検索
    search_keywords = ["卵", "濃厚", "現代"]
    
    for keyword in search_keywords:
        print(f"\n'{keyword}' でレシピを全文検索中...")
        results = search_service.search_by_fulltext(keyword, 3)
        
        if results:
            for recipe_id, recipe_name, description, rank in results:
                print(f"  • {recipe_name} (ID: {recipe_id}, スコア: {rank:.3f})")
                if description:
                    desc_preview = description[:50].replace('\n', ' ')
                    print(f"    説明: {desc_preview}{'...' if len(description) > 50 else ''}")
        else:
            print(f"  '{keyword}' に関するレシピが見つかりませんでした")


def demo_combined_search(search_service: RecipeSearchService) -> None:
    """複合検索デモ"""
    print("\n=== 複合検索デモ ===")
    
    # レシピ名 + 材料での検索
    search_combinations = [
        ("卵", "ウニ"),
        ("濃厚", "卵白"),
        ("現代", "油")
    ]
    
    for recipe_keyword, ingredient_keyword in search_combinations:
        print(f"\nレシピ名に'{recipe_keyword}'、材料に'{ingredient_keyword}'を含むレシピを検索中...")
        results = search_service.search_combined(recipe_keyword, ingredient_keyword, 2)
        
        if results:
            for recipe_id, recipe_name, description, ingredients in results:
                print(f"  • {recipe_name} (ID: {recipe_id})")
                print(f"    材料: {', '.join(ingredients[:3])}{'...' if len(ingredients) > 3 else ''}")
                if description:
                    desc_preview = description[:40].replace('\n', ' ')
                    print(f"    説明: {desc_preview}{'...' if len(description) > 40 else ''}")
        else:
            print(f"  条件に合うレシピが見つかりませんでした")


def show_recipe_detail_example(search_service: RecipeSearchService) -> None:
    """レシピ詳細表示例"""
    print("\n=== レシピ詳細表示例 ===")
    
    # ランダムなレシピを1つ取得して詳細表示
    random_recipes = search_service.get_random_recipes(1)
    
    if random_recipes:
        recipe_id, recipe_name = random_recipes[0]
        print(f"\n'{recipe_name}' の詳細情報:")
        
        details = search_service.get_recipe_details(recipe_id)
        if details:
            print(f"URL: {details['url']}")
            print(f"説明: {details['description'][:100]}{'...' if len(details.get('description', '')) > 100 else ''}")
            print(f"材料数: {len(details['ingredients'])}種類")
            print(f"現代手順数: {len(details['modern_instructions'])}ステップ")
            if details['tips']:
                print(f"コツ: {details['tips']}")


def cleanup_database(manager: EdoRecipeManager) -> bool:
    """データベースクリーンアップ
    
    Args:
        manager: EdoRecipeManagerインスタンス
        
    Returns:
        成功時True、失敗時False
    """
    print("\n=== データベースクリーンアップ ===")
    
    if manager.drop_tables():
        print("✓ 江戸料理レシピテーブルを削除しました")
        return True
    else:
        print("✗ テーブル削除に失敗しました")
        return False


def run_edo_recipe_demo() -> bool:
    """江戸料理レシピデモを実行
    
    Returns:
        実行成功時はTrue、失敗時はFalse
    """
    print("=== 江戸料理レシピ検索デモ ===\n")
    
    # 環境に応じた設定を自動取得
    db_config = DatabaseConfig.from_environment()
    
    try:
        with EdoRecipeManager(db_config) as manager:
            # 1. データベースセットアップとデータロード
            if not setup_database_and_load_data(manager):
                return False
            
            # 2. 検索デモ実行
            with RecipeSearchService(db_config) as search_service:
                demo_ingredient_search(search_service)
                demo_fulltext_search(search_service)
                demo_combined_search(search_service)
                show_recipe_detail_example(search_service)
            
            # 3. クリーンアップ
            if not cleanup_database(manager):
                return False
            
            print(f"\n✓ 江戸料理レシピデモ完了！")
            return True
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False


def main() -> None:
    """メイン関数"""
    success = run_edo_recipe_demo()
    
    if not success:
        print("\nデモの実行に失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()