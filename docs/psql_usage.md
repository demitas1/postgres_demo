# psqlを使用したデータベース接続・操作

## 概要

psqlはPostgreSQLの公式コマンドラインツールです。ホストマシンからDockerコンテナ内のPostgreSQLデータベースに直接接続し、SQLクエリを実行できます。

## 前提条件

- PostgreSQLのクライアントツール（psql）がホストマシンにインストールされていること
- Dockerコンテナが起動していること（`./start.sh` 実行済み）
- 環境設定ファイル（`.env`）が正しく配置されていること

## 接続方法

### 基本的な接続コマンド

```bash
psql -h localhost -p 5555 -U postgres -d mydatabase
```

### パラメータ説明

- `-h localhost`: ホスト名（Dockerコンテナがlocalhostに公開されている）
- `-p 5555`: ポート番号（`.env`ファイルの`POSTGRES_PORT`で設定）
- `-U postgres`: ユーザー名（`.env`ファイルの`POSTGRES_USER`で設定）
- `-d mydatabase`: データベース名（`.env`ファイルの`POSTGRES_DB`で設定）

### 認証

パスワードを尋ねられるので、`.env`ファイルの`POSTGRES_PASSWORD`に設定したパスワードを入力してください。

## 基本的なクエリ例

### 1. 接続確認とテーブル一覧

```sql
-- 現在のデータベース名を確認
SELECT current_database();

-- 利用可能なテーブル一覧を表示
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';
```

**実行例**:
```console
mydatabase=# SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';
 table_name 
------------
 tasks
(1 row)
```

### 2. データの確認

```sql
-- tasksテーブルのデータを全て表示
SELECT * FROM tasks;

-- tasksテーブルの構造を確認
\d tasks
```

**実行例**:
```console
mydatabase=# SELECT * from tasks;
 id |      title       |        description         |   status    |         created_at         |         updated_at         
----+------------------+----------------------------+-------------+----------------------------+----------------------------
  2 | Dockerの理解     | コンテナ技術の基礎を学ぶ   | pending     | 2025-08-22 05:42:04.289251 | 2025-08-22 05:42:04.289251
  1 | PostgreSQLの学習 | 基本的なCRUD操作を実装する | in_progress | 2025-08-22 05:42:04.28822  | 2025-08-22 05:42:04.289956
(2 rows)
```

### 3. pg_bigm拡張の確認（江戸料理デモ実行後）

```sql
-- インストール済み拡張の確認
SELECT extname, extversion FROM pg_extension;

-- pg_bigm関数の確認
SELECT proname FROM pg_proc WHERE proname LIKE '%bigm%';

-- 江戸料理レシピテーブル（デモ実行時のみ存在）
SELECT name, id FROM edo_recipes ORDER BY id LIMIT 5;
```

## 便利なpsqlコマンド

### メタコマンド

```sql
\l          -- データベース一覧
\dt         -- テーブル一覧
\d [table]  -- テーブル構造表示
\di         -- インデックス一覧
\df         -- 関数一覧
\dx         -- 拡張機能一覧
\q          -- psql終了
\h [SQL]    -- SQLヘルプ
\?          -- psqlヘルプ
```

### 出力設定

```sql
\x          -- 拡張表示モードの切り替え（縦表示）
\timing     -- 実行時間表示の切り替え
\pset pager off  -- ページャーを無効化（長い結果の途中で止まらない）
```

## トラブルシューティング

### 接続エラー

**エラー**: `psql: error: could not connect to server`

**解決方法**:
1. Dockerコンテナが起動していることを確認: `docker ps`
2. ポート番号が正しいことを確認: `.env`ファイルの`POSTGRES_PORT`
3. ファイアウォール設定を確認

### 認証エラー

**エラー**: `psql: FATAL: password authentication failed`

**解決方法**:
1. `.env`ファイルの`POSTGRES_PASSWORD`を確認
2. 環境変数が正しくDockerコンテナに渡されているか確認

### データベース存在エラー

**エラー**: `psql: FATAL: database "mydatabase" does not exist`

**解決方法**:
1. `.env`ファイルの`POSTGRES_DB`設定を確認
2. Dockerコンテナを再起動: `./stop.sh && ./start.sh`

## 高度な使用方法

### 1. SQLファイルの実行

```bash
# ホストのSQLファイルを実行
psql -h localhost -p 5555 -U postgres -d mydatabase -f /path/to/script.sql
```

### 2. 結果をファイルに出力

```bash
# クエリ結果をCSVファイルに出力
psql -h localhost -p 5555 -U postgres -d mydatabase -c "SELECT * FROM tasks;" --csv > tasks.csv
```

### 3. バックアップとリストア

```bash
# データベースのダンプ作成
pg_dump -h localhost -p 5555 -U postgres mydatabase > backup.sql

# ダンプファイルからリストア
psql -h localhost -p 5555 -U postgres -d mydatabase < backup.sql
```

## 関連情報

- [PostgreSQL公式ドキュメント - psql](https://www.postgresql.org/docs/current/app-psql.html)
- [pgAdminを使用したGUI操作](./pgadmin_usage.md)
- [江戸料理デモでの検索機能](./edo_recipe_demo.md)