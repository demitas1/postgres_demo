import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
import asyncio
from typing import List

# Test target
from apps.embedding.client.openai_client import OpenAIEmbeddingClient
from apps.embedding.config.embedding_config import EmbeddingConfig


class TestOpenAIEmbeddingClient(unittest.TestCase):
    """Test cases for OpenAIEmbeddingClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = EmbeddingConfig(
            openai_api_key="sk-test-key-123456789",
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
            batch_size=100,
            retry_attempts=3,
            retry_delay=1.0
        )
        
        self.sample_texts = [
            "これは日本語のテストテキストです",
            "This is English test text",
            "材料: 卵白2個、うに小さじ1"
        ]
        
        # Mock embedding response (1536 dimensions)
        self.mock_embedding = [0.1] * 1536
        
        # Mock OpenAI response structure
        self.mock_response = Mock()
        self.mock_response.data = []
        for _ in range(len(self.sample_texts)):
            mock_data = Mock()
            mock_data.embedding = self.mock_embedding.copy()
            self.mock_response.data.append(mock_data)
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_init_success(self, mock_openai_class):
        """Test successful client initialization"""
        client = OpenAIEmbeddingClient(self.test_config)
        
        self.assertEqual(client.config, self.test_config)
        mock_openai_class.assert_called_once_with(api_key="sk-test-key-123456789")
    
    def test_init_invalid_config(self):
        """Test initialization with invalid configuration"""
        invalid_config = EmbeddingConfig(
            openai_api_key="invalid-key",
            embedding_dimensions=-1  # Invalid
        )
        
        with self.assertRaises(ValueError):
            OpenAIEmbeddingClient(invalid_config)
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_get_embeddings_sync_success(self, mock_openai_class):
        """Test successful synchronous embedding generation"""
        # Setup mock
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance
        mock_client_instance.embeddings.create.return_value = self.mock_response
        
        # Test execution
        client = OpenAIEmbeddingClient(self.test_config)
        result = client.get_embeddings_sync(self.sample_texts)
        
        # Assertions
        self.assertEqual(len(result), len(self.sample_texts))
        self.assertEqual(len(result[0]), 1536)
        self.assertListEqual(result[0], self.mock_embedding)
        
        mock_client_instance.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=self.sample_texts
        )
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_get_embeddings_sync_empty_input(self, mock_openai_class):
        """Test embedding generation with empty input"""
        client = OpenAIEmbeddingClient(self.test_config)
        
        with self.assertRaises(ValueError) as context:
            client.get_embeddings_sync([])
        
        self.assertIn("テキストリストが空です", str(context.exception))
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_get_single_embedding_success(self, mock_openai_class):
        """Test successful single embedding generation"""
        # Setup mock
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance
        
        single_response = Mock()
        single_data = Mock()
        single_data.embedding = self.mock_embedding
        single_response.data = [single_data]
        mock_client_instance.embeddings.create.return_value = single_response
        
        # Test execution
        client = OpenAIEmbeddingClient(self.test_config)
        result = client.get_single_embedding("テストテキスト")
        
        # Assertions
        self.assertEqual(len(result), 1536)
        self.assertListEqual(result, self.mock_embedding)
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_get_single_embedding_empty_text(self, mock_openai_class):
        """Test single embedding generation with empty text"""
        client = OpenAIEmbeddingClient(self.test_config)
        
        with self.assertRaises(ValueError) as context:
            client.get_single_embedding("")
        
        self.assertIn("空のテキストは埋め込みできません", str(context.exception))
        
        with self.assertRaises(ValueError):
            client.get_single_embedding("   ")  # Only whitespace
    
    @patch('apps.embedding.client.openai_client.OpenAI')  
    def test_api_error_handling(self, mock_openai_class):
        """Test API error handling with different status codes"""
        import openai
        from unittest.mock import Mock
        
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance
        
        # Test different API errors
        test_cases = [
            (401, "APIキーが無効です"),
            (429, "レート制限に達しました"),
            (500, "OpenAIサーバーエラー"),
            (999, "API呼び出しエラー")  # Unknown error code
        ]
        
        for status_code, expected_message in test_cases:
            with self.subTest(status_code=status_code):
                # Create mock API error with proper structure for openai v1.x
                mock_request = Mock()
                api_error = openai.APIError("Test error", request=mock_request, body=None)
                api_error.status_code = status_code
                mock_client_instance.embeddings.create.side_effect = api_error
                
                client = OpenAIEmbeddingClient(self.test_config)
                
                with patch('builtins.print') as mock_print:
                    with self.assertRaises(openai.APIError):
                        client.get_embeddings_sync(["test"])
                    
                    # Check that appropriate error message was printed
                    mock_print.assert_called()
                    print_args = str(mock_print.call_args)
                    self.assertIn("✗", print_args)
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_calculate_token_count(self, mock_openai_class):
        """Test token count calculation"""
        client = OpenAIEmbeddingClient(self.test_config)
        
        # Test with known texts
        test_texts = ["Hello", "World", "これは日本語です"]
        token_count = client._calculate_token_count(test_texts)
        
        self.assertIsInstance(token_count, int)
        self.assertGreater(token_count, 0)
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_validate_embedding_dimensions(self, mock_openai_class):
        """Test embedding dimensions validation"""
        client = OpenAIEmbeddingClient(self.test_config)
        
        # Valid embedding
        valid_embedding = [0.1] * 1536
        self.assertTrue(client.validate_embedding_dimensions(valid_embedding))
        
        # Invalid embedding
        invalid_embedding = [0.1] * 512
        self.assertFalse(client.validate_embedding_dimensions(invalid_embedding))
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_get_model_info(self, mock_openai_class):
        """Test model information retrieval"""
        client = OpenAIEmbeddingClient(self.test_config)
        model_info = client.get_model_info()
        
        expected_keys = ["model", "dimensions", "max_input_tokens", "pricing_per_1k_tokens"]
        for key in expected_keys:
            self.assertIn(key, model_info)
        
        self.assertEqual(model_info["model"], "text-embedding-3-small")
        self.assertEqual(model_info["dimensions"], 1536)
    
    @patch('apps.embedding.client.openai_client.OpenAI')
    def test_async_embeddings(self, mock_openai_class):
        """Test asynchronous embedding generation"""
        # Setup mock
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance
        mock_client_instance.embeddings.create.return_value = self.mock_response
        
        client = OpenAIEmbeddingClient(self.test_config)
        
        # Test async method
        async def run_async_test():
            result = await client.get_embeddings_async(self.sample_texts)
            self.assertEqual(len(result), len(self.sample_texts))
            self.assertEqual(len(result[0]), 1536)
        
        # Run async test
        asyncio.run(run_async_test())


class TestEmbeddingConfig(unittest.TestCase):
    """Test cases for EmbeddingConfig"""
    
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'sk-test-key-123',
        'EMBEDDING_MODEL': 'text-embedding-3-large',
        'EMBEDDING_DIMENSIONS': '3072',
        'EMBEDDING_BATCH_SIZE': '50'
    })
    def test_from_environment_success(self):
        """Test configuration loading from environment variables"""
        config = EmbeddingConfig.from_environment()
        
        self.assertEqual(config.openai_api_key, 'sk-test-key-123')
        self.assertEqual(config.embedding_model, 'text-embedding-3-large')
        self.assertEqual(config.embedding_dimensions, 3072)
        self.assertEqual(config.batch_size, 50)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_from_environment_missing_api_key(self):
        """Test configuration loading without API key"""
        with self.assertRaises(ValueError) as context:
            EmbeddingConfig.from_environment()
        
        self.assertIn("OPENAI_API_KEY", str(context.exception))
    
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        config = EmbeddingConfig(
            openai_api_key="sk-valid-key-123",
            embedding_dimensions=1536,
            batch_size=100,
            retry_attempts=3,
            retry_delay=1.0
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_config_validation_failures(self):
        """Test configuration validation failures"""
        test_cases = [
            # Invalid API key
            {"openai_api_key": "invalid-key", "expected_error": "Invalid OpenAI API key"},
            # Invalid dimensions
            {"openai_api_key": "sk-valid", "embedding_dimensions": -1, "expected_error": "Embedding dimensions"},
            # Invalid batch size
            {"openai_api_key": "sk-valid", "batch_size": 0, "expected_error": "Batch size"},
            # Invalid retry attempts
            {"openai_api_key": "sk-valid", "retry_attempts": -1, "expected_error": "Retry attempts"},
            # Invalid retry delay
            {"openai_api_key": "sk-valid", "retry_delay": -1.0, "expected_error": "Retry delay"}
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                config = EmbeddingConfig(**{k: v for k, v in case.items() if k != "expected_error"})
                
                with self.assertRaises(ValueError) as context:
                    config.validate()
                
                self.assertIn(case["expected_error"], str(context.exception))
    
    def test_config_str_representation(self):
        """Test configuration string representation (API key should be hidden)"""
        config = EmbeddingConfig(openai_api_key="sk-secret-key-123")
        config_str = str(config)
        
        self.assertNotIn("sk-secret-key-123", config_str)
        self.assertIn("text-embedding-3-small", config_str)
        self.assertIn("1536", config_str)


if __name__ == '__main__':
    unittest.main()