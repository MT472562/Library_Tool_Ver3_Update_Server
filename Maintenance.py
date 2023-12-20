import os
import shutil
import sqlite3
import sys
import time
import datetime

def main():
    # Maintenance関数統括関数
    backup()
    file_cleanup("ics")
    file_cleanup("img")
    file_cleanup("inventory")
    file_cleanup("logs")
    log_data_management()
    time.sleep(1)
    print("-" * 30)
    print("すべての処理を終了")



def loading_animation():
    chars = "/—\\|"
    for char in chars:
        sys.stdout.write('\r' + f'実行中... {char}')
        sys.stdout.flush()
        time.sleep(1)


def file_cleanup(folder_path):
    # 使用例
    loading_animation()
    # 引数ののファイルをクリーンアンプする関数
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"フォルダ '{folder_path}' を作成→◎")
    else:
        print(f"フォルダ '{folder_path}' を確認→◎")
    loading_animation()
    shutil.rmtree(folder_path)
    os.makedirs(folder_path)
    print(f"フォルダ '{folder_path}' をクリーンアップ→◎")


def log_data_management():
    import datetime
    now = datetime.datetime.now()
    now = now.strftime("%Y/%m/%d %H:%M:%S")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    data_type = 1
    interval = datetime.timedelta(days=30)
    target_date = datetime.datetime.now() - interval
    delete_query = f"DELETE FROM log WHERE level = {data_type} AND time <= ?;"
    loading_animation()
    try:
        cursor.execute(delete_query, (target_date.strftime("%Y/%m/%d %H:%M:%S"),))
        conn.commit()
        print("level1のログデータで30日以上前のものを削除→◎")
    except sqlite3.Error as e:
        pass
    data_type = 2
    interval = datetime.timedelta(days=365)
    target_date = datetime.datetime.now() - interval
    delete_query = f"DELETE FROM log WHERE level = {data_type} AND time <= ?;"
    loading_animation()
    try:
        cursor.execute(delete_query, (target_date.strftime("%Y/%m/%d %H:%M:%S"),))
        conn.commit()
        print("level2のログデータで365日以上前のものを削除→◎")
    except sqlite3.Error as e:
        pass
    conn.close()

def backup():
    now = datetime.datetime.now()
    now = now.strftime("%Y-%m-%d_%H-%M-%S")
    original_db_path = "database.db"
    backup_db_path = f"backup/{now}_backup_data.db"
    original_db_path_inventory = "inventoryDatabase.db"
    backup_db_path_inventory = f"backup/{now}_backup_data_inventory.db"
    try:
        shutil.copy2(original_db_path, backup_db_path)
        shutil.copy2(original_db_path_inventory, backup_db_path_inventory)
        print('データベースのバックアップ終了→◎')

    except FileNotFoundError:
        print('データベースファイルが不明')

    except Exception as e:
        print(f'Error: {e}')
        exit()

if __name__ == "__main__":
    response = input("Maintenanceを開始すると以下の操作が行われます。\n----------------------------\n"
                     "データベースのフルバックアップ\n"
                     "icsファイルの初期化\n"
                     "imgファイルの初期化\n"
                     "inventoryファイルの初期化\n"
                     "logsファイルの初期化\n"
                     "----------------------------\n"
                     "Maintenanceをほんとに開始しますか？ (y/n): ")

    if response.lower() == 'y':
        loading_animation()
        print("Maintenanceを開始中...")
        print("-----|||||||途中で停止する場合はControlキーを押しながらCを押してください|||||||-----")
        main()
    elif response.lower() == 'n':
        print("Maintenanceを中止")
        exit()
    else:
        print("yまたはnを入力してください")
        exit()
