#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
토큰 강제 갱신 테스트
"""

import asyncio
import logging
from pathlib import Path
import sys
import os

# 프로젝트 루트 디렉터리를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data_collectors.kis_collector import KISCollector
from config.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_token_refresh.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

async def test_token_refresh():
    """토큰 강제 갱신 테스트"""
    try:
        logger.info("🚀 토큰 강제 갱신 테스트 시작")

        # 설정 로드
        config = Config()
        logger.info("✅ 설정 로드 완료")

        # KIS Collector 초기화
        async with KISCollector(config) as collector:
            logger.info("✅ KIS Collector 초기화 완료")

            # 기존 토큰 상태 확인
            logger.info(f"현재 토큰: {collector.token_manager.access_token[:8] if collector.token_manager.access_token else 'None'}...")
            logger.info(f"토큰 만료: {collector.token_manager.token_expired}")

            # 토큰 강제 갱신
            logger.info("🔄 토큰 강제 갱신 중...")
            session = await collector.http_session.get_session()
            success = await collector.token_manager.ensure_valid_token(session, force_refresh=True)

            if success:
                logger.info("✅ 토큰 갱신 성공")
                logger.info(f"새 토큰: {collector.token_manager.access_token[:8]}...")
                logger.info(f"토큰 만료: {collector.token_manager.token_expired}")

                # 간단한 API 호출 테스트
                logger.info("📊 API 호출 테스트 중...")
                try:
                    balance = await collector.get_orderable_cash()
                    logger.info(f"✅ API 호출 성공 - 매수가능금액: {balance:,}원")
                except Exception as e:
                    logger.error(f"❌ API 호출 실패: {e}")
            else:
                logger.error("❌ 토큰 갱신 실패")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_token_refresh())