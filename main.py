# ライブラリ読み込み
import base64
import binascii
import hashlib
import json
import logging
import math
import os
import random
import re
import secrets
import sqlite3
import string
import threading
import time
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import arrow
import flask
import qrcode
from flask import render_template, url_for, redirect, jsonify, send_file
from flask import request
from flask_httpauth import HTTPDigestAuth
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pyngrok import ngrok, conf

import Maintenance
import update_module
from ics import Calendar, Event
today = datetime.now()
logging.basicConfig(filename=f'logs/{today.strftime("%Y-%m-%d")}.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)
one_week_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d.log')

files = os.listdir('./logs')
for file in files:
    if one_week_ago > file:
        os.remove(f"logs/{file}")
    else:
        pass
# ログメッセージの出力例の提示
logging.debug('This is a debug message')
logging.info('This is an info message')
logging.warning('This is a warning message')
logging.error('This is an error message')
logging.critical('This is a critical message')

# Flaskの設定
app = flask.Flask(__name__, static_folder='./templates/resources')
app.config['SECRET_KEY'] = secrets.token_urlsafe(128)
app.config['SESSION_TYPE'] = 'filesystem'
RESET_PASSWORD_EXPIRATION = 3600
DATABASE = "database.db"
INVENTORY_DATABASE = "inventoryDatabase.db"
tokens = {}
auth = None
auth = HTTPDigestAuth()
with open("digest.json", 'r') as file:
    data = json.load(file)
users = {
    data["userid"]:data["password"]
}


@auth.get_password
def get_pw(username):
    if username in users:
        return users.get(username)
    return None


@app.route("/test")
def test():
    return render_template("code.html")


# 引数で入力されたファイルを削除する関数
def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            insert_log("ファイルの削除", "2",
                       f"システム処理で次のファイルが削除されました。\n{file_path}", "delete_file()",
                       "System")
        else:
            pass
    except Exception as e:
        insert_log("ファイルの削除に失敗しました", "2",
                   f"システム処理で次のファイルの削除に失敗しました。。\n{file_path}\n{e}", "delete_file()",
                   "System")


@app.route("/MaintenanceRun", methods=['POST'])
@auth.login_required
def MaintenanceRun():
    if flask.session['access_level'] in [5]:
        Maintenance.main()
        insert_log("メンテナンスの実行", "3",
                   f"メンテナンス処理が実行されました。", "MaintenanceRun()",
                   f"{flask.session['userid']}")

        return redirect("/setting")

    else:
        return ERROR(16)


@app.route("/install_setup_python_on_run")
def install_setup_python_on_run():
    import Install_check
    Install_check.main()
    return redirect("/")


# System用のログを保存する関数
def insert_log(type, level, msg, function, user):

    try:
        date = time.strftime("%Y/%m/%d %H:%M:%S")
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO log (type,time,function,level,msg,userid) VALUES (?,?,?,?,?,?)",
                  (type, date, function, level, msg, user))
        conn.commit()
    except:
        date = time.strftime("%Y/%m/%d %H:%M:%S")
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO log (type,time,function,level,msg,userid) VALUES (?,?,?,?,?,?)",
                  (type, date, function, level, msg, "System"))
    finally:
        conn.close()


# ランダム英数字を引数で入力された桁数作成
def generate_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


param_query_global = generate_random_string(5)


# 入力された文字列をbase64の形式に変換し返却する関数
def message_base64_encode(message):
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


# 文字列のみのメールを送信する関数
def mail_post(mail_text, mail_to, title):
    scopes = ['https://mail.google.com/']
    creds = Credentials.from_authorized_user_file('token.json', scopes)
    service = build('gmail', 'v1', credentials=creds)
    message = MIMEText(f'{mail_text}')
    message['To'] = f'{mail_to}'
    message['From'] = 'n.s.fukuoka.cp.book@gmail.com'
    message['Subject'] = f'{title}'
    raw = {'raw': message_base64_encode(message)}
    service.users().messages().send(
        userId='me',
        body=raw
    ).execute()
    try:
        insert_log("メールの送信", "1",
                   f"メールアドレス[{mail_to}]に対して[{title}]というメールの送信を行いました。", "mail_post()",
                   f"{flask.session['userid']}")
    except:
        insert_log("メールの送信", "1",
                   f"メールアドレス[{mail_to}]に対して[{title}]というメールの送信を行いました。", "mail_post()",
                   f"未ログイン")


# 引数で入力されたリストのpathをメールに添付して送信する関数
def mail_post_on_file(mail_text, mail_to, title, attachment_paths):
    scopes = ['https://mail.google.com/']
    creds = Credentials.from_authorized_user_file('token.json', scopes)
    service = build('gmail', 'v1', credentials=creds)
    message = MIMEMultipart()
    message['To'] = mail_to
    message['From'] = 'n.s.fukuoka.cp.book@gmail.com'
    message['Subject'] = title
    body = MIMEText(mail_text)
    message.attach(body)
    for attachment_path in attachment_paths:
        attachment = MIMEBase('application', 'octet-stream')
        with open(attachment_path, 'rb') as file:
            attachment.set_payload(file.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment_path)}"')
        message.attach(attachment)
    raw = {'raw': message_base64_encode(message)}
    service.users().messages().send(userId='me', body=raw).execute()
    try:
        insert_log("ファイル付きメールの送信", "1",
                   f"メールアドレス[{mail_to}]に対して[{title}]というファイル付きメールの送信を行いました。送信したファイル一覧はこちらです{attachment_paths}",
                   "mail_post_on_file()",
                   f"{flask.session['userid']}")
    except:
        insert_log("ファイル付きメールの送信", "1",
                   f"メールアドレス[{mail_to}]に対して[{title}]というファイル付きメールの送信を行いました。送信したファイル一覧はこちらです{attachment_paths}",
                   "mail_post_on_file()",
                   f"未ログイン")


# 引数で入力された数値をErrorTableからErrorIDを元にエラーページにリダイレクトする
def ERROR(error_db_id):
    con = sqlite3.connect(DATABASE)
    error_db = con.execute(
        "SELECT error_id,error_msg FROM error WHERE id LIKE ?",
        (error_db_id,))
    result = error_db.fetchall()
    errorid = result[0][0]
    msg = result[0][1]
    con.close()
    insert_log("エラー", "2", f"{errorid}|{msg}",
               "ERROR()", "System")
    return render_template("axesserror.html",
                           msg=msg,
                           errorid=errorid)


# BookTableの一覧を返却する関数
def book_database():
    con = sqlite3.connect(DATABASE)
    db_book = con.execute("SELECT * FROM book").fetchall()
    con.close()
    return db_book


# .icsファイルを生成してidを返却する関数
def Create_Calendar(START_DATE, END_DATE, EVENT_NAME, EVENT_LOCATION, EVENT_DESCRIPTION, file_id):
    cal = Calendar()
    event = Event()
    event.name = EVENT_NAME
    event.begin = arrow.get(START_DATE, "YYYY-MM-DD HH:mm:ss").replace(tzinfo="Asia/Tokyo")
    event.end = arrow.get(END_DATE, "YYYY-MM-DD HH:mm:ss").replace(tzinfo="Asia/Tokyo")
    event.location = EVENT_LOCATION
    event.description = EVENT_DESCRIPTION
    cal.events.add(event)
    with open(file_id, "w") as file:
        file.writelines(cal)
    return file_id


# ユーザーIDとpoint数(-を含む)でオペレーションする関数
def point_operation(user_id, point_, operation):
    if flask.session["point"] == None:
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("UPDATE users SET point = point + ? WHERE userid = ? ;", (0, user_id))
        flask.session['point'] = 0
        con.commit()
        con.close()
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    if operation == "add":
        cur.execute("UPDATE users SET point = point + ? WHERE userid = ? ;", (point_, user_id))
        flask.session['point'] = flask.session['point'] + point_
    elif operation == "sub":
        cur.execute("UPDATE users SET point = point - ? WHERE userid = ? ", (point_, user_id))
        flask.session['point'] = flask.session['point'] - point_
    else:
        pass
    con.commit()
    con.close()


@app.route("/")
def index():
    if 'userid' in flask.session:
        st = {"st": "True"}
    else:
        st = {"st": "False"}

    db_book = book_database()
    i = 1
    img_url = []
    links = []
    codes = []
    for num in range(3):
        url = db_book[-i][7]
        code = db_book[-i][0]
        codes.append(code)
        link = "https://www.google.com/search?q=" + db_book[-i][1]
        links.append(link)

        i = i + 1
        img_url.append(url)
    return render_template('index.html',
                           url=img_url,
                           links=links,
                           st=st,
                           codes=codes,
                           page_name="トップページ--")


@app.route("/cat")
def cat():
    return render_template("cat.html")


@app.route("/account")
def account():
    msg = request.args.get('msg')
    re_url = request.args.get('re_url')
    if 'userid' in flask.session:
        return render_template('account.html', page_name="マイページ--")
    elif msg is not None:
        return render_template('redirect_login.html',
                               operation=msg, redirect_url=re_url)
    else:
        return render_template('login.html', page_name="ログインページ--")


