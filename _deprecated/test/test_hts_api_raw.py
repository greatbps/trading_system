#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건검색 API 원본 응답 확인
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector
import json

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    # 조건식 0번 (3분봉 스캘핑) - HTS 결과: 0개
    print("\n" + "="*80)
    print("조건식 0번 (3분봉 스캘핑 전략) 테스트 - HTS 예상: 0개")
    print("="*80)
    
    result = await collector.get_stocks_by_condition("0", "3분봉 스캘핑 전략")
    print(f"\nAPI 반환 결과 개수: {len(result)}개")
    if result:
        print(f"상위 3개 종목: {result[:3]}")
    
    # 조건식 1번 (Breakout) - HTS 결과: 3개
    print("\n" + "="*80)
    print("조건식 1번 (Breakout) 테스트 - HTS 예상: 3개")
    print("="*80)
    
    result = await collector.get_stocks_by_condition("1", "Breakout")
    print(f"\nAPI 반환 결과 개수: {len(result)}개")
    if result:
        print(f"상위 3개 종목: {result[:3]}")
    
    # 조건식 7번 (momentum) - HTS 결과: 7개
    print("\n" + "="*80)
    print("조건식 7번 (momentum) 테스트 - HTS 예상: 7개")
    print("="*80)
    
    result = await collector.get_stocks_by_condition("7", "momentum")
    print(f"\nAPI 반환 결과 개수: {len(result)}개")
    if result:
        print(f"상위 3개 종목: {result[:3]}")

if __name__ == "__main__":
    asyncio.run(main())
