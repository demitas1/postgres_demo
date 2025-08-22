import psycopg2
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict

from .database_config import DatabaseConfig


class EdoRecipeManager:
    """江戸料理レシピデータの管理を担当するクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """EdoRecipeManagerを初期化
        
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
    
    def tables_exist(self) -> bool:
        """江戸料理レシピテーブルの存在確認
        
        Returns:
            すべてのテーブルが存在する場合True
        """
        try:
            tables = ['edo_recipes', 'recipe_ingredients', 'recipe_instructions']
            
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
            print(f"Error checking table existence: {e}")
            return False
    
    def create_tables(self) -> bool:
        """江戸料理レシピテーブルを作成
        
        Returns:
            作成成功時はTrue、失敗時はFalse
        """
        # メインテーブル
        create_recipes_table_query = """
        CREATE TABLE IF NOT EXISTS edo_recipes (
            id SMALLINT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            tips TEXT,
            original_text TEXT,
            modern_translation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # 材料テーブル
        create_ingredients_table_query = """
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
            ingredient TEXT NOT NULL,
            sort_order SMALLINT NOT NULL
        );
        """
        
        # 手順テーブル
        create_instructions_table_query = """
        CREATE TABLE IF NOT EXISTS recipe_instructions (
            id SERIAL PRIMARY KEY,
            recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
            instruction_type VARCHAR(20) NOT NULL,
            instruction TEXT NOT NULL,
            step_number SMALLINT NOT NULL
        );
        """
        
        # インデックス作成クエリ（デフォルト設定を使用）
        create_indexes_queries = [
            "CREATE INDEX IF NOT EXISTS idx_recipes_name ON edo_recipes USING gin (to_tsvector('simple', name));",
            "CREATE INDEX IF NOT EXISTS idx_recipes_description ON edo_recipes USING gin (to_tsvector('simple', description));",
            "CREATE INDEX IF NOT EXISTS idx_ingredients_text ON recipe_ingredients USING gin (to_tsvector('simple', ingredient));",
            "CREATE INDEX IF NOT EXISTS idx_ingredients_recipe_id ON recipe_ingredients(recipe_id);",
            "CREATE INDEX IF NOT EXISTS idx_instructions_recipe_id ON recipe_instructions(recipe_id);",
            "CREATE INDEX IF NOT EXISTS idx_instructions_type ON recipe_instructions(instruction_type);"
        ]
        
        try:
            # テーブル作成
            self.cur.execute(create_recipes_table_query)
            print("✓ edo_recipesテーブルを作成しました")
            
            self.cur.execute(create_ingredients_table_query)
            print("✓ recipe_ingredientsテーブルを作成しました")
            
            self.cur.execute(create_instructions_table_query)
            print("✓ recipe_instructionsテーブルを作成しました")
            
            # インデックス作成
            for index_query in create_indexes_queries:
                self.cur.execute(index_query)
            print("✓ 検索用インデックスを作成しました")
            
            self.conn.commit()
            return True
            
        except Error as e:
            print(f"Error creating tables: {e}")
            self.conn.rollback()
            return False
    
    def drop_tables(self) -> bool:
        """江戸料理レシピ関連テーブルを削除
        
        Returns:
            削除成功時はTrue、失敗時はFalse
        """
        try:
            # CASCADE で外部キー制約も含めて削除
            drop_queries = [
                "DROP TABLE IF EXISTS recipe_instructions CASCADE;",
                "DROP TABLE IF EXISTS recipe_ingredients CASCADE;",
                "DROP TABLE IF EXISTS edo_recipes CASCADE;"
            ]
            
            for query in drop_queries:
                self.cur.execute(query)
            
            self.conn.commit()
            print("✓ 江戸料理レシピテーブルを削除しました")
            return True
            
        except Error as e:
            print(f"Error dropping tables: {e}")
            self.conn.rollback()
            return False
    
    def recipe_exists(self, recipe_id: int) -> bool:
        """指定IDのレシピが存在するかチェック
        
        Args:
            recipe_id: レシピID
            
        Returns:
            存在する場合True
        """
        try:
            self.cur.execute("SELECT EXISTS (SELECT 1 FROM edo_recipes WHERE id = %s);", (recipe_id,))
            return self.cur.fetchone()[0]
        except Error as e:
            print(f"Error checking recipe existence: {e}")
            return False
    
    def insert_recipe(self, recipe_data: Dict) -> bool:
        """レシピデータを挿入
        
        Args:
            recipe_data: レシピデータ辞書
            
        Returns:
            挿入成功時はTrue、失敗時はFalse
        """
        try:
            # 既存チェック
            if self.recipe_exists(recipe_data['id']):
                print(f"レシピID {recipe_data['id']} は既に存在します。スキップします。")
                return True
            
            # メインレシピデータ挿入
            insert_recipe_query = """
            INSERT INTO edo_recipes (
                id, name, url, description, tips, original_text, modern_translation
            ) VALUES (
                %(id)s, %(name)s, %(url)s, %(description)s, %(tips)s, %(original_text)s, %(modern_translation)s
            );
            """
            
            self.cur.execute(insert_recipe_query, recipe_data)
            
            # 材料データ挿入
            ingredients = recipe_data.get('ingredients', [])
            for i, ingredient in enumerate(ingredients, 1):
                self.cur.execute("""
                    INSERT INTO recipe_ingredients (recipe_id, ingredient, sort_order)
                    VALUES (%s, %s, %s);
                """, (recipe_data['id'], ingredient, i))
            
            # 手順データ挿入
            self._insert_instructions(recipe_data['id'], 'modern', recipe_data.get('modern_instructions', []))
            self._insert_instructions(recipe_data['id'], 'translation', recipe_data.get('modern_translation_instructions', []))
            self._insert_instructions(recipe_data['id'], 'original', recipe_data.get('original_instructions', []))
            
            self.conn.commit()
            return True
            
        except Error as e:
            print(f"Error inserting recipe data: {e}")
            self.conn.rollback()
            return False
    
    def _insert_instructions(self, recipe_id: int, instruction_type: str, instructions: List[str]) -> None:
        """手順データを挿入
        
        Args:
            recipe_id: レシピID
            instruction_type: 手順タイプ
            instructions: 手順リスト
        """
        for i, instruction in enumerate(instructions, 1):
            self.cur.execute("""
                INSERT INTO recipe_instructions (recipe_id, instruction_type, instruction, step_number)
                VALUES (%s, %s, %s, %s);
            """, (recipe_id, instruction_type, instruction, i))
    
    def get_total_recipes_count(self) -> int:
        """登録済みレシピ総数を取得
        
        Returns:
            レシピ数、エラー時は0
        """
        try:
            self.cur.execute("SELECT COUNT(*) FROM edo_recipes;")
            return self.cur.fetchone()[0]
        except Error as e:
            print(f"Error getting recipe count: {e}")
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