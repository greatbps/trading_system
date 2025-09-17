#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
새로운 JWT 토큰으로 실제 API 호출 테스트
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_api_with_jwt_token():
    """JWT 토큰으로 실제 API 호출 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"

    # 캐시된 토큰 확인
    try:
        with open("data/kis_token_cache.json", 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            cached_token = cache_data.get("access_token", "")
            print(f"캐시된 토큰: {cached_token[:20]}...")
    except:
        cached_token = ""

    print("[JWT 토큰으로 API 호출 테스트]")
    print("")

    async with aiohttp.ClientSession() as session:
        try:
            # 1단계: 새로운 JWT 토큰 획득
            print("[1단계] JWT 토큰 획득...")

            token_url = f"{base_url}/oauth2/tokenP"
            token_payload = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecret": app_secret
            }
            token_headers = {
                "content-type": "application/json"
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(token_url, json=token_payload, headers=token_headers, timeout=timeout) as response:
                if response.status == 200:
                    token_result = json.loads(await response.text())
                    access_token = token_result['access_token']
                    expires_in = token_result.get('expires_in', 86400)
                    
                    print(f"SUCCESS: JWT 토큰 획득")
                    print(f"Token Type: {token_result.get('token_type', 'Bearer')}")
                    print(f"Expires In: {expires_in} seconds")
                    print(f"Token: {access_token[:50]}...")
                    print("")

                    # 2단계: 실제 API 호출
                    print("[2단계] 주식 현재가 조회 API 호출...")

                    api_url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
                    api_headers = {
                        "content-type": "application/json; charset=utf-8",
                        "authorization": f"Bearer {access_token}",
                        "appkey": app_key,
                        "appsecret": app_secret,
                        "tr_id": "FHKST01010100"
                    }
                    api_params = {
                        "FID_COND_MRKT_DIV_CODE": "J",
                        "FID_INPUT_ISCD": "005930"  # 삼성전자
                    }

                    print(f"API URL: {api_url}")
                    print(f"Headers: {api_headers}")
                    print(f"Params: {api_params}")
                    print("")

                    async with session.get(api_url, headers=api_headers, params=api_params, timeout=timeout) as api_response:
                        api_text = await api_response.text()
                        
                        print(f"API 응답 상태: {api_response.status}")
                        print(f"API 응답 (처음 500자): {api_text[:500]}")
                        
                        if api_response.status == 200:
                            try:
                                api_data = json.loads(api_text)
                                rt_cd = api_data.get('rt_cd', '1')
                                
                                print(f"응답 키들: {list(api_data.keys())}")
                                print(f"RT_CD (결과코드): {rt_cd}")
                                print(f"MSG1 (메시지): {api_data.get('msg1', '')}")
                                
                                if rt_cd == '0':
                                    print("SUCCESS: 정상적인 주식 데이터 수신!")
                                    
                                    # output 데이터 확인
                                    if 'output' in api_data:
                                        output = api_data['output']
                                        print(f"주식 정보:")
                                        print(f"  종목명: {output.get('hts_kor_isnm', 'N/A')}")
                                        print(f"  현재가: {output.get('stck_prpr', 'N/A')}")
                                        print(f"  전일 대비: {output.get('prdy_vrss', 'N/A')}")
                                        print(f"  등락률: {output.get('prdy_ctrt', 'N/A')}%")
                                    
                                    # 성공한 토큰을 캐시에 저장
                                    cache_data = {
                                        "access_token": access_token,
                                        "token_expired": "2025-09-17T21:17:47.000000",  # API 응답의 만료시간
                                        "token_type": "Bearer"
                                    }
                                    
                                    os.makedirs("data", exist_ok=True)
                                    with open("data/kis_token_cache.json", 'w', encoding='utf-8') as f:
                                        json.dump(cache_data, f, indent=2, ensure_ascii=False)
                                    
                                    print("토큰 캐시 업데이트 완료")
                                    return True
                                else:
                                    print(f"API 에러: RT_CD={rt_cd}, MSG={api_data.get('msg1', '')}")
                                    
                            except json.JSONDecodeError:
                                print("JSON 파싱 실패")
                                
                        else:
                            print(f"API 호출 실패: HTTP {api_response.status}")
                            try:
                                error_data = json.loads(api_text)
                                print(f"에러 상세: {error_data}")
                            except:
                                print(f"에러 텍스트: {api_text}")

                else:
                    response_text = await response.text()
                    print(f"토큰 획득 실패: HTTP {response.status}")
                    print(f"응답: {response_text}")

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            return False

    return False

async def main():
    print("=" * 60)
    print("JWT 토큰으로 실제 API 호출 테스트")
    print("=" * 60)

    success = await test_api_with_jwt_token()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 전체 API 호출 성공!")
    else:
        print("ERROR: API 호출 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
