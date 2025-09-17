#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 가상투자 서버 테스트
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_virtual_server():
    """KIS 가상투자 서버로 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")

    print("[KIS API 가상투자 서버 테스트]")
    print(f"APP_KEY: {app_key[:10]}...")
    print("")

    if not app_key or not app_secret:
        print("ERROR: KIS API 키가 설정되지 않았습니다.")
        return False

    # 실전투자 vs 가상투자 서버
    servers = [
        {
            "name": "실전투자 서버",
            "base_url": "https://openapi.koreainvestment.com:9443",
            "is_virtual": False
        },
        {
            "name": "가상투자 서버",
            "base_url": "https://openapivts.koreainvestment.com:29443",
            "is_virtual": True
        }
    ]

    async with aiohttp.ClientSession() as session:
        for server in servers:
            print(f"=== {server['name']} 테스트 ===")
            print(f"URL: {server['base_url']}")

            try:
                # 1단계: approval_key 획득
                print("  [1] Approval key 요청...")

                endpoint1 = "/oauth2/Approval"
                url1 = f"{server['base_url']}{endpoint1}"

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

                timeout = aiohttp.ClientTimeout(total=30)
                async with session.post(url1, json=payload1, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()

                    print(f"  Approval 응답 상태: {response.status}")
                    print(f"  Approval 응답: {response_text}")

                    if response.status == 200:
                        result1 = json.loads(response_text)
                        if 'approval_key' in result1:
                            approval_key = result1['approval_key']
                            print(f"  SUCCESS: Approval key 획득: {approval_key[:8]}...")

                            # 2단계: API 호출 테스트
                            print("  [2] API 호출 테스트...")

                            # 가상투자용과 실전투자용 엔드포인트가 다를 수 있음
                            if server['is_virtual']:
                                test_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                            else:
                                test_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"

                            test_url = f"{server['base_url']}{test_endpoint}"

                            test_headers = {
                                'Authorization': f'Bearer {approval_key}',
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

                            print(f"  API URL: {test_url}")
                            print(f"  API 헤더: {test_headers}")

                            async with session.get(test_url, headers=test_headers, params=test_params, timeout=timeout) as api_response:
                                api_response_text = await api_response.text()
                                print(f"  API 응답 상태: {api_response.status}")
                                print(f"  API 응답 (처음 200자): {api_response_text[:200]}")

                                if api_response.status == 200:
                                    print(f"  SUCCESS: {server['name']} API 호출 성공!")

                                    try:
                                        api_data = json.loads(api_response_text)
                                        print(f"  응답 데이터 키: {list(api_data.keys())}")
                                    except:
                                        pass

                                    # 성공한 토큰을 캐시에 저장
                                    cache_data = {
                                        "access_token": approval_key,
                                        "token_expired": "2025-09-17T23:44:50.000000",
                                        "server_type": "virtual" if server['is_virtual'] else "real",
                                        "base_url": server['base_url']
                                    }

                                    os.makedirs("data", exist_ok=True)
                                    with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                        json.dump(cache_data, f, indent=2, ensure_ascii=False)

                                    print("  토큰 캐시 업데이트 완료")
                                    return True

                                else:
                                    try:
                                        api_error = json.loads(api_response_text)
                                        print(f"  API 에러: {api_error}")
                                    except:
                                        print(f"  API 에러 텍스트: {api_response_text}")

                        else:
                            print(f"  ERROR: approval_key가 없음: {result1}")

                    else:
                        print(f"  ERROR: Approval 요청 실패: {response.status}")
                        print(f"  에러: {response_text}")

            except Exception as e:
                print(f"  ERROR: 예외 발생: {e}")

            print("")  # 구분선

    return False

async def main():
    print("=" * 60)
    print("KIS API 가상투자 vs 실전투자 서버 테스트")
    print("=" * 60)

    success = await test_virtual_server()

    print("=" * 60)
    if success:
        print("SUCCESS: 작동하는 서버 발견!")
    else:
        print("ERROR: 모든 서버 테스트 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())