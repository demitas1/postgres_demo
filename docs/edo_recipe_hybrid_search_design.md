# 江戸料理ハイブリッド検索デモ設計書

## 概要

PostgreSQLのpg_bigm拡張（全文検索）とpg_vector拡張（ベクトル検索）を組み合わせた高度な検索システムのデモ実装設計書です。キーワード検索と意味的検索を統合し、実用的な条件付き検索機能を提供します。

## 目的

- pg_bigmとpg_vectorの連携活用方法を示す
- 実世界での検索ニーズに対応した複合検索機能の実演
- 検索手法の性能比較と最適化手法の学習支援
- 透明性の高いスコアリングシステムの提供

## 機能要件

### 1. 基本検索機能

#### 必須キーワード検索
- 指定されたキーワードを必ず含むレシピを検索
- pg_bigm の `bigm_similarity()` による類似度閾値設定
- 複数キーワードのOR条件対応

#### 除外キーワード検索  
- 指定されたキーワードを含まないレシピを検索
- 除外条件の類似度閾値設定
- 複数キーワードのAND条件対応

#### 意味的検索
- 自然言語クエリによるベクトル類似度検索
- OpenAI embeddings + pg_vector によるコサイン類似度計算
- 検索意図に基づく柔軟なマッチング

#### ハイブリッドスコアリング
- 全文検索スコアと ベクトル類似度スコアの重み付け合成
- ユーザー定義による重み比率調整機能
- 正規化済みスコアによる公平な評価

### 2. 検索モード

#### 段階的検索（Cascade Search）
```
pg_bigm絞り込み → ベクトル類似度ランキング → スコア合成
```
- 高速処理を重視
- 大量データセットでの効率的な検索
- メモリ使用量の最適化

#### 並列検索（Parallel Search）
```  
pg_bigm検索 ∥ ベクトル検索 → 結果マージ → スコア合成
```
- 高精度を重視
- 両方の検索結果を活用
- より包括的なマッチング

#### 単一手法検索
- 全文検索のみ（高速テスト用）
- ベクトル検索のみ（意味重視用）
- 性能比較とデバッグ用途

### 3. デモシナリオ

#### 精進料理風レシピ検索
```yaml
必須キーワード: ["野菜", "豆腐", "きのこ"]
除外キーワード: ["肉", "魚", "だし"]
意味的検索: "健康的でシンプルな精進料理"
重み設定: キーワード(30%) + 意味的(70%)
```

#### 季節の料理検索
```yaml  
必須キーワード: ["春", "桜", "筍", "菜の花"]
意味的検索: "季節感のある彩り豊かな春料理"
重み設定: キーワード(60%) + 意味的(40%)
```

#### 調理法指定検索
```yaml
必須キーワード: ["煮る", "蒸す"]
除外キーワード: ["揚げる", "焼く"]  
意味的検索: "やさしい味付けの煮物料理"
重み設定: キーワード(40%) + 意味的(60%)
```

## アーキテクチャ設計

### システム構成図

```
┌─────────────────────────────────────────┐
│           Demo Application              │
│     edo_recipe_hybrid_demo.py          │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│        Service Layer                   │
│   HybridRecipeSearchService           │
│   ├─ SearchCondition                  │
│   ├─ SearchResult                     │
│   └─ ScoreCalculator                  │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│       Manager Layer                    │
│  EdoRecipeHybridManager               │
│  ├─ Fulltext Search (pg_bigm)        │
│  ├─ Vector Search (pg_vector)        │
│  └─ Combined Query Builder           │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│         Database Layer                 │
│  PostgreSQL + pg_bigm + pg_vector     │
│  ├─ GIN Index (fulltext)              │
│  ├─ HNSW Index (vector)               │
│  └─ Combined Indexes                  │
└─────────────────────────────────────────┘
```

### データモデル設計

