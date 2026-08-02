@echo off
chcp 65001 >nul
echo ================================================
echo   VOICEVOX 事前キャッシュ生成（本番前に1回実行）
echo ================================================
echo.
echo これを実行すると、カエルが喋る全セリフを事前に合成して
echo voice\cache\ に保存します。本番中はここで生成したWAVを
echo 再生するだけになるので、VOICEVOXの合成待ちタイムアウトで
echo 声が出ない問題が起きなくなります。
echo.
echo [事前確認] VOICEVOXアプリを起動済みですか？（起動していないと失敗します）
echo.
pause

cd /d %~dp0
python voice_control.py --warmup

echo.
echo ================================================
echo 完了しました（失敗0件ならOKです）。
echo セリフ（LINE_TEMPLATES / RETRY_LINES）を変更した場合は
echo 必ずもう一度このスクリプトを実行してください。
echo ================================================
pause
