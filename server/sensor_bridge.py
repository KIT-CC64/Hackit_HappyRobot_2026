import time
import requests
import serial

PORT = "COM4"  # 使用環境に合わせて設定
BAUD_RATE = 9600
# sensor_bridge.py 内の変更箇所

# 仮想マシンのIPアドレスを指定
FLASK_URL = "http://172.20.124.38:5000/api/feed"


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
                    # Flaskへ送信
                    requests.post(FLASK_URL, json={"type": trash_type})

            # 🔥 Point 2: ループの待機時間を 0.01秒（10ms）に短縮
            time.sleep(0.01)

    except Exception as e:
        print(f"エラー: {e}")


if __name__ == "__main__":
    main()