#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건검색 수정 - user_id를 조건식 목록에서 가져온 것으로 사용
"""

import asyncio
import json
from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

logger = get_logger("ConditionSearchFix")

async def main():
    """조건식 목록에서 실제 user_id를 가져와 검색"""
    try:
        config = Config()
        collector = KISCollector(config)

        logger.info("🔍 KIS Collector 초기화 중...")
        await collector.initialize()

        # 1단계: 조건식 목록 조회하여 실제 user_id 확인
        logger.info("\n📋 1단계: HTS 조건식 목록 조회")
        conditions = await collector.get_hts_condition_list()

        if not conditions:
            logger.error("❌ 조건식 목록 조회 실패")
            return

        # Breakout 조건식 찾기
        breakout_condition = None
        for cond in conditions:
            if cond.get('name') == 'Breakout' or cond.get('id') == '1':
                breakout_condition = cond
                break

        if not breakout_condition:
            logger.error("❌ Breakout 조건식을 찾을 수 없습니다")
            return

        logger.info(f"✅ Breakout 조건식 발견:")
        logger.info(f"   - ID: {breakout_condition.get('id')}")
        logger.info(f"   - 이름: {breakout_condition.get('name')}")
        logger.info(f"   - user_id: {breakout_condition.get('user_id')}")

        # 2단계: 실제 user_id로 조건검색 실행
        actual_user_id = breakout_condition.get('user_id')
        condition_id = breakout_condition.get('id')

        logger.info(f"\n📊 2단계: 조건식 {condition_id} 검색 (user_id={actual_user_id})")

        result = await collector._make_api_request_with_pagination(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/psearch-result",
            params={
                "user_id": actual_user_id,  # 조건식 목록에서 가져온 실제 user_id
                "seq": condition_id
            },
            tr_id="HHKST03900400",
            custtype="P"
        )

        logger.info(f"\n📋 API 응답:")
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

        # output2에서 종목 추출
        output2 = result.get('output2', [])
        if output2 and len(output2) > 0:
            logger.info(f"\n✅ {len(output2)}개 종목 발견!")
            logger.info(f"\n📋 추출된 종목 목록:")
            for idx, stock in enumerate(output2[:7], 1):  # 7개만 표시
                code = stock.get('code', stock.get('mksc_shrn_iscd', 'N/A'))
                name = stock.get('name', stock.get('hts_kor_isnm', 'N/A'))
                logger.info(f"   {idx}. {code} - {name}")
        else:
            logger.warning(f"⚠️ 종목이 없습니다")
            logger.info(f"   msg_cd: {result.get('msg_cd')}")
            logger.info(f"   msg1: {result.get('msg1')}")

        await collector.cleanup()

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
