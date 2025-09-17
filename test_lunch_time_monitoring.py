#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, time

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_lunch_time_monitoring():
    """점심시간 모니터링 테스트"""
    try:
        print("=== 점심시간 모니터링 허용 테스트 ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("❌ Trading System 초기화 실패")
            return False
        
        # Market Schedule Manager 확인 (db_auto_trader 안에 있음)
        if hasattr(trading_system, 'db_auto_trader') and trading_system.db_auto_trader and hasattr(trading_system.db_auto_trader, 'market_manager'):
            market_manager = trading_system.db_auto_trader.market_manager
            
            # 현재 시장 상태 업데이트
            await market_manager.update_market_status()
            
            print(f"\n현재 시장 상태: {market_manager.current_status.value}")
            print(f"한국어 상태: {market_manager._get_status_korean(market_manager.current_status)}")
            
            # 모니터링 허용 여부 확인
            is_monitoring_allowed = market_manager.is_monitoring_allowed_now()
            print(f"모니터링 허용: {is_monitoring_allowed}")
            
            # 점심시간 시뮬레이션 테스트
            print("\n=== 점심시간 시뮬레이션 테스트 ===")
            
            # 현재 시간 백업
            original_time = datetime.now().time()
            
            # 점심시간으로 강제 설정 (12:30)
            from utils.market_schedule_manager import MarketStatus
            market_manager.current_status = MarketStatus.LUNCH_BREAK
            
            lunch_monitoring_allowed = market_manager.is_monitoring_allowed_now()
            print(f"점심시간 상태: {market_manager._get_status_korean(MarketStatus.LUNCH_BREAK)}")
            print(f"점심시간 모니터링 허용: {lunch_monitoring_allowed}")
            
            if lunch_monitoring_allowed:
                print("OK 점심시간에도 모니터링이 허용됩니다!")
            else:
                print("NO 점심시간 모니터링이 차단되어 있습니다.")
            
            # 각 시간대별 모니터링 허용 상태 확인
            print("\n=== 시간대별 모니터링 허용 상태 ===")
            test_statuses = [
                (MarketStatus.CLOSED, "휴장"),
                (MarketStatus.PRE_MARKET, "장 시작 전 (동시호가)"),
                (MarketStatus.OPEN, "정규 거래"),
                (MarketStatus.LUNCH_BREAK, "점심 시간"),
                (MarketStatus.AFTER_HOURS, "장 마감 후 (동시호가)"),
                (MarketStatus.WEEKEND, "주말")
            ]
            
            for status, korean_name in test_statuses:
                market_manager.current_status = status
                allowed = market_manager.is_monitoring_allowed_now()
                status_mark = "OK" if allowed else "NO"
                print(f"  {status_mark} {korean_name}: {'허용' if allowed else '차단'}")
            
            return True
        else:
            print("NO MarketScheduleManager가 없습니다")
            return False
            
    except Exception as e:
        print(f"NO 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_lunch_time_monitoring())
    if success:
        print("\nOK 점심시간 모니터링 테스트 완료!")
    else:
        print("\nNO 점심시간 모니터링 테스트 실패!")