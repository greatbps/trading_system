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

async def check_monitoring_status():
    """현재 모니터링 상태 확인"""
    try:
        print("=== 모니터링 상태 확인 ===")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return
        
        # DB Auto Trader 상태 확인
        db_auto_trader = trading_system.db_auto_trader
        if db_auto_trader:
            print(f"모니터링 실행 중: {db_auto_trader.is_monitoring}")
            
            # 상세 상태 정보
            status = db_auto_trader.get_monitoring_status()
            print(f"활성 종목 수: {len(status.get('monitoring_stocks', []))}")
            print(f"거래 활성화: {status.get('trading_enabled', False)}")
            
            if status.get('monitoring_stocks'):
                print("\n활성 모니터링 종목:")
                for stock in status['monitoring_stocks'][:5]:  # 처음 5개만
                    print(f"  - {stock['symbol']}({stock['name']}) 현재가: {stock['current_price']:,}")
        else:
            print("DB Auto Trader 없음")
            
    except Exception as e:
        print(f"상태 확인 실패: {e}")

if __name__ == "__main__":
    asyncio.run(check_monitoring_status())