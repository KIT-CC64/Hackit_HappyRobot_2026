# サーバーimport os
from weasyprint import HTML

# Content for README.md / Specification document for 2年生B
readme_content = """# 🐸 ケロッと!はらぺこエコガエル - 2年生B（通信・Flaskサーバー担当）仕様書 & README

本リポジトリ／モジュールは、「ケロッと!はらぺこエコガエル」システムにおける **PC↔Arduino間のシリアル通信** および **Webステータス管理Flaskサーバー** の実装・設定ガイドです。

---

## 📁 プログラム構成一覧

| プログラム・ファイル名 | 担当モジュール | 概要 | 関連担当者 |
| :--- | :--- | :--- | :--- |
| `serial_control.py` | シリアル通信モジュール | PythonからArduinoへサーボ駆動コマンド（`"1\\n"`, `"2\\n"` 等）を送信する | 2年生A, 1年生A |
| `app.py` | Flask Web API サーバー | ゲーム状態（満腹度・LV・経験値・カウント）の保持とAPIの提供 | 2年生A, 1年生C |
| `arduino_servo.ino` | Arduino用スケッチ | PCからのシリアル信号を受信し、サーボ開閉・センサ検知を行う | 1年生A |

---

## 📄 各プログラムの仕様・呼び出しのルール

### 1. `serial_control.py`（シリアル通信モジュール）

PCからArduinoに対してフタの開閉命令をシリアル通信経由で送信します。

#### ■ 仕様パラメータ
* **ボーレート:** `9600`
* **接続ポート:** `COM3` （Windows）または `/dev/tty.usbmodemXXXX` （Mac/Linux）

#### ■ 提供関数（2年生Aが呼び出すインターフェース）

```python
def open_lid(servo_num: int) -> bool:
    \"\"\"
    指定した投入口のフタを開けるコマンドをArduinoへ送信します。
    
    :param servo_num: 1（口1: ペットボトル用）または 2（口2: 缶用）
    :return: 送信成功時 True
    \"\"\"