import psycopg2
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict

from .database_config import DatabaseConfig


class PrefectureManager:
    """都道府県データの管理を担当するクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """PrefectureManagerを初期化
        
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
    
    def table_exists(self, table_name: str) -> bool:
        """テーブルの存在確認
        
        Args:
            table_name: 確認するテーブル名
            
        Returns:
            テーブルが存在する場合True
        """
        try:
            self.cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (table_name,))
            return self.cur.fetchone()[0]
        except Error as e:
            print(f"Error checking table existence: {e}")
            return False
    
    def create_tables(self) -> bool:
        """都道府県テーブルを作成
        
        Returns:
            作成成功時はTrue、失敗時はFalse
        """
        create_prefectures_table_query = """
        CREATE TABLE IF NOT EXISTS prefectures (
            id SMALLINT PRIMARY KEY,
            name VARCHAR(10) NOT NULL,
            name_kana VARCHAR(20) NOT NULL,
            capital VARCHAR(20) NOT NULL,
            largest_city VARCHAR(20) NOT NULL,
            region VARCHAR(10) NOT NULL,
            population INTEGER NOT NULL,
            area DECIMAL(10,2) NOT NULL,
            population_density DECIMAL(8,1) NOT NULL,
            municipalities_count SMALLINT NOT NULL,
            lower_house_seats SMALLINT NOT NULL,
            upper_house_seats SMALLINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # インデックス作成クエリ
        create_indexes_queries = [
            "CREATE INDEX IF NOT EXISTS idx_prefectures_population ON prefectures(population DESC);",
            "CREATE INDEX IF NOT EXISTS idx_prefectures_area ON prefectures(area DESC);",
            "CREATE INDEX IF NOT EXISTS idx_prefectures_density ON prefectures(population_density DESC);",
            "CREATE INDEX IF NOT EXISTS idx_prefectures_region ON prefectures(region);"
        ]
        
        try:
            # テーブル作成
            self.cur.execute(create_prefectures_table_query)
            print("✓ prefecturesテーブルを作成しました")
            
            # インデックス作成
            for index_query in create_indexes_queries:
                self.cur.execute(index_query)
            print("✓ インデックスを作成しました")
            
            self.conn.commit()
            return True
            
        except Error as e:
            print(f"Error creating tables: {e}")
            self.conn.rollback()
            return False
    
    def drop_tables(self) -> bool:
        """都道府県関連テーブルを削除
        
        Returns:
            削除成功時はTrue、失敗時はFalse
        """
        try:
            # CASCADE でインデックスも含めて削除
            self.cur.execute("DROP TABLE IF EXISTS prefectures CASCADE;")
            self.conn.commit()
            print("✓ 既存テーブルを削除しました")
            return True
            
        except Error as e:
            print(f"Error dropping tables: {e}")
            self.conn.rollback()
            return False
    
    def insert_prefecture_data(self, data_list: List[Dict]) -> bool:
        """都道府県データを挿入
        
        Args:
            data_list: 都道府県データの辞書リスト
            
        Returns:
            挿入成功時はTrue、失敗時はFalse
        """
        insert_query = """
        INSERT INTO prefectures (
            id, name, name_kana, capital, largest_city, region,
            population, area, population_density, municipalities_count,
            lower_house_seats, upper_house_seats
        ) VALUES (
            %(id)s, %(name)s, %(name_kana)s, %(capital)s, %(largest_city)s, %(region)s,
            %(population)s, %(area)s, %(population_density)s, %(municipalities_count)s,
            %(lower_house_seats)s, %(upper_house_seats)s
        );
        """
        
        try:
            # バッチ挿入の実行
            self.cur.executemany(insert_query, data_list)
            self.conn.commit()
            print(f"✓ {len(data_list)}件のデータを挿入しました")
            return True
            
        except Error as e:
            print(f"Error inserting prefecture data: {e}")
            self.conn.rollback()
            return False
    
    def get_top_prefectures_by_area(self, limit: int = 3) -> Optional[List[Tuple]]:
        """面積の大きい都道府県を取得
        
        Args:
            limit: 取得する件数
            
        Returns:
            (都道府県名, 面積) のタプルリスト、失敗時はNone
        """
        try:
            self.cur.execute("""
                SELECT name, area 
                FROM prefectures 
                ORDER BY area DESC 
                LIMIT %s;
            """, (limit,))
            return self.cur.fetchall()
        except Error as e:
            print(f"Error getting top prefectures by area: {e}")
            return None
    
    def get_top_prefectures_by_population(self, limit: int = 3) -> Optional[List[Tuple]]:
        """人口の多い都道府県を取得
        
        Args:
            limit: 取得する件数
            
        Returns:
            (都道府県名, 人口) のタプルリスト、失敗時はNone
        """
        try:
            self.cur.execute("""
                SELECT name, population 
                FROM prefectures 
                ORDER BY population DESC 
                LIMIT %s;
            """, (limit,))
            return self.cur.fetchall()
        except Error as e:
            print(f"Error getting top prefectures by population: {e}")
            return None
    
    def get_total_records_count(self) -> int:
        """テーブル内の総レコード数を取得
        
        Returns:
            レコード数、エラー時は0
        """
        try:
            self.cur.execute("SELECT COUNT(*) FROM prefectures;")
            return self.cur.fetchone()[0]
        except Error as e:
            print(f"Error getting record count: {e}")
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