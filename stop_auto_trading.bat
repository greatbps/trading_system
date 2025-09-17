@echo off
echo === MANUAL AUTO TRADING STOP ===
echo.

cd /d "D:\trading_system"

REM 가상환경 활성화 후 중지 스크립트 실행
call "trading_env_64\Scripts\activate.bat"
python stop_auto_trading.py

echo.
pause