#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 최종 수정 테스트
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_multiple_endpoints():
    """다양한 KIS API 끝점 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print("[KIS API 다중 끝점 테스트]")
    print(f"APP_KEY: {app_key[:10]}...")
    print("")

    if not app_key or not app_secret:
        print("ERROR: KIS API 키가 설정되지 않았습니다.")
        return False

    # 테스트할 다양한 끝점들
    test_cases = [
        {
            "name": "tokenP 끝점 (appsecret)",
            "endpoint": "/oauth2/tokenP",
            "payload": {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecret": app_secret
            }
        },
        {
            "name": "tokenP 끝점 (secretkey)",
            "endpoint": "/oauth2/tokenP",
            "payload": {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "secretkey": app_secret
            }
        },
        {
            "name": "token 끝점 (appsecret)",
            "endpoint": "/oauth2/token",
            "payload": {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecret": app_secret
            }
        },
        {
            "name": "Approval 끝점 (secretkey) - 기존",
            "endpoint": "/oauth2/Approval",
            "payload": {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "secretkey": app_secret
            }
        }
    ]

    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}] {test_case['name']} 테스트...")

            url = f"{base_url}{test_case['endpoint']}"

            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'TradingSystem/2.0',
                'Accept': 'application/json'
            }

            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with session.post(url, json=test_case['payload'], headers=headers, timeout=timeout) as response:
                    response_text = await response.text()

                    print(f"  응답 상태: {response.status}")
                    print(f"  응답 길이: {len(response_text)} 문자")

                    # HTML 응답 확인
                    if response_text.strip().startswith('<'):
                        print("  응답 타입: HTML (에러 페이지)")
                        print(f"  HTML 내용: {response_text[:100]}...")
                    else:
                        print("  응답 타입: JSON")
                        try:
                            result = json.loads(response_text)
                            print(f"  JSON 키들: {list(result.keys())}")

                            # 토큰 필드 확인
                            token_fields = ['access_token', 'approval_key', 'token', 'bearer_token']
                            found_tokens = {k: v for k, v in result.items() if k in token_fields}

                            if found_tokens:
                                print(f"  SUCCESS: 토큰 발견! {found_tokens}")

                                # 첫 번째 토큰으로 API 테스트
                                token_key, token_value = next(iter(found_tokens.items()))
                                print(f"  토큰으로 API 호출 테스트: {token_value[:8]}...")

                                # API 호출 테스트
                                test_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                                test_url = f"{base_url}{test_endpoint}"

                                test_headers = {
                                    'Authorization': f'Bearer {token_value}',
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

                                async with session.get(test_url, headers=test_headers, params=test_params, timeout=timeout) as test_response:
                                    test_response_text = await test_response.text()
                                    print(f"  API 테스트 상태: {test_response.status}")

                                    if test_response.status == 200:
                                        print("  SUCCESS: API 호출 성공!")

                                        # 성공한 토큰을 캐시에 저장
                                        cache_data = {
                                            "access_token": token_value,
                                            "token_expired": "2025-09-17T23:44:50.000000"
                                        }

                                        os.makedirs("data", exist_ok=True)
                                        with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                            json.dump(cache_data, f, indent=2, ensure_ascii=False)

                                        print("  토큰 캐시 업데이트 완료")
                                        return True
                                    else:
                                        try:
                                            error_data = json.loads(test_response_text)
                                            print(f"  API 에러: {error_data}")
                                        except:
                                            print(f"  API 에러 텍스트: {test_response_text[:100]}")
                            else:
                                print(f"  응답에 토큰이 없음: {result}")

                        except json.JSONDecodeError:
                            print(f"  JSON 파싱 실패: {response_text[:100]}...")

            except Exception as e:
                print(f"  ERROR: 예외 발생: {e}")

            print("")  # 구분선

    return False

async def main():
    print("=" * 60)
    print("KIS API 최종 수정 테스트")
    print("=" * 60)

    success = await test_multiple_endpoints()

    print("=" * 60)
    if success:
        print("SUCCESS: 올바른 토큰 발견!")
    else:
        print("ERROR: 모든 끝점 테스트 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())