import time
import serial

# --- 設定項目 ---
# 環境に合わせてCOMポートを変更してください
PORT = "COM6"
BAUD_RATE = 9600

# シリアル通信オブジェクト（グローバル変数として保持）
_ser = None


def init_serial(port=PORT, baud_rate=BAUD_RATE):
    """シリアル通信を初期化する関数

    プログラム起動時に1度だけ呼び出します。
    """
    global _ser
    if _ser is not None and _ser.is_open:
        print("[Serial] すでに接続されています。")
        return

    try:
        _ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"[Serial] {port} (ボーレート: {baud_rate}) に接続しました。")
        # Arduinoが接続直後に自動リセットされるため、起動待ちとして2秒待機
        time.sleep(2)
    except Exception as e:
        print(f"[Serial エラー] 接続に失敗しました: {e}")
        _ser = None


def open_lid(servo_num):
    """2年生A（推論スクリプト担当）から呼ばれる関数

    引数:
        servo_num (int または str): 口番号 (1: ペットボトル, 2: 缶, 0: 全閉・リセット)
    """
    global _ser

    # 未接続の場合は自動で初期化を試みる
    if _ser is None or not _ser.is_open:
        print("[Serial] 未接続のため初期化を行います...")
        init_serial()
        if _ser is None or not _ser.is_open:
            print("[Serial エラー] 送信できません（接続されていません）。")
            return False

    # コマンドの整形 (例: 1 -> "1\n")
    command_str = f"{servo_num}\n"

    try:
        # 送信 (文字列を utf-8 バイト列に変換)
        _ser.write(command_str.encode("utf-8"))
        print(f"[Serial] 送信完了: {repr(command_str)}")

        # Arduinoからの返信確認（"OK1\n" などが返ってくる想定）
        response = _ser.readline().decode("utf-8").strip()
        if response:
            print(f"[Serial] Arduinoからの返信: {response}")

        return True

    except Exception as e:
        print(f"[Serial エラー] 送信中にエラーが発生しました: {e}")
        return False


def close_serial():
    """プログラム終了時に通信を安全に閉じる関数"""
    global _ser
    if _ser is not None and _ser.is_open:
        _ser.close()
        print("[Serial] ポートを閉じました。")


# --- 単体テスト用メイン処理 ---
if __name__ == "__main__":
    print("=== シリアル通信モジュール 単体テスト ===")
    init_serial()

    # 口1（ペットボトル）を開けるテスト
    print("\n--- テスト1: 口1 (ペットボトル) 送信 ---")
    open_lid(1)  # 数値の 1 でも OK
    time.sleep(3)

    # 口2（缶）を開けるテスト
    print("\n--- テスト2: 口2 (缶) 送信 ---")
    open_lid("2")  # 文字列の "2" でも OK
    time.sleep(3)

    # 口0（リセット・全閉）のテスト
    print("\n--- テスト3: 口0 (全閉) 送信 ---")
    open_lid(0)

    close_serial()
    print("\nテスト終了")