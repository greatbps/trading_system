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

async def test_kis_api():
    """KIS API 종목명 조회 테스트"""
    try:
        print("=== KIS API Stock Name Test ===")
        
        from data_collectors.kis_collector import KISCollector
        from config import Config
        
        # Config 및 KIS Collector 초기화
        config = Config()
        kis_collector = KISCollector(config)
        await kis_collector.initialize()
        
        # 테스트 종목들
        test_symbols = ["005930", "000660", "035420", "207940", "068270"]
        print(f"Testing {len(test_symbols)} symbols...")
        
        for symbol in test_symbols:
            try:
                print(f"\nTesting {symbol}...")
                stock_data = await asyncio.wait_for(
                    kis_collector.get_stock_info(symbol), timeout=5.0
                )
                
                if stock_data:
                    print(f"  Symbol: {symbol}")
                    print(f"  Name: {stock_data.name if hasattr(stock_data, 'name') else 'NO_NAME'}")
                    print(f"  Price: {stock_data.current_price if hasattr(stock_data, 'current_price') else 'NO_PRICE'}")
                    print(f"  Type: {type(stock_data)}")
                else:
                    print(f"  No data returned for {symbol}")
                    
            except Exception as e:
                print(f"  ERROR {symbol}: {e}")
                
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_kis_api())