#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF/우선주 필터링 적용 후 검증
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    print("\n" + "="*80)
    print("ETF/우선주 필터링 적용 후 검증")
    print("="*80 + "\n")
    
    # SuperTrend 조건식 테스트 (가장 많은 ETF 포함)
    result = await collector.get_filtered_stocks('supertrend_ema_rsi', limit=999)
    
    if result:
        print(f"✅ SuperTrend 필터링 결과: {len(result)}개 종목\n")
        print("상위 20개 종목:")
        for i, (code, name) in enumerate(result[:20], 1):
            print(f"  {i:2}. {code} {name}")
        
        # ETF/우선주 섞여있는지 재확인
        has_etf = any(
            not code.isdigit() or 
            any(kw in name.upper() for kw in ['ETF', 'KODEX', 'TIGER', 'PLUS', 'SOL', 'RISE', 'KIWOOM', 'KOACT'])
            for code, name in result
        )
        has_preferred = any('우' in name for code, name in result)
        
        print(f"\n검증:")
        print(f"  ETF 포함 여부: {'❌ 있음' if has_etf else '✅ 없음'}")
        print(f"  우선주 포함 여부: {'❌ 있음' if has_preferred else '✅ 없음'}")
    else:
        print("❌ 조회 실패")

if __name__ == "__main__":
    asyncio.run(main())
