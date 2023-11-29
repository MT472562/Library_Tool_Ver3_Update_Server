import sqlite3


def reset_autoincrement_and_delete(database_path, table_name, column_name, value):
    # SQLiteデータベースに接続
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    try:
        # 行の削除
        cursor.execute(f"DELETE FROM {table_name} WHERE {column_name} = ?", (value,))

        connection.commit()

        # データベースの再構築（自動生成されたIDをリセット）
        cursor.execute("VACUUM")

        # コミットして変更を確定
        connection.commit()
    except Exception as e:
        print(f"エラー: {e}")
    finally:
        # 接続を閉じる
        connection.close()


# 使用例
database_path = "database.db"
table_name = "users"
column_name = "id"
value_to_delete = 0
confirmation = input("本当に実行しますか？ (yes/no): ")
if confirmation.lower() == "yes":
    if confirmation.lower() == "yes":
        confirmation = input("この操作を実行するとdatabaseの破壊につながる可能性があります。本当によろしいですか？")
        if confirmation.lower() == "yes":
            confirmation = input(
                "最終確認！！！！本当に実行してもよろしいですか？この操作はデータベースを破壊する可能性があります。")
            reset_autoincrement_and_delete(database_path, table_name, column_name, value_to_delete)
        else:
            print("中止します")
    else:
        print("中止します")
else:
    print("中止します")