#### SearchCondition
```python
@dataclass
class SearchCondition:
    # 必須キーワード条件
    required_keywords: List[str] = field(default_factory=list)
    required_similarity_threshold: float = 0.1
    
    # 除外キーワード条件
    excluded_keywords: List[str] = field(default_factory=list)
    excluded_similarity_threshold: float = 0.1
    
    # ベクトル検索条件
    vector_query_text: str = ""
    vector_similarity_threshold: float = 0.5
    
    # ハイブリッドスコア重み
    fulltext_weight: float = 0.5
    vector_weight: float = 0.5
    
    # 結果制御
    max_results: int = 20
    search_mode: SearchMode = SearchMode.CASCADE
```

#### SearchResult
```python
@dataclass
class SearchResult:
    recipe_id: int
    recipe_name: str
    description: str
    ingredients: str
    
    # スコア詳細
    fulltext_score: float      # pg_bigm類似度スコア
    vector_score: float        # ベクトル類似度スコア  
    combined_score: float      # 重み付き合成スコア
    
    # マッチング詳細
    matched_keywords: List[str]    # ヒットしたキーワード
    excluded_keywords: List[str]   # 除外されたキーワード
    
    # メタ情報
    search_stage: str          # どの段階でマッチしたか
    rank: int                  # 最終ランキング
```

#### SearchMode
```python
class SearchMode(Enum):
    CASCADE = "cascade"        # 段階的検索（絞り込み→ベクトル）
    PARALLEL = "parallel"      # 並列検索（同時スコア計算）
    FULLTEXT_ONLY = "fulltext" # 全文検索のみ
    VECTOR_ONLY = "vector"     # ベクトル検索のみ
```

## 技術設計

### データベース最適化

#### インデックス戦略
```sql
-- pg_bigm用GINインデックス（Generalized Inverted Index）（既存）
CREATE INDEX idx_edo_recipes_bigm_text ON edo_recipes 
    USING gin (recipe_text gin_bigm_ops);

-- pg_vector用HNSWインデックス（Hierarchical Navigable Small World）（既存）  
CREATE INDEX idx_edo_recipes_embedding ON edo_recipes 
    USING hnsw (embedding vector_cosine_ops);

-- 複合検索用の新しいインデックス
CREATE INDEX idx_edo_recipes_hybrid ON edo_recipes 
    (recipe_id, recipe_name) 
    INCLUDE (description, ingredients, recipe_text);
```

#### パフォーマンス最適化クエリ

**段階的検索用（高速絞り込み）**
```sql
WITH filtered_recipes AS (
    SELECT recipe_id 
    FROM edo_recipes 
    WHERE bigm_similarity(recipe_text, $1) > $2
    LIMIT 1000  -- 最大候補数制限
)
SELECT fr.recipe_id, r.*, 1 - (r.embedding <=> $3) as vector_score
FROM filtered_recipes fr
JOIN edo_recipes r ON fr.recipe_id = r.recipe_id
ORDER BY vector_score DESC;
```

**複合クエリ（一度の実行で両方のスコア取得）**
```sql
SELECT 
    r.recipe_id,
    r.recipe_name,
    r.description, 
    r.ingredients,
    -- pg_bigm類似度スコア
    GREATEST(
        bigm_similarity(r.recipe_text, $1),
        bigm_similarity(r.ingredients, $1)
    ) as fulltext_score,
    -- ベクトル類似度スコア
    1 - (r.embedding <=> $2) as vector_score
FROM edo_recipes r
WHERE [条件]
ORDER BY [重み付けスコア] DESC;
```

### サービス層設計

#### HybridRecipeSearchService
```python
class HybridRecipeSearchService:
    def __init__(self, manager: EdoRecipeHybridManager):
        self.manager = manager
        self.score_calculator = ScoreCalculator()
    
    # メイン検索API
    async def search_recipes(self, condition: SearchCondition) -> SearchResponse:
        """全ての検索モードに対応するメインAPI"""
        
    async def suggest_keywords(self, partial_text: str) -> List[str]:
        """キーワード候補提案"""
        
    async def analyze_query(self, query_text: str) -> QueryAnalysis:
        """クエリ解析 - 自動的な条件抽出"""
        
    # パフォーマンス分析API
    async def compare_search_modes(self, condition: SearchCondition) -> PerformanceComparison:
        """異なる検索モードの性能比較（実行時間、CPU、メモリ測定）"""
```

