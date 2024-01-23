import json
import os
import random
import shutil
import sys
import time
import requests


def main():
    response = input("Updateを開始す場合はメインプログラムの停止を行ってください\n"
                     "メインプログラムを実行している場合は実行をキャンセルしてください\n"
                     "----------------------------\n"
                     "Updateを開始しますか？ (y/n): ")
    if response.lower() == 'y':
        print("Updateを開始...\n")
        print("Update準備中...")
        loading_animation()
        update(version_check(), now_version_check())
    elif response.lower() == 'n':
        print("Updateを中止...")
        exit()
    else:
        print("yまたはnを入力してください")
        exit()

def main_flask():
    update(version_check(), now_version_check())
    if sys.platform.startswith("linux"):
        os.system('sudo reboot')
    else:
        print("shutdownスキップ")
        pass


def show_download_progress(progress, color='white'):
    bar_length = 20
    block_width = 2
    blocks = int(round(bar_length * progress))
    remaining_blocks = bar_length - blocks
    progress_bar = "■" * (blocks * block_width) + "□" * (remaining_blocks * block_width)

    # ANSIエスケープコードで色を指定
    color_code = {
        'white': '\033[97m',
        'green': '\033[92m'
    }
    end_code = '\033[0m'

    sys.stdout.write(f"\r[{color_code.get(color, '')}{progress_bar}{end_code}] {int(progress * 100)}%")
    sys.stdout.flush()


def loading_animation():
    for i in range(101):
        progress = i / 100.0
        if i == 100:
            show_download_progress(progress, color='green')
        else:
            show_download_progress(progress)

        if random.random() < 0.05:
            stop_duration = random.uniform(0.5, 1.5)
            time.sleep(stop_duration)
            show_download_progress(progress)
        elif random.random() < 0.05:
            i += 2

        time.sleep(0.005)
    print()
def version_check():
    try:
        print("UpdateServerからデータを取得中...")
        loading_animation()
        json_file_path = "system_version.json"
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)
            url = data.get("version_data")
        response = requests.get(url)
        response.raise_for_status()
        version_data = response.json()
        version_data = [list(item) if not isinstance(item, (str, int, float)) else item for item in
                        version_data.items()]
        return version_data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
def now_version_check():
    try:
        print("現在データを取得中...")
        loading_animation()
        json_file_path = "system_version.json"
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)
            data = [list(item) if not isinstance(item, (str, int, float)) else item for item in data.items()]
            return data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None
def download_file(url, destination):
    try:
        response = requests.get(url)
        response.raise_for_status()  # エラーレスポンスが返された場合、例外を発生させる
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as file:
            file.write(response.content)
        loading_animation()
        print(f"ファイルを {destination} にダウンロードしました...")
    except requests.exceptions.RequestException as e:
        print(f"\033[91mダウンロードエラー: {e}\033[0m")
def overwrite_file(source_path, destination_path):
    try:
        shutil.copyfile(source_path, destination_path)
        print(f"{source_path} を {destination_path} に上書きしました...")
    except FileNotFoundError:
        print(f"\033[91mエラー: {source_path} が見つかりませんでした...\033[0m")
def update(Server, Program):
    Update_List = []
    if float(Server[2][1]) == float(Program[2][1]):
        print(f"\033[91m更新Serverとのprogramのバージョンは同一です...\n"
              f"この状態ではアップデートをすることができません\n"
              f"Server:{Server[2][1]}\nProgram:{Program[2][1]}\033[0m")
        return None
    elif float(Server[2][1]) < float(Program[2][1]):
        print(f"\033[91mprogramのデータが更新Serverのバージョンよりも高いです...\n"
              f"この状態ではアップデートをすることができません...\n"
              f"Server:{Server[2][1]}\nProgram:{Program[2][1]}\033[0m")
        return None
    else:
        items = Server[4][1]
        if len(items) != 0:
            print("新規fileを追加を確認中...")
            loading_animation()
            for item in items:
                directory = os.path.dirname(item)
                if os.path.exists(item):
                    print(f"{item} ファイルは既に存在しています。スキップします。")
                else:
                    print(item)
                    with open(item, 'w') as new_file:
                        new_file.write("# Updateによるfile作成")
                    with open('system_version.json', 'r') as file:
                        data = json.load(file)
                    # 新しいデータの作成（例として辞書を使用）
                    new_data = {
                        item: 0.0
                    }
                    # 既存のデータに新しいデータをマージ
                    data.update(new_data)
                    # 更新されたデータをJSONファイルに書き込み
                    with open('system_version.json', 'w') as file:
                        json.dump(data, file, indent=2)
                    print(f"{item} ファイルを作成しました。")
                    print("再度情報確認に入ります....")
                    update(version_check(), now_version_check())
                    return None
        else:
            pass
        print("検証結果")
    for num in range(len(Server) - 5):
        count = num + 5
        server_value = Server[count][1]
        program_value = Program[count][1]
        if server_value > program_value:
            print(
                f"\033[92mUpdate可能です [{Server[count][0]}] Version:{Program[count][1]} →→→→→ Version:{Server[count][1]}\033[0m")
            Update_List.append(Server[count][0])
            time.sleep(0.1)
        else:
            print(f"Updateスキップ [{Server[count][0]}:{Server[count][1]}]")
            time.sleep(0.1)
    try:
        json_file_path = "system_version.json"
        with open(json_file_path, "r") as json_file:
            data = json.load(json_file)
            data = [list(item) if not isinstance(item, (str, int, float)) else item for item in data.items()]
            URL = data[0][1]
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None
    for file in Update_List:
        dw_url = URL + file
        download_file(dw_url, "Update/" + file)
        source_file_path = "Update/" + file
        overwrite_file(source_file_path, file)
    print("書き込み処理中...")
    loading_animation()

    json_file_path = "system_version.json"
    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)
        data = [list(item) if not isinstance(item, (str, int, float)) else item for item in data.items()]
        URL = data[0][1]

    print("バージョンデータを更新中...")
    download_file(URL + "system_version.json", "Update/system_version.json")
    overwrite_file("Update/system_version.json", "system_version.json")
    shutil.rmtree("Update")

if __name__ == "__main__":
    main()
    print("Update処理を終了しています...")
    loading_animation()
    print("Update終了")
