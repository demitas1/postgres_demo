import time
import math
import psycopg2
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict, Any

from .database_config import DatabaseConfig


class RecipeVectorSearchService:
    """レシピベクター検索サービスクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """RecipeVectorSearchServiceを初期化
        
        Args:
            db_config: データベース設定オブジェクト
        """
        self.db_config = db_config
        self.conn: Optional[connection] = None
        self.cur = None
        self._connect()
    
    def _connect(self) -> None:
        """データベースに接続"""
        try:
            self.conn = psycopg2.connect(**self.db_config.to_connection_params())
            self.cur = self.conn.cursor()
            print(f"Connected to database: {self.db_config}")
        except Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def semantic_search_recipes(self, query_embedding: List[float], search_type: str = 'combined', 
                              limit: int = 5, similarity_threshold: float = 0.0) -> List[Tuple]:
        """意味的類似性によるレシピ検索
        
        Args:
            query_embedding: クエリの埋め込みベクター
            search_type: 検索対象 ('description', 'ingredients', 'instructions', 'combined')
            limit: 検索結果数の上限
            similarity_threshold: 類似度の最小閾値
            
        Returns:
            (recipe_id, recipe_name, similarity_score, matched_text, description)のタプルリスト
        """
        start_time = time.time()
        
        try:
            # 検索タイプに応じてカラムを選択
            embedding_column = f"{search_type}_embedding"
            text_column = f"{search_type}_text"
            
            # コサイン類似度検索クエリ
            search_query = f"""
            SELECT 
                rv.recipe_id,
                r.name as recipe_name,
                1 - (rv.{embedding_column} <=> %s::vector) as similarity_score,
                rv.{text_column} as matched_text,
                r.description
            FROM edo_recipe_vectors rv
            JOIN edo_recipes r ON rv.recipe_id = r.id
            WHERE rv.{embedding_column} IS NOT NULL
            AND (1 - (rv.{embedding_column} <=> %s::vector)) >= %s
            ORDER BY rv.{embedding_column} <=> %s::vector
            LIMIT %s;
            """
            
            # クエリ実行
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            self.cur.execute(search_query, (embedding_str, embedding_str, similarity_threshold, embedding_str, limit))
            
            results = self.cur.fetchall()
            execution_time = (time.time() - start_time) * 1000  # ms
            
            # 検索ログを記録
            self._log_search_query("", query_embedding, search_type, limit, similarity_threshold, 
                                 len(results), execution_time)
            
            return results
            
        except Error as e:
            print(f"Error in semantic search: {e}")
            return []
    
    def find_similar_recipes(self, recipe_id: int, search_type: str = 'combined', 
                           limit: int = 5, exclude_self: bool = True) -> List[Tuple]:
        """指定レシピに類似するレシピを検索
        
        Args:
            recipe_id: 基準となるレシピID
            search_type: 検索対象タイプ
            limit: 検索結果数の上限
            exclude_self: 自分自身を結果から除外するかどうか
            
        Returns:
            (recipe_id, recipe_name, similarity_score, matched_text)のタプルリスト
        """
        try:
            # 基準レシピの埋め込みを取得
            embedding_column = f"{search_type}_embedding"
            text_column = f"{search_type}_text"
            
            get_embedding_query = f"""
            SELECT {embedding_column}
            FROM edo_recipe_vectors
            WHERE recipe_id = %s AND {embedding_column} IS NOT NULL;
            """
            
            self.cur.execute(get_embedding_query, (recipe_id,))
            result = self.cur.fetchone()
            
            if not result:
                print(f"レシピID {recipe_id} の埋め込みが見つかりません")
                return []
            
            base_embedding = result[0]
            
            # 類似レシピ検索
            exclusion_clause = "AND rv.recipe_id != %s" if exclude_self else ""
            
            similar_query = f"""
            SELECT 
                rv.recipe_id,
                r.name as recipe_name,
                1 - (rv.{embedding_column} <=> %s::vector) as similarity_score,
                rv.{text_column} as matched_text
            FROM edo_recipe_vectors rv
            JOIN edo_recipes r ON rv.recipe_id = r.id
            WHERE rv.{embedding_column} IS NOT NULL
            {exclusion_clause}
            ORDER BY rv.{embedding_column} <=> %s::vector
            LIMIT %s;
            """
            
            params = [base_embedding, base_embedding, limit]
            if exclude_self:
                params.insert(-2, recipe_id)  # 除外するrecipe_idを追加
            
            self.cur.execute(similar_query, params)
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error finding similar recipes: {e}")
            return []
    
    def hybrid_search(self, query_text: str, query_embedding: List[float], 
                     keyword_weight: float = 0.3, vector_weight: float = 0.7,
                     limit: int = 5) -> List[Tuple]:
        """キーワード検索とベクター検索を組み合わせたハイブリッド検索
        
        Args:
            query_text: 検索キーワード
            query_embedding: クエリの埋め込みベクター
            keyword_weight: キーワード検索の重み
            vector_weight: ベクター検索の重み
            limit: 検索結果数の上限
            
        Returns:
            (recipe_id, recipe_name, hybrid_score, keyword_score, vector_score)のタプルリスト
        """
        try:
            # ハイブリッド検索クエリ（pg_bigmのキーワード検索 + ベクター検索）
            hybrid_query = """
            WITH keyword_scores AS (
                SELECT 
                    rv.recipe_id,
                    r.name,
                    GREATEST(
                        COALESCE(bigm_similarity(r.name, %s), 0),
                        COALESCE(bigm_similarity(r.description, %s), 0),
                        COALESCE(bigm_similarity(rv.combined_text, %s), 0)
                    ) as keyword_score
                FROM edo_recipe_vectors rv
                JOIN edo_recipes r ON rv.recipe_id = r.id
                WHERE rv.combined_embedding IS NOT NULL
            ),
            vector_scores AS (
                SELECT 
                    rv.recipe_id,
                    r.name,
                    1 - (rv.combined_embedding <=> %s::vector) as vector_score
                FROM edo_recipe_vectors rv
                JOIN edo_recipes r ON rv.recipe_id = r.id
                WHERE rv.combined_embedding IS NOT NULL
            )
            SELECT 
                ks.recipe_id,
                ks.name as recipe_name,
                (%s * ks.keyword_score + %s * vs.vector_score) as hybrid_score,
                ks.keyword_score,
                vs.vector_score
            FROM keyword_scores ks
            JOIN vector_scores vs ON ks.recipe_id = vs.recipe_id
            WHERE ks.keyword_score > 0.0 OR vs.vector_score > 0.3
            ORDER BY hybrid_score DESC
            LIMIT %s;
            """
            
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            self.cur.execute(hybrid_query, (
                query_text, query_text, query_text,  # キーワード検索用
                embedding_str,  # ベクター検索用
                keyword_weight, vector_weight,  # 重み
                limit
            ))
            
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error in hybrid search: {e}")
            return []
    
    def get_recipe_details_with_vectors(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """レシピの詳細情報をベクターデータと共に取得
        
        Args:
            recipe_id: レシピID
            
        Returns:
            レシピ詳細辞書、失敗時はNone
        """
        try:
            detail_query = """
            SELECT 
                r.id, r.name, r.url, r.description, r.tips,
                rv.description_text, rv.ingredients_text, rv.instructions_text, rv.combined_text,
                rv.embedding_model, rv.created_at as vector_created_at
            FROM edo_recipes r
            LEFT JOIN edo_recipe_vectors rv ON r.id = rv.recipe_id
            WHERE r.id = %s;
            """
            
            self.cur.execute(detail_query, (recipe_id,))
            result = self.cur.fetchone()
            
            if not result:
                return None
            
            # 材料と手順を取得
            ingredients_query = """
            SELECT ingredient FROM recipe_ingredients 
            WHERE recipe_id = %s ORDER BY sort_order;
            """
            
            instructions_query = """
            SELECT instruction FROM recipe_instructions 
            WHERE recipe_id = %s AND instruction_type = 'modern'
            ORDER BY step_number;
            """
            
            self.cur.execute(ingredients_query, (recipe_id,))
            ingredients = [row[0] for row in self.cur.fetchall()]
            
            self.cur.execute(instructions_query, (recipe_id,))
            instructions = [row[0] for row in self.cur.fetchall()]
            
            return {
                "id": result[0],
                "name": result[1],
                "url": result[2],
                "description": result[3],
                "tips": result[4],
                "ingredients": ingredients,
                "instructions": instructions,
                "vector_data": {
                    "description_text": result[5],
                    "ingredients_text": result[6],
                    "instructions_text": result[7],
                    "combined_text": result[8],
                    "embedding_model": result[9],
                    "vector_created_at": result[10]
                } if result[5] else None
            }
            
        except Error as e:
            print(f"Error getting recipe details: {e}")
            return None
    
    def calculate_recipe_similarities(self, limit_pairs: int = 100) -> bool:
        """レシピ間の類似性を事前計算してテーブルに保存
        
        Args:
            limit_pairs: 計算するペア数の上限
            
        Returns:
            計算成功時はTrue、失敗時はFalse
        """
        try:
            print("🔄 レシピ間類似性の計算を開始...")
            
            # 全レシピの埋め込みを取得
            get_all_embeddings_query = """
            SELECT recipe_id, description_embedding, ingredients_embedding, 
                   instructions_embedding, combined_embedding
            FROM edo_recipe_vectors
            WHERE combined_embedding IS NOT NULL
            ORDER BY recipe_id;
            """
            
            self.cur.execute(get_all_embeddings_query)
            all_embeddings = self.cur.fetchall()
            
            if len(all_embeddings) < 2:
                print("⚠️  計算に必要な埋め込みデータが不足しています")
                return False
            
            # 類似性計算とDB挿入
            similarity_pairs = []
            pair_count = 0
            
            for i, recipe1 in enumerate(all_embeddings):
                for j, recipe2 in enumerate(all_embeddings[i+1:], i+1):
                    if pair_count >= limit_pairs:
                        break
                    
                    # 各タイプの類似度計算
                    desc_sim = self._cosine_similarity(recipe1[1], recipe2[1])
                    ing_sim = self._cosine_similarity(recipe1[2], recipe2[2])
                    inst_sim = self._cosine_similarity(recipe1[3], recipe2[3])
                    comb_sim = self._cosine_similarity(recipe1[4], recipe2[4])
                    
                    similarity_pairs.append((
                        recipe1[0], recipe2[0],  # source_recipe_id, target_recipe_id
                        desc_sim, ing_sim, inst_sim, comb_sim
                    ))
                    
                    pair_count += 1
                
                if pair_count >= limit_pairs:
                    break
            
            # バッチでDB挿入
            if similarity_pairs:
                insert_query = """
                INSERT INTO recipe_similarities 
                (source_recipe_id, target_recipe_id, description_similarity, 
                 ingredients_similarity, instructions_similarity, combined_similarity)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_recipe_id, target_recipe_id) 
                DO UPDATE SET
                    description_similarity = EXCLUDED.description_similarity,
                    ingredients_similarity = EXCLUDED.ingredients_similarity,
                    instructions_similarity = EXCLUDED.instructions_similarity,
                    combined_similarity = EXCLUDED.combined_similarity;
                """
                
                self.cur.executemany(insert_query, similarity_pairs)
                self.conn.commit()
                
                print(f"✓ {len(similarity_pairs)}ペアの類似性を計算・保存しました")
                return True
            else:
                print("⚠️  計算可能なペアがありません")
                return False
                
        except Error as e:
            print(f"Error calculating similarities: {e}")
            self.conn.rollback()
            return False
    
    def get_search_logs(self, limit: int = 50) -> List[Tuple]:
        """検索ログを取得
        
        Args:
            limit: 取得するログ数の上限
            
        Returns:
            検索ログのタプルリスト
        """
        try:
            log_query = """
            SELECT query_text, search_type, result_count, max_similarity, 
                   avg_similarity, execution_time_ms, created_at
            FROM vector_search_logs
            ORDER BY created_at DESC
            LIMIT %s;
            """
            
            self.cur.execute(log_query, (limit,))
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error getting search logs: {e}")
            return []
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """コサイン類似度を計算
        
        Args:
            vec1: ベクター1（List[float]またはPostgreSQL vector型文字列）
            vec2: ベクター2（List[float]またはPostgreSQL vector型文字列）
            
        Returns:
            コサイン類似度 (0.0-1.0)
        """
        # PostgreSQL vector型から Python listに変換
        v1 = self._parse_vector(vec1)
        v2 = self._parse_vector(vec2)
        
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _parse_vector(self, vector_data) -> List[float]:
        """PostgreSQL vector型データをPython listに変換
        
        Args:
            vector_data: PostgreSQL vector型データ（文字列またはリスト）
            
        Returns:
            float値のリスト
        """
        if vector_data is None:
            return []
        
        # 既にリストの場合はそのまま返す
        if isinstance(vector_data, list):
            return [float(x) for x in vector_data]
        
        # 文字列の場合はパース
        if isinstance(vector_data, str):
            # PostgreSQL vector型は "[1.0,2.0,3.0]" 形式
            vector_str = vector_data.strip()
            if vector_str.startswith('[') and vector_str.endswith(']'):
                vector_str = vector_str[1:-1]  # 角括弧を除去
            
            try:
                return [float(x.strip()) for x in vector_str.split(',') if x.strip()]
            except (ValueError, AttributeError):
                print(f"Warning: Failed to parse vector data: {vector_data}")
                return []
        
        # その他の型（メモリビューなど）
        try:
            return [float(x) for x in vector_data]
        except (TypeError, ValueError):
            print(f"Warning: Unsupported vector data type: {type(vector_data)}")
            return []
    
    def _log_search_query(self, query_text: str, query_embedding: List[float], 
                         search_type: str, limit_count: int, similarity_threshold: float,
                         result_count: int, execution_time_ms: float) -> None:
        """検索クエリをログに記録
        
        Args:
            query_text: 検索テキスト
            query_embedding: クエリ埋め込み
            search_type: 検索タイプ
            limit_count: 結果数制限
            similarity_threshold: 類似度閾値
            result_count: 実際の結果数
            execution_time_ms: 実行時間（ミリ秒）
        """
        try:
            # 結果の統計計算（簡易版）
            max_similarity = 1.0 if result_count > 0 else 0.0
            min_similarity = similarity_threshold
            avg_similarity = (max_similarity + min_similarity) / 2
            
            embedding_str = f"[{','.join(map(str, query_embedding))}]" if query_embedding else None
            
            log_query = """
            INSERT INTO vector_search_logs 
            (query_text, query_embedding, search_type, limit_count, similarity_threshold,
             result_count, max_similarity, min_similarity, avg_similarity, execution_time_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            
            self.cur.execute(log_query, (
                query_text, embedding_str, search_type, limit_count, similarity_threshold,
                result_count, max_similarity, min_similarity, avg_similarity, execution_time_ms
            ))
            self.conn.commit()
            
        except Error:
            # ログ記録失敗は検索機能に影響しないようにサイレント
            pass
    
    def close(self) -> None:
        """データベース接続を適切にクローズ"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """コンテキストマネージャーのエントリー"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのイグジット"""
        self.close()
    
    def __del__(self):
        """デストラクタ: データベース接続を適切にクローズ"""
        self.close()