#### ScoreCalculator
```python
class ScoreCalculator:
    def calculate_final_scores(self, results: List[SearchResult], 
                             condition: SearchCondition) -> List[SearchResult]:
        """重み付きスコア合成とランキング"""
        for result in results:
            result.combined_score = (
                result.fulltext_score * condition.fulltext_weight +
                result.vector_score * condition.vector_weight
            )
        return sorted(results, key=lambda r: r.combined_score, reverse=True)
    
    def normalize_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """スコアの0-1正規化"""
```

### マネージャー層設計

#### EdoRecipeHybridManager
```python
class EdoRecipeHybridManager:
    def __init__(self, connection_params: dict):
        self.connection_params = connection_params
        self.fulltext_manager = EdoRecipeManager(connection_params)
        self.vector_manager = EdoRecipeVectorManager(connection_params)
    
    # pg_bigmによる候補絞り込み
    async def filter_by_fulltext(self, condition: SearchCondition) -> List[int]:
        """全文検索による高速な候補絞り込み"""
        
    # ベクトル類似度による並び替え
    async def rank_by_vector_similarity(self, recipe_ids: List[int], 
                                      query_text: str) -> List[SearchResult]:
        """指定レシピIDに対するベクトル検索"""
        
    # 複合クエリ（両方のスコア同時取得）
    async def search_combined(self, condition: SearchCondition) -> List[SearchResult]:
        """一度のクエリで全文検索・ベクトル検索を実行"""
```

## ユーザーインターフェース設計

### メインメニュー
```
=== ハイブリッド検索デモ ===
1. カスタム検索 - 自由な条件設定
2. シナリオ検索 - 事前定義された実用例  
3. 性能比較デモ - 各検索手法の性能測定
4. 終了

選択してください [1-4]:
```

### カスタム検索フロー
```
=== カスタム検索 ===

■ 必須キーワード設定
含まなければならない言葉（複数可、カンマ区切り）: だし,魚
類似度閾値 [0.1-1.0] (デフォルト: 0.1): 0.2

■ 除外キーワード設定
含んではならない言葉（複数可、カンマ区切り）: 砂糖,甘い  
類似度閾値 [0.1-1.0] (デフォルト: 0.1): 0.1

■ 意味的検索設定
検索したい料理のイメージ: うま味の効いたあっさりした料理

■ スコア重み設定  
キーワードマッチ重み [0.0-1.0] (デフォルト: 0.5): 0.3
意味的類似度重み [0.0-1.0] (デフォルト: 0.5): 0.7

■ 検索モード
1. 段階的検索（高速）  2. 並列検索（高精度）  3. キーワードのみ  4. 意味検索のみ
選択 [1-4]: 1

検索を実行しますか？ [y/n]: y
```

### 結果表示
```
=== 検索結果 ===
実行時間: 0.234秒 | 総マッチ数: 156件 | 表示: 10件
CPU使用率: 45% | メモリ使用量: 128MB

【検索処理の流れ】
Stage 1 (全文検索): 1,234件 → 156件 (0.089秒)
Stage 2 (ベクトル検索): 156件 → 156件 (0.134秒)
Stage 3 (スコア計算): 156件 → 10件 (0.011秒)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 第1位 (総合スコア: 0.89)
【レシピ名】鯛のだし茶漬け
【説明文】上品な鯛の旨みとだしの香りが調和した、あっさりとした一品
【材料】鯛, 昆布だし, 米, 海苔, わさび
【マッチ詳細】
  ✓ 必須キーワード: "だし"(0.94), "魚→鯛"(0.87)
  ✗ 除外キーワード: なし  
  🎯 意味的類似度: 0.91 ("うま味があっさり" との類似性)
  📊 スコア内訳: キーワード(0.91) × 0.3 + 意味的(0.91) × 0.7 = 0.89

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 性能比較デモ
```
=== 検索手法性能比較 ===
🔍 段階的検索を実行中...
実行時間: 0.234秒 | CPU使用率: 45% | メモリ使用量: 128MB | マッチ数: 156件

