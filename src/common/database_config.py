import os
from dataclasses import dataclass
from typing import Dict

@dataclass
class DatabaseConfig:
    """データベース接続設定を管理するクラス（SRP準拠）"""
    host: str
    port: str
    database: str
    user: str
    password: str
    
    @classmethod
    def from_environment(cls) -> 'DatabaseConfig':
        """環境変数から設定を読み込み
        
        実行環境を自動検出してデフォルト値を設定：
        - コンテナ内: host=db, port=5432
        - ホスト: host=127.0.0.1, port=5555
        """
        # Dockerコンテナ内実行の判定
        is_container = os.path.exists('/.dockerenv')
        
        return cls(
            host=os.getenv('DB_HOST', 'db' if is_container else '127.0.0.1'),
            port=os.getenv('DB_PORT', '5432' if is_container else '5555'),
            database=os.getenv('DB_NAME', 'mydatabase'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'mysecretpassword')
        )
    
    def to_connection_params(self) -> Dict[str, str]:
        """psycopg2接続パラメータに変換"""
        return {
            'host': self.host,
            'port': self.port,
            'dbname': self.database,
            'user': self.user,
            'password': self.password
        }
    
    def __str__(self) -> str:
        """接続情報の表示（パスワードは隠蔽）"""
        return f"DatabaseConfig(host={self.host}, port={self.port}, database={self.database}, user={self.user})"