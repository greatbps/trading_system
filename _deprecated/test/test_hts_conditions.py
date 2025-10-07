#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건검색식 목록 조회 테스트
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

logger = get_logger("HTSTest")

async def main():
    """HTS 조건검색식 목록 조회"""
    try:
        config = Config()
        collector = KISCollector(config)

        logger.info("🔍 KIS Collector 초기화 중...")
        await collector.initialize()

        logger.info("📋 HTS 조건검색식 목록 조회 중...")
        conditions = await collector.get_hts_condition_list()

        if conditions:
            logger.info(f"✅ 조건검색식 {len(conditions)}개 발견:")
            for idx, cond in enumerate(conditions):
                logger.info(f"  [{idx}] 원본 데이터: {cond}")
                logger.info(f"  - ID: {cond.get('condition_id', 'N/A'):>5} | 이름: {cond.get('condition_name', 'N/A')}")
        else:
            logger.warning("⚠️ 조건검색식이 없거나 조회 실패")

        await collector.cleanup()

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
