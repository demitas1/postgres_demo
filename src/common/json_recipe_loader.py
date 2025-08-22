import json
from pathlib import Path
from typing import List, Dict, Optional


class JsonRecipeLoader:
    """JSONレシピデータの読み込みを担当するクラス（SRP準拠）"""
    
    @staticmethod
    def load_edo_recipes_json(file_path: str) -> List[Dict]:
        """江戸料理レシピJSONファイルを読み込み
        
        Args:
            file_path: JSONファイルのパス
            
        Returns:
            レシピデータの辞書リスト
            
        Raises:
            FileNotFoundError: ファイルが見つからない場合
            ValueError: JSONデータが不正な場合
        """
        try:
            json_path = Path(file_path)
            if not json_path.exists():
                raise FileNotFoundError(f"JSON file not found: {file_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError("JSON data must be a list of recipes")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    @staticmethod
    def filter_valid_recipes(recipes: List[Dict]) -> List[Dict]:
        """有効なレシピ（modern_recipeが存在するもの）をフィルタリング
        
        Args:
            recipes: レシピデータの辞書リスト
            
        Returns:
            有効なレシピのみの辞書リスト
        """
        valid_recipes = []
        
        for recipe in recipes:
            if JsonRecipeLoader._is_valid_recipe(recipe):
                valid_recipes.append(recipe)
        
        return valid_recipes
    
    @staticmethod
    def _is_valid_recipe(recipe: Dict) -> bool:
        """レシピが有効かどうかを判定
        
        Args:
            recipe: レシピデータの辞書
            
        Returns:
            有効な場合True
        """
        modern_recipe = recipe.get('modern_recipe', {})
        ingredients = modern_recipe.get('ingredients', [])
        
        # 材料が存在し、空でない場合を有効とする
        return isinstance(ingredients, list) and len(ingredients) > 0
    
    @staticmethod
    def extract_recipe_data(recipe: Dict) -> Dict:
        """レシピデータを database用の形式に変換
        
        Args:
            recipe: 元のレシピデータ辞書
            
        Returns:
            データベース用に変換されたレシピデータ辞書
        """
        modern_recipe = recipe.get('modern_recipe', {})
        
        # 配列データを改行区切り文字列に変換
        description_list = modern_recipe.get('description', [])
        description = '\n'.join(description_list) if description_list else ''
        
        original_text_list = recipe.get('original_text', [])
        original_text = '\n'.join(original_text_list) if original_text_list else ''
        
        modern_translation_list = recipe.get('modern_translation', [])
        modern_translation = '\n'.join(modern_translation_list) if modern_translation_list else ''
        
        return {
            'id': int(recipe.get('id', 0)),
            'name': recipe.get('name', ''),
            'url': recipe.get('url', ''),
            'description': description,
            'tips': modern_recipe.get('tips', ''),
            'original_text': original_text,
            'modern_translation': modern_translation,
            'ingredients': modern_recipe.get('ingredients', []),
            'modern_instructions': modern_recipe.get('modern_instructions', []),
            'modern_translation_instructions': recipe.get('modern_translation_instructions', []),
            'original_instructions': recipe.get('original_instructions', [])
        }
    
    @staticmethod
    def validate_recipe_data(recipe_data: Dict) -> bool:
        """変換後のレシピデータをバリデーション
        
        Args:
            recipe_data: 変換後のレシピデータ辞書
            
        Returns:
            バリデーション成功時True
        """
        required_fields = ['id', 'name', 'url']
        
        for field in required_fields:
            if not recipe_data.get(field):
                return False
        
        # IDが正の整数であることを確認
        if not isinstance(recipe_data['id'], int) or recipe_data['id'] <= 0:
            return False
        
        # 材料が存在することを確認
        if not recipe_data.get('ingredients'):
            return False
        
        return True