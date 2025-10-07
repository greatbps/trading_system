#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건검색 API 상세 디버깅 - 실제 응답 확인
"""

import asyncio
import json
from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

logger = get_logger("ConditionAPIDebug")

async def main():
    """조건식 1번 API 응답 상세 확인"""
    try:
        config = Config()
        collector = KISCollector(config)

        logger.info("🔍 KIS Collector 초기화 중...")
        await collector.initialize()

        # 조건식 1번 테스트
        condition_id = "1"
        condition_name = "Breakout"

        logger.info(f"\n{'='*60}")
        logger.info(f"📊 조건식 {condition_id} ({condition_name}) API 응답 상세 분석")
        logger.info(f"{'='*60}\n")

        # API 직접 호출하여 전체 응답 확인
        result = await collector._make_api_request_with_pagination(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/psearch-result",
            params={
                "user_id": config.kis_account.KIS_USER_ID,
                "seq": condition_id
            },
            tr_id="HHKST03900400",
            custtype="P"
        )

        logger.info("📋 전체 API 응답:")
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

        logger.info(f"\n📋 응답 키 목록: {list(result.keys())}")
        logger.info(f"📋 rt_cd: {result.get('rt_cd')}")
        logger.info(f"📋 msg_cd: {result.get('msg_cd')}")
        logger.info(f"📋 msg1: {result.get('msg1')}")

        if 'output1' in result:
            logger.info(f"\n📋 output1 내용:")
            logger.info(json.dumps(result.get('output1'), indent=2, ensure_ascii=False))

        if 'output2' in result:
            output2 = result.get('output2', [])
            logger.info(f"\n📋 output2 종목 수: {len(output2)}")
            if output2:
                logger.info(f"📋 첫 번째 종목 샘플:")
                logger.info(json.dumps(output2[0], indent=2, ensure_ascii=False))

        await collector.cleanup()

    except Exception as e:
        logger.error(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
