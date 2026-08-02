# 🐸 ケロッと！はらぺこエコガエル（分別強制ゴミ箱）

ハッカソンテーマ『突破』：ゴミをかざすと、RealSenseカメラと画像認識AIが種類を判別し、
正解のゴミ箱（カエルの口）だけが物理的にパカッと開いて可愛い声で喋る、分別強制ゴミ箱です。
人間のモラルに依存していた分別を「正解の口しか開かない」という物理的制限と
「エサやりゲーム」というエンタメ体験で突破します。

## 全体構成

本番デモは **ホストPC（ノートPC）** と **仮想マシン** の2台のマシン、
**2台のArduino** で構成されます。

```
[ホストPC（本番ノートPC）]                    [仮想マシン（2年生B開発環境）]
 - RealSenseカメラ（USB接続）                    - server/app.py（Flask：API + Web画面配信）
 - サーボ制御Arduino（USB, servo_3.ino）           - server/sensor_bridge.py（補助）
 - ai_core/State machine.py（AI推論・頭脳）        - カウント用Arduino（USB, GarbageCounter.ino）
     ├─ server/serial_control.py 経由でサーボ制御
     ├─ POST /api/feed で仮想マシンのFlaskへ通知
     └─ voice/voice_control.py 経由でVOICEVOX（同じホストPCで起動）
```

スマホはQRコードから `http://<仮想マシンのIP>:5000/` にアクセスし、
満腹度・レベル・投入数を見られます（会場Wi-Fi/モバイルホットスポットから
仮想マシンに到達できるネットワーク設定が必要）。

詳しい構成・起動手順は各フォルダのREADMEを参照してください：

| フォルダ | 内容 | README |
|---|---|---|
| `ai_core/` | RealSense + AI推論 + ステートマシン（2年生A担当） | [`ai_core/README.md`](ai_core/README.md) |
| `server/` | シリアル通信 + Flask APIサーバー（2年生B担当） | [`server/README.md`](server/README.md) |
| `voice/` | VOICEVOXによる音声合成（1年生A担当） | [`voice/README.md`](voice/README.md) |
| `arduino/` | サーボ制御Arduinoスケッチ（1年生A担当） | [`arduino/README.md`](arduino/README.md) |
| `web/` | カウント用Arduinoスケッチ（1年生B担当） | [`web/README.md`](web/README.md) |
| `site_flog/` | スマホ向けステータス画面（1年生C担当、`server/app.py`から配信） | - |

## クイックスタート

1. **仮想マシン側**（2年生B）
   ```bash
   pip install -r requirements.txt   # flask / flask-cors / pyserial / requests があればOK
   cd server
   python app.py           # ターミナル1：Flask（API + Web画面）
   python sensor_bridge.py # ターミナル2：カウント用Arduinoの橋渡し（任意）
   ```
2. **ホストPC側**（本番ノートPC）
   - VOICEVOXアプリを起動
   - `ai_core/State machine.py` 冒頭の `FLASK_SERVER_URL` を仮想マシンの最新IPに合わせる
   - `run_demo.bat` を実行、またはコマンドプロンプトで：
     ```bash
     pip install -r requirements.txt
     cd ai_core
     python "State machine.py"
     ```

Flask・シリアル通信・音声のいずれかが未接続でも、対応する機能だけスタブ動作
（ログ出力のみ）にフォールバックしてデモ自体は止まらない設計になっています。

## ゴミの種類とサーボ番号

| ゴミの種類 | servo_num | Flaskの`type`値 |
|---|---|---|
| ペットボトル | 1 | `petbottle` |
| 缶 | 2 | `can` |
| 燃えるゴミ | 3 | `burnable` |

## 手動フェイルセーフ（本番デモ用の保険）

`ai_core/State machine.py` 実行中、キーボードから：

- `1` / `2` / `3` … AI判定を無視して該当の口を強制的に開ける
- `4` … 強制的にRETRY状態へ（「もう一回近づけてケロ」）
- `q` … 終了

AIが誤判定・無反応でも、これで確実にデモを進行できます。

## 既知の申し送り事項

- 実機で`open_lid()`が本当にフタを開くか（統合作業で修正したパス解決バグの再テスト）
- 2台のArduinoのCOMポートを`server/serial_control.py`・`server/sensor_bridge.py`それぞれに設定
- 仮想マシンのIPアドレスが変わったら`ai_core/State machine.py`の`FLASK_SERVER_URL`を更新
- `site_flog/images/`のキャラクター画像は仮のプレースホルダー。本番イラストに差し替え
- ゴミのカウント確定は現在「AI判定確定時」が正規ルート（`server/sensor_bridge.py`のセンサー検知は
  二重カウント防止のためデフォルトでFlask送信OFF）。方針の詳細は`server/README.md`参照
