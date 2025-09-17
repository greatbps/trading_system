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

async def test_kis_header_formats():
    """KIS API 다양한 헤더 형식 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print("[KIS API 헤더 형식 테스트]")
    print("")

    async with aiohttp.ClientSession() as session:
        try:
            # 1. 토큰 획득
            print("[1] 토큰 획득...")

            endpoint = "/oauth2/Approval"
            url = f"{base_url}{endpoint}"

            payload = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "secretkey": app_secret
            }

            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'TradingSystem/2.0'
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    result = json.loads(await response.text())
                    access_token = result['approval_key']
                    print(f"토큰 획득: {access_token[:10]}...")

                    # 2. 다양한 헤더 형식 테스트
                    api_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                    api_url = f"{base_url}{api_endpoint}"

                    api_params = {
                        'fid_cond_mrkt_div_code': 'J',
                        'fid_input_iscd': '005930'
                    }

                    # 테스트 케이스들
                    test_cases = [
                        {
                            "name": "Bearer Token",
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
                            "name": "authorization (소문자)",
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
                            "name": "access_token 헤더",
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
                            "name": "token 헤더",
                            "headers": {
                                'token': access_token,
                                'appkey': app_key,
                                'appsecret': app_secret,
                                'tr_id': 'FHKST01010100',
                                'custtype': 'P',
                                'Content-Type': 'application/json; charset=utf-8'
                            }
                        },
                        {
                            "name": "approval_key 헤더",
                            "headers": {
                                'approval_key': access_token,
                                'appkey': app_key,
                                'appsecret': app_secret,
                                'tr_id': 'FHKST01010100',
                                'custtype': 'P',
                                'Content-Type': 'application/json; charset=utf-8'
                            }
                        },
                        {
                            "name": "OAuth Bearer (공백 없음)",
                            "headers": {
                                'Authorization': f'Bearer{access_token}',
                                'appkey': app_key,
                                'appsecret': app_secret,
                                'tr_id': 'FHKST01010100',
                                'custtype': 'P',
                                'Content-Type': 'application/json; charset=utf-8'
                            }
                        }
                    ]

                    for i, test_case in enumerate(test_cases, 2):
                        print(f"\n[{i}] {test_case['name']} 테스트...")

                        try:
                            async with session.get(api_url, headers=test_case['headers'], params=api_params, timeout=timeout) as api_response:
                                api_response_text = await api_response.text()

                                print(f"  응답 코드: {api_response.status}")
                                print(f"  응답 내용: {api_response_text[:150]}...")

                                if api_response.status == 200:
                                    print(f"  SUCCESS: {test_case['name']} 성공!")
                                    return True
                                elif "유효하지 않은 token" in api_response_text:
                                    print(f"  ERROR: 토큰 인증 실패")
                                else:
                                    print(f"  ERROR: 다른 오류")

                        except Exception as e:
                            print(f"  ERROR: 예외 발생: {e}")

                    print("\n모든 헤더 형식 테스트 완료. 성공한 형식이 없습니다.")
                    return False

                else:
                    print(f"ERROR: 토큰 획득 실패: {response.status}")
                    return False

        except Exception as e:
            print(f"ERROR: 전체 예외 발생: {e}")
            return False

async def main():
    print("=" * 60)
    print("KIS API 헤더 형식 테스트")
    print("=" * 60)

    success = await test_kis_header_formats()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 성공한 헤더 형식을 찾았습니다!")
    else:
        print("ERROR: 모든 헤더 형식이 실패했습니다.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())