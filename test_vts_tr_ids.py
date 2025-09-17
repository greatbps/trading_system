#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모의투자(VTS) TR_ID 테스트
"""

import asyncio
import aiohttp
import json
from config import Config

async def test_vts_tr_ids():
    """모의투자용 TR_ID들 테스트"""
    print("=== 모의투자 TR_ID 테스트 ===")

    config = Config()

    # 모의투자 URL 사용
    vts_url = "https://openapivts.koreainvestment.com:29443"

    # 토큰 획득
    token = await get_vts_token(config, vts_url)
    if not token:
        print("VTS 토큰 획득 실패")
        return

    print(f"VTS 토큰: {token[:20]}...")

    # 다양한 TR_ID 시도 (V로 시작하는 모의투자용)
    tr_ids_to_test = [
        "VHKST01010100",  # V + HKST01010100 (현재가)
        "VFHKST01010100", # VF + HKST01010100
        "VTCA0903R",      # V + TCA0903R (휴장일)
        "VCTCA0903R",     # VC + TCA0903R
        "FHKST01010100",  # 기존 실거래용
        "CTCA0903R",      # 기존 휴장일용
    ]

    endpoints_to_test = [
        {
            "name": "현재가 조회",
            "url": "/uapi/domestic-stock/v1/quotations/inquire-price",
            "params": {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"}
        },
        {
            "name": "휴장일 조회",
            "url": "/uapi/domestic-stock/v1/quotations/chk-holiday",
            "params": {"BASS_DT": "20250916"}
        }
    ]

    for endpoint in endpoints_to_test:
        print(f"\n=== {endpoint['name']} 테스트 ===")

        for tr_id in tr_ids_to_test:
            result = await test_api_call(config, vts_url, token, endpoint, tr_id)
            if result:
                print(f"✅ 성공! TR_ID: {tr_id}, 엔드포인트: {endpoint['name']}")
                return vts_url, token, tr_id, endpoint
            else:
                print(f"❌ 실패: TR_ID: {tr_id}")

    return None, None, None, None

async def get_vts_token(config, base_url):
    """VTS 토큰 획득"""
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
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    response_text = await response.text()
                    result = json.loads(response_text)

                    if 'approval_key' in result:
                        return result['approval_key']

                return None

    except Exception as e:
        print(f"토큰 요청 예외: {e}")
        return None

async def test_api_call(config, base_url, token, endpoint, tr_id):
    """API 호출 테스트"""
    headers = {
        'Authorization': f'Bearer {token}',
        'appkey': config.api.KIS_APP_KEY,
        'appsecret': config.api.KIS_APP_SECRET,
        'tr_id': tr_id,
        'custtype': 'P',
        'Content-Type': 'application/json; charset=utf-8'
    }

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}{endpoint['url']}"

            async with session.get(url, params=endpoint['params'], headers=headers) as response:
                response_text = await response.text()

                if response.status == 200:
                    print(f"  200 OK: {response_text[:100]}...")
                    return True
                else:
                    error_msg = response_text[:100] if len(response_text) <= 100 else response_text[:100] + "..."
                    if "유효하지 않은 token" in response_text:
                        print(f"  토큰 오류")
                    elif "invalid tr_id" in response_text.lower():
                        print(f"  잘못된 TR_ID")
                    elif "not found" in response_text.lower():
                        print(f"  엔드포인트 없음")
                    else:
                        print(f"  {response.status}: {error_msg}")

                    return False

    except Exception as e:
        print(f"  예외: {e}")
        return False

async def test_without_tr_id():
    """TR_ID 없이 API 호출 테스트"""
    print("\n=== TR_ID 없이 테스트 ===")

    config = Config()
    vts_url = "https://openapivts.koreainvestment.com:29443"

    token = await get_vts_token(config, vts_url)
    if not token:
        return

    # TR_ID 없는 헤더
    headers = {
        'Authorization': f'Bearer {token}',
        'appkey': config.api.KIS_APP_KEY,
        'appsecret': config.api.KIS_APP_SECRET,
        'custtype': 'P',
        'Content-Type': 'application/json; charset=utf-8'
    }

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{vts_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"}

            async with session.get(url, params=params, headers=headers) as response:
                response_text = await response.text()
                print(f"TR_ID 없이: {response.status} - {response_text[:100]}...")

    except Exception as e:
        print(f"TR_ID 없이 예외: {e}")

if __name__ == "__main__":
    async def main():
        # 1단계: VTS TR_ID 테스트
        vts_url, token, tr_id, endpoint = await test_vts_tr_ids()

        if vts_url and tr_id:
            print(f"\n🎉 성공 조합 발견!")
            print(f"URL: {vts_url}")
            print(f"TR_ID: {tr_id}")
            print(f"엔드포인트: {endpoint['name']}")
        else:
            print("\n❌ 모든 조합 실패")

        # 2단계: TR_ID 없이 테스트
        await test_without_tr_id()

    asyncio.run(main())