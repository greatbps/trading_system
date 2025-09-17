#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
토큰 응답 구조 및 유효성 확인
"""

import asyncio
import aiohttp
import json
import logging
from pathlib import Path
import sys

# 프로젝트 루트 디렉터리를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def analyze_token_response():
    """토큰 응답 구조 분석"""
    try:
        logger.info("🔍 토큰 응답 구조 분석 시작")

        # 설정 로드
        config = Config()
        app_key = getattr(config.api, 'KIS_APP_KEY', None)
        app_secret = getattr(config.api, 'KIS_APP_SECRET', None)
        base_url = getattr(config.api, 'KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')

        if not app_key or not app_secret:
            raise ValueError("KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다")

        logger.info(f"Base URL: {base_url}")
        logger.info(f"App Key: {app_key[:8]}...")
        logger.info(f"App Secret: {app_secret[:8]}...")

        async with aiohttp.ClientSession() as session:
            # 토큰 발급 요청
            logger.info("🔑 토큰 발급 요청")
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

            logger.info(f"요청 URL: {token_url}")
            logger.info(f"요청 페이로드: {token_payload}")
            logger.info(f"요청 헤더: {token_headers}")

            async with session.post(token_url, json=token_payload, headers=token_headers) as response:
                response_text = await response.text()
                response_headers = dict(response.headers)

                logger.info(f"응답 상태: {response.status}")
                logger.info(f"응답 헤더: {response_headers}")
                logger.info(f"응답 내용: {response_text}")

                if response.status == 200:
                    try:
                        token_data = json.loads(response_text)
                        logger.info("📊 토큰 응답 분석:")

                        # 모든 키-값 출력
                        for key, value in token_data.items():
                            logger.info(f"  {key}: {value}")

                        # approval_key 확인
                        approval_key = token_data.get('approval_key')
                        if approval_key:
                            logger.info(f"✅ approval_key 찾음: {approval_key[:12]}...")

                            # 토큰을 즉시 사용해서 API 호출 테스트
                            logger.info("🚀 토큰 즉시 사용 테스트")

                            # 가장 간단한 API로 테스트
                            test_url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
                            test_params = {
                                "fid_cond_mrkt_div_code": "J",
                                "fid_input_iscd": "005930"
                            }
                            test_headers = {
                                'Authorization': f'Bearer {approval_key}',
                                'appkey': app_key,
                                'appsecret': app_secret,
                                'tr_id': 'FHKST01010100',
                                'custtype': 'P',
                                'Content-Type': 'application/json; charset=utf-8'
                            }

                            logger.info(f"테스트 URL: {test_url}")
                            logger.info(f"테스트 파라미터: {test_params}")
                            logger.info(f"테스트 헤더 (토큰 마스킹): {dict(test_headers)}")
                            test_headers_masked = dict(test_headers)
                            test_headers_masked['Authorization'] = f"Bearer {approval_key[:8]}..."
                            logger.info(f"마스킹된 헤더: {test_headers_masked}")

                            async with session.get(test_url, params=test_params, headers=test_headers) as test_response:
                                test_response_text = await test_response.text()
                                logger.info(f"즉시 테스트 응답 상태: {test_response.status}")
                                logger.info(f"즉시 테스트 응답 내용: {test_response_text}")

                                if test_response.status == 200:
                                    try:
                                        test_result = json.loads(test_response_text)
                                        if test_result.get('rt_cd') == '0':
                                            logger.info("✅ 토큰이 정상 작동합니다!")
                                            return True
                                        else:
                                            logger.error(f"❌ API 오류: {test_result.get('msg1', 'Unknown')}")
                                    except json.JSONDecodeError:
                                        logger.error(f"❌ JSON 파싱 실패: {test_response_text}")
                                else:
                                    logger.error(f"❌ HTTP 오류 {test_response.status}")

                        else:
                            logger.error("❌ approval_key를 찾을 수 없습니다")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON 파싱 실패: {e}")
                        logger.error(f"응답 내용: {response_text}")
                else:
                    logger.error(f"❌ 토큰 발급 실패: HTTP {response.status}")
                    logger.error(f"응답 내용: {response_text}")

        return False

    except Exception as e:
        logger.error(f"❌ 분석 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(analyze_token_response())
    if success:
        logger.info("🎉 토큰이 정상적으로 작동합니다!")
    else:
        logger.error("💥 토큰에 문제가 있습니다!")
    sys.exit(0 if success else 1)