#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
가장 간단한 API 테스트
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

async def test_simple_api():
    """가장 간단한 API 테스트"""
    try:
        logger.info("🔑 간단한 API 테스트 시작")

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

            # 2. 가장 간단한 API 호출 - 주식 현재가
            logger.info("📊 주식 현재가 조회 테스트")
            api_url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"

            # 삼성전자 현재가 조회
            params = {
                "fid_cond_mrkt_div_code": "J",  # 시장 구분
                "fid_input_iscd": "005930"      # 삼성전자 종목코드
            }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'FHKST01010100',  # 주식 현재가 시세
                'custtype': 'P',
                'Content-Type': 'application/json; charset=utf-8'
            }

            logger.info(f"요청 URL: {api_url}")
            logger.info(f"파라미터: {params}")
            logger.info(f"헤더 (토큰 마스킹): Authorization=Bearer {access_token[:8]}..., appkey={app_key[:8]}...")

            async with session.get(api_url, params=params, headers=headers) as response:
                response_text = await response.text()
                logger.info(f"응답 상태: {response.status}")

                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        if result.get('rt_cd') == '0':
                            logger.info("✅ API 호출 성공!")
                            output = result.get('output', {})
                            current_price = output.get('stck_prpr', '0')
                            change_rate = output.get('prdy_ctrt', '0')
                            logger.info(f"📈 삼성전자 현재가: {current_price}원")
                            logger.info(f"📈 전일 대비: {change_rate}%")
                            return True
                        else:
                            logger.error(f"❌ API 응답 오류: {result.get('msg1', 'Unknown error')}")
                            logger.error(f"전체 응답: {response_text}")
                            return False
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON 파싱 오류: {e}")
                        logger.error(f"응답 내용: {response_text}")
                        return False
                else:
                    logger.error(f"❌ HTTP 오류 {response.status}")
                    logger.error(f"응답 내용: {response_text}")
                    return False

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_api())
    if success:
        logger.info("🎉 테스트 성공!")
    else:
        logger.error("💥 테스트 실패!")
    sys.exit(0 if success else 1)