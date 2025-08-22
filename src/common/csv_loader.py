import csv
from typing import List, Dict, Optional
from pathlib import Path


class CSVLoader:
    """CSV読み取り専用クラス（SRP準拠）"""
    
    @staticmethod
    def load_prefectures_csv(file_path: str) -> List[Dict]:
        """都道府県CSVファイルを読み込み、辞書のリストとして返す
        
        Args:
            file_path: CSVファイルのパス
            
        Returns:
            都道府県データの辞書リスト
            
        Raises:
            FileNotFoundError: CSVファイルが見つからない場合
            ValueError: CSVデータの形式が不正な場合
        """
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        prefectures_data = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row_num, row in enumerate(csv_reader, start=2):  # ヘッダー行の次から
                    try:
                        prefecture_data = CSVLoader._convert_row_to_prefecture_data(row)
                        prefectures_data.append(prefecture_data)
                    except (ValueError, KeyError) as e:
                        raise ValueError(f"Invalid data in row {row_num}: {e}")
                        
        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Error reading CSV file: {e}")
        
        if not prefectures_data:
            raise ValueError("No valid prefecture data found in CSV")
            
        return prefectures_data
    
    @staticmethod
    def _convert_row_to_prefecture_data(row: Dict[str, str]) -> Dict:
        """CSVの1行を都道府県データ辞書に変換
        
        Args:
            row: CSV行データ（DictReaderから取得）
            
        Returns:
            変換された都道府県データ辞書
        """
        try:
            return {
                'id': int(row['id']),
                'name': row['name'].strip(),
                'name_kana': row['furigana'].strip(),
                'capital': row['capital'].strip(),
                'largest_city': row['largest_city'].strip(),
                'region': row['region'].strip(),
                'population': int(row['population']),
                'area': float(row['area']),
                'population_density': float(row['ppa']),
                'municipalities_count': int(row['towns']),
                'lower_house_seats': int(row['seats1']),
                'upper_house_seats': int(row['seats2'])
            }
        except (ValueError, KeyError) as e:
            raise ValueError(f"Failed to convert row data: {e}")
    
    @staticmethod
    def validate_csv_data(data_list: List[Dict]) -> bool:
        """都道府県データリストのバリデーション
        
        Args:
            data_list: 都道府県データの辞書リスト
            
        Returns:
            バリデーション結果（True: 正常, False: エラー）
        """
        if not data_list:
            return False
        
        required_fields = [
            'id', 'name', 'name_kana', 'capital', 'largest_city', 'region',
            'population', 'area', 'population_density', 'municipalities_count',
            'lower_house_seats', 'upper_house_seats'
        ]
        
        for i, prefecture in enumerate(data_list):
            # 必須フィールドの存在確認
            for field in required_fields:
                if field not in prefecture:
                    print(f"Missing field '{field}' in prefecture {i+1}")
                    return False
            
            # 基本的なデータ妥当性チェック
            if prefecture['id'] < 1 or prefecture['id'] > 47:
                print(f"Invalid prefecture ID: {prefecture['id']}")
                return False
            
            if prefecture['population'] < 0:
                print(f"Invalid population: {prefecture['population']}")
                return False
                
            if prefecture['area'] <= 0:
                print(f"Invalid area: {prefecture['area']}")
                return False
        
        return True