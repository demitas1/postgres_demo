# 江戸料理ベクター検索デモガイド

PostgreSQLのpg_vector拡張とOpenAI埋め込みを使用した意味的レシピ検索システムのデモンストレーションです。

## 概要

このデモは、従来のキーワード検索（pg_bigm）に加えて、**意味的類似性**に基づくレシピ検索を実現します。OpenAIの埋め込みモデルを使用してテキストをベクター化し、pg_vectorによるコサイン類似度検索を行います。

### 主な機能

- **A. 意味的レシピ検索**: 自然言語クエリによる柔軟な検索
- **C. レシピ間類似性分析**: 類似レシピの発見と推薦
- **D. 創作レシピ支援**: ハイブリッド検索による精度向上

## 前提条件

### 必要な環境
- Docker環境（postgres_bigm_demo + python_postgres_demo コンテナ）
- OpenAI APIキー（環境変数`OPENAI_API_KEY`に設定）
- 基本レシピデータ（42件の現代レシピデータ対象）

### 拡張機能
- **pg_vector**: PostgreSQLのベクター検索拡張
- **pg_bigm**: 日本語全文検索拡張（既存）

## デモの実行

### 1. 基本実行

```bash
# Pythonコンテナに入る
docker exec -it python_postgres_demo /bin/bash

# デモ実行
cd /app/src/apps
python edo_recipe_vector_demo.py
```

### 2. 実行フロー

```
1. 基本レシピデータセットアップ
   └── 江戸料理JSONデータの読み込みと登録

2. ベクターデータベースセットアップ
   ├── pg_vector拡張の有効化
   ├── ベクターテーブル作成
   ├── 埋め込み生成（初回のみ、コスト確認あり）
   └── 42件のレシピをベクター化

3. 検索デモ実行
   ├── 意味的レシピ検索
   ├── 類似レシピ発見
   ├── ハイブリッド検索
   └── レシピ類似性分析

4. クリーンアップ（オプション）
   └── ベクターテーブル削除
```

## 検索機能の詳細

### A. 意味的レシピ検索

自然言語による柔軟なレシピ検索が可能です。

**検索例**:
```
クエリ: "卵を使った甘い料理"
結果: 
  • 丸雪卵 (類似度: 0.6479)
  • 五色卵 (類似度: 0.6367)
  • 青海卵 (類似度: 0.6332)
```

**特徴**:
- キーワードに含まれない概念でも意味的に関連するレシピを発見
- 多言語対応（英語クエリでも日本語レシピを検索可能）
- 類似度スコア（0.0-1.0）による関連度表示

### C. レシピ間類似性分析

指定レシピに基づく類似レシピの推薦機能です。

**分析例**:
```
基準レシピ: "金糸卵"
類似レシピ:
  • 銀糸卵 (類似度: 0.7630)
  • 糸組卵 (類似度: 0.7274)
  • 源氏卵 (類似度: 0.7142)
```

**機能**:
- レシピ間の事前類似性計算
- 類似度マトリクスの保存
- 検索履歴とパフォーマンス監視

### D. 創作レシピ支援（ハイブリッド検索）

キーワード検索とベクター検索を組み合わせた高精度検索です。

**検索例**:
```
クエリ: "卵"
結果:
  • 花卵 統合スコア: 0.4294
    (キーワード: 0.3333, ベクター: 0.4935)
```

**重み調整**:
- `keyword_weight`: キーワード検索の重み（デフォルト: 0.4）
- `vector_weight`: ベクター検索の重み（デフォルト: 0.6）

## 技術仕様

### データベース構成

#### メインベクターテーブル: `edo_recipe_vectors`

```sql
CREATE TABLE edo_recipe_vectors (
    id SERIAL PRIMARY KEY,
    recipe_id SMALLINT REFERENCES edo_recipes(id),
    
    -- テキストデータ
    description_text TEXT NOT NULL,
    ingredients_text TEXT NOT NULL, 
    instructions_text TEXT NOT NULL,
    combined_text TEXT NOT NULL,
    
    -- 1536次元埋め込みベクター
    description_embedding vector(1536),
    ingredients_embedding vector(1536),
    instructions_embedding vector(1536),
    combined_embedding vector(1536),
    
    embedding_model VARCHAR(50) DEFAULT 'text-embedding-3-small'
);
```

#### インデックス設計

```sql
-- HNSWインデックス（コサイン類似度最適化）
CREATE INDEX ON edo_recipe_vectors 
USING hnsw (combined_embedding vector_cosine_ops);
```

### 埋め込み生成

**使用モデル**: OpenAI `text-embedding-3-small`
- **次元数**: 1536
- **コスト**: $0.00002 USD / 1,000トークン
- **推定トークン数**: 42レシピで約4,200トークン
- **推定コスト**: 約$0.08 USD（約12円）

**テキスト処理**:
- 説明文、材料、手順を統合
- 日本語テキスト正規化
- 8,000文字制限での切り詰め

