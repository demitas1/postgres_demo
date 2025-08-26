import psycopg2
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict

from .database_config import DatabaseConfig


class RecipeSearchService:
    """江戸料理レシピ検索機能を担当するクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """RecipeSearchServiceを初期化
        
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
        except Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def search_by_ingredient(self, ingredient_keyword: str, limit: int = 10) -> Optional[List[Tuple]]:
        """材料での検索 (pg_bigm使用)
        
        Args:
            ingredient_keyword: 材料キーワード
            limit: 取得件数
            
        Returns:
            (レシピID, レシピ名, 材料, 類似度) のタプルリスト、失敗時はNone
        """
        try:
            query = """
            SELECT DISTINCT r.id, r.name, array_agg(ri.ingredient ORDER BY ri.sort_order) as ingredients,
                   MAX(bigm_similarity(ri.ingredient, %s)) as max_similarity
            FROM edo_recipes r
            JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            WHERE ri.ingredient LIKE %s
            GROUP BY r.id, r.name
            ORDER BY max_similarity DESC, r.name
            LIMIT %s;
            """
            
            search_pattern = f"%{ingredient_keyword}%"
            
            self.cur.execute(query, (ingredient_keyword, search_pattern, limit))
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error searching by ingredient: {e}")
            return None
    
    def search_by_fulltext(self, search_keyword: str, limit: int = 10) -> Optional[List[Tuple]]:
        """全文検索 (pg_bigm使用)
        
        Args:
            search_keyword: 検索キーワード
            limit: 取得件数
            
        Returns:
            (レシピID, レシピ名, 説明文, 類似度スコア) のタプルリスト、失敗時はNone
        """
        try:
            query = """
            SELECT r.id, r.name, r.description,
                   GREATEST(
                       bigm_similarity(r.name, %s),
                       bigm_similarity(COALESCE(r.description, ''), %s)
                   ) as similarity_score
            FROM edo_recipes r
            WHERE (r.name LIKE %s OR COALESCE(r.description, '') LIKE %s)
            ORDER BY similarity_score DESC, r.name
            LIMIT %s;
            """
            
            search_pattern = f"%{search_keyword}%"
            
            self.cur.execute(query, (search_keyword, search_keyword, search_pattern, search_pattern, limit))
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error in fulltext search: {e}")
            return None
    
    def search_combined(self, recipe_keyword: str, ingredient_keyword: str, limit: int = 10) -> Optional[List[Tuple]]:
        """複合検索 (pg_bigm使用)
        
        Args:
            recipe_keyword: レシピ名キーワード
            ingredient_keyword: 材料キーワード
            limit: 取得件数
            
        Returns:
            (レシピID, レシピ名, 説明文, 材料リスト, 総合スコア) のタプルリスト、失敗時はNone
        """
        try:
            query = """
            SELECT DISTINCT r.id, r.name, r.description, 
                   array_agg(ri.ingredient ORDER BY ri.sort_order) as ingredients,
                   GREATEST(
                       bigm_similarity(r.name, %s),
                       bigm_similarity(COALESCE(r.description, ''), %s)
                   ) as recipe_similarity,
                   MAX(bigm_similarity(ri.ingredient, %s)) as ingredient_similarity,
                   (GREATEST(
                       bigm_similarity(r.name, %s),
                       bigm_similarity(COALESCE(r.description, ''), %s)
                   ) + MAX(bigm_similarity(ri.ingredient, %s))) as total_score
            FROM edo_recipes r
            JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            WHERE (r.name LIKE %s OR COALESCE(r.description, '') LIKE %s)
              AND ri.ingredient LIKE %s
            GROUP BY r.id, r.name, r.description
            ORDER BY total_score DESC, r.name
            LIMIT %s;
            """
            
            recipe_pattern = f"%{recipe_keyword}%"
            ingredient_pattern = f"%{ingredient_keyword}%"
            
            self.cur.execute(query, (
                recipe_keyword, recipe_keyword, ingredient_keyword,  # similarity計算用
                recipe_keyword, recipe_keyword, ingredient_keyword,  # total_score計算用
                recipe_pattern, recipe_pattern, ingredient_pattern,  # WHERE条件用
                limit
            ))
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error in combined search: {e}")
            return None
    
    def get_recipe_details(self, recipe_id: int) -> Optional[Dict]:
        """レシピ詳細情報を取得
        
        Args:
            recipe_id: レシピID
            
        Returns:
            レシピ詳細情報の辞書、失敗時はNone
        """
        try:
            # 基本情報取得
            self.cur.execute("""
                SELECT id, name, url, description, tips, original_text, modern_translation
                FROM edo_recipes WHERE id = %s;
            """, (recipe_id,))
            
            recipe_row = self.cur.fetchone()
            if not recipe_row:
                return None
            
            recipe_details = {
                'id': recipe_row[0],
                'name': recipe_row[1],
                'url': recipe_row[2],
                'description': recipe_row[3],
                'tips': recipe_row[4],
                'original_text': recipe_row[5],
                'modern_translation': recipe_row[6]
            }
            
            # 材料取得
            self.cur.execute("""
                SELECT ingredient FROM recipe_ingredients 
                WHERE recipe_id = %s ORDER BY sort_order;
            """, (recipe_id,))
            
            ingredients = [row[0] for row in self.cur.fetchall()]
            recipe_details['ingredients'] = ingredients
            
            # 手順取得
            instruction_types = ['modern', 'translation', 'original']
            for inst_type in instruction_types:
                self.cur.execute("""
                    SELECT instruction FROM recipe_instructions 
                    WHERE recipe_id = %s AND instruction_type = %s 
                    ORDER BY step_number;
                """, (recipe_id, inst_type))
                
                instructions = [row[0] for row in self.cur.fetchall()]
                recipe_details[f'{inst_type}_instructions'] = instructions
            
            return recipe_details
            
        except Error as e:
            print(f"Error getting recipe details: {e}")
            return None
    
    def get_random_recipes(self, count: int = 5) -> Optional[List[Tuple]]:
        """ランダムなレシピを取得
        
        Args:
            count: 取得件数
            
        Returns:
            (レシピID, レシピ名) のタプルリスト、失敗時はNone
        """
        try:
            query = """
            SELECT id, name FROM edo_recipes 
            ORDER BY RANDOM() 
            LIMIT %s;
            """
            
            self.cur.execute(query, (count,))
            return self.cur.fetchall()
            
        except Error as e:
            print(f"Error getting random recipes: {e}")
            return None
    
    def get_all_ingredients(self) -> Optional[List[str]]:
        """すべての材料を取得（検索候補用）
        
        Returns:
            材料名のリスト、失敗時はNone
        """
        try:
            query = """
            SELECT DISTINCT ingredient FROM recipe_ingredients 
            ORDER BY ingredient;
            """
            
            self.cur.execute(query)
            return [row[0] for row in self.cur.fetchall()]
            
        except Error as e:
            print(f"Error getting all ingredients: {e}")
            return None
    
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