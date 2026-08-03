@echo off
chcp 65001 >nul
echo ================================================
echo   ケロッと！はらぺこエコガエル - 起動スクリプト
echo ================================================
echo.
echo このPC1台に集約した本番構成用です。
echo Flask（API+Web）・センサーブリッジ・AI推論を、それぞれ別ウィンドウで起動します。
echo.
echo [事前確認1] VOICEVOXアプリを起動済みですか？
echo            （起動していないと音声だけスタブ動作＝無音になります）
echo [事前確認2] サーボ制御用Arduino・カウント用Arduinoの2台とも
echo            このPCにUSB接続済みですか？（未接続でもデモ自体は止まりません）
echo [事前確認3] Arduino IDEのシリアルモニタは閉じてありますか？
echo            （開いたままだとポートが占有されPythonから接続できません）
echo [事前確認4] voice\warmup_voice_cache.bat を一度実行済みですか？
echo            （未実施だと本番中に音声合成タイムアウトで声が出ないことがあります）
echo.
pause

echo.
echo [1/3] Flaskサーバーを起動します（server\app.py）...
start "Flask Server" cmd /k "chcp 65001>nul && set PYTHONIOENCODING=utf-8 && cd /d %~dp0server && python app.py"

echo 3秒待機（Flask起動待ち）...
timeout /t 3 /nobreak >nul

echo.
echo [2/3] センサーブリッジを起動します（server\sensor_bridge.py・任意）...
start "Sensor Bridge" cmd /k "chcp 65001>nul && set PYTHONIOENCODING=utf-8 && cd /d %~dp0server && python sensor_bridge.py"

echo.
echo [3/3] AI推論・ステートマシンを起動します（ai_core\State machine.py）...
start "AI State Machine" cmd /k "chcp 65001>nul && set PYTHONIOENCODING=utf-8 && cd /d %~dp0ai_core && python "State machine.py""

echo.
echo ================================================
echo 起動処理を開始しました。
echo.
echo スマホからのアクセス方法（8/2時点、Plan Cを本命に変更）:
echo   [本命] network_relay\start_cloudflare_tunnel.bat を実行し、
echo          表示される公開URL/QRコードでアクセス（会場WiFi非依存）
echo   [予備] 同一WiFiで繋がる場合のみ http://＜このPCのIPアドレス＞:5000/
echo          （IPアドレスは別窓で ipconfig を実行して確認）
echo 詳細は network_relay\README.md を参照。
echo ================================================
pause
