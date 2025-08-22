"""タスク管理デモアプリケーション

TaskManagerクラスを使用してCRUD操作のデモを実行します。
"""

from common.database_config import DatabaseConfig
from common.task_manager import TaskManager


def run_task_demo() -> None:
    """タスク管理のデモを実行"""
    
    # 環境に応じた設定を自動取得
    db_config = DatabaseConfig.from_environment()
    
    # TaskManagerを使用してCRUD操作のデモ
    with TaskManager(db_config) as task_manager:
        print("=== Task Management Demo ===\n")
        
        # タスクの作成
        print("1. Creating tasks...")
        task_id1 = task_manager.create_task(
            "PostgreSQLの学習",
            "基本的なCRUD操作を実装する"
        )
        task_id2 = task_manager.create_task(
            "Dockerの理解",
            "コンテナ技術の基礎を学ぶ"
        )
        
        print()
        
        # 全タスクの読み取り
        print("2. Reading all tasks...")
        all_tasks = task_manager.read_task()
        if all_tasks:
            for task in all_tasks:
                print(f"ID: {task[0]}, Title: {task[1]}, Status: {task[3]}")
        
        print()
        
        # 特定のタスクの更新
        if task_id1:
            print(f"3. Updating task {task_id1}...")
            task_manager.update_task(
                task_id1,
                status="in_progress"
            )
        
        print()
        
        # 更新されたタスクの確認
        if task_id1:
            print("4. Reading updated task...")
            updated_task = task_manager.read_task(task_id1)
            if updated_task and updated_task[0]:
                task = updated_task[0]
                print(f"Updated task - ID: {task[0]}, Title: {task[1]}, Status: {task[3]}")
        
        print()
        
        # タスクの削除（オプション：デモデータを残したい場合はコメントアウト）
        # if task_id1:
        #     print(f"5. Deleting task {task_id1}...")
        #     task_manager.delete_task(task_id1)
        
        # if task_id2:
        #     print(f"6. Deleting task {task_id2}...")
        #     task_manager.delete_task(task_id2)
        
        print("Demo completed successfully!")


if __name__ == "__main__":
    run_task_demo()