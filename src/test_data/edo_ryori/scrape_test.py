import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from urllib.parse import urljoin
import re
import argparse

class EdoRecipeScraper:
    def __init__(self, sleep_time=1):
        self.base_url = "https://codh.rois.ac.jp/edo-cooking/tamago-hyakuchin/recipe/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.recipes = []
        self.sleep_time = sleep_time
        
    def get_recipe_list(self):
        """レシピ一覧ページから個別レシピのURLを取得"""
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # デバッグ情報を追加
            print(f"ページタイトル: {soup.title.text if soup.title else 'タイトルなし'}")
            
            # テーブルからレシピリンクを抽出
            recipe_links = []
            table = soup.find('table')
            
            if table:
                print("テーブル要素を発見しました")
                tbody = table.find('tbody')
                rows = tbody.find_all('tr') if tbody else table.find_all('tr')
                print(f"テーブル内の行数: {len(rows)}")
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # 1列目から番号を取得
                        recipe_id = cells[0].text.strip()
                        
                        # 2列目からレシピ名とリンクを取得
                        recipe_cell = cells[1]
                        link = recipe_cell.find('a')
                        
                        if link and link.get('href'):
                            recipe_name = link.text.strip()
                            recipe_url = urljoin(self.base_url, link.get('href'))
                            
                            recipe_links.append({
                                'id': recipe_id,
                                'name': recipe_name,
                                'url': recipe_url
                            })
                            print(f"レシピを発見: {recipe_id} - {recipe_name}")
            else:
                print("テーブル要素が見つかりませんでした")
                # 代替方法：レシピリンクを直接検索
                recipe_links_alt = soup.find_all('a', href=re.compile(r'\d{3}\.html\.ja'))
                print(f"代替方法で {len(recipe_links_alt)} 個のレシピリンクを発見")
                
                for i, link in enumerate(recipe_links_alt, 1):
                    recipe_name = link.text.strip()
                    recipe_url = urljoin(self.base_url, link.get('href'))
                    
                    recipe_links.append({
                        'id': str(i),
                        'name': recipe_name,
                        'url': recipe_url
                    })
            
            print(f"レシピ一覧から {len(recipe_links)} 件のレシピを発見")
            return recipe_links
            
        except Exception as e:
            print(f"レシピ一覧の取得に失敗: {e}")
            import traceback
            print(f"エラー詳細: {traceback.format_exc()}")
            return []

    def scrape_recipe_detail(self, recipe_info):
        """個別レシピページの詳細情報を取得"""
        try:
            print(f"レシピ '{recipe_info['name']}' を取得中...")
            
            # サーバー負荷軽減のためのスリープ
            if self.sleep_time > 0:
                time.sleep(self.sleep_time)
            
            response = requests.get(recipe_info['url'], headers=self.headers)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            recipe_data = {
                'id': recipe_info['id'],
                'name': recipe_info['name'],
                'url': recipe_info['url'],
                'original_text': [],
                'modern_translation': [],
                'modern_recipe': {
                    'description': [],
                    'ingredients': [],
                    'modern_instructions': [],  # 現代レシピの手順
                    'tips': ''
                },
                'modern_translation_instructions': [],  # 現代語訳の手順
                'original_instructions': [],  # 翻刻テキストの手順
                'usage': '',
                'tools': '',
                'raw_content': ''
            }
            
            # ページの全テキストを取得
            main_content = soup.find('main') or soup.find('body')
            if main_content:
                recipe_data['raw_content'] = main_content.get_text(separator='\n', strip=True)
            
            # 翻刻テキスト（原文）を取得 - h2タグを探す
            original_section = soup.find('h2', string=re.compile('翻刻テキスト'))
            if original_section:
                print("翻刻テキストセクションを発見")
                # 次の要素を取得
                current = original_section.find_next_sibling()
                original_parts = []
                while current and current.name != 'h2':
                    if current.name in ['h4', 'p', 'div', 'table']:
                        original_parts.append(current.get_text(strip=True))
                    current = current.find_next_sibling()
                
                if original_parts:
                    # 複数行テキストを行単位の配列に変換
                    all_text = '\n'.join(original_parts)
                    recipe_data['original_text'] = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            # 現代語訳を取得 - h2タグを探す
            modern_section = soup.find('h2', string=re.compile('現代語訳'))
            if modern_section:
                print("現代語訳セクションを発見")
                current = modern_section.find_next_sibling()
                modern_parts = []
                while current and current.name != 'h2':
                    if current.name in ['h4', 'p', 'div', 'table']:
                        modern_parts.append(current.get_text(strip=True))
                    current = current.find_next_sibling()
                
                if modern_parts:
                    # 複数行テキストを行単位の配列に変換
                    all_text = '\n'.join(modern_parts)
                    recipe_data['modern_translation'] = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            # 現代レシピを取得 - h2タグを探す
            recipe_section = soup.find('h2', string=re.compile('現代レシピ'))
            if recipe_section:
                print("現代レシピセクションを発見")
                current = recipe_section.find_next_sibling()
                recipe_parts = []
                
                while current and current.name != 'h2':
                    if current.name == 'h3':
                        # レシピ名・説明
                        recipe_parts.append(current.get_text(strip=True))
                    elif current.name == 'p':
                        # コツ・ポイントかどうか確認
                        prev_h4 = current.find_previous_sibling('h4')
                        if prev_h4 and any(keyword in prev_h4.get_text() for keyword in ['コツ', 'ポイント']):
                            recipe_data['modern_recipe']['tips'] = current.get_text(strip=True)
                            print(f"コツ・ポイントを発見: {current.get_text(strip=True)[:50]}...")
                        else:
                            recipe_parts.append(current.get_text(strip=True))
                    elif current.name == 'ol':
                        # 作り方（リスト形式）
                        instructions = [li.get_text(strip=True) for li in current.find_all('li')]
                        recipe_data['modern_recipe']['instructions'].extend(instructions)
                    current = current.find_next_sibling()
                
                if recipe_parts:
                    # 複数行テキストを行単位の配列に変換
                    all_text = '\n'.join(recipe_parts)
                    recipe_data['modern_recipe']['description'] = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            # 材料と手順を全ページから検索（現代レシピセクション外にある）
            print("\\n材料と手順をページ全体から検索中...")
            
            # 材料テーブルを検索：ヘッダーに「材料」と「分量」が含まれているテーブル
            all_tables = soup.find_all('table')
            print(f"ページ内のテーブル数: {len(all_tables)}")
            
            for table in all_tables:
                thead = table.find('thead')
                tbody = table.find('tbody')
                
                if thead and tbody:
                    thead_text = thead.get_text()
                    print(f"テーブルヘッダー確認: {thead_text}")
                    
                    if '材料' in thead_text and '分量' in thead_text:
                        # 材料テーブル
                        print("★ 材料テーブルを発見!")
                        rows = tbody.find_all('tr')
                        print(f"材料テーブル行数: {len(rows)}")
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                ingredient_name = cells[0].get_text(strip=True)
                                ingredient_amount = cells[1].get_text(strip=True)
                                print(f"材料候補: {ingredient_name} - {ingredient_amount}")
                                # 有効な材料データかチェック
                                if ingredient_name and ingredient_amount and ingredient_name != '材料':
                                    ingredient = f"{ingredient_name}: {ingredient_amount}"
                                    recipe_data['modern_recipe']['ingredients'].append(ingredient)
                                    print(f"✓ 材料を追加: {ingredient}")
            
            # 手順テーブルを検索：h4で「手順」の直後にあるテーブル
            # 現代レシピ、現代語訳、翻刻テキストの各セクションを識別
            print("\\n手順テーブルを検索中...")
            current_section = ""
            h2_headers = soup.find_all('h2')
            
            # セクションの境界を特定
            for h2 in h2_headers:
                h2_text = h2.get_text()
                if '現代レシピ' in h2_text:
                    current_section = "modern_recipe"
                    self._extract_instructions_for_section(soup, h2, recipe_data, current_section)
                elif '現代語訳' in h2_text:
                    current_section = "modern_translation"
                    self._extract_instructions_for_section(soup, h2, recipe_data, current_section)
                elif '翻刻テキスト' in h2_text:
                    current_section = "original"
                    self._extract_instructions_for_section(soup, h2, recipe_data, current_section)
            
            # より柔軟なアプローチ：キーワードベースで情報抽出
            self._extract_flexible_content(soup, recipe_data)
            
            return recipe_data
            
        except Exception as e:
            print(f"レシピ '{recipe_info['name']}' の取得に失敗: {e}")
            return None

    def _extract_instructions_for_section(self, soup, section_header, recipe_data, section_type):
        """特定のセクション内の手順テーブルを抽出"""
        print(f"\\n=== {section_header.get_text()} セクションの手順を検索 ===")
        
        # セクション内のh4「手順」ヘッダーを探す
        current = section_header.find_next_sibling()
        
        while current and current.name != 'h2':  # 次のh2まで
            if current.name == 'h4' and '手順' in current.get_text():
                print(f"★ 手順ヘッダーを発見: {current.get_text()}")
                
                # 次のテーブルを探す
                next_element = current.find_next_sibling()
                while next_element and next_element.name != 'h2':
                    if next_element.name == 'table' or (next_element.name == 'div' and next_element.find('table')):
                        table = next_element if next_element.name == 'table' else next_element.find('table')
                        print(f"★ {section_type} 手順テーブルを発見!")
                        
                        tbody = table.find('tbody') if table.find('tbody') else table
                        rows = tbody.find_all('tr')
                        print(f"手順テーブル行数: {len(rows)}")
                        
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                step_number = cells[0].get_text(strip=True)
                                step_text = cells[-1].get_text(strip=True)
                                print(f"手順候補: {step_number} - {step_text[:30]}...")
                                
                                # 有効な手順データかチェック
                                if (step_text and step_number.isdigit() and 
                                    step_text != '手順' and len(step_text) > 5):
                                    # 手順番号付きでテキストを作成
                                    formatted_step = f"{step_number}: {step_text}"
                                    
                                    # セクションタイプに応じて格納先を決定
                                    if section_type == "modern_recipe":
                                        recipe_data['modern_recipe']['modern_instructions'].append(formatted_step)
                                        print(f"✓ 現代レシピ手順を追加: {formatted_step[:50]}...")
                                    elif section_type == "modern_translation":
                                        recipe_data['modern_translation_instructions'].append(formatted_step)
                                        print(f"✓ 現代語訳手順を追加: {formatted_step[:50]}...")
                                    elif section_type == "original":
                                        recipe_data['original_instructions'].append(formatted_step)
                                        print(f"✓ 翻刻テキスト手順を追加: {formatted_step[:50]}...")
                        break
                    elif next_element.name in ['h3', 'h4']:
                        # 別のヘッダーに到達したら終了
                        break
                    next_element = next_element.find_next_sibling()
                break
            current = current.find_next_sibling()

    def _extract_flexible_content(self, soup, recipe_data):
        """柔軟なアプローチでコンテンツを抽出"""
        # 全てのテキストコンテンツを取得
        all_text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        
        # パターンマッチングで情報を抽出
        current_section = ""
        
        for i, line in enumerate(lines):
            # セクションヘッダーを識別
            if any(keyword in line for keyword in ['翻刻テキスト', '原文', '古文']):
                current_section = "original"
            elif any(keyword in line for keyword in ['現代語訳', '現代語']):
                current_section = "translation"
            elif any(keyword in line for keyword in ['現代レシピ', 'レシピ']):
                current_section = "recipe"
            elif any(keyword in line for keyword in ['材料']):
                current_section = "ingredients"
            elif any(keyword in line for keyword in ['作り方', '手順']):
                current_section = "instructions"
            elif any(keyword in line for keyword in ['使い方', '用途']):
                current_section = "usage"
            
            # コンテンツを該当セクションに分類
            if current_section == "original" and not any(keyword in line for keyword in ['翻刻テキスト', '原文']):
                if line.strip():
                    recipe_data['original_text'].append(line.strip())
            
            elif current_section == "translation" and not any(keyword in line for keyword in ['現代語訳', '現代語']):
                if line.strip():
                    recipe_data['modern_translation'].append(line.strip())

    def get_recipe_count(self):
        """レシピ数のみを表示"""
        print("=== レシピ数を確認中 ===")
        recipe_list = self.get_recipe_list()
        if recipe_list:
            print(f"利用可能なレシピ数: {len(recipe_list)} 件")
            return len(recipe_list)
        else:
            print("レシピ一覧の取得に失敗しました")
            return 0
    
    def scrape_single_recipe(self, recipe_number):
        """指定番号の単一レシピを取得"""
        print(f"=== 指定レシピ #{recipe_number} の取得開始 ===")
        
        # レシピ一覧を取得
        recipe_list = self.get_recipe_list()
        
        if not recipe_list:
            print("レシピ一覧の取得に失敗しました")
            return []
        
        # 指定番号のレシピを探す
        target_recipe = None
        for recipe in recipe_list:
            if int(recipe['id']) == recipe_number:
                target_recipe = recipe
                break
        
        if not target_recipe:
            print(f"レシピ #{recipe_number} が見つかりませんでした")
            print(f"利用可能なレシピ番号: 1-{len(recipe_list)}")
            return []
        
        print(f"レシピ '{target_recipe['name']}' を取得中...")
        
        # 単一レシピを取得
        recipe_data = self.scrape_recipe_detail(target_recipe)
        if recipe_data:
            self._print_recipe_summary(recipe_data)
            print(f"\n=== 完了: レシピ #{recipe_number} を取得 ===")
            return [recipe_data]
        else:
            print(f"レシピ #{recipe_number} の取得に失敗しました")
            return []
    
    def scrape_recipes(self, num_recipes=None):
        """指定された数のレシピを取得"""
        print("=== 江戸料理レシピスクレイピング開始 ===")
        
        # レシピ一覧を取得
        recipe_list = self.get_recipe_list()
        
        if not recipe_list:
            print("レシピ一覧の取得に失敗しました")
            return []
        
        # 取得する数を決定
        if num_recipes is None:
            selected_recipes = recipe_list
            print(f"全 {len(recipe_list)} 件のレシピを取得します")
        else:
            selected_recipes = recipe_list[:num_recipes]
            print(f"{len(selected_recipes)} 件のレシピを取得します")
        
        scraped_recipes = []
        for i, recipe_info in enumerate(selected_recipes, 1):
            print(f"\n[{i}/{len(selected_recipes)}] 処理中...")
            
            recipe_data = self.scrape_recipe_detail(recipe_info)
            if recipe_data:
                scraped_recipes.append(recipe_data)
                self._print_recipe_summary(recipe_data)
        
        print(f"\n=== 完了: {len(scraped_recipes)} 件のレシピを取得 ===")
        return scraped_recipes

    def _print_recipe_summary(self, recipe_data):
        """レシピデータの概要を表示"""
        print(f"\n--- レシピ: {recipe_data['name']} ---")
        print(f"ID: {recipe_data['id']}")
        
        if recipe_data['original_text']:
            original_text = '; '.join(recipe_data['original_text']) if isinstance(recipe_data['original_text'], list) else recipe_data['original_text']
            print(f"翻刻テキスト: {original_text[:100]}...")
        
        if recipe_data['modern_translation']:
            modern_text = '; '.join(recipe_data['modern_translation']) if isinstance(recipe_data['modern_translation'], list) else recipe_data['modern_translation']
            print(f"現代語訳: {modern_text[:100]}...")
        
        if recipe_data['modern_recipe']['description']:
            description = '; '.join(recipe_data['modern_recipe']['description']) if isinstance(recipe_data['modern_recipe']['description'], list) else recipe_data['modern_recipe']['description']
            print(f"レシピ説明: {description[:100]}...")
        
        if recipe_data['modern_recipe']['ingredients']:
            print(f"材料数: {len(recipe_data['modern_recipe']['ingredients'])} 個")
        
        if recipe_data['modern_recipe']['modern_instructions']:
            print(f"現代レシピ手順数: {len(recipe_data['modern_recipe']['modern_instructions'])} ステップ")
        
        if recipe_data['modern_translation_instructions']:
            print(f"現代語訳手順数: {len(recipe_data['modern_translation_instructions'])} ステップ")
        
        if recipe_data['original_instructions']:
            print(f"翻刻テキスト手順数: {len(recipe_data['original_instructions'])} ステップ")

    def save_to_json(self, recipes, filename='edo_recipes.json'):
        """レシピデータをJSONファイルに保存"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            print(f"\nデータを {filename} に保存しました")
        except Exception as e:
            print(f"ファイル保存に失敗: {e}")

    def save_to_csv(self, recipes, filename='edo_recipes.csv'):
        """レシピデータをCSVファイルに保存"""
        try:
            # フラット化されたデータを作成
            flattened_data = []
            for recipe in recipes:
                flat_recipe = {
                    'id': recipe['id'],
                    'name': recipe['name'],
                    'url': recipe['url'],
                    'original_text': '; '.join(recipe['original_text']) if isinstance(recipe['original_text'], list) else recipe['original_text'],
                    'modern_translation': '; '.join(recipe['modern_translation']) if isinstance(recipe['modern_translation'], list) else recipe['modern_translation'],
                    'recipe_description': '; '.join(recipe['modern_recipe']['description']) if isinstance(recipe['modern_recipe']['description'], list) else recipe['modern_recipe']['description'],
                    'ingredients_count': len(recipe['modern_recipe']['ingredients']),
                    'ingredients': '; '.join(recipe['modern_recipe']['ingredients']),
                    'modern_instructions_count': len(recipe['modern_recipe']['modern_instructions']),
                    'modern_instructions': '; '.join(recipe['modern_recipe']['modern_instructions']),
                    'modern_translation_instructions_count': len(recipe['modern_translation_instructions']),
                    'modern_translation_instructions': '; '.join(recipe['modern_translation_instructions']),
                    'original_instructions_count': len(recipe['original_instructions']),
                    'original_instructions': '; '.join(recipe['original_instructions']),
                    'tips': recipe['modern_recipe']['tips']
                }
                flattened_data.append(flat_recipe)
            
            df = pd.DataFrame(flattened_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"データを {filename} に保存しました")
            
        except Exception as e:
            print(f"CSV保存に失敗: {e}")

def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description='江戸料理レシピスクレイピングツール')
    
    parser.add_argument('--count-only', action='store_true', default=False,
                      help='レシピ数のみを表示して終了')
    parser.add_argument('--num-recipes', type=int, default=5,
                      help='取得するレシピ数を指定（デフォルト: 5、0で全件取得）')
    parser.add_argument('--get-recipe', type=int, default=None,
                      help='指定番号のレシピのみを取得（--num-recipesとは同時指定不可）')
    parser.add_argument('--sleep-time', type=float, default=1.0,
                      help='HTTP取得前のスリープ時間（秒、デフォルト: 1.0）')
    parser.add_argument('--output', type=str, default='edo_recipes',
                      help='出力ファイル名のベース（デフォルト: edo_recipes）')
    
    args = parser.parse_args()
    
    # --get-recipe と --num-recipes の排他制御
    if args.get_recipe is not None and args.num_recipes != 5:
        parser.error("--get-recipe と --num-recipes は同時に指定できません")
    
    return args

def main():
    """メイン実行関数"""
    args = parse_arguments()
    
    # スクレイパーを初期化
    scraper = EdoRecipeScraper(sleep_time=args.sleep_time)
    
    # レシピ数のみ表示して終了
    if args.count_only:
        scraper.get_recipe_count()
        return
    
    # 指定番号のレシピのみ取得
    if args.get_recipe is not None:
        recipes = scraper.scrape_single_recipe(args.get_recipe)
    else:
        # レシピを取得（0が指定された場合は全件取得）
        num_recipes = None if args.num_recipes == 0 else args.num_recipes
        recipes = scraper.scrape_recipes(num_recipes=num_recipes)
    
    if recipes:
        # 詳細分析
        print("\n" + "="*50)
        print("取得データの詳細分析")
        print("="*50)
        
        for recipe in recipes:
            print(f"\n【{recipe['name']}】")
            print(f"データの種類:")
            print(f"  - 翻刻テキスト: {'✓' if recipe['original_text'] else '✗'}")
            print(f"  - 現代語訳: {'✓' if recipe['modern_translation'] else '✗'}")
            print(f"  - 現代レシピ: {'✓' if recipe['modern_recipe']['description'] else '✗'}")
            print(f"  - 材料情報: {len(recipe['modern_recipe']['ingredients'])} 個")
            print(f"  - 現代レシピ手順: {len(recipe['modern_recipe']['modern_instructions'])} ステップ")
            print(f"  - 現代語訳手順: {len(recipe['modern_translation_instructions'])} ステップ")
            print(f"  - 翻刻テキスト手順: {len(recipe['original_instructions'])} ステップ")
            
            # 実際のコンテンツのサンプル表示
            if recipe['original_text']:
                original_text = '; '.join(recipe['original_text']) if isinstance(recipe['original_text'], list) else recipe['original_text']
                print(f"\n翻刻テキスト（抜粋）:")
                print(f"  {original_text[:150]}...")
            
            if recipe['modern_translation']:
                modern_text = '; '.join(recipe['modern_translation']) if isinstance(recipe['modern_translation'], list) else recipe['modern_translation']
                print(f"\n現代語訳（抜粋）:")
                print(f"  {modern_text[:150]}...")
        
        # データをファイルに保存
        json_filename = f"{args.output}.json"
        csv_filename = f"{args.output}.csv"
        scraper.save_to_json(recipes, json_filename)
        scraper.save_to_csv(recipes, csv_filename)
        
        print(f"\n✅ 正常に {len(recipes)} 件のレシピデータを取得・保存しました")
        print(f"   出力ファイル: {json_filename}, {csv_filename}")
    else:
        print("❌ レシピデータの取得に失敗しました")

if __name__ == "__main__":
    main()
