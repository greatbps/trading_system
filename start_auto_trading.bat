@echo off
echo === AUTO TRADING DAEMON STARTER ===
echo 50만원 계좌 안전 자동매매 시스템
echo.

cd /d "D:\trading_system"

echo [%date% %time%] Starting Auto Trading Daemon...
echo.

REM 가상환경 활성화 후 데몬 실행
call "trading_env_64\Scripts\activate.bat"
python auto_trading_daemon.py

echo.
echo [%date% %time%] Auto Trading Daemon Stopped
pause