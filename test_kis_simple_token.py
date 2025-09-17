#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 간단 토큰 테스트 (approval_key 직접 사용)
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_kis_simple_token():
    """KIS approval_key 직접 사용 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print("[KIS 간단 토큰 테스트]")
    print(f"APP_KEY: {app_key[:10]}...")
    print("")

    if not app_key or not app_secret:
        print("ERROR: KIS API 키가 설정되지 않았습니다.")
        return False

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Approval Key 요청
            print("[1] Approval Key 요청...")

            endpoint = "/oauth2/Approval"
            url = f"{base_url}{endpoint}"

            payload = {
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
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                response_text = await response.text()

                print(f"응답 상태: {response.status}")
                print(f"응답 내용: {response_text}")

                if response.status == 200:
                    result = json.loads(response_text)
                    if 'approval_key' in result:
                        approval_key = result['approval_key']
                        print(f"SUCCESS: Approval key 획득: {approval_key[:8]}...")

                        # 2. Approval Key를 직접 access token으로 사용하여 API 호출
                        print("\n[2] Approval Key로 직접 API 호출 테스트...")

                        test_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                        test_url = f"{base_url}{test_endpoint}"

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
                            'fid_input_iscd': '005930'  # 삼성전자
                        }

                        print(f"테스트 URL: {test_url}")
                        print(f"테스트 헤더: {test_headers}")
                        print(f"테스트 파라미터: {test_params}")

                        async with session.get(test_url, headers=test_headers, params=test_params, timeout=timeout) as test_response:
                            test_response_text = await test_response.text()

                            print(f"API 응답 상태: {test_response.status}")
                            print(f"API 응답 내용 (처음 300자): {test_response_text[:300]}")

                            if test_response.status == 200:
                                print("SUCCESS: API 호출 성공! approval_key가 올바른 access token입니다.")

                                # 토큰을 캐시 파일에 저장
                                cache_data = {
                                    "access_token": approval_key,
                                    "token_expired": "2025-09-17T20:44:50.000000"  # 임시 만료 시간
                                }

                                os.makedirs("data", exist_ok=True)
                                with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                    json.dump(cache_data, f, indent=2, ensure_ascii=False)

                                print("토큰 캐시 파일 업데이트 완료")
                                return True
                            else:
                                print(f"ERROR: API 호출 실패: {test_response.status}")
                                try:
                                    error_data = json.loads(test_response_text)
                                    print(f"에러 상세: {error_data}")
                                except:
                                    print(f"에러 텍스트: {test_response_text}")
                                return False
                    else:
                        print(f"ERROR: approval_key가 응답에 없습니다: {result}")
                        return False
                else:
                    print(f"ERROR: Approval key 요청 실패: {response.status}")
                    print(f"에러 응답: {response_text}")
                    return False

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            return False

async def main():
    print("=" * 60)
    print("KIS API 간단 토큰 테스트 (approval_key 직접 사용)")
    print("=" * 60)

    success = await test_kis_simple_token()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 테스트 성공!")
    else:
        print("ERROR: 테스트 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())