#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9월달 실제 체결된 거래내역 조회 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import pandas as pd
from datetime import datetime, date
from config import APIConfig, KISAccountConfig
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_access_token():
    """KIS API 접근 토큰 발급 또는 캐시된 토큰 사용"""
    try:
        # 캐시된 토큰 확인
        cache_file = "data/kis_token_cache.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                token = cache_data.get("access_token")
                if token:
                    print("캐시된 토큰 사용")
                    return token

        url = f"{APIConfig.KIS_BASE_URL}/oauth2/tokenP"

        data = {
            "grant_type": "client_credentials",
            "appkey": APIConfig.KIS_APP_KEY,
            "appsecret": APIConfig.KIS_APP_SECRET
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            return result.get("access_token")
        else:
            print(f"토큰 발급 실패: {response.status_code}")
            print(response.text)
            return None

    except Exception as e:
        print(f"토큰 발급 중 오류: {e}")
        return None

def get_september_filled_orders():
    """9월달 실제 체결된 거래내역 조회"""
    try:
        print("=" * 80)
        print("KIS API를 통한 9월달 체결된 거래내역 조회")
        print("=" * 80)

        # 토큰 발급
        token = get_access_token()
        if not token:
            print("KIS API 토큰 발급 실패")
            return

        print("KIS API 토큰 발급 성공")

        # 9월 기간 설정
        start_date = "20250901"  # 2025년 9월 1일
        end_date = "20250930"    # 2025년 9월 30일

        print(f"\n기간: {start_date} ~ {end_date}")

        # API 호출 - 체결된 내역만 조회
        url = f"{APIConfig.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": APIConfig.KIS_APP_KEY,
            "appsecret": APIConfig.KIS_APP_SECRET,
            "tr_id": "TTTC0081R",  # 일별 체결조회
            "custtype": "P"  # 개인
        }

        # 계좌번호 분리
        account_parts = APIConfig.KIS_ACCOUNT_NUMBER.split('-')
        if len(account_parts) != 2:
            print(f"계좌번호 형식 오류: {APIConfig.KIS_ACCOUNT_NUMBER}")
            return

        params = {
            "CANO": account_parts[0][:8],   # 계좌번호 앞 8자리
            "ACNT_PRDT_CD": account_parts[1][-2:],  # 계좌번호 뒤 2자리
            "INQR_STRT_DT": start_date,     # 조회시작일자
            "INQR_END_DT": end_date,        # 조회종료일자
            "SLL_BUY_DVSN_CD": "00",        # 매도매수구분코드 (전체: 00)
            "INQR_DVSN": "00",              # 조회구분 (전체)
            "PDNO": "",                     # 종목번호 (전체)
            "CCLD_DVSN": "01",              # 체결구분 (체결만: 01) ★★★
            "ORD_GNO_BRNO": "",             # 주문채번지점번호
            "ODNO": "",                     # 주문번호
            "INQR_DVSN_3": "00",            # 조회구분3
            "INQR_DVSN_1": "",              # 조회구분1
            "CTX_AREA_FK100": "",           # 연속조회검색조건100
            "CTX_AREA_NK100": ""            # 연속조회키100
        }

        print("체결된 내역만 조회 (CCLD_DVSN=01)")
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()

            if data.get("rt_cd") == "0":  # 성공
                output = data.get("output1", [])

                if output:
                    print(f"\n9월달 체결된 거래내역 {len(output)}건 조회 성공")

                    # 체결 데이터 분석
                    filled_data = []
                    total_buy_amount = 0
                    total_sell_amount = 0

                    for trade in output:
                        ccld_qty = int(trade.get('ccld_qty', '0'))
                        ccld_unpr = int(trade.get('ccld_unpr', '0'))
                        ccld_amt = int(trade.get('ccld_amt', '0'))

                        if ccld_qty > 0 and ccld_unpr > 0:  # 실제 체결된 것만
                            trade_type = '매수' if trade.get('sll_buy_dvsn_cd') == '02' else '매도'

                            filled_data.append({
                                '주문일자': trade.get('ord_dt', ''),
                                '체결시간': trade.get('ord_tmd', ''),
                                '종목명': trade.get('prdt_name', ''),
                                '종목번호': trade.get('pdno', ''),
                                '매매구분': trade_type,
                                '체결수량': ccld_qty,
                                '체결단가': ccld_unpr,
                                '체결금액': ccld_amt,
                                '주문번호': trade.get('odno', ''),
                                '주문구분': trade.get('ord_dvsn_name', '')
                            })

                            # 총 금액 계산
                            if trade_type == '매수':
                                total_buy_amount += ccld_amt
                            else:
                                total_sell_amount += ccld_amt

                    if filled_data:
                        print(f"\n실제 체결된 거래: {len(filled_data)}건")
                        print("=" * 120)
                        df = pd.DataFrame(filled_data)
                        print(df.to_string(index=False))

                        # 요약 통계
                        print("\n체결 거래 요약:")
                        print("-" * 50)
                        buy_count = len([x for x in filled_data if x['매매구분'] == '매수'])
                        sell_count = len([x for x in filled_data if x['매매구분'] == '매도'])

                        print(f"총 체결 건수: {len(filled_data)}건")
                        print(f"  - 매수: {buy_count}건 (총 {total_buy_amount:,}원)")
                        print(f"  - 매도: {sell_count}건 (총 {total_sell_amount:,}원)")
                        print(f"순 거래금액: {total_sell_amount - total_buy_amount:,}원")

                        # 종목별 통계
                        print("\n종목별 체결 통계:")
                        print("-" * 60)
                        stock_summary = df.groupby(['종목명', '매매구분']).agg({
                            '체결수량': 'sum',
                            '체결금액': 'sum'
                        }).reset_index()
                        print(stock_summary.to_string(index=False))

                        # CSV 파일로 저장
                        filename = f"september_filled_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        df.to_csv(filename, index=False, encoding='utf-8-sig')
                        print(f"\n체결내역이 '{filename}' 파일로 저장되었습니다.")

                        return df

                    else:
                        print("9월달 실제 체결된 거래가 없습니다.")
                        print("(주문은 있지만 체결되지 않은 상태)")

                else:
                    print("9월달 거래내역이 없습니다.")

            else:
                error_msg = data.get("msg1", "알 수 없는 오류")
                print(f"API 호출 실패: {error_msg}")

                # 원본 응답 출력
                print(f"\n원본 응답:")
                print(json.dumps(data, indent=2, ensure_ascii=False))

        else:
            print(f"HTTP 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")

    except Exception as e:
        logger.error(f"체결내역 조회 중 오류 발생: {e}")
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    get_september_filled_orders()