#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최종 검증: 모든 조건식 ETF/우선주 필터링 확인
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    strategies = [
        ('scalping_3m', '3분봉 스캘핑 전략'),
        ('breakout', 'Breakout'),
        ('eod', 'EOD'),
        ('momentum', 'momentum'),
        ('rsi', 'RSI'),
        ('squeeze_momentum_pro', 'Squeeze Momentum Pro'),
        ('supertrend_ema_rsi', 'SuperTrend'),
        ('vwap', 'VWAP'),
    ]
    
    print("\n" + "="*80)
    print("최종 검증: 모든 조건식 ETF/우선주 필터링 확인")
    print("="*80 + "\n")
    
    for strategy, name in strategies:
        result = await collector.get_filtered_stocks(strategy, limit=999)
        
        if result:
            # ETF/우선주 체크
            has_etf = any(
                not code.isdigit() or 
                any(kw in stock_name.upper() for kw in ['ETF', 'KODEX', 'TIGER', 'PLUS', 'SOL', 'RISE', 'KIWOOM', 'KOACT'])
                for code, stock_name in result
            )
            has_preferred = any('우' in stock_name for code, stock_name in result)
            
            status = "✅" if not has_etf and not has_preferred else "❌"
            print(f"{status} {name:30} | 결과: {len(result):3}개 | ETF: {'있음' if has_etf else '없음':4} | 우선주: {'있음' if has_preferred else '없음':4}")
        else:
            print(f"⚠️  {name:30} | 조회 실패")
        
        await asyncio.sleep(0.3)

if __name__ == "__main__":
    asyncio.run(main())
