#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 토큰 인증 디버깅 테스트
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv
from datetime import datetime

# 환경변수 로드
load_dotenv(override=True)

async def test_kis_token():
    """KIS 토큰 요청 테스트"""

    # 환경변수에서 설정 로드
    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print(f"[KIS API 인증 테스트]")
    print(f"APP_KEY: {app_key[:10]}{'*' * (len(app_key) - 10) if len(app_key) > 10 else 'NOT SET'}")
    print(f"APP_SECRET: {'*' * 20 if app_secret else 'NOT SET'}")
    print(f"BASE_URL: {base_url}")
    print("")

    if not app_key or not app_secret:
        print("ERROR: KIS API 키가 설정되지 않았습니다.")
        return False

    # 1. Approval Key 요청 (첫 번째 단계)
    async with aiohttp.ClientSession() as session:
        try:
            print("[1] Approval Key 요청 중...")

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

            print(f"URL: {url}")
            print(f"Payload: {payload}")
            print(f"Headers: {headers}")
            print("")

            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                response_text = await response.text()

                print(f"응답 상태: {response.status}")
                print(f"응답 헤더: {dict(response.headers)}")
                print(f"응답 내용: {response_text}")
                print("")

                if response.status == 200:
                    try:
                        result = json.loads(response_text)

                        if 'approval_key' in result:
                            approval_key = result['approval_key']
                            print(f"SUCCESS: Approval key 획득: {approval_key[:8]}...")

                            # 2. 실제 Access Token 요청 (두 번째 단계)
                            print("\n[2] Access Token 요청 중...")

                            token_endpoint = "/oauth2/token"
                            token_url = f"{base_url}{token_endpoint}"

                            token_payload = {
                                "grant_type": "authorization_code",
                                "appkey": app_key,
                                "appsecret": app_secret,
                                "approval_key": approval_key
                            }

                            print(f"Token URL: {token_url}")
                            print(f"Token Payload: {token_payload}")
                            print("")

                            async with session.post(token_url, json=token_payload, headers=headers, timeout=timeout) as token_response:
                                token_response_text = await token_response.text()

                                print(f"토큰 응답 상태: {token_response.status}")
                                print(f"토큰 응답 헤더: {dict(token_response.headers)}")
                                print(f"토큰 응답 내용: {token_response_text}")
                                print("")

                                if token_response.status == 200:
                                    try:
                                        token_result = json.loads(token_response_text)

                                        if 'access_token' in token_result:
                                            access_token = token_result['access_token']
                                            print(f"SUCCESS: Access token 획득: {access_token[:8]}...")

                                            # 3. Token 검증 - 간단한 API 호출 테스트
                                            print("\n[3] Token 검증 테스트 중...")

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
                                                'fid_input_iscd': '005930'  # 삼성전자
                                            }

                                            print(f"Test URL: {test_url}")
                                            print(f"Test Headers: {test_headers}")
                                            print(f"Test Params: {test_params}")
                                            print("")

                                            async with session.get(test_url, headers=test_headers, params=test_params, timeout=timeout) as test_response:
                                                test_response_text = await test_response.text()

                                                print(f"검증 응답 상태: {test_response.status}")
                                                print(f"검증 응답 헤더: {dict(test_response.headers)}")
                                                print(f"검증 응답 내용 (처음 200자): {test_response_text[:200]}")

                                                if test_response.status == 200:
                                                    print("SUCCESS: 토큰 검증 성공!")
                                                    return True
                                                else:
                                                    print(f"ERROR: 토큰 검증 실패: HTTP {test_response.status}")
                                                    return False

                                        else:
                                            print(f"ERROR: Access token이 응답에 없습니다: {list(token_result.keys())}")
                                            return False

                                    except json.JSONDecodeError as e:
                                        print(f"ERROR: 토큰 응답 JSON 파싱 실패: {e}")
                                        return False
                                else:
                                    print(f"ERROR: 토큰 요청 실패: HTTP {token_response.status}")
                                    print(f"에러 응답: {token_response_text}")
                                    return False

                        else:
                            print(f"ERROR: Approval key가 응답에 없습니다: {list(result.keys())}")
                            return False

                    except json.JSONDecodeError as e:
                        print(f"ERROR: 응답 JSON 파싱 실패: {e}")
                        return False
                else:
                    print(f"ERROR: Approval key 요청 실패: HTTP {response.status}")
                    print(f"에러 응답: {response_text}")
                    return False

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            return False

async def main():
    """메인 함수"""
    print("=" * 50)
    print("KIS API 토큰 인증 디버깅 테스트")
    print("=" * 50)

    success = await test_kis_token()

    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: 전체 테스트 성공!")
    else:
        print("ERROR: 테스트 실패!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())