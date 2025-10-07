#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건검색 결과의 종목 타입 확인
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    # SuperTrend 조건식으로 테스트 (158개 중 100개 반환)
    print("\n" + "="*80)
    print("SuperTrend 조건식 결과 분석 (ETF/우선주 확인)")
    print("="*80 + "\n")
    
    result = await collector.get_stocks_by_condition("6", "SuperTrend")
    
    etf_count = 0
    preferred_count = 0
    normal_count = 0
    
    print(f"총 {len(result)}개 종목:\n")
    
    for stock in result[:30]:  # 상위 30개만 확인
        code = stock['code']
        name = stock['name']
        
        # ETF 판별 (종목코드가 특수문자 포함 또는 종목명에 ETF/KODEX/TIGER 등 포함)
        is_etf = (
            not code.isdigit() or  # 숫자가 아닌 코드
            'ETF' in name.upper() or
            'KODEX' in name.upper() or
            'TIGER' in name.upper() or
            'KINDEX' in name.upper() or
            'KOSEF' in name.upper() or
            'KBSTAR' in name.upper() or
            'ARIRANG' in name.upper() or
            'PLUS' in name.upper() or
            'SOL' in name.upper() or
            'RISE' in name.upper() or
            'KIWOOM' in name.upper() or
            'KoAct' in name
        )
        
        # 우선주 판별 (종목명에 '우' 포함 또는 종목코드 5번째 자리가 5 이상)
        is_preferred = (
            '우' in name or
            (len(code) == 6 and code.isdigit() and int(code[5]) >= 5)
        )
        
        if is_etf:
            etf_count += 1
            print(f"  [ETF] {code} {name}")
        elif is_preferred:
            preferred_count += 1
            print(f"  [우선주] {code} {name}")
        else:
            normal_count += 1
            print(f"  [일반] {code} {name}")
    
    print(f"\n{'='*80}")
    print(f"통계 (상위 30개 기준):")
    print(f"  ETF: {etf_count}개")
    print(f"  우선주: {preferred_count}개")
    print(f"  일반 종목: {normal_count}개")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
