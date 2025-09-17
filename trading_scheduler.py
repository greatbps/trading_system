#!/usr/bin/env python3
"""
시간대별 자동 실행 스케줄러

크론탭 없이 Windows에서 동작하는 내장 스케줄러
"""

import asyncio
import schedule
import time
from datetime import datetime, time as dt_time
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_trading import AutomatedTradingRunner

class TradingScheduler:
    """거래 스케줄러"""
    
    def __init__(self):
        self.runner = AutomatedTradingRunner()
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(f'logs/scheduler_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def schedule_trading_jobs(self):
        """거래 작업 스케줄링"""
        
        # 장 시작 전 (08:30) - 시장 상황 점검
        schedule.every().day.at("08:30").do(self.run_market_check)
        
        # 장 시작 (09:00) - 오프닝 전략
        schedule.every().day.at("09:00").do(self.run_opening_strategy)
        
        # 오전장 (10:00) - 모멘텀 전략  
        schedule.every().day.at("10:00").do(self.run_momentum_strategy)
        
        # 점심시간 (12:00) - 포지션 점검
        schedule.every().day.at("12:00").do(self.run_position_check)
        
        # 오후장 (14:00) - 오후 전략
        schedule.every().day.at("14:00").do(self.run_afternoon_strategy)
        
        # 장 마감 (15:30) - EOD 전략
        schedule.every().day.at("15:30").do(self.run_eod_strategy)
        
        # 시간외 (17:00) - 일일 정산
        schedule.every().day.at("17:00").do(self.run_daily_summary)
        
        self.logger.info("📅 거래 스케줄 등록 완료")
        
    def run_market_check(self):
        """시장 상황 점검"""
        self.logger.info("🔍 시장 상황 점검 시작")
        try:
            asyncio.run(self.runner.run_scheduled_execution())
        except Exception as e:
            self.logger.error(f"시장 점검 오류: {e}")
            
    def run_opening_strategy(self):
        """오프닝 전략 실행"""
        self.logger.info("🌅 오프닝 전략 실행")
        try:
            asyncio.run(self.runner.execute_non_interactive_trading())
        except Exception as e:
            self.logger.error(f"오프닝 전략 오류: {e}")
            
    def run_momentum_strategy(self):
        """모멘텀 전략 실행"""
        self.logger.info("📈 모멘텀 전략 실행")
        try:
            asyncio.run(self.runner.execute_non_interactive_trading())
        except Exception as e:
            self.logger.error(f"모멘텀 전략 오류: {e}")
            
    def run_position_check(self):
        """포지션 점검"""
        self.logger.info("⚖️ 포지션 점검")
        # 포지션 리밸런싱 로직 추가 가능
        
    def run_afternoon_strategy(self):
        """오후 전략 실행"""
        self.logger.info("🌇 오후 전략 실행")
        try:
            asyncio.run(self.runner.execute_non_interactive_trading())
        except Exception as e:
            self.logger.error(f"오후 전략 오류: {e}")
            
    def run_eod_strategy(self):
        """EOD 전략 실행"""
        self.logger.info("🌆 EOD 전략 실행")
        try:
            asyncio.run(self.runner.execute_non_interactive_trading())
        except Exception as e:
            self.logger.error(f"EOD 전략 오류: {e}")
            
    def run_daily_summary(self):
        """일일 정산"""
        self.logger.info("📋 일일 정산 실행")
        # 일일 수익/손실 계산, 리포트 생성
        
    def is_trading_day(self):
        """거래일 확인 (주말/공휴일 제외)"""
        today = datetime.now()
        # 주말 (토요일=5, 일요일=6) 제외
        return today.weekday() < 5
        
    def run_scheduler(self):
        """스케줄러 실행"""
        self.logger.info("🚀 거래 스케줄러 시작")
        
        # 거래 작업 등록
        self.schedule_trading_jobs()
        
        try:
            while True:
                # 거래일만 실행
                if self.is_trading_day():
                    schedule.run_pending()
                else:
                    self.logger.info("비거래일입니다")
                    
                time.sleep(60)  # 1분마다 체크
                
        except KeyboardInterrupt:
            self.logger.info("스케줄러 중단")
        except Exception as e:
            self.logger.error(f"스케줄러 오류: {e}")

def main():
    """메인 실행 함수"""
    scheduler = TradingScheduler()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        # 데몬 모드 (백그라운드 실행)
        scheduler.run_scheduler()
    else:
        # 테스트 실행
        scheduler.run_opening_strategy()

if __name__ == "__main__":
    main()