## コスト管理

### 自動コスト見積もり

デモ実行時に自動で表示されます：

```
💰 推定コスト:
   トークン数: 4,200
   推定時間: 2.8分
   推定コスト: $0.000084 USD
             (約0.013円)
```

### 埋め込み生成の確認

初回実行時のみ埋め込み生成が必要で、ユーザー確認が求められます：

```
⚠️  42件のレシピの埋め込み生成が必要です
埋め込み生成を実行しますか？ (y/N): 
```

## パフォーマンス

### 検索速度
- **ベクター検索**: 4-6ms（HNSWインデックス使用）
- **ハイブリッド検索**: 10-15ms
- **類似性計算**: 50ペアで約2秒

### リソース使用量
- **メモリ**: 1536次元×42レシピ×4種類 = 約1MB
- **ストレージ**: インデックス含めて約10MB

## トラブルシューティング

### 1. OpenAI API関連

**エラー**: `OPENAI_API_KEY環境変数が設定されていません`
```bash
# .envファイルにAPIキーを追加
echo "OPENAI_API_KEY=sk-your-api-key" >> docker/.env
```

**エラー**: `レート制限に達しました`
- 自動リトライ機能が動作します（最大3回、指数バックオフ）
- 必要に応じて`RETRY_DELAY`環境変数で調整可能

### 2. データベースロック問題

**症状**: テーブル削除時に長時間待機

**原因**: 他のセッションによるテーブルロック

**解決方法**:
```sql
-- 1. ロック状況確認
SELECT pid, state, query 
FROM pg_stat_activity 
WHERE query LIKE '%recipe%';

-- 2. idle in transactionセッション確認
SELECT pid, state, state_change 
FROM pg_stat_activity 
WHERE state = 'idle in transaction';

-- 3. 問題セッション強制終了
SELECT pg_terminate_backend(PID番号);
```

**コンテナでの実行例**:
```bash
docker exec postgres_bigm_demo psql -U postgres -d mydatabase -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction' 
AND pid != pg_backend_pid();
"
```

### 3. 埋め込み関連

**エラー**: `can't multiply sequence by non-int`
- PostgreSQL vector型の文字列パースエラー
- 最新版では修正済み

**エラー**: `推定トークン数の計算エラー`
- tiktoken版数が古い可能性
- `pip install tiktoken==0.8.0`で更新

## アーキテクチャ

### コンポーネント構成

```
edo_recipe_vector_demo.py (メインアプリ)
├── EdoRecipeVectorManager (ベクターDB管理)
├── RecipeVectorSearchService (検索エンジン)
├── EmbeddingBatchProcessor (埋め込み生成)
├── RecipeTextProcessor (テキスト前処理)
└── OpenAIEmbeddingClient (API連携)
```

### データフロー

```
1. JSONレシピデータ読み込み
   ↓
2. 現代レシピデータフィルタリング (42件)
   ↓
3. テキスト統合・正規化
   ↓
4. OpenAI APIで埋め込み生成
   ↓
5. PostgreSQL pg_vectorテーブル保存
   ↓
6. HNSWインデックス構築
   ↓ 
7. コサイン類似度検索
```

## 関連ファイル

### 実装ファイル
- `src/apps/edo_recipe_vector_demo.py` - メインデモアプリ
- `src/common/edo_recipe_vector_manager.py` - ベクターDB管理
- `src/common/recipe_vector_search_service.py` - 検索サービス
- `src/apps/embedding/` - 埋め込み処理モジュール

### テストファイル
- `src/run_embedding_tests.py` - 単体テスト（モック使用）
- `src/run_embedding_integration_tests.py` - 統合テスト（実API使用）

### 設定ファイル
- `docker/.env` - 環境変数設定
- `docker/python_dev/requirements.txt` - Python依存関係

## 比較: pg_bigm vs pg_vector

| 機能 | pg_bigm | pg_vector |
|------|---------|-----------|
| **検索方式** | N-gramキーワード検索 | 意味的類似性検索 |
| **対象** | 文字列の部分一致 | 意味・コンテキスト |
| **精度** | 文字レベル | 概念レベル |
| **多言語** | 日本語特化 | 多言語対応 |
| **コスト** | なし | OpenAI API料金 |
| **即座性** | 即座 | 事前埋め込み必要 |
| **用途** | 正確な用語検索 | 曖昧・概念的検索 |

## まとめ

このベクター検索デモにより、従来のキーワード検索では発見できない**意味的に関連するレシピ**を見つけることができます。江戸料理という歴史的なデータセットを題材に、最新のAI技術（OpenAI埋め込み + PostgreSQL pg_vector）の実用性を体験できるシステムです。

42件のレシピデータを使用した実証により、自然言語クエリによる柔軟なレシピ検索、類似レシピ推薦、ハイブリッド検索の有効性が確認されています。