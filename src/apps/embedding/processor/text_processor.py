import re
from typing import List


class RecipeTextProcessor:
    """レシピテキスト前処理クラス（SRP準拠）"""
    
    def __init__(self, max_length: int = 8000):
        """RecipeTextProcessorを初期化
        
        Args:
            max_length: 最大テキスト長（OpenAIのトークン制限対応）
        """
        self.max_length = max_length
    
    def prepare_description_text(self, descriptions: List[str]) -> str:
        """説明文テキストを準備
        
        Args:
            descriptions: 説明文リスト
            
        Returns:
            統合された説明文テキスト
        """
        if not descriptions:
            return ""
        
        # リストを結合し、前処理
        combined = "。".join(desc.strip() for desc in descriptions if desc and desc.strip())
        processed = self._clean_text(combined)
        
        return self._truncate_text(processed, self.max_length)
    
    def prepare_ingredients_text(self, ingredients: List[str]) -> str:
        """材料テキストを準備
        
        Args:
            ingredients: 材料リスト
            
        Returns:
            統合された材料テキスト
        """
        if not ingredients:
            return ""
        
        # 材料リストを自然な日本語形式で結合
        cleaned_ingredients = [ing.strip() for ing in ingredients if ing and ing.strip()]
        
        if not cleaned_ingredients:
            return ""
        
        # 「材料: 」プレフィックス付きで結合
        ingredients_text = "材料: " + "、".join(cleaned_ingredients)
        processed = self._clean_text(ingredients_text)
        
        return self._truncate_text(processed, self.max_length)
    
    def prepare_instructions_text(self, instructions: List[str]) -> str:
        """手順テキストを準備
        
        Args:
            instructions: 手順リスト
            
        Returns:
            統合された手順テキスト
        """
        if not instructions:
            return ""
        
        # 手順リストを番号付きで結合
        cleaned_instructions = [inst.strip() for inst in instructions if inst and inst.strip()]
        
        if not cleaned_instructions:
            return ""
        
        # 「手順: 」プレフィックス付きで結合
        numbered_instructions = [
            f"{i+1}. {inst}" 
            for i, inst in enumerate(cleaned_instructions)
        ]
        instructions_text = "手順: " + " ".join(numbered_instructions)
        processed = self._clean_text(instructions_text)
        
        return self._truncate_text(processed, self.max_length)
    
    def prepare_combined_text(self, description: str, ingredients: str, instructions: str) -> str:
        """全体統合テキストを準備
        
        Args:
            description: 説明文
            ingredients: 材料テキスト
            instructions: 手順テキスト
            
        Returns:
            統合されたフルテキスト
        """
        parts = []
        
        if description and description.strip():
            parts.append(f"説明: {description.strip()}")
        
        if ingredients and ingredients.strip():
            parts.append(ingredients.strip())
        
        if instructions and instructions.strip():
            parts.append(instructions.strip())
        
        if not parts:
            return ""
        
        combined = "。".join(parts) + "。"
        processed = self._clean_text(combined)
        
        return self._truncate_text(processed, self.max_length)
    
    def _clean_text(self, text: str) -> str:
        """テキストをクリーニング
        
        Args:
            text: 元テキスト
            
        Returns:
            クリーニング済みテキスト
        """
        if not text:
            return ""
        
        # 日本語テキストの正規化
        text = self._normalize_japanese_text(text)
        
        # 余分な空白・改行を削除
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        
        # 連続する句読点を整理
        text = re.sub(r'[。]+', '。', text)
        text = re.sub(r'[、]+', '、', text)
        
        # 文頭・文末の空白削除
        text = text.strip()
        
        # HTMLエンティティやURL削除（必要に応じて）
        text = re.sub(r'https?://[^\s]+', '', text)
        text = re.sub(r'&[a-zA-Z]+;', '', text)
        
        return text
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """テキストを指定長に切り詰め
        
        Args:
            text: 元テキスト
            max_length: 最大文字数
            
        Returns:
            切り詰められたテキスト
        """
        if not text or len(text) <= max_length:
            return text
        
        # 文境界で切り詰めを試行
        truncated = text[:max_length]
        
        # 最後の句点で切り詰め（より自然な切断）
        last_period = truncated.rfind('。')
        if last_period > max_length * 0.8:  # 80%以上の位置に句点があれば使用
            truncated = truncated[:last_period + 1]
        
        return truncated
    
    def _normalize_japanese_text(self, text: str) -> str:
        """日本語テキストの正規化
        
        Args:
            text: 元テキスト
            
        Returns:
            正規化されたテキスト
        """
        if not text:
            return ""
        
        # 全角・半角の統一（数字は半角、記号は全角に統一）
        text = text.translate(str.maketrans(
            '０１２３４５６７８９',
            '0123456789'
        ))
        
        # よくある表記ゆれの統一
        replacements = {
            'ヶ': 'ケ',
            'ヵ': 'カ',
            '～': 'ー',
            '〜': 'ー',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def calculate_text_stats(self, text: str) -> dict:
        """テキストの統計情報を計算
        
        Args:
            text: 対象テキスト
            
        Returns:
            統計情報辞書
        """
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "japanese_char_ratio": 0.0
            }
        
        char_count = len(text)
        
        # 単語数（スペース・句読点区切り）
        words = re.findall(r'[^\s、。]+', text)
        word_count = len(words)
        
        # 文数（句点区切り）
        sentences = [s.strip() for s in text.split('。') if s.strip()]
        sentence_count = len(sentences)
        
        # 日本語文字比率
        japanese_chars = len(re.findall(r'[ひらがなカタカナ漢字]', text))
        japanese_char_ratio = japanese_chars / char_count if char_count > 0 else 0.0
        
        return {
            "char_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "japanese_char_ratio": japanese_char_ratio
        }