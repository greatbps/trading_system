#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 헤더 형식 테스트
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

async def test_header_formats():
    """다양한 헤더 형식으로 테스트"""
    try:
        logger.info("🔑 KIS API 헤더 형식 테스트 시작")

        # 설정 로드
        config = Config()
        app_key = getattr(config.api, 'KIS_APP_KEY', None)
        app_secret = getattr(config.api, 'KIS_APP_SECRET', None)
        base_url = getattr(config.api, 'KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')

        if not app_key or not app_secret:
            raise ValueError("KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다")

        async with aiohttp.ClientSession() as session:
            # 1. 토큰 발급
            logger.info("🔑 토큰 발급")
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
                if response.status == 200:
                    token_data = json.loads(await response.text())
                    access_token = token_data.get('approval_key')
                    logger.info(f"✅ 토큰 발급 성공: {access_token[:8]}...")
                else:
                    logger.error(f"❌ 토큰 발급 실패: {await response.text()}")
                    return False

            # 2. API 호출 테스트 - 다양한 헤더 형식
            api_url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": "005930"
            }

            # 테스트 케이스들
            test_cases = [
                {
                    "name": "형식 1: Bearer with Authorization",
                    "headers": {
                        'Authorization': f'Bearer {access_token}',
                        'appkey': app_key,
                        'appsecret': app_secret,
                        'tr_id': 'FHKST01010100',
                        'custtype': 'P',
                        'Content-Type': 'application/json; charset=utf-8'
                    }
                },
                {
                    "name": "형식 2: Bearer with authorization (소문자)",
                    "headers": {
                        'authorization': f'Bearer {access_token}',
                        'appkey': app_key,
                        'appsecret': app_secret,
                        'tr_id': 'FHKST01010100',
                        'custtype': 'P',
                        'Content-Type': 'application/json; charset=utf-8'
                    }
                },
                {
                    "name": "형식 3: 토큰 직접 전달",
                    "headers": {
                        'access_token': access_token,
                        'appkey': app_key,
                        'appsecret': app_secret,
                        'tr_id': 'FHKST01010100',
                        'custtype': 'P',
                        'Content-Type': 'application/json; charset=utf-8'
                    }
                },
                {
                    "name": "형식 4: approval_key 직접 전달",
                    "headers": {
                        'approval_key': access_token,
                        'appkey': app_key,
                        'appsecret': app_secret,
                        'tr_id': 'FHKST01010100',
                        'custtype': 'P',
                        'Content-Type': 'application/json; charset=utf-8'
                    }
                }
            ]

            for test_case in test_cases:
                logger.info(f"\n🔍 {test_case['name']}")

                async with session.get(api_url, params=params, headers=test_case['headers']) as response:
                    response_text = await response.text()
                    logger.info(f"응답 상태: {response.status}")

                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            if result.get('rt_cd') == '0':
                                logger.info("✅ 성공!")
                                output = result.get('output', {})
                                current_price = output.get('stck_prpr', '0')
                                logger.info(f"📈 삼성전자 현재가: {current_price}원")
                                return True
                            else:
                                logger.warning(f"⚠️ API 오류: {result.get('msg1', 'Unknown')}")
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ JSON 파싱 실패: {response_text[:100]}")
                    else:
                        logger.warning(f"⚠️ HTTP {response.status}: {response_text[:100]}")

            logger.error("❌ 모든 헤더 형식 테스트 실패")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_header_formats())
    if success:
        logger.info("🎉 성공적인 헤더 형식을 찾았습니다!")
    else:
        logger.error("💥 모든 헤더 형식이 실패했습니다!")
    sys.exit(0 if success else 1)