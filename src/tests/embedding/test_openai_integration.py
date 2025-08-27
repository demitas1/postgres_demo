import unittest
import os
import time
from typing import List, Dict

# Test target
from apps.embedding.client.openai_client import OpenAIEmbeddingClient
from apps.embedding.config.embedding_config import EmbeddingConfig


class TestOpenAIEmbeddingIntegration(unittest.TestCase):
    """Integration tests using real OpenAI API
    
    WARNING: These tests make actual API calls and will incur costs!
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up integration test environment"""
        # Check if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or not api_key.startswith('sk-'):
            raise unittest.SkipTest(
                "OPENAI_API_KEY environment variable not found or invalid. "
                "Skipping integration tests."
            )
        
        cls.config = EmbeddingConfig.from_environment()
        cls.client = OpenAIEmbeddingClient(cls.config)
        cls.test_costs = []  # Track estimated costs
        
        print(f"✓ 統合テスト開始 - モデル: {cls.config.embedding_model}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up and show cost summary"""
        if hasattr(cls, 'test_costs') and cls.test_costs:
            total_tokens = sum(cls.test_costs)
            estimated_cost = total_tokens / 1000 * 0.00002  # $0.00002 per 1K tokens for text-embedding-3-small
            print(f"\n=== API使用量サマリー ===")
            print(f"総使用トークン数: {total_tokens:,}")
            print(f"推定コスト: ${estimated_cost:.6f} USD")
    
    def test_single_japanese_text_embedding(self):
        """Test embedding generation for single Japanese text"""
        test_text = "これは日本語のテスト用レシピです。卵と醤油を使った料理の説明文。"
        
        start_time = time.time()
        embedding = self.client.get_single_embedding(test_text)
        duration = time.time() - start_time
        
        # Record cost tracking
        token_count = self.client._calculate_token_count([test_text])
        self.test_costs.append(token_count)
        
        # Assertions
        self.assertEqual(len(embedding), self.config.embedding_dimensions)
        self.assertTrue(all(isinstance(x, float) for x in embedding))
        self.assertTrue(self.client.validate_embedding_dimensions(embedding))
        
        print(f"✓ 単一日本語テキスト埋め込み完了 ({duration:.2f}秒, {token_count}トークン)")
    
    def test_multiple_recipe_texts_embedding(self):
        """Test embedding generation for multiple recipe-like texts"""
        recipe_texts = [
            "卵白2個とうに小さじ1を使った金糸卵のレシピ",
            "醤油ベースの煮物料理、野菜と肉を柔らかく煮込む",
            "甘いお菓子作り、砂糖と小麦粉を主材料とする",
            "Modern Japanese cooking with traditional ingredients",
            "Fresh seafood preparation with soy sauce marinade"
        ]
        
        start_time = time.time()
        embeddings = self.client.get_embeddings_sync(recipe_texts)
        duration = time.time() - start_time
        
        # Record cost tracking
        token_count = self.client._calculate_token_count(recipe_texts)
        self.test_costs.append(token_count)
        
        # Assertions
        self.assertEqual(len(embeddings), len(recipe_texts))
        for i, embedding in enumerate(embeddings):
            self.assertEqual(len(embedding), self.config.embedding_dimensions)
            self.assertTrue(self.client.validate_embedding_dimensions(embedding))
        
        print(f"✓ 複数レシピテキスト埋め込み完了 ({duration:.2f}秒, {token_count}トークン)")
    
    def test_embedding_similarity_calculation(self):
        """Test semantic similarity between related texts"""
        similar_texts = [
            "卵を使った料理のレシピ",
            "たまご料理の作り方",
        ]
        
        different_texts = [
            "卵を使った料理のレシピ", 
            "魚を焼いた料理の説明"
        ]
        
        # Get embeddings
        similar_embeddings = self.client.get_embeddings_sync(similar_texts)
        different_embeddings = self.client.get_embeddings_sync(different_texts)
        
        # Record costs
        total_token_count = (
            self.client._calculate_token_count(similar_texts) +
            self.client._calculate_token_count(different_texts)
        )
        self.test_costs.append(total_token_count)
        
        # Calculate similarities (cosine similarity)
        similar_similarity = self._cosine_similarity(similar_embeddings[0], similar_embeddings[1])
        different_similarity = self._cosine_similarity(different_embeddings[0], different_embeddings[1])
        
        # Assertions
        self.assertGreater(similar_similarity, different_similarity,
                          "類似したテキストの類似度が異なるテキストより高いはず")
        self.assertGreater(similar_similarity, 0.5, "類似テキストの類似度は0.5以上のはず")
        
        print(f"✓ 意味的類似度計算完了")
        print(f"  類似テキスト類似度: {similar_similarity:.4f}")
        print(f"  異なるテキスト類似度: {different_similarity:.4f}")
    
    def test_long_text_handling(self):
        """Test embedding generation for longer texts"""
        long_recipe_text = """
        江戸時代の金糸卵というレシピについて詳しく説明します。
        この料理は卵白を主材料とし、金箔の代わりにウニを使用する現代的なアレンジが施されています。
        手順としては、まず卵白をきれいに濾し、その後でウニを少量加えてよく混ぜ合わせます。
        平鍋で湯を沸かし、湯煎にかけながらゆっくりと固めていくのがポイントです。
        この調理法により、滑らかで上品な食感を持つ料理が完成します。
        江戸時代の人々にとって、このような料理は特別な日のご馳走でした。
        現代でも高級料亭などで提供されることがある、歴史ある日本料理の一つです。
        """ * 3  # Make it longer
        
        start_time = time.time()
        embedding = self.client.get_single_embedding(long_recipe_text)
        duration = time.time() - start_time
        
        # Record cost tracking
        token_count = self.client._calculate_token_count([long_recipe_text])
        self.test_costs.append(token_count)
        
        # Assertions
        self.assertEqual(len(embedding), self.config.embedding_dimensions)
        self.assertTrue(self.client.validate_embedding_dimensions(embedding))
        
        print(f"✓ 長文テキスト埋め込み完了 ({duration:.2f}秒, {token_count}トークン)")
    
    def test_empty_and_edge_cases(self):
        """Test edge cases and error handling with real API"""
        # Test single space (should be handled gracefully)
        with self.assertRaises(ValueError):
            self.client.get_single_embedding("")
        
        with self.assertRaises(ValueError):
            self.client.get_single_embedding("   ")
        
        # Test very short text
        short_embedding = self.client.get_single_embedding("卵")
        token_count = self.client._calculate_token_count(["卵"])
        self.test_costs.append(token_count)
        
        self.assertEqual(len(short_embedding), self.config.embedding_dimensions)
        
        print(f"✓ エッジケーステスト完了")
    
    def test_model_consistency(self):
        """Test that same input produces same output (consistency check)"""
        test_text = "一貫性テスト用のレシピテキスト"
        
        # Generate embedding twice
        embedding1 = self.client.get_single_embedding(test_text)
        time.sleep(0.1)  # Small delay
        embedding2 = self.client.get_single_embedding(test_text)
        
        # Record costs
        token_count = self.client._calculate_token_count([test_text]) * 2
        self.test_costs.append(token_count)
        
        # Should be nearly identical (deterministic within floating point precision)
        similarity = self._cosine_similarity(embedding1, embedding2)
        self.assertAlmostEqual(similarity, 1.0, places=5,
                              msg="同一テキストの埋め込みはほぼ完全に一致するはず")
        
        print(f"✓ モデル一貫性テスト完了 (類似度: {similarity:.8f})")
    
    @unittest.skipIf(os.getenv('SKIP_RATE_LIMIT_TEST', 'false').lower() == 'true',
                     "Rate limit test skipped by environment variable")
    def test_batch_processing_performance(self):
        """Test performance with batch processing"""
        batch_texts = [f"レシピ{i}: 材料と調理法の説明文" for i in range(20)]
        
        start_time = time.time()
        embeddings = self.client.get_embeddings_sync(batch_texts)
        duration = time.time() - start_time
        
        # Record costs
        token_count = self.client._calculate_token_count(batch_texts)
        self.test_costs.append(token_count)
        
        # Assertions
        self.assertEqual(len(embeddings), len(batch_texts))
        
        # Performance check (should be faster than individual calls)
        per_text_time = duration / len(batch_texts)
        self.assertLess(per_text_time, 1.0, "バッチ処理は1テキストあたり1秒未満で完了するはず")
        
        print(f"✓ バッチ処理パフォーマンステスト完了")
        print(f"  {len(batch_texts)}件処理: {duration:.2f}秒")
        print(f"  1件あたり: {per_text_time:.3f}秒")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)


if __name__ == '__main__':
    unittest.main()