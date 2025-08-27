# PostgreSQL Demo

PostgreSQLの基本操作と全文検索システムを学習するためのプロジェクトです。
DockerコンテナとPythonを使用して、データベース操作の実践的な学習ができます。

## 主な特徴

- **pg_bigm拡張**: 日本語テキストの高速全文検索
- **Docker構成**: PostgreSQL + Python + pgAdmin の3コンテナ
- **実践的デモ**: 基本CRUD操作から高度な検索機能まで
- **江戸料理データ**: 歴史的レシピデータによる検索システム実演

## クイックスタート

### 1. 起動

```bash
./start.sh
```

### 2. 終了

```bash
./stop.sh
```

### 3. 基本的な動作確認

```bash
# 接続テスト
./test.sh
```

## デモアプリケーション

### 基本CRUD操作デモ

**タスク管理システム**:
```bash
docker exec -it python_postgres_demo /bin/bash
python src/apps/task_demo.py
```

**接続確認とテーブル一覧**:
```bash
python src/apps/connection_test.py
```

**都道府県データ管理**:
```bash
python src/apps/prefecture_demo.py
```

### 江戸料理検索デモ（pg_bigm活用）

PostgreSQLのpg_bigm拡張を使った日本語全文検索の実演：

```bash
python src/apps/edo_recipe_demo.py
```

このデモでは以下の機能を体験できます：
- **材料検索**: 指定した材料を含むレシピを類似度順で表示
- **全文検索**: レシピ名・説明文を対象とした包括的検索  
- **複合検索**: 複数条件を満たすレシピの検索
- **類似度計算**: pg_bigm の `bigm_similarity()` 関数による関連性評価

**詳細**: [江戸料理検索デモガイド](./docs/edo_recipe_demo.md)

### 江戸料理ベクター検索デモ（pg_vector + OpenAI活用）

PostgreSQLのpg_vector拡張とOpenAI埋め込みを使った意味的レシピ検索の実演：

```bash
python src/apps/edo_recipe_vector_demo.py
```

このデモでは以下の機能を体験できます：
- **意味的検索**: 自然言語クエリによる柔軟なレシピ検索
- **類似レシピ発見**: 指定レシピからの類似度ランキング
- **ハイブリッド検索**: キーワード検索×ベクター検索の統合
- **レシピ類似性分析**: レシピ間関係性の事前計算と推薦

**詳細**: [江戸料理ベクター検索デモガイド](./docs/edo_recipe_vector_demo.md)

## データベース操作方法

### コマンドライン（psql）

ホストマシンからpsqlを使用してデータベースに直接接続：

```bash
psql -h localhost -p 5555 -U postgres -d mydatabase
```

**詳細**: [psql使用ガイド](./docs/psql_usage.md)

### GUI操作（pgAdmin）

WebブラウザからGUIでデータベース管理：

```
http://localhost:8080
```

**詳細**: [pgAdmin使用ガイド](./docs/pgadmin_usage.md)

## プロジェクト構成

```
postgres_demo/
├── docker/                    # Docker設定
│   ├── docker-compose.yml     # コンテナ構成定義
│   ├── env.example            # 環境変数テンプレート
│   └── postgres_dev/          # PostgreSQL + pg_bigm設定
├── src/
│   ├── apps/                  # デモアプリケーション
│   ├── common/                # 共通ライブラリ
│   └── test_data/             # テストデータ
├── docs/                      # ドキュメント
└── *.sh                       # 操作スクリプト
```

## 環境設定

1. 環境設定ファイルをコピー：
   ```bash
   cp docker/env.example docker/.env
   ```

2. 必要に応じて `.env` ファイルを編集：
   ```bash
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=mysecretpassword
   POSTGRES_DB=mydatabase
   POSTGRES_PORT=5555
   PGADMIN_EMAIL=admin@example.com
   PGADMIN_PASSWORD=admin123
   ```

## 技術スタック

- **PostgreSQL 16**: メインデータベース
- **pg_bigm 1.2**: 日本語全文検索拡張
- **pg_vector 0.7.4**: ベクター検索拡張
- **Python 3**: アプリケーション開発
- **OpenAI API**: text-embedding-3-small埋め込みモデル
- **pgAdmin 4**: Web管理インターface
- **Docker**: コンテナ化環境

## 学習内容

このプロジェクトで学習できる内容：

1. **PostgreSQL基礎**
   - CRUD操作の実装
   - テーブル設計とリレーション
   - インデックス設計と最適化

2. **pg_bigm拡張**
   - 日本語全文検索の実装
   - GINインデックスの活用
   - 類似度検索アルゴリズム

3. **pg_vector拡張**
   - ベクター検索の実装
   - HNSWインデックスによる高速類似度検索
   - 意味的類似性とコサイン類似度

4. **AI連携**
   - OpenAI埋め込みAPIの活用
   - テキストベクター化
   - 意味的検索システム

5. **Python-PostgreSQL連携**
   - psycopg2によるデータベース接続
   - コンテキストマネージャーの活用
   - エラーハンドリング

6. **Docker環境**
   - マルチコンテナアプリケーション
   - 環境変数による設定管理
   - ネットワーク構成

## トラブルシューティング

### コンテナ起動問題

```bash
# ログ確認
docker logs postgres_bigm_demo
docker logs python_postgres_demo

# 完全リセット
./stop.sh
docker system prune -f
./start.sh
```

### データベース接続問題

```bash
# 接続確認
./test.sh

# 手動接続テスト
docker exec postgres_bigm_demo pg_isready -U postgres
```

## ドキュメント

- [江戸料理検索デモガイド](./docs/edo_recipe_demo.md) - pg_bigm全文検索
- [江戸料理ベクター検索デモガイド](./docs/edo_recipe_vector_demo.md) - pg_vector意味検索
- [psql使用ガイド](./docs/psql_usage.md)
- [pgAdmin使用ガイド](./docs/pgadmin_usage.md)