@app.route("/login", methods=['POST'])
def login():
    login_data = request.get_json()
    userid = login_data['userid']
    password = login_data['password']
    redirect_url = login_data['redirect']
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE userid = ? ", (userid,))
    salt_db = c.fetchone()
    if salt_db is None:
        res = {"url": redirect_url, "msg": "ユーザーIDまたはパスワードが間違っています。", "st": "False"}
        return jsonify(res=res)
    password = str(password) + str(salt_db["salt"])
    if str(salt_db["salt"]) == "":
        res = {"url": redirect_url, "msg": "パスワードの入力試行回数が既定値をオーバーしました"
                                           "<br>アカウントを復元するためにはパスワードのリセットが必要です。<br>"
                                           "<a href='/reset_account'>こちら</a>からパスワードのリセットを行ってください。",
               "st": "False"}
        return jsonify(res=res)
    else:
        pass

    password = hashlib.sha512(password.encode()).hexdigest()
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE userid = ? AND password = ?", (userid, password,))
    db_userid = c.fetchone()
    conn.close()

    if db_userid is not None and db_userid['password'] == password:
        flask.session['userid'] = userid
        flask.session['access_level'] = db_userid['access_level']
        flask.session['username'] = db_userid['username']
        flask.session['mail'] = db_userid['mail']
        flask.session['point'] = db_userid['point']
        flask.session['id'] = db_userid['id']
        insert_log("ログイン", "1", "次のユーザーがログインしました。", "login()", f"{flask.session['userid']}")
        res = {"url": redirect_url, "msg": f"{flask.session['username']}さんようこそ！\nログイン完了しました",
               "st": "True"}
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        update_query = "UPDATE users SET login_failures = ? WHERE userid = ?"
        new_value = 0
        cursor.execute(update_query, (new_value, userid,))
        conn.commit()
        conn.close()
        return jsonify(res=res)
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        login_failures_query = "SELECT login_failures FROM users WHERE userid = ?"
        cursor.execute(login_failures_query, (userid,))
        result = cursor.fetchone()
        login_failures_query = result[0]
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        update_query = "UPDATE users SET login_failures = ? WHERE userid = ?"
        new_value = login_failures_query + 1
        cursor.execute(update_query, (new_value, userid))
        conn.commit()
        conn.close()

        if login_failures_query >= 4:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            update_query = "UPDATE users SET salt = ? WHERE userid = ?"
            cursor.execute(update_query, ("", userid,))
            conn.commit()
            conn.close()

        # res = {"url": redirect_url, "msg": "ユーザーIDまたはパスワードが間違っています。", "st": "False"}
        res = {"url": redirect_url, "msg": "パスワードが間違っています。", "st": "False"}
        return jsonify(res=res)


@app.route('/logout')
def logout():
    if 'userid' not in flask.session:
        # ログインしていない場合はログインページにリダイレクト
        return redirect('/login')

    # ログアウトする前にログ情報を記録
    insert_log("ログアウト", "1", "次のユーザーがログアウトしました。", "logout()", f"{flask.session['userid']}")

    # セッションデータをクリア
    flask.session.pop('userid', None)
    flask.session.pop('username', None)
    flask.session.pop('access_level', None)
    flask.session.pop('mail', None)

    return redirect(url_for('account'))


@app.route("/account_edit")
def account_edit():
    if 'access_level' not in flask.session:
        return render_template("redirect_login.html",
                               operation="アカウントの情報編集はログインが必要です。ログインをしてください。",
                               redirect_url="/account_edit")

    return render_template('account_edit.html', page_name="アカウント編集ページ--")


def edit_account_set_data(sql, prams):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(sql, prams)
    conn.commit()
    conn.close()


def contains_special_characters(text):
    import re
    pattern = re.compile(r'[ぁ-んァ-ン一-龥]')
    return bool(pattern.search(text))


def contains_fullwidth_characters(input_str):
    import re
    pattern = r'[^\x01-\x7E\xA1-\xDF]'  # 正規表現パターン：ASCII以外の文字（全角文字や全角数字）にマッチ
    return bool(re.search(pattern, input_str))


@app.route("/account_edit_post", methods=['POST'])
def account_edit_post():
    data = request.get_json()
    val_list = ["username", "userid", "mail", "password", "access_level"]
    type = data['val']
    if type in ["0", 0]:
        if data["after_data"] == "":
            res = {"msg": "空白のユーザー名は使用できません。", "st": "False"}
            return jsonify(res_data=res)
        val = val_list[0]
        sql = "UPDATE users SET username = ? WHERE userid = ?"
        prams = (data["after_data"], flask.session["userid"])
        edit_account_set_data(sql, prams)
        flask.session['username'] = data["after_data"]
    elif type in ["1", 1]:
        if data["after_data"] == "":
            res = {"msg": "空白のユーザーIDは使用できません。", "st": "False"}
            return jsonify(res_data=res)
        val = val_list[1]
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE userid = ?", (data["after_data"],))
        db_userid_ck = c.fetchone()
        conn.close()
        result = contains_special_characters(data["after_data"])
        result2 = contains_fullwidth_characters(data["after_data"])
        if result and result2:
            res = {"msg": "ユーザーIDには半角英数字のみ使用できます。", "st": "False"}
            return jsonify(res_data=res)
        if db_userid_ck is None:
            sql = "UPDATE users SET userid = ? WHERE userid = ?"
            prams = (data["after_data"], flask.session["userid"])
            edit_account_set_data(sql, prams)
            flask.session['userid'] = data["after_data"]
        else:
            res = {"msg": "そのユーザーIDは既に使用されています。\n別のユーザーIDを使用してください", "st": "False"}
            return jsonify(res_data=res)

    elif type in ["2", 2]:

        val = val_list[2]
        sql = "UPDATE users SET mail = ? WHERE userid = ?"
        prams = (data["after_data"], flask.session["userid"])
        edit_account_set_data(sql, prams)
        flask.session['mail'] = data["after_data"]
    elif type in ["3", 3]:
        val = val_list[3]
        if data["after_data"] == "":
            res = {"msg": "空白のパスワードは使用できません。", "st": "False"}
            return jsonify(res_data=res)
        password = hashlib.sha512(data["after_data"].encode()).hexdigest()
        salt = generate_salt(16)
        new_password = str(password) + str(salt)
        password_hash = hashlib.sha512(new_password.encode()).hexdigest()
        sql = "UPDATE users SET password = ? ,salt = ? WHERE userid = ?"
        prams = (password_hash, salt, flask.session["userid"])
        edit_account_set_data(sql, prams)


    elif type in ["4", 4]:
        val = val_list[4]
        input_axesslevel = data["after_data"]
        input_axesslevel = str(input_axesslevel)
        if input_axesslevel == "1" or input_axesslevel == "2":
            sql = "UPDATE users SET access_level = ? WHERE userid = ?"
            prams = (data["after_data"], flask.session["userid"])
            edit_account_set_data(sql, prams)
            flask.session['access_level'] = data["after_data"]
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE userid = ?", (data["userid"],))
            db_data = c.fetchone()
            password_hash = hashlib.sha512(data["password"].encode()).hexdigest()
            salt = db_data["salt"]
            password_hash = str(password_hash) + str(salt)
            password_hash = hashlib.sha512(password_hash.encode()).hexdigest()
            c.execute("SELECT * FROM users WHERE userid = ? AND password = ?", (data["userid"], password_hash,))
            db_userid = c.fetchone()
            conn.close()
            if db_userid is None:
                return jsonify(res_data={"msg": "ユーザーIDかパスワードを使用できません", "st": "False"})
            ck_access_level = db_userid[4]
            ck_access_level = str(ck_access_level)

            if input_axesslevel == "5":
                axesslevelstatus = ck_access_level == "5"
            elif input_axesslevel in ["3", "4"]:
                axesslevelstatus = ck_access_level in ["4", "5"]
            elif input_axesslevel in ["1", "2"]:
                axesslevelstatus = True
            else:
                axesslevelstatus = False
            if not axesslevelstatus:
                return jsonify(res_data={"msg": "ユーザー権限が不足しています。", "st": "False"})
            sql = "UPDATE users SET access_level = ? WHERE userid = ?"
            prams = (data["after_data"], flask.session["userid"])
            edit_account_set_data(sql, prams)
            flask.session['access_level'] = data["after_data"]

    else:
        return jsonify(res_data={"msg": "原因不明のエラーが発生しました。", "st": "False"})

    return jsonify(res_data={"msg": "正常に更新が完了しました\n自動でページのリロードを行います。", "st": "True"})


def is_valid_email(email):
    import re
    # メールアドレスの正規表現パターン
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # 正規表現パターンに一致するかを確認
    if re.match(pattern, email):
        return True
    else:
        return False


@app.route("/account_edit_post_ck_email", methods=['POST'])
def account_edit_post_ck_email():
    random_number = random.randint(100000, 999999)
    random_number_hash = hashlib.sha512(str(random_number).encode()).hexdigest()
    data = request.get_json()
    email = data["email"]
    if data["email"] == "":
        res = {"msg": "空白のメールアドレスは使用できません。", "st": "False"}
        return jsonify(res_data=res)
    if is_valid_email(data["email"]) == False:
        res = {"msg": "このアドレスは無効です。", "st": "False"}
        return jsonify(res_data=res)

    mail_text = f"ご利用のメールアドレスの変更についてのお知らせせ\n\n" \
                f"図書管理システムをご利用いただきありがとうございます。\n" \
                f"ご利用メールアドレスの変更が申請されました。\n" \
                f"以下の６桁の認証コードを申請画面に入力してください\n"
    mail_text = mail_text + "認証コード 【" + str(random_number) + "】\n\n" \
                                                                  f"もしこのメールに心当たりがない場合は、このメッセージを破棄してください。\n\n" \
                                                                  f"図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
    mail_title = "【図書管理システム】ご利用のメールアドレスの変更についてのお知らせ"
    mail_post(mail_text, email, mail_title)

    res_data = {
        "msg": "メールを送信しました。メールに記載されている6桁の数字を入力してください。",
        "st": "True",
        "random_number_hash": random_number_hash,
        "email": email
    }
    return jsonify(res_data=res_data)


