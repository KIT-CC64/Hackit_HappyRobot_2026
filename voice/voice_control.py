"""
voice/voice_control.py
ケロッと！はらぺこエコガエル - VOICEVOXによる動的セリフ生成モジュール（タスク1-2）

ai_core/State machine.py の play_voice() / play_retry_voice() スタブから
呼び出される想定のモジュール。VOICEVOX ENGINE (http://127.0.0.1:50021) に
テキストを投げて音声合成→再生する。

設計方針（他パートのスタブと同じ考え方）：
- VOICEVOX ENGINEが未起動／通信エラーでも例外を握りつぶし、ログだけ出して
  ステートマシンの処理は絶対に止めない（本番デモで音声だけ落ちても続行できる）
- 音声合成・再生はステートマシンのメインループをブロックしないよう、
  専用ワーカースレッドで直列に処理する（同時に喋って音が重ならないようにするため）

使い方（ai_core/State machine.py 側）：
    from voice_control import play_voice, play_retry_voice
    play_voice("petbottle", streak_count)   # 種類名 + 連続正解数
    play_retry_voice()                      # 「もう一回近づけてケロ」

単体テスト：
    python voice_control.py
    （事前にVOICEVOXアプリを起動しておくこと。詳細はvoice/README.md参照）
"""

import platform
import queue
import random
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import requests

# ============================================================
# 設定
# ============================================================
VOICEVOX_URL = "http://127.0.0.1:50021"
SPEAKER_NAME = "ずんだもん"
SPEAKER_STYLE = "ノーマル"
FALLBACK_SPEAKER_ID = 3  # /speakers取得に失敗した場合のフォールバック
                          # （多くのVOICEVOXバージョンで「ずんだもん(ノーマル)」= 3。
                          #   ずれていた場合は list_speakers.py で確認して書き換える）
REQUEST_TIMEOUT = 6.0
ENGINE_START_WAIT_SEC = 15  # VOICEVOX起動直後で/speakersがまだ応答しない場合の最大待ち時間

# ============================================================
# セリフテンプレート（タスク1-2仕様：3種類＋確信度低の計4パターン以上）
# 複数バリエーションを持たせてランダム再生 → 同じセリフの繰り返しで飽きさせない（UX/エンタメ重視）
# ============================================================
LINE_TEMPLATES = {
    "petbottle": [
        "ペットボトルいただきますケロ！{n}個目だよ！",
        "ペットボトル、ナイス分別ケロ！これで{n}個目ケロ〜",
        "キラキラのペットボトル、ごちそうさまケロ！",
    ],
    "can": [
        "缶いただきますケロ！{n}個目だよ！",
        "缶、ぺろっと食べちゃうケロ！{n}個目ケロ〜",
        "カンカン、いい音するケロ！ごちそうさまケロ！",
    ],
    "burnable": [
        "燃えるゴミいただきますケロ！{n}個目だよ！",
        "燃えるゴミもおいしくいただくケロ！{n}個目ケロ〜",
        "もぐもぐ、燃えるゴミもぺろりんケロ！",
    ],
}

RETRY_LINES = [
    "うーん、よくわからないケロ…もう一回近づけてケロ！",
    "もう一回近づけてケロ〜！",
    "ケロ？もうちょっとカメラに近づけてほしいケロ！",
]

GOMI_TYPE_JA = {"petbottle": "ペットボトル", "can": "缶", "burnable": "燃えるゴミ"}

# ============================================================
# 話者ID解決（起動時に一度だけ /speakers を叩いてキャッシュする）
# ============================================================
_speaker_id_cache = None
_speaker_lock = threading.Lock()


