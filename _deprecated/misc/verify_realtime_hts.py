#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 HTS 조건 검색 결과 비교
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

# 실시간 HTS 결과 (사용자 제공 - 휴장 시간 기준)
HTS_REALTIME = {
    '3분봉 스캘핑 전략': ('0', 7),
    'Breakout': ('1', 10),
    'EOD': ('2', 83),
    'momentum': ('3', None),  # 제공 안됨
    'RSI (상대강도지수) 전략': ('4', 6),
    'Squeeze Momentum Pro': ('5', 44),
    'SuperTrend': ('6', 158),
    'VWAP': ('7', None),  # 제공 안됨
}

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    print("\n" + "="*80)
    print("실시간 HTS 조건 검색 결과 비교 (휴장 시간 기준)")
    print("="*80 + "\n")
    
    for name, (cond_id, expected) in HTS_REALTIME.items():
        result = await collector.get_stocks_by_condition(cond_id, name)
        actual = len(result)
        
        if expected is None:
            print(f"ID {cond_id} | {name:30} | HTS: ???개 | API: {actual:3}개")
        else:
            match = "✅" if actual == expected else f"❌ (차이: {actual - expected:+d})"
            print(f"{match} ID {cond_id} | {name:30} | HTS: {expected:3}개 | API: {actual:3}개")
        
        await asyncio.sleep(0.3)

if __name__ == "__main__":
    asyncio.run(main())
