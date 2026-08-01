"""
ケロッと！はらぺこエコガエル - ステートマシン統合スクリプト（2年生A担当）
 
【このスクリプトで解決すること】
1. AI推論が1フレームごとに「ペットボトル」「缶」...とブレる問題
   → 複数フレームの多数決（時間方向の平滑化）で安定させてから確定する
2. 距離検知→画像取得→AI判定→状態遷移という頭脳部分（タスク4-3）を実装
3. シリアル通信（2年生B）／Flask（2年生B）／音声（1年生A）は
   まだ相手の実装が無くても動くように「スタブ関数」にしてある
   → サーバー担当の完成を待たずに、この1本で単体テストを進められる
   → 本実装ができたら、スタブ関数の中身だけ差し替えればよい
 
【事前準備】
    pip install pyrealsense2 opencv-python transformers torch pillow numpy pyserial requests
 
【使い方】
    python state_machine.py
    - ゴミをかざして数フレーム静止させると判定が確定してOPEN状態に遷移する
    - 'q' 終了
    - 手動フェイルセーフ：'1'=ペットボトル / '2'=缶 / '3'=燃えるゴミ を
      キー入力するとAI判定を無視して強制的にOPENへ遷移できる
      （本番デモでAIが誤判定・無反応のときの保険として用意）
 
【要確認・要相談（チームに投げてほしい項目）】
    - シリアル仕様（0-1節）には "1"=petbottle, "2"=can, "0"=全閉 しか
      定義がなく、"燃えるゴミ用の口を開けるコード" が未定義。
      3口目があるなら "3" を追加するか、1年生B・2年生Bと仕様を詰めてください。
      （下のSERVO_CODE_MAPは仮に"3"を割り当てています）
"""
 
import time
from collections import deque, Counter
from enum import Enum, auto
 
import cv2
import numpy as np
import pyrealsense2 as rs
from transformers import pipeline
from PIL import Image
 
# ============================================================
# 設定値（実測しながら調整すること）
# ============================================================
DETECT_MIN_M = 0.30          # 距離ゲート下限（使用カメラのMin-Zより大きく）
DETECT_MAX_M = 0.50          # 距離ゲート上限
MIN_CONTOUR_AREA = 3000      # 検出領域の最小ピクセル数（ノイズ除去用）
MOVEMENT_THRESHOLD_PX = 15   # これ以上動いたら「まだ静止してない」とみなしバッファをリセット
 
WINDOW_SIZE = 6              # 何フレーム分の判定を貯めてから多数決するか
CONSENSUS_RATIO = 0.6        # このバッファの中で同じラベルが何割以上を占めたら確定とするか
CONFIDENCE_THRESHOLD = 0.5   # 1フレームごとの最低確信度（これ未満は"unknown"扱い）
 
MAX_RETRY = 3                # 何回連続でJUDGEに失敗したらフェイルセーフを検討するか
FAILSAFE_DEFAULT_AFTER_RETRIES = None  # 例: "burnable" にすると規定回数失敗後に自動でその扱いにする（Noneなら無効）
 
OPEN_DURATION_SEC = 3.0      # フタを開けている想定時間（1年生Aの実機タイミングに合わせて調整）
THANKS_DURATION_SEC = 1.5    # お礼演出の時間
RETRY_MESSAGE_DURATION_SEC = 1.0
 
MODEL_NAME = "yangy50/garbage-classification"
LABEL_MAP = {
    "plastic": "petbottle",
    "glass": "petbottle",
    "metal": "can",
    "cardboard": "burnable",
    "paper": "burnable",
    "trash": "burnable",
}
 
SERVO_CODE_MAP = {
    "petbottle": "1",
    "can": "2",
    "burnable": "3",  # ← 要確認（上部の注意書き参照）
}
 
 
# ============================================================
# 状態定義（タスク4-3準拠）
# ============================================================
class State(Enum):
    IDLE = auto()
    DETECT = auto()
    JUDGE = auto()
    OPEN = auto()
    THANKS = auto()
    COOLDOWN = auto()
    RETRY = auto()
 
 
