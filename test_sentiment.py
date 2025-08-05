#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analyzers.sentiment_analyzer import SentimentAnalyzer
from config import Config

async def test():
    analyzer = SentimentAnalyzer(Config())
    result = await analyzer.analyze('005930', '삼성전자', [
        {'title': '삼성전자 실적 개선', 'description': '반도체 매출 증가'}
    ])
    print(f"감성분석 완료: {result.get('news_sentiment')}")
    print(f"점수: {result.get('overall_score')}")

if __name__ == "__main__":
    asyncio.run(test())