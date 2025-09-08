"""
HybridRecipeSearchService for high-level search operations.
Implements business logic for hybrid search combining pg_bigm and pg_vector.
"""
import time
import asyncio
from typing import List, Dict, Optional, Tuple
import statistics

from .database_config import DatabaseConfig
from .edo_recipe_hybrid_manager import EdoRecipeHybridManager
from .search_models import (
    SearchCondition, SearchResult, SearchResponse, SearchStage, 
    PerformanceMetrics, PerformanceComparison, SearchMode, QueryAnalysis
)


class ScoreCalculator:
    """スコア計算とランキング処理を担当するクラス"""
    
    @staticmethod
    def calculate_final_scores(results: List[SearchResult], condition: SearchCondition) -> List[SearchResult]:
        """最終スコア計算とランキング
        
        Args:
            results: 検索結果リスト
            condition: 検索条件
            
        Returns:
            スコア計算済みでソートされた結果リスト
        """
        if not results:
            return results
        
        # Normalize scores to 0-1 range
        normalized_results = ScoreCalculator.normalize_scores(results)
        
        # Calculate combined scores
        for result in normalized_results:
            result.combined_score = (
                result.fulltext_score * condition.fulltext_weight +
                result.vector_score * condition.vector_weight
            )
        
        # Sort by combined score and update rankings
        sorted_results = sorted(normalized_results, key=lambda r: r.combined_score, reverse=True)
        
        for i, result in enumerate(sorted_results):
            result.rank = i + 1
        
        return sorted_results[:condition.max_results]
    
    @staticmethod
    def normalize_scores(results: List[SearchResult]) -> List[SearchResult]:
        """スコアを0-1範囲に正規化
        
        Args:
            results: 正規化前の結果リスト
            
        Returns:
            正規化済みの結果リスト
        """
        if not results:
            return results
        
        # Extract scores
        fulltext_scores = [r.fulltext_score for r in results if r.fulltext_score > 0]
        vector_scores = [r.vector_score for r in results if r.vector_score > 0]
        
        # Calculate normalization parameters
        fulltext_min = min(fulltext_scores) if fulltext_scores else 0
        fulltext_max = max(fulltext_scores) if fulltext_scores else 1
        vector_min = min(vector_scores) if vector_scores else 0
        vector_max = max(vector_scores) if vector_scores else 1
        
        # Normalize scores
        for result in results:
            # Normalize fulltext score
            if fulltext_max > fulltext_min and result.fulltext_score > 0:
                result.fulltext_score = (result.fulltext_score - fulltext_min) / (fulltext_max - fulltext_min)
            
            # Normalize vector score
            if vector_max > vector_min and result.vector_score > 0:
                result.vector_score = (result.vector_score - vector_min) / (vector_max - vector_min)
        
        return results
    
    @staticmethod
    def merge_and_score(fulltext_results: List[SearchResult], 
                       vector_results: List[SearchResult], 
                       condition: SearchCondition) -> List[SearchResult]:
        """並列検索結果のマージとスコア計算
        
        Args:
            fulltext_results: 全文検索結果
            vector_results: ベクトル検索結果
            condition: 検索条件
            
        Returns:
            マージされた結果リスト
        """
        # Create recipe_id -> result mapping
        fulltext_map = {r.recipe_id: r for r in fulltext_results}
        vector_map = {r.recipe_id: r for r in vector_results}
        
        # Get all unique recipe IDs
        all_recipe_ids = set(fulltext_map.keys()) | set(vector_map.keys())
        
        # Merge results
        merged_results = []
        for recipe_id in all_recipe_ids:
            fulltext_result = fulltext_map.get(recipe_id)
            vector_result = vector_map.get(recipe_id)
            
            # Create merged result
            if fulltext_result and vector_result:
                # Both results exist - merge
                merged_result = SearchResult(
                    recipe_id=recipe_id,
                    recipe_name=fulltext_result.recipe_name or vector_result.recipe_name,
                    description=fulltext_result.description or vector_result.description,
                    ingredients=fulltext_result.ingredients or vector_result.ingredients,
                    fulltext_score=fulltext_result.fulltext_score,
                    vector_score=vector_result.vector_score,
                    matched_keywords=fulltext_result.matched_keywords,
                    search_stage="並列マージ"
                )
            elif fulltext_result:
                # Only fulltext result
                merged_result = fulltext_result
                merged_result.search_stage = "全文検索のみ"
            else:
                # Only vector result
                merged_result = vector_result
                merged_result.search_stage = "ベクトル検索のみ"
            
            merged_results.append(merged_result)
        
        return ScoreCalculator.calculate_final_scores(merged_results, condition)


