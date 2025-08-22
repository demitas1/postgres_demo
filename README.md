# PostgreSQL Demo

PostgreSQLの基本操作と全文検索システムを学習するためのプロジェクトです。
DockerコンテナとPythonを使用して、データベース操作の実践的な学習ができます。

## クイックスタート

### 1. 起動

```bash
# コンテナを起動
./start.sh

# 環境が起動するまで少し待つ（初回は数分かかります）
```

### 2. 終了

```bash
# コンテナを終了
./stop.sh
```

## pgAdmin4 を使う

- `localhost:8080` にアクセス
- ログイン

  <img src="./docs/image/pgadmin_login.jpg" style="width:400px">

  - Email Address: `.env` で設定した `PGADMIN_EMAIL`
  - Password: `.env` で設定した `PGADMIN_PASSWORD`

- New server
  - General

    <img src="./docs/image/pgadmin_new_server_general.jpg" style="width:400px">
  
    - Name: 適当な名称

  - Connection

    <img src="./docs/image/pgadmin_new_server_connection.jpg" style="width:400px">
    
    - Host name/address: コンテナ名 `db`
    - Port: コンテナ側　`db` のポート `5432`
    - Maintenance database: `POSTGRES_DB`
    - Username: `POSTGRES_USER`
    - Password: `POSTGRES_PASSWORD`
    
  上記を設定して `Save`.
  
- Query Tool

  `mydatabase (POSTGRES_DB)` から Query Tool を開く

  <img src="./docs/image/pgadmin_query_tool.jpg" style="width:600px">