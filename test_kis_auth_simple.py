#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 KIS API 인증 테스트
"""

import asyncio
import aiohttp
import json
import logging
from pathlib import Path
import sys
import os

# 프로젝트 루트 디렉터리를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def test_kis_auth():
    """KIS API 인증 단순 테스트"""
    try:
        logger.info("🔑 KIS API 인증 단순 테스트 시작")

        # 설정 로드
        config = Config()
        app_key = getattr(config.api, 'KIS_APP_KEY', None)
        app_secret = getattr(config.api, 'KIS_APP_SECRET', None)
        base_url = getattr(config.api, 'KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')

        if not app_key or not app_secret:
            raise ValueError("KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다")

        logger.info(f"App Key: {app_key[:8]}...")
        logger.info(f"Base URL: {base_url}")

        async with aiohttp.ClientSession() as session:
            # 1. 토큰 발급 테스트
            logger.info("🔑 토큰 발급 테스트")
            token_url = f"{base_url}/oauth2/Approval"
            token_payload = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "secretkey": app_secret
            }
            token_headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json'
            }

            async with session.post(token_url, json=token_payload, headers=token_headers) as response:
                response_text = await response.text()
                logger.info(f"토큰 응답 상태: {response.status}")
                logger.info(f"토큰 응답 내용: {response_text}")

                if response.status == 200:
                    token_data = json.loads(response_text)
                    access_token = token_data.get('approval_key')
                    if access_token:
                        logger.info(f"✅ 토큰 발급 성공: {access_token[:8]}...")
                    else:
                        logger.error("❌ approval_key를 찾을 수 없습니다")
                        return False
                else:
                    logger.error(f"❌ 토큰 발급 실패: {response_text}")
                    return False

            # 2. API 호출 테스트 - 여러 헤더 형식 시도
            logger.info("📊 API 호출 테스트")
            api_url = f"{base_url}/uapi/domestic-stock/v1/quotations/chk-holiday"
            params = {
                "BASS_DT": "20250916",
                "CTX_AREA_NK": "",
                "CTX_AREA_FK": ""
            }

            # 헤더 형식 1: Bearer 토큰
            headers_v1 = {
                'Authorization': f'Bearer {access_token}',
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'CTCA0903R',
                'custtype': 'P',
                'Content-Type': 'application/json; charset=utf-8'
            }

            logger.info("테스트 1: Bearer 토큰 형식")
            async with session.get(api_url, params=params, headers=headers_v1) as response:
                response_text = await response.text()
                logger.info(f"응답 상태: {response.status}")
                logger.info(f"응답 내용: {response_text[:500]}")

            # 헤더 형식 2: approval_key 헤더 직접 사용
            headers_v2 = {
                'approval_key': access_token,
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'CTCA0903R',
                'custtype': 'P',
                'Content-Type': 'application/json; charset=utf-8'
            }

            logger.info("테스트 2: approval_key 헤더 직접 사용")
            async with session.get(api_url, params=params, headers=headers_v2) as response:
                response_text = await response.text()
                logger.info(f"응답 상태: {response.status}")
                logger.info(f"응답 내용: {response_text[:500]}")

            # 헤더 형식 3: token 헤더
            headers_v3 = {
                'token': access_token,
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'CTCA0903R',
                'custtype': 'P',
                'Content-Type': 'application/json; charset=utf-8'
            }

            logger.info("테스트 3: token 헤더 사용")
            async with session.get(api_url, params=params, headers=headers_v3) as response:
                response_text = await response.text()
                logger.info(f"응답 상태: {response.status}")
                logger.info(f"응답 내용: {response_text[:500]}")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    asyncio.run(test_kis_auth())