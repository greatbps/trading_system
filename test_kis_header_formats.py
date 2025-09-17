#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 헤더 형식 테스트
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_header_formats():
    """다양한 헤더 형식으로 KIS API 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print("[KIS API 헤더 형식 테스트]")
    print(f"APP_KEY: {app_key[:10]}...")
    print("")

    if not app_key or not app_secret:
        print("ERROR: KIS API 키가 설정되지 않았습니다.")
        return False

    async with aiohttp.ClientSession() as session:
        # 1단계: approval_key 획득
        print("[1단계] Approval key 요청...")

        endpoint1 = "/oauth2/Approval"
        url1 = f"{base_url}{endpoint1}"

        payload1 = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret
        }

        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'TradingSystem/2.0',
            'Accept': 'application/json'
        }

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(url1, json=payload1, headers=headers, timeout=timeout) as response:
                response_text = await response.text()

                if response.status == 200:
                    result1 = json.loads(response_text)
                    if 'approval_key' in result1:
                        approval_key = result1['approval_key']
                        print(f"SUCCESS: Approval key 획득: {approval_key[:8]}...")

                        # 2단계: 다양한 헤더 형식으로 API 테스트
                        print("\n[2단계] 다양한 헤더 형식 테스트...")

                        test_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                        test_url = f"{base_url}{test_endpoint}"

                        test_params = {
                            'fid_cond_mrkt_div_code': 'J',
                            'fid_input_iscd': '005930'
                        }

                        # 테스트할 헤더 형식들
                        header_formats = [
                            {
                                "name": "Bearer 토큰 형식",
                                "headers": {
                                    'Authorization': f'Bearer {approval_key}',
                                    'appkey': app_key,
                                    'appsecret': app_secret,
                                    'tr_id': 'FHKST01010100',
                                    'custtype': 'P',
                                    'Content-Type': 'application/json; charset=utf-8'
                                }
                            },
                            {
                                "name": "토큰만 형식",
                                "headers": {
                                    'Authorization': approval_key,
                                    'appkey': app_key,
                                    'appsecret': app_secret,
                                    'tr_id': 'FHKST01010100',
                                    'custtype': 'P',
                                    'Content-Type': 'application/json; charset=utf-8'
                                }
                            },
                            {
                                "name": "access_token 헤더 형식",
                                "headers": {
                                    'access_token': approval_key,
                                    'appkey': app_key,
                                    'appsecret': app_secret,
                                    'tr_id': 'FHKST01010100',
                                    'custtype': 'P',
                                    'Content-Type': 'application/json; charset=utf-8'
                                }
                            },
                            {
                                "name": "approval_key 헤더 형식",
                                "headers": {
                                    'approval_key': approval_key,
                                    'appkey': app_key,
                                    'appsecret': app_secret,
                                    'tr_id': 'FHKST01010100',
                                    'custtype': 'P',
                                    'Content-Type': 'application/json; charset=utf-8'
                                }
                            },
                            {
                                "name": "token 헤더 형식",
                                "headers": {
                                    'token': approval_key,
                                    'appkey': app_key,
                                    'appsecret': app_secret,
                                    'tr_id': 'FHKST01010100',
                                    'custtype': 'P',
                                    'Content-Type': 'application/json; charset=utf-8'
                                }
                            }
                        ]

                        for i, header_format in enumerate(header_formats, 1):
                            print(f"\n  [{i}] {header_format['name']} 테스트...")

                            print(f"  헤더: {header_format['headers']}")

                            async with session.get(test_url, headers=header_format['headers'], params=test_params, timeout=timeout) as api_response:
                                api_response_text = await api_response.text()
                                print(f"  응답 상태: {api_response.status}")

                                if api_response.status == 200:
                                    print("  SUCCESS: API 호출 성공!")

                                    try:
                                        api_data = json.loads(api_response_text)
                                        print(f"  응답 데이터 키: {list(api_data.keys())}")
                                    except:
                                        print(f"  응답 길이: {len(api_response_text)} 문자")

                                    # 성공한 토큰을 캐시에 저장
                                    cache_data = {
                                        "access_token": approval_key,
                                        "token_expired": "2025-09-17T23:44:50.000000"
                                    }

                                    os.makedirs("data", exist_ok=True)
                                    with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                        json.dump(cache_data, f, indent=2, ensure_ascii=False)

                                    print("  토큰 캐시 업데이트 완료")
                                    print(f"  성공한 헤더 형식: {header_format['name']}")
                                    return True

                                else:
                                    try:
                                        api_error = json.loads(api_response_text)
                                        print(f"  에러: {api_error}")
                                    except:
                                        print(f"  에러 텍스트: {api_response_text[:100]}")

                    else:
                        print(f"ERROR: approval_key가 없음: {result1}")
                        return False
                else:
                    print(f"ERROR: 1단계 실패: {response.status}")
                    return False

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            return False

    return False

async def main():
    print("=" * 60)
    print("KIS API 헤더 형식 테스트")
    print("=" * 60)

    success = await test_header_formats()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 올바른 헤더 형식 발견!")
    else:
        print("ERROR: 모든 헤더 형식 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())