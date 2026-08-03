@echo off
chcp 65001 >nul
echo ================================================
echo   Cloudflare Tunnel 起動（Plan C・会場ネットワーク非依存の保険）
echo ================================================
echo.
echo Plan A（同一WiFi直接アクセス）・Plan B（配布VM経由の中継）が
echo うまくいかない場合の最終手段です。
echo ノートPCから外部（Cloudflare）への発信さえ通れば、会場WiFiの
echo クライアント分離やVM側のファイアウォール設定に関係なく、
echo スマホは会場WiFiでもモバイル回線でも公開URLでアクセスできます。
echo.
echo 事前に server\app.py（Flask）を起動しておいてください
echo （run_demo.batで起動済みなら問題ありません）。
echo.
pause

cd /d %~dp0

if not exist cloudflared.exe (
    echo cloudflared.exe が見つからないため、初回のみダウンロードします...
    powershell -Command "try { Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe' -UseBasicParsing } catch { exit 1 }"
    if not exist cloudflared.exe (
        echo.
        echo [エラー] ダウンロードに失敗しました。
        echo 会場から外部インターネットへ接続できているか確認してください。
        echo 手動で用意する場合は、別のネット環境で
        echo https://github.com/cloudflare/cloudflared/releases を開き、
        echo cloudflared-windows-amd64.exe をダウンロードして、このフォルダに
        echo 「cloudflared.exe」という名前で置いてから、もう一度実行してください。
        echo.
        pause
        exit /b 1
    )
    echo ダウンロード完了。
    echo.
)

python start_cloudflare_tunnel.py

echo.
echo トンネルを終了しました。
pause