class HybridRecipeSearchService:
    """ハイブリッド検索の高レベル操作を提供するサービスクラス"""
    
    def __init__(self, db_config: DatabaseConfig):
        """HybridRecipeSearchServiceを初期化
        
        Args:
            db_config: データベース設定
        """
        self.db_config = db_config
        self.score_calculator = ScoreCalculator()
    
    def search_recipes(self, condition: SearchCondition) -> SearchResponse:
        """メイン検索API - 全ての検索モードに対応
        
        Args:
            condition: 検索条件
            
        Returns:
            検索レスポンス
        """
        start_time = time.time()
        
        with EdoRecipeHybridManager(self.db_config) as manager:
            if condition.search_mode == SearchMode.CASCADE:
                return self._cascade_search(manager, condition, start_time)
            elif condition.search_mode == SearchMode.PARALLEL:
                return self._parallel_search(manager, condition, start_time)
            elif condition.search_mode == SearchMode.FULLTEXT_ONLY:
                return self._fulltext_only_search(manager, condition, start_time)
            elif condition.search_mode == SearchMode.VECTOR_ONLY:
                return self._vector_only_search(manager, condition, start_time)
            else:
                raise ValueError(f"未対応の検索モード: {condition.search_mode}")
    
    def _cascade_search(self, manager: EdoRecipeHybridManager, 
                       condition: SearchCondition, start_time: float) -> SearchResponse:
        """段階的検索実装
        
        Args:
            manager: ハイブリッドマネージャー
            condition: 検索条件
            start_time: 開始時刻
            
        Returns:
            検索レスポンス
        """
        stages = []
        
        # Stage 1: pg_bigmで候補絞り込み
        candidate_ids, stage1 = manager.filter_by_fulltext(condition)
        stages.append(stage1)
        
        if not candidate_ids:
            # No candidates found
            return SearchResponse(
                results=[],
                total_matches=0,
                execution_time=time.time() - start_time,
                search_stages=stages,
                performance_metrics=manager.get_performance_metrics(),
                search_condition=condition
            )
        
        # Stage 2: ベクトル類似度で並び替え
        if condition.vector_query_text:
            results, stage2 = manager.rank_by_vector_similarity(candidate_ids, condition.vector_query_text)
            stages.append(stage2)
        else:
            # Vector search not requested, get basic info
            results = self._get_basic_recipe_info(manager, candidate_ids)
            stage2 = SearchStage("基本情報取得", len(candidate_ids), len(results), 0.01)
            stages.append(stage2)
        
        # Stage 3: スコア計算と最終ランキング
        final_results = self.score_calculator.calculate_final_scores(results, condition)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=final_results,
            total_matches=len(candidate_ids),
            execution_time=execution_time,
            search_stages=stages,
            performance_metrics=manager.get_performance_metrics(),
            search_condition=condition
        )
    
    def _parallel_search(self, manager: EdoRecipeHybridManager, 
                        condition: SearchCondition, start_time: float) -> SearchResponse:
        """並列検索実装
        
        Args:
            manager: ハイブリッドマネージャー
            condition: 検索条件
            start_time: 開始時刻
            
        Returns:
            検索レスポンス
        """
        # Use combined search for efficiency
        results, stage = manager.search_combined(condition)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_matches=len(results),
            execution_time=execution_time,
            search_stages=[stage],
            performance_metrics=manager.get_performance_metrics(),
            search_condition=condition
        )
    
    def _fulltext_only_search(self, manager: EdoRecipeHybridManager, 
                             condition: SearchCondition, start_time: float) -> SearchResponse:
        """全文検索のみの実装
        
        Args:
            manager: ハイブリッドマネージャー
            condition: 検索条件
            start_time: 開始時刻
            
        Returns:
            検索レスポンス
        """
        # Modify condition to disable vector search
        modified_condition = SearchCondition(
            required_keywords=condition.required_keywords,
            excluded_keywords=condition.excluded_keywords,
            required_similarity_threshold=condition.required_similarity_threshold,
            excluded_similarity_threshold=condition.excluded_similarity_threshold,
            vector_query_text="",  # Disable vector search
            fulltext_weight=1.0,
            vector_weight=0.0,
            max_results=condition.max_results,
            search_mode=SearchMode.FULLTEXT_ONLY
        )
        
        results, stage = manager.search_combined(modified_condition)
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=results,
            total_matches=len(results),
            execution_time=execution_time,
            search_stages=[stage],
            performance_metrics=manager.get_performance_metrics(),
            search_condition=modified_condition
        )
    
    def _vector_only_search(self, manager: EdoRecipeHybridManager, 
                           condition: SearchCondition, start_time: float) -> SearchResponse:
        """ベクトル検索のみの実装
        
        Args:
            manager: ハイブリッドマネージャー
            condition: 検索条件
            start_time: 開始時刻
            
        Returns:
            検索レスポンス
        """
        if not condition.vector_query_text:
            return SearchResponse(
                results=[],
                total_matches=0,
                execution_time=time.time() - start_time,
                search_stages=[],
                performance_metrics=manager.get_performance_metrics(),
                search_condition=condition
            )
        
        # Get all recipe IDs for vector search
        all_ids, _ = manager.filter_by_fulltext(SearchCondition())  # No filters
        results, stage = manager.rank_by_vector_similarity(all_ids, condition.vector_query_text)
        
        # Limit results
        limited_results = results[:condition.max_results]
        
        execution_time = time.time() - start_time
        
        return SearchResponse(
            results=limited_results,
            total_matches=len(results),
            execution_time=execution_time,
            search_stages=[stage],
            performance_metrics=manager.get_performance_metrics(),
            search_condition=condition
        )
    
    def _get_basic_recipe_info(self, manager: EdoRecipeHybridManager, recipe_ids: List[int]) -> List[SearchResult]:
        """基本的なレシピ情報を取得
        
        Args:
            manager: ハイブリッドマネージャー
            recipe_ids: レシピIDリスト
            
        Returns:
            基本情報付きの検索結果リスト
        """
        if not recipe_ids:
            return []
        
        sql_query = """
        SELECT recipe_id, recipe_name, description, ingredients
        FROM edo_recipes
        WHERE recipe_id = ANY(%s)
        ORDER BY recipe_id
        """
        
        try:
            manager.cur.execute(sql_query, (recipe_ids,))
            rows = manager.cur.fetchall()
            
            results = []
            for i, row in enumerate(rows):
                result = SearchResult(
                    recipe_id=row[0],
                    recipe_name=row[1],
                    description=row[2],
                    ingredients=row[3],
                    fulltext_score=1.0,  # Default score
                    vector_score=0.0,
                    search_stage="基本情報",
                    rank=i + 1
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"基本情報取得エラー: {e}")
            return []
    
    def compare_search_modes(self, condition: SearchCondition) -> PerformanceComparison:
        """異なる検索モードの性能比較
        
        Args:
            condition: 基準となる検索条件
            
        Returns:
            性能比較結果
        """
        # Test each search mode
        cascade_response = self.search_recipes(
            SearchCondition(**{**condition.__dict__, 'search_mode': SearchMode.CASCADE})
        )
        
        parallel_response = self.search_recipes(
            SearchCondition(**{**condition.__dict__, 'search_mode': SearchMode.PARALLEL})
        )
        
        fulltext_response = self.search_recipes(
            SearchCondition(**{**condition.__dict__, 'search_mode': SearchMode.FULLTEXT_ONLY})
        )
        
        vector_response = self.search_recipes(
            SearchCondition(**{**condition.__dict__, 'search_mode': SearchMode.VECTOR_ONLY})
        )
        
        # Determine recommendation
        times = {
            SearchMode.CASCADE: cascade_response.execution_time,
            SearchMode.PARALLEL: parallel_response.execution_time,
            SearchMode.FULLTEXT_ONLY: fulltext_response.execution_time,
            SearchMode.VECTOR_ONLY: vector_response.execution_time
        }
        
        # Simple recommendation logic: fastest with reasonable result count
        result_counts = {
            SearchMode.CASCADE: len(cascade_response.results),
            SearchMode.PARALLEL: len(parallel_response.results),
            SearchMode.FULLTEXT_ONLY: len(fulltext_response.results),
            SearchMode.VECTOR_ONLY: len(vector_response.results)
        }
        
        # Prefer modes with more results, but consider speed
        if result_counts[SearchMode.PARALLEL] >= result_counts[SearchMode.CASCADE] * 0.8:
            recommended_mode = SearchMode.PARALLEL
            reason = "高精度を維持しつつ高速な実行が可能"
        elif times[SearchMode.CASCADE] < times[SearchMode.PARALLEL] * 1.5:
            recommended_mode = SearchMode.CASCADE
            reason = "バランスの取れた速度と精度"
        else:
            recommended_mode = min(times.keys(), key=lambda k: times[k])
            reason = "最も高速な実行"
        
        return PerformanceComparison(
            cascade_metrics=cascade_response.performance_metrics,
            parallel_metrics=parallel_response.performance_metrics,
            fulltext_metrics=fulltext_response.performance_metrics,
            vector_metrics=vector_response.performance_metrics,
            recommended_mode=recommended_mode,
            recommendation_reason=reason
        )
    
    def suggest_keywords(self, partial_text: str) -> List[str]:
        """キーワード候補提案
        
        Args:
            partial_text: 部分テキスト
            
        Returns:
            キーワード候補リスト
        """
        # Simple keyword suggestion based on common ingredients/terms
        common_keywords = [
            "だし", "醤油", "味噌", "砂糖", "塩", "酢", "油",
            "魚", "肉", "野菜", "豆腐", "米", "麺",
            "煮る", "焼く", "蒸す", "揚げる", "炒める",
            "春", "夏", "秋", "冬", "季節"
        ]
        
        if not partial_text:
            return common_keywords[:10]
        
        # Filter keywords that contain the partial text
        matching_keywords = [kw for kw in common_keywords if partial_text in kw]
        
        return matching_keywords[:10] if matching_keywords else common_keywords[:10]
    
    def analyze_query(self, query_text: str) -> QueryAnalysis:
        """クエリ解析 - 自動的な条件抽出
        
        Args:
            query_text: 解析対象のクエリテキスト
            
        Returns:
            クエリ解析結果
        """
        # Simple keyword extraction logic
        positive_indicators = ["含む", "使う", "入っている", "ある"]
        negative_indicators = ["含まない", "使わない", "入っていない", "ない", "除く"]
        
        suggested_required = []
        suggested_excluded = []
        
        # Basic keyword extraction (this could be enhanced with NLP)
        ingredient_keywords = ["だし", "魚", "肉", "野菜", "豆腐", "油", "砂糖"]
        cooking_keywords = ["煮る", "焼く", "蒸す", "揚げる"]
        
        for keyword in ingredient_keywords + cooking_keywords:
            if keyword in query_text:
                # Check context
                context_negative = any(neg in query_text for neg in negative_indicators)
                if context_negative:
                    suggested_excluded.append(keyword)
                else:
                    suggested_required.append(keyword)
        
        # Simple complexity assessment
        complexity = "simple"
        if len(suggested_required) + len(suggested_excluded) > 3:
            complexity = "complex"
        elif len(suggested_required) + len(suggested_excluded) > 1:
            complexity = "moderate"
        
        confidence = min(0.8, len(suggested_required + suggested_excluded) * 0.2)
        
        return QueryAnalysis(
            suggested_required=suggested_required,
            suggested_excluded=suggested_excluded,
            confidence_score=confidence,
            query_complexity=complexity
        )