@echo off
chcp 65001 >nul
echo ================================================
echo   SSH中継トンネル起動（保険Plan B用）
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
echo このウィンドウは接続を維持するため、デモが終わるまで閉じないでください。
echo ================================================
echo.
ssh -N -R 5001:localhost:5000 team%TEAMNO%@team%TEAMNO%.hackit

echo.
echo （接続が切れた/終了しました）
pause
