# 🐸 ケロッと！はらぺこエコガエル（分別強制ゴミ箱）

ハッカソンテーマ『突破』：ゴミをかざすと、RealSenseカメラと画像認識AIが種類を判別し、
正解のゴミ箱（カエルの口）だけが物理的にパカッと開いて可愛い声で喋る、分別強制ゴミ箱です。
人間のモラルに依存していた分別を「正解の口しか開かない」という物理的制限と
「エサやりゲーム」というエンタメ体験で突破します。

## 全体構成

本番デモは **リーダーのノートPC1台に集約** する構成です。RealSenseカメラ、
サーボ制御用Arduino、カウント用Arduinoの計3つのUSBデバイスをすべてこのPCに接続します。

```
[ノートPC（本番機）]
 - RealSenseカメラ（USB接続）
 - サーボ制御Arduino（USB接続、servo_3.ino）
 - カウント用Arduino（USB接続、GarbageCounter.ino）
 - VOICEVOXアプリ
 - server/app.py（Flask：API + Web画面配信）
 - server/sensor_bridge.py（カウント用Arduinoの橋渡し、任意）
 - ai_core/State machine.py（AI推論・頭脳）
     ├─ server/serial_control.py 経由でサーボ制御
     ├─ POST http://localhost:5000/api/feed でFlaskへ通知
     └─ voice/voice_control.py 経由でVOICEVOX
```

> ハッカソン運営から`team番号.hackit`宛にSSH接続できる仮想マシン（Ubuntu 24.04）が
> 配布されていますが、USB経由のシリアル通信を直接受けられないため、本番のハードウェア
> 連携（サーボ・センサー・カメラ）には使用しません。すべてノートPC上で完結させます。

### 「なぜlocalhostなのか」「なぜ仮想マシンなのか」の整理

このシステムには**性質の違う2つの通信経路**があり、混同しやすいので整理しておく。

**経路1：ノートPCの中だけで完結する通信**（AI推論⇄Flask、AI推論⇄Arduino）
`ai_core/State machine.py`・`server/app.py`・`server/serial_control.py`・
`server/sensor_bridge.py`は**すべて同じノートPC上で動く別プロセス**。プロセス間通信は
`http://localhost:5000`で固定でよく、会場WiFiの種類やPCのIPアドレスが変わっても
一切影響を受けない。ここに仮想マシンを挟む意味はない（USB機器を仮想マシンに
繋げられないのが理由）。今回はここ（`server/sensor_bridge.py`のFlask送信先）が
テスト時の仮想マシンIP直指定のまま本番設定に戻し忘れていたことが不具合の原因になった。
**この経路のURLは常に`localhost:5000`で固定、絶対に変更しないこと。**

**経路2：スマホがWeb画面を見に行く通信**（QRコード用）
ノートPCの実IP（`http://192.168.x.x:5000/`等）を直接QRコードにすると、
WiFiに繋ぎ直すたびにIPが変わりQRの作り直しが必要になる。これを避けたい場合に
仮想マシンの**固定ホスト名**（`team<番号>.hackit`）を中継点として使うのが下記Plan B。
Plan Bを使ってもRealSense・Arduino・Flask本体は引き続きノートPC上で動く。
仮想マシンは中継（`tcp_relay.py`）を1つ動かすだけで、ハードウェアとは一切関係ない。

### スマホからWeb画面を見る方法

⚠️ **会場ではモバイルホットスポットの使用が禁止されている可能性がある**（電波混線対策）。
以下の順で試すこと（詳細・トラブルシュートは[`network_relay/README.md`](network_relay/README.md)）：

**Plan A（まずこれ）**：PCとスマホを両方とも会場WiFi「KIT-GUEST3」に接続し、
`ipconfig`で確認したPCのIPアドレスに`http://<PCのIP>:5000/`でスマホから直接
アクセスできるか試す。うまくいけば一番シンプル。クライアント分離（AP isolation）で
繋がらない場合はPlan Bへ。

**Plan B（保険・QRコードを毎回変えたくない場合はこちらが本命）**：

```
[スマホ] → http://team<番号>.hackit:5000/ （固定URL・QRも一度作れば使い回せる）
   ↓（会場WiFi経由）
[仮想マシン team<番号>.hackit] tcp_relay.py が 0.0.0.0:5000 で待受 → 127.0.0.1:5001へ中継
   ↓（SSHの逆ポートフォワードのトンネル）
[ノートPC] Flask（server/app.py）が localhost:5000 で稼働中（推論・サーボもここで動作）
```

手順（本番前に必ず一度リハーサルすること）：

1. 仮想マシンにSSHログインし、以下を実行したままにする（閉じない）
   ```bash
   ssh team<番号>@team<番号>.hackit   # パスワード：（別途共有された合言葉、学籍番号などの個人情報はここに書かない）
   python3 tcp_relay.py --listen-port 5000 --forward-port 5001
   ```
2. ノートPC側で（別ウィンドウで）以下を実行したままにする（閉じない）
   ```bash
   network_relay\start_ssh_relay.bat
   ```
   （チーム番号の入力を求められる。中身は`ssh -N -R 5001:localhost:5000 team<番号>@team<番号>.hackit`）
3. QRコードは`http://team<番号>.hackit:5000/`で作成する（`site_flog/index.html`のAPI呼び出しは
   相対パス`/api/status`なので、PC直IPでもこの固定URLでもコード変更は不要）

