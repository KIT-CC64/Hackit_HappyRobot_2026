# 🐸 ケロッと！はらぺこエコガエル - サーバー・通信（2年生B担当）README

「PC↔Arduino間のシリアル通信」と「Webステータス管理Flaskサーバー」の実装・設定・トラブルシューティングガイドです。

---

## 📁 プログラム構成一覧

| ファイル | 役割 | 状態 |
|---|---|---|
| `app.py` | Flask Webサーバー（API配信 + Web画面配信を統合） | **メインで使用** |
| `serial_control.py` | サーボ制御Arduino（`arduino/servo_3/servo_3.ino`）向けのシリアル通信モジュール | **メインで使用** |
| `sensor_bridge.py` | フォトインタラプタ用Arduino（`web/GarbageCounter/GarbageCounter.ino`）からのカウント通過検知を橋渡し | 補助・デフォルトOFF（下記参照） |
| `gar_info_recieve.py` | 受信処理の初期検討イメージ（PASS1/2/3形式） | 未使用（参考のみ、実際はCAN:/PETBOTTLE:/BURNABLE:形式） |

## 🖥 全体構成（本番はノートPC1台に集約）

```
[リーダーのノートPC（本番機）]
 - RealSenseカメラ（USB接続）
 - サーボ制御Arduino（USB接続、servo_3.ino）
 - カウント用Arduino（USB接続、GarbageCounter.ino）
 - ai_core/State machine.py（AI推論・頭脳）
     ├─ server/serial_control.py を直接import（同じPC上のCOMポートに接続）
     └─ POST http://localhost:5000/api/feed
 - server/app.py（Flask：API + Web画面配信、同じPC上）
 - server/sensor_bridge.py（同じPC上、任意）
 - VOICEVOXアプリ（同じPC上）
```

**すべて1台のノートPCに集約する構成です。** RealSenseカメラ、サーボ制御用Arduino、
カウント用Arduinoの3つのUSBデバイスをすべてこのPCに接続します。

> ハッカソン運営（ネットワークチーム）から`team番号.hackit`宛にSSH接続できる
> 仮想マシン（Ubuntu 24.04）が配布されていますが、これはUSB経由のシリアル通信を
> 直接受けられないため、本番のハードウェア連携（サーボ・センサー）には使用しません。

**本番当日の注意**：会場ではモバイルホットスポットの使用が禁止されている可能性がある
（電波混線対策）。スマホからWeb画面へアクセスする方法は、PCとスマホを両方とも
会場WiFi「KIT-GUEST3」に繋いで直接アクセスする方法（Plan A）と、それがダメだった場合に
上記の仮想マシンをWeb画面だけの中継点として使う方法（Plan B）の2段階を用意している。
詳細は[`../network_relay/README.md`](../network_relay/README.md)を参照。

---

## 📄 各プログラムの仕様・呼び出しルール

### 1. `app.py`（Flask Web APIサーバー + Web画面配信）

`http://<このPCのIP>:5000/` にアクセスすると、1年生C担当のステータス画面
（`../site_flog/index.html`）がそのまま表示される（Flaskから直接配信するよう統合済み）。

#### API仕様（仕様書0-2節に準拠）

- `GET /api/status` … 満腹度・レベル・経験値・種類別カウントをJSONで返す
- `POST /api/feed` … `{"type": "petbottle"|"can"|"burnable", "correct": true}` を受け取り、
  該当カウント+1・EXP加算・レベル/満腹度を再計算する（呼び出し元は`sensor_bridge.py`。
  【方針確定・8/2】詳細は下記「二重カウントに関する注意」参照）

### 2. `serial_control.py`（フタ開閉Arduino向けシリアル通信）

PCからArduino（サーボ制御・`servo_3.ino`書き込み側）に対して、フタの開閉命令を送信します。

* **ボーレート:** `9600`
* **接続ポート:** `PORT`変数で設定（既定 `COM4`、環境に合わせて変更）
  * Windowsの場合は、**デバイスマネージャー** を開き、「ポート (COM と LPT)」項目から
    接続中のArduinoが割り当てられている `COM` の後の数字を確認してください。
  * サーボ用Arduinoとカウント用Arduino（`sensor_bridge.py`が使う方）は
    **物理的に別ポート**になるので、2台とも接続した状態でデバイスマネージャーを開き、
    どちらがどのCOM番号か確認すること。

```python
def open_lid(servo_num) -> bool:
    """
    指定した投入口のフタを開けるコマンドをArduinoへ送信する。
    servo_num: 1（ペットボトル）/ 2（缶）/ 3（燃えるゴミ）
    戻り値: 送信成功時 True
    """
```

`servo_3.ino` は3口分（servoNum 1〜3）に対応済み。

### 3. `sensor_bridge.py`（フォトインタラプタ・カウント検知、補助機能）

