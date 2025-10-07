#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 검색 병렬 처리 검증
"""

import asyncio
import time
from config import Config
from data_collectors.kis_collector import KISCollector
from data_collectors.news_collector import NewsCollector
from utils.parallel_analyzer import ParallelStockAnalyzer

async def main():
    config = Config()
    collector = KISCollector(config)
    news_collector = NewsCollector(config)
    
    await collector.initialize()
    
    # 테스트용 종목 (RSI 조건식에서 10개)
    stocks = await collector.get_filtered_stocks('rsi', limit=10)
    
    if not stocks:
        print("❌ 종목 조회 실패")
        return
    
    print("\n" + "="*80)
    print(f"뉴스 검색 병렬 처리 테스트 ({len(stocks)}개 종목)")
    print("="*80 + "\n")
    
    # 병렬 분석기 생성
    analyzer = ParallelStockAnalyzer(
        data_collector=collector,
        news_collector=news_collector,
        analysis_engine=None
    )
    
    print("🚀 병렬 뉴스 검색 시작...")
    start = time.time()
    
    # 병렬 실행
    tasks = [analyzer._fetch_news(symbol, name) for symbol, name in stocks]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    print(f"\n✅ 완료: {elapsed:.2f}초")
    print(f"평균: {elapsed/len(stocks):.2f}초/종목")
    print(f"\n뉴스 수집 결과:")
    for i, ((symbol, name), news) in enumerate(zip(stocks, results), 1):
        print(f"  {i}. {name}: {len(news)}개 뉴스")

if __name__ == "__main__":
    asyncio.run(main())
