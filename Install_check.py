# Install_check モジュールの修正
import os
import sys
import time

def loading_animation():
    chars = "/—\\|"
    for char in chars:
        sys.stdout.write('\r' + f'実行中... {char}')
        sys.stdout.flush()
        time.sleep(0.5)

def file_check_and_create(folder_path):
    loading_animation()
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Result...|フォルダ '{folder_path}' を作成")
        return True
    else:
        print(f"Result...フォルダ '{folder_path}' を確認")
        return True

def file_check(folder_path):
    loading_animation()
    if not os.path.exists(folder_path):
        print(f"Result...|フォルダ '{folder_path}' が確認できませんでした")
        return False
    else:
        print(f"Result...フォルダ '{folder_path}' を確認")
        return True

def main():
    total_check = []
    file_check_and_create_list = ["ics", "img", "inventory", "logs", "backup", "templates", "templates/resources",
                                  "templates/resources/css", "templates/resources/svgs"]
    for num in file_check_and_create_list:
        res = file_check_and_create(num)
        total_check.append(["file_check_and_create_list", num, res])

    file_check_list = ["main.py", "database.db", "inventoryDatabase.db", "token.json", "Maintenance.py","update_module.py",
                       "client_secret.json"]
    for num in file_check_list:
        res = file_check(num)
        total_check.append(["file_check_list", num, res])

    total = True
    print("実行結果" + "-" * 50)
    for num in total_check:
        if num[0] == "file_check_and_create_list" and num[2]:
            pass
        elif num[0] == "file_check_and_create_list" and not num[2]:
            print(f"{num[1]}のファイルが見つからず、作成を試みましたが失敗しました...")
            total = False
        elif num[0] == "file_check_list" and num[2]:
            pass
        elif num[0] == "file_check_list" and not num[2]:
            print(f"{num[1]}のファイルが見つからず、またはファイルは自動生成不可のファイルです...")
            total = False

    if total:
        print("【問題なし】")
        print("すべての必要なファイルの確認を完了しました....\nこれでシステムを使用することができます...")
    else:
        print("【問題あり】")
        print("↑↑↑↑↑↑↑↑\nシステムの構成に問題があります....\n上記のエラーを解決してエラーが出ないようにしてください...")

if __name__ == '__main__':
    main()
