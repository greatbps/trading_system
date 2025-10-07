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

async def direct_monitoring_test():
    """시장 시간 체크를 완전히 우회하고 직접 모니터링 로직 실행"""
    try:
        print("=== 직접 모니터링 테스트 ===")
        print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return False
        
        print("Trading System 초기화 완료")
        
        # DB Auto Trader 가져오기
        db_auto_trader = trading_system.db_auto_trader
        print(f"모니터링 상태: {db_auto_trader.is_monitoring}")
        
        # 시장 시간 체크를 우회하기 위해 임시로 메서드 교체
        original_method = getattr(db_auto_trader.market_manager, 'is_monitoring_allowed_now', None)
        
        # 항상 True를 반환하는 함수로 대체
        def always_allow():
            return True
            
        db_auto_trader.market_manager.is_monitoring_allowed_now = always_allow
        
        print("시장 시간 체크 우회 설정 완료")
        
        # 모니터링 사이클 실행 전 활성 종목 수 확인
        from database.models import MonitoringStock
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from config import Config
        
        config = Config()
        engine = create_engine(config.database.DB_URL)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            active_count = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE'
            ).count()
            print(f"활성 모니터링 종목 수: {active_count}개")
        
        # 직접 모니터링 사이클 실행
        print("모니터링 사이클 실행 중...")
        await db_auto_trader._monitoring_cycle()
        print("모니터링 사이클 실행 완료")
        
        # 원본 메서드 복원 (있다면)
        if original_method:
            db_auto_trader.market_manager.is_monitoring_allowed_now = original_method
        
        # 결과 확인 - 최근 업데이트된 종목
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
                print("모니터링이 아직 동작하지 않았습니다.")
                return False
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(direct_monitoring_test())
    if success:
        print("\n직접 모니터링 테스트 완료!")
    else:
        print("\n직접 모니터링 테스트 실패!")