@app.route("/reset_account")
def reset_account():
    return render_template('reset.html', page_name="パスワードリセットページ--")


@app.route("/account_id_check", methods=['POST'])
def accout_id_check():
    res = request.get_json()
    email = res['mailaddress']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    query = "SELECT * FROM users WHERE mail = ?"
    c.execute(query, (email,))
    result = c.fetchall()
    if result is None:
        return jsonify({"status": False})
    userids = []

    for row in result:
        userids.append(row[1])
    meil_user_text = ""
    for num in range(len(userids)):
        meil_user_text = meil_user_text + f"・{userids[num]}\n"
    conn.close()
    mail_text = f"ご利用のメールアドレスに紐付けられているユーザーIDのお知らせ\n\n" \
                f"図書管理システムをご利用いただきありがとうございます。\n" \
                f"ご利用メールアドレスに紐づけされているユーザーIDの確認メールです。\n" \
                f"以下のユーザーIDの中にご利用のIDがあれば、そちらを使用して、ログイン・パスワードリセットができます。\n" \
                f"【{email}】のアドレスに紐づけされているあなたのユーザーIDは以下のようになります。\n\n"
    mail_text = mail_text + meil_user_text + "\n\n" \
                                             f"もしこのメールに心当たりがない場合は、このメッセージを破棄してください。\n\n" \
                                             f"図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
    mail_title = "【図書管理システム】ご利用のメールアドレスに紐付けられているユーザーIDのお知らせ"
    mail_post(mail_text, email, mail_title)

    return jsonify({"status": True})


@app.route("/reset_account_check", methods=['POST'])
def reset_account_check():
    res = request.get_json()
    email = res['mailaddress']
    userid = res['userid']
    if email and userid:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        query = "SELECT * FROM users WHERE userid = ?"
        c.execute(query, (userid,))
        result = c.fetchone()
        if result is None:
            status = False
        else:
            if result["mail"] == email:
                import datetime
                status = True
                token = secrets.token_urlsafe(32)
                expiration_time = datetime.datetime.now() + timedelta(seconds=RESET_PASSWORD_EXPIRATION)
                import datetime

                now = datetime.datetime.now()
                timestamp = int(datetime.datetime.timestamp(now))
                one_hour_later = timestamp + 3600
                con = sqlite3.connect(DATABASE)
                con.execute("INSERT INTO reset_hash (hash, deadline,userid,mail,status) VALUES (?,?,?,?,?)",
                            (token, one_hour_later, userid, result["mail"], True))
                con.commit()
                con.close()
                insert_log("パスワードリセットリクエスト", "2", "パスワードのリセットがリクエストされました。",
                           "reset_account_check()",
                           f"{result['username']}")
                one_hour_later = datetime.datetime.fromtimestamp(one_hour_later)
                formatted_datetime = one_hour_later.strftime('%Y-%m-%d %H:%M:%S')

                reset_url = f"{request.host_url}reset_account_new_password?{param_query_global}={token}"
                mail_text = f"パスワードリセットURLのお知らせ\n\n" \
                            f"{result['username']}様\n\n" \
                            f"図書管理システムをご利用いただきありがとうございます。\n" \
                            f"パスワードのリセットを受け付けました。\n" \
                            f"URLのアクセスは、キャンパスのWi-Fi内でないと、利用できません\n" \
                            f"下記のURLをクリックして、新しいパスワードを設定してください。\n\n" \
                            f"パスワードリセットURL:{reset_url}\n" \
                            f"このリンクの有効期限: {formatted_datetime}\n\n" \
                            f"なお、このURLは有効期限が1時間に設定されており、一度のみ有効ですので、ご注意ください。\n" \
                            f"もしこのメールに心当たりがない場合は、このメッセージを破棄してください。\n\n" \
                            f"図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
                mail_title = "【図書管理システム】パスワードリセットURLのお知らせ"
                mail_post(mail_text, result["mail"], mail_title)
            else:
                status = False

        data = {
            "status": status
        }
        conn.close()

    else:
        data = {
            "status": False
        }
    return jsonify(data)


@app.route("/reset_account_new_password", methods=['GET'])
def reset_password():
    query_param = request.args.get(param_query_global)
    if query_param == "" or query_param == None or query_param == False:
        return ERROR(4)
    else:
        import datetime
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        query = "SELECT * FROM reset_hash WHERE hash = ?"
        c.execute(query, (query_param,))
        result = c.fetchone()
        now = datetime.datetime.now()
        timestamp = int(datetime.datetime.timestamp(now))
        c.close()
        if result is None:
            return ERROR(4)
        if result["deadline"] > timestamp:
            if result["status"]:
                return render_template('new_password.html', token=query_param, page_name="新パスワード登録ページ--")
            else:
                return ERROR(6)
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = "UPDATE reset_hash SET status = ? WHERE hash = ?"
            c.execute(query, (False, query_param))
            conn.commit()
            c.close()
            return ERROR(5)


@app.route("/reset_account_new_password_post", methods=['POST'])
def reset_password_post():
    rq = request.get_json()
    token = rq["token"]
    new_password = rq["password"]

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = "SELECT * FROM reset_hash WHERE hash = ?"
    c.execute(query, (token,))
    result = c.fetchone()
    query = "UPDATE reset_hash SET status = ? WHERE hash = ?"
    c.execute(query, (False, token))
    conn.commit()

    c.close()
    if result is None:
        return redirect(ERROR(4))
    elif result["status"] == False:
        return redirect(ERROR(6))
    else:
        user_id = result["userid"]
        salt = generate_salt(16)
        new_password = str(new_password) + str(salt)
        new_password = hashlib.sha512(new_password.encode()).hexdigest()
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        query = "UPDATE users SET password = ? , salt = ? WHERE userid = ?"
        c.execute(query, (new_password, salt, user_id))
        conn.commit()
        c.close()
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        update_query = "UPDATE users SET login_failures = ? WHERE userid = userid"
        new_value = 0
        cursor.execute(update_query, (new_value,))
        conn.commit()
        conn.close()
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        query = "SELECT * FROM users WHERE userid = ?"
        c.execute(query, (user_id,))
        result = c.fetchone()
        c.close()
        conn.close()
        insert_log("パスワードリセット", "2", "パスワードのリセットが実行されました。", "reset_password_post()",
                   f"{result['username']}")
        mail_text = f"パスワード変更のお知らせ\n\n" \
                    f"{result['username']}様\n\n" \
                    f"図書管理システムをご利用いただきありがとうございます。\n" \
                    f"このメールは、パスワード変更のご依頼を受け、パスワードが変更されたことをお知らせいたします。\n" \
                    f"なお、本メールに心当たりのない場合は、お手数ですが速やかに下記問い合わせ先までご連絡ください。\n\n" \
                    f"【パスワード変更の詳細】\n" \
                    f"変更されたアカウントID:{result['userid']}\n\n" \
                    f"図書管理システムのご利用にあたって、不明な点や不具合などございましたら、下記問い合わせ先までお問い合わせください。\n\n" \
                    f"図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
        mail_title = "【図書管理システム】パスワード変更のお知らせ"
        mail_post(mail_text, result["mail"], mail_title)
        logout()

        return redirect("/account", page_name="マイページ--")
    return


@app.route("/new_account")
def create_account():
    return render_template('create_account.html', page_name="アカウント作成ページ--")


@app.route("/user_check", methods=['POST'])
def user_check():
    userid = request.get_json()
    userid = userid["new_id"]
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = "SELECT * FROM users WHERE userid =?"
    c.execute(query, (userid,))
    result = c.fetchone()
    if result is None:
        status = True
    else:
        status = False
    conn.close()

    data = {
        "new_id": userid,
        "status": status
    }
    return jsonify(data)


