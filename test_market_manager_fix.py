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

async def test_market_manager_fix():
    """market_manager 수정 테스트"""
    try:
        print("=== market_manager 수정 테스트 ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        print("Trading System 초기화 중...")
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return False
        
        print("Trading System 초기화 완료")
        
        # DB Auto Trader 확인
        db_auto_trader = trading_system.db_auto_trader
        if not db_auto_trader:
            print("DB Auto Trader가 없습니다")
            return False
        
        print(f"DB Auto Trader: {type(db_auto_trader).__name__}")
        print(f"market_manager: {type(db_auto_trader.market_manager).__name__}")
        
        # market_manager 메서드 확인
        market_manager = db_auto_trader.market_manager
        print(f"has is_monitoring_allowed_now: {hasattr(market_manager, 'is_monitoring_allowed_now')}")
        
        if hasattr(market_manager, 'is_monitoring_allowed_now'):
            print("market_manager 메서드 테스트 중...")
            result = market_manager.is_monitoring_allowed_now()
            print(f"is_monitoring_allowed_now(): {result}")
            
            # 실제 모니터링 사이클 테스트
            print("모니터링 사이클 직접 실행 테스트...")
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
            
            with Session() as session:
                recent_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE',
                    MonitoringStock.last_check_time.isnot(None)
                ).order_by(MonitoringStock.last_check_time.desc()).limit(3).all()
                
                if recent_stocks:
                    print("최근 체크된 종목들:")
                    for stock in recent_stocks:
                        print(f"  - {stock.symbol}({stock.name}) at {stock.last_check_time}")
                    print("SUCCESS: 모니터링이 정상 동작했습니다!")
                    return True
                else:
                    print("WARNING: 아직 체크된 종목이 없습니다.")
                    return False
        else:
            print(f"ERROR: market_manager에 is_monitoring_allowed_now 메서드가 없습니다")
            print(f"market_manager 타입: {type(market_manager)}")
            print(f"available methods: {[m for m in dir(market_manager) if not m.startswith('_')]}")
            return False
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_market_manager_fix())
    if success:
        print("\nmarket_manager 수정 테스트 성공!")
    else:
        print("\nmarket_manager 수정 테스트 실패!")