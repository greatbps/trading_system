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

async def test_table_display():
    """테이블 표시 테스트"""
    try:
        print("=== 테이블 표시 테스트 ===")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return
        
        # DB Auto Trading Handler에서 테이블 테스트  
        db_handler = trading_system.auto_trading_handler
        if db_handler:
            print("\n=== 감시 종목 테이블 테스트 ===")
            try:
                monitoring_table = await db_handler._get_monitoring_stocks_table()
                print("✅ 감시 종목 테이블 생성 성공")
                print(f"테이블 타입: {type(monitoring_table)}")
            except Exception as e:
                print(f"❌ 감시 종목 테이블 생성 실패: {e}")
                
            print("\n=== 보유 종목 테이블 테스트 ===")  
            try:
                holdings_table = await db_handler._get_holdings_table()
                print("✅ 보유 종목 테이블 생성 성공")
                print(f"테이블 타입: {type(holdings_table)}")
            except Exception as e:
                print(f"❌ 보유 종목 테이블 생성 실패: {e}")
                
            print("\n=== KIS API 종목명 조회 테스트 ===")
            kis_collector = trading_system.kis_collector
            if kis_collector:
                test_symbols = ["005930", "000660", "035420"]  # 삼성전자, SK하이닉스, NAVER
                for symbol in test_symbols:
                    try:
                        stock_data = await asyncio.wait_for(
                            kis_collector.get_stock_info(symbol), timeout=5.0
                        )
                        if stock_data and hasattr(stock_data, 'name'):
                            print(f"✅ {symbol}: {stock_data.name}")
                        else:
                            print(f"❌ {symbol}: 종목명 없음")
                    except Exception as e:
                        print(f"❌ {symbol}: {e}")
        else:
            print("DB Auto Trading Handler 없음")
            
    except Exception as e:
        print(f"테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_table_display())