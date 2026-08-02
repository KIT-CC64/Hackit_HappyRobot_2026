from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# 他の端末（スマホなど）からのWebアクセスを許可する設定
CORS(app)

# カエルの状態管理（メモリ上に保持）
# カエルの状態管理（初期値を直接変更）
state = {
    "hunger": 65,  # 初期値を 0 から 65 に変更
    "level": 2,  # 初期値を 1 から 2 に変更
    "exp": 12,
    "next_exp": 20,
    "stage": "kogaeru",  # 見た目の初期値を変更
    "counts": {
        "petbottle": 5,  # テスト用に初期値を設定
        "can": 3,
        "burnable": 4,  # 🔥 燃えるゴミの初期値を変更
    },
}


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
# API 2: ごみ投入記録 (2年生Aの推論スクリプトが使用)
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
# サーバー起動設定
# --------------------------------------------------
if __name__ == "__main__":
    # host="0.0.0.0" にすることで外部（スマホや別PC）からのアクセスを許可する
    app.run(host="0.0.0.0", port=5000, debug=True)