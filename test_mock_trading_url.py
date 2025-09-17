#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모의투자용 URL 테스트
"""

import asyncio
import aiohttp
import json
from config import Config

async def test_mock_trading_urls():
    """모의투자용 URL들 테스트"""
    print("=== 모의투자 URL 테스트 ===")

    config = Config()

    # 다양한 모의투자 URL 시도
    mock_urls = [
        "https://openapivts.koreainvestment.com:29443",  # VTS (Virtual Trading System)
        "https://openapi.koreainvestment.com:29443",     # 모의투자 포트
        "https://openapi-vts.koreainvestment.com:9443",  # VTS 서브도메인
        "https://vts.koreainvestment.com:9443",          # VTS 간단 도메인
    ]

    for mock_url in mock_urls:
        print(f"\n테스트 URL: {mock_url}")

        # 토큰 요청
        token = await request_token_with_url(config, mock_url)

        if token:
            print(f"  토큰 획득 성공: {token[:20]}...")

            # 즉시 API 테스트
            success = await test_api_with_token(config, mock_url, token)
            if success:
                print(f"  ✅ API 호출 성공! 올바른 URL: {mock_url}")
                return mock_url, token
            else:
                print(f"  ❌ API 호출 실패")
        else:
            print(f"  ❌ 토큰 획득 실패")

    return None, None

async def request_token_with_url(config, base_url):
    """특정 URL로 토큰 요청"""
    endpoint = "/oauth2/Approval"
    url = f"{base_url}{endpoint}"

    payload = {
        "grant_type": "client_credentials",
        "appkey": config.api.KIS_APP_KEY,
        "secretkey": config.api.KIS_APP_SECRET
    }

    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'TradingSystem/2.0',
        'Accept': 'application/json'
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    response_text = await response.text()
                    result = json.loads(response_text)

                    if 'approval_key' in result:
                        return result['approval_key']

                return None

    except Exception as e:
        print(f"  토큰 요청 예외: {e}")
        return None

async def test_api_with_token(config, base_url, token):
    """토큰으로 API 호출 테스트"""
    headers = {
        'Authorization': f'Bearer {token}',
        'appkey': config.api.KIS_APP_KEY,
        'appsecret': config.api.KIS_APP_SECRET,
        'tr_id': 'FHKST01010100',
        'custtype': 'P',
        'Content-Type': 'application/json; charset=utf-8'
    }

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "005930"
            }

            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return True
                else:
                    response_text = await response.text()
                    print(f"  API 응답: {response.status} - {response_text[:100]}...")
                    return False

    except Exception as e:
        print(f"  API 테스트 예외: {e}")
        return False

async def test_environment_headers():
    """환경별 헤더 차이 테스트"""
    print("\n=== 환경별 헤더 테스트 ===")

    config = Config()
    token = "test-token"  # 더미 토큰

    # 실거래용 헤더
    real_headers = {
        'Authorization': f'Bearer {token}',
        'appkey': config.api.KIS_APP_KEY,
        'appsecret': config.api.KIS_APP_SECRET,
        'tr_id': 'FHKST01010100',
        'custtype': 'P',  # P: 개인, B: 법인
        'Content-Type': 'application/json; charset=utf-8'
    }

    # 모의투자용 헤더 (custtype 다를 수 있음)
    mock_headers = {
        'Authorization': f'Bearer {token}',
        'appkey': config.api.KIS_APP_KEY,
        'appsecret': config.api.KIS_APP_SECRET,
        'tr_id': 'VHKST01010100',  # V로 시작하는 TR_ID
        'custtype': 'P',
        'Content-Type': 'application/json; charset=utf-8'
    }

    print("실거래용 헤더:")
    for k, v in real_headers.items():
        print(f"  {k}: {v}")

    print("\n모의투자용 헤더:")
    for k, v in mock_headers.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    async def main():
        # 1단계: 모의투자 URL 테스트
        success_url, token = await test_mock_trading_urls()

        if success_url:
            print(f"\n🎉 성공한 모의투자 URL: {success_url}")
        else:
            print("\n❌ 모든 모의투자 URL 실패")

        # 2단계: 환경별 헤더 차이 확인
        await test_environment_headers()

    asyncio.run(main())