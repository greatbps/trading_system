#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병렬 처리 성능 테스트
"""

import asyncio
import time
from config import Config
from data_collectors.kis_collector import KISCollector
from utils.parallel_analyzer import ParallelStockAnalyzer

async def test_sequential(collector, stocks):
    """순차 처리 (기존 방식)"""
    print("\n📊 순차 처리 테스트...")
    start = time.time()
    
    results = []
    for symbol, name in stocks:
        try:
            stock_info = await collector.get_stock_info(symbol)
            if stock_info:
                results.append(stock_info)
        except:
            pass
    
    elapsed = time.time() - start
    print(f"  ⏱️  순차 처리: {elapsed:.2f}초 ({len(results)}개 성공)")
    return elapsed

async def test_parallel(collector, stocks):
    """병렬 처리 (새 방식)"""
    print("\n⚡ 병렬 처리 테스트...")
    start = time.time()
    
    analyzer = ParallelStockAnalyzer(
        data_collector=collector,
        news_collector=None,
        analysis_engine=None
    )
    
    results = await analyzer.analyze_stocks_batch(stocks, strategy='test', max_concurrent=10)
    
    elapsed = time.time() - start
    print(f"  ⏱️  병렬 처리: {elapsed:.2f}초 ({len(results)}개 성공)")
    return elapsed

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    # SuperTrend 조건식에서 종목 추출
    print("\n" + "="*80)
    print("병렬 처리 성능 비교 테스트")
    print("="*80)
    
    stock_list = await collector.get_filtered_stocks('supertrend_ema_rsi', limit=20)
    
    if not stock_list:
        print("❌ 종목 조회 실패")
        return
    
    print(f"\n테스트 대상: {len(stock_list)}개 종목")
    
    # 순차 처리 테스트
    seq_time = await test_sequential(collector, stock_list)
    
    # 병렬 처리 테스트
    par_time = await test_parallel(collector, stock_list)
    
    # 결과 비교
    print("\n" + "="*80)
    print("📊 성능 비교 결과")
    print("="*80)
    print(f"  순차 처리: {seq_time:.2f}초")
    print(f"  병렬 처리: {par_time:.2f}초")
    print(f"  성능 향상: {seq_time/par_time:.1f}배 빠름")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
