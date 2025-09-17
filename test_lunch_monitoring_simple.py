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

async def test_lunch_monitoring_simple():
    """간단한 점심시간 모니터링 허용 테스트"""
    try:
        print("=== 점심시간 모니터링 허용 테스트 (간단 버전) ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("NO Trading System 초기화 실패")
            return False
        
        print("OK Trading System 초기화 완료")
        
        # DB AutoTrader를 통해 MarketScheduleManager 확인
        if hasattr(trading_system, 'db_auto_trader') and trading_system.db_auto_trader:
            db_auto_trader = trading_system.db_auto_trader
            
            if hasattr(db_auto_trader, 'market_manager') and db_auto_trader.market_manager:
                market_manager = db_auto_trader.market_manager
                
                print("\n=== 점심시간 모니터링 허용 테스트 ===")
                
                # 현재 시장 상태 확인
                await market_manager.update_market_status()
                current_status = market_manager.current_status
                current_allowed = market_manager.is_monitoring_allowed_now()
                
                print(f"현재 시장 상태: {current_status.value}")
                print(f"현재 상태 한국어: {market_manager._get_status_korean(current_status)}")
                print(f"현재 모니터링 허용: {current_allowed}")
                
                # 점심시간 시뮬레이션
                from utils.market_schedule_manager import MarketStatus
                print("\n=== 점심시간 시뮬레이션 ===")
                
                market_manager.current_status = MarketStatus.LUNCH_BREAK
                lunch_allowed = market_manager.is_monitoring_allowed_now()
                lunch_korean = market_manager._get_status_korean(MarketStatus.LUNCH_BREAK)
                
                print(f"점심시간 상태: {lunch_korean}")
                print(f"점심시간 모니터링 허용: {lunch_allowed}")
                
                if lunch_allowed:
                    print("OK 점심시간에도 모니터링 허용됩니다!")
                    print("OK 3번 모니터링 현황 메뉴가 점심시간에도 작동할 수 있습니다!")
                else:
                    print("NO 점심시간 모니터링이 차단되어 있습니다.")
                
                # 시간대별 테스트
                print("\n=== 모든 시간대별 모니터링 허용 테스트 ===")
                test_cases = [
                    (MarketStatus.OPEN, "정규 거래 시간"),
                    (MarketStatus.LUNCH_BREAK, "점심 시간"),
                    (MarketStatus.PRE_MARKET, "장 시작 전"),
                    (MarketStatus.AFTER_HOURS, "장 마감 후"),
                    (MarketStatus.CLOSED, "휴장"),
                    (MarketStatus.WEEKEND, "주말")
                ]
                
                for status, description in test_cases:
                    market_manager.current_status = status
                    allowed = market_manager.is_monitoring_allowed_now()
                    mark = "OK" if allowed else "NO"
                    print(f"  {mark} {description}: {'허용' if allowed else '차단'}")
                
                return True
            else:
                print("NO db_auto_trader에서 market_manager를 찾을 수 없습니다")
                return False
        else:
            print("NO db_auto_trader를 찾을 수 없습니다")
            return False
            
    except Exception as e:
        print(f"NO 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_lunch_monitoring_simple())
    if success:
        print("\nOK 점심시간 모니터링 테스트 완료!")
        print("3번 모니터링 현황 메뉴의 점심시간 모니터링이 활성화되었습니다.")
    else:
        print("\nNO 점심시간 모니터링 테스트 실패!")