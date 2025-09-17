#!/usr/bin/env python3
"""
Debug the token usage issue - examine exactly what's happening
"""

import asyncio
import aiohttp
from data_collectors.kis_collector import KISTokenManager
from utils.logger import setup_logger
from config.config import Config
import os

async def debug_token_issue():
    """Debug 토큰 사용 이슈 상세 분석"""
    logger = setup_logger("debug_token")

    logger.info("=== KIS 토큰 사용 이슈 디버깅 ===")

    # 설정 로드
    config = Config()

    logger.info("=== 환경변수 확인 ===")
    logger.info(f"KIS_APP_KEY: {config.kis.APP_KEY[:8] + '...' if config.kis.APP_KEY else 'None'}")
    logger.info(f"KIS_APP_SECRET: {config.kis.APP_SECRET[:8] + '...' if config.kis.APP_SECRET else 'None'}")
    logger.info(f"KIS_ACCOUNT_NUMBER: {config.api.KIS_ACCOUNT_NUMBER}")
    logger.info(f"KIS_BASE_URL: {config.kis.URL_BASE}")

    # TokenManager 초기화
    token_manager = KISTokenManager(
        app_key=config.kis.APP_KEY,
        app_secret=config.kis.APP_SECRET,
        base_url=config.kis.URL_BASE,
        logger=logger
    )

    async with aiohttp.ClientSession() as session:
        try:
            # 새 토큰 요청
            logger.info("\n=== 토큰 요청 테스트 ===")
            success = await token_manager.request_new_token(session)

            if success:
                logger.info(f"✅ 토큰 획득 성공")
                logger.info(f"토큰 길이: {len(token_manager.access_token)}")
                logger.info(f"토큰 형식: {token_manager.access_token[:8]}...{token_manager.access_token[-8:]}")
                logger.info(f"토큰 만료 시간: {token_manager.token_expired}")
                logger.info(f"토큰 유효성: {token_manager.is_token_valid()}")

                # 헤더 생성 테스트
                headers = token_manager.get_headers(tr_id="TTTC8434R")
                logger.info(f"\n=== 헤더 확인 ===")
                for key, value in headers.items():
                    if key == 'Authorization':
                        logger.info(f"{key}: {value[:20]}...")
                    elif key in ['appkey', 'appsecret']:
                        logger.info(f"{key}: {value[:8]}...")
                    else:
                        logger.info(f"{key}: {value}")

                # 간단한 API 테스트 - 시장지수 조회
                logger.info(f"\n=== 간단한 API 테스트 (시장지수) ===")
                test_url = f"{config.kis.URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-index-price"
                test_params = {
                    "FID_COND_MRKT_DIV_CODE": "U",
                    "FID_INPUT_ISCD": "0001"  # KOSPI
                }

                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(test_url, params=test_params, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()
                    logger.info(f"응답 상태: {response.status}")
                    logger.info(f"응답 내용 (처음 200자): {response_text[:200]}")

                    if response.status == 200:
                        logger.info("✅ 토큰이 정상적으로 작동합니다!")
                    else:
                        logger.error("❌ API 호출에서 오류 발생")

            else:
                logger.error("❌ 토큰 획득 실패")

        except Exception as e:
            logger.error(f"❌ 디버깅 중 오류: {e}")

if __name__ == "__main__":
    asyncio.run(debug_token_issue())