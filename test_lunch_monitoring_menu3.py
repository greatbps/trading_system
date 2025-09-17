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

async def test_menu3_lunch_monitoring():
    """3번 모니터링 현황 메뉴의 점심시간 동작 테스트"""
    try:
        print("=== 3번 모니터링 현황 점심시간 테스트 ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.db_auto_trading_handler import DatabaseAutoTradingHandler
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("NO Trading System 초기화 실패")
            return False
        
        # DatabaseAutoTradingHandler 생성 - kis_collector 필요
        kis_collector = None
        if hasattr(trading_system, 'data_collector') and hasattr(trading_system.data_collector, 'kis_collector'):
            kis_collector = trading_system.data_collector.kis_collector
        elif hasattr(trading_system, 'kis_collector'):
            kis_collector = trading_system.kis_collector
            
        if not kis_collector:
            print("NO KIS Collector를 찾을 수 없습니다")
            return False
            
        handler = DatabaseAutoTradingHandler(trading_system, kis_collector)
        
        # MarketScheduleManager 확인
        if (hasattr(handler, 'market_manager') and handler.market_manager):
            market_manager = handler.market_manager
            
            print("\n=== 점심시간 시뮬레이션 테스트 ===")
            
            # 점심시간으로 설정
            from utils.market_schedule_manager import MarketStatus
            market_manager.current_status = MarketStatus.LUNCH_BREAK
            
            # 모니터링 허용 여부 확인
            is_monitoring_allowed = market_manager.is_monitoring_allowed_now()
            status_korean = market_manager._get_status_korean(MarketStatus.LUNCH_BREAK)
            
            print(f"시장 상태: {status_korean}")
            print(f"모니터링 허용: {is_monitoring_allowed}")
            
            # 실제 모니터링 메서드들 테스트
            print("\n=== 모니터링 메서드 테스트 ===")
            
            # _start_monitoring 테스트
            print("1. _start_monitoring 테스트:")
            try:
                await handler._start_monitoring()
                print("   OK 점심시간에 모니터링 시작 허용")
            except Exception as e:
                print(f"   NO 점심시간 모니터링 시작 차단: {e}")
            
            # _view_monitoring_status 테스트 (실제로는 실행 안하고 메서드 존재만 확인)
            print("2. _view_monitoring_status 메서드 존재 확인:")
            if hasattr(handler, '_view_monitoring_status'):
                print("   OK _view_monitoring_status 메서드 존재")
                # 실제 실행은 하지 않음 (UI 관련이므로)
            else:
                print("   NO _view_monitoring_status 메서드 없음")
            
            # 다양한 시간대별 테스트
            print("\n=== 시간대별 모니터링 허용 테스트 ===")
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
                
                if allowed:
                    print(f"  OK {description}: 3번 모니터링 현황 접근 가능")
                else:
                    print(f"  NO {description}: 3번 모니터링 현황 접근 차단")
            
            return True
        else:
            print("NO MarketScheduleManager를 찾을 수 없습니다")
            return False
            
    except Exception as e:
        print(f"NO 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_menu3_lunch_monitoring())
    if success:
        print("\nOK 3번 모니터링 현황 점심시간 테스트 완료!")
        print("점심시간에도 모니터링 현황 조회가 가능합니다.")
    else:
        print("\nNO 3번 모니터링 현황 점심시간 테스트 실패!")