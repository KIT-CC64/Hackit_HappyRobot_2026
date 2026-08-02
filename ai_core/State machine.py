import time
from collections import deque, Counter
from enum import Enum, auto
 
import cv2
import numpy as np
import pyrealsense2 as rs
from transformers import pipeline
from PIL import Image

# 手/腕の誤反応対策：MediaPipe Hands（Tasks API）で手を検出し、判定対象から除外する
# 未インストール／モデルファイル未配置の環境でも動作は止めず、除外なしにフォールバックする
try:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import (
        HandLandmarker,
        HandLandmarkerOptions,
        RunningMode,
    )
    _HAS_MEDIAPIPE = True
except ImportError:
    _HAS_MEDIAPIPE = False
 
# 2年生B担当：serial_control.py（同じフォルダに置く想定）
# まだファイルが無い/インポートできない環境でもスタブ動作で動き続けられるようにしておく
try:
    from serial_control import open_lid
    _HAS_SERIAL_MODULE = True
except ImportError:
    _HAS_SERIAL_MODULE = False

# 1年生A担当：voice/voice_control.py（このファイルの1つ上の階層のvoiceフォルダに置く想定）
# まだファイルが無い/インポートできない環境でもスタブ動作で動き続けられるようにしておく
import os
import sys

_VOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "voice")
if _VOICE_DIR not in sys.path:
    sys.path.insert(0, _VOICE_DIR)
try:
    from voice_control import play_voice as _play_voice_impl, play_retry_voice as _play_retry_voice_impl
    _HAS_VOICE_MODULE = True
except ImportError:
    _HAS_VOICE_MODULE = False

# ============================================================
# 設定値（実測しながら調整すること）
# ============================================================
DETECT_MIN_M = 0.20          # 距離ゲート下限（使用カメラのMin-Zより大きく）
DETECT_MAX_M = 0.40          # 距離ゲート上限
MIN_CONTOUR_AREA = 3000      # 検出領域の最小ピクセル数（ノイズ除去用）
MOVEMENT_THRESHOLD_PX = 15   # これ以上動いたら「まだ静止してない」とみなしバッファをリセット
 
WINDOW_SIZE = 4              # 何フレーム分の判定を貯めてから多数決するか
CONSENSUS_RATIO = 0.6        # このバッファの中で同じラベルが何割以上を占めたら確定とするか
CONFIDENCE_THRESHOLD = 0.5   # 1フレームごとの最低確信度（これ未満は"unknown"扱い）
 
HAND_EXCLUDE_PAD_PX = 30      # 検出した手の矩形をこの分だけ外側に広げてから除外する
BORDER_TOUCH_MARGIN_PX = 20   # この分だけ画面端に接している輪郭は「フレーム外から伸びる腕」とみなして除外する
HAND_LANDMARKER_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task"
)  # https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

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
 
