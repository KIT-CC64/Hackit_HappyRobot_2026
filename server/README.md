# 🐸 ケロッと！はらぺこエコガエル - サーバー・通信（2年生B担当）README

「PC↔Arduino間のシリアル通信」と「Webステータス管理Flaskサーバー」の実装・設定・トラブルシューティングガイドです。

---

## 📁 プログラム構成一覧

| ファイル | 役割 | 実行場所 | 状態 |
|---|---|---|---|
| `app.py` | Flask Webサーバー（API配信 + Web画面配信を統合） | **仮想マシン** | **メインで使用** |
| `sensor_bridge.py` | フォトインタラプタ用Arduino（`web/GarbageCounter/GarbageCounter.ino`）からのカウント通過検知を橋渡し | **仮想マシン**（`app.py`と同じマシン） | 補助・デフォルトOFF（下記参照） |
| `serial_control.py` | サーボ制御Arduino（`arduino/servo_3/servo_3.ino`）向けのシリアル通信モジュール | **ホストPC**（`ai_core/State machine.py`から呼ばれる） | **メインで使用** |
| `gar_info_recieve.py` | 受信処理の初期検討イメージ（PASS1/2/3形式） | - | 未使用（参考のみ、実際はCAN:/PETBOTTLE:/BURNABLE:形式） |

## 🖥 全体構成（2台のマシン + 2台のArduino）

```
[ホストPC（ノートPC・本番機）]                [仮想マシン（2年生B開発環境）]
 - RealSenseカメラ                              - server/app.py（Flask）
 - サーボ制御Arduino（servo_3.ino, COM4）         - server/sensor_bridge.py
 - ai_core/State machine.py                       - カウント用Arduino（GarbageCounter.ino）
     ├─ server/serial_control.py を直接import
     │   （同じホスト上のCOM4に直接接続）
     └─ POST http://<仮想マシンIP>:5000/api/feed
         （FLASK_SERVER_URL、要ネットワーク到達性）
```

**重要**：ホストPCと仮想マシンは別マシン扱いなので、`ai_core/State machine.py`から
Flaskへ`localhost`ではアクセスできない。仮想マシンのIPアドレスへ直接アクセスする
（`ai_core/State machine.py`冒頭の`FLASK_SERVER_URL`）。

**本番当日の注意**：スマホからQRコードでWeb画面にアクセスするには、会場のWi-Fi/モバイル
ホットスポットのネットワークから仮想マシンのIPアドレスに到達できる必要がある
（仮想マシンのネットワークアダプタ設定がNATのみだと外から届かない可能性があるので、
ブリッジ接続になっているか事前に必ず確認すること）。

---

## 📄 各プログラムの仕様・呼び出しルール

### 1. `app.py`（Flask Web APIサーバー + Web画面配信）

`http://<仮想マシンのIP>:5000/` にアクセスすると、1年生C担当のステータス画面
（`../site_flog/index.html`）がそのまま表示される（Flaskから直接配信するよう統合済み）。

#### API仕様（仕様書0-2節に準拠）

- `GET /api/status` … 満腹度・レベル・経験値・種類別カウントをJSONで返す
- `POST /api/feed` … `{"type": "petbottle"|"can"|"burnable", "correct": true}` を受け取り、
  該当カウント+1・EXP加算・レベル/満腹度を再計算する（呼び出し元は `ai_core/State machine.py` の `post_feed()`）

### 2. `serial_control.py`（フタ開閉Arduino向けシリアル通信）

PCからArduino（サーボ制御・`servo_3.ino`書き込み側）に対して、フタの開閉命令を送信します。

* **ボーレート:** `9600`
* **接続ポート:** `PORT`変数で設定（既定 `COM4`、環境に合わせて変更）
  * Windowsの場合は、**デバイスマネージャー** を開き、「ポート (COM と LPT)」項目から
    接続中のArduinoが割り当てられている `COM` の後の数字を確認してください。

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
テキストをシリアルで送ってくる想定です。`app.py`と同じ仮想マシン上で実行するため、
Flaskへは`localhost`でアクセスします。

#### ⚠️ 二重カウントに関する注意

カウントの正規ルートは **AIが判定を確定した瞬間に `ai_core/State machine.py` が
`POST /api/feed` を呼ぶ方式**（仕様書0-2節どおり）です。`sensor_bridge.py` も同時に
`/api/feed` を叩くと、投入1個につきAI側とセンサー側で二重にカウントされてしまいます。

そのため `sensor_bridge.py` の `ENABLE_DIRECT_FEED_POST` は既定で `False` にしてあり、
現状はセンサー検知をコンソールに表示するだけ（Flaskへは送信しない）動作です。

もし方針を変えたい場合は、
1. `sensor_bridge.py` の `ENABLE_DIRECT_FEED_POST` を `True` にする
2. `ai_core/State machine.py` 側の `post_feed(...)` 呼び出しをコメントアウトする

の**両方**をセットで行ってください（片方だけ変更すると二重カウント／未カウントになります）。

---

## 🚀 実行・セットアップ手順

### 1. 事前準備（事前テスト & シリアルポート解放）

**Arduino IDE での疎通確認**

- Arduino IDEの「シリアルモニタ」を開き、センサやサーボの通信値が正しく読み取れることを確認する
- **⚠️【最重要注意点】確認完了後、Arduino IDEのシリアルモニタは必ず閉じておくこと**
  （シリアルモニタが開いたままだとポートが占有され、後続のPythonスクリプトから通信エラーになる）

### 2. システムの起動手順

**Step 1: 仮想マシンでの Web API サーバー起動**

```bash
cd server
python app.py
```

**Step 2: センサーブリッジ（`sensor_bridge.py`）の実行**（仮想マシン上で、別ターミナル）

```bash
cd server
python sensor_bridge.py
```

**Step 3: ホストPCでのAI推論・ステートマシン起動**

```bash
cd ai_core
python "State machine.py"
```

事前にVOICEVOXアプリを起動しておくこと（`voice/README.md`参照）。

**Step 4: Web画面へのアクセス確認**

ブラウザ／スマホで `http://<仮想マシンのIP>:5000/` にアクセスする
（QRコードもこのURLで生成する）。IPアドレスは仮想マシンのネットワーク設定に依存するため、
本番前に必ず`ipconfig`（仮想マシン側）で最新の値を確認し、`ai_core/State machine.py`冒頭の
`FLASK_SERVER_URL`が同じ値になっているか確認すること。

---

## 進行メモ

- `site_flog/app.py`・`site_flog/server.js` は初期検討時の別実装で、現在は使用しません
  （API配信・Web画面配信は本ファイルの `app.py` に統合済み）。ファイル冒頭にその旨コメントを追記済みです。
- `gar_info_recieve.py` は初期検討時のイメージスニペットで未使用です。
