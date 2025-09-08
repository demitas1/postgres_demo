"""
Search models for hybrid recipe search functionality.
Data classes and enums for search conditions and results.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time


class SearchMode(Enum):
    """Search execution modes"""
    CASCADE = "cascade"        # Stage-wise search (filter → vector)
    PARALLEL = "parallel"      # Parallel search (simultaneous scoring)
    FULLTEXT_ONLY = "fulltext" # Full-text search only
    VECTOR_ONLY = "vector"     # Vector search only


@dataclass
class SearchCondition:
    """Search condition parameters"""
    # Required keyword conditions
    required_keywords: List[str] = field(default_factory=list)
    required_similarity_threshold: float = 0.1  # pg_bigm threshold
    
    # Excluded keyword conditions
    excluded_keywords: List[str] = field(default_factory=list)
    excluded_similarity_threshold: float = 0.1
    
    # Vector search conditions
    vector_query_text: str = ""
    vector_similarity_threshold: float = 0.5  # Cosine similarity threshold
    
    # Hybrid score weights
    fulltext_weight: float = 0.5
    vector_weight: float = 0.5
    
    # Result control
    max_results: int = 20
    search_mode: SearchMode = SearchMode.CASCADE

    def __post_init__(self):
        """Validate search condition parameters"""
        if self.fulltext_weight + self.vector_weight != 1.0:
            # Normalize weights if they don't sum to 1.0
            total = self.fulltext_weight + self.vector_weight
            if total > 0:
                self.fulltext_weight /= total
                self.vector_weight /= total
            else:
                self.fulltext_weight = 0.5
                self.vector_weight = 0.5


@dataclass
class SearchResult:
    """Individual search result"""
    recipe_id: int
    recipe_name: str
    description: str
    ingredients: str
    
    # Score details
    fulltext_score: float = 0.0      # pg_bigm similarity score
    vector_score: float = 0.0        # Vector similarity score
    combined_score: float = 0.0      # Weighted combined score
    
    # Matching details
    matched_keywords: List[str] = field(default_factory=list)    # Matched keywords
    excluded_keywords: List[str] = field(default_factory=list)   # Excluded keywords found
    
    # Meta information
    search_stage: str = ""           # Which stage matched this result
    rank: int = 0                    # Final ranking position


@dataclass
class SearchStage:
    """Search stage execution information"""
    stage_name: str
    candidates_in: int
    candidates_out: int
    execution_time: float
    sql_query: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance measurement data"""
    fulltext_time: float = 0.0
    vector_time: float = 0.0
    scoring_time: float = 0.0
    total_time: float = 0.0
    cpu_percent: float = 0.0
    memory_usage_mb: float = 0.0
    
    def start_timing(self):
        """Start performance timing"""
        self.start_time = time.time()
        return self
    
    def end_timing(self):
        """End performance timing and calculate total"""
        if hasattr(self, 'start_time'):
            self.total_time = time.time() - self.start_time
        return self


@dataclass
class SearchResponse:
    """Complete search response"""
    results: List[SearchResult]
    total_matches: int
    execution_time: float
    search_stages: List[SearchStage] = field(default_factory=list)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    search_condition: Optional[SearchCondition] = None


@dataclass
class PerformanceComparison:
    """Performance comparison between different search modes"""
    cascade_metrics: PerformanceMetrics
    parallel_metrics: PerformanceMetrics
    fulltext_metrics: PerformanceMetrics
    vector_metrics: PerformanceMetrics
    recommended_mode: SearchMode
    recommendation_reason: str


@dataclass
class QueryAnalysis:
    """Query analysis results for automatic condition extraction"""
    suggested_required: List[str] = field(default_factory=list)
    suggested_excluded: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    query_complexity: str = "simple"  # "simple", "moderate", "complex"


# Predefined demo scenarios
DEMO_SCENARIOS = {
    "卵料理専門": SearchCondition(
        required_keywords=["卵"],
        excluded_keywords=["肉", "魚"],
        vector_query_text="色鮮やかで美しい卵料理",
        fulltext_weight=0.4,
        vector_weight=0.6,
        search_mode=SearchMode.CASCADE,
        max_results=15
    ),
    
    "華やか卵料理": SearchCondition(
        required_keywords=["卵"],
        vector_query_text="華やかで彩り豊かな卵料理",
        fulltext_weight=0.6,
        vector_weight=0.4,
        search_mode=SearchMode.PARALLEL,
        max_results=15
    ),
    
    "お吸い物風": SearchCondition(
        required_keywords=["卵"],
        vector_query_text="上品でやさしい味の料理",
        fulltext_weight=0.4,
        vector_weight=0.6,
        search_mode=SearchMode.CASCADE,
        max_results=15
    ),
    
    "色鮮やか卵": SearchCondition(
        required_keywords=["卵"],
        vector_query_text="色とりどりで美しい卵料理",
        fulltext_weight=0.5,
        vector_weight=0.5,
        search_mode=SearchMode.PARALLEL,
        max_results=20
    )
}