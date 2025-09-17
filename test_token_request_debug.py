#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
토큰 요청 과정 상세 디버깅
"""

import asyncio
import aiohttp
import json
import os
from config import Config

async def test_manual_token_request():
    """수동 토큰 요청으로 상세 디버깅"""
    print("=== 수동 토큰 요청 디버깅 ===")

    config = Config()

    print("1. 설정 확인")
    print(f"   BASE_URL: {config.api.KIS_BASE_URL}")
    print(f"   APP_KEY: {config.api.KIS_APP_KEY[:10]}...")
    print(f"   APP_SECRET: {config.api.KIS_APP_SECRET[:10]}...")

    # 수동으로 토큰 요청
    print("\n2. 수동 토큰 요청")

    endpoint = "/oauth2/Approval"
    url = f"{config.api.KIS_BASE_URL}{endpoint}"

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

    print(f"   URL: {url}")
    print(f"   Payload keys: {list(payload.keys())}")
    print(f"   Headers: {headers}")

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()

                print(f"\n3. 토큰 요청 응답")
                print(f"   상태: {response.status}")
                print(f"   헤더: {dict(response.headers)}")
                print(f"   내용: {response_text}")

                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        print(f"\n4. 파싱된 응답")
                        print(f"   키들: {list(result.keys())}")

                        if 'approval_key' in result:
                            approval_key = result['approval_key']
                            print(f"   approval_key: {approval_key[:20]}...")
                            print(f"   approval_key 길이: {len(approval_key)}")
                            print(f"   approval_key 타입: {type(approval_key)}")

                            # UUID 형식 확인
                            import re
                            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                            is_uuid = bool(re.match(uuid_pattern, approval_key))
                            print(f"   UUID 형식: {is_uuid}")

                            # 이 토큰으로 즉시 API 테스트
                            print(f"\n5. 즉시 API 테스트")
                            await test_immediate_api_call(config, approval_key)

                            return approval_key
                        else:
                            print(f"   ❌ approval_key 없음")
                            return None

                    except json.JSONDecodeError as e:
                        print(f"   ❌ JSON 파싱 실패: {e}")
                        return None
                else:
                    print(f"   ❌ 토큰 요청 실패: {response.status}")
                    print(f"   오류 내용: {response_text}")
                    return None

    except Exception as e:
        print(f"   ❌ 예외 발생: {e}")
        return None

async def test_immediate_api_call(config, token):
    """토큰 획득 직후 즉시 API 호출"""
    print("   즉시 API 호출 테스트 중...")

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
            url = f"{config.api.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "005930"
            }

            async with session.get(url, params=params, headers=headers) as response:
                response_text = await response.text()

                print(f"   즉시 테스트 결과: {response.status}")
                print(f"   즉시 테스트 내용: {response_text[:150]}...")

                if response.status == 200:
                    print("   ✅ 즉시 API 호출 성공!")
                    return True
                else:
                    print(f"   ❌ 즉시 API 호출 실패")
                    return False

    except Exception as e:
        print(f"   즉시 테스트 예외: {e}")
        return False

async def test_different_endpoints():
    """다른 API 엔드포인트로 테스트"""
    print("\n=== 다른 엔드포인트 테스트 ===")

    config = Config()

    # 캐시된 토큰 사용
    cache_file = "data/kis_token_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            token = cache_data.get('access_token')
            print(f"캐시된 토큰: {token[:20]}...")

            # 다른 엔드포인트들 시도
            endpoints = [
                {
                    "name": "현재가 조회",
                    "url": "/uapi/domestic-stock/v1/quotations/inquire-price",
                    "tr_id": "FHKST01010100",
                    "params": {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"}
                },
                {
                    "name": "휴장일 조회",
                    "url": "/uapi/domestic-stock/v1/quotations/chk-holiday",
                    "tr_id": "CTCA0903R",
                    "params": {"BASS_DT": "20250916"}
                }
            ]

            for endpoint in endpoints:
                print(f"\n테스트: {endpoint['name']}")

                headers = {
                    'Authorization': f'Bearer {token}',
                    'appkey': config.api.KIS_APP_KEY,
                    'appsecret': config.api.KIS_APP_SECRET,
                    'tr_id': endpoint['tr_id'],
                    'custtype': 'P',
                    'Content-Type': 'application/json; charset=utf-8'
                }

                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"{config.api.KIS_BASE_URL}{endpoint['url']}"

                        async with session.get(url, params=endpoint['params'], headers=headers) as response:
                            response_text = await response.text()

                            print(f"   결과: {response.status} - {response_text[:100]}...")

                except Exception as e:
                    print(f"   예외: {e}")

if __name__ == "__main__":
    async def main():
        # 1단계: 수동 토큰 요청
        token = await test_manual_token_request()

        # 2단계: 다른 엔드포인트 테스트
        await test_different_endpoints()

    asyncio.run(main())