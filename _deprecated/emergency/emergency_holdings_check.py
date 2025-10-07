#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 계좌 보유 현황 확인 및 긴급 손절 대상 식별
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(override=True)

async def check_kis_holdings():
    """KIS 계좌 보유 현황 확인"""

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    base_url = "https://openapi.koreainvestment.com:9443"
    account_number = os.getenv("KIS_ACCOUNT_NUMBER", "")

    # 계좌번호 분리 (앞 8자리-뒤 2자리)
    cano = account_number[:8] if len(account_number) >= 8 else ""
    acnt_prdt_cd = account_number[8:] if len(account_number) > 8 else "01"

    print("긴급 손절 확인 시스템")
    print("=" * 50)
    print(f"APP_KEY: {app_key[:10]}...")
    print(f"계좌번호: {cano}-{acnt_prdt_cd}")
    print("")

    if not app_key or not app_secret or not account_number:
        print("KIS API 설정이 없습니다.")
        print("환경변수를 확인하세요: KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NUMBER")
        return

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Access Token 발급
            print("[1] Access Token 발급 중...")

            auth_url = f"{base_url}/oauth2/Approval"
            auth_payload = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "secretkey": app_secret
            }

            auth_headers = {
                'Content-Type': 'application/json; charset=utf-8'
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(auth_url, json=auth_payload, headers=auth_headers, timeout=timeout) as response:
                if response.status != 200:
                    print(f"토큰 발급 실패: {response.status}")
                    return

                auth_data = await response.json()
                access_token = auth_data.get("access_token")

                if not access_token:
                    print("Access Token 없음")
                    return

                print(f"토큰 발급 성공: {access_token[:20]}...")

            # 2. 보유 종목 조회
            print("\n[2] 보유 종목 조회 중...")

            holdings_url = f"{base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

            holdings_headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'authorization': f'Bearer {access_token}',
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'TTTC8434R',  # 실거래용
                'custtype': 'P'  # 개인
            }

            holdings_params = {
                'CANO': cano,
                'ACNT_PRDT_CD': acnt_prdt_cd,
                'AFHR_FLPR_YN': 'N',  # 시간외호가포함여부
                'OFL_YN': '',         # 오프라인여부
                'INQR_DVSN': '02',    # 조회구분: 02(일반)
                'UNPR_DVSN': '01',    # 단가구분: 01(기본)
                'FUND_STTL_ICLD_YN': 'N',  # 펀드결제분포함여부
                'FNCG_AMT_AUTO_RDPT_YN': 'N',  # 융자금액자동상환여부
                'PRCS_DVSN': '00',    # 처리구분
                'CTX_AREA_FK100': '',  # 연속조회검색조건100
                'CTX_AREA_NK100': ''   # 연속조회키100
            }

            async with session.get(holdings_url, headers=holdings_headers, params=holdings_params, timeout=timeout) as response:
                if response.status != 200:
                    print(f"보유종목 조회 실패: {response.status}")
                    text = await response.text()
                    print(f"응답: {text}")
                    return

                holdings_data = await response.json()

                if holdings_data.get('rt_cd') != '0':
                    print(f"API 오류: {holdings_data.get('msg1', '알 수 없는 오류')}")
                    return

                output1 = holdings_data.get('output1', [])
                output2 = holdings_data.get('output2', [])

                print(f"보유 종목 수: {len(output1)}개")

                if not output1:
                    print("현재 보유 종목이 없습니다.")
                    return

                # 3. 손절 대상 확인
                print("\n[3] 손절 대상 확인")
                print("-" * 50)

                stop_loss_threshold = -3.0  # -3% 손절 기준
                emergency_candidates = []

                for holding in output1:
                    symbol = holding.get('pdno', '')  # 종목코드
                    name = holding.get('prdt_name', '')  # 종목명
                    quantity = int(holding.get('hldg_qty', 0))  # 보유수량
                    avg_price = float(holding.get('pchs_avg_pric', 0))  # 매입평균단가
                    current_price = float(holding.get('prpr', 0))  # 현재가
                    eval_amt = int(holding.get('evlu_amt', 0))  # 평가금액
                    eval_pfls_amt = int(holding.get('evlu_pfls_amt', 0))  # 평가손익금액
                    eval_pfls_rt = float(holding.get('evlu_pfls_rt', 0))  # 평가손익률

                    if quantity <= 0:
                        continue

                    print(f"{symbol} ({name})")
                    print(f"  보유수량: {quantity:,}주")
                    print(f"  매입평균: {avg_price:,.0f}원")
                    print(f"  현재가: {current_price:,.0f}원")
                    print(f"  평가금액: {eval_amt:,}원")
                    print(f"  평가손익: {eval_pfls_amt:+,}원 ({eval_pfls_rt:+.2f}%)")

                    # 손절 대상 확인
                    if eval_pfls_rt <= stop_loss_threshold:
                        emergency_candidates.append({
                            'symbol': symbol,
                            'name': name,
                            'quantity': quantity,
                            'avg_price': avg_price,
                            'current_price': current_price,
                            'eval_amt': eval_amt,
                            'loss_amt': eval_pfls_amt,
                            'loss_rate': eval_pfls_rt,
                            'urgency': 'HIGH' if eval_pfls_rt <= -5.0 else 'MEDIUM'
                        })
                        print(f"  *** 긴급 손절 대상! ***")
                    else:
                        print(f"  정상 범위")

                    print()

                # 4. 긴급 조치 안내
                if emergency_candidates:
                    print("*** 긴급 손절 대상 종목 ***")
                    print("=" * 50)

                    total_loss = 0
                    for i, candidate in enumerate(emergency_candidates, 1):
                        print(f"{i}. {candidate['symbol']} ({candidate['name']})")
                        print(f"   보유수량: {candidate['quantity']:,}주")
                        print(f"   손실률: {candidate['loss_rate']:.2f}%")
                        print(f"   손실금액: {candidate['loss_amt']:,}원")
                        print(f"   시급도: {candidate['urgency']}")
                        total_loss += candidate['loss_amt']
                        print()

                    print(f"총 손실금액: {total_loss:,}원")
                    print()

                    print("즉시 실행 권장:")
                    print("1. KIS HTS/MTS 접속")
                    print("2. 위 종목들 시장가 매도")
                    print("3. 매도 체결 확인")
                    print()

                    # 자동 매도 제안
                    response = input("자동 시장가 매도를 실행하시겠습니까? (y/N): ")
                    if response.lower() == 'y':
                        await execute_emergency_sell_orders(session, emergency_candidates,
                                                          access_token, app_key, app_secret,
                                                          cano, acnt_prdt_cd, base_url)
                    else:
                        print("수동 매도를 권장합니다.")
                else:
                    print("손절이 필요한 종목이 없습니다.")
                    print("모든 보유 종목이 손절 기준(-3%) 이내입니다.")

        except Exception as e:
            print(f"오류 발생: {e}")


