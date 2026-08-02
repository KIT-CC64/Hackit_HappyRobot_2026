"""
server/sensor_bridge.py
投入口のフォトインタラプタ（GarbageCounter.ino を書き込んだ「カウント用」Arduino）から
CAN: / PETBOTTLE: / BURNABLE: を受信し、必要であればFlaskへカウントを送る橋渡しスクリプト。

【統合時の重要な注意：二重カウントについて】
このシステムは既に ai_core/State machine.py がAIの判定確定と同時に
POST /api/feed を呼んでカウントしている（仕様書0-2節どおりの正規ルート）。
このスクリプトも同時に /api/feed を叩くと「AIの判定」と「物理センサー通過」の
両方でカウントされ、投入1個につき+2されてしまう。
そのため ENABLE_DIRECT_FEED_POST はデフォルトで False にしてあり、
今はセンサー検知をログ表示するだけ（Flaskへは送らない）動作になっている。

もし「AI判定ではなく、物理的に投入口を通過したことをもってカウント確定にしたい」
という方針に変更する場合は、
  1. ENABLE_DIRECT_FEED_POST を True にする
  2. ai_core/State machine.py 側の post_feed(...) 呼び出しをコメントアウトする
の両方をセットで行うこと（どちらか片方だけ変更すると二重カウント／未カウントになる）。
"""

import time
import requests
import serial

# 【要変更】GarbageCounter.ino（フォトインタラプタ用）を書き込んだArduinoのCOMポート。
# servo_3.ino（フタ開閉用）を書き込んだ別のArduino（server/serial_control.py の PORT="COM4"）
# とは別の物理ポートになるはずなので、デバイスマネージャーで確認して設定すること。
PORT = "COM5"  # 使用環境に合わせて設定（servo用のCOM4とは別ポート）
BAUD_RATE = 9600

# 【構成メモ】このスクリプトは server/app.py（Flask）と同じ仮想マシン上で実行する想定
# （2年生Bの開発環境）。同じマシン上で動かす前提なので localhost でOK。
# ai_core/State machine.py 側は別のホストPC上で動くため、そちらは
# 仮想マシンのIPアドレス（FLASK_SERVER_URL）を直接指定している（State machine.py参照）。
FLASK_URL = "http://localhost:5000/api/feed"

# 上記の「二重カウント注意」を参照。デフォルトはFalse＝ログ表示のみでFlaskには送らない。
ENABLE_DIRECT_FEED_POST = False


def main():
    try:
        # 🔥 Point 1: timeout を 0.1秒 に短縮して読み込み待ちをなくす
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        ser.reset_input_buffer()
        print("リアルタイム監視中（高速化モード）...")

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                trash_type = None
                if line.startswith("CAN:"):
                    trash_type = "can"
                elif line.startswith("PETBOTTLE:"):
                    trash_type = "petbottle"
                elif line.startswith("BURNABLE:"):
                    trash_type = "burnable"

                if trash_type:
                    print(f"【検知】 {trash_type}")
                    if ENABLE_DIRECT_FEED_POST:
                        # Flaskへ送信（AI側のpost_feedと併用すると二重カウントになるので注意。
                        # ファイル冒頭のコメント参照）
                        try:
                            requests.post(FLASK_URL, json={"type": trash_type}, timeout=0.5)
                        except Exception as e:
                            print(f"[WARN] Flask送信失敗: {e}")

            # 🔥 Point 2: ループの待機時間を 0.01秒（10ms）に短縮
            time.sleep(0.01)

    except Exception as e:
        print(f"エラー: {e}")


if __name__ == "__main__":
    main()