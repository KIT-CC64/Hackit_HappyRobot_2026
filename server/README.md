# サーバー・通信（server/）

Arduinoとのシリアル通信、およびWebステータス画面配信用のFlask APIサーバーです。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `app.py` | Flask Webサーバー（API配信 + Web画面配信） |
| `serial_control.py` | サーボ制御Arduino（`arduino/servo_3/servo_3.ino`）とのシリアル通信 |
| `sensor_bridge.py` | カウント用Arduino（`web/GarbageCounter/GarbageCounter.ino`）からの通過検知を受け取り、Flaskへ通知 |
| `gar_info_recieve.py` | 未使用（初期検討用スニペット） |

## 全体構成

RealSenseカメラ・サーボ制御Arduino・カウント用Arduinoの3台のUSBデバイスをすべて1台のノートPCに接続し、`app.py`・`sensor_bridge.py`・`ai_core/State machine.py`も同じPC上で動作させます。

```
[ノートPC]
 - RealSenseカメラ／サーボ制御Arduino／カウント用Arduino（すべてUSB接続）
 - ai_core/State machine.py ──POST /api/feed──▶ server/app.py（Flask）
                             └─serial_control.py 経由──▶ サーボArduino
 - server/sensor_bridge.py ──POST /api/feed──▶ server/app.py
 - VOICEVOXアプリ
```

スマホからWebステータス画面へアクセスする方法は[`../network_relay/README.md`](../network_relay/README.md)を参照してください。

## API仕様

- `GET /api/status` — 満腹度・レベル・経験値・種類別カウントをJSONで返す
- `POST /api/feed` — `{"type": "petbottle"|"can"|"burnable", "correct": true}` を受け取り、カウント・EXP・レベルを更新
- `POST /api/reset` — 状態を初期値にリセット

## serial_control.py

`open_lid(servo_num)`でサーボArduinoにフタ開閉コマンドを送信します（`servo_num`: 1=ペットボトル / 2=缶 / 3=燃えるゴミ）。ボーレートは9600、接続ポートは`PORT`変数で指定します（デバイスマネージャーで実機のCOM番号を確認して設定してください）。

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
