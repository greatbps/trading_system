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

async def simple_monitoring_test():
    """간단한 모니터링 테스트"""
    try:
        print("=== 간단한 모니터링 테스트 ===")
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
        
        # 직접 모니터링 사이클 실행
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
            recent = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.last_check_time.isnot(None)
            ).order_by(MonitoringStock.last_check_time.desc()).first()
            
            if recent:
                print(f"마지막 체크: {recent.symbol}({recent.name}) at {recent.last_check_time}")
                print("모니터링이 정상 동작했습니다!")
            else:
                print("모니터링이 아직 동작하지 않았습니다.")
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_monitoring_test())
    if success:
        print("\n간단한 모니터링 테스트 완료!")
    else:
        print("\n간단한 모니터링 테스트 실패!")