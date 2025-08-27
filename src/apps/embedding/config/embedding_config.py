import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmbeddingConfig:
    """Embedding configuration management class (SRP compliance)"""
    # OpenAI settings
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    # API rate limiting settings
    max_requests_per_minute: int = 3000
    max_tokens_per_minute: int = 1000000
    
    # Batch processing settings
    batch_size: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    
    @classmethod
    def from_environment(cls) -> 'EmbeddingConfig':
        """Load configuration from environment variables
        
        Returns:
            EmbeddingConfig instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return cls(
            openai_api_key=api_key,
            embedding_model=os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
            embedding_dimensions=int(os.getenv('EMBEDDING_DIMENSIONS', '1536')),
            max_requests_per_minute=int(os.getenv('MAX_REQUESTS_PER_MINUTE', '3000')),
            max_tokens_per_minute=int(os.getenv('MAX_TOKENS_PER_MINUTE', '1000000')),
            batch_size=int(os.getenv('EMBEDDING_BATCH_SIZE', '100')),
            retry_attempts=int(os.getenv('RETRY_ATTEMPTS', '3')),
            retry_delay=float(os.getenv('RETRY_DELAY', '1.0')),
            cache_enabled=os.getenv('EMBEDDING_CACHE_ENABLED', 'true').lower() == 'true',
            cache_ttl_hours=int(os.getenv('CACHE_TTL_HOURS', '24'))
        )
    
    def validate(self) -> None:
        """Validate configuration parameters
        
        Raises:
            ValueError: If configuration parameters are invalid
        """
        if not self.openai_api_key or not self.openai_api_key.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key format")
        
        if self.embedding_dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")
        
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")
        
        if self.retry_attempts < 0:
            raise ValueError("Retry attempts cannot be negative")
        
        if self.retry_delay < 0:
            raise ValueError("Retry delay cannot be negative")
    
    def __str__(self) -> str:
        """String representation with hidden API key"""
        return f"EmbeddingConfig(model={self.embedding_model}, dimensions={self.embedding_dimensions})"