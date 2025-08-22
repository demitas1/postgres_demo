import psycopg2
from psycopg2 import Error
from psycopg2.extensions import connection
from typing import Optional, List, Tuple, Dict, Any

from .database_config import DatabaseConfig


class TaskManager:
    """タスクのCRUD操作を管理するクラス（SRP準拠）"""
    
    def __init__(self, db_config: DatabaseConfig):
        """TaskManagerを初期化
        
        Args:
            db_config: データベース設定オブジェクト
        """
        self.db_config = db_config
        self.conn: Optional[connection] = None
        self.cur = None
        self._connect()
        self._create_table()
    
    def _connect(self) -> None:
        """データベースに接続"""
        try:
            self.conn = psycopg2.connect(**self.db_config.to_connection_params())
            self.cur = self.conn.cursor()
            print(f"Connected to database: {self.db_config}")
        except Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            raise
    
    def _create_table(self) -> None:
        """テーブルが存在しない場合、新規作成"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.cur.execute(create_table_query)
            self.conn.commit()
        except Error as e:
            print(f"Error creating table: {e}")
            self.conn.rollback()
            raise
    
    def create_task(self, title: str, description: str = "") -> Optional[int]:
        """新しいタスクを作成
        
        Args:
            title: タスクのタイトル
            description: タスクの説明
            
        Returns:
            作成されたタスクのID、失敗時はNone
        """
        insert_query = """
        INSERT INTO tasks (title, description)
        VALUES (%s, %s)
        RETURNING id;
        """
        try:
            self.cur.execute(insert_query, (title, description))
            task_id = self.cur.fetchone()[0]
            self.conn.commit()
            print(f"Task created successfully with ID: {task_id}")
            return task_id
        except Error as e:
            print(f"Error creating task: {e}")
            self.conn.rollback()
            return None
    
    def read_task(self, task_id: Optional[int] = None) -> Optional[List[Tuple]]:
        """タスクを読み取り
        
        Args:
            task_id: 特定のタスクID、Noneの場合は全タスクを取得
            
        Returns:
            タスクデータのリスト、失敗時はNone
        """
        try:
            if task_id:
                self.cur.execute("SELECT * FROM tasks WHERE id = %s;", (task_id,))
                result = self.cur.fetchone()
                return [result] if result else []
            else:
                self.cur.execute("SELECT * FROM tasks ORDER BY created_at DESC;")
                return self.cur.fetchall()
        except Error as e:
            print(f"Error reading task(s): {e}")
            return None
    
    def update_task(self, task_id: int, title: Optional[str] = None, 
                    description: Optional[str] = None, status: Optional[str] = None) -> bool:
        """タスクを更新
        
        Args:
            task_id: 更新するタスクのID
            title: 新しいタイトル
            description: 新しい説明
            status: 新しいステータス
            
        Returns:
            更新成功時はTrue、失敗時はFalse
        """
        update_fields = []
        values = []
        
        if title:
            update_fields.append("title = %s")
            values.append(title)
        if description:
            update_fields.append("description = %s")
            values.append(description)
        if status:
            update_fields.append("status = %s")
            values.append(status)
        
        if not update_fields:
            return False
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        
        update_query = f"""
        UPDATE tasks
        SET {", ".join(update_fields)}
        WHERE id = %s
        """
        
        try:
            self.cur.execute(update_query, values)
            self.conn.commit()
            print(f"Task {task_id} updated successfully")
            return True
        except Error as e:
            print(f"Error updating task: {e}")
            self.conn.rollback()
            return False
    
    def delete_task(self, task_id: int) -> bool:
        """タスクを削除
        
        Args:
            task_id: 削除するタスクのID
            
        Returns:
            削除成功時はTrue、失敗時はFalse
        """
        try:
            self.cur.execute("DELETE FROM tasks WHERE id = %s;", (task_id,))
            self.conn.commit()
            print(f"Task {task_id} deleted successfully")
            return True
        except Error as e:
            print(f"Error deleting task: {e}")
            self.conn.rollback()
            return False
    
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