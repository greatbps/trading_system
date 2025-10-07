#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건식별 실제 API 결과 비교
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    # 실제 HTS 조건식 순서대로 테스트
    test_cases = [
        ("0", "3분봉 스캘핑 전략", 0),
        ("1", "Breakout", 3),
        ("2", "EOD", 22),
        ("3", "momentum", 7),
        ("4", "RSI (상대강도지수) 전략", 1),
        ("5", "Squeeze Momentum Pro", 4),
        ("6", "SuperTrend", 54),
        ("7", "VWAP", 147),
    ]
    
    print("\n" + "="*80)
    print("HTS 조건식 ID별 API 조회 결과")
    print("="*80 + "\n")
    
    for cond_id, cond_name, expected in test_cases:
        result = await collector.get_stocks_by_condition(cond_id, cond_name)
        actual = len(result)
        
        status = "✅" if actual == expected else "❌"
        print(f"{status} ID {cond_id} | {cond_name:30} | HTS: {expected:3}개 | API: {actual:3}개")
        
        if result and actual != expected:
            stocks_str = [f"{s['code']} {s['name']}" for s in result[:3]]
            print(f"    첫 3개 종목: {stocks_str}")
        
        await asyncio.sleep(0.3)

if __name__ == "__main__":
    asyncio.run(main())
