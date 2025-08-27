import psycopg2
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict, Any

from .database_config import DatabaseConfig


class EdoRecipeVectorManager:
    """江戸料理レシピベクターデータの管理を担当するクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """EdoRecipeVectorManagerを初期化
        
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
    
    def vector_tables_exist(self) -> bool:
        """ベクターテーブルの存在確認
        
        Returns:
            すべてのベクターテーブルが存在する場合True
        """
        try:
            tables = ['edo_recipe_vectors', 'recipe_similarities']
            
            for table_name in tables:
                self.cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
                
                if not self.cur.fetchone()[0]:
                    return False
            
            return True
        except Error as e:
            print(f"Error checking vector table existence: {e}")
            return False
    
    def create_vector_tables(self) -> bool:
        """ベクターテーブルを作成
        
        Returns:
            作成成功時はTrue、失敗時はFalse
        """
        # pg_vector extension enable query
        enable_vector_extension_query = "CREATE EXTENSION IF NOT EXISTS vector;"
        
        # メインベクターテーブル
        create_vectors_table_query = """
        CREATE TABLE IF NOT EXISTS edo_recipe_vectors (
            id SERIAL PRIMARY KEY,
            recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
            
            -- テキストデータ（埋め込み対象）
            description_text TEXT NOT NULL,
            ingredients_text TEXT NOT NULL,
            instructions_text TEXT NOT NULL,
            combined_text TEXT NOT NULL,
            
            -- 埋め込みベクター（OpenAI text-embedding-3-small: 1536次元）
            description_embedding vector(1536),
            ingredients_embedding vector(1536),
            instructions_embedding vector(1536),
            combined_embedding vector(1536),
            
            -- メタデータ
            embedding_model VARCHAR(50) DEFAULT 'text-embedding-3-small',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- 制約
            UNIQUE(recipe_id)
        );
        """
        
        # 類似性テーブル
        create_similarities_table_query = """
        CREATE TABLE IF NOT EXISTS recipe_similarities (
            id SERIAL PRIMARY KEY,
            source_recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
            target_recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
            
            -- 類似度スコア
            description_similarity FLOAT NOT NULL,
            ingredients_similarity FLOAT NOT NULL,  
            instructions_similarity FLOAT NOT NULL,
            combined_similarity FLOAT NOT NULL,
            
            -- 類似性タイプ
            similarity_type VARCHAR(20) DEFAULT 'cosine',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- 制約（自己参照防止、重複防止）
            CHECK (source_recipe_id != target_recipe_id),
            UNIQUE(source_recipe_id, target_recipe_id)
        );
        """
        
        # ベクター検索ログテーブル
        create_search_logs_table_query = """
        CREATE TABLE IF NOT EXISTS vector_search_logs (
            id SERIAL PRIMARY KEY,
            query_text TEXT NOT NULL,
            query_embedding vector(1536),
            
            -- 検索パラメータ
            search_type VARCHAR(20) NOT NULL,
            limit_count INTEGER DEFAULT 5,
            similarity_threshold FLOAT DEFAULT 0.0,
            
            -- 結果メタデータ
            result_count INTEGER NOT NULL,
            max_similarity FLOAT,
            min_similarity FLOAT,
            avg_similarity FLOAT,
            
            -- 実行情報
            execution_time_ms FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # ベクター類似性検索用インデックス作成クエリ（HNSW方式、コサイン類似度最適化）
        create_vector_indexes_queries = [
            "CREATE INDEX IF NOT EXISTS idx_recipe_vectors_description_cosine ON edo_recipe_vectors USING hnsw (description_embedding vector_cosine_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recipe_vectors_ingredients_cosine ON edo_recipe_vectors USING hnsw (ingredients_embedding vector_cosine_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recipe_vectors_instructions_cosine ON edo_recipe_vectors USING hnsw (instructions_embedding vector_cosine_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recipe_vectors_combined_cosine ON edo_recipe_vectors USING hnsw (combined_embedding vector_cosine_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recipe_vectors_recipe_id ON edo_recipe_vectors(recipe_id);",
            "CREATE INDEX IF NOT EXISTS idx_similarities_source ON recipe_similarities(source_recipe_id, combined_similarity DESC);",
            "CREATE INDEX IF NOT EXISTS idx_similarities_combined ON recipe_similarities(combined_similarity DESC);",
            "CREATE INDEX IF NOT EXISTS idx_search_logs_type ON vector_search_logs(search_type);",
            "CREATE INDEX IF NOT EXISTS idx_search_logs_created ON vector_search_logs(created_at);"
        ]
        
        try:
            # pg_vector拡張を有効化
            self.cur.execute(enable_vector_extension_query)
            print("✓ pg_vector拡張を有効化しました")
            
            # テーブル作成
            self.cur.execute(create_vectors_table_query)
            print("✓ edo_recipe_vectorsテーブルを作成しました")
            
            self.cur.execute(create_similarities_table_query)
            print("✓ recipe_similaritiesテーブルを作成しました")
            
            self.cur.execute(create_search_logs_table_query)
            print("✓ vector_search_logsテーブルを作成しました")
            
            # ベクター検索用インデックス作成
            for index_query in create_vector_indexes_queries:
                self.cur.execute(index_query)
            print("✓ ベクター検索用インデックスを作成しました")
            
            self.conn.commit()
            return True
            
        except Error as e:
            print(f"Error creating vector tables: {e}")
            self.conn.rollback()
            return False
    
    def drop_vector_tables(self) -> bool:
        """ベクターテーブルを削除
        
        Returns:
            削除成功時はTrue、失敗時はFalse
        """
        try:
            # CASCADE で外部キー制約も含めて削除
            drop_queries = [
                "DROP TABLE IF EXISTS vector_search_logs CASCADE;",
                "DROP TABLE IF EXISTS recipe_similarities CASCADE;",
                "DROP TABLE IF EXISTS edo_recipe_vectors CASCADE;"
            ]
            
            for query in drop_queries:
                self.cur.execute(query)
            
            self.conn.commit()
            print("✓ ベクターテーブルを削除しました")
            return True
            
        except Error as e:
            print(f"Error dropping vector tables: {e}")
            self.conn.rollback()
            return False
    
    def get_recipes_with_modern_data(self) -> List[Tuple[int, str]]:
        """現代レシピデータが存在するレシピの一覧を取得
        
        Returns:
            (recipe_id, recipe_name)のタプルリスト
        """
        try:
            query = """
            SELECT DISTINCT r.id, r.name 
            FROM edo_recipes r
            INNER JOIN recipe_instructions ri ON r.id = ri.recipe_id 
            WHERE ri.instruction_type = 'modern'
            AND EXISTS (
                SELECT 1 FROM recipe_ingredients ing 
                WHERE ing.recipe_id = r.id
            )
            ORDER BY r.id;
            """
            
            self.cur.execute(query)
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error getting recipes with modern data: {e}")
            return []
    
    def get_recipe_text_data(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """指定レシピのテキストデータを取得して統合
        
        Args:
            recipe_id: レシピID
            
        Returns:
            統合されたテキストデータ辞書、失敗時はNone
        """
        try:
            # レシピ基本情報取得
            recipe_query = """
            SELECT name, description, tips
            FROM edo_recipes 
            WHERE id = %s;
            """
            
            self.cur.execute(recipe_query, (recipe_id,))
            recipe_info = self.cur.fetchone()
            
            if not recipe_info:
                return None
            
            name, description, tips = recipe_info
            
            # 材料データ取得
            ingredients_query = """
            SELECT ingredient
            FROM recipe_ingredients 
            WHERE recipe_id = %s
            ORDER BY sort_order;
            """
            
            self.cur.execute(ingredients_query, (recipe_id,))
            ingredients = [row[0] for row in self.cur.fetchall()]
            
            # 現代手順データ取得
            instructions_query = """
            SELECT instruction
            FROM recipe_instructions 
            WHERE recipe_id = %s AND instruction_type = 'modern'
            ORDER BY step_number;
            """
            
            self.cur.execute(instructions_query, (recipe_id,))
            instructions = [row[0] for row in self.cur.fetchall()]
            
            # テキスト統合
            description_text = f"{name}。{description or ''}。{tips or ''}".strip()
            ingredients_text = "材料: " + "、".join(ingredients)
            instructions_text = "手順: " + "。".join(instructions)
            combined_text = f"レシピ名: {name}。説明: {description or ''}。{ingredients_text}。{instructions_text}。{tips or ''}".strip()
            
            return {
                "recipe_id": recipe_id,
                "recipe_name": name,
                "description_text": description_text,
                "ingredients_text": ingredients_text,
                "instructions_text": instructions_text,
                "combined_text": combined_text
            }
            
        except Error as e:
            print(f"Error getting recipe text data for ID {recipe_id}: {e}")
            return None
    
    def insert_recipe_vectors(self, vector_data: Dict[str, Any]) -> bool:
        """レシピベクターデータを挿入
        
        Args:
            vector_data: ベクターデータ辞書
            
        Returns:
            挿入成功時はTrue、失敗時はFalse
        """
        try:
            # 既存チェック
            self.cur.execute("""
                SELECT EXISTS (SELECT 1 FROM edo_recipe_vectors WHERE recipe_id = %s);
            """, (vector_data['recipe_id'],))
            
            if self.cur.fetchone()[0]:
                print(f"レシピID {vector_data['recipe_id']} のベクターデータは既に存在します。スキップします。")
                return True
            
            # ベクターデータ挿入
            insert_query = """
            INSERT INTO edo_recipe_vectors (
                recipe_id, description_text, ingredients_text, instructions_text, combined_text,
                description_embedding, ingredients_embedding, instructions_embedding, combined_embedding,
                embedding_model
            ) VALUES (
                %(recipe_id)s, %(description_text)s, %(ingredients_text)s, %(instructions_text)s, %(combined_text)s,
                %(description_embedding)s, %(ingredients_embedding)s, %(instructions_embedding)s, %(combined_embedding)s,
                %(embedding_model)s
            );
            """
            
            self.cur.execute(insert_query, vector_data)
            self.conn.commit()
            return True
            
        except Error as e:
            print(f"Error inserting recipe vectors: {e}")
            self.conn.rollback()
            return False
    
    def get_total_vector_recipes_count(self) -> int:
        """ベクター化済みレシピ総数を取得
        
        Returns:
            ベクター化済みレシピ数、エラー時は0
        """
        try:
            self.cur.execute("SELECT COUNT(*) FROM edo_recipe_vectors;")
            return self.cur.fetchone()[0]
        except Error as e:
            print(f"Error getting vector recipe count: {e}")
            return 0
    
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