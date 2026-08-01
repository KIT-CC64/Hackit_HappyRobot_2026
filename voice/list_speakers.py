"""
voice/list_speakers.py
VOICEVOX ENGINEに登録されている話者・スタイル名とIDの一覧を表示するユーティリティ。

ずんだもん以外のキャラクター／スタイル（あまあま・ツンツン等）を使いたくなった場合や、
voice_control.py の FALLBACK_SPEAKER_ID がずれていないか確認したいときに使う。

使い方：
    python list_speakers.py
    （事前にVOICEVOXアプリを起動しておくこと）
"""

import requests

VOICEVOX_URL = "http://127.0.0.1:50021"


def main():
    try:
        resp = requests.get(f"{VOICEVOX_URL}/speakers", timeout=5.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"VOICEVOX ENGINEに接続できませんでした: {e}")
        print("VOICEVOXアプリを起動してから再実行してください。")
        return

    speakers = resp.json()
    print(f"{len(speakers)}件のキャラクターが見つかりました。\n")
    for speaker in speakers:
        print(f"■ {speaker['name']}")
        for style in speaker.get("styles", []):
            print(f"    - {style['name']:10s}  id={style['id']}")
    print("\n※ voice_control.py の SPEAKER_NAME / SPEAKER_STYLE / FALLBACK_SPEAKER_ID を")
    print("  ここに出てきた名前・IDに合わせて設定してください。")


if __name__ == "__main__":
    main()