🔍 並列検索を実行中...  
実行時間: 0.187秒 | CPU使用率: 62% | メモリ使用量: 156MB | マッチ数: 203件

🔍 キーワードのみ検索を実行中...
実行時間: 0.089秒 | CPU使用率: 23% | メモリ使用量: 89MB | マッチ数: 89件

🔍 意味検索のみを実行中...
実行時間: 0.334秒 | CPU使用率: 38% | メモリ使用量: 201MB | マッチ数: 234件

┌─────────────┬─────────┬─────────┬─────────┬─────────┐
│検索手法      │実行時間  │CPU使用率│メモリ    │推奨用途 │
├─────────────┼─────────┼─────────┼─────────┼─────────┤
│段階的検索    │0.234秒  │45%      │128MB    │バランス │
│並列検索      │0.187秒  │62%      │156MB    │高精度   │
│キーワードのみ│0.089秒  │23%      │89MB     │高速     │
│意味検索のみ  │0.334秒  │38%      │201MB    │発見性   │
└─────────────┴─────────┴─────────┴─────────┴─────────┘

【推奨】この条件では「並列検索」が最適です
理由: 高精度を維持しつつ高速な実行が可能
```

## ファイル構成

```
src/
├── common/
│   ├── edo_recipe_hybrid_manager.py          # 新規追加
│   ├── hybrid_recipe_search_service.py       # 新規追加
│   └── search_models.py                      # 新規追加
├── apps/
│   └── edo_recipe_hybrid_demo.py             # 新規追加
└── tests/
    └── hybrid_search/
        ├── test_hybrid_manager.py
        ├── test_hybrid_search_service.py
        └── test_search_scenarios.py
```

## 実装スケジュール

### Phase 1: 基盤実装
1. データモデル定義 (`search_models.py`)
2. ハイブリッドマネージャー実装 (`edo_recipe_hybrid_manager.py`)
3. 基本的な検索機能実装

### Phase 2: サービス層実装
1. 検索サービス実装 (`hybrid_recipe_search_service.py`)
2. スコア計算ロジック実装
3. 検索モード切り替え機能

### Phase 3: デモアプリケーション実装
1. デモアプリケーション本体 (`edo_recipe_hybrid_demo.py`)
2. ユーザーインターフェース実装
3. シナリオ検索機能

### Phase 4: 最適化・テスト
1. パフォーマンス最適化
2. ユニットテスト実装
3. 統合テスト・シナリオテスト

## 期待される学習効果

1. **pg_bigmとpg_vectorの実用的な組み合わせ方法**
2. **複合検索条件の効率的な実装パターン**  
3. **検索精度と実行速度のトレードオフ理解**
4. **透明性の高いスコアリングシステムの実装**
5. **実世界のニーズに対応した検索システム設計**

## 技術的課題と対策

### 課題1: パフォーマンス最適化
- **対策**: 段階的絞り込みによる計算量削減
- **実装**: WITH句を活用した効率的なクエリ構成

### 課題2: スコア正規化の品質  
- **対策**: 統計的手法による動的正規化
- **実装**: 各検索手法のスコア分布特性を考慮した調整

### 課題3: メモリ使用量の制御
- **対策**: 結果セットサイズの段階的制限
- **実装**: LIMITとバッチ処理による制御

### 課題4: 検索意図の解析精度
- **対策**: キーワード抽出ロジックの改良  
- **実装**: 自然言語処理による条件自動抽出

この設計により、pg_bigmとpg_vectorの連携活用を通じて、実用的で教育的価値の高いハイブリッド検索システムの実装が可能になります。