# ============================================================
# 他担当インターフェースのスタブ（本実装ができたら中身だけ差し替える）
# ============================================================
_serial_conn = None
 
 
def send_serial_command(gomi_type):
    """2年生B担当：本来は pyserial 経由でArduinoに1文字+改行を送る関数。
    実機シリアルが繋がっていなければログ出力のみのスタブ動作にフォールバックする。
    """
    code = SERVO_CODE_MAP.get(gomi_type)
    if code is None:
        print(f"[WARN] '{gomi_type}' に対応するシリアルコードが未定義です")
        return
    global _serial_conn
    if _serial_conn is None:
        try:
            import serial
            _serial_conn = serial.Serial("COM3", 9600, timeout=1)  # ポート名は要確認
        except Exception as e:
            print(f"[STUB] シリアル未接続のためスタブ動作: {e}")
    if _serial_conn is not None:
        try:
            _serial_conn.write(f"{code}\n".encode())
        except Exception as e:
            print(f"[WARN] シリアル送信失敗: {e}")
    else:
        print(f'[STUB] シリアル送信: "{code}\\n"')
 
 
def post_feed(gomi_type, correct=True):
    """2年生B担当：Flaskの POST /api/feed を呼ぶ関数。
    サーバーが未起動でも例外を握りつぶしてスタブとして継続する。
    """
    try:
        import requests
        requests.post(
            "http://localhost:5000/api/feed",
            json={"type": gomi_type, "correct": correct},
            timeout=0.5,
        )
    except Exception as e:
        print(f"[STUB] Flask送信スキップ（サーバー未起動の可能性）: {e}")
 
 
def play_voice(gomi_type, streak_count):
    """1年生A担当：VOICEVOXでセリフを喋らせる関数。
    まだ実装が無いのでprintだけのスタブ。
    """
    print(f"[STUB] 音声再生: type={gomi_type}, streak={streak_count}")
 
 
def play_retry_voice():
    """1年生A担当：「もう一回近づけてケロ」用のスタブ。"""
    print("[STUB] 音声再生: もう一回近づけてケロ")
 
 
# ============================================================
# 距離ゲート付き物体検出（前回渡したv2スクリプトと同じロジック）
# ============================================================
def get_object_bbox(depth_image, depth_scale):
    depth_m = depth_image.astype(np.float32) * depth_scale
    mask = np.where(
        (depth_m > DETECT_MIN_M) & (depth_m < DETECT_MAX_M), 255, 0
    ).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_CONTOUR_AREA:
        return None
    return cv2.boundingRect(largest)
 
 
def classify_crop(classifier, color_image, bbox):
    x, y, w, h = bbox
    pad = 10
    x0, y0 = max(x - pad, 0), max(y - pad, 0)
    x1 = min(x + w + pad, color_image.shape[1])
    y1 = min(y + h + pad, color_image.shape[0])
    crop = color_image[y0:y1, x0:x1]
    rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    result = classifier(Image.fromarray(rgb_crop))[0]
    raw_label, score = result["label"], result["score"]
    if score < CONFIDENCE_THRESHOLD:
        mapped = "unknown"
    else:
        mapped = LABEL_MAP.get(raw_label, "unknown")
    return mapped, raw_label, score
 
 
def decide_consensus(buffer):
    """バッファ内(mapped_labelのリスト)から多数決を取る。"""
    labels = [item[0] for item in buffer]
    counts = Counter(labels)
    top_label, top_count = counts.most_common(1)[0]
    ratio = top_count / len(buffer)
    scores = [item[2] for item in buffer if item[0] == top_label]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    return top_label, ratio, avg_score
 
 
