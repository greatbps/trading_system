#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 2단계 토큰 요청 테스트 (다양한 grant_type)
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_two_step_auth():
    """KIS API 2단계 인증 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print("[KIS API 2단계 인증 테스트]")
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

                print(f"1단계 응답 상태: {response.status}")
                print(f"1단계 응답: {response_text}")

                if response.status == 200:
                    result1 = json.loads(response_text)
                    if 'approval_key' in result1:
                        approval_key = result1['approval_key']
                        print(f"SUCCESS: Approval key 획득: {approval_key[:8]}...")

                        # 2단계: 다양한 grant_type으로 access_token 요청
                        print("\n[2단계] Access token 요청 테스트...")

                        grant_types = [
                            "client_credentials",
                            "authorization_code",
                            "approval_key",  # 커스텀
                            "urn:ietf:params:oauth:grant-type:jwt-bearer"
                        ]

                        for grant_type in grant_types:
                            print(f"\n  grant_type '{grant_type}' 테스트...")

                            endpoint2 = "/oauth2/token"
                            url2 = f"{base_url}{endpoint2}"

                            payload2 = {
                                "grant_type": grant_type,
                                "appkey": app_key,
                                "appsecret": app_secret,
                                "approval_key": approval_key
                            }

                            print(f"  URL: {url2}")
                            print(f"  Payload: {payload2}")

                            async with session.post(url2, json=payload2, headers=headers, timeout=timeout) as token_response:
                                token_response_text = await token_response.text()

                                print(f"  응답 상태: {token_response.status}")
                                print(f"  응답 내용: {token_response_text}")

                                if token_response.status == 200:
                                    try:
                                        token_result = json.loads(token_response_text)
                                        print(f"  JSON 키들: {list(token_result.keys())}")

                                        # access_token 확인
                                        if 'access_token' in token_result:
                                            access_token = token_result['access_token']
                                            print(f"  SUCCESS: Access token 획득: {access_token[:8]}...")

                                            # API 테스트
                                            print(f"  API 호출 테스트...")

                                            test_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                                            test_url = f"{base_url}{test_endpoint}"

                                            test_headers = {
                                                'Authorization': f'Bearer {access_token}',
                                                'appkey': app_key,
                                                'appsecret': app_secret,
                                                'tr_id': 'FHKST01010100',
                                                'custtype': 'P',
                                                'Content-Type': 'application/json; charset=utf-8'
                                            }

                                            test_params = {
                                                'fid_cond_mrkt_div_code': 'J',
                                                'fid_input_iscd': '005930'
                                            }

                                            async with session.get(test_url, headers=test_headers, params=test_params, timeout=timeout) as api_response:
                                                api_response_text = await api_response.text()
                                                print(f"  API 응답 상태: {api_response.status}")

                                                if api_response.status == 200:
                                                    print("  SUCCESS: API 호출 성공!")

                                                    # 토큰 캐시 저장
                                                    cache_data = {
                                                        "access_token": access_token,
                                                        "token_expired": "2025-09-17T23:44:50.000000"
                                                    }

                                                    os.makedirs("data", exist_ok=True)
                                                    with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                                        json.dump(cache_data, f, indent=2, ensure_ascii=False)

                                                    print("  토큰 캐시 업데이트 완료")
                                                    print(f"  성공한 grant_type: {grant_type}")
                                                    return True
                                                else:
                                                    try:
                                                        api_error = json.loads(api_response_text)
                                                        print(f"  API 에러: {api_error}")
                                                    except:
                                                        print(f"  API 에러 텍스트: {api_response_text[:100]}")

                                        else:
                                            print(f"  access_token이 없음: {token_result}")

                                    except json.JSONDecodeError:
                                        print(f"  JSON 파싱 실패: {token_response_text}")

                                else:
                                    # 에러 응답 파싱
                                    try:
                                        error_result = json.loads(token_response_text)
                                        print(f"  에러 상세: {error_result}")
                                    except:
                                        print(f"  에러 텍스트: {token_response_text}")

                    else:
                        print(f"ERROR: approval_key가 없음: {result1}")
                        return False
                else:
                    print(f"ERROR: 1단계 실패: {response.status}")
                    print(f"에러: {response_text}")
                    return False

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            return False

    return False

async def main():
    print("=" * 60)
    print("KIS API 2단계 인증 테스트 (다양한 grant_type)")
    print("=" * 60)

    success = await test_two_step_auth()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 올바른 인증 방법 발견!")
    else:
        print("ERROR: 모든 방법 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())