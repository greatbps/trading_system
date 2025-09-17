#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 손익 계산 테스트
"""

import sys
from pathlib import Path
import asyncio

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from data_collectors.kis_collector import KISCollector
from trading.profit_calculator import ProfitCalculator
from config import Config

async def simple_test():
    """간단한 손익 계산 테스트"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        
        await kis_collector.initialize()
        calculator = ProfitCalculator(config, db_manager, kis_collector)
        
        print("손익 계산 시스템 테스트")
        print("-" * 40)
        
        # 보유종목 손익 업데이트 테스트
        result = await calculator.update_all_holdings_profit_loss()
        
        print("손익 업데이트 결과:")
        print(f"  성공: {result.get('success', False)}")
        print(f"  업데이트된 종목: {result.get('updated_count', 0)}개")
        print(f"  실패한 종목: {result.get('failed_count', 0)}개")
        print(f"  전체 대상: {result.get('total_count', 0)}개")
        
        print("\n손익 계산 테스트 완료")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_test())