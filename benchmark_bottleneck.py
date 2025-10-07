#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전략 종목 추출 병목 지점 측정
"""

import asyncio
import time
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    
    print("\n" + "="*80)
    print("전략 종목 추출 성능 측정")
    print("="*80 + "\n")
    
    # 1. 초기화 시간
    start = time.time()
    await collector.initialize()
    init_time = time.time() - start
    print(f"1️⃣  초기화: {init_time:.2f}초")
    
    # 2. HTS 조건검색 API 호출 시간
    start = time.time()
    stocks_data = await collector.get_stocks_by_condition("6", "SuperTrend")
    api_time = time.time() - start
    print(f"2️⃣  HTS 조건검색 API: {api_time:.2f}초 (결과: {len(stocks_data)}개)")
    
    # 3. ETF/우선주 필터링 시간
    start = time.time()
    filtered = []
    for stock in stocks_data:
        symbol = stock.get('code')
        name = stock.get('name')
        if symbol and name:
            if not symbol.isdigit():
                continue
            if any(kw in name.upper() for kw in ['ETF', 'KODEX', 'TIGER', 'PLUS', 'SOL', 'RISE', 'KIWOOM', 'KOACT']):
                continue
            if '우' in name:
                continue
            if len(symbol) == 6 and int(symbol[5]) >= 5:
                continue
            filtered.append((symbol, name))
    filter_time = time.time() - start
    print(f"3️⃣  ETF/우선주 필터링: {filter_time:.3f}초 (결과: {len(filtered)}개)")
    
    # 4. 2차 필터링 시뮬레이션 (get_filtered_stocks 사용)
    start = time.time()
    result = await collector.get_filtered_stocks('supertrend_ema_rsi', limit=999)
    total_time = time.time() - start
    print(f"4️⃣  get_filtered_stocks 전체: {total_time:.2f}초 (결과: {len(result) if result else 0}개)")
    
    print(f"\n{'='*80}")
    print(f"병목 분석:")
    print(f"  - API 호출: {api_time:.2f}초 ({api_time/total_time*100:.1f}%)")
    print(f"  - 필터링: {filter_time:.3f}초 ({filter_time/total_time*100:.1f}%)")
    print(f"  - 기타(초기화 등): {total_time - api_time - filter_time:.2f}초")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
