import time
import asyncio
from typing import List, Optional, Dict, Any
import openai
from openai import OpenAI
import tiktoken

from ..config.embedding_config import EmbeddingConfig


class OpenAIEmbeddingClient:
    """OpenAI embedding API client (SRP compliance)"""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize OpenAI embedding client
        
        Args:
            config: Embedding configuration
        """
        config.validate()
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self._encoding = tiktoken.get_encoding("cl100k_base")  # For text-embedding models
    
    def get_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts synchronously
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty
            openai.APIError: If OpenAI API call fails
        """
        if not texts:
            raise ValueError("テキストリストが空です")
        
        # Calculate token count for rate limiting
        total_tokens = self._calculate_token_count(texts)
        print(f"推定トークン数: {total_tokens}")
        
        try:
            response = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            print(f"✓ {len(embeddings)}件の埋め込みを生成しました")
            
            return embeddings
            
        except openai.APIError as e:
            self._handle_api_error(e)
            raise
        except Exception as e:
            print(f"予期しないエラーが発生しました: {e}")
            raise
    
    def get_single_embedding(self, text: str) -> List[float]:
        """Get embedding for single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("空のテキストは埋め込みできません")
        
        embeddings = self.get_embeddings_sync([text])
        return embeddings[0]
    
    async def get_embeddings_async(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts asynchronously
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Run sync method in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_embeddings_sync, texts)
    
    def _handle_api_error(self, error: openai.APIError) -> None:
        """Handle OpenAI API errors with Japanese messages
        
        Args:
            error: OpenAI API error
        """
        error_messages = {
            401: "APIキーが無効です",
            429: "レート制限に達しました。しばらく待ってから再試行してください",
            500: "OpenAIサーバーエラーが発生しました",
            503: "OpenAIサービスが一時的に利用できません"
        }
        
        if hasattr(error, 'status_code'):
            message = error_messages.get(error.status_code, f"API呼び出しエラー: {error}")
        else:
            message = f"API呼び出しエラー: {error}"
        
        print(f"✗ {message}")
    
    def _calculate_token_count(self, texts: List[str]) -> int:
        """Calculate approximate token count for texts
        
        Args:
            texts: List of texts
            
        Returns:
            Approximate total token count
        """
        total_tokens = 0
        for text in texts:
            tokens = len(self._encoding.encode(text))
            total_tokens += tokens
        
        return total_tokens
    
    def validate_embedding_dimensions(self, embedding: List[float]) -> bool:
        """Validate embedding dimensions
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if valid, False otherwise
        """
        return len(embedding) == self.config.embedding_dimensions
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.config.embedding_model,
            "dimensions": self.config.embedding_dimensions,
            "max_input_tokens": 8191,  # For text-embedding-3-small/large
            "pricing_per_1k_tokens": 0.00002  # USD for text-embedding-3-small
        }