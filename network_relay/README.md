# Web画面のスマホ公開・保険プラン（network_relay/）

本番デモはノートPC1台にRealSense・Arduino2台・Flaskをすべて集約する構成（`../README.md`参照）。
スマホからWeb画面（満腹度・レベル画面）を見るには、通常はノートPCをモバイルホットスポット化して
`http://<PCのIP>:5000/` にアクセスしてもらう想定だった。

**ただし会場ではモバイルホットスポットの使用が禁止されている可能性がある**（電波混線対策）。
このフォルダは、ホットスポットが使えない場合の代替手段（Plan B・Plan C）をまとめたもの。

**【8/2追記】Plan A・Plan Bを現地で何度も試したが安定してつながらなかったため、
Plan C（Cloudflare Tunnel）を追加した。本番はPlan Cを主軸に、Plan A（同一WiFiで
繋がるなら一番シンプル）が使えるならそちらでもよい、という運用に変更する。**

| プラン | 方式 | 必要な通信の向き | 弱点 |
| --- | --- | --- | --- |
| A | 同一WiFiに直接アクセス | 端末間（PC⇔スマホ）の直接通信 | クライアント分離があると不可 |
| B | 配布VM経由のSSH中継 | PC→VM（送信）＋端末→VM（受信） | VM側ファイアウォール・sshd設定に依存、切り分けが難しい |
| C | Cloudflare Tunnel | PC→Cloudflare（送信のみ） | PCから外部インターネットに出られないと不可（8/2に会場から確認済みで問題なし） |

## Plan A（まずこれを試す）：会場WiFi（KIT-GUEST3）に両方接続

PCとスマホの両方を会場のゲストWiFi「KIT-GUEST3」に接続し、PCの実際のIPアドレス
（`ipconfig`で確認、KIT-GUEST3側のアダプター）に、スマホから直接
`http://<PCのIP>:5000/` でアクセスできるか試す。

**これがうまくいけば一番シンプルなので、本番前に必ず一度試すこと。**
うまくいかない場合（多くのゲストWiFiは「クライアント分離（AP isolation）」という
セキュリティ設定で、同じWiFiに繋いだ端末同士が直接通信できないようになっている）は
Plan Bへ。

## Plan B（保険）：仮想マシンをWeb画面の中継点として使う

ハッカソン運営から配布された仮想マシン（`team<番号>.hackit`、SSH接続）を、
**ハードウェア連携には使わず、Web画面をスマホから見えるようにするための中継専用**として使う。
PC側のFlask・シリアル通信・AI推論は今までどおりノートPC上で動かしたまま変更しない。

```
[スマホ]
   │ （会場WiFi/KIT-GUEST3経由でHTTPアクセス）
   ▼
[仮想マシン team<番号>.hackit]
   - tcp_relay.py が 0.0.0.0:5000 で待ち受け
   │ （127.0.0.1:5001へ中継）
   ▼
   - SSHの逆ポートフォワード（ssh -R）の出口が 127.0.0.1:5001
   │ （SSHトンネル経由）
   ▼
[ノートPC]
   - Flask（server/app.py）が localhost:5000 で稼働中
```

### 手順

**1. 仮想マシン側**（SSHでログインして）

```bash
ssh team<番号>@team<番号>.hackit
# パスワード：チームリーダーの学籍番号

# このリポジトリのnetwork_relayフォルダを仮想マシンにも置いておく（git cloneでもscpでもOK）
python3 tcp_relay.py --listen-port 5000 --forward-port 5001
```

このウィンドウは開いたままにしておく（Ctrl+Cで終了）。

**2. ノートPC側**（別のコマンドプロンプトで）

```bash
network_relay\start_ssh_relay.bat
```

または直接：

```bash
ssh -N -R 5001:localhost:5000 team<番号>@team<番号>.hackit
```

パスワード入力を求められたら、チームリーダーの学籍番号を入力。このウィンドウも
デモが終わるまで開いたままにする。

**3. スマホから確認**

`http://team<番号>.hackit:5000/` にアクセスする（QRコードもこのURLで作り直す）。

### うまくいかない場合

- 仮想マシンのファイアウォール（ufw等）で5000番ポートが塞がれている可能性がある
  → `sudo ufw allow 5000/tcp` が必要か、鈴木さん（ネットワークチーム）に確認