# ============================================================
# メインループ（ステートマシン本体）
# ============================================================
def main():
    print("モデルを読み込み中...")
    classifier = pipeline("image-classification", model=MODEL_NAME)
 
    rs_pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    profile = rs_pipeline.start(config)
    depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
    align = rs.align(rs.stream.color)
 
    state = State.IDLE
    buffer = deque(maxlen=WINDOW_SIZE)
    last_center = None
    retry_count = 0
    streak_count = 0
    committed_label = None
    state_entered_at = time.time()
 
    print("起動完了。'q'で終了 / '1','2','3'で手動フェイルセーフ")
 
    try:
        while True:
            frames = rs_pipeline.wait_for_frames()
            aligned = align.process(frames)
            depth_frame = aligned.get_depth_frame()
            color_frame = aligned.get_color_frame()
            if not depth_frame or not color_frame:
                continue
 
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            bbox = get_object_bbox(depth_image, depth_scale)
 
            key = cv2.waitKey(1) & 0xFF
 
            # ---- 手動フェイルセーフ（AIを無視して強制OPEN） ----
            manual_map = {ord("1"): "petbottle", ord("2"): "can", ord("3"): "burnable"}
            if key in manual_map and state not in (State.OPEN, State.THANKS):
                committed_label = manual_map[key]
                state = State.OPEN
                state_entered_at = time.time()
                streak_count += 1
                send_serial_command(committed_label)
                post_feed(committed_label, correct=True)
                play_voice(committed_label, streak_count)
                print(f"[手動] {committed_label} を強制送信")
 
            # ---- 物体が視界から消えた場合の処理 ----
            if bbox is None:
                if state in (State.DETECT, State.JUDGE, State.RETRY):
                    # 判定確定前に物体が離れた→やり直し
                    state = State.IDLE
                    buffer.clear()
                    last_center = None
                elif state == State.COOLDOWN:
                    state = State.IDLE
                    streak_count = 0  # 連続正解カウントは物体が離れたらリセット（仕様に応じて調整）
 
            # ---- 状態ごとの処理 ----
            if state == State.IDLE:
                if bbox is not None:
                    state = State.DETECT
                    buffer.clear()
                    last_center = None
                    retry_count = 0
 
            elif state == State.DETECT:
                x, y, w, h = bbox
                cx, cy = x + w // 2, y + h // 2
                if last_center is not None:
                    moved = ((cx - last_center[0]) ** 2 + (cy - last_center[1]) ** 2) ** 0.5
                    if moved > MOVEMENT_THRESHOLD_PX:
                        buffer.clear()  # まだ動いている間はカウントしない
                last_center = (cx, cy)
 
                mapped, raw_label, score = classify_crop(classifier, color_image, bbox)
                buffer.append((mapped, raw_label, score))
 
                if len(buffer) >= WINDOW_SIZE:
                    state = State.JUDGE
 
            elif state == State.JUDGE:
                top_label, ratio, avg_score = decide_consensus(buffer)
                if top_label != "unknown" and ratio >= CONSENSUS_RATIO and avg_score >= CONFIDENCE_THRESHOLD:
                    committed_label = top_label
                    streak_count += 1
                    retry_count = 0
                    state = State.OPEN
                    state_entered_at = time.time()
                    send_serial_command(committed_label)
                    post_feed(committed_label, correct=True)
                    play_voice(committed_label, streak_count)
                    print(f"[確定] {committed_label} (一致率{ratio:.0%}, 平均確信度{avg_score:.2f})")
                else:
                    retry_count += 1
                    print(f"[判定不能] 一致率{ratio:.0%}, 平均確信度{avg_score:.2f} → リトライ{retry_count}/{MAX_RETRY}")
                    if FAILSAFE_DEFAULT_AFTER_RETRIES and retry_count >= MAX_RETRY:
                        committed_label = FAILSAFE_DEFAULT_AFTER_RETRIES
                        state = State.OPEN
                        state_entered_at = time.time()
                        streak_count += 1
                        send_serial_command(committed_label)
                        post_feed(committed_label, correct=True)
                        play_voice(committed_label, streak_count)
                        print(f"[フェイルセーフ] {committed_label} に自動確定")
                    else:
                        state = State.RETRY
                        state_entered_at = time.time()
                        buffer.clear()
                        play_retry_voice()
 
            elif state == State.RETRY:
                if time.time() - state_entered_at >= RETRY_MESSAGE_DURATION_SEC:
                    state = State.DETECT
                    last_center = None
 
            elif state == State.OPEN:
                if time.time() - state_entered_at >= OPEN_DURATION_SEC:
                    state = State.THANKS
                    state_entered_at = time.time()
 
            elif state == State.THANKS:
                if time.time() - state_entered_at >= THANKS_DURATION_SEC:
                    state = State.COOLDOWN
                    state_entered_at = time.time()
 
            elif state == State.COOLDOWN:
                pass  # 物体が離れるのを待つ（上のbbox is Noneブロックで処理済み）
 
            # ---- 描画 ----
            if bbox is not None:
                x, y, w, h = bbox
                cv2.rectangle(color_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            info = f"STATE={state.name}"
            if state == State.DETECT:
                info += f"  buffer={len(buffer)}/{WINDOW_SIZE}"
            if committed_label and state in (State.OPEN, State.THANKS, State.COOLDOWN):
                info += f"  label={committed_label}  streak={streak_count}"
            cv2.putText(color_image, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow("Kerotto State Machine", color_image)
 
            if key == ord("q"):
                break
 
    finally:
        rs_pipeline.stop()
        cv2.destroyAllWindows()
 
 
if __name__ == "__main__":
    main()