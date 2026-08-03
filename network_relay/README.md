# Web画面のスマホ公開（network_relay/）

本番デモはノートPC1台にRealSense・Arduino2台・Flaskをすべて集約する構成です（`../README.md`参照）。スマホからWeb画面（満腹度・レベル画面）を見るために、Cloudflare Tunnelでノートpc上のFlaskを外部公開します。

同一WiFi直接アクセスやVM経由の中継といった他の方式は、会場ネットワークのクライアント分離やVM側のファイアウォール設定に依存し不安定だったため、PCから外部への発信のみで完結するこの方式を採用しています。

## 構成

```
[スマホ]（会場WiFi でもモバイル回線でもOK）
   │ HTTPSアクセス
   ▼
[Cloudflareのエッジサーバー]
   │ トンネル（ノートPCが確立した発信のみの接続）
   ▼
[ノートPC] cloudflared → localhost:5000のFlask（server/app.py）
```

## 使い方

1. `server\app.py`（Flask）を起動しておく（`run_demo.bat`でOK）
2. `network_relay\start_cloudflare_tunnel.bat`をダブルクリック
   - 初回のみ`cloudflared.exe`（本フォルダ直下）を自動ダウンロードする
   - `cloudflared tunnel --url http://localhost:5000`を起動し、公開URL（`https://xxxx.trycloudflare.com`）を検出して表示する
   - `pip install qrcode`済みなら、その場でターミナルにQRコードも表示する
3. 表示されたQRコード、またはURLをスマホで開く

## 注意点

- クイックトンネルは**起動のたびにURLが変わる**。本番直前に一度起動し直して、そのときのQRコードを使うこと
- このウィンドウを閉じる（または`cloudflared`プロセスを終了する）と公開が止まる。デモが終わるまで開いたままにする
- 公開URLには認証がかからない。SNS等で不特定多数に共有せず、会場でのQRコード掲示にとどめること
- 会場が「発信」にもプロキシ経由を強制する場合は、`start_cloudflare_tunnel.bat`を実行する前に同じコマンドプロンプトで
  ```
  set HTTP_PROXY=http://プロキシアドレス:ポート
  set HTTPS_PROXY=http://プロキシアドレス:ポート
  ```
  を実行してからにする（Flask側には影響しない、`cloudflared`の通信だけの設定）
- `cloudflared.exe`の自動ダウンロードにも外部インターネットへの発信が必要。事前に一度ダウンロードして`network_relay\cloudflared.exe`として置いておくと当日のリハーサルが早い

同フォルダには予備の中継スクリプト（`tcp_relay.py`・`start_ssh_relay.bat`）も残していますが、本番運用ではCloudflare Tunnelのみを使用します。
