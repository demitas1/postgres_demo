import time
import asyncio
from typing import List, Dict, Any, Optional
from ..client.openai_client import OpenAIEmbeddingClient
from ..config.embedding_config import EmbeddingConfig


class EmbeddingBatchProcessor:
    """埋め込み生成バッチ処理クラス（SRP準拠）"""
    
    def __init__(self, client: OpenAIEmbeddingClient, config: EmbeddingConfig):
        """EmbeddingBatchProcessorを初期化
        
        Args:
            client: OpenAI埋め込みクライアント
            config: 埋め込み設定
        """
        self.client = client
        self.config = config
    
    def process_recipe_batch_sync(self, recipe_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """レシピデータのバッチ処理（同期版）
        
        Args:
            recipe_data: レシピデータのリスト
            
        Returns:
            埋め込み付きレシピデータのリスト
        """
        if not recipe_data:
            return []
        
        print(f"🔄 {len(recipe_data)}件のレシピの埋め込み生成を開始...")
        start_time = time.time()
        
        processed_data = []
        total_tokens = 0
        
        # バッチサイズでデータを分割
        batches = self._split_into_batches(recipe_data, self.config.batch_size)
        
        for batch_idx, batch in enumerate(batches, 1):
            print(f"📦 バッチ {batch_idx}/{len(batches)} を処理中... ({len(batch)}件)")
            
            batch_start = time.time()
            processed_batch = []
            
            for recipe in batch:
                try:
                    # 各テキストタイプの埋め込み生成
                    texts_to_embed = [
                        recipe['description_text'],
                        recipe['ingredients_text'],
                        recipe['instructions_text'],
                        recipe['combined_text']
                    ]
                    
                    # APIに送信するテキストを準備
                    non_empty_texts = [text for text in texts_to_embed if text and text.strip()]
                    
                    if not non_empty_texts:
                        print(f"⚠️  レシピID {recipe['recipe_id']}: 埋め込み可能なテキストがありません")
                        continue
                    
                    # 埋め込み生成（リトライ機能付き）
                    embeddings = self._retry_with_backoff(
                        self.client.get_embeddings_sync,
                        texts_to_embed
                    )
                    
                    # 結果を辞書に格納
                    recipe_with_embeddings = recipe.copy()
                    recipe_with_embeddings.update({
                        'description_embedding': embeddings[0] if len(embeddings) > 0 else None,
                        'ingredients_embedding': embeddings[1] if len(embeddings) > 1 else None,
                        'instructions_embedding': embeddings[2] if len(embeddings) > 2 else None,
                        'combined_embedding': embeddings[3] if len(embeddings) > 3 else None,
                        'embedding_model': self.config.embedding_model
                    })
                    
                    processed_batch.append(recipe_with_embeddings)
                    
                    # トークン数計算
                    token_count = self.client._calculate_token_count(non_empty_texts)
                    total_tokens += token_count
                    
                    print(f"✓ レシピID {recipe['recipe_id']} 完了 ({token_count}トークン)")
                    
                except Exception as e:
                    print(f"❌ レシピID {recipe.get('recipe_id', 'unknown')}: {e}")
                    continue
            
            processed_data.extend(processed_batch)
            batch_duration = time.time() - batch_start
            print(f"✓ バッチ {batch_idx} 完了 ({batch_duration:.2f}秒)\n")
            
            # レート制限対策：バッチ間で少し待機
            if batch_idx < len(batches):
                time.sleep(0.5)
        
        # 処理時間統計
        total_duration = time.time() - start_time
        processing_stats = self._calculate_processing_time(start_time, len(processed_data))
        
        print(f"🎉 バッチ処理完了!")
        print(f"   処理件数: {len(processed_data)}/{len(recipe_data)}")
        print(f"   総処理時間: {total_duration:.2f}秒")
        print(f"   平均処理時間: {processing_stats['avg_time_per_item']:.2f}秒/件")
        print(f"   総使用トークン数: {total_tokens:,}")
        print(f"   推定コスト: ${total_tokens/1000 * 0.00002:.6f} USD")
        
        return processed_data
    
    async def process_recipe_batch_async(self, recipe_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """レシピデータのバッチ処理（非同期版）
        
        Args:
            recipe_data: レシピデータのリスト
            
        Returns:
            埋め込み付きレシピデータのリスト
        """
        # 同期版をスレッドプールで実行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process_recipe_batch_sync, recipe_data)
    
    def _split_into_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """リストをバッチサイズで分割
        
        Args:
            items: 分割対象リスト
            batch_size: バッチサイズ
            
        Returns:
            分割されたバッチのリスト
        """
        if batch_size <= 0:
            return [items]
        
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i + batch_size])
        
        return batches
    
    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """指数バックオフによるリトライ処理
        
        Args:
            func: 実行する関数
            *args: 関数の位置引数
            **kwargs: 関数のキーワード引数
            
        Returns:
            関数の実行結果
            
        Raises:
            Exception: 最大リトライ回数後も失敗した場合
        """
        last_exception = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.retry_attempts - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)  # 指数バックオフ
                    print(f"⚠️  API呼び出し失敗 (試行 {attempt + 1}/{self.config.retry_attempts}): {e}")
                    print(f"   {wait_time:.1f}秒後に再試行...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ 最大リトライ回数に達しました: {e}")
        
        raise last_exception
    
    def _calculate_processing_time(self, start_time: float, item_count: int) -> Dict[str, Any]:
        """処理時間統計を計算
        
        Args:
            start_time: 処理開始時刻
            item_count: 処理アイテム数
            
        Returns:
            処理時間統計辞書
        """
        end_time = time.time()
        total_duration = end_time - start_time
        
        return {
            "total_duration": total_duration,
            "item_count": item_count,
            "avg_time_per_item": total_duration / item_count if item_count > 0 else 0,
            "items_per_second": item_count / total_duration if total_duration > 0 else 0,
            "start_time": start_time,
            "end_time": end_time
        }
    
    def estimate_processing_time(self, recipe_count: int) -> Dict[str, Any]:
        """処理時間の推定
        
        Args:
            recipe_count: 処理予定レシピ数
            
        Returns:
            推定時間情報
        """
        # 経験値ベースの推定（1レシピあたり約1-2秒）
        estimated_time_per_recipe = 1.5  # 秒
        estimated_total_time = recipe_count * estimated_time_per_recipe
        
        # トークン数とコストの推定
        estimated_tokens_per_recipe = 100  # 平均的なトークン数
        estimated_total_tokens = recipe_count * estimated_tokens_per_recipe
        estimated_cost = estimated_total_tokens / 1000 * 0.00002  # USD
        
        return {
            "recipe_count": recipe_count,
            "estimated_time_seconds": estimated_total_time,
            "estimated_time_minutes": estimated_total_time / 60,
            "estimated_tokens": estimated_total_tokens,
            "estimated_cost_usd": estimated_cost,
            "estimated_cost_jpy": estimated_cost * 150  # 概算レート
        }