SERVO_NUM_MAP = {
    "petbottle": 1,
    "can": 2,
    "burnable": 3,
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
# 他担当インターフェースの呼び出し
# ============================================================
def send_serial_command(gomi_type):
    """2年生B担当 serial_control.py の open_lid(servo_num) を呼び出す。
    serial_control.py がまだ無い/実機が繋がっていない環境でも、
    ログ出力のみのスタブ動作にフォールバックして処理は止めない。
    """
    servo_num = SERVO_NUM_MAP.get(gomi_type)
    if servo_num is None:
        print(f"[WARN] '{gomi_type}' に対応するservo_numが未定義です")
        return
 
    if gomi_type == "burnable":
        # 上部の注意書き参照：2年生Bのopen_lid()にservo_num=3の定義が
        # まだ無い可能性があるため、実機テスト前に必ず確認すること
        print("[WARN] burnable用servo_num(=3)は2年生Bと要確認（open_lid仕様に未定義の可能性）")
 
    if _HAS_SERIAL_MODULE:
        try:
            success = open_lid(servo_num)
            if not success:
                print(f"[WARN] open_lid({servo_num}) がFalseを返しました")
        except Exception as e:
            print(f"[WARN] open_lid({servo_num}) 呼び出し失敗: {e}")
    else:
        print(f"[STUB] serial_control.open_lid({servo_num}) 未接続のためスタブ動作")
 
 
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
    voice/voice_control.py が読み込めていればそちらに委譲する。
    未接続・実行時エラー時は例外を握りつぶしログのみのスタブ動作にフォールバックする。
    """
    if _HAS_VOICE_MODULE:
        try:
            _play_voice_impl(gomi_type, streak_count)
            return
        except Exception as e:
            print(f"[WARN] play_voice実行時エラー、スタブ動作にフォールバック: {e}")
    print(f"[STUB] 音声再生: type={gomi_type}, streak={streak_count}")


def play_retry_voice():
    """1年生A担当：「もう一回近づけてケロ」用。voice_control.pyに委譲、失敗時はスタブ。"""
    if _HAS_VOICE_MODULE:
        try:
            _play_retry_voice_impl()
            return
        except Exception as e:
            print(f"[WARN] play_retry_voice実行時エラー、スタブ動作にフォールバック: {e}")
    print("[STUB] 音声再生: もう一回近づけてケロ")
 
 
# ============================================================
# 距離ゲート付き物体検出（前回渡したv2スクリプトと同じロジック）
# ============================================================
def create_hand_landmarker():
    """MediaPipe Tasks APIのHandLandmarkerを生成する。
    mediapipe未インストール、またはモデルファイル未配置の場合はNoneを返す（呼び出し側は除外なしにフォールバック）。
    """
    if not _HAS_MEDIAPIPE:
        print("[WARN] mediapipe未インストールのため、手/腕の除外は無効です（pip install mediapipe）")
        return None
    if not os.path.exists(HAND_LANDMARKER_MODEL_PATH):
        print(f"[WARN] 手検出モデルが見つかりません: {HAND_LANDMARKER_MODEL_PATH}")
        print("[WARN] 手/腕の除外は無効です。以下からダウンロードして配置してください:")
        print("[WARN] https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task")
        return None
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_LANDMARKER_MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return HandLandmarker.create_from_options(options)


def detect_hand_boxes(hands_detector, color_image, timestamp_ms, pad=HAND_EXCLUDE_PAD_PX):
    """MediaPipe Hands（Tasks API）で手を検出し、(x0, y0, x1, y1)の矩形リストを返す。
    未検出/未初期化時は空リスト。
    """
    if hands_detector is None:
        return []
    h, w = color_image.shape[:2]
    rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = hands_detector.detect_for_video(mp_image, timestamp_ms)
    boxes = []
    for hand_landmarks in result.hand_landmarks:
        xs = [lm.x * w for lm in hand_landmarks]
        ys = [lm.y * h for lm in hand_landmarks]
        x0 = max(int(min(xs)) - pad, 0)
        y0 = max(int(min(ys)) - pad, 0)
        x1 = min(int(max(xs)) + pad, w)
        y1 = min(int(max(ys)) + pad, h)
        boxes.append((x0, y0, x1, y1))
    return boxes


def _touches_border(x, y, w, h, frame_w, frame_h, margin=BORDER_TOUCH_MARGIN_PX):
    """輪郭のバウンディングボックスが画面端に接しているかを判定する。
    カメラの外から伸びてくる腕/手は、必ずどこかの辺でフレーム外に繋がっている＝
    画面端に接する塊になるはず、という前提で「腕らしさ」の簡易フィルタとして使う。
    （MediaPipeの手検出が漏れた/未インストールの場合の保険にもなる）
    """
    return (
        x <= margin
        or y <= margin
        or (x + w) >= (frame_w - margin)
        or (y + h) >= (frame_h - margin)
    )


def get_object_bbox(depth_image, depth_scale, exclude_rects=None):
    """距離ゲート内の輪郭から、投入されたゴミ本体と思われるものを1つ選ぶ。

    選定方針（優先順）：
      1. 画面端に接していないこと（腕はフレーム外から伸びてくるので端に接する）
      2. 面積がMIN_CONTOUR_AREA以上であること（ノイズ除去）
      3. 上記を満たす輪郭の中で、平均深度が最小＝カメラに最も近いものを採用
         （同じフレームに複数の塊が写っても「一番手前にあるもの」を優先する）
    """
    depth_m = depth_image.astype(np.float32) * depth_scale
    mask = np.where(
        (depth_m > DETECT_MIN_M) & (depth_m < DETECT_MAX_M), 255, 0
    ).astype(np.uint8)
    for x0, y0, x1, y1 in (exclude_rects or []):
        mask[y0:y1, x0:x1] = 0
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    frame_h, frame_w = mask.shape[:2]
    candidates = []
    fallback = []  # 画面端接触フィルタで候補が0件になった場合の保険（面積のみで判定）
    for c in contours:
        area = cv2.contourArea(c)
        if area < MIN_CONTOUR_AREA:
            continue
        x, y, w, h = cv2.boundingRect(c)

        contour_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.drawContours(contour_mask, [c], -1, 255, thickness=cv2.FILLED)
        mean_depth = cv2.mean(depth_m, mask=contour_mask)[0]

        entry = (mean_depth, area, (x, y, w, h))
        fallback.append(entry)
        if not _touches_border(x, y, w, h, frame_w, frame_h):
            candidates.append(entry)

    pool = candidates if candidates else fallback
    if not pool:
        return None

    # 深度が最小（＝カメラに一番近い）ものを優先。同距離なら面積が大きい方を採用
    pool.sort(key=lambda item: (item[0], -item[1]))
    return pool[0][2]
 
 
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

    hands_detector = create_hand_landmarker()

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
    last_timestamp_ms = -1
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
            timestamp_ms = int(color_frame.get_timestamp())
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms
            hand_boxes = detect_hand_boxes(hands_detector, color_image, timestamp_ms)
            bbox = get_object_bbox(depth_image, depth_scale, exclude_rects=hand_boxes)
 
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

            # ---- 手動リトライ（AI判定を打ち切ってRETRYへ強制遷移） ----
            if key == ord("4") and state not in (State.OPEN, State.THANKS):
                state = State.RETRY
                state_entered_at = time.time()
                buffer.clear()
                last_center = None
                play_retry_voice()
                print("[手動] リトライを強制送信")
 
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
        if hands_detector is not None:
            hands_detector.close()
 
 
if __name__ == "__main__":
    main()