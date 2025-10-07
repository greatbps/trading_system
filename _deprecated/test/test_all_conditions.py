#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 HTS 조건식 테스트 - 어떤 조건식이 종목을 반환하는지 확인
"""

import asyncio
import logging
from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

logger = get_logger("AllConditionsTest")

async def main():
    """모든 조건식 테스트"""
    try:
        config = Config()
        collector = KISCollector(config)

        logger.info("🔍 KIS Collector 초기화 중...")
        await collector.initialize()

        # 모든 조건식 테스트
        conditions = [
            ("0", "3분봉 스캘핑 전략"),
            ("1", "Breakout"),
            ("2", "EOD"),
            ("3", "momentum"),
            ("4", "RSI (상대강도지수) 전략"),
            ("5", "Squeeze Momentum Pro"),
            ("6", "SuperTrend"),
            ("7", "VWAP"),
        ]

        results = {}

        for condition_id, condition_name in conditions:
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 조건식 {condition_id} ({condition_name}) 테스트 중...")
            logger.info(f"{'='*60}")

            try:
                stocks = await collector.get_stocks_by_condition(condition_id, condition_name)

                if stocks and len(stocks) > 0:
                    logger.info(f"✅ {len(stocks)}개 종목 발견!")
                    results[condition_name] = len(stocks)

                    # 처음 5개만 출력
                    logger.info(f"📋 처음 5개 종목:")
                    for stock in stocks[:5]:
                        code = stock.get('code', 'N/A')
                        name = stock.get('name', 'N/A')
                        logger.info(f"  - {code}: {name}")
                else:
                    logger.warning(f"⚠️ 조건식 {condition_id}에 해당하는 종목 없음")
                    results[condition_name] = 0

            except Exception as e:
                logger.error(f"❌ 조건식 {condition_id} 검색 실패: {e}")
                results[condition_name] = -1

            # API 호출 제한 방지
            await asyncio.sleep(0.5)

        # 결과 요약
        logger.info(f"\n{'='*60}")
        logger.info("📊 전체 조건식 테스트 결과 요약")
        logger.info(f"{'='*60}")

        for condition_name, count in results.items():
            if count > 0:
                logger.info(f"✅ {condition_name}: {count}개 종목")
            elif count == 0:
                logger.warning(f"⚠️ {condition_name}: 종목 없음")
            else:
                logger.error(f"❌ {condition_name}: 검색 실패")

        await collector.cleanup()

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
