# 音声（VOICEVOX連携） - voice/

ゴミの種類・状況に応じてカエルのセリフをVOICEVOXで生成・再生するモジュールです。`ai_core/State machine.py`の`play_voice()` / `play_retry_voice()`から呼び出されます。

## できること

- `play_voice(gomi_type, streak_count)`：`petbottle` / `can` / `burnable`それぞれに複数パターンのセリフを用意し、ランダムに選んで再生（`{n}個目だよ！`に連続正解数を埋め込む）
- `play_retry_voice()`：判定不能時の「もう一回近づけてケロ」
- VOICEVOX ENGINEが未起動／通信エラーの場合はログのみを出して処理を止めない
- 音声合成・再生は専用スレッドで直列処理し、ステートマシンのメインループをブロックしない

## 事前キャッシュ方式

本番機はRealSense・AI推論・Flask・シリアル通信・VOICEVOX ENGINEを1台のノートPCに集約するため、ゴミ検知直後（CPU負荷が高い瞬間）にその場で音声合成すると、HTTPリクエストがタイムアウトしやすくなります。そのため、セリフのテンプレート（`LINE_TEMPLATES` / `RETRY_LINES`）を本番前に一度すべて合成して`voice/cache/*.wav`に保存しておき、本番中はキャッシュ済みWAVを再生するだけにしています。

**本番当日・セリフを変更した日は、必ず事前にキャッシュを生成してください**（VOICEVOXアプリを起動した状態で）：

```bash
python voice_control.py --warmup
```

またはダブルクリックで`voice/warmup_voice_cache.bat`を実行。

- 初回は数分かかることがあります。カメラやAI推論を起動する前、CPUが空いているタイミングで実行してください
- 2回目以降、既にキャッシュ済みのファイルはスキップされるためほぼ一瞬で終わります
- `LINE_TEMPLATES` / `RETRY_LINES`を追加・変更した場合は必ずwarmupを再実行してください
- `{n}個目だよ！`のような連続正解数入りのセリフは`MAX_CACHED_STREAK`（既定20）まで事前キャッシュします。それを超える回数投入しても、セリフ上の数字は20で頭打ちになりますが、Web画面側の実際のカウント・レベルには影響しません
- キャッシュに無いテキストが本番中に来た場合は、保険として15秒タイムアウトでその場合成にフォールバックします

## 事前準備：VOICEVOX ENGINEのセットアップ（Windows）

1. https://voicevox.hiroshiba.jp/ からVOICEVOXをダウンロード
2. インストールして起動する（起動すると`http://127.0.0.1:50021`で待ち受け状態になる。ウィンドウは最小化・タスクトレイに置いたままでOK、閉じるとエンジンも止まる）
3. 動作確認：ブラウザで http://127.0.0.1:50021/docs を開き、Swagger UIが表示されればOK
   ```bash
   curl http://127.0.0.1:50021/version
   ```
4. 話者一覧の確認：
   ```bash
   python list_speakers.py
   ```

VOICEVOXアプリは`State machine.py`を動かす前に起動しておいてください（エンジン起動には数秒〜十数秒かかります）。カメラ・AI推論を起動する前に`--warmup`を一度実行しておくことも忘れずに。

## 依存パッケージ

```bash
pip install requests
```

（Windowsの`winsound`は標準ライブラリのため追加インストール不要）

## 単体テスト

VOICEVOXアプリを起動した状態で：

```bash
python voice_control.py
```

petbottle → can → burnable → retry の順に4パターン再生されれば疎通OKです。

## ai_core/State machine.py との連携

```python
from voice_control import play_voice, play_retry_voice

play_voice("petbottle", streak_count)
play_retry_voice()
```

`voice_control.py`が無い／importできない環境では自動でスタブ動作にフォールバックします。

## セリフのカスタマイズ

`voice_control.py`冒頭の`LINE_TEMPLATES` / `RETRY_LINES`にテキストを追加するとバリエーションが増やせます。追加・変更したら`python voice_control.py --warmup`を再実行してキャッシュを更新してください。

## 話者を変更する場合

`voice_control.py`の`SPEAKER_NAME` / `SPEAKER_STYLE`を書き換えると、`/speakers`から自動的に該当IDを解決します。話者変更後は`voice/cache/`を削除してから`--warmup`を再実行してください。

## 既知の制限

- `{n}個目`の`n`は`MAX_CACHED_STREAK`（既定20）までしか事前キャッシュしない
- 再生キューは`queue.Queue(maxsize=4)`で直列化しており、詰まると古いセリフから捨てられる
- `voice/cache/`は自動生成されるバイナリ(.wav)フォルダのため`.gitignore`で除外済み
