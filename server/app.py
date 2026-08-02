import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# 【統合】1年生Cのステータス画面（site_flog/）をこのFlaskサーバーから直接配信する。
# こうすることで「Flaskだけ起動すればWeb画面もAPIも同じPC・同じポートから出る」状態になり、
# site_flog/index.html側で本番PCのIPアドレスをハードコードして毎回書き換える必要がなくなる
# （index.html側のfetch先も相対パス "/api/status" に変更済み）。
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(BASE_DIR, "..", "site_flog")

app = Flask(__name__, static_folder=SITE_DIR, static_url_path="")
# 他の端末（スマホなど）からのWebアクセスを許可する設定
CORS(app)


# --------------------------------------------------
# Web画面配信：site_flog/index.html をルートで返す
# （images/等の静的ファイルは static_folder 設定により自動で配信される）
# --------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(SITE_DIR, "index.html")


# 【8/2追加】リハーサル・本番直前に何度でもゼロから始め直せるように、
# 初期値は必ずゼロにしておく（以前はテスト用の数値が入ったままで、
# 本番でうっかりそのまま起動するとレベルが最初から上がった状態になっていた）。
DEFAULT_STATE = {
    "hunger": 0,
    "level": 1,
    "exp": 0,
    "next_exp": 10,
    "stage": "otamajakushi",
    "counts": {
        "petbottle": 0,
        "can": 0,
        "burnable": 0,
    },
}

# カエルの状態管理（メモリ上に保持）
state = dict(DEFAULT_STATE)
state["counts"] = dict(DEFAULT_STATE["counts"])


def update_level_and_stage():
    """経験値（exp）に応じてレベルと見た目（stage）を更新する内部関数"""
    total_trash = sum(state["counts"].values())

    # レベル判定（仕様書0-3節の目安に基づく）
    if total_trash >= 10:
        state["level"] = 3
        state["stage"] = "manpuku"
        state["next_exp"] = 20  # MAX想定
    elif total_trash >= 5:
        state["level"] = 2
        state["stage"] = "kogaeru"
        state["next_exp"] = 20
    else:
        state["level"] = 1
        state["stage"] = "otamajakushi"
        state["next_exp"] = 10

    # 満腹度の計算 (例: 10個で満腹度100%)
    state["hunger"] = min(100, total_trash * 10)


# --------------------------------------------------
# API 1: ステータス取得 (1年生CのWeb画面が使用)
# --------------------------------------------------
@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify(state)


# --------------------------------------------------
# API 2: ごみ投入記録 (2年生Aの推論スクリプト／sensor_bridge.pyが使用)
# --------------------------------------------------
@app.route("/api/feed", methods=["POST"])
def feed():
    data = request.get_json()

    # リクエストのチェック
    if not data or "type" not in data:
        return jsonify({"error": "Invalid request"}), 400

    trash_type = data.get("type")

    # 指定された種類（petbottle | can | burnable）が存在すればカウント＋1
    if trash_type in state["counts"]:
        state["counts"][trash_type] += 1
        state["exp"] += 2  # ゴミ1個につきEXP+2

        # レベルと満腹度を再計算
        update_level_and_stage()

        print(
            f"[API Feed] {trash_type} が追加されました。現在のEXP: {state['exp']}, レベル: {state['level']}"
        )
        return jsonify({"success": True, "state": state})
    else:
        return jsonify({"error": f"Unknown type: {trash_type}"}), 400


# --------------------------------------------------
# API 3【8/2追加】: 状態リセット（リハーサル・本番直前に叩く用）
# 例:  curl -X POST http://localhost:5000/api/reset
#      （PowerShellなら curl.exe でもOK。ブラウザで直接は叩けないのでcurl/Postman推奨）
# --------------------------------------------------
@app.route("/api/reset", methods=["POST"])
def reset():
    state["hunger"] = DEFAULT_STATE["hunger"]
    state["level"] = DEFAULT_STATE["level"]
    state["exp"] = DEFAULT_STATE["exp"]
    state["next_exp"] = DEFAULT_STATE["next_exp"]
    state["stage"] = DEFAULT_STATE["stage"]
    state["counts"] = dict(DEFAULT_STATE["counts"])
    print("[API Reset] 状態をリセットしました。")
    return jsonify({"success": True, "state": state})


# --------------------------------------------------
# サーバー起動設定
# --------------------------------------------------
if __name__ == "__main__":
    # host="0.0.0.0" にすることで外部（スマホや別PC）からのアクセスを許可する
    #
    # 【8/2追記】threaded=True を追加：Flask開発用サーバーはデフォルトだと
    # 一度に1リクエストしか処理できず、仮想マシン経由の2段中継（tcp_relay.py＋SSH
    # トンネル）でレイテンシが増える構成だと、HTML/CSS/JS/画像/APIなど複数リクエストが
    # ほぼ同時に来た際に処理待ちで詰まり「読み込み中のまま開けない」症状が出ていた。
    # あわせて本番デモ中はファイル変更監視で勝手に再起動するリローダー（debug=Trueの
    # 副作用）も余計な不安定要素になるためオフにする。
    # 開発中にデバッグ画面が欲しい場合は一時的にdebug=Trueに戻してもよいが、
    # 本番前には必ずFalseに戻すこと。
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