投入口を実際にゴミが通過したことを、`web/GarbageCounter/GarbageCounter.ino` を書き込んだ
**もう1台の別Arduino**（フォトインタラプタ3個）で検知し、`CAN:`/`PETBOTTLE:`/`BURNABLE:` という
テキストをシリアルで送ってくる想定です。`app.py`と同じPC上で実行するため、
Flaskへは`localhost`でアクセスします。

#### ⚠️ 二重カウントに関する注意

【方針確定・8/2リーダー判断】カウントの正規ルートは **`sensor_bridge.py`が
物理センサー（フォトインタラプタ）の通過を検知した瞬間にPOST /api/feedを呼ぶ方式**に
決定した（仕様書0-2節では当初「AI判定確定時」が正規ルートだったが変更）。
`ai_core/State machine.py`側の`post_feed(...)`呼び出しも同時にオンだと、投入1個につき
AI側とセンサー側で二重にカウントされてしまうため、そちらは3箇所ともコメントアウト済み。

そのため `sensor_bridge.py` の `ENABLE_DIRECT_FEED_POST` は `True` にしてあり、
カウント用Arduinoが`CAN:`/`PETBOTTLE:`/`BURNABLE:`を送ってきた時点でFlaskへ送信される。

もし今後「AI判定確定を正規ルートに戻す」方針に変更する場合は、
1. `sensor_bridge.py` の `ENABLE_DIRECT_FEED_POST` を `False` にする
2. `ai_core/State machine.py` 側の `post_feed(...)` 呼び出し（3箇所）のコメントアウトを解除する

の**両方**をセットで行ってください（片方だけ変更すると二重カウント／未カウントになります）。

---

## 🚀 実行・セットアップ手順

### 1. 事前準備（事前テスト & シリアルポート解放）

**Arduino IDE での疎通確認**

- Arduino IDEの「シリアルモニタ」を開き、センサやサーボの通信値が正しく読み取れることを確認する
- **⚠️【最重要注意点】確認完了後、Arduino IDEのシリアルモニタは必ず閉じておくこと**
  （シリアルモニタが開いたままだとポートが占有され、後続のPythonスクリプトから通信エラーになる）

### 2. システムの起動手順（すべて同じPC上、別ターミナルで）

```bash
cd server
python app.py             # ターミナル1：Flask（API + Web画面）
python sensor_bridge.py   # ターミナル2：カウント用Arduinoの橋渡し（任意）
```

```bash
cd ai_core
python "State machine.py" # ターミナル3：AI推論・ステートマシン本体
```

事前にVOICEVOXアプリを起動しておくこと（`voice/README.md`参照）。
リポジトリ直下の `run_demo.bat` を使うとFlask起動〜State machine.py起動までまとめて行えます。

### 3. Web画面へのアクセス確認

会場ではモバイルホットスポットが禁止の可能性があるため、まずPCとスマホを両方
「KIT-GUEST3」に接続した状態で試すこと（Plan A、詳細は[`../network_relay/README.md`](../network_relay/README.md)）。
ホットスポットが使える場合は、ノートPCをモバイルホットスポット化してその
ローカルIPアドレスへスマホから接続してもよい。

ブラウザ／スマホで `http://<このPCのIP>:5000/` にアクセスする（QRコードもこのURLで生成する）。
IPアドレスは`ipconfig`（KIT-GUEST3またはモバイルホットスポット用アダプター）で確認。

#### スマホから見えない場合のチェックリスト

コード側（`host="0.0.0.0"`・`CORS(app)`・相対パスfetch）は外部アクセスに対応済みだが、
実機では以下でつまずきやすいので、**本番前に一度必ずスマホで疎通確認しておくこと**：

1. **Windowsファイアウォールの許可ダイアログ**：`python app.py`を初めて実行したとき、
   「Windows セキュリティの重要な警告」ダイアログが出ることがある。ここで
   **「プライベートネットワーク」にチェックを入れて「アクセスを許可する」を押す**こと
   （拒否した/見逃した場合は、コントロールパネル→Windows Defender ファイアウォール→
   アプリのアクセス許可 から`python.exe`を手動で有効化する）
2. **`localhost`ではなくPCの実際のIPアドレスを使う**：スマホからは`http://localhost:5000/`
   ではアクセスできない。`ipconfig`で確認したホットスポット用アダプターのIPv4アドレスを使う
3. **スマホとPCが同じネットワークにいること**：PCのモバイルホットスポットにスマホが
   接続できているか確認する（会場Wi-Fiに両方繋いでも、ネットワーク分離設定で
   端末間通信がブロックされている場合があるため、確実なのはPC自身のホットスポット）
4. 上記を確認してもダメな場合は、`python app.py`実行中のターミナルにアクセスログ
   （`GET /api/status HTTP/1.1`等）が出るかを見て、リクエストがそもそも届いているか切り分ける

---

## 進行メモ

- `site_flog/app.py`・`site_flog/server.js` は初期検討時の別実装で、現在は使用しません
  （API配信・Web画面配信は本ファイルの `app.py` に統合済み）。ファイル冒頭にその旨コメントを追記済みです。
- `gar_info_recieve.py` は初期検討時のイメージスニペットで未使用です。
