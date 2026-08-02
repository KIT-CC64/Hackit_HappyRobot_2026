# AI判定 - ケロッと！はらぺこエコガエル

ゴミ分別ロボット「ケロッと！はらぺこエコガエル」のAI判定・ステートマシン統合スクリプト（`State machine.py`）です。
RealSenseカメラで距離を測ってゴミを検知し、複数フレームの画像分類結果を多数決で確定させたうえで、
サーボ（フタ開閉）・Flaskサーバー・音声再生の各モジュールを呼び出します。

## このスクリプトが解決すること

1. **AI推論のブレを抑える**
   1フレームごとに「ペットボトル」「缶」…と判定がブレる問題を、複数フレームの多数決（時間方向の平滑化）で安定させてから確定する。
2. **頭脳部分（タスク4-3）の実装**
   距離検知 → 画像取得 → AI判定 → 状態遷移、という一連の流れを1つのステートマシンとして実装する。
3. **他パート未完成でも単体テスト可能にする**
   シリアル通信（2年生B）／Flask（2年生B）／音声（1年生A）は、まだ相手の実装が無くても動くように
   スタブ関数にしてある。サーバー担当の完成を待たずにこの1本で単体テストを進められ、
   本実装ができたらスタブ関数の中身だけ差し替えればよい。

## 動作環境・事前準備

- Intel RealSenseカメラ（距離検知に使用）
- Python 3.9+ を推奨

```bash
pip install pyrealsense2 opencv-python transformers torch pillow numpy requests mediapipe
```

- `mediapipe`はゴミをかざす手/腕を判定対象から除外するために使用（MediaPipe Tasks APIの`HandLandmarker`を利用。未インストールでも動作は止まるが、除外が効かず誤判定が起きやすくなる）
- 手検出モデルファイル`hand_landmarker.task`を`ai_core`フォルダに配置すること（未配置でも動作は止まるが除外が無効になる）
  ```bash
  curl -L -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
  ```

- 2年生B担当の `serial_control.py` を `State machine.py` と同じフォルダに置くこと
  （`open_lid(servo_num: int) -> bool` を提供する想定）
  - 置かれていない／importできない場合は自動でスタブ動作になり、処理は止まらない

## 使い方

```bash
python "State machine.py"
```

- ゴミをカメラにかざして数フレーム静止させると、判定が確定してOPEN状態に遷移する
- `q` キーで終了
- **手動フェイルセーフ**：`1`=ペットボトル / `2`=缶 / `3`=燃えるゴミ をキー入力すると、
  AI判定を無視して強制的にOPEN状態へ遷移できる（本番デモでAIが誤判定・無反応のときの保険）
- **手動リトライ**：`4`キーで強制的にRETRY状態へ遷移できる（「もう一回近づけてケロ」音声を再生してDETECTからやり直す）

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
| `HAND_EXCLUDE_PAD_PX` | MediaPipe Handsで検出した手の矩形をこの分だけ外側に広げてから判定対象（深度マスク）から除外する |
| `HAND_LANDMARKER_MODEL_PATH` | `hand_landmarker.task`モデルファイルのパス（既定は`ai_core`フォルダ直下） |
| `MOVEMENT_THRESHOLD_PX` | これ以上動くと「まだ静止していない」とみなしバッファをリセット |
| `WINDOW_SIZE` | 多数決に使うフレーム数 |
| `CONSENSUS_RATIO` | バッファ内で同じラベルが占める割合がこれ以上なら確定 |
| `CONFIDENCE_THRESHOLD` | 1フレームごとの最低確信度（未満は`unknown`扱い） |
| `MAX_RETRY` | JUDGE失敗の連続回数の上限（フェイルセーフ検討の目安） |
| `FAILSAFE_DEFAULT_AFTER_RETRIES` | 例: `"burnable"` にすると規定回数失敗後に自動でその扱いにする（`None`なら無効） |
| `OPEN_DURATION_SEC` / `THANKS_DURATION_SEC` / `RETRY_MESSAGE_DURATION_SEC` | 各状態の待機時間（実機のタイミングに合わせて調整） |
| `MODEL_NAME` | 使用する画像分類モデル（`yangy50/garbage-classification`） |
| `LABEL_MAP` | モデルの出力ラベルを `petbottle` / `can` / `burnable` にマッピング |
| `SERVO_NUM_MAP` | ゴミ種別とサーボ番号（`open_lid`引数）の対応表 |

すべて実機で調整しながら値を決めることを想定しています。

## 他パートとのインターフェース

| 関数 | 呼び出し先 | 担当 | 状態 | 未接続時の挙動 |
|---|---|---|---|---|
| `send_serial_command(gomi_type)` | `serial_control.open_lid(servo_num)` | 2年生B | 未実装（スタブ） | `[STUB]` ログのみ出力して継続 |
| `post_feed(gomi_type, correct)` | Flask `POST /api/feed`（`http://localhost:5000`） | 2年生B | 未実装（スタブ） | 例外を握りつぶし `[STUB]` ログを出力して継続 |
| `play_voice(gomi_type, streak_count)` | `voice/voice_control.py`（VOICEVOX音声再生） | 1年生A | **実装済み** | `voice_control.py`が無い/import失敗/VOICEVOX ENGINE未起動の場合は`[STUB]`ログのみで継続 |
| `play_retry_voice()` | `voice/voice_control.py`（「もう一回近づけてケロ」音声） | 1年生A | **実装済み** | 同上 |

音声まわりは`voice/voice_control.py`が同階層の`voice`フォルダにあれば自動でそちらに委譲される。
セットアップ手順・カスタマイズ方法は`voice/README.md`を参照。
残りのスタブ関数も、本実装ができたら中身だけ差し替えれば良い設計です。

## 要確認・要相談（チームに投げてほしい項目）

- 2年生Bの `serial_control.py`（`open_lid(servo_num: int)`）は現状 `servo_num=1`（petbottle）,
  `2`（can）しか定義が無い模様。「燃えるゴミ用の口を開けるservo_num」が未定義なので、
  1年生B・2年生Bと仕様を詰めてください。
  `SERVO_NUM_MAP`では仮に`3`を割り当てています。インターフェースは今後変更あるかもとのことなので、
  変更されたら`SERVO_NUM_MAP`と`send_serial_command()`だけ直せば追従できます。

## 既知の制限

- カメラ・モデルの実機依存が強く、パラメータ（距離ゲート・閾値など）は実測しながらの調整が前提
- Flask/シリアルは未接続の環境ではスタブ動作となる。音声（VOICEVOX）は実装済みだが、
  VOICEVOX ENGINEが起動していない環境では同様にスタブ動作（ログのみ）になる
