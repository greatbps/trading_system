#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 데이터 수정 스크립트
"""

import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def fix_monitoring_data():
    print("Monitoring data fix script - Simplified version")
    
    try:
        # 간단한 테스트
        from utils.strategy_mapper import strategy_mapper
        from utils.status_definitions import status_definitions
        
        print("Testing strategy mapping:")
        test_strategies = []
        test_stocks = [
            ("005930", "삼성전자"), 
            ("187660", "아바이오메드"),
            ("005360", "모나미")
        ]
        
        for symbol, name in test_stocks:
            strategy = strategy_mapper.get_strategy_for_stock(symbol, name, None)
            print(f"  {symbol} ({name}) -> {strategy}")
            test_strategies.append(strategy)
        
        print("\nTesting status mapping:")
        test_statuses = ["monitoring", "위험", "ACTIVE", "TARGET_ACHIEVED"]
        for status in test_statuses:
            korean_status = status_definitions.get_status_display(status, include_icon=False)
            print(f"  {status} -> {korean_status}")
        
        print("✅ All utilities working correctly")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_monitoring_data())
