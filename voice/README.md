# 音声（VOICEVOX連携） - ケロッと！はらぺこエコガエル

タスク1-2（1年生A担当）：ゴミの種類・状況に応じてカエルが違うセリフをVOICEVOXで
その場生成・再生するモジュールです。`ai_core/State machine.py` の `play_voice()` /
`play_retry_voice()` スタブから呼び出される想定で作ってあります。

## できること

- `play_voice(gomi_type, streak_count)`：`"petbottle" / "can" / "burnable"` それぞれに
  複数パターンのセリフを用意し、ランダムに選んで喋る（`{n}個目だよ！` に連続正解数を埋め込む）
- `play_retry_voice()`：判定不能（確信度が低い）ときの「もう一回近づけてケロ」
- VOICEVOX ENGINEが未起動／通信エラーの場合は例外を握りつぶし、ログだけ出して
  処理を止めない（他パートのスタブと同じフェイルセーフ方針）
- 音声合成・再生は専用スレッドで直列処理するので、ステートマシンのメインループ
  （カメラ映像の描画など）をブロックしない

## 事前準備：VOICEVOX ENGINEのセットアップ（Windows）

1. https://voicevox.hiroshiba.jp/ からVOICEVOXをダウンロード（Windows版インストーラ）
2. インストールして起動する。起動すると自動的に音声合成エンジンが
   `http://127.0.0.1:50021` で待ち受け状態になる（アプリのウィンドウは
   最小化・タスクトレイに置いたままでOK、閉じるとエンジンも止まるので注意）
3. 動作確認：ブラウザで http://127.0.0.1:50021/docs を開き、Swagger UIの画面が
   表示されればOK。または以下でも確認できる：
   ```
   curl http://127.0.0.1:50021/version
   ```
4. 話者一覧の確認（「ずんだもん」のID・スタイル名を確認したい場合）：
   ```
   python list_speakers.py
   ```

**本番当日の注意**：VOICEVOXアプリは推論スクリプト（`State machine.py`）を動かす
**前に**起動しておくこと。エンジン起動には数秒〜十数秒かかるため、リハーサル時は
`voice_control.py` 内の `wait_for_engine()` で疎通確認してから本番に臨むと安心。

## Pythonの依存パッケージ

`ai_core/README.md` の手順で `requests` は入っている想定ですが、voiceフォルダ単体で
動かす場合は以下だけでOK（Windowsなら`winsound`は標準ライブラリなので追加インストール不要）：

```bash
pip install requests
```

## 単体テスト

VOICEVOXアプリを起動した状態で：

```bash
python voice_control.py
```

petbottle → can → burnable → retry の順に4パターン喋れば疎通OK。

## ai_core/State machine.py との連携

`State machine.py` 側は `play_voice()` / `play_retry_voice()` の中で、同階層から見て
一つ上の `voice/` フォルダにある本モジュールを import するようにしてあります
（`voice_control.py` が無い/importできない環境でも自動でログのみのスタブ動作に
フォールバックするので、統合前でも各自の単体テストが止まりません）。

```python
from voice_control import play_voice, play_retry_voice

play_voice("petbottle", streak_count)  # 種類名 + 連続正解数
play_retry_voice()
```

## セリフのカスタマイズ

`voice_control.py` 冒頭の `LINE_TEMPLATES` / `RETRY_LINES` にテキストを追加するだけで
バリエーションが増やせます（毎回ランダムに1つ選んで再生）。エンタメ性を上げたい場合は
ここにレベルアップ演出用のセリフなどを足していくと良さそうです（時間があれば）。

## 話者を変えたい場合

`voice_control.py` の `SPEAKER_NAME` / `SPEAKER_STYLE` を書き換えるだけで、
`/speakers` から自動的に該当IDを解決します（`python list_speakers.py` で
利用可能な名前一覧を確認できます）。

## 既知の制限・今後の改善候補

- 現状は音声を毎回VOICEVOX ENGINEにリクエストして合成している（キャッシュ無し）。
  同じセリフの合成に時間がかかる／会場のネットワークが不安定などの問題が出た場合は、
  よく使うセリフだけ事前に`.wav`として保存しておき、再生だけ行う方式に切り替えるのも
  フェイルセーフとして検討の余地あり
- 複数セリフが同時に来た場合は再生キューで直列化しているが、キューが詰まると
  古いセリフから捨てられる（`queue.Queue(maxsize=4)`）。連続投入が多い場合は
  上限値を調整すること
