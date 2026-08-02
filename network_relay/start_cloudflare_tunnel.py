#!/usr/bin/env python3
"""
network_relay/start_cloudflare_tunnel.py
【Plan C】Cloudflareのクイックトンネルを使って、ノートPC上のFlask（localhost:5000）を
外部公開する。Plan A（同一WiFi直接アクセス）・Plan B（配布VM経由のSSH中継）が
会場WiFiのクライアント分離やVM側のファイアウォール設定でうまくいかなかった場合の
最終手段として8/2に追加。

【なぜこれなら通る可能性が高いか】
Plan A・Plan Bはどちらも「外から中へ」（他端末→PC、PC→VM）という受信(インバウンド)方向の
通信が必要で、会場ネットワークやVMのポリシーに阻まれやすい。
このPlan Cは「ノートPCからCloudflareへの発信(アウトバウンド)」だけで成立するため、
一般的なブラウジングと同じ扱いになりやすく、通りやすい
（8/2にリーダーのPCから会場経由で一般のインターネットに問題なく繋がることは確認済み）。
スマホ側も会場WiFiである必要はなく、モバイル回線からでも公開URLでアクセスできる。

【使い方】
    network_relay\\start_cloudflare_tunnel.bat をダブルクリック
    （cloudflared.exe が無ければ自動ダウンロードしてからこのスクリプトを呼ぶ）

または直接:
    python network_relay/start_cloudflare_tunnel.py

【前提】
- server/app.py（Flask）が localhost:5000 で起動済みであること（run_demo.batでOK）
- cloudflared 実行ファイルが network_relay/ にある、またはPATHが通っていること
- 会場から一般のインターネットへ発信できること（8/2確認済み・プロキシ設定は不要だった）

【もし会場が発信にもプロキシ経由を強制する場合】
このスクリプトを実行する前に、コマンドプロンプトで
    set HTTP_PROXY=http://プロキシアドレス:ポート
    set HTTPS_PROXY=http://プロキシアドレス:ポート
を実行してから同じウィンドウでこのスクリプトを起動すれば、cloudflaredの通信だけ
プロキシ経由になる（Flask側の設定は一切不要）。8/2時点では不要と確認済みなので、
通常は気にしなくてよい。
"""
import os
import re
import shutil
import subprocess
import sys

URL_PATTERN = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED = os.path.join(BASE_DIR, "cloudflared.exe" if os.name == "nt" else "cloudflared")
LOCAL_URL = "http://localhost:5000"


def find_cloudflared():
    """network_relay/直下のcloudflared実行ファイル、無ければPATH上のものを探す。"""
    if os.path.exists(CLOUDFLARED):
        return CLOUDFLARED
    which = shutil.which("cloudflared")
    if which:
        return which
    return None


def print_qr(url):
    """qrcodeライブラリがあればターミナルにQRコードを表示する（無ければURLのみ）。"""
    try:
        import qrcode
    except ImportError:
        print("[情報] qrcodeライブラリが無いのでQR表示は省略します。")
        print("       pip install qrcode  を実行しておくと次回からQR表示できます。")
        print("       今回は上のURLをスマホに直接入力してください。")
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    qr.print_ascii(invert=True)


def main():
    exe = find_cloudflared()
    if not exe:
        print("[エラー] cloudflared が見つかりません。")
        print(r"network_relay\start_cloudflare_tunnel.bat から起動してください")
        print("（cloudflared.exe を自動ダウンロードします）。")
        print("手動で用意する場合は https://github.com/cloudflare/cloudflared/releases から")
        print(f"cloudflared-windows-amd64.exe を取得し、{BASE_DIR} に")
        print("cloudflared.exe という名前で置いてください。")
        sys.exit(1)

    print(f"[起動] {exe} tunnel --url {LOCAL_URL}")
    print("（公開URLが出るまで数秒〜十数秒かかります。気長にお待ちください）")
    print()

    proc = subprocess.Popen(
        [exe, "tunnel", "--url", LOCAL_URL, "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    found_url = None
    try:
        for line in proc.stdout:
            print(line, end="")
            if not found_url:
                m = URL_PATTERN.search(line)
                if m:
                    found_url = m.group(0)
                    print()
                    print("=" * 60)
                    print(f"  公開URL: {found_url}")
                    print("=" * 60)
                    print_qr(found_url)
                    print()
                    print("上のQRコード、またはURLをスマホのブラウザで開いてください。")
                    print("（会場WiFiでもモバイル回線でもアクセス可能）")
                    print("（このウィンドウを閉じると公開が止まります。デモ中は開いたままに）")
                    print()
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
