#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 검색 래퍼 - 네이버 API 우선, 크롤링 폴백
"""

import asyncio
from typing import List, Dict
from utils.logger import get_logger

logger = get_logger("NewsSearchWrapper")

async def search_news_hybrid(news_collector, stock_name: str, stock_code: str) -> List[Dict]:
    """
    하이브리드 뉴스 검색:
    1. 네이버 API 시도 (빠르고 안정적)
    2. 실패 시 크롤링 폴백
    """
    news_items = []
    
    # 1. 네이버 API 우선 시도
    try:
        if hasattr(news_collector, 'search_naver_news_api'):
            api_news = await news_collector.search_naver_news_api(stock_name, display=10)
            if api_news and len(api_news) > 0:
                logger.debug(f"{stock_name} 네이버 API에서 {len(api_news)}개 뉴스 발견")
                return api_news  # API 성공 시 바로 반환
    except Exception as e:
        logger.debug(f"{stock_name} 네이버 API 실패: {e}")
    
    # 2. 크롤링 폴백 (동기 함수를 비동기로 실행)
    try:
        loop = asyncio.get_event_loop()
        crawl_news = await loop.run_in_executor(
            None,
            news_collector.search_stock_news_naver,
            stock_name,
            stock_code
        )
        if crawl_news and len(crawl_news) > 0:
            logger.debug(f"{stock_name} 크롤링에서 {len(crawl_news)}개 뉴스 발견")
            return crawl_news
    except Exception as e:
        logger.debug(f"{stock_name} 크롤링 실패: {e}")
    
    # 3. 둘 다 실패
    logger.info(f"   ⚠️ {stock_name} 뉴스를 찾을 수 없습니다 (API/크롤링 모두 실패)")
    return []