@app.route("/check_email_and_certification", methods=['POST'])
def check_email_and_certification():
    random_number_hash = ""
    rq = request.get_json()
    certification_id = rq["certification_id"]
    certification_pw_hash = rq["certification_pw_hash"]
    axesslevel = rq["axesslevel"]
    if axesslevel in ["3", "4", "5"]:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        query = "SELECT * FROM users WHERE userid = ?"
        c.execute(query, (certification_id,))
        result = c.fetchone()

        if result:
            db_password = result['password']
            db_accesslevel = result['access_level']
            axesslevelstatus = False
            axesslevel = str(axesslevel)
            db_accesslevel = str(db_accesslevel)
            salt_db = result['salt']
            certification_pw_hash = str(certification_pw_hash) + str(salt_db)
            certification_pw_hash = hashlib.sha512(certification_pw_hash.encode()).hexdigest()
            if certification_pw_hash == db_password:
                if axesslevel == "5":
                    axesslevelstatus = db_accesslevel == "5"
                elif axesslevel == "3" or "4":
                    axesslevelstatus = db_accesslevel == "4" or db_accesslevel == "5"
                else:
                    axesslevelstatus = False
        else:
            axesslevelstatus = False
        conn.close()
    elif axesslevel in ["1", "2"]:
        axesslevelstatus = True
    else:
        axesslevelstatus = False

    if axesslevelstatus:
        rq = request.get_json()
        email_address = rq["email"]
        username = rq["username"]
        insert_log("アカウント作成メール認証依頼", "1", "アカウント作成メール認証依頼のメールが送信されました。",
                   "check_email_and_certification()", f"{username}(仮)")
        random_number = random.randint(100000, 999999)
        random_number_hash = hashlib.sha512(str(random_number).encode()).hexdigest()
        mail_text = f"メールアドレス認証のお願い\n\n" \
                    f"{username}様\n\n" \
                    f"図書管理システムをご利用いただきありがとうございます。\n" \
                    f"アカウント作成時にご登録いただいたメールアドレスが正しいか確認するために、" \
                    f"下記の6桁の数字を登録フォームに入力して認証を完了してください。\n\n" \
                    f"認証コード: 【{random_number}】\n\n" \
                    f"もし、このメールに心当たりがない場合は、このメッセージを破棄してください。\n\n" \
                    f"図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
        mail_title = "【図書管理システム】メールアドレス認証のお願い"
        mail_post(mail_text, email_address, mail_title)
    data = {
        "axess_status": axesslevelstatus,
        "random_hash": random_number_hash

    }
    return jsonify(data)


def generate_salt(length=16):
    return binascii.hexlify(os.urandom(length)).decode('utf-8')


@app.route("/create_account_data_post", methods=['POST'])
def create_account_data_post():
    res = request.get_json()
    mailaddress = res['mailaddress']
    password_hash = res['password_hash']
    userid = res['userid']
    username = res['username']
    axesslevel = res['axesslevel']
    salt = generate_salt(16)
    password_hash = str(password_hash) + str(salt)
    password_hash = hashlib.sha512(password_hash.encode()).hexdigest()
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (userid,username, password, access_level,mail,point,salt,login_failures) VALUES (?, ?, ?, ?, ?,?,?,?)",
        (userid, username, password_hash, axesslevel, mailaddress, 0, salt, 0))
    conn.commit()

    conn.close()
    new_account = {
        "username": username,
        "userid": userid,
        "axesslevel": axesslevel
    }
    insert_log("アカウント作成", "3", "新規アカウントが作成されました。", "create_account_data_post()",
               f"{username}")
    mail_text = f"アカウント登録完了のお知らせ\n\n" \
                f"{username}様\n\n" \
                "この度は図書管理システムをご利用いただきありがとうございます。\n" \
                "お客様のアカウントが正常に登録されましたことをお知らせいたします。\n\n" \
                "以下の情報でアカウントが作成されました。\n" \
                f"ユーザー名: {username}\nユーザーID: {userid}\nアクセスレベル: {axesslevel}\n\n" \
                "図書管理システムのご利用に際して不明な点やお困りのことがございましたら、\n" \
                "いつでもサポートチームまでお問い合わせください。\n\n" \
                "図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
    mail_title = "【図書管理システム】アカウント登録完了のお知らせ"
    mail_post(mail_text, mailaddress, mail_title)

    return jsonify(new_account)


conn = sqlite3.connect(DATABASE)
c = conn.cursor()
c.execute(
    "SELECT book_title FROM book ")
result = c.fetchall()
suggestion_data = []
for row in result:
    title = row[0]  # タプル内の要素を取り出す
    suggestion_data.append(title)
conn.close()


@app.route('/suggest', methods=['GET'])
def suggest():
    query = request.args.get('q', '').lower()
    suggestions = [item for item in suggestion_data if query in item.lower()]
    return jsonify(suggestions)


@app.route("/search", methods=['GET'])
def search():
    search_keyword = request.args.get("k", '')
    pagenumber = request.args.get("p", "")
    if pagenumber == "":
        pagenumber = "1"

    constant_page = 30
    request_page_st = (int(pagenumber) - 1) * constant_page
    request_page_ed = (int(pagenumber) - 1) * constant_page + constant_page
    if search_keyword == "":
        search_keyword = "検索ボックスにキーワードを入力することで絞り込みができます。"
        con = sqlite3.connect(DATABASE)
        query = f"SELECT * FROM book;"
        all_book_len = con.execute(query).fetchall()
        all_book_len = math.ceil(len(all_book_len) / constant_page)
        query = f"SELECT * FROM book LIMIT {request_page_ed - request_page_st} OFFSET {request_page_st};"
        books = con.execute(query).fetchall()
        con.close()
        books_list = []
        i = 0
        for num in books:
            i = i + 1
            data = [num[0], num[3], num[4], num[5], num[2], num[7], num[1]]
            books_list.append(data)
        return render_template('search.html', key=search_keyword, result=books_list, all_book_len=all_book_len,
                               page_name="本検索ページ--")

    def search_normal(search_keyword):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # キーワードを半角・全角のスペースで分割
        keywords = search_keyword.split()  # スペースで分割

        # 各キーワードをANDで結合してクエリを生成
        query = "SELECT management_code, last_rental_date, book_title, author, stock, sample_url, isbn_code FROM book WHERE "
        query += " AND ".join(["book_title LIKE ?" for _ in keywords])  # 各キーワードに対して部分一致検索
        if search_keyword == "$貸出中":
            query += " OR stock = 0"
        elif search_keyword == "$蔵書中":
            query += " OR stock = 1"
        else:
            pass
        query += " ORDER BY management_code DESC"

        # 各キーワードに '%' を追加
        keyword_with_wildcards = ['%' + keyword + '%' for keyword in keywords]

        c.execute(query, keyword_with_wildcards)
        result = c.fetchall()
        conn.close()

        return result

    def search_option(search_keyword):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        keywords = search_keyword.split()  # スペースで分割
        query = "SELECT management_code, last_rental_date, book_title, author, stock, sample_url, isbn_code FROM book WHERE "
        query += " AND ".join(["headline LIKE ? OR management_code LIKE ? OR isbn_code LIKE ?" for _ in keywords])
        query += " ORDER BY management_code DESC"
        keyword_with_wildcards = ['%' + keyword + '%' for keyword in keywords * 3]
        c.execute(query, keyword_with_wildcards)
        result = c.fetchall()
        conn.close()

        return result

    option = request.args.get("o", '')
    if option == "true" or option == "TRUE":
        base = search_normal(search_keyword)
        option_search = search_option(search_keyword)
        for item in option_search:
            if item in base:
                option_search.remove(item)
        base = base + option_search
    else:
        base = search_normal(search_keyword)

    hit_count = len(base)
    base = list(base)
    if hit_count == 0 or hit_count == "0":
        hit = "none"
    else:
        hit = "yes"

    searchquery = search_keyword

    if search_keyword != "":
        search_keyword = "「{0}」の検索結果 {1}件ヒット".format(search_keyword, hit_count)
    else:
        search_keyword = "検索ボックスにキーワードを入力することで絞り込みができます。"

    return render_template('search.html', query=searchquery, key=search_keyword, hit=hit, result=base
                           , page_name="本検索ページ--")


@app.route("/book")
def book():
    query = request.args.get("code", '')
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM book WHERE management_code = ?", (query,))
    result = c.fetchone()
    conn.close()
    if result is None:
        return ERROR(13)
    book_managementcode = result["management_code"]
    book_isbn = result["isbn_code"]
    book_stock = result["stock"]
    book_last_rental_date = result["last_rental_date"]
    book_title = result["book_title"]
    book_author = result["author"]
    book_hedline = result["headline"]
    book_sample_url = result["sample_url"]
    book_number_of_pages = result["number_of_pages"]
    book_release_date = result["release_date"]
    book_register = result["register"]

    book_title_page = book_title if book_title != "" else "本の詳細ページ"
    book_title = book_title if book_title != "" else "タイトルは未登録です"
    book_author = book_author if book_author != "" else "著者は未登録です"
    book_hedline = book_hedline if book_hedline != "" else "概要は未登録です"
    book_number_of_pages = book_number_of_pages if book_number_of_pages != "" else "ページ数は未登録です"
    book_release_date = book_release_date if book_release_date != "" else "発売日は未登録です"

    if len(book_hedline) > 300:
        book_hedline = book_hedline[:300] + "..."

    return render_template('book.html', page_name="「" + book_title_page + "」の詳細--",
                           book_managementcode=book_managementcode, book_isbn=book_isbn, book_stock=book_stock,
                           book_last_rental_date=book_last_rental_date, book_title=book_title, book_author=book_author,
                           book_hedline=book_hedline, book_sample_url=book_sample_url,
                           book_number_of_pages=book_number_of_pages, book_release_date=book_release_date)


@app.route("/lending")
def lending():
    # flask.session['userid']="root"
    if 'userid' in flask.session:
        return render_template('lending.html', page_name="貸出ページ--")
    else:
        return render_template('redirect_login.html',
                               operation="本のレンタルを利用するには、ログインする必要があります。")


