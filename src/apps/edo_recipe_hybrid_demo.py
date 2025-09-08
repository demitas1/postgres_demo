#!/usr/bin/env python3
"""
江戸料理ハイブリッド検索デモ
pg_bigm（全文検索）とpg_vector（ベクトル検索）を組み合わせた高度な検索システムの実演

使用方法:
    python src/apps/edo_recipe_hybrid_demo.py
"""
import sys
import os
import traceback
from typing import List, Dict, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.database_config import DatabaseConfig
from common.hybrid_recipe_search_service import HybridRecipeSearchService
from common.search_models import (
    SearchCondition, SearchMode, SearchResponse, DEMO_SCENARIOS,
    PerformanceComparison
)


class HybridSearchDemo:
    """ハイブリッド検索デモのメインクラス"""
    
    def __init__(self):
        """デモ初期化"""
        self.db_config = DatabaseConfig.from_environment()
        self.search_service = HybridRecipeSearchService(self.db_config)
        print("🔍 江戸料理ハイブリッド検索デモを初期化しました")
    
    def run_demo(self):
        """メインデモループ"""
        print("\n" + "=" * 50)
        print("🍱 江戸料理ハイブリッド検索デモへようこそ！")
        print("=" * 50)
        print("このデモでは、PostgreSQLのpg_bigm（全文検索）と")
        print("pg_vector（ベクトル検索）を組み合わせた高度な検索を体験できます。")
        
        while True:
            try:
                choice = self._show_main_menu()
                
                if choice == "1":
                    self._run_custom_search()
                elif choice == "2":
                    self._run_scenario_search()
                elif choice == "3":
                    self._run_performance_comparison()
                elif choice == "4":
                    self._run_basic_data_initialization()
                elif choice == "5":
                    self._run_vector_initialization()
                elif choice == "6":
                    self._run_data_cleanup()
                elif choice == "7":
                    print("\n👋 デモを終了します。ありがとうございました！")
                    break
                else:
                    print("❌ 無効な選択です。1-7の数字を入力してください。")
                
                input("\n⏸️  何かキーを押して続行...")
                
            except KeyboardInterrupt:
                print("\n\n👋 デモを終了します。")
                break
            except Exception as e:
                print(f"\n❌ エラーが発生しました: {e}")
                print("詳細:")
                traceback.print_exc()
                input("何かキーを押して続行...")
    
    def _show_main_menu(self) -> str:
        """メインメニュー表示"""
        print("\n" + "=" * 40)
        print("🔍 ハイブリッド検索デモ")
        print("=" * 40)
        print("1. カスタム検索 - 自由な条件設定")
        print("2. シナリオ検索 - 事前定義された実用例")
        print("3. 性能比較デモ - 各検索手法の性能測定")
        print("4. 基本データ初期化 - 江戸料理レシピデータの作成")
        print("5. ベクター初期化 - 全レシピの埋め込みデータ生成")
        print("6. 全データ消去 - デモ用テーブルの完全削除")
        print("7. 終了")
        print()
        
        return input("選択してください [1-7]: ").strip()
    
    def _run_custom_search(self):
        """カスタム検索実行"""
        print("\n" + "=" * 30)
        print("📝 カスタム検索")
        print("=" * 30)
        
        try:
            condition = self._build_custom_condition()
            if condition:
                print(f"\n🔍 検索モード: {condition.search_mode.value}")
                print("検索を実行しています...")
                
                response = self.search_service.search_recipes(condition)
                self._display_search_results(response)
            else:
                print("❌ 検索条件の設定がキャンセルされました。")
                
        except Exception as e:
            print(f"❌ カスタム検索エラー: {e}")
            traceback.print_exc()
    
    def _build_custom_condition(self) -> Optional[SearchCondition]:
        """カスタム検索条件を構築"""
        print("\n■ 必須キーワード設定")
        required_input = input("含まなければならない言葉（複数可、カンマ区切り）: ").strip()
        required_keywords = [kw.strip() for kw in required_input.split(",") if kw.strip()] if required_input else []
        
        required_threshold = 0.1
        if required_keywords:
            threshold_input = input(f"類似度閾値 [0.1-1.0] (デフォルト: 0.1): ").strip()
            if threshold_input:
                try:
                    required_threshold = float(threshold_input)
                    required_threshold = max(0.1, min(1.0, required_threshold))
                except ValueError:
                    print("⚠️  無効な閾値です。デフォルト値 0.1 を使用します。")
        
        print("\n■ 除外キーワード設定")
        excluded_input = input("含んではならない言葉（複数可、カンマ区切り）: ").strip()
        excluded_keywords = [kw.strip() for kw in excluded_input.split(",") if kw.strip()] if excluded_input else []
        
        excluded_threshold = 0.1
        if excluded_keywords:
            threshold_input = input(f"類似度閾値 [0.1-1.0] (デフォルト: 0.1): ").strip()
            if threshold_input:
                try:
                    excluded_threshold = float(threshold_input)
                    excluded_threshold = max(0.1, min(1.0, excluded_threshold))
                except ValueError:
                    print("⚠️  無効な閾値です。デフォルト値 0.1 を使用します。")
        
        print("\n■ 意味的検索設定")
        vector_query = input("検索したい料理のイメージ: ").strip()
        
        print("\n■ スコア重み設定")
        fulltext_weight = 0.5
        vector_weight = 0.5
        
        if required_keywords or excluded_keywords:
            weight_input = input("キーワードマッチ重み [0.0-1.0] (デフォルト: 0.5): ").strip()
            if weight_input:
                try:
                    fulltext_weight = float(weight_input)
                    fulltext_weight = max(0.0, min(1.0, fulltext_weight))
                    vector_weight = 1.0 - fulltext_weight
                except ValueError:
                    print("⚠️  無効な重みです。デフォルト値 0.5 を使用します。")
        
        if vector_query:
            vector_weight_input = input(f"意味的類似度重み [0.0-1.0] (デフォルト: {vector_weight:.1f}): ").strip()
            if vector_weight_input:
                try:
                    vector_weight = float(vector_weight_input)
                    vector_weight = max(0.0, min(1.0, vector_weight))
                    fulltext_weight = 1.0 - vector_weight
                except ValueError:
                    print(f"⚠️  無効な重みです。デフォルト値 {vector_weight:.1f} を使用します。")
        
        print("\n■ 検索モード")
        print("1. 段階的検索（高速）  2. 並列検索（高精度）")
        print("3. キーワードのみ     4. 意味検索のみ")
        
        mode_choice = input("選択 [1-4]: ").strip()
        mode_map = {
            "1": SearchMode.CASCADE,
            "2": SearchMode.PARALLEL,
            "3": SearchMode.FULLTEXT_ONLY,
            "4": SearchMode.VECTOR_ONLY
        }
        search_mode = mode_map.get(mode_choice, SearchMode.CASCADE)
        
        print("\n■ 結果設定")
        max_results = 10
        max_input = input("最大表示件数 [1-100] (デフォルト: 10): ").strip()
        if max_input:
            try:
                max_results = int(max_input)
                max_results = max(1, min(100, max_results))
            except ValueError:
                print("⚠️  無効な件数です。デフォルト値 10 を使用します。")
        
        # Confirm search execution
        print(f"\n📋 検索条件確認:")
        if required_keywords:
            print(f"  ✅ 必須キーワード: {', '.join(required_keywords)} (閾値: {required_threshold})")
        if excluded_keywords:
            print(f"  ❌ 除外キーワード: {', '.join(excluded_keywords)} (閾値: {excluded_threshold})")
        if vector_query:
            print(f"  🎯 意味的検索: \"{vector_query}\"")
        print(f"  ⚖️  重み: キーワード({fulltext_weight:.1f}) + 意味的({vector_weight:.1f})")
        print(f"  🔍 モード: {search_mode.value}")
        print(f"  📊 最大件数: {max_results}件")
        
        confirm = input("\n検索を実行しますか？ [y/n]: ").strip().lower()
        if confirm not in ['y', 'yes', 'はい']:
            return None
        
        return SearchCondition(
            required_keywords=required_keywords,
            required_similarity_threshold=required_threshold,
            excluded_keywords=excluded_keywords,
            excluded_similarity_threshold=excluded_threshold,
            vector_query_text=vector_query,
            fulltext_weight=fulltext_weight,
            vector_weight=vector_weight,
            search_mode=search_mode,
            max_results=max_results
        )
    
    def _run_scenario_search(self):
        """シナリオ検索実行"""
        print("\n" + "=" * 30)
        print("📚 シナリオ検索")
        print("=" * 30)
        print("実用的な検索パターンを体験できます\n")
        
        scenarios = list(DEMO_SCENARIOS.keys())
        descriptions = {
            "卵料理専門": "🥚 様々な技法で作る多彩な卵料理",
            "華やか卵料理": "🌈 見た目も美しい華やかな卵料理",
            "お吸い物風": "🍲 上品でやさしい味わいの料理",
            "色鮮やか卵": "🎨 カラフルで色とりどりの卵料理"
        }
        
        for i, scenario in enumerate(scenarios, 1):
            desc = descriptions.get(scenario, "")
            print(f"{i}. {scenario}")
            print(f"   {desc}")
            print()
        
        choice = input(f"選択してください [1-{len(scenarios)}]: ").strip()
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(scenarios):
                scenario_name = scenarios[choice_idx]
                condition = DEMO_SCENARIOS[scenario_name]
                
                print(f"\n=== {scenario_name} ===")
                self._display_scenario_condition(condition)
                
                confirm = input("この条件で検索しますか？ [y/n/c(カスタマイズ)]: ").strip().lower()
                
                if confirm in ['c', 'custom', 'カスタマイズ']:
                    # Allow customization (simplified)
                    print("\n重み調整（オプション）:")
                    weight_input = input(f"キーワード重み [0.0-1.0] (現在: {condition.fulltext_weight:.1f}): ").strip()
                    if weight_input:
                        try:
                            condition.fulltext_weight = float(weight_input)
                            condition.vector_weight = 1.0 - condition.fulltext_weight
                        except ValueError:
                            pass
                
                if confirm in ['y', 'yes', 'はい', 'c', 'custom', 'カスタマイズ']:
                    print("🔍 検索を実行しています...")
                    response = self.search_service.search_recipes(condition)
                    self._display_search_results(response)
                else:
                    print("❌ 検索がキャンセルされました。")
            else:
                print("❌ 無効な選択です。")
        except ValueError:
            print("❌ 無効な入力です。")
        except Exception as e:
            print(f"❌ シナリオ検索エラー: {e}")
            traceback.print_exc()
    
    def _display_scenario_condition(self, condition: SearchCondition):
        """シナリオ検索条件の表示"""
        print("【検索条件】")
        if condition.required_keywords:
            print(f"  ✅ 必須: {' OR '.join(condition.required_keywords)}")
        if condition.excluded_keywords:
            print(f"  ❌ 除外: {' AND '.join(condition.excluded_keywords)}")
        if condition.vector_query_text:
            print(f"  🎯 意味検索: \"{condition.vector_query_text}\"")
        print(f"  ⚖️  重み: キーワード({int(condition.fulltext_weight*100)}%) + 意味的({int(condition.vector_weight*100)}%)")
        print(f"  🔍 モード: {condition.search_mode.value}")
        print()
    
    def _run_performance_comparison(self):
        """性能比較デモ実行"""
        print("\n" + "=" * 30)
        print("⚡ 検索手法性能比較")
        print("=" * 30)
        print("同じ条件で異なる検索手法を比較します\n")
        
        print("テスト条件を選択:")
        print("1. 軽い条件（高速テスト）")
        print("2. 標準条件（バランステスト）")
        print("3. 重い条件（性能限界テスト）")
        print("4. カスタム条件")
        
        choice = input("選択 [1-4]: ").strip()
        
        # Define test conditions
        test_conditions = {
            "1": SearchCondition(
                required_keywords=["だし"],
                vector_query_text="魚料理",
                fulltext_weight=0.5,
                vector_weight=0.5,
                max_results=10
            ),
            "2": SearchCondition(
                required_keywords=["野菜", "豆腐"],
                excluded_keywords=["肉"],
                vector_query_text="健康的な料理",
                fulltext_weight=0.4,
                vector_weight=0.6,
                max_results=15
            ),
            "3": SearchCondition(
                required_keywords=["料理"],  # Broad match
                vector_query_text="美味しい食事",  # Abstract query
                fulltext_weight=0.5,
                vector_weight=0.5,
                max_results=20
            )
        }
        
        if choice in test_conditions:
            condition = test_conditions[choice]
        elif choice == "4":
            condition = self._build_custom_condition()
            if not condition:
                print("❌ カスタム条件の設定がキャンセルされました。")
                return
        else:
            print("❌ 無効な選択です。")
            return
        
        print(f"\n🔍 性能比較を実行中...")
        print("各検索手法を順次実行します...\n")
        
        try:
            # Run individual searches for detailed metrics
            modes = [
                (SearchMode.CASCADE, "段階的検索"),
                (SearchMode.PARALLEL, "並列検索"),
                (SearchMode.FULLTEXT_ONLY, "キーワードのみ"),
                (SearchMode.VECTOR_ONLY, "意味検索のみ")
            ]
            
            results = {}
            
            for mode, name in modes:
                print(f"🔍 {name}を実行中...")
                test_condition = SearchCondition(**{**condition.__dict__, 'search_mode': mode})
                response = self.search_service.search_recipes(test_condition)
                results[mode] = response
                
                print(f"実行時間: {response.execution_time:.3f}秒 | "
                      f"CPU使用率: {response.performance_metrics.cpu_percent:.1f}% | "
                      f"メモリ使用量: {response.performance_metrics.memory_usage_mb:.1f}MB | "
                      f"マッチ数: {len(response.results)}件")
                print()
            
            # Display comparison table
            self._display_performance_table(results)
            
            # Show recommendation
            comparison = self.search_service.compare_search_modes(condition)
            print(f"【推奨】この条件では「{comparison.recommended_mode.value}」が最適です")
            print(f"理由: {comparison.recommendation_reason}")
            
        except Exception as e:
            print(f"❌ 性能比較エラー: {e}")
            traceback.print_exc()
    
    def _display_performance_table(self, results: Dict[SearchMode, SearchResponse]):
        """性能比較テーブルの表示"""
        print("=" * 80)
        print("📊 検索手法性能比較結果")
        print("=" * 80)
        
        header = f"{'検索手法':<12} {'実行時間':<8} {'CPU使用率':<8} {'メモリ':<8} {'マッチ数':<8} {'推奨用途':<10}"
        print(header)
        print("-" * 75)
        
        mode_names = {
            SearchMode.CASCADE: "段階的検索",
            SearchMode.PARALLEL: "並列検索", 
            SearchMode.FULLTEXT_ONLY: "キーワードのみ",
            SearchMode.VECTOR_ONLY: "意味検索のみ"
        }
        
        use_cases = {
            SearchMode.CASCADE: "バランス",
            SearchMode.PARALLEL: "高精度",
            SearchMode.FULLTEXT_ONLY: "高速",
            SearchMode.VECTOR_ONLY: "発見性"
        }
        
        for mode, response in results.items():
            name = mode_names[mode]
            time_str = f"{response.execution_time:.3f}秒"
            cpu_str = f"{response.performance_metrics.cpu_percent:.1f}%"
            memory_str = f"{response.performance_metrics.memory_usage_mb:.0f}MB"
            count_str = f"{len(response.results)}件"
            use_case = use_cases[mode]
            
            print(f"{name:<12} {time_str:<8} {cpu_str:<8} {memory_str:<8} {count_str:<8} {use_case:<10}")
        
        print("=" * 80)
    
    def _display_search_results(self, response: SearchResponse):
        """検索結果の表示"""
        print("\n" + "=" * 60)
        print("📋 検索結果")
        print("=" * 60)
        
        print(f"実行時間: {response.execution_time:.3f}秒 | "
              f"総マッチ数: {response.total_matches}件 | "
              f"表示: {len(response.results)}件")
        
        if response.performance_metrics:
            print(f"CPU使用率: {response.performance_metrics.cpu_percent:.1f}% | "
                  f"メモリ使用量: {response.performance_metrics.memory_usage_mb:.0f}MB")
        
        # Display search stages
        if response.search_stages:
            print(f"\n【検索処理の流れ】")
            for stage in response.search_stages:
                flow = f"{stage.candidates_in}件 → {stage.candidates_out}件" if stage.candidates_in > 0 else f"{stage.candidates_out}件"
                print(f"  {stage.stage_name}: {flow} ({stage.execution_time:.3f}秒)")
        
        if not response.results:
            print("\n❌ 検索条件に一致するレシピが見つかりませんでした。")
            print("💡 条件を緩和するか、別のキーワードを試してください。")
            return
        
        print("\n" + "━" * 80)
        
        # Display top results
        for i, result in enumerate(response.results[:10]):  # Show top 10
            rank_emoji = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            emoji = rank_emoji[i] if i < len(rank_emoji) else "📍"
            
            print(f"\n{emoji} 第{result.rank}位 (総合スコア: {result.combined_score:.2f})")
            print(f"【レシピ名】{result.recipe_name}")
            print(f"【説明文】{result.description[:100]}{'...' if len(result.description) > 100 else ''}")
            print(f"【材料】{result.ingredients[:100]}{'...' if len(result.ingredients) > 100 else ''}")
            
            print(f"【マッチ詳細】")
            if result.matched_keywords:
                print(f"  ✅ 必須キーワード: {', '.join(result.matched_keywords)}")
            if result.excluded_keywords:
                print(f"  ❌ 除外キーワード: {', '.join(result.excluded_keywords)}")
            if result.vector_score > 0:
                print(f"  🎯 意味的類似度: {result.vector_score:.2f}")
            
            if response.search_condition:
                condition = response.search_condition
                print(f"  📊 スコア内訳: "
                      f"キーワード({result.fulltext_score:.2f}) × {condition.fulltext_weight:.1f} + "
                      f"意味的({result.vector_score:.2f}) × {condition.vector_weight:.1f} = "
                      f"{result.combined_score:.2f}")
            
            print("━" * 80)
        
        # Show pagination options if there are more results
        if len(response.results) > 10:
            print(f"\n💡 残り {len(response.results) - 10}件の結果があります。")
        
        print(f"\n【操作】")
        print("検索結果の表示が完了しました。")
    
    def _run_basic_data_initialization(self):
        """基本データ初期化実行"""
        print("\n" + "=" * 40)
        print("🔧 基本データ初期化")
        print("=" * 40)
        
        print("江戸料理レシピの基本データを初期化します。")
        print("この処理では以下のテーブルを作成・データを投入します:")
        print("  • edo_recipes (レシピ基本情報)")
        print("  • recipe_ingredients (材料情報)")
        print("  • recipe_instructions (手順情報)")
        print()
        
        try:
            # Use EdoRecipeManager for basic data setup
            from common.edo_recipe_manager import EdoRecipeManager
            from common.json_recipe_loader import JsonRecipeLoader
            
            manager = EdoRecipeManager(self.db_config)
            
            print("📊 データベース状態確認中...")
            
            # Check if tables exist
            if not manager.tables_exist():
                print("  ⚠️  基本テーブルが存在しません。作成します...")
                if not manager.create_tables():
                    print("❌ テーブル作成に失敗しました。")
                    return
                print("  ✅ 基本テーブルを作成しました")
            else:
                print("  ✅ 基本テーブルは既に存在します")
            
            # Check existing data
            existing_count = manager.get_total_recipes_count()
            print(f"  📋 既存レシピ数: {existing_count}件")
            
            if existing_count > 0:
                print(f"\n✅ 既に{existing_count}件のレシピが登録されています。")
                print("データロードをスキップします。")
                manager.close()
                return
            
            # Load JSON data
            print("\n🔄 江戸料理JSONデータを読み込み中...")
            json_path = "/app/src/test_data/edo_ryori/edo_recipes_all.json"
            
            try:
                # Load and validate recipes
                all_recipes = JsonRecipeLoader.load_edo_recipes_json(json_path)
                print(f"  ✅ {len(all_recipes)}件のレシピデータを読み込みました")
                
                valid_recipes = JsonRecipeLoader.filter_valid_recipes(all_recipes)
                print(f"  ✅ {len(valid_recipes)}件の有効なレシピを検出しました")
                
                # Insert into database
                print(f"\n💾 データベースに挿入中...")
                success_count = 0
                
                for i, recipe in enumerate(valid_recipes, 1):
                    recipe_data = JsonRecipeLoader.extract_recipe_data(recipe)
                    
                    if JsonRecipeLoader.validate_recipe_data(recipe_data):
                        if manager.insert_recipe(recipe_data):
                            success_count += 1
                            if success_count % 5 == 0:
                                print(f"  進捗: {success_count}件完了")
                    else:
                        print(f"  ⚠️  レシピID {recipe.get('id')} のバリデーションに失敗しました")
                
                print(f"\n🎉 基本データ初期化が完了しました！")
                print(f"  📊 登録されたレシピ: {success_count}件")
                print(f"  📋 テーブル: edo_recipes, recipe_ingredients, recipe_instructions")
                print(f"\n💡 次のステップ:")
                print(f"  • ベクター初期化を実行して意味検索を有効化")
                print(f"  • カスタム検索やシナリオ検索をお試しください")
                
            except (FileNotFoundError, ValueError) as e:
                print(f"❌ データ読み込みエラー: {e}")
                print("JSONファイルパスを確認してください:")
                print(f"  期待パス: {json_path}")
            
            manager.close()
            
        except Exception as e:
            print(f"❌ 基本データ初期化エラー: {e}")
            import traceback
            traceback.print_exc()
    
    def _run_vector_initialization(self):
        """ベクター初期化実行"""
        print("\n" + "=" * 40)
        print("🔧 ベクター初期化")
        print("=" * 40)
        
        try:
            # Import here to avoid circular import
            from common.edo_recipe_hybrid_manager import EdoRecipeHybridManager
            
            # Check current status
            with EdoRecipeHybridManager(self.db_config) as manager:
                manager.cur.execute('SELECT COUNT(*) FROM edo_recipes')
                total_recipes = manager.cur.fetchone()[0]
                
                try:
                    manager.cur.execute('SELECT COUNT(*) FROM edo_recipe_vectors')
                    existing_vectors = manager.cur.fetchone()[0]
                except Exception:
                    existing_vectors = 0
                
                print(f"📊 状況確認:")
                print(f"  総レシピ数: {total_recipes}件")
                print(f"  既存ベクター数: {existing_vectors}件")
                
                if existing_vectors >= total_recipes:
                    print(f"\n✅ 全てのレシピのベクターデータが既に存在します。")
                    print("初期化は不要です。")
                    return
                
                missing_count = total_recipes - existing_vectors
                print(f"\n⚠️  {missing_count}件のレシピのベクターデータが不足しています。")
                
                # Cost estimation
                estimated_tokens = missing_count * 100  # Rough estimate
                estimated_cost_usd = estimated_tokens * 0.00000002  # text-embedding-3-small price
                estimated_cost_jpy = estimated_cost_usd * 150  # Rough conversion
                
                print(f"\n💰 生成コスト見積もり:")
                print(f"  推定トークン数: {estimated_tokens:,}")
                print(f"  推定時間: {missing_count * 0.5:.1f}秒")
                print(f"  推定コスト: ${estimated_cost_usd:.6f} USD")
                print(f"             (約{estimated_cost_jpy:.3f}円)")
                
                confirm = input(f"\n{missing_count}件のベクターデータを生成しますか？ [y/N]: ").strip().lower()
                
                if confirm not in ['y', 'yes', 'はい']:
                    print("❌ ベクター初期化がキャンセルされました。")
                    return
                
                print(f"\n🔄 ベクター生成を開始します...")
                
                # Get recipes that don't have vectors
                manager.cur.execute('''
                    SELECT r.id, r.name, r.description 
                    FROM edo_recipes r
                    LEFT JOIN edo_recipe_vectors rv ON r.id = rv.recipe_id
                    WHERE rv.recipe_id IS NULL
                    ORDER BY r.id
                ''')
                
                missing_recipes = manager.cur.fetchall()
                
                success_count = 0
                error_count = 0
                
                for i, (recipe_id, name, description) in enumerate(missing_recipes, 1):
                    print(f"[{i:2d}/{len(missing_recipes)}] {name[:30]:<30}", end="")
                    
                    # Generate embedding
                    text_to_embed = f"{name} {description[:300]}"  # Limit length
                    embedding = manager.get_text_embedding(text_to_embed)
                    
                    if embedding:
                        try:
                            # Insert vector data
                            manager.cur.execute('''
                                INSERT INTO edo_recipe_vectors 
                                (recipe_id, description_text, ingredients_text, instructions_text, 
                                 combined_text, combined_embedding) 
                                VALUES (%s, %s, '', '', %s, %s::vector)
                            ''', (recipe_id, description, text_to_embed, embedding))
                            
                            manager.conn.commit()
                            print(" ✅")
                            success_count += 1
                        except Exception as e:
                            print(f" ❌ DB Error: {str(e)[:50]}")
                            error_count += 1
                    else:
                        print(" ❌ Embedding failed")
                        error_count += 1
                
                # Final status
                manager.cur.execute('SELECT COUNT(*) FROM edo_recipe_vectors')
                final_count = manager.cur.fetchone()[0]
                
                print(f"\n📋 完了報告:")
                print(f"  成功: {success_count}件")
                print(f"  エラー: {error_count}件")
                print(f"  最終ベクター数: {final_count}/{total_recipes}件")
                
                if final_count == total_recipes:
                    print("\n🎉 全レシピのベクターデータ生成が完了しました！")
                    print("意味検索（ベクトル検索）が全機能で利用可能です。")
                else:
                    print(f"\n⚠️  {total_recipes - final_count}件のベクターデータが未完了です。")
                
        except Exception as e:
            print(f"❌ ベクター初期化エラー: {e}")
            traceback.print_exc()
    
    def _run_data_cleanup(self):
        """全データ消去実行"""
        print("\n" + "=" * 40)
        print("🗑️  全データ消去")
        print("=" * 40)
        
        print("⚠️  この操作により以下のテーブルが完全に削除されます:")
        print("  • edo_recipes (江戸料理レシピ)")
        print("  • edo_recipe_vectors (ベクターデータ)")  
        print("  • recipe_similarities (類似度データ)")
        print("  • vector_search_logs (検索ログ)")
        print("  • recipe_ingredients (レシピ材料)")
        print("  • recipe_instructions (レシピ手順)")
        
        print(f"\n❗ この操作は取り消せません！")
        
        confirm1 = input("本当にすべてのデータを削除しますか？ [y/N]: ").strip().lower()
        if confirm1 not in ['y', 'yes', 'はい']:
            print("❌ データ消去がキャンセルされました。")
            return
        
        confirm2 = input("最終確認: 'DELETE' と入力してください: ").strip()
        if confirm2 != 'DELETE':
            print("❌ 確認文字列が一致しません。データ消去がキャンセルされました。")
            return
        
        try:
            import psycopg2
            conn = psycopg2.connect(**self.db_config.to_connection_params())
            cur = conn.cursor()
            
            print(f"\n🔥 データ削除を実行中...")
            
            # List of tables to drop (in dependency order)
            tables_to_drop = [
                'vector_search_logs',
                'recipe_similarities', 
                'edo_recipe_vectors',
                'recipe_instructions',
                'recipe_ingredients',
                'edo_recipes'
            ]
            
            dropped_count = 0
            for table_name in tables_to_drop:
                try:
                    cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                    print(f"  ✅ {table_name}")
                    dropped_count += 1
                except Exception as e:
                    print(f"  ⚠️  {table_name}: {str(e)[:100]}")
            
            conn.commit()
            conn.close()
            
            print(f"\n🎯 削除完了: {dropped_count}/{len(tables_to_drop)}テーブル")
            print("\n💡 新しいデータを使用するには:")
            print("  1. 江戸料理デモを実行してレシピデータを再作成")
            print("  2. ベクター初期化を実行して埋め込みデータを生成")
            
        except Exception as e:
            print(f"❌ データ削除エラー: {e}")
            traceback.print_exc()


def main():
    """メイン実行関数"""
    try:
        demo = HybridSearchDemo()
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n👋 デモを終了します。")
    except Exception as e:
        print(f"❌ デモ実行エラー: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()