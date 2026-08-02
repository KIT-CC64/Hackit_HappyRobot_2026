@echo off
chcp 65001 >nul
echo ================================================
echo   SSH中継トンネル起動（保険Plan B用・自動再接続版）
echo ================================================
echo.
echo Plan A（PCとスマホを両方KIT-GUEST3につないで、PCのIPに直接アクセス）が
echo うまくいかない場合の保険です。事前に仮想マシン側で以下を起動しておくこと：
echo   python3 tcp_relay.py --listen-port 5000 --forward-port 5001
echo.
set /p TEAMNO="チーム番号を入力してください（例: 1）: "
echo.
echo team%TEAMNO%@team%TEAMNO%.hackit へSSH接続し、
echo このPCのlocalhost:5000(Flask)を仮想マシンのlocalhost:5001へ転送します。
echo パスワードはチームリーダーの学籍番号です。
echo.
echo 【8/2追加】このウィンドウはSSHが切断されても自動で再接続を試みます。
echo 完全に終わらせたい時だけ、このウィンドウを閉じるかCtrl+Cを押してください。
echo ================================================
echo.

:RETRY
echo [%date% %time%] トンネルを開始します（切断されたら自動で再接続します）...
ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -N -R 5001:localhost:5000 team%TEAMNO%@team%TEAMNO%.hackit

echo.
echo [%date% %time%] 接続が切れました。3秒後に自動で再接続します（やめる場合はこのウィンドウを閉じてください）...
timeout /t 3 /nobreak >nul
goto RETRY