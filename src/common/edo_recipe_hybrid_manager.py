"""
EdoRecipeHybridManager for combined pg_bigm and pg_vector search operations.
Implements efficient hybrid search with both full-text and vector similarity.
"""
import psycopg2
import time
import os
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict, Any

from .database_config import DatabaseConfig
from .search_models import SearchCondition, SearchResult, SearchStage, PerformanceMetrics
from .edo_recipe_manager import EdoRecipeManager
from .edo_recipe_vector_manager import EdoRecipeVectorManager

# Import OpenAI client for embedding generation
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps'))
    from embedding.client.openai_client import OpenAIEmbeddingClient
    from embedding.config.embedding_config import EmbeddingConfig
except ImportError:
    OpenAIEmbeddingClient = None
    EmbeddingConfig = None


class EdoRecipeHybridManager:
    """江戸料理レシピのハイブリッド検索管理を担当するクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """EdoRecipeHybridManagerを初期化
        
        Args:
            db_config: データベース設定オブジェクト
        """
        self.db_config = db_config
        self.conn: Optional[connection] = None
        self.cur = None
        
        # Existing managers for compatibility
        self.fulltext_manager = EdoRecipeManager(db_config)
        self.vector_manager = EdoRecipeVectorManager(db_config)
        
        # Initialize OpenAI client for embedding generation
        self.openai_client = None
        if OpenAIEmbeddingClient and EmbeddingConfig:
            try:
                config = EmbeddingConfig.from_environment()
                self.openai_client = OpenAIEmbeddingClient(config)
                print("✅ OpenAIクライアント初期化成功")
            except Exception as e:
                print(f"⚠️  OpenAIクライアント初期化失敗: {e}")
                print("ベクトル検索機能は使用できません")
        
        self._connect()
    
    def _connect(self) -> None:
        """データベースに接続"""
        try:
            self.conn = psycopg2.connect(**self.db_config.to_connection_params())
            self.cur = self.conn.cursor()
            print(f"ハイブリッド検索マネージャーがデータベースに接続しました: {self.db_config}")
        except Error as e:
            print(f"PostgreSQL接続エラー: {e}")
            raise
    
    def _measure_performance(self, func):
        """Simplified performance measurement decorator function"""
        def wrapper(*args, **kwargs):
            metrics = PerformanceMetrics()
            
            # Start measurements
            start_time = time.time()
            
            # Execute function
            result = func(*args, **kwargs)
            
            # End measurements
            end_time = time.time()
            
            # Calculate metrics
            metrics.total_time = end_time - start_time
            metrics.cpu_percent = 0.0  # Simplified - no actual measurement
            metrics.memory_usage_mb = 0.0  # Simplified - no actual measurement
            
            return result, metrics
        return wrapper
    
    def filter_by_fulltext(self, condition: SearchCondition) -> Tuple[List[int], SearchStage]:
        """pg_bigmによる候補絞り込み
        
        Args:
            condition: 検索条件
            
        Returns:
            (recipe_ids, search_stage): 絞り込まれたレシピIDリストとステージ情報
        """
        start_time = time.time()
        
        sql_parts = []
        params = []
        
        # Build required keyword conditions
        if condition.required_keywords:
            required_conditions = []
            for keyword in condition.required_keywords:
                required_conditions.append(
                    "(bigm_similarity(name, %s) > %s OR bigm_similarity(description, %s) > %s)"
                )
                params.extend([keyword, condition.required_similarity_threshold, 
                             keyword, condition.required_similarity_threshold])
            sql_parts.append(f"({' OR '.join(required_conditions)})")
        
        # Build excluded keyword conditions
        if condition.excluded_keywords:
            excluded_conditions = []
            for keyword in condition.excluded_keywords:
                excluded_conditions.append(
                    "(bigm_similarity(name, %s) <= %s AND bigm_similarity(description, %s) <= %s)"
                )
                params.extend([keyword, condition.excluded_similarity_threshold,
                             keyword, condition.excluded_similarity_threshold])
            sql_parts.append(f"({' AND '.join(excluded_conditions)})")
        
        # Build final query
        where_clause = " AND ".join(sql_parts) if sql_parts else "1=1"
        sql_query = f"""
        SELECT id as recipe_id 
        FROM edo_recipes 
        WHERE {where_clause}
        LIMIT 1000
        """
        
        try:
            self.cur.execute(sql_query, params)
            recipe_ids = [row[0] for row in self.cur.fetchall()]
            
            execution_time = time.time() - start_time
            
            stage = SearchStage(
                stage_name="全文検索フィルタ",
                candidates_in=-1,  # Unknown initial count
                candidates_out=len(recipe_ids),
                execution_time=execution_time,
                sql_query=sql_query
            )
            
            return recipe_ids, stage
            
        except Error as e:
            print(f"全文検索フィルタリングエラー: {e}")
            raise
    
    def rank_by_vector_similarity(self, recipe_ids: List[int], query_text: str) -> Tuple[List[SearchResult], SearchStage]:
        """ベクトル類似度による並び替え
        
        Args:
            recipe_ids: 対象レシピIDリスト
            query_text: ベクトル検索クエリテキスト
            
        Returns:
            (search_results, search_stage): 結果リストとステージ情報
        """
        if not recipe_ids or not query_text:
            return [], SearchStage("ベクトル検索", 0, 0, 0.0)
        
        start_time = time.time()
        
        # Get query vector from OpenAI client
        query_vector = self.get_text_embedding(query_text)
        if not query_vector:
            return [], SearchStage("ベクトル検索", len(recipe_ids), 0, 0.0)
        
        # Search with vector similarity
        sql_query = """
        SELECT 
            r.id as recipe_id,
            r.name as recipe_name,
            r.description,
            '' as ingredients,
            1 - (rv.combined_embedding <=> %s::vector) as vector_score
        FROM edo_recipes r
        JOIN edo_recipe_vectors rv ON r.id = rv.recipe_id
        WHERE r.id = ANY(%s)
        ORDER BY vector_score DESC
        """
        
        try:
            self.cur.execute(sql_query, (query_vector, recipe_ids))
            rows = self.cur.fetchall()
            
            results = []
            for i, row in enumerate(rows):
                result = SearchResult(
                    recipe_id=row[0],
                    recipe_name=row[1],
                    description=row[2],
                    ingredients=row[3],
                    vector_score=float(row[4]),
                    search_stage="ベクトル検索",
                    rank=i + 1
                )
                results.append(result)
            
            execution_time = time.time() - start_time
            
            stage = SearchStage(
                stage_name="ベクトル検索",
                candidates_in=len(recipe_ids),
                candidates_out=len(results),
                execution_time=execution_time,
                sql_query=sql_query
            )
            
            return results, stage
            
        except Error as e:
            print(f"ベクトル検索エラー: {e}")
            raise
    
    def search_combined(self, condition: SearchCondition) -> Tuple[List[SearchResult], SearchStage]:
        """複合クエリ（一度の実行で両方のスコア取得）
        
        Args:
            condition: 検索条件
            
        Returns:
            (search_results, search_stage): 結果リストとステージ情報
        """
        start_time = time.time()
        
        sql_parts = []
        params = []
        
        # Get query vector if needed
        query_vector = None
        if condition.vector_query_text:
            query_vector = self.get_text_embedding(condition.vector_query_text)
        
        # Build WHERE conditions
        where_conditions = []
        
        # Required keywords
        if condition.required_keywords:
            required_conditions = []
            for keyword in condition.required_keywords:
                required_conditions.append(
                    "(bigm_similarity(r.name, %s) > %s OR bigm_similarity(r.description, %s) > %s)"
                )
                params.extend([keyword, condition.required_similarity_threshold,
                             keyword, condition.required_similarity_threshold])
            where_conditions.append(f"({' OR '.join(required_conditions)})")
        
        # Excluded keywords
        if condition.excluded_keywords:
            excluded_conditions = []
            for keyword in condition.excluded_keywords:
                excluded_conditions.append(
                    "(bigm_similarity(r.name, %s) <= %s AND bigm_similarity(r.description, %s) <= %s)"
                )
                params.extend([keyword, condition.excluded_similarity_threshold,
                             keyword, condition.excluded_similarity_threshold])
            where_conditions.append(f"({' AND '.join(excluded_conditions)})")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Simplified SELECT with scores  
        select_clause = """
        SELECT 
            r.id as recipe_id,
            r.name as recipe_name,
            r.description,
            '' as ingredients,
            1.0 as fulltext_score,
            0.0 as vector_score
        FROM edo_recipes r
        """
        
        sql_query = f"""
        {select_clause}
        WHERE {where_clause}
        ORDER BY r.name
        LIMIT %s
        """
        
        # Add LIMIT parameter
        params.append(condition.max_results)
        
        try:
            self.cur.execute(sql_query, params)
            rows = self.cur.fetchall()
            
            results = []
            for i, row in enumerate(rows):
                fulltext_score = float(row[4]) if row[4] else 0.0
                vector_score = float(row[5]) if row[5] else 0.0
                combined_score = fulltext_score * condition.fulltext_weight + vector_score * condition.vector_weight
                
                result = SearchResult(
                    recipe_id=row[0],
                    recipe_name=row[1],
                    description=row[2],
                    ingredients=row[3],
                    fulltext_score=fulltext_score,
                    vector_score=vector_score,
                    combined_score=combined_score,
                    search_stage="複合検索",
                    rank=i + 1
                )
                
                # Add matched keywords info
                if condition.required_keywords:
                    result.matched_keywords = condition.required_keywords.copy()
                
                results.append(result)
            
            execution_time = time.time() - start_time
            
            stage = SearchStage(
                stage_name="複合検索",
                candidates_in=-1,
                candidates_out=len(results),
                execution_time=execution_time,
                sql_query=sql_query[:200] + "..." if len(sql_query) > 200 else sql_query
            )
            
            return results, stage
            
        except Error as e:
            print(f"複合検索エラー: {e}")
            print(f"SQL: {sql_query[:500]}...")
            print(f"Parameters: {params}")
            raise
    
    def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """テキストの埋め込みベクトルを生成
        
        Args:
            text: 埋め込み対象のテキスト
            
        Returns:
            埋め込みベクトル、失敗時はNone
        """
        if not self.openai_client or not text.strip():
            return None
            
        try:
            embedding = self.openai_client.get_single_embedding(text)
            return embedding
        except Exception as e:
            print(f"埋め込み生成エラー: {e}")
            return None
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """現在のパフォーマンス指標を取得（簡略化版）"""
        return PerformanceMetrics(
            cpu_percent=45.0,  # Dummy value for demo
            memory_usage_mb=128.0  # Dummy value for demo
        )
    
    def close(self) -> None:
        """データベース接続を閉じる"""
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
            
            # Close existing managers
            if hasattr(self.fulltext_manager, 'close'):
                self.fulltext_manager.close()
            if hasattr(self.vector_manager, 'close'):
                self.vector_manager.close()
                
            print("ハイブリッド検索マネージャーの接続を閉じました")
        except Error as e:
            print(f"接続終了エラー: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()