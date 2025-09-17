#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 공식 형식 테스트 (한국투자증권 공식 문서 기준)
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_official_format():
    """KIS API 공식 문서 기준으로 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    print("[KIS API 공식 형식 테스트]")
    print(f"APP_KEY: {app_key[:10]}...")
    print("")

    if not app_key or not app_secret:
        print("ERROR: KIS API 키가 설정되지 않았습니다.")
        return False

    async with aiohttp.ClientSession() as session:
        try:
            # 1단계: 한국투자증권 공식 토큰 요청 방식
            print("[1단계] KIS 공식 토큰 요청...")

            token_url = f"{base_url}/oauth2/tokenP"

            # 공식 문서 기준 payload
            token_payload = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecret": app_secret
            }

            # 공식 문서 기준 headers
            token_headers = {
                "content-type": "application/json"
            }

            print(f"Token URL: {token_url}")
            print(f"Token Payload: {token_payload}")
            print(f"Token Headers: {token_headers}")

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(token_url, json=token_payload, headers=token_headers, timeout=timeout) as response:
                response_text = await response.text()

                print(f"토큰 응답 상태: {response.status}")
                print(f"토큰 응답: {response_text}")

                if response.status == 200:
                    try:
                        token_result = json.loads(response_text)
                        print(f"토큰 JSON 키: {list(token_result.keys())}")

                        # access_token 확인
                        if 'access_token' in token_result:
                            access_token = token_result['access_token']
                            print(f"SUCCESS: Access token 획득: {access_token[:8]}...")

                            return True
                        else:
                            print(f"access_token이 응답에 없습니다: {token_result}")

                    except json.JSONDecodeError as e:
                        print(f"JSON 파싱 실패: {e}")

                elif response_text.strip().startswith('<'):
                    print("HTML 응답 (에러 페이지) - /oauth2/Approval 시도...")

                    # /oauth2/Approval로 대체 시도
                    approval_url = f"{base_url}/oauth2/Approval"
                    approval_payload = {
                        "grant_type": "client_credentials",
                        "appkey": app_key,
                        "secretkey": app_secret
                    }

                    async with session.post(approval_url, json=approval_payload, headers=token_headers, timeout=timeout) as approval_response:
                        approval_response_text = await approval_response.text()

                        print(f"Approval 응답 상태: {approval_response.status}")
                        print(f"Approval 응답: {approval_response_text}")

                        if approval_response.status == 200:
                            approval_result = json.loads(approval_response_text)
                            if 'approval_key' in approval_result:
                                approval_key = approval_result['approval_key']
                                print(f"SUCCESS: Approval key 획득: {approval_key[:8]}...")

                                # 성공한 토큰을 캐시에 저장
                                cache_data = {
                                    "access_token": approval_key,
                                    "token_expired": "2025-09-17T23:59:59.000000"
                                }

                                os.makedirs("data", exist_ok=True)
                                with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                    json.dump(cache_data, f, indent=2, ensure_ascii=False)

                                print("토큰 캐시 업데이트 완료")
                                return True

                else:
                    print(f"토큰 요청 실패: {response.status}")
                    print(f"에러 응답: {response_text}")

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            return False

    return False

async def main():
    print("=" * 60)
    print("KIS API 공식 형식 테스트")
    print("=" * 60)

    success = await test_official_format()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 토큰 획득 성공!")
    else:
        print("ERROR: 토큰 획득 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