- `ssh`コマンドがWindowsで見つからない（`'ssh' は認識されません`等のエラー）
  → Windowsの「設定」→「アプリ」→「オプション機能」から「OpenSSH クライアント」を
    追加インストールする（Windows 10 1809以降は標準搭載のことが多い）
- `team<番号>.hackit`に繋がらない
  → お知らせのとおり、まずPC自体がKIT-GUEST3に接続できているか確認する

### 補足：なぜtcp_relay.pyが必要か

`ssh -R`だけで外部公開できるかどうかは、仮想マシンのsshd設定（`GatewayPorts`）次第。
既定では`GatewayPorts no`になっていることが多く、その場合SSHで転送したポートは
仮想マシンの`localhost`からしかアクセスできない（＝外部のスマホからは届かない）。
`tcp_relay.py`はPython標準ライブラリだけで動く簡易TCP中継で、`0.0.0.0`で待ち受けて
`localhost`の転送ポートへつなぎ直すことで、sshd設定を変更せずに外部公開できるようにする。

もし仮想マシンで最初から`GatewayPorts yes`（またはネットワークチームがそう設定済み）なら
`tcp_relay.py`は不要で、`ssh -N -R 5000:localhost:5000 team<番号>@team<番号>.hackit`
だけで直接`http://team<番号>.hackit:5000/`が外部公開される。まずはPlan Bを試すときに
`tcp_relay.py`無しの単純な方法から試し、ダメならこのリレーを使う、という順序でもよい。

## Plan C（8/2追加・現在の本命）：Cloudflare Tunnelで外部公開

Plan A・Plan Bはどちらも「外から中へ」（他端末→PC、PC→VM）という**受信(インバウンド)方向**の
通信が必要で、会場ネットワークやVM側のポリシーに阻まれやすい。現地で両方試して安定しなかった
ため、「PCからCloudflareへの発信(アウトバウンド)」だけで完結するこの方式に切り替えた。
一般的なブラウジングと同じ扱いになりやすく、通りやすい（8/2にリーダーのPCから会場経由で
一般のインターネットに問題なく繋がることは確認済み）。スマホ側も会場WiFiである必要はなく、
モバイル回線からでも公開URLでアクセスできる。

```
[スマホ]（会場WiFi でもモバイル回線でもOK）
   │ HTTPSアクセス
   ▼
[Cloudflareのエッジサーバー]
   │ トンネル（ノートPCが確立した発信のみの接続）
   ▼
[ノートPC] cloudflared → localhost:5000のFlask（server/app.py）
```

### 使い方

1. `server\app.py`（Flask）を起動しておく（`run_demo.bat`でOK）。
2. `network_relay\start_cloudflare_tunnel.bat` をダブルクリック。
   - 初回のみ`cloudflared.exe`（本フォルダ直下）を自動ダウンロードする。
   - `cloudflared tunnel --url http://localhost:5000` を起動し、出力から
     `https://xxxx.trycloudflare.com` の公開URLを検出して画面に大きく表示する。
   - `pip install qrcode` 済みなら、その場でターミナルにQRコードも表示する
     （未インストールでもURL表示だけで動作する）。
3. 表示されたQRコード、またはURLをスマホで開く。

### 注意点

- クイックトンネル（`--url`のみの起動）は**毎回URLが変わる**。デモ本番の直前に一度
  起動し直して、そのときのQRコードを使うこと（前回のURLは無効になっている）。
- このウィンドウを閉じる（または`cloudflared`プロセスを終了する）と公開が止まる。
  デモが終わるまで開いたままにする。
- もし会場が「発信」にもプロキシ経由を強制する場合（8/2時点では不要と確認済みだが、
  会場や当日の状況が変わった場合のため）は、`start_cloudflare_tunnel.bat`を実行する前に
  同じコマンドプロンプトで
  ```
  set HTTP_PROXY=http://プロキシアドレス:ポート
  set HTTPS_PROXY=http://プロキシアドレス:ポート
  ```
  を実行してからにする。Flask側やPlan A/Bには影響しない、`cloudflared`の通信だけの設定。
- `cloudflared.exe`の自動ダウンロードにも外部インターネットへの発信が必要。可能なら
  本番当日を待たず、事前に一度（別のネット環境でもよい）ダウンロードして
  `network_relay\cloudflared.exe`として置いておくと当日のリハーサルが早い。
