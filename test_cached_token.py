#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캐시된 JWT 토큰으로 API 호출 테스트
"""

import asyncio
import aiohttp
import json
import os

async def test_with_cached_token():
    """캐시된 토큰으로 API 호출 테스트"""
    
    # 캐시된 토큰 로드
    try:
        with open("data/kis_token_cache.json", 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            access_token = cache_data.get("access_token", "")
            
        print("[캐시된 JWT 토큰으로 API 테스트]")
        print(f"토큰: {access_token[:50]}...")
        print("")
        
    except FileNotFoundError:
        print("ERROR: 토큰 캐시 파일이 없습니다.")
        return False
    
    if not access_token:
        print("ERROR: 캐시된 토큰이 없습니다.")
        return False

    # API 설정
    app_key = os.getenv("KIS_APP_KEY", "PSHxQQJPRPkOU3dpVKePKpTtLt03p3RRaSqf")
    app_secret = os.getenv("KIS_APP_SECRET", "uX8/GRXNBhGquQEafPVWzKURSQPDK9fQEfBvmdQx58khf/TNRInTJ/ek3LVHlVffImQS1Dafvcw1f7eE7QTS5PA+88NXp9byxexz/8va7CBZPDU9cQBAMGYfJFt6p5jNKI1CcaumXO9fDlNR0+GpyTbPV36er7h+I3xkA5KPNn94Wl86XiY=")
    base_url = "https://openapi.koreainvestment.com:9443"

    async with aiohttp.ClientSession() as session:
        try:
            print("[1] 주식 현재가 조회 API 호출...")
            
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

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(api_url, headers=api_headers, params=api_params, timeout=timeout) as response:
                response_text = await response.text()
                
                print(f"응답 상태: {response.status}")
                print(f"응답 (처음 500자): {response_text[:500]}")
                
                if response.status == 200:
                    try:
                        api_data = json.loads(response_text)
                        rt_cd = api_data.get('rt_cd', '1')
                        
                        print(f"RT_CD: {rt_cd}")
                        print(f"MSG1: {api_data.get('msg1', '')}")
                        
                        if rt_cd == '0':
                            print("SUCCESS: 정상적인 API 응답!")
                            
                            if 'output' in api_data:
                                output = api_data['output']
                                print(f"종목 정보:")
                                print(f"  종목명: {output.get('hts_kor_isnm', 'N/A')}")
                                print(f"  현재가: {output.get('stck_prpr', 'N/A')}")
                                print(f"  전일대비: {output.get('prdy_vrss', 'N/A')}")
                                print(f"  등락률: {output.get('prdy_ctrt', 'N/A')}%")
                            
                            return True
                        else:
                            print(f"API 에러: {api_data.get('msg1', '')}")
                    except json.JSONDecodeError:
                        print("JSON 파싱 실패")
                else:
                    try:
                        error_data = json.loads(response_text)
                        print(f"HTTP 에러: {error_data}")
                    except:
                        print(f"HTTP 에러 텍스트: {response_text}")
                        
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    return False

async def main():
    print("=" * 50)
    print("캐시된 JWT 토큰으로 API 테스트")
    print("=" * 50)

    success = await test_with_cached_token()

    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: API 호출 성공!")
    else:
        print("ERROR: API 호출 실패!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
