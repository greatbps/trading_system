@echo off
REM 자동화된 거래 실행 배치 스크립트
REM EOF 에러와 시간대 문제 해결

cd /d D:\trading_system

REM 환경 변수 설정
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 현재 시간 확인
echo [%date% %time%] 자동화 거래 실행 시작 >> logs\batch_execution.log

REM Python 스크립트 실행 (비대화형)
python run_trading.py --schedule >> logs\batch_execution.log 2>&1

echo [%date% %time%] 자동화 거래 실행 완료 >> logs\batch_execution.log

REM 30초 대기 후 종료 (로그 확인용)
timeout /t 30 /nobreak > nul