うまくいかない場合は仮想マシンのufwで5000番ポートが塞がれていないか確認（要:鈴木さん）。
詳細は[`network_relay/README.md`](network_relay/README.md)。

詳しい構成・起動手順は各フォルダのREADMEを参照してください：

| フォルダ | 内容 | README |
|---|---|---|
| `ai_core/` | RealSense + AI推論 + ステートマシン（2年生A担当） | [`ai_core/README.md`](ai_core/README.md) |
| `server/` | シリアル通信 + Flask APIサーバー（2年生B担当） | [`server/README.md`](server/README.md) |
| `voice/` | VOICEVOXによる音声合成（1年生A担当） | [`voice/README.md`](voice/README.md) |
| `arduino/` | サーボ制御Arduinoスケッチ（1年生A担当） | [`arduino/README.md`](arduino/README.md) |
| `web/` | カウント用Arduinoスケッチ（1年生B担当） | [`web/README.md`](web/README.md) |
| `site_flog/` | スマホ向けステータス画面（1年生C担当、`server/app.py`から配信） | - |
| `network_relay/` | ホットスポット禁止時の保険（仮想マシン経由でWeb画面を公開） | [`network_relay/README.md`](network_relay/README.md) |

## クイックスタート

0. **事前確認（サーボが動かないトラブルの9割はここ）**
   - デバイスマネージャーで、サーボ制御Arduino（`servo_3.ino`書き込み済み）と
     カウント用Arduino（`GarbageCounter.ino`書き込み済み）が実際に何番のCOMポートに
     割り当てられているか確認する（USB抜き差しで番号がずれることがよくある）。
   - `server/serial_control.py`の`PORT`・`server/sensor_bridge.py`の`PORT`が
     実機のCOM番号と一致しているか確認し、違っていれば書き換える。
   - Arduino IDEのシリアルモニタは**必ず閉じておく**（開いたままだとポートが
     占有されPythonから接続できない）。閉じた後は、既に起動済みのPythonプロセスが
     あれば一度再起動すること（開いたまま接続に失敗した状態は、モニタを閉じるだけ
     では直らず再起動が必要な場合がある）。
1. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
2. VOICEVOXアプリを起動
3. `run_demo.bat` を実行（Flask・センサーブリッジ・AI推論を順番に別ウィンドウで起動）
   - 各ウィンドウとも`chcp 65001`＋`PYTHONIOENCODING=utf-8`を設定してから起動するので
     日本語ログは基本的に文字化けしないはず。それでも読めない場合は、コンソールの
     フォントをTrueTypeフォント（Consolas等）に変更するか、下記の手動起動で
     個別のターミナルから実行して直接ログを確認する。
   - 手動で個別に起動する場合：
     ```bash
     cd server && python app.py            # ターミナル1
     cd server && python sensor_bridge.py  # ターミナル2（任意）
     cd ai_core && python "State machine.py" # ターミナル3
     ```
4. （本番当日・QRコードを固定にしたい場合のみ）スマホ公開の設定は
   上の「スマホからWeb画面を見る方法」を参照。ここまでの1〜3はPlan A・Plan Bどちらでも
   共通で、変更不要。

**動作確認のおすすめ順序**（いきなり全部繋げず、下から積み上げる）：

1. `python server/serial_control.py`を単体実行し、カメラ・AIを介さずに
   サーボが`open_lid(1)`→`open_lid("2")`→`open_lid(0)`で動くか確認
2. `python server/app.py`を起動し、ブラウザで`http://localhost:5000/api/status`が
   JSONを返すか確認
3. 上記2つが単体で動くことを確認してから`run_demo.bat`（またはターミナル3つ手動起動）で
   全体を繋げる

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

- 【解消済み・8/2】`server/sensor_bridge.py`のFlask送信先が、以前team9.hackitで
  テストしていた頃のIP:ポート直指定のまま本番用の`localhost:5000`に戻し忘れていたバグを修正。
  併せて`ai_core/State machine.py`側で`post_feed(...)`呼び出しが3箇所ともコメントアウトされ
  Web画面のカウントが一切更新されない状態だったのも修正（詳細は`claude/統合作業ログ`参照）。
- 未解決：2台のArduino（サーボ用・カウント用）のCOMポートが実機と一致しているか要確認
  （`server/serial_control.py`のPORT・`server/sensor_bridge.py`のPORT）。シリアルモニタ手動
  テストでは動くのに自動パイプラインから動かない場合、まずここを疑うこと。
- `site_flog/images/`のキャラクター画像は仮のプレースホルダー。本番イラストに差し替え
- 【方針確定・8/2】ゴミのカウント確定は「物理センサー通過」（`server/sensor_bridge.py`＋
  カウント用Arduino）が正規ルートに決定。`ENABLE_DIRECT_FEED_POST = True`にし、
  `ai_core/State machine.py`側の`post_feed(...)`は二重カウント防止のためコメントアウト済み。
  （以前の仕様書では「AI判定確定時」が正規ルートだったが、リーダー判断でこちらに変更）
- モバイルホットスポットが会場で本当に禁止かどうか、運営に確認する。禁止の場合に備えて
  Plan B（仮想マシン経由の公開）を本番前に一度リハーサルしておくこと
- 仮想マシンのIPアドレスやポート番号を各スクリプトに直接ハードコードしない。
  スマホ公開用の経路は必ず`team<番号>.hackit`＋`network_relay/`のリレー経由にする
  （直IP指定は今回のバグのように環境が変わると即座に壊れるため）
