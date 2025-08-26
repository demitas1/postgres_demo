# 江戸料理レシピ検索デモ (edo_recipe_demo.py)

## 概要

`edo_recipe_demo.py` は、PostgreSQLの **pg_bigm拡張** を活用した日本語全文検索のデモプログラムです。江戸時代の料理書『万宝料理秘密箱 卵百珍』から抽出された107件のレシピデータ（うち現代レシピ42件）を使用して、pg_bigmによる高性能な日本語テキスト検索機能を実演します。

## 主な特徴

### pg_bigm拡張の活用
- **バイグラム検索**: 2文字の組み合わせによる高精度な日本語検索
- **GINインデックス**: pg_bigm専用インデックスによる高速検索
- **類似度計算**: `bigm_similarity()` 関数による検索結果の関連性評価
- **日本語最適化**: 従来のtsvectorと比べて日本語テキストに特化した検索性能

### 検索機能
1. **材料検索**: 指定した材料を含むレシピを類似度順で検索
2. **全文検索**: レシピ名・説明文を対象とした包括的検索
3. **複合検索**: レシピ名と材料の両方条件を満たすレシピを検索
4. **詳細表示**: 検索結果の完全な情報を表示

## 実行方法

### 1. 基本実行

```bash
# Pythonコンテナに入る
docker exec -it python_postgres_demo /bin/bash

# デモプログラムを実行
python src/apps/edo_recipe_demo.py
```

### 2. 実行フロー

```
起動 → pg_bigm拡張有効化 → テーブル作成 → データ読み込み → 検索デモ → クリーンアップ → 終了
```

## デモ内容

### 1. 材料検索デモ

**検索対象**: `recipe_ingredients` テーブル
**機能**: 指定材料を含むレシピを類似度順で表示

```sql
-- 実行されるクエリ例（卵の場合）
SELECT DISTINCT r.id, r.name, array_agg(ri.ingredient ORDER BY ri.sort_order) as ingredients,
       MAX(bigm_similarity(ri.ingredient, '卵')) as max_similarity
FROM edo_recipes r
JOIN recipe_ingredients ri ON r.id = ri.recipe_id
WHERE ri.ingredient LIKE '%卵%'
GROUP BY r.id, r.name
ORDER BY max_similarity DESC, r.name
LIMIT 3;
```

**検索例**:
- 「卵」→ 冷し卵羊羹、卜活卵、卵潮煎 など
- 「うに」→ 金糸卵（ウニを使用）
- 「醤油」→ 漉粉卵善哉、長崎ズズヘイ など

### 2. 全文検索デモ

**検索対象**: `edo_recipes.name`, `edo_recipes.description`
**機能**: レシピ名と説明文から関連レシピを類似度順で表示

```sql
-- 実行されるクエリ例（卵の場合）
SELECT r.id, r.name, r.description,
       GREATEST(
           bigm_similarity(r.name, '卵'),
           bigm_similarity(COALESCE(r.description, ''), '卵')
       ) as similarity_score
FROM edo_recipes r
WHERE (r.name LIKE '%卵%' OR COALESCE(r.description, '') LIKE '%卵%')
ORDER BY similarity_score DESC, r.name
LIMIT 3;
```

**検索例**:
- 「卵」→ 花卵、丸雪卵、五色卵 など（レシピ名に含まれる場合）
- 「濃厚」→ 金糸卵（説明文に「旨味濃厚！」が含まれる）
- 「現代」→ 現代風アレンジの説明があるレシピ

### 3. 複合検索デモ

**検索対象**: レシピ名・説明文 + 材料
**機能**: 複数条件を満たすレシピを総合スコア順で表示

```sql
-- 実行されるクエリ例
SELECT DISTINCT r.id, r.name, r.description, 
       array_agg(ri.ingredient ORDER BY ri.sort_order) as ingredients,
       (GREATEST(
           bigm_similarity(r.name, 'レシピキーワード'),
           bigm_similarity(COALESCE(r.description, ''), 'レシピキーワード')
       ) + MAX(bigm_similarity(ri.ingredient, '材料キーワード'))) as total_score
FROM edo_recipes r
JOIN recipe_ingredients ri ON r.id = ri.recipe_id
WHERE (r.name LIKE '%レシピキーワード%' OR COALESCE(r.description, '') LIKE '%レシピキーワード%')
  AND ri.ingredient LIKE '%材料キーワード%'
GROUP BY r.id, r.name, r.description
ORDER BY total_score DESC, r.name
LIMIT 2;
```

