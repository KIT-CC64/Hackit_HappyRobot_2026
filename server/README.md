<<<<<<< HEAD
# 🐸 ケロッと!はらぺこエコガエル - バックエンド・通信モジュール総合仕様書 & README

本リポジトリは、「ケロッと!はらぺこエコガエル」システムにおける **PC↔Arduino間のシリアル通信** および **Webステータス管理Flaskサーバー** の実装・設定・トラブルシューティングガイドです。
=======
# サーバー・通信（server/）

Arduinoとのシリアル通信、およびWebステータス画面配信用のFlask APIサーバーです。

## ファイル構成
>>>>>>> 4d76ce186cc98bc727fb52bf64597344acc68117

| ファイル | 役割 |
|---|---|
| `app.py` | Flask Webサーバー（API配信 + Web画面配信） |
| `serial_control.py` | サーボ制御Arduino（`arduino/servo_3/servo_3.ino`）とのシリアル通信 |
| `sensor_bridge.py` | カウント用Arduino（`web/GarbageCounter/GarbageCounter.ino`）からの通過検知を受け取り、Flaskへ通知 |
| `gar_info_recieve.py` | 未使用（初期検討用スニペット） |

## 全体構成

<<<<<<< HEAD
| プログラム・ファイル名 | 担当モジュール | 概要 | 関連担当者 |
| :--- | :--- | :--- | :--- |
| `serial_control.py` | シリアル通信モジュール | PythonからArduinoへサーボ駆動コマンド（`"1\n"`, `"2\n"` 等）を送信 | 2年生A, 1年生A |
| `app.py` | Flask Web API サーバー | ゲーム状態（満腹度・LV・経験値・カウント）の保持とAPIの提供 | 2年生A, 1年生C, 2年生B |
| `sensor_bridge.py` | センサー・通信ブリッジ | シリアル通信とサーバー間のデータ連携処理を橋渡しするスクリプト | 2年生B |
| `arduino_servo.ino` | Arduino用スケッチ | PCからのシリアル信号を受信し、サーボ開閉・センサ検知を行う | 1年生A |
=======
RealSenseカメラ・サーボ制御Arduino・カウント用Arduinoの3台のUSBデバイスをすべて1台のノートPCに接続し、`app.py`・`sensor_bridge.py`・`ai_core/State machine.py`も同じPC上で動作させます。
>>>>>>> 4d76ce186cc98bc727fb52bf64597344acc68117

```
[ノートPC]
 - RealSenseカメラ／サーボ制御Arduino／カウント用Arduino（すべてUSB接続）
 - ai_core/State machine.py ──POST /api/feed──▶ server/app.py（Flask）
                             └─serial_control.py 経由──▶ サーボArduino
 - server/sensor_bridge.py ──POST /api/feed──▶ server/app.py
 - VOICEVOXアプリ
```

<<<<<<< HEAD
## 📄 各プログラムの仕様・呼び出しルール
=======
スマホからWebステータス画面へアクセスする方法は[`../network_relay/README.md`](../network_relay/README.md)を参照してください。
>>>>>>> 4d76ce186cc98bc727fb52bf64597344acc68117

## API仕様

- `GET /api/status` — 満腹度・レベル・経験値・種類別カウントをJSONで返す
- `POST /api/feed` — `{"type": "petbottle"|"can"|"burnable", "correct": true}` を受け取り、カウント・EXP・レベルを更新
- `POST /api/reset` — 状態を初期値にリセット

<<<<<<< HEAD
* **ボーレート:** `9600`
* **接続ポート例:** `COM3`（Windows）または `/dev/tty.usbmodemXXXX`（Mac/Linux）
  * Windowsの場合は、**デバイスマネージャー** を開き、「ポート (COM と LPT)」項目から接続中のArduinoが割り当てられている `COM` の後の数字（例: COM3, COM4 等）を確認してください。
=======
## serial_control.py
>>>>>>> 4d76ce186cc98bc727fb52bf64597344acc68117

`open_lid(servo_num)`でサーボArduinoにフタ開閉コマンドを送信します（`servo_num`: 1=ペットボトル / 2=缶 / 3=燃えるゴミ）。ボーレートは9600、接続ポートは`PORT`変数で指定します（デバイスマネージャーで実機のCOM番号を確認して設定してください）。

<<<<<<< HEAD
```python
def open_lid(servo_num: int) -> bool:
    """
    指定した投入口のフタを開けるコマンドをArduinoへ送信します。
    
    :param servo_num: 1（口1: ペットボトル用）または 2（口2: 缶用）
    :return: 送信成功時 True
    """
```

## 🚀 実行・セットアップ手順

### 1. 事前準備（事前テスト & シリアルポート解放）

1. **Arduino IDE での疎通確認**
   * Arduino IDEの「シリアルモニタ」を開き、センサやサーボの通信値が正しく読み取れることを確認します。
   * **⚠️【最重要注意点】**
     * **確認完了後、Arduino IDEのシリアルモニタは必ず閉じておいてください。**
     * （※シリアルモニタが開いたままだとポートが占有され、後続のPythonスクリプトから通信エラーになります）

---

### 2. システムの起動手順

#### Step 1: 仮想マシンでの Web API サーバー起動
仮想マシン環境へ移動し、`server` ディレクトリ内にある `app.py` をコマンドラインから実行します。

cd server
python3 app.py

#### Step 2: センサーブリッジ（`sensor_bridge.py`）の実行
新しいシェル（ターミナル / コマンドプロンプト）を開き、同様に `server` ディレクトリ内にある `sensor_bridge.py` を実行します。


cd server
python sensor_bridge.py

#### Step 3: Web画面へのアクセス確認
ブラウザを開き、以下のURLへアクセスします。


[http://172.20.125.69:5500/](http://172.20.125.69:5500/)
これは仮想マシンのIPアドレスなので逐一変更する必要はないです。
=======
## sensor_bridge.py とカウントの正規ルート

ゴミのカウント確定は、カウント用Arduinoのフォトインタラプタが物理的にゴミの通過を検知した瞬間（`sensor_bridge.py`が`CAN:`/`PETBOTTLE:`/`BURNABLE:`を受信してPOST /api/feedを呼ぶ）を正規ルートとしています。`ai_core/State machine.py`側のPOST呼び出しは二重カウント防止のため無効化しています。ルートを変更する場合は、`sensor_bridge.py`の`ENABLE_DIRECT_FEED_POST`と`State machine.py`側の`post_feed(...)`呼び出しを両方セットで切り替えてください。

## セットアップ・起動

Arduino IDEのシリアルモニタで疎通確認後、必ず閉じてからPythonを実行してください（開いたままだとポートが競合します）。

```bash
cd server
python app.py             # Flask（API + Web画面）
python sensor_bridge.py   # カウント用Arduinoの橋渡し（任意）
```

`ai_core/State machine.py`・VOICEVOXの起動を含めた一括起動はリポジトリ直下の`run_demo.bat`を使用してください。

## 補足

`site_flog/app.py`・`site_flog/server.js`は初期検討時の別実装で未使用です（API・Web画面配信は本ファイルの`app.py`に統合済み）。
>>>>>>> 4d76ce186cc98bc727fb52bf64597344acc68117
