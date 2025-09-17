#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_improved_monitoring():
    """개선된 모니터링 시스템 테스트"""
    try:
        print("=== 개선된 모니터링 시스템 테스트 ===")
        print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        print("Trading System 초기화 중...")
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return False
        
        print("Trading System 초기화 완료")
        
        # DB Auto Trader 가져오기
        db_auto_trader = trading_system.db_auto_trader
        print(f"모니터링 상태: {db_auto_trader.is_monitoring}")
        
        # Market Schedule Manager 테스트 (auto_trading_handler 내부에서 접근)
        if hasattr(trading_system, 'auto_trading_handler') and trading_system.auto_trading_handler:
            market_manager = trading_system.auto_trading_handler.market_manager
            print("Market Schedule Manager 테스트 중...")
        else:
            print("auto_trading_handler가 없어 Market Schedule Manager 테스트 건너뜀")
            market_manager = None
        
        # 오늘 날짜 시장 일정 조회 (토큰 방식)
        if market_manager:
            today = datetime.now().strftime('%Y%m%d')
            print(f"오늘 ({today}) 시장 일정 조회 중...")
            
            schedule = await market_manager.get_market_schedule(today)
            if schedule:
                print(f"오늘 시장 상태:")
                print(f"  - 개장 여부: {schedule.is_market_open}")
                print(f"  - 영업일 여부: {schedule.is_business_day}")
                print(f"  - 거래일 여부: {schedule.is_trading_day}")
                print(f"  - 요일 코드: {schedule.weekday_code}")
            else:
                print("시장 일정 조회 실패")
                return False
            
            # 시장 상태 업데이트 테스트
            print("시장 상태 업데이트 테스트 중...")
            market_status = await market_manager.update_market_status()
            print(f"현재 시장 상태: {market_status}")
            print(f"모니터링 허용 여부: {market_manager.is_monitoring_allowed_now()}")
            
            # 모니터링 사이클 실행 테스트
            monitoring_allowed = market_manager.is_monitoring_allowed_now()
        else:
            print("market_manager가 없어 직접 모니터링 실행 시도")
            monitoring_allowed = True
        
        if monitoring_allowed:
            print("모니터링 사이클 실행 중...")
            await db_auto_trader._monitoring_cycle()
            print("모니터링 사이클 실행 완료")
            
            # 결과 확인
            from database.models import MonitoringStock
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config import Config
            
            config = Config()
            engine = create_engine(config.database.DB_URL)
            Session = sessionmaker(bind=engine)
            
            print("결과 확인 중...")
            with Session() as session:
                recent_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE',
                    MonitoringStock.last_check_time.isnot(None)
                ).order_by(MonitoringStock.last_check_time.desc()).limit(5).all()
                
                if recent_stocks:
                    print("최근 체크된 종목들:")
                    for stock in recent_stocks:
                        print(f"  - {stock.symbol}({stock.name}) at {stock.last_check_time}")
                    print("모니터링이 정상 동작했습니다!")
                    return True
                else:
                    print("모니터링 결과가 아직 반영되지 않았습니다.")
                    return False
        else:
            print("현재 모니터링이 허용되지 않는 시간입니다.")
            print("(주말, 휴장일, 또는 장외 시간)")
            return True  # 정상적인 상황
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_improved_monitoring())
    if success:
        print("\n개선된 모니터링 시스템 테스트 성공!")
    else:
        print("\n개선된 모니터링 시스템 테스트 실패!")