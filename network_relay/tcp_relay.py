#!/usr/bin/env python3
"""
network_relay/tcp_relay.py
仮想マシン（team番号.hackit）上で実行する、Web画面を外部公開するための中継リレー。

【背景】本番デモではノートPC(RealSense・Arduino2台・Flask全部)1台に集約する構成だが、
会場でモバイルホットスポットが使用禁止の場合、スマホからノートPCへ直接アクセスする手段が
無くなる可能性がある。その保険（Plan B）として、ハッカソン運営配布の仮想マシンを
「ノートPC上のFlaskへの中継点」として使う。

【なぜこのスクリプトが必要か】
単純に `ssh -R 5000:localhost:5000 team<番号>@team<番号>.hackit` を実行するだけだと、
sshdの`GatewayPorts`設定が既定（no）のままの場合、転送されたポートは仮想マシンの
localhost（127.0.0.1）からしかアクセスできず、外部（スマホ等）からは届かない。
このスクリプトは仮想マシン上で 0.0.0.0:<EXTERNAL_PORT> で待ち受けて、
127.0.0.1:<INTERNAL_PORT>（SSHトンネルの出口）へそのまま中継することで、
sshd設定を変更せずに外部公開できるようにする（Python標準ライブラリのみ・追加インストール不要）。

【使い方】
1. 仮想マシン上でこのスクリプトを起動：
       python3 tcp_relay.py --listen-port 5000 --forward-port 5001

2. ノートPC側でSSH逆ポートフォワードを開始（別ターミナルで、接続を維持する）：
       ssh -N -R 5001:localhost:5000 team<番号>@team<番号>.hackit
   （`network_relay/start_ssh_relay.bat` でも起動可能）

3. スマホ・ブラウザから `http://team<番号>.hackit:5000/` にアクセス
   （経路：スマホ → 仮想マシン:5000（本スクリプト）→ 仮想マシン:5001（SSHトンネル出口）
     → ノートPCのlocalhost:5000（Flask本体））

【うまくいかない場合】
- 仮想マシンのファイアウォール（ufw等）で5000番ポートが塞がれている可能性がある。
  `sudo ufw allow 5000/tcp` 等が必要な場合は、鈴木さん（ネットワークチーム）に確認すること。
- そもそも`ssh -R`だけでGatewayPortsが有効になっている環境であれば、このリレーは不要
  （その場合は `ssh -N -R 5000:localhost:5000 team<番号>@team<番号>.hackit` だけで動く）。
"""
import argparse
import socket
import threading


def relay(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            src.shutdown(socket.SHUT_RD)
        except OSError:
            pass
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle_client(client_sock, forward_host, forward_port):
    try:
        upstream = socket.create_connection((forward_host, forward_port), timeout=5)
    except OSError as e:
        print(f"[WARN] 転送先 {forward_host}:{forward_port} に接続できません "
              f"（SSHトンネルが繋がっていない可能性）: {e}")
        client_sock.close()
        return

    t1 = threading.Thread(target=relay, args=(client_sock, upstream), daemon=True)
    t2 = threading.Thread(target=relay, args=(upstream, client_sock), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    client_sock.close()
    upstream.close()


def main():
    parser = argparse.ArgumentParser(description="シンプルなTCP中継リレー（外部公開用・保険Plan B）")
    parser.add_argument("--listen-host", default="0.0.0.0", help="外部から待ち受けるアドレス（既定: 0.0.0.0）")
    parser.add_argument("--listen-port", type=int, default=5000, help="外部から待ち受けるポート（既定: 5000）")
    parser.add_argument("--forward-host", default="127.0.0.1", help="転送先ホスト（既定: 127.0.0.1、SSHトンネルの出口）")
    parser.add_argument("--forward-port", type=int, default=5001, help="転送先ポート（既定: 5001）")
    args = parser.parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.listen_host, args.listen_port))
    server.listen(20)
    print(f"[relay] {args.listen_host}:{args.listen_port} で待ち受け中 → "
          f"{args.forward_host}:{args.forward_port} へ中継します（Ctrl+Cで終了）")

    try:
        while True:
            client_sock, addr = server.accept()
            print(f"[relay] 接続: {addr}")
            threading.Thread(
                target=handle_client,
                args=(client_sock, args.forward_host, args.forward_port),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("\n[relay] 終了します")
    finally:
        server.close()


if __name__ == "__main__":
    main()
