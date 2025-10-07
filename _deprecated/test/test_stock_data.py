#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종목 데이터 수집 테스트
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    # 문제 종목 테스트
    symbol = "253590"
    
    print(f"\n{'='*80}")
    print(f"종목 {symbol} 데이터 수집 테스트")
    print(f"{'='*80}\n")
    
    # 1. 종목 정보 조회
    print("1️⃣ 종목 정보 조회...")
    try:
        stock_info = await collector.get_stock_info(symbol)
        if stock_info:
            print(f"✅ 성공: {stock_info}")
        else:
            print(f"❌ 실패: None 반환")
    except Exception as e:
        print(f"❌ 에러: {e}")
    
    # 2. 차트 데이터 조회
    print("\n2️⃣ 차트 데이터 조회...")
    try:
        chart_data = await collector.get_ohlcv_data(symbol, period='D', count=30)
        if chart_data:
            print(f"✅ 성공: {len(chart_data)}개 데이터")
        else:
            print(f"❌ 실패: None 반환")
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    asyncio.run(main())