def _resolve_speaker_id():
    global _speaker_id_cache
    if _speaker_id_cache is not None:
        return _speaker_id_cache
    with _speaker_lock:
        if _speaker_id_cache is not None:
            return _speaker_id_cache
        try:
            resp = requests.get(f"{VOICEVOX_URL}/speakers", timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            for speaker in resp.json():
                if speaker.get("name") == SPEAKER_NAME:
                    for style in speaker.get("styles", []):
                        if style.get("name") == SPEAKER_STYLE:
                            _speaker_id_cache = style["id"]
                            print(f"[voice] 話者解決: {SPEAKER_NAME}/{SPEAKER_STYLE} -> id={_speaker_id_cache}")
                            return _speaker_id_cache
            print(f"[voice][WARN] {SPEAKER_NAME}/{SPEAKER_STYLE} が/speakers内に見つからず。"
                  f"フォールバックID={FALLBACK_SPEAKER_ID}を使用")
        except Exception as e:
            print(f"[voice][WARN] /speakers取得失敗、フォールバックID={FALLBACK_SPEAKER_ID}を使用: {e}")
        _speaker_id_cache = FALLBACK_SPEAKER_ID
        return _speaker_id_cache


def wait_for_engine(timeout_sec=ENGINE_START_WAIT_SEC):
    """VOICEVOX ENGINEが応答するまで待つ（起動直後の疎通確認・デモ前チェック用）。"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            resp = requests.get(f"{VOICEVOX_URL}/version", timeout=1.0)
            if resp.ok:
                print(f"[voice] VOICEVOX ENGINE 応答確認OK（version={resp.text}）")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    print("[voice][WARN] VOICEVOX ENGINEへの疎通確認がタイムアウトしました。"
          "VOICEVOXアプリが起動しているか確認してください。")
    return False


# ============================================================
# 音声合成・再生
# ============================================================
def _synthesize(text: str) -> bytes:
    """VOICEVOX ENGINEにテキストを渡し、WAVバイト列を返す。"""
    speaker_id = _resolve_speaker_id()
    query_resp = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": speaker_id},
        timeout=REQUEST_TIMEOUT,
    )
    query_resp.raise_for_status()
    synth_resp = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker_id},
        json=query_resp.json(),
        timeout=REQUEST_TIMEOUT,
    )
    synth_resp.raise_for_status()
    return synth_resp.content


def _play_wav_bytes(wav_bytes: bytes):
    system = platform.system()
    if system == "Windows":
        import winsound  # Windows標準ライブラリ、追加インストール不要
        winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
    elif system == "Darwin":
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                tmp_path = f.name
            subprocess.run(["afplay", tmp_path], check=False)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
    else:
        # Linux等：simpleaudioが使えればそれを使い、無ければaplayにフォールバック
        try:
            import io
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(io.BytesIO(wav_bytes))
            wave_obj.play().wait_done()
        except ImportError:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(wav_bytes)
                    tmp_path = f.name
                subprocess.run(["aplay", tmp_path], check=False)
            finally:
                if tmp_path:
                    Path(tmp_path).unlink(missing_ok=True)


# ---- 再生キュー（同時に複数のセリフが重ならないよう直列で再生する）----
_speech_queue = queue.Queue(maxsize=4)


def _worker():
    while True:
        text = _speech_queue.get()
        try:
            wav_bytes = _synthesize(text)
            _play_wav_bytes(wav_bytes)
        except Exception as e:
            print(f"[voice][STUB] VOICEVOX再生失敗、ログのみ: '{text}' ({e})")
        finally:
            _speech_queue.task_done()


_worker_thread = threading.Thread(target=_worker, daemon=True)
_worker_thread.start()


def _enqueue_speech(text: str):
    print(f"[voice] 再生キュー投入: {text}")
    try:
        _speech_queue.put_nowait(text)
    except queue.Full:
        # キューが詰まっている（連投され過ぎ）場合は諦めて処理を止めない
        print(f"[voice][WARN] 再生キューが満杯のためスキップ: {text}")


# ============================================================
# ai_core/State machine.py から呼ばれる公開関数
#   ※引数の型・意味は仕様書0章・4章の合意通り
#     gomi_type: "petbottle" | "can" | "burnable"
#     streak_count: 連続正解数（int）
# ============================================================
def play_voice(gomi_type: str, streak_count: int):
    templates = LINE_TEMPLATES.get(gomi_type)
    if not templates:
        print(f"[voice][WARN] 未知のgomi_type: {gomi_type}")
        return
    text = random.choice(templates).format(n=streak_count)
    _enqueue_speech(text)


def play_retry_voice():
    text = random.choice(RETRY_LINES)
    _enqueue_speech(text)


# ============================================================
# 単体テスト（VOICEVOXアプリを起動した状態で実行すること）
# ============================================================
if __name__ == "__main__":
    print("=== VOICEVOX疎通テスト ===")
    if not wait_for_engine(timeout_sec=5):
        print("ENGINEに接続できていませんが、スタブ動作の確認としてそのまま続行します。")

    play_voice("petbottle", 1)
    time.sleep(3.5)
    play_voice("can", 2)
    time.sleep(3.5)
    play_voice("burnable", 3)
    time.sleep(3.5)
    play_retry_voice()
    time.sleep(3.5)

    _speech_queue.join()
    print("=== テスト完了 ===")
