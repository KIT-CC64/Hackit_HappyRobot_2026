# AI判定・ステートマシン（ai_core/）

RealSenseカメラで距離検知したゴミを画像分類AIで判定し、複数フレームの多数決で結果を確定したうえで、サーボ・Flask・音声再生の各モジュールを呼び出す統合スクリプト（`State machine.py`）です。

## 概要

1. **AI推論のブレを抑制**：1フレームごとの判定ブレを、複数フレームの多数決（時間方向の平滑化）で安定させる
2. **距離検知→画像取得→AI判定→状態遷移**を1つのステートマシンとして実装
3. シリアル通信・Flask・音声の各モジュールが未接続でもスタブ動作にフォールバックし、単体テストが可能

## 動作環境・事前準備

- Intel RealSenseカメラ
- Python 3.9+

```bash
pip install -r requirements.txt
```

- `mediapipe`：ゴミをかざす手を判定対象から除外するために使用。手検出モデル`hand_landmarker.task`を`ai_core`フォルダに配置してください。
  ```bash
  curl -L -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
  ```
- `server/serial_control.py`（`open_lid(servo_num)`）は自動でパス解決されるため、`server`フォルダに置いてあれば動作します。

## 使い方

```bash
python "State machine.py"
```

- ゴミをカメラにかざして数フレーム静止させると判定が確定し、OPEN状態に遷移
- `q`：終了
- 手動フェイルセーフ：`1`=ペットボトル / `2`=缶 / `3`=燃えるゴミ をキー入力するとAI判定を無視して強制的にOPEN状態へ
- `4`：強制的にRETRY状態へ（「もう一回近づけてケロ」）

## ステートマシン

```
IDLE ──(物体検知)──▶ DETECT ──(WINDOW_SIZE枚たまる)──▶ JUDGE
  ▲                     │                                 │
  │              (物体が離れる)                    多数決が閾値未満
  │                     │                                 ▼
  │                     └───────────────────────────── RETRY ──▶ DETECT
  │
  │                                        多数決成立 / 手動フェイルセーフ
  │                                                        ▼
COOLDOWN ◀── THANKS ◀── OPEN（サーボ・Flask・音声を呼び出し）
```

| 状態 | 内容 |
|---|---|
| `IDLE` | 待機中。距離ゲート内に物体が入るとDETECTへ |
| `DETECT` | フレームごとに分類し結果をバッファへ蓄積。動きすぎるとバッファをリセット |
| `JUDGE` | バッファ内の多数決を取り、閾値を満たせばOPENへ。満たさなければRETRYへ |
| `RETRY` | 判定不能時の一時状態。一定時間後にDETECTへ戻る |
| `OPEN` | フタを開ける想定時間だけ待機（サーボ制御・Flask送信・音声再生を実行） |
| `THANKS` | お礼演出の時間だけ待機 |
| `COOLDOWN` | 物体がカメラから離れるまで待機。離れたらIDLEへ戻る |

## 主要な設定値（`State machine.py` 冒頭）

| 変数名 | 役割 |
|---|---|
| `DETECT_MIN_M` / `DETECT_MAX_M` | 距離ゲートの範囲（m）。使用カメラのMin-Zより大きい値にすること |
| `MIN_CONTOUR_AREA` | 検出領域の最小ピクセル数（ノイズ除去用） |
| `HAND_EXCLUDE_PAD_PX` | 手の矩形をこの分だけ外側に広げてから判定対象から除外 |
| `HAND_LANDMARKER_MODEL_PATH` | `hand_landmarker.task`モデルファイルのパス |
| `MOVEMENT_THRESHOLD_PX` | これ以上動くと「まだ静止していない」とみなしバッファをリセット |
| `WINDOW_SIZE` | 多数決に使うフレーム数 |
| `CONSENSUS_RATIO` | バッファ内で同じラベルが占める割合がこれ以上なら確定 |
| `CONFIDENCE_THRESHOLD` | 1フレームごとの最低確信度（未満は`unknown`扱い） |
| `MAX_RETRY` | JUDGE失敗の連続回数の上限 |
| `FAILSAFE_DEFAULT_AFTER_RETRIES` | 規定回数失敗後に自動確定させる種類（`None`なら無効） |
| `OPEN_DURATION_SEC` / `THANKS_DURATION_SEC` / `RETRY_MESSAGE_DURATION_SEC` | 各状態の待機時間 |
| `MODEL_NAME` | 使用する画像分類モデル（`yangy50/garbage-classification`） |
| `LABEL_MAP` | モデルの出力ラベルを`petbottle`/`can`/`burnable`にマッピング |
| `SERVO_NUM_MAP` | ゴミ種別とサーボ番号の対応表 |

## 他モジュールとのインターフェース

| 関数 | 呼び出し先 | 未接続時の挙動 |
|---|---|---|
| `send_serial_command(gomi_type)` | `server/serial_control.py`の`open_lid(servo_num)` | `[STUB]`ログのみで継続 |
| `post_feed(gomi_type, correct)` | Flask `POST /api/feed`（`server/app.py`） | `[STUB]`ログのみで継続 |
| `play_voice(gomi_type, streak_count)` | `voice/voice_control.py` | `[STUB]`ログのみで継続 |
| `play_retry_voice()` | `voice/voice_control.py` | 同上 |

ゴミのカウント確定は`server/sensor_bridge.py`（物理センサー通過検知）を正規ルートとしており、二重カウント防止のため本スクリプト側の`post_feed(...)`呼び出しはコメントアウトしています。詳細は`server/README.md`を参照してください。

## 実行構成

`server/app.py`・`server/sensor_bridge.py`・`ai_core/State machine.py`はすべて同じノートPC上で実行する構成です。リポジトリ直下の`run_demo.bat`でまとめて起動できます。

1. VOICEVOXアプリ（`voice/README.md`参照）
2. `python server/app.py`
3. `python "ai_core/State machine.py"`

いずれかが未起動でも、対応する機能だけスタブ動作にフォールバックしてデモは止まりません。

## 既知の制限

- カメラ・モデルのパラメータ（距離ゲート・閾値など）は実機で調整することが前提
- Flask・シリアル通信・音声（VOICEVOX）はそれぞれ未接続の環境ではスタブ動作（ログのみ）になる
