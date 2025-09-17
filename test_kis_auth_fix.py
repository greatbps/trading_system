#!/usr/bin/env python3
"""
KIS Authentication Fix Test
테스트: 수정된 인증 플로우 검증
"""

import asyncio
import aiohttp
from data_collectors.kis_collector import KISTokenManager
from utils.logger import setup_logger
import json

async def test_authentication_fix():
    """인증 플로우 수정 사항 테스트"""
    logger = setup_logger("test_auth_fix")

    logger.info("=== KIS 인증 플로우 수정 테스트 시작 ===")

    # 설정 로드
    try:
        import sys
        sys.path.append('.')
        from config.config import Config
        config = Config()
    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {e}")
        return False

    # 필수 설정 확인
    if not config.kis.APP_KEY or not config.kis.APP_SECRET:
        logger.error("KIS API 키 설정이 없습니다. 환경변수를 확인하세요.")
        return False

    # TokenManager 초기화
    token_manager = KISTokenManager(
        app_key=config.kis.APP_KEY,
        app_secret=config.kis.APP_SECRET,
        base_url=config.kis.URL_BASE,
        logger=logger
    )

    # 토큰 유효성 확인 (초기 상태)
    logger.info(f"초기 토큰 유효성: {token_manager.is_token_valid()}")
    logger.info(f"현재 토큰: {token_manager.access_token[:10] + '...' if token_manager.access_token else 'None'}")
    logger.info(f"토큰 만료 시간: {token_manager.token_expired}")

    # HTTP 세션 생성 및 토큰 요청
    async with aiohttp.ClientSession() as session:
        try:
            # 새 토큰 요청
            logger.info("\n--- 새 토큰 요청 테스트 ---")
            success = await token_manager.request_new_token(session)

            if success:
                logger.info("✅ 토큰 요청 성공!")
                logger.info(f"새 토큰 유효성: {token_manager.is_token_valid()}")
                logger.info(f"새 토큰: {token_manager.access_token[:10] + '...' if token_manager.access_token else 'None'}")
                logger.info(f"토큰 만료 시간: {token_manager.token_expired}")

                # 헤더 생성 테스트
                try:
                    headers = token_manager.get_headers(tr_id="TTTC8434R")
                    logger.info("✅ 헤더 생성 성공!")
                    logger.info(f"Authorization 헤더: Bearer {headers['Authorization'][7:17]}...")

                    return True
                except Exception as e:
                    logger.error(f"❌ 헤더 생성 실패: {e}")
                    return False
            else:
                logger.error("❌ 토큰 요청 실패!")
                return False

        except Exception as e:
            logger.error(f"❌ 테스트 중 예외 발생: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_authentication_fix())