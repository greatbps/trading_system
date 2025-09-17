#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 간단한 인증 및 API 테스트
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def test_simple_kis_auth():
    """간단한 KIS 인증 및 API 호출 테스트"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"
    account_number = os.getenv("KIS_ACCOUNT_NUMBER", "")

    print("[KIS 간단 인증 테스트]")
    print(f"APP_KEY: {app_key[:10]}...")
    print(f"BASE_URL: {base_url}")
    print(f"ACCOUNT: {account_number}")
    print("")

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Approval Key 요청 (이것이 실제 access_token)
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
                'User-Agent': 'TradingSystem/2.0'
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                response_text = await response.text()

                if response.status == 200:
                    result = json.loads(response_text)
                    access_token = result['approval_key']  # 이것이 실제 access_token
                    print(f"SUCCESS: Access token 획득: {access_token[:8]}...")

                    # 2. 간단한 API 호출로 토큰 검증
                    print("\n[2] 토큰 검증 - 주식현재가 조회...")

                    api_endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
                    api_url = f"{base_url}{api_endpoint}"

                    api_headers = {
                        'Authorization': f'Bearer {access_token}',
                        'appkey': app_key,
                        'appsecret': app_secret,
                        'tr_id': 'FHKST01010100',
                        'custtype': 'P',
                        'Content-Type': 'application/json; charset=utf-8'
                    }

                    api_params = {
                        'fid_cond_mrkt_div_code': 'J',
                        'fid_input_iscd': '005930'  # 삼성전자
                    }

                    async with session.get(api_url, headers=api_headers, params=api_params, timeout=timeout) as api_response:
                        api_response_text = await api_response.text()

                        print(f"주식현재가 조회 응답: {api_response.status}")
                        print(f"응답 내용 (처음 300자): {api_response_text[:300]}")

                        if api_response.status == 200:
                            print("SUCCESS: 주식현재가 조회 성공!")
                        else:
                            print(f"ERROR: 주식현재가 조회 실패")

                    # 3. 계좌 잔고 조회로 추가 검증
                    if account_number:
                        print("\n[3] 계좌 잔고 조회...")

                        balance_endpoint = "/uapi/domestic-stock/v1/trading/inquire-balance"
                        balance_url = f"{base_url}{balance_endpoint}"

                        balance_headers = {
                            'Authorization': f'Bearer {access_token}',
                            'appkey': app_key,
                            'appsecret': app_secret,
                            'tr_id': 'TTTC8434R',
                            'custtype': 'P',
                            'Content-Type': 'application/json; charset=utf-8'
                        }

                        cano, acnt_prdt_cd = account_number.split('-')
                        balance_params = {
                            'CANO': cano,
                            'ACNT_PRDT_CD': acnt_prdt_cd,
                            'AFHR_FLPR_YN': 'N',
                            'OFL_YN': '',
                            'INQR_DVSN': '02',
                            'UNPR_DVSN': '01',
                            'FUND_STTL_ICLD_YN': 'N',
                            'FNCG_AMT_AUTO_RDPT_YN': 'N',
                            'PRCS_DVSN': '01',
                            'CTX_AREA_FK100': '',
                            'CTX_AREA_NK100': ''
                        }

                        async with session.get(balance_url, headers=balance_headers, params=balance_params, timeout=timeout) as balance_response:
                            balance_response_text = await balance_response.text()

                            print(f"계좌잔고 조회 응답: {balance_response.status}")
                            print(f"응답 내용 (처음 300자): {balance_response_text[:300]}")

                            if balance_response.status == 200:
                                print("SUCCESS: 계좌잔고 조회 성공!")
                                return True
                            else:
                                print(f"ERROR: 계좌잔고 조회 실패")
                                return False
                    else:
                        print("INFO: 계좌번호 없음, 주식현재가 조회 결과만 확인")
                        return api_response.status == 200

                else:
                    print(f"ERROR: Approval key 요청 실패: {response.status}")
                    print(f"응답: {response_text}")
                    return False

        except Exception as e:
            print(f"ERROR: 예외 발생: {e}")
            return False

async def main():
    print("=" * 60)
    print("KIS API 간단 인증 및 토큰 검증 테스트")
    print("=" * 60)

    success = await test_simple_kis_auth()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 전체 테스트 성공!")
    else:
        print("ERROR: 테스트 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())