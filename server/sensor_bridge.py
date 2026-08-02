"""
server/sensor_bridge.py
投入口のフォトインタラプタ（GarbageCounter.ino を書き込んだ「カウント用」Arduino）から
CAN: / PETBOTTLE: / BURNABLE: を受信し、Flaskへカウントを送る橋渡しスクリプト。

【方針確定・8/2リーダー判断】カウント確定の正規ルートは「物理センサー通過」
（このスクリプト＝カウント用Arduino）に決定。AI判定確定側（ai_core/State machine.py の
post_feed(...)）は二重カウント防止のためコメントアウト済み。
このファイルの ENABLE_DIRECT_FEED_POST は True のまま維持すること。
もし将来また「AI判定確定を正規ルートに戻す」場合は、
  1. ENABLE_DIRECT_FEED_POST を False にする
  2. ai_core/State machine.py 側の post_feed(...) 呼び出しのコメントアウトを解除する
の両方をセットで行うこと（どちらか片方だけ変更すると二重カウント／未カウントになる）。
"""

import time
import requests
import serial

# 【要変更】GarbageCounter.ino（フォトインタラプタ用）を書き込んだArduinoのCOMポート。
# servo_3.ino（フタ開閉用）を書き込んだ別のArduino（server/serial_control.py の PORT="COM4"）
# とは別の物理ポートになるはずなので、デバイスマネージャーで確認して設定すること。
PORT = "COM6"  # 【8/2更新】デバイスマネージャーで実機確認：COM6=カウント用Arduino
BAUD_RATE = 9600

# 【本番構成に復帰済み】ノートPC1台に集約する構成のため localhost:5000 に固定。
# （以前は仮想マシン(team9.hackit)テスト用に172.20.125.69:5500を指していたが、
#  本番はこのPC上でapp.pyが動くのでlocalhostに戻した）
FLASK_URL = "http://localhost:5000/api/feed"

# 【方針確定・8/2】正規ルートはこちら（物理センサー通過）。
# ai_core/State machine.py 側の post_feed() はコメントアウト済みなので、
# こちらをTrueにしても二重カウントにはならない。
ENABLE_DIRECT_FEED_POST = True


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
                            # 【要注意】仮想マシン等リモート宛の場合、0.5秒は短すぎて
                            # 単純に間に合わないだけで失敗することがあるため、切り分けのため延長してある
                            requests.post(FLASK_URL, json={"type": trash_type}, timeout=3.0)
                        except Exception as e:
                            print(f"[WARN] Flask送信失敗: {e}")

            # 🔥 Point 2: ループの待機時間を 0.01秒（10ms）に短縮
            time.sleep(0.01)

    except Exception as e:
        print(f"エラー: {e}")


if __name__ == "__main__":
    main()