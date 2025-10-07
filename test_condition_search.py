#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건검색 테스트
"""

import asyncio
import logging
from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

# 디버그 로깅 활성화
logging.getLogger("KISCollector").setLevel(logging.DEBUG)

logger = get_logger("ConditionSearchTest")

async def main():
    """momentum 조건식으로 종목 검색 테스트"""
    try:
        config = Config()
        collector = KISCollector(config)

        logger.info("🔍 KIS Collector 초기화 중...")
        await collector.initialize()

        # momentum 조건식 ID = 3
        condition_id = "3"
        condition_name = "momentum"

        logger.info(f"📊 조건식 {condition_id} ({condition_name}) 종목 검색 중...")
        stocks = await collector.get_stocks_by_condition(condition_id, condition_name)

        if stocks:
            logger.info(f"✅ {len(stocks)}개 종목 발견:")
            for stock in stocks[:10]:  # 처음 10개만 출력
                logger.info(f"  - {stock.get('code', 'N/A')}: {stock.get('name', 'N/A')}")
        else:
            logger.warning("⚠️ 조건에 맞는 종목이 없거나 검색 실패")

        await collector.cleanup()

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