**検索例**:
- レシピ名「濃厚」+ 材料「卵白」→ 金糸卵
- レシピ名「現代」+ 材料「油」→ 金糸卵、かもじ卵 など

### 4. レシピ詳細表示例

ランダムに選択されたレシピの完全な情報を表示：
- URL、説明、材料数、手順数、調理のコツ

## データベーススキーマ

### 1. メインテーブル

```sql
-- レシピ基本情報
edo_recipes (
    id SMALLINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    tips TEXT,
    original_text TEXT,
    modern_translation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 材料情報
recipe_ingredients (
    id SERIAL PRIMARY KEY,
    recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
    ingredient TEXT NOT NULL,
    sort_order SMALLINT NOT NULL
);

-- 手順情報
recipe_instructions (
    id SERIAL PRIMARY KEY,
    recipe_id SMALLINT REFERENCES edo_recipes(id) ON DELETE CASCADE,
    instruction_type VARCHAR(20) NOT NULL,  -- 'modern', 'translation', 'original'
    instruction TEXT NOT NULL,
    step_number SMALLINT NOT NULL
);
```

### 2. pg_bigm専用インデックス

```sql
-- pg_bigmを活用したGINインデックス
CREATE INDEX idx_recipes_name_bigm ON edo_recipes USING gin (name gin_bigm_ops);
CREATE INDEX idx_recipes_description_bigm ON edo_recipes USING gin (description gin_bigm_ops);
CREATE INDEX idx_ingredients_bigm ON recipe_ingredients USING gin (ingredient gin_bigm_ops);
```

## 技術仕様

### 使用技術
- **PostgreSQL 16**: メインデータベース
- **pg_bigm 1.2**: 日本語全文検索拡張
- **Python 3**: アプリケーション言語
- **psycopg2**: PostgreSQLドライバ

### pg_bigm機能の利用
1. **拡張の有効化**: `CREATE EXTENSION IF NOT EXISTS pg_bigm;`
2. **専用インデックス**: `gin_bigm_ops` オペレータークラス使用
3. **類似度計算**: `bigm_similarity()` 関数による数値化
4. **高速検索**: バイグラムベースの効率的な部分文字列検索

## 実行結果例

```
=== 材料検索デモ ===

'卵' を使ったレシピを検索中...
  • 冷し卵羊羹 (ID: 47, 類似度: 0.167)
    材料: 卵: 5個, 卵: 5個
  • 卜活卵（しめじたまご） (ID: 12, 類似度: 0.167)
    材料: 卵: 2個
  • 卵潮煎（たまごうしおに） (ID: 96, 類似度: 0.167)
    材料: 卵: 4個

=== 全文検索デモ ===

'卵' でレシピを全文検索中...
  • 花卵 (ID: 16, 類似度: 0.333)
    説明: お箸で作れる！かんたん花卵 考案：AMANE 江戸時代からあった花形卵☆...
  • 丸雪卵 (ID: 73, 類似度: 0.250)
    説明: 新食感！丸雪卵 考案：三ツ星たまごソムリエ友加里...
```

## 学習ポイント

このデモを通じて以下を学習できます：

1. **pg_bigm拡張の実装方法**: PostgreSQLでの日本語検索拡張の導入
2. **GINインデックスの活用**: 高速全文検索のためのインデックス設計
3. **類似度検索の実装**: テキストの関連性を数値化する手法
4. **複合検索の設計**: 複数条件を組み合わせた高度な検索機能
5. **日本語テキスト処理**: バイグラムベースの文字列処理の理解

## 注意事項

- データのクリーンアップが自動実行されるため、データは永続化されません
- 検索性能は pg_bigm インデックスにより大幅に向上していますが、データサイズが小さいため体感差は限定的です
- 類似度スコアは0.0〜1.0の範囲で、値が高いほど関連性が高いことを示します
- 全42件のレシピが検索対象となり、残り65件は現代レシピデータが存在しないため除外されます

## 関連ファイル

- **アプリケーション**: `src/apps/edo_recipe_demo.py`
- **データベース管理**: `src/common/edo_recipe_manager.py`
- **検索サービス**: `src/common/recipe_search_service.py`
- **データローダー**: `src/common/json_recipe_loader.py`
- **テストデータ**: `src/test_data/edo_ryori/edo_recipes_all.json`