@app.route("/get_book_data", methods=['POST'])
def get_book_data():
    rq = request.get_json()
    search_code = rq['management_code']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM book WHERE management_code = ?", (search_code,))
    result = cursor.fetchone()
    conn.close()
    if result is None:
        data = {
            "status": False,
            "rental_status": False,
            "book_title": "",
            "book_code": ""
        }
    else:
        data = {
            "status": True,
            "rental_status": result[2],
            "book_title": result[4],
            "book_code": result[0]
        }
    return jsonify(data)


@app.route("/rental_book_set", methods=['POST'])
def rental_book_set():
    if flask.session["userid"] is None:
        result = {
            "status": False,
        }
        return jsonify(result)

    rq = request.get_json()
    rental_book_list = []
    rental_book_title = []
    for num in range(len(rq["book_data"])):
        rental_book_list.append(rq["book_data"][num]["book_code"])
        rental_book_title.append(rq["book_data"][num]["title"])
    rental_book_list = list(set(rental_book_list))
    rental_book_title = list(set(rental_book_title))
    now = time.strftime("%Y/%m/%d")
    timestamp = time.mktime(time.strptime(now, "%Y/%m/%d"))
    new_timestamp = timestamp + (7 * 24 * 60 * 60)
    rental_id = time.strftime("%Y%m%d%H%M%S") + str(flask.session['userid'])
    qr = qrcode.QRCode(
        version=1,  # QRコードのバージョン
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # 誤り訂正レベル
        box_size=10,  # ボックスのサイズ
        border=4,  # 境界のサイズ
    )
    qr.add_data(rental_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    q_filename = f"img/{rental_id}.png"
    img.save(q_filename)

    dayplusseven = time.strftime("%Y/%m/%d", time.localtime(new_timestamp))
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    rental_userid = '''SELECT * FROM users WHERE userid = ?'''
    cursor.execute(rental_userid, (flask.session['userid'],))
    result = cursor.fetchone()
    rental_userid = result["id"]
    for num in range(len(rental_book_list)):
        update_query = "UPDATE book SET stock = ?, last_rental_date = ? WHERE management_code = ?"
        cursor.execute(update_query, (False, dayplusseven, rental_book_list[num]))
        insert_query = '''
            INSERT INTO rental (rental_date, rental_id, rental_userid, rental_book_code, rental_status)
            VALUES (?, ?, ?, ?, ?)
        '''
        cursor.execute(insert_query, (now, rental_id, rental_userid, rental_book_list[num], True))
    result_status = {
        "status": True,
    }
    conn.commit()
    conn.close()
    insert_log("本の貸出", "2", f"本の貸出が行われました。貸出コード{rental_id}", "rental_book_set()",
               f"{result['username']}")
    points = 100 * len(rental_book_list)
    point_operation(flask.session['userid'], points, "add")
    mail_text = f"貸出のお知らせ\n\n" \
                f"{result['username']}様\n\n" \
                "この度は図書管理システムをご利用いただきありがとうございます。\n\n" \
                "お客様のアカウントで本の貸出が行われたことをお知らせいたします。\n" \
                "以下の本が貸出されました。\n\n" \
                f"【返却期限{dayplusseven}】\n\n"

    for num in range(len(rental_book_title)):
        mail_text += f"・{rental_book_title[num]}〈{rental_book_list[num]}〉\n"
    mail_text += f"\n返却の際は添付されているバーコードか、返却コードを使用してください。\n" \
                 f"また、マイページからも返却することができます。\n\n" \
                 f"返却コード\n" \
                 f"《{rental_id}》\n\n" \
                 f"メールの中からカレンダーに予定を追加できる様になっています。\n" \
                 f"もしよろしければ、ご利用ください。\n\n" \
                 "図書管理システムのご利用に際して不明な点やお困りのことがございましたら、\n" \
                 "いつでもサポートチームまでお問い合わせください。\n\n" \
                 "図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"

    mail_title = "【図書管理システム】貸出のお知らせ"

    import datetime
    now = datetime.datetime.now()
    start_date = now + datetime.timedelta(days=7)
    start_date = start_date.replace(hour=9, minute=30, second=0)
    START_DATE = start_date.strftime("%Y-%m-%d %H:%M:%S")

    end_date = now + datetime.timedelta(days=7)
    end_date = end_date.replace(hour=16, minute=0, second=0)
    END_DATE = end_date.strftime("%Y-%m-%d %H:%M:%S")

    ics_file_name = Create_Calendar(START_DATE, END_DATE, "本の返却日のお知らせ",
                                    "〒810-0004 福岡県福岡市中央区渡辺通2-4-8 小学館ビル7階",
                                    f"返却期限が本日です。\n返却コードは『{rental_id}』です。\nキャンパスに返却してください\n返却済みの方は無視してください。",
                                    f"ics/{rental_id}.ics")
    file_path = [q_filename, ics_file_name]
    mail_post_on_file(mail_text, result["mail"], mail_title, file_path)

    delete_file(ics_file_name)

    return jsonify(result_status)


@app.route("/rental_book_id_check", methods=['POST'])
def rental_book_id_check():
    rq = request.get_json()
    rental_id = rq["id"]
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = 'SELECT * FROM rental WHERE rental_id = ?'
    cursor.execute(query, (rental_id,))
    results = cursor.fetchall()
    book_data_list = []
    for row in results:
        book_data_list.append(row["rental_book_code"])
        rental_user_id = row["rental_userid"]
        rental_status = row["rental_status"]

    conn.close()
    if book_data_list == []:
        res_data = {
            "status": False,
            "msg": "該当する貸出登録はありません",
            "data": []
        }
        return jsonify(res_data)
    elif rental_status == 0 or rental_status == False or rental_status == "0" or rental_status == "False":
        res_data = {
            "status": False,
            "msg": "この本は返却済みです",
            "data": []
        }

        return jsonify(res_data)
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        for num in range(len(book_data_list)):
            query = 'UPDATE book SET stock = ? WHERE management_code = ?'
            cursor.execute(query, (True, book_data_list[num]))

        query = 'UPDATE rental SET rental_status = ? WHERE rental_id = ?'
        cursor.execute(query, (False, rental_id))

        conn.commit()
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = 'SELECT * FROM users WHERE id = ?'
        cursor.execute(query, (rental_user_id,))
        result = cursor.fetchone()
        mailaddress = result["mail"]
        username = result["username"]
        insert_log("本の返却", "2", f"本の返却が行われました。貸出コード{rental_id}", "rental_book_id_check()",
                   f"{rental_user_id}(レンタルユーザーID)")
        return_data = []
        mail_text = f"返却のお知らせ\n\n" \
                    f"{username}様\n\n" \
                    "この度は図書管理システムをご利用いただきありがとうございます。\n" \
                    "お客様のアカウントで本の返却が行われたことをお知らせいたします。\n\n" \
                    "以下の管理コードの本が返却されました。\n\n" \
                    f"《{rental_id}》\n\n"
        for num in range(len(book_data_list)):
            query = 'SELECT * FROM book WHERE management_code = ?'
            cursor.execute(query, (book_data_list[num],))
            result = cursor.fetchone()
            title = result["book_title"]
            mail_text += f"・{title}〈{book_data_list[num]}〉\n"
            return_data.append(f"{title}〈{book_data_list[num]}〉")

        mail_text = mail_text + "\n返却が完了した本は、本棚に戻してください。\n" \
                                "ご利用いただきありがとうございました。またのご利用を心よりお待ちしております。\n\n" \
                                "図書管理システムのご利用に際して不明な点やお困りのことがございましたら、\n" \
                                "いつでもサポートチームまでお問い合わせください。\n\n" \
                                "図書管理システムサポートチーム\nお問合せ先:https://forms.gle/hYsSKbNmjnPbUfyBA"
        mail_title = "【図書管理システム】返却のお知らせ"
        mail_post(mail_text, mailaddress, mail_title)
        res_data = {
            "status": True,
            "msg": "",
            "data": return_data
        }
        conn.close()

        file_ph = f"img/{rental_id}.png"
        delete_file(file_ph)
        file_ph = f"img/{rental_id}.png_qr.png"
        delete_file(file_ph)

    return jsonify(res_data)


@app.route("/return")
def areturn():
    if 'access_level' in flask.session:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        rental_userid = '''SELECT * FROM users WHERE userid = ?'''
        cursor.execute(rental_userid, (flask.session['userid'],))
        result = cursor.fetchone()
        rental_userid = result["id"]

        query = 'SELECT * FROM rental WHERE rental_userid = ? AND rental_status=?'
        cursor.execute(query, (rental_userid, 1,))
        result = cursor.fetchall()
        rental_book_list =[]

        for row in result:
            rental_id = row["rental_id"]
            # 重複をチェックしてから追加
            if rental_id not in rental_book_list:
                rental_book_list.append(rental_id)

        lental_book_count = len(rental_book_list)

        return render_template('return.html', page_name="返却ページ--",
                               lental_book_count=lental_book_count,rental_book_list=rental_book_list)
    else:
        return render_template("redirect_login.html",
                               operation="本の返却をする際は、ログインが必要です",
                               redirect_url="/return")




@app.route("/new-book")
def new_book():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="新規登録機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4, 3]:
        return render_template('redirect_login.html',
                               operation="新規登録機能を利用するには、アクセスレベルが4以上である必要があります。。")
    elif flask.session['access_level'] in [5, 4, 3]:
        last_books = book_database()
        last_book = last_books[-1]
        db_management_list = []
        for a in last_books:
            db_management_list.append(a[0])
        return render_template('new-book.html', last_book=last_book, db_management_list=db_management_list,
                               page_name="新本登録ページ--")


@app.route("/db_commit", methods=["GET", "POST"])
def new_book_db_commit():
    if request.method == 'GET':
        return render_template('new-book.html')
    else:
        management_code = request.form['managementCode']
        isbn_code = request.form['isbnCode']
        book_title = request.form['bookTitle']
        book_author = request.form['bookAuthor']
        book_headline = request.form['bookHeadline']
        book_sample_img = request.form['bookSampleImg']
        book_page = request.form['bookPage']
        book_release = request.form['bookRelease']

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        sql_query = '''INSERT INTO book (management_code, isbn_code, stock, last_rental_date, book_title, author, headline, sample_url, number_of_pages, release_date, register) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

        values = (
            management_code, isbn_code, True, "1899/12/30", book_title, book_author, book_headline, book_sample_img,
            book_page,
            book_release, "1899/12/30")

        cursor.execute(sql_query, values)

        conn.commit()

        conn.close()
        insert_log("新本登録", "3", f"新本の登録が行われました。登録された本{management_code}", "new_book_db_commit()",
                   f"{flask.session['userid']}")
        return redirect(url_for('new_book', page_name="データベース操作--"))


@app.route("/setting")
@auth.login_required
def setting():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="システム管理機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4]:
        return render_template('redirect_login.html',
                               operation="システム管理機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] in [5, 4]:
        insert_log("設定にログイン", "2", "システム管理の設定にログインされました。", "db_setting()",
                   flask.session['userid'])
        return render_template('db_setting.html', page_name="データベース設定--")


@app.route("/book_setting")
@auth.login_required
def book_deletes():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="データベース操作を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4]:
        insert_log("ブックデータベースアクセス", "1", f"次のユーザーでデータベースへのアクセスがされました。",
                   "book_deletes()",
                   f"{flask.session['userid']}")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM book')
        columns = [desc[0] for desc in cursor.description]

        data = cursor.execute('SELECT * FROM book ').fetchall()

        return render_template("book_setting.html", columns=columns, data=data, page_name="データベース操作--")


@app.route('/setting_books', methods=["POST"])
@auth.login_required
def update_book():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = "SELECT isbn_code, book_title, author, headline, sample_url, number_of_pages, release_date,stock FROM book WHERE management_code = ?"
    cursor.execute(query, (request.form["management_code"],))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        isbn_code = result[0]
        title = result[1]
        author = result[2]
        headline = result[3]
        sample_url = result[4]
        number_of_pages = result[5]
        release_date = result[6]
        stoke = result[7]
        return render_template("update_book.html", management_code=request.form['management_code'], isbn_code=isbn_code,
                               title=title, author=author, headline=headline, sample_url="",
                               number_of_pages=number_of_pages, release_date=release_date, stoke=stoke)
    else:
        return None


@app.route('/update', methods=['POST'])
def book_db_update():
    form = request.get_json()
    if form["stock"] == "1":
        stock = True
    else:
        stock = False

    coon = sqlite3.connect(DATABASE)
    cursor = coon.cursor()

    if form["bookSampleImg"] == "":
        update_query = "UPDATE book SET isbn_code=?,stock=?,book_title=?,author=?,headline=?" \
                       ",number_of_pages=?,release_date=? WHERE management_code = ?"
        cursor.execute(update_query, (form["isbnCode"], stock, form["bookTitle"], form["bookAuthor"],
                                      form["bookHeadline"], form["bookPage"],
                                      form["bookRelease"],
                                      form["managementCode"]))
    else:
        update_query = "UPDATE book SET isbn_code=?,stock=?,book_title=?,author=?,headline=?," \
                       "sample_url=?,number_of_pages=?,release_date=? WHERE management_code = ?"
        cursor.execute(update_query, (form["isbnCode"], stock, form["bookTitle"], form["bookAuthor"],
                                      form["bookHeadline"], form["bookSampleImg"], form["bookPage"],
                                      form["bookRelease"],
                                      form["managementCode"]))

    coon.commit()
    coon.close()
    insert_log("ブックデータベース更新", "3", f"次のユーザーでデータベースの更新をしました。", "book_db_update()",
               f"{flask.session['userid']}")

    return jsonify({"status": True})


@app.route('/delete', methods=['POST'])
def delete_row():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    data = request.get_json()
    management_code = data.get("code")
    cursor.execute('DELETE FROM book WHERE management_code = ?', (management_code,))
    conn.commit()
    insert_log("ブックデータベース削除", "3",
               f"次のユーザーでデータベースの本を削除しました。削除された本{management_code}", "book_db_update()",
               f"{flask.session['userid']}")
    return jsonify({"status": True})


@app.route('/log_check')
@auth.login_required
def return_log_data():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="ログチェック機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4]:
        insert_log("ログダウンロードにアクセス", "2", "システムログダウンロードページにアクセスしました。",
                   "return_log_data()",
                   flask.session['userid'])
        logs_directory = 'logs'
        log_files = sorted(os.listdir(logs_directory), reverse=True)
        file_list = []
        for log_file in log_files:
            if log_file.endswith('.log'):
                log_file_path = os.path.join(logs_directory, log_file)
                file_list.append(os.path.basename(log_file_path))

        return render_template("log_data.html", data=file_list)


@app.route("/dw", methods=['GET'])
def file_download():
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4]:
        query = request.args.get("file", '')
        if query == "":
            return ERROR(11)
        elif query[-4:] == ".log":
            if 'access_level' not in flask.session:
                return ERROR(2)

            access_level = flask.session['access_level']
            if access_level not in [5, 4]:
                return ERROR(1)

            file_path = f"logs/{query}"
            if os.path.exists(file_path):
                insert_log("ファイルのダウンロード", "3",
                           f"次のユーザーがシステムログファイルのダウンロードをしました。　ダウンロードしたログ名{file_path}",
                           "file_download()",
                           f"{flask.session['userid']}")
                return send_file(file_path, as_attachment=True)
            else:
                return ERROR(12)
        else:
            return ERROR(12)


@app.route("/db_log", methods=['GET'])
@auth.login_required
def db_log():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="データベースログ管理機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4]:
        insert_log("ログ確認ページへのアクセス", "2", f"次のユーザーがシステムログ確認ページへアクセスしました。",
                   "db_log()", flask.session['userid'])
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        level = request.args.get('level')
        word = request.args.get('word')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM log WHERE 1=1"
        params = []

        if start_date:
            start_date = start_date.replace("-", "/")
            sql += f" AND time >= ?"
            params.append(start_date)
        if end_date:
            end_date = end_date.replace("-", "/")
            end_date += " 23:59:59"
            sql += f" AND time <= ?"
            params.append(end_date)
        if level:
            sql += f" AND level = ?"
            params.append(level)
        if word:
            keywords = word.split()
            keyword_conditions = " OR ".join(
                ["(msg LIKE ? OR id LIKE ? OR type LIKE ? OR function LIKE ?)"] * len(keywords))
            sql += f" AND ({keyword_conditions})"

            # パラメータを拡張
            for keyword in keywords:
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param] * 4)

        sql += " ORDER BY id DESC"

        cursor.execute(sql, params)
        result = cursor.fetchall()
        conn.close()
        return_data = []
        count = len(result)
        for num in range(count):
            return_data.append({"id": result[num][0], "type": result[num][1],
                                "datetime": result[num][2], "function": result[num][3],
                                "user": result[num][6], "msg": result[num][5], "level": result[num][4], })
        return render_template('db_log.html', page_name="データベースログ--", logData=return_data)


def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(letters) for _ in range(length))
    return random_string


@app.route("/rental_data", methods=['GET'])
@auth.login_required
def rental_data():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="貸出管理機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4]:
        insert_log("貸出データへのアクセス", "2", f"次のユーザーが貸出データページへアクセスしました。",
                   "rental_data()", flask.session['userid'])
        sqlite3.connect(DATABASE)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM rental ORDER BY id DESC;"
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return render_template('rental_data.html', value=result)


@app.route("/rental_data_update", methods=['POST'])
def rental_data_post():
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4]:
        data = request.get_json()
        rental_id = data["id"]
        conn = sqlite3.connect(DATABASE)
        cursor_book = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM rental WHERE rental_id = ?"
        params = (rental_id,)
        cursor_book.execute(sql, params)
        result = cursor_book.fetchall()
        conn.close()
        return_data = []
        count = len(result)
        for num in range(count):
            return_data.append({result[num][4]})

        if data["status"] == 0:
            sql = "UPDATE rental SET rental_status = 0 WHERE rental_id = ?"
            mode = True
            params = (rental_id,)
        elif data["status"] == 1:
            sql = "UPDATE rental SET rental_status = 1 WHERE rental_id = ?"
            mode = False
            params = (rental_id,)
        elif data["status"] == 999:
            sql = "DELETE FROM rental WHERE rental_id = ?"
            mode = False
            params = (rental_id,)
        else:
            return "エラー"

        conn_book = sqlite3.connect(DATABASE)
        cursor_book = conn_book.cursor()
        for data in return_data:
            management_code = int(next(iter(data)))
            update_sql = "UPDATE book SET stock = ? WHERE management_code = ?"
            params_book = (mode, management_code)
            cursor_book.execute(update_sql, params_book)

        conn_book.commit()
        conn_book.close()

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        conn.close()

        insert_log("貸出データの強制更新", "3", f"貸出データを強制的に更新しました{rental_data}",
                   "rental_data_post()",
                   f"{flask.session['userid']}")
        return jsonify({"status": True})


@app.errorhandler(400)
def error_400(error):
    return render_template('error_page.html',
                           page_name="400 Bad Request --",
                           title="400 Bad Request",
                           error=error)


@app.errorhandler(401)
def error_401(error):
    return render_template('error_page.html',
                           page_name="401 Unauthorized --",
                           title="401 Unauthorized",
                           error=error)


@app.errorhandler(403)
def error_403(error):
    return render_template('error_page.html',
                           page_name="403 Forbidden --",
                           title="403 Forbidden",
                           error=error)


@app.errorhandler(404)
def error_404(error):
    return render_template('error_page.html',
                           page_name="404 Not Found --",
                           title="404 Not Found",
                           error=error)


@app.errorhandler(405)
def error_405(error):
    return render_template('error_page.html',
                           page_name="405 Method Not Allowed --",
                           title="405 Method Not Allowed",
                           error=error)


@app.errorhandler(408)
def error_408(error):
    return render_template('error_page.html',
                           page_name="408 Request Timeout --",
                           title="408 Request Timeout",
                           error=error)


@app.errorhandler(410)
def error_410(error):
    return render_template('error_page.html',
                           page_name="410 Gone --",
                           title="410 Gone",
                           error=error)


@app.errorhandler(429)
def error_429(error):
    return render_template('error_page.html',
                           page_name="429 Too Many Requests --",
                           title="429 Too Many Requests",
                           error=error)


@app.errorhandler(500)
def error_500(error):
    insert_log("500エラー", "1", f"500エラーが発生しました。{error}",
               "error_500()",
               f"null")
    return render_template('error_page.html',
                           page_name="500 Internal Server Error --",
                           title="500 Internal Server Error",
                           error=error)


@app.errorhandler(503)
def error_503(error):
    return render_template('error_page.html',
                           page_name="503 Service Unavailable --",
                           title="503 Service Unavailable",
                           error=error)


@app.route("/er")
def keyword_update():
    from flask import abort
    abort(401)
    return render_template('keyword_update.html')


@app.route("/inventory")
def inventory():
    if 'access_level' not in flask.session:
        return render_template('redirect_login.html',
                               operation="棚卸し機能を利用するには、ログインする必要があります。")
    elif flask.session['access_level'] not in [5, 4, 2]:
        return render_template('redirect_login.html',
                               operation="level2,4,5のいずれかでログインする必要があります。")
    elif flask.session['access_level'] in [5, 4, 2]:
        conn = sqlite3.connect(INVENTORY_DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM inventory ORDER BY id DESC LIMIT 20;"
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return render_template('inventory.html', page_name="棚卸しページ--", data=result)


@app.route("/new_inventory", methods=['POST'])
def new_inventory():
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4, 2]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4, 2]:
        data = request.get_json()
        name = data["name"]
        conn = sqlite3.connect(INVENTORY_DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        import datetime
        now = datetime.datetime.now()
        now = str(now)
        hash = hashlib.sha512(now.encode()).hexdigest()

        conn_db = sqlite3.connect(DATABASE)
        cursor_db = conn_db.cursor()
        conn_db.row_factory = sqlite3.Row
        sql = "SELECT management_code,isbn_code,book_title,stock FROM book;"
        cursor_db.execute(sql)
        result = cursor_db.fetchall()
        conn_db.close()
        for num in range(len(result)):
            if result[num][3] == 0 or result[num][3] == "0":
                statusData = f"在庫不在の書籍があります。在庫を確認し、すべての本を蔵書の状態に変更してください。"
                return jsonify(statusData)

        tabel_name = now.replace(" ", "_").replace(":", "_").replace(".", "_").replace("-", "_")
        tabel_name = "inventory_" + tabel_name
        create_tabel_sql = f"CREATE TABLE IF NOT EXISTS {tabel_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, management_code INTEGER, isbn INTEGER, title TEXT, inventory INTEGER);"
        cursor.execute(create_tabel_sql)

        for num in range(len(result)):
            insert_sql = f"INSERT INTO {tabel_name} (management_code, isbn, title, inventory) VALUES (?, ?, ?, ?);"
            params = (result[num][0], result[num][1], result[num][2], False)
            cursor.execute(insert_sql, params)

        inventory_insert_sql = "INSERT INTO inventory (name, date, status, last_updated,hash) VALUES (?, ?, ?, ?,?);"
        params = (name, now, 1, now, hash)
        cursor.execute(inventory_insert_sql, params)
        conn.commit()
        conn.close()
        insert_log("棚卸しデータベースを作成", "3",
                   f"次のユーザーで棚卸しデータベースを作成しました。。", "new_inventory()",
                   f"{flask.session['userid']}")

        statusData = f"[{name}] で棚卸し新規登録を行いました。\n一覧に追加されている棚卸しデータから更新を行ってください。"
        return jsonify(statusData)


@app.route("/inventory/<url>")
def inventory_edit(url):
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4, 2]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4, 2]:
        conn = sqlite3.connect(INVENTORY_DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM inventory WHERE hash = ?;"
        params = (url,)
        cursor.execute(sql, params)
        result = cursor.fetchone()
        tabel_name = result[2]
        tabel_name = tabel_name.replace(" ", "_").replace(":", "_").replace(".", "_").replace("-", "_")
        tabel_name = "inventory_" + tabel_name
        sql = f"SELECT * FROM {tabel_name};"
        cursor.execute(sql)
        result_inventory = cursor.fetchall()

        if result is None:
            return ERROR(14)
        else:
            conn_db = sqlite3.connect(DATABASE)
            cursor_db = conn_db.cursor()
            conn_db.row_factory = sqlite3.Row
            sql = "SELECT management_code,isbn_code,book_title,stock FROM book;"
            cursor_db.execute(sql)
            result_book_st = cursor_db.fetchall()
            conn_db.close()

            inventory_list = [item[1] for item in result_inventory]
            book_st_list = [item[0] for item in result_book_st]

            if set(inventory_list) != set(book_st_list):
                return render_template('inventory_edit.html', page_name="棚卸しページ", data=result,
                                       inventory_data=result_inventory, table_name=tabel_name, update="400")

            if any(item[3] == 0 or item[3] == "0" for item in result_book_st):
                return render_template('inventory_edit.html', page_name="棚卸しページ", data=result,
                                       inventory_data=result_inventory, table_name=tabel_name, update="0")
            if result[3] == 0:
                return render_template('inventory_edit.html', page_name="棚卸しページ", data=result,
                                       inventory_data=result_inventory, table_name=tabel_name, update="403")

            return render_template('inventory_edit.html', page_name="棚卸しページ", data=result,
                                   inventory_data=result_inventory, table_name=tabel_name, update="1")


@app.route("/inventory/<url>/update", methods=['POST'])
def inventory_update(url):
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4, 2]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4, 2]:
        data = request.get_json()
        tabel_name = data["table_name"]
        code = data["code"]
        conn = sqlite3.connect(INVENTORY_DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = f"SELECT * FROM {tabel_name} WHERE management_code = ?;"
        params = (code,)
        cursor.execute(sql, params)
        result = cursor.fetchone()
        if result is None:
            res_data = {"status": 400,
                        "message": "この管理コードは存在しません。"}
            return jsonify(res_data=res_data)
        elif result[4] == 1:
            res_data = {"status": 400,
                        "message": "すでに更新済みです。"}
            return jsonify(res_data=res_data)

        sql = f"UPDATE {tabel_name} SET inventory = ? WHERE management_code = ?;"
        params = (True, code)
        cursor.execute(sql, params)

        sql = f"SELECT * FROM {tabel_name} WHERE management_code =?;"
        params = (code,)
        cursor.execute(sql, params)
        result = cursor.fetchone()
        title = result[3]

        sql = "UPDATE inventory SET last_updated = ? WHERE hash = ?;"
        import datetime
        now = datetime.datetime.now()
        now = str(now)
        params = (now, url)
        cursor.execute(sql, params)
        conn.commit()
        conn.close()

        res_data = {"status": 200,
                    "message": f"テーブル名:{tabel_name}\n管理コード:{code}\n書籍名:<h3>{title}</h3>\n\n上記の情報を更新しました。"}
        # if data
        return jsonify(res_data=res_data)


@app.route("/inventory/<url>/dw_data", methods=['POST'])
def inventory_dw_data(url):
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4, 2]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4, 2]:
        data = request.get_json()
        tabel_name = data["table_name"]
        conn = sqlite3.connect(INVENTORY_DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = f"SELECT * FROM {tabel_name};"
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        column_names = ["ID", "管理コード", "ISBNコード", "書籍名", "蔵書状況"]

        result_list = [list(row) for row in result]
        for num in range(len(result_list)):
            if result_list[num][4] == 0:
                result_list[num][4] = "在庫不足"
            elif result_list[num][4] == 1:
                result_list[num][4] = "在庫あり"
            else:
                result_list[num][4] = "不明"
            if result_list[num][3] == "" or result_list[num][3] is None:
                result_list[num][3] = "書籍名が不明です"
            if result_list[num][2] == "" or result_list[num][2] is None or result_list[num][2] == 0:
                result_list[num][2] = "ISBNが不明です"

        import csv
        with open(f'inventory/{tabel_name}.csv', 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(column_names)  # 列名を追加
            csvwriter.writerows(result_list)

        conn.close()
        file_path = f"inventory/{tabel_name}.csv"
        res_data = {"status": 200,
                    "url": f"inventory_dw?q={file_path}"}
        time.sleep(3)
        return jsonify(res_data=res_data)


@app.route("/inventory_dw")
def inventory_dw():
    if 'access_level' not in flask.session:
        return ERROR(2)
    elif flask.session['access_level'] not in [5, 4, 2]:
        return ERROR(1)
    elif flask.session['access_level'] in [5, 4, 2]:
        query = request.args.get('q')
        if query is None:
            return ERROR(11)
        else:
            insert_log("棚卸しデータをダウンロード", "2",
                       f"次のユーザーで棚卸しデータをダウンロードしました。\n" + query, "inventory_dw()",
                       f"{flask.session['userid']}")
            return send_file(query, as_attachment=True)


@app.route("/inventory/<url>/lock", methods=['POST'])
def inventory_lock(url):
    data = request.get_json()
    data = {"status": 200}
    conn = sqlite3.connect(INVENTORY_DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    sql = "UPDATE inventory SET status = ? WHERE hash = ?;"
    params = (False, url)
    cursor.execute(sql, params)
    conn.commit()
    conn.close()
    insert_log("棚卸しデータベースをロック", "3",
               f"次のユーザーで棚卸しデータをロックしました。", "inventory_lock(url)",
               f"{flask.session['userid']}")
    return jsonify(data=data)


@app.route("/info")
def ainfo():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    sql = "SELECT username, point FROM users ORDER BY point DESC LIMIT 10"
    cursor.execute(sql)
    result = cursor.fetchall()
    conn.close()
    result = [row for row in result if row[1] is not None and row[1] != 0]

    with open("system_version.json", 'r') as file:
        data = json.load(file)  # assuming the file contains JSON data
        VersionName = data.get("VersionName")
    import datetime
    current_date_time = datetime.datetime.now()
    current_year = current_date_time.year

    return render_template('info.html', page_name="このシステムについて--", ranking_data=result, Year=current_year,
                           VersionName=VersionName)


@app.route("/user_setting")
@auth.login_required
def user_setting():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM users"
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return render_template('user_setting.html', page_name="ユーザー総合設定--", data=result)


@app.route("/user_setting/point_operation", methods=['POST'])
def user_edit_point_operation():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        data = request.get_json()
        primary_userid = data["primary_userid"]
        new_point = data["new_point"]
        if primary_userid == "" or new_point == "":
            return jsonify(res_data={"status": 400,
                                     "message": "ポイント数が入力されていないか、全角で入力されています。\n数値は半角で入力してください"})

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "UPDATE users SET point = ? WHERE id = ?"
        params = (new_point, primary_userid)
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        insert_log("ポイントデータベース更新", "2",
                   f"次のユーザーがポイントデータを更新しました。", "user_edit_point_operation()",
                   f"{flask.session['userid']}")
        return jsonify(
            res_data={"status": 200, "message": "ポイント情報の更新を正常に完了しました。\nページをリロードします。"})


@app.route("/user_setting/mail_transmission", methods=['POST'])
def mail_transmission():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        data = request.get_json()
        primary_userid = data["primary_userid"]
        subject = data["mail_subject"]
        body = data["mail_text"]
        if primary_userid == "" or subject == "" or body == "":
            return jsonify(res_data={"status": 400, "message": "入力されていない項目があります。"})
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT mail FROM users WHERE id = ?"
        params = (primary_userid,)
        cursor.execute(sql, params)
        result = cursor.fetchone()
        conn.close()
        if result is None:
            return jsonify(res_data={"status": 400, "message": "ユーザーのメールアドレスが存在しません"})
        mail_post(body, result[0], subject)
        insert_log("ユーザーデータベース更新", "2",
                   f"次のユーザーがメールアドレスを更新しました。。", "mail_transmission()",
                   f"{flask.session['userid']}")
        return jsonify(res_data={"status": 200, "message": "メール送信を正常に完了しました。\nページをリロードします。"})


@app.route("/error", methods=['GET'])
def error():
    mode = request.args.get('e')
    int(mode)
    return ERROR(mode)


def return_mail_post():
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
        ids = []
        for num in range(len(result)):
            ids.append(result[num][2])
        ids = list(set(ids))
        sql = "SELECT * FROM rental WHERE rental_id = ?"
        book_sql = "SELECT * FROM book WHERE management_code = ?"
        for num in range(len(ids)):
            i = num
            rental_code = ids[num]
            cursor.execute(sql, (ids[num],))
            result = cursor.fetchall()
            user_sql = "SELECT * FROM users WHERE id = ?"
            cursor.execute(user_sql, (result[0][3],))
            user_result = cursor.fetchall()
            user_mail_address = user_result[0][5]
            user_name = user_result[0][3]
            book_list = []
            title_list = []
            for num in range(len(result)):
                cursor.execute(book_sql, (result[num][4],))
                book_result = cursor.fetchall()
                book_list.append(result[num][4])
                title_list.append(book_result[0][4])

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

            conn.commit()
            conn.close()
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            sql = "UPDATE send_email SET execution = TRUE WHERE scheduled = ?"
            cursor.execute(sql, (today,))
            conn.commit()
            conn.close()
    else:
        pass


@app.route("/error_setting")
@auth.login_required
def error_setting():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM error"
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return render_template('error_setting.html', page_name="エラー設定--", data=result)


@app.route("/error_setting_update", methods=['POST'])
def error_setting_update():
    data = request.get_json()
    id = data["id"]
    error_id = data["error_id"]
    error_msg = data["error_msg"]
    if id == "" or error_id == "" or error_msg == "":
        return jsonify({"status": False})
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    conn.row_factory = sqlite3.Row
    sql = "UPDATE error SET error_id=?, error_msg=? WHERE id = ?"
    cursor.execute(sql, (error_id, error_msg, id,))
    conn.commit()
    conn.close()
    insert_log("エラーデータベース更新", "3",
               f"次のユーザーでデータベースの更新をしました。" + error_id + "\n" + error_msg, "error_setting_update()",
               f"{flask.session['userid']}")
    return jsonify({"status": True})


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


def run_flask_app():
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)
    app.run(port=80, host="0.0.0.0")


@app.route("/403")
def cancel_request():
    if 'access_level' in flask.session:
        flask.session.pop('userid', None)
        flask.session.pop('username', None)
        flask.session.pop('access_level', None)
        flask.session.pop('mail', None)
    return render_template("IP_access_restrictions.html")


@app.route("/backup_db")
def backup_db():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        Maintenance.backup()
        return redirect("/setting")


@app.route("/SystemUpdate", methods=['POST'])
@auth.login_required
def SystemUpdate():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        update_module.main_flask()
        return redirect("/setting")



def delete_old_backups(folder_path):
    files = os.listdir(folder_path)
    backup_files = [f for f in files if f.endswith("_backup_data.db") or f.endswith("_backup_data_inventory.db")]

    # タイムスタンプを抽出して、ファイルを最新から古い順にソート
    backup_files.sort(key=lambda x: datetime.strptime(x[:19], "%Y-%m-%d_%H-%M-%S"), reverse=True)

    # 最新の5つ以外を削除
    files_to_delete = backup_files[6:]
    for file_to_delete in files_to_delete:
        file_path = os.path.join(folder_path, file_to_delete)
        os.remove(file_path)


@app.route("/support", methods=['POST'])
def support():
    default_section = conf.get_default()
    try:
        data = request.get_json()
        key1_value = data.get('key1', None)
        default_section.auth_token = key1_value
        public_url = ngrok.connect(80)
        public_url = str(public_url)
        match = re.search(r'https://[^"]+', public_url)
        if match:
            extracted_url = match.group(0)
            extracted_url_text = f"コネクトに成功しました。現在外部サポートが受けられる状態です。<br>以下のURLをサポート先に公開してください"
            print(f"抽出されたURL: {extracted_url}")
        else:
            extracted_url = "/"
            extracted_url_text = "コネクトに失敗しました。しばらく時間をおいてお試しください"
    except:
        extracted_url = "/"
        extracted_url_text = "コネクトに失敗しました。しばらく時間をおいてお試しください"
    return jsonify(
        f"<p style='text-align:center;'>{extracted_url_text}<br><a href='{extracted_url}'>{extracted_url}</a></p>")


@app.route("/support_end")
def kill():
    ngrok.kill()
    return "<h1>Disconnected</h1><a href='/'>戻る</a>"


@app.route("/database_backup_Maintenance")
@auth.login_required
def delete_backup():
    if 'access_level' not in flask.session:
        return ERROR(16)
    elif flask.session['access_level'] not in [5]:
        return ERROR(15)
    elif flask.session['access_level'] in [5]:
        Maintenance.backup()
        delete_old_backups("backup")
        return redirect("/setting")


if __name__ == '__main__':
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.start()