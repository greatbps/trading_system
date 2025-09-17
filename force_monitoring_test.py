#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from pathlib import Path

# UTF-8 인코딩 설정  
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def force_monitoring():
    """시장 시간 체크를 무시하고 강제 모니터링 실행"""
    try:
        print("=== 강제 모니터링 테스트 ===")
        
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
        print(f"현재 모니터링 상태: {db_auto_trader.is_monitoring}")
        
        # 시장 시간 체크를 우회하는 방법
        original_market_check = db_auto_trader.market_manager.is_monitoring_allowed_now
        
        # 항상 True를 반환하는 함수로 대체
        db_auto_trader.market_manager.is_monitoring_allowed_now = lambda: True
        
        print("시장 시간 체크 무시 설정 완료")
        
        # 모니터링 한 번만 실행
        print("모니터링 사이클 실행 중...")
        await db_auto_trader._monitoring_cycle()
        print("모니터링 사이클 실행 완료")
        
        # 원본 함수 복원
        db_auto_trader.market_manager.is_monitoring_allowed_now = original_market_check
        
        return True
        
    except Exception as e:
        print(f"강제 모니터링 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(force_monitoring())
    if success:
        print("\n강제 모니터링 테스트 성공!")
    else:
        print("\n강제 모니터링 테스트 실패!")