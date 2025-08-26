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
        """
        # Dockerコンテナ内実行の判定
        is_container = os.path.exists('/.dockerenv')
        
        # TODO: コンテナ内でのみ実行するように変更

        # 環境変数 POSTGRES_* から取得する。設定されていなければデフォルト値を返す.
        return cls(
            host=os.getenv('POSTGRES_HOST', 'db'),
            port='5432',  # Container 側のポート 固定設定
            database=os.getenv('POSTGRES_DB', 'mydatabase'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'mysecretpassword')
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