async def execute_emergency_sell_orders(session, candidates, access_token, app_key, app_secret,
                                      cano, acnt_prdt_cd, base_url):
    """긴급 매도 주문 실행"""

    print("\n긴급 매도 주문 실행 중...")
    print("=" * 50)

    for candidate in candidates:
        symbol = candidate['symbol']
        quantity = candidate['quantity']
        name = candidate['name']

        print(f"매도 주문: {symbol} ({name}) {quantity}주")

        try:
            # 매도 주문 API 호출
            sell_url = f"{base_url}/uapi/domestic-stock/v1/trading/order-cash"

            sell_headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'authorization': f'Bearer {access_token}',
                'appkey': app_key,
                'appsecret': app_secret,
                'tr_id': 'TTTC0801U',  # 현금 매도 주문
                'custtype': 'P',
                'hashkey': ''  # 실제로는 해시키 생성 필요
            }

            sell_payload = {
                'CANO': cano,
                'ACNT_PRDT_CD': acnt_prdt_cd,
                'PDNO': symbol,
                'ORD_DVSN': '01',  # 시장가
                'ORD_QTY': str(quantity),
                'ORD_UNPR': '0'  # 시장가는 0
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(sell_url, json=sell_payload, headers=sell_headers, timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('rt_cd') == '0':
                        order_no = result.get('output', {}).get('ODNO', '')
                        print(f"  매도 주문 성공: 주문번호 {order_no}")
                    else:
                        print(f"  매도 주문 실패: {result.get('msg1', '알 수 없는 오류')}")
                else:
                    print(f"  매도 주문 오류: HTTP {response.status}")

            # 주문 간격
            await asyncio.sleep(1)

        except Exception as e:
            print(f"  {symbol} 매도 오류: {e}")

    print("\n긴급 매도 주문 완료")


if __name__ == "__main__":
    asyncio.run(check_kis_holdings())