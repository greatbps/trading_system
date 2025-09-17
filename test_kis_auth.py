#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 인증 테스트 스크립트
"""

import asyncio
import aiohttp
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config
from utils.logger import get_logger

async def test_kis_auth():
    """KIS API 인증 테스트"""

    config = Config()
    logger = get_logger("KISAuthTest")

    # 설정 확인
    logger.info("=== KIS API 설정 확인 ===")
    logger.info(f"Base URL: {config.api.KIS_BASE_URL}")
    logger.info(f"App Key: {'*' * 8 if config.api.KIS_APP_KEY else 'NOT SET'}")
    logger.info(f"App Secret: {'*' * 8 if config.api.KIS_APP_SECRET else 'NOT SET'}")

    if not config.api.KIS_APP_KEY or not config.api.KIS_APP_SECRET:
        logger.error("KIS API 키가 설정되지 않았습니다.")
        return False

    # 토큰 요청 테스트
    logger.info("=== KIS API 토큰 요청 테스트 ===")

    # KIS API에서 지원하는 다양한 grant_type 테스트
    test_configs = [
        {
            "name": "KIS API Standard (POST)",
            "endpoint": "/oauth2/tokenP",
            "method": "json",
            "payload": {
                "grant_type": "client_credentials",
                "appkey": config.api.KIS_APP_KEY,
                "appsecret": config.api.KIS_APP_SECRET
            },
            "headers": {
                'Content-Type': 'application/json; charset=utf-8'
            }
        },
        {
            "name": "OAuth2 authorization_code",
            "endpoint": "/oauth2/token",
            "method": "json",
            "payload": {
                "grant_type": "authorization_code",
                "appkey": config.api.KIS_APP_KEY,
                "appsecret": config.api.KIS_APP_SECRET
            },
            "headers": {
                'Content-Type': 'application/json; charset=utf-8'
            }
        },
        {
            "name": "OAuth2 refresh_token",
            "endpoint": "/oauth2/token",
            "method": "json",
            "payload": {
                "grant_type": "refresh_token",
                "appkey": config.api.KIS_APP_KEY,
                "appsecret": config.api.KIS_APP_SECRET
            },
            "headers": {
                'Content-Type': 'application/json; charset=utf-8'
            }
        },
        {
            "name": "KIS Custom Grant Type",
            "endpoint": "/oauth2/token",
            "method": "json",
            "payload": {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "appkey": config.api.KIS_APP_KEY,
                "appsecret": config.api.KIS_APP_SECRET
            },
            "headers": {
                'Content-Type': 'application/json; charset=utf-8'
            }
        }
    ]

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:

            for test_config in test_configs:
                name = test_config["name"]
                endpoint = test_config["endpoint"]
                method = test_config["method"]
                payload = test_config["payload"]
                headers = test_config["headers"]

                url = f"{config.api.KIS_BASE_URL}{endpoint}"
                logger.info(f"테스트 설정: {name}")
                logger.info(f"요청 URL: {url}")
                logger.info(f"페이로드: {list(payload.keys())}")

                # 요청 방식에 따라 다르게 처리
                if method == "json":
                    async with session.post(url, json=payload, headers=headers) as response:
                        response_text = await response.text()
                elif method == "form":
                    async with session.post(url, data=payload, headers=headers) as response:
                        response_text = await response.text()
                else:
                    continue

                logger.info(f"응답 상태: {response.status}")
                logger.info(f"응답 헤더: {dict(response.headers)}")
                logger.info(f"응답 내용 (처음 500자): {response_text[:500]}")

                # HTML 에러 페이지 감지
                if response_text.strip().startswith('<'):
                    logger.warning(f"❌ {endpoint} ({method}): HTML 에러 페이지 반환")
                    continue

                if response.status == 200:
                    if not response_text.strip():
                        logger.warning(f"❌ {endpoint} ({method}): 빈 응답")
                        continue

                    try:
                        result = json.loads(response_text)

                        if 'access_token' in result:
                            logger.info(f"✅ 토큰 요청 성공! (엔드포인트: {endpoint}, 방식: {method})")
                            logger.info(f"토큰 타입: {result.get('token_type', 'Unknown')}")
                            logger.info(f"만료 시간: {result.get('expires_in', 'Unknown')} 초")
                            return True
                        else:
                            logger.warning(f"❌ {endpoint} ({method}): 응답에 access_token이 없습니다.")
                            logger.info(f"응답 구조: {list(result.keys()) if result else 'None'}")
                            continue

                    except json.JSONDecodeError as e:
                        logger.warning(f"❌ {endpoint} ({method}): JSON 파싱 실패: {str(e)}")
                        continue

                else:
                    logger.warning(f"❌ {endpoint} ({method}): HTTP 에러 {response.status}")
                    if response_text:
                        logger.info(f"에러 내용: {response_text[:200]}")
                    continue

            # 모든 테스트 설정 실패
            logger.error("❌ 모든 테스트 설정에서 토큰 요청 실패")
            return False

    except asyncio.TimeoutError:
        logger.error("❌ 요청 시간 초과")
        return False
    except Exception as e:
        logger.error(f"❌ 예외 발생: {str(e)}")
        import traceback
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        return False

async def main():
    """메인 함수"""
    logger = get_logger("KISAuthTest")

    logger.info("KIS API 인증 테스트 시작")

    success = await test_kis_auth()

    if success:
        logger.info("✅ 모든 테스트 성공!")
    else:
        logger.error("❌ 테스트 실패!")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)