#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 뉴스 검색 테스트
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector
from data_collectors.news_collector import NewsCollector
from data_collectors.news_search_wrapper import search_news_hybrid

async def main():
    config = Config()
    collector = KISCollector(config)
    news_collector = NewsCollector(config)
    
    await collector.initialize()
    
    # 테스트 종목 (뉴스가 없었던 종목들)
    test_stocks = [
        ("004890", "동일산업"),
        ("008500", "일정실업"),
        ("022100", "포스코DX"),
        ("005930", "삼성전자"),
    ]
    
    print("\n" + "="*80)
    print("개선된 뉴스 검색 테스트 (API 우선)")
    print("="*80 + "\n")
    
    for symbol, name in test_stocks:
        print(f"📰 {name} ({symbol}) 뉴스 검색...")
        news = await search_news_hybrid(news_collector, name, symbol)
        print(f"   결과: {len(news)}개")
        if news:
            for i, item in enumerate(news[:3], 1):
                print(f"   {i}. {item.get('title', 'N/A')[:50]}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
