@echo off
REM 자동 거래 시스템 실행 스크립트
REM 매일 08:30에 실행되어 자동으로 거래를 수행합니다.

echo ========================================
echo 자동 거래 시스템 시작 - %DATE% %TIME%
echo ========================================

REM 작업 디렉토리 이동
cd /d D:\trading_system

REM Python 환경 설정
set PYTHONIOENCODING=utf-8
set PYTHONPATH=D:\trading_system

REM 가상환경 활성화 (만약 있다면)
REM call venv\Scripts\activate

echo 자동 거래 모드로 시스템 시작...
python main.py --mode auto --no-interactive

echo ========================================
echo 자동 거래 시스템 종료 - %DATE% %TIME%
echo ========================================

REM 로그 파일에 실행 기록 저장
echo [%DATE% %TIME%] 자동 거래 시스템 실행 완료 >> D:\trading_system\logs\auto_trading_schedule.log