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

async def test_market_schedule():
    """시장 시간 체크 테스트"""
    try:
        print("=== 시장 시간 체크 테스트 ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return False
        
        # Market Schedule Manager 확인
        if hasattr(trading_system, 'market_schedule_manager'):
            market_manager = trading_system.market_schedule_manager
            print(f"MarketScheduleManager: {type(market_manager).__name__}")
            
            # 현재 시장 상태 업데이트
            await market_manager.update_market_status()
            
            # 상태 정보 출력
            current_status = market_manager.current_status
            print(f"현재 시장 상태: {current_status.value}")
            
            if hasattr(market_manager, '_get_status_korean'):
                status_korean = market_manager._get_status_korean(current_status)
                print(f"한국어 상태: {status_korean}")
            
            # 모니터링/거래 허용 여부 확인
            is_market_open = market_manager.is_market_open_now()
            is_trading_allowed = market_manager.is_trading_allowed_now()
            is_monitoring_allowed = market_manager.is_monitoring_allowed_now()
            
            print(f"시장 개장 중: {is_market_open}")
            print(f"거래 허용: {is_trading_allowed}")
            print(f"모니터링 허용: {is_monitoring_allowed}")
            
            # 다음 개장 시간 확인
            try:
                next_market_open = await market_manager.get_next_market_open()
                if next_market_open:
                    print(f"다음 개장 시간: {next_market_open.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print("다음 개장 시간: 조회 불가")
            except Exception as e:
                print(f"다음 개장 시간 조회 오류: {e}")
            
            # 주간 일정 확인
            try:
                weekly_schedule = await market_manager.get_weekly_schedule()
                if weekly_schedule:
                    print(f"\n=== 이번 주 시장 일정 ===")
                    for day_info in weekly_schedule:
                        date = day_info['date']
                        weekday = day_info['weekday_korean']
                        is_market_open = day_info['is_market_open']
                        is_today = day_info['is_today']
                        
                        status_mark = "개장" if is_market_open else "휴장"
                        today_mark = " (오늘)" if is_today else ""
                        
                        print(f"  {date} {weekday}: {status_mark}{today_mark}")
            except Exception as e:
                print(f"주간 일정 조회 오류: {e}")
            
            return True
        else:
            print("MarketScheduleManager가 없습니다")
            return False
            
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_market_schedule())
    if success:
        print("\n시장 시간 체크 테스트 완료!")
    else:
        print("\n시장 시간 체크 테스트 실패!")