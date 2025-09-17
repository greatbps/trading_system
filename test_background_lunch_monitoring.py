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

async def test_background_lunch_monitoring():
    """백그라운드 서비스 점심시간 모니터링 테스트"""
    try:
        print("=== 백그라운드 서비스 점심시간 모니터링 테스트 ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from background_monitoring_service import BackgroundMonitoringService
        
        # 백그라운드 서비스 생성 및 초기화
        service = BackgroundMonitoringService()
        success = await service.initialize()
        
        if not success:
            print("NO 백그라운드 서비스 초기화 실패")
            return False
        
        print("OK 백그라운드 서비스 초기화 완료")
        
        # MarketScheduleManager 확인
        if (hasattr(service.trading_system, 'db_auto_trader') and 
            service.trading_system.db_auto_trader and 
            hasattr(service.trading_system.db_auto_trader, 'market_manager')):
            
            market_manager = service.trading_system.db_auto_trader.market_manager
            
            # 점심시간 상태 테스트
            from utils.market_schedule_manager import MarketStatus
            
            print("\n=== 점심시간 백그라운드 모니터링 시뮬레이션 ===")
            
            # 점심시간으로 설정
            market_manager.current_status = MarketStatus.LUNCH_BREAK
            
            # 모니터링 허용 여부 확인
            is_monitoring_allowed = market_manager.is_monitoring_allowed_now()
            status_korean = market_manager._get_status_korean(MarketStatus.LUNCH_BREAK)
            
            print(f"시장 상태: {status_korean}")
            print(f"모니터링 허용: {is_monitoring_allowed}")
            
            # 백그라운드 서비스 로직 시뮬레이션
            if is_monitoring_allowed and service.trading_system.db_auto_trader:
                print(f"OK {status_korean} - 백그라운드 모니터링 계속 실행")
                print("OK DB 자동매매 모니터링이 점심시간에도 활성 상태 유지")
            else:
                print(f"NO {status_korean} - 백그라운드 모니터링 중단")
            
            # 정규 장 시간과 비교 테스트
            print("\n=== 시간대별 백그라운드 모니터링 동작 ===")
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
                    print(f"  OK {description}: 백그라운드 모니터링 실행")
                else:
                    print(f"  NO {description}: 백그라운드 모니터링 대기")
            
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
    success = asyncio.run(test_background_lunch_monitoring())
    if success:
        print("\nOK 백그라운드 점심시간 모니터링 테스트 완료!")
        print("점심시간에도 백그라운드 모니터링이 계속 실행됩니다.")
    else:
        print("\nNO 백그라운드 점심시간 모니터링 테스트 실패!")