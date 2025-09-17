#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 토큰 수정 사항 테스트 스크립트
"""

import asyncio
import sys
from datetime import datetime
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append('.')

from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

async def test_kis_token_fix():
    """KIS API 토큰 수정 사항 테스트"""
    logger = get_logger("TokenFixTest")

    try:
        logger.info("🧪 KIS API 토큰 수정 사항 테스트 시작")

        # 설정 로드
        config = Config()

        # KIS Collector 초기화
        kis_collector = KISCollector(config)
        await kis_collector.initialize()

        logger.info("✅ KIS Collector 초기화 완료")

        # 현재 토큰 상태 확인
        token_manager = kis_collector.token_manager
        logger.info(f"토큰 상태: {token_manager.access_token[:10] if token_manager.access_token else 'None'}...")
        logger.info(f"토큰 만료: {token_manager.token_expired}")

        # 헤더 생성 테스트
        headers = token_manager.get_headers(tr_id="CTCA0903R")
        logger.info("🔍 생성된 헤더:")
        for key, value in headers.items():
            if key == 'authorization':
                logger.info(f"  {key}: {value[:10]}..." if value else f"  {key}: None")
            else:
                logger.info(f"  {key}: {value}")

        # API 호출 테스트 (오늘 날짜로 휴장일 조회)
        today = datetime.now().strftime('%Y%m%d')
        logger.info(f"📅 {today} 휴장일 정보 조회 테스트")

        result = await kis_collector._make_api_request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/chk-holiday",
            params={
                "BASS_DT": today,
                "CTX_AREA_NK": "",
                "CTX_AREA_FK": ""
            },
            tr_id="CTCA0903R"
        )

        if result.get('rt_cd') == '0':
            logger.info("✅ API 호출 성공!")
            output = result.get('output', [])
            if output:
                today_data = None
                for item in output:
                    if item.get('bass_dt') == today:
                        today_data = item
                        break

                if today_data:
                    logger.info(f"📊 {today} 시장 정보:")
                    logger.info(f"  개장일 여부: {'개장' if today_data.get('opnd_yn') == 'Y' else '휴장'}")
                    logger.info(f"  영업일 여부: {'영업일' if today_data.get('bzdy_yn') == 'Y' else '비영업일'}")
                    logger.info(f"  거래일 여부: {'거래일' if today_data.get('tr_day_yn') == 'Y' else '비거래일'}")
                else:
                    logger.warning(f"⚠️ {today} 데이터를 찾을 수 없습니다")
            else:
                logger.warning("⚠️ API 응답에 output 데이터가 없습니다")
        else:
            logger.error(f"❌ API 호출 실패: {result.get('msg1', 'Unknown error')}")
            return False

        logger.info("🎉 토큰 수정 사항 테스트 완료!")
        return True

    except Exception as e:
        logger.error(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return False

    finally:
        # 정리
        if 'kis_collector' in locals():
            await kis_collector.cleanup()

if __name__ == "__main__":
    result = asyncio.run(test_kis_token_fix())
    sys.exit(0 if result else 1)