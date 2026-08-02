@echo off
chcp 65001 >nul
echo ================================================
echo   ケロッと！はらぺこエコガエル - 起動スクリプト（ホストPC用）
echo ================================================
echo.
echo 【構成メモ】Flask(server\app.py)とsensor_bridge.pyは
echo            2年生Bの仮想マシン側で動かす運用です。
echo            このスクリプトはホストPC側（RealSense・サーボArduino接続機）で
echo            AI推論・ステートマシンだけを起動します。
echo.
echo [事前確認1] 仮想マシン側で server\app.py と sensor_bridge.py は
echo            起動済みですか？（Flask未起動でもデモ自体は止まりませんが
echo            満腹度・レベルがWeb画面に反映されません）
echo [事前確認2] ai_core\State machine.py 冒頭の FLASK_SERVER_URL が
echo            仮想マシンの最新IPアドレスと一致していますか？
echo [事前確認3] VOICEVOXアプリを起動済みですか？
echo            （起動していないと音声だけスタブ動作＝無音になります）
echo [事前確認4] サーボ制御用Arduinoはこのホストにusb接続済みですか？
echo            （フォトインタラプタ用Arduinoは仮想マシン側です）
echo.
pause

echo.
echo AI推論・ステートマシンを起動します（ai_core\State machine.py）...
cd /d %~dp0ai_core
python "State machine.py"

pause
