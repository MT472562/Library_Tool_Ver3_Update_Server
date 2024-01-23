import sqlite3

from main import mail_post_on_file

DATABASE = "database.db"


def return_mail_post_today():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sql = "SELECT * FROM send_email WHERE scheduled = ?"
    params = (today,)
    cursor.execute(sql, params)
    result = cursor.fetchall()
    conn.close()
    if len(result) == 0:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "UPDATE send_email SET execution = TRUE WHERE scheduled = ?"
        cursor.execute(sql, (today,))
        conn.commit()
        conn.close()
        return
    elif result[0][2] == 0:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        import datetime
        now = datetime.datetime.now()
        now = now - datetime.timedelta(days=7)
        date = now.strftime('%Y/%m/%d')
        sql = "SELECT * FROM rental WHERE rental_date = ? AND rental_status = 1"
        cursor.execute(sql, (date,))
        result = cursor.fetchall()
        conn.close()
        ids = []
        for num in range(len(result)):
            ids.append(result[num][2])
        ids = list(set(ids))
        for num in range(len(ids)):  # 貸出データ処理
            rental_code = ids[num]
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row  # row_factoryの設定をクエリ実行の前に行う
            sql = "SELECT * FROM rental WHERE rental_id = ?"
            cursor.execute(sql, (rental_code,))
            result = cursor.fetchall()
            conn.close()
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            user_sql = "SELECT * FROM users WHERE id = ?"
            cursor.execute(user_sql, (result[0][3],))
            user_result = cursor.fetchall()
            user_mail_address = user_result[0][5]
            user_name = user_result[0][3]
            conn.close()
            book_list = []
            title_list = []
            for num in range(len(result)):  # 個別メール送信処理
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                conn.row_factory = sqlite3.Row
                book_sql = "SELECT * FROM book WHERE management_code = ?"
                cursor.execute(book_sql, (result[num][4],))
                book_result = cursor.fetchall()
                book_list.append(result[num][4])
                title_list.append(book_result[0][4])
                conn.close()

                title = "【図書管理システム】本の返却日になりました"
                mail_text = f"返却期限のお知らせ\n\n" \
                            f"{user_name}様\n\n" \
                            "図書管理システムをご利用いただきありがとうございます。\n" \
                            "お客様のアカウントで貸し出された本の返却日は本日です。\n" \
                            "返却対象の本は以下の本です。\n\n"

                for num in range(len(book_list)):
                    mail_text = mail_text + f"・{title_list[num]} <{book_list[num]}>\n"

                mail_text = mail_text + "\n返却する際は、返却ページの入力欄に返却IDを入力するか、QRコードを読み込んでください。\n" \
                                        f"\n返却コード\n《{rental_code}》\n" \
                                        "返却期日を過ぎている場合、図書委員会からお声がけさせて頂く場合があります。\n\n" \
                                        "図書管理システムのご利用に際して不明な点やお困りのことがございましたら、\n" \
                                        "いつでもサポートチームまでお問い合わせください。\n\n" \
                                        "図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"

                file_name = f"img/{rental_code}.png"
                file_path = [file_name]
                mail_post_on_file(mail_text, user_mail_address, title, file_path)


def delayed_return():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sql = "SELECT * FROM send_email WHERE scheduled = ?"
    params = (today,)
    cursor.execute(sql, params)
    result = cursor.fetchall()
    conn.close()
    if len(result) == 0:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "UPDATE send_email SET execution = TRUE WHERE scheduled = ?"
        cursor.execute(sql, (today,))
        conn.commit()
        conn.close()
        return
    elif result[0][2] == 0:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        import datetime
        now = datetime.datetime.now()
        now = now - datetime.timedelta(days=8)
        date = now.strftime('%Y/%m/%d')
        sql = "SELECT * FROM rental WHERE rental_date <= ? AND rental_status = 1"
        cursor.execute(sql, (date,))
        result = cursor.fetchall()
        conn.close()
        ids = []
        for num in range(len(result)):
            ids.append(result[num][2])
        ids = list(set(ids))
        for num in range(len(ids)):
            rental_code = ids[num]
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM rental WHERE rental_id = ?"
            cursor.execute(sql, (rental_code,))
            result = cursor.fetchall()
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            user_sql = "SELECT * FROM users WHERE id = ?"
            cursor.execute(user_sql, (result[0][3],))
            user_result = cursor.fetchall()
            user_mail_address = user_result[0][5]
            user_name = user_result[0][3]
            conn.close()
            book_list = []
            title_list = []
            real_list = []
            for num in range(len(result)):  # 個別メール送信処理
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                conn.row_factory = sqlite3.Row
                book_sql = "SELECT * FROM book WHERE management_code = ?"
                cursor.execute(book_sql, (result[num][4],))
                book_result = cursor.fetchall()
                book_list.append(result[num][4])
                title_list.append(book_result[0][4])
                real_list.append(book_result[0][5])
                conn.close()
                title = "【重要】【図書管理システム】本の返却日が過ぎています"
                mail_text = f"返却期限超過のお知らせ\n\n" \
                            f"{user_name}様\n\n" \
                            "図書管理システムをご利用いただきありがとうございます。\n" \
                            "お客様のアカウントで貸し出された以下の本が返却期限を過ぎています。\n" \
                            "以下の本を速やかに返却をするようにしてください。\n" \
                            "返却対象の本は以下の本です。\n\n"

                for num in range(len(book_list)):
                    mail_text = mail_text + f"・{title_list[num]} <{book_list[num]}>\n"

                mail_text = mail_text + "\n返却する際は、返却ページの入力欄に返却IDを入力するか、QRコードを読み込んでください。\n" \
                                        f"\n返却コード\n《{rental_code}》\n" \
                                        "今後も返却期日を過ぎている場合、図書委員会からお声がけさせて頂く場合がありますので了承ください。\n\n" \
                                        "図書管理システムのご利用に際して不明な点やお困りのことがございましたら、\n" \
                                        "いつでもサポートチームまでお問い合わせください。\n\n" \
                                        "図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"

                file_name = f"img/{rental_code}.png"
                file_path = [file_name]
                print("メール送信")
                mail_post_on_file(mail_text, user_mail_address, title, file_path)


def new_date_in():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    sql = "SELECT * FROM send_email"
    cursor.execute(sql)
    result = cursor.fetchall()
    ck = False
    for num in range(len(result)):
        if result[num][1] == today:
            ck = True
        else:
            pass
    if ck == False:
        sql = "INSERT INTO send_email (scheduled,execution) VALUES (?,FALSE)"
        cursor.execute(sql, (today,))
        conn.commit()
        conn.close()


def end_task():
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    sql = "UPDATE send_email SET execution = TRUE WHERE scheduled = ?"
    cursor.execute(sql, (today,))
    conn.commit()
    conn.close()
    return


new_date_in()
return_mail_post_today()
delayed_return()
end_task()
