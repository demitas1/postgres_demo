#!/usr/bin/env python3
"""都道府県データデモアプリケーション

PostgreSQLデータベースに都道府県データを登録し、
面積・人口のTOP3を表示するデモプログラム。

Usage:
    python prefecture_demo.py [--clean]
    
Options:
    --clean: 既存テーブルを削除してからクリーンスタート
"""

import sys
import argparse
from pathlib import Path

from common.database_config import DatabaseConfig
from common.prefecture_manager import PrefectureManager
from common.csv_loader import CSVLoader


def get_csv_file_path() -> str:
    """都道府県CSVファイルのパスを取得"""
    csv_path = "/app/src/test_data/prefectures/prefectures.csv"
    return str(csv_path)


def display_top_areas(prefecture_manager: PrefectureManager, limit: int = 3) -> None:
    """面積TOP3を表示"""
    print(f"\n=== 面積TOP{limit} ===")
    
    top_areas = prefecture_manager.get_top_prefectures_by_area(limit)
    if top_areas:
        for rank, (name, area) in enumerate(top_areas, 1):
            print(f"{rank}位: {name} ({area:,.2f} km²)")
    else:
        print("データの取得に失敗しました")


def display_top_populations(prefecture_manager: PrefectureManager, limit: int = 3) -> None:
    """人口TOP3を表示"""
    print(f"\n=== 人口TOP{limit} ===")
    
    top_populations = prefecture_manager.get_top_prefectures_by_population(limit)
    if top_populations:
        for rank, (name, population) in enumerate(top_populations, 1):
            print(f"{rank}位: {name} ({population:,} 人)")
    else:
        print("データの取得に失敗しました")


def run_prefecture_demo(clean_start: bool = False) -> bool:
    """都道府県デモを実行
    
    Args:
        clean_start: True の場合、既存テーブルを削除してから開始
        
    Returns:
        実行成功時はTrue、失敗時はFalse
    """
    print("=== 都道府県データデモ ===\n")
    
    # 環境に応じた設定を自動取得
    db_config = DatabaseConfig.from_environment()
    
    try:
        with PrefectureManager(db_config) as prefecture_manager:
            
            # 1. クリーンスタートの場合はテーブル削除
            if clean_start:
                print("クリーンスタートモード: 既存テーブルを削除中...")
                if not prefecture_manager.drop_tables():
                    return False
                print()
            
            # 2. テーブル作成
            print("テーブル作成中...")
            if not prefecture_manager.create_tables():
                return False
            print()
            
            # 3. 既存データの確認
            existing_records = prefecture_manager.get_total_records_count()
            if existing_records > 0 and not clean_start:
                print(f"既に{existing_records}件のデータが存在します。")
                print("データ挿入をスキップします。\n")
                skip_insert = True
            else:
                skip_insert = False
            
            # 4. CSVデータの読み込みと挿入
            if not skip_insert:
                print("CSVデータ読み込み中...")
                csv_path = get_csv_file_path()
                
                try:
                    prefecture_data = CSVLoader.load_prefectures_csv(csv_path)
                    print(f"✓ {len(prefecture_data)}件の都道府県データを読み込みました")
                    
                    # データバリデーション
                    if not CSVLoader.validate_csv_data(prefecture_data):
                        print("CSVデータのバリデーションに失敗しました")
                        return False
                    print("✓ データバリデーション完了")
                    
                except (FileNotFoundError, ValueError) as e:
                    print(f"CSVファイルの読み込みに失敗: {e}")
                    return False
                
                print("\nデータ挿入中...")
                if not prefecture_manager.insert_prefecture_data(prefecture_data):
                    return False
                print()
            
            # 5. 面積TOP3表示
            display_top_areas(prefecture_manager)
            
            # 6. 人口TOP3表示
            display_top_populations(prefecture_manager)
            
            print(f"\n✓ デモ完了！")
            return True
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False


def main() -> None:
    """メイン関数"""
    parser = argparse.ArgumentParser(description='都道府県データデモ')
    parser.add_argument('--clean', action='store_true', 
                       help='既存テーブルを削除してからクリーンスタート')
    
    args = parser.parse_args()
    
    success = run_prefecture_demo(clean_start=args.clean)
    
    if not success:
        print("\nデモの実行に失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()