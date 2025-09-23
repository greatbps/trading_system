#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/execute_emergency_stop_loss.py

KIS API를 통한 실제 잔고 조회 및 손절 자동 매도 실행
"""

import os
import sys
import json
import time
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

# Windows 콘솔 인코딩 설정
if os.name == 'nt':
    os.system('chcp 65001 >nul')
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

class EmergencyStopLoss:
    def __init__(self):
        """긴급 손절 시스템 초기화"""
        self.config = Config()
        self.access_token = None
        self.stop_loss_threshold = -0.03  # -3% 손실

        print("*** 긴급 손절 시스템 시작 ***")
        print("=" * 60)

    def get_access_token(self) -> Optional[str]:
        """KIS API 접근 토큰 발급"""
        print("[토큰] KIS API 토큰 발급 중...")

        try:
            # 토큰 캐시 파일 확인
            cache_file = "data/kis_token_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)

                # 토큰이 유효한지 확인
                if cache_data.get('expires_at', 0) > time.time():
                    self.access_token = cache_data.get('access_token')
                    print("[성공] 캐시된 토큰 사용")
                    return self.access_token

            # 새 토큰 발급
            url = f"{self.config.api.KIS_BASE_URL}/oauth2/tokenP"
            headers = {
                "content-type": "application/json"
            }
            data = {
                "grant_type": "client_credentials",
                "appkey": self.config.api.KIS_APP_KEY,
                "appsecret": self.config.api.KIS_APP_SECRET
            }

            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']

                # 토큰 캐시 저장
                cache_data = {
                    'access_token': self.access_token,
                    'expires_at': time.time() + token_data.get('expires_in', 86400) - 300  # 5분 여유
                }

                os.makedirs("data", exist_ok=True)
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)

                print("[성공] 새 토큰 발급 완료")
                return self.access_token
            else:
                print(f"[오류] 토큰 발급 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"[오류] 토큰 발급 오류: {e}")
            return None

    def get_current_holdings(self) -> List[Dict[str, Any]]:
        """KIS API로 현재 보유 종목 조회"""
        print("[조회] 실제 보유 종목 조회 중...")

        if not self.access_token:
            print("[오류] 접근 토큰이 없습니다.")
            return []

        try:
            url = f"{self.config.api.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"

            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.config.api.KIS_APP_KEY,
                "appsecret": self.config.api.KIS_APP_SECRET,
                "tr_id": "TTTC8434R"
            }

            # 계좌번호에서 - 제거하고 분리
            account_no = self.config.api.KIS_ACCOUNT_NUMBER.replace("-", "")
            params = {
                "CANO": account_no[:8],
                "ACNT_PRDT_CD": account_no[8:],
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": ""
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                holdings = []

                if data.get('rt_cd') == '0':
                    output1 = data.get('output1', [])

                    for item in output1:
                        # 보유 수량이 있는 종목만 처리
                        if int(item.get('hldg_qty', '0')) > 0:
                            holdings.append({
                                'symbol': item.get('pdno', ''),
                                'name': item.get('prdt_name', ''),
                                'holding_qty': int(item.get('hldg_qty', '0')),
                                'avg_buy_price': float(item.get('pchs_avg_pric', '0')),
                                'current_price': float(item.get('prpr', '0')),
                                'eval_profit_loss': float(item.get('evlu_pfls_amt', '0')),
                                'profit_rate': float(item.get('evlu_pfls_rt', '0'))
                            })

                    print(f"[성공] 보유 종목 {len(holdings)}개 조회 완료")
                    return holdings
                else:
                    print(f"[오류] API 응답 오류: {data.get('msg1', 'Unknown error')}")
                    return []
            else:
                print(f"[오류] 보유 종목 조회 실패: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"[오류] 보유 종목 조회 오류: {e}")
            return []

    def get_current_price(self, symbol: str) -> Optional[float]:
        """종목의 현재가 조회"""
        try:
            url = f"{self.config.api.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"

            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.config.api.KIS_APP_KEY,
                "appsecret": self.config.api.KIS_APP_SECRET,
                "tr_id": "FHKST01010100"
            }

            params = {
                "FID_COND_MRKT_DIV_CD": "J",
                "FID_INPUT_ISCD": symbol
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    output = data.get('output', {})
                    return float(output.get('stck_prpr', '0'))

            return None

        except Exception as e:
            print(f"[오류] {symbol} 현재가 조회 오류: {e}")
            return None

    def place_sell_order(self, symbol: str, quantity: int, name: str = "") -> bool:
        """시장가 매도 주문 실행"""
        print(f"[주문] {symbol}({name}) {quantity}주 시장가 매도 주문 실행 중...")

        try:
            url = f"{self.config.api.KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"

            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.config.api.KIS_APP_KEY,
                "appsecret": self.config.api.KIS_APP_SECRET,
                "tr_id": "TTTC0801U",  # 현금 매도
                "custtype": "P"
            }

            # 계좌번호에서 - 제거하고 분리
            account_no = self.config.api.KIS_ACCOUNT_NUMBER.replace("-", "")
            data = {
                "CANO": account_no[:8],
                "ACNT_PRDT_CD": account_no[8:],
                "PDNO": symbol,
                "ORD_DVSN": "01",  # 시장가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": "0"    # 시장가이므로 0
            }

            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()

                if result.get('rt_cd') == '0':
                    order_no = result.get('output', {}).get('KRX_FWDG_ORD_ORGNO', 'N/A')
                    print(f"[성공] 매도 주문 성공 - 주문번호: {order_no}")
                    return True
                else:
                    error_msg = result.get('msg1', 'Unknown error')
                    print(f"[오류] 매도 주문 실패: {error_msg}")
                    return False
            else:
                print(f"[오류] 매도 주문 API 호출 실패: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"[오류] {symbol} 매도 주문 오류: {e}")
            return False

    def analyze_holdings_for_stop_loss(self, holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """보유 종목 중 손절 대상 분석"""
        print("\n[분석] 손절 대상 종목 분석 중...")
        print("-" * 60)

        stop_loss_candidates = []

        for holding in holdings:
            symbol = holding['symbol']
            name = holding['name']
            avg_buy_price = holding['avg_buy_price']
            current_price = holding['current_price']
            quantity = holding['holding_qty']
            profit_rate = holding['profit_rate'] / 100  # 퍼센트를 소수로 변환

            # 현재가 다시 확인 (더 정확한 데이터)
            real_current_price = self.get_current_price(symbol)
            if real_current_price:
                current_price = real_current_price
                # 손익률 재계산
                if avg_buy_price > 0:
                    profit_rate = (current_price - avg_buy_price) / avg_buy_price

            loss_amount = (current_price - avg_buy_price) * quantity

            print(f"\n[종목] {symbol} ({name})")
            print(f"   매수가: {avg_buy_price:,.0f}원 -> 현재가: {current_price:,.0f}원")
            print(f"   수량: {quantity:,}주")
            print(f"   손익률: {profit_rate*100:+.2f}%")
            print(f"   손익금액: {loss_amount:+,.0f}원")

            # 손절 기준 확인 (-3% 이하)
            if profit_rate <= self.stop_loss_threshold:
                stop_loss_candidates.append({
                    'symbol': symbol,
                    'name': name,
                    'avg_buy_price': avg_buy_price,
                    'current_price': current_price,
                    'quantity': quantity,
                    'profit_rate': profit_rate,
                    'loss_amount': loss_amount
                })
                print(f"   *** 손절 대상! (기준: {self.stop_loss_threshold*100:.1f}% 이하)")
            else:
                print(f"   [정상] 정상 범위")

        return stop_loss_candidates

    def execute_emergency_stop_loss(self):
        """긴급 손절 시스템 실행"""
        try:
            # 1. KIS API 토큰 발급
            if not self.get_access_token():
                print("[오류] API 토큰 발급 실패. 시스템을 종료합니다.")
                return

            # 2. 현재 보유 종목 조회
            holdings = self.get_current_holdings()
            if not holdings:
                print("[정보] 현재 보유 종목이 없습니다.")
                return

            # 3. 손절 대상 종목 분석
            stop_loss_candidates = self.analyze_holdings_for_stop_loss(holdings)

            if not stop_loss_candidates:
                print("\n[정상] 손절 대상 종목이 없습니다.")
                print(f"모든 보유 종목이 손절 기준({self.stop_loss_threshold*100:.1f}%) 이상입니다.")
                return

            # 4. 손절 대상 요약 출력
            print("\n" + "="*60)
            print("*** 긴급 손절 대상 종목 요약 ***")
            print("="*60)

            total_loss = 0
            for i, candidate in enumerate(stop_loss_candidates, 1):
                print(f"\n{i}. {candidate['symbol']} ({candidate['name']})")
                print(f"   손실률: {candidate['profit_rate']*100:+.2f}%")
                print(f"   손실금액: {candidate['loss_amount']:+,.0f}원")
                print(f"   수량: {candidate['quantity']:,}주")
                print(f"   매수가: {candidate['avg_buy_price']:,.0f}원 -> 현재가: {candidate['current_price']:,.0f}원")
                total_loss += candidate['loss_amount']

            print(f"\n[손실] 총 예상 손실: {total_loss:+,.0f}원")
            print(f"[개수] 손절 대상 종목 수: {len(stop_loss_candidates)}개")

            # 5. 자동 실행 (확인 없이)
            print("\n[실행] 자동으로 손절 매도 주문을 실행합니다...")
            print("이 작업은 되돌릴 수 없습니다!")

            # 6. 실제 매도 주문 실행
            print("\n[실행] 긴급 손절 매도 주문 실행 시작...")
            print("="*60)

            success_count = 0
            fail_count = 0

            for i, candidate in enumerate(stop_loss_candidates, 1):
                print(f"\n[{i}/{len(stop_loss_candidates)}] 매도 주문 실행 중...")

                if self.place_sell_order(
                    symbol=candidate['symbol'],
                    quantity=candidate['quantity'],
                    name=candidate['name']
                ):
                    success_count += 1
                    print(f"[성공] {candidate['symbol']} 매도 주문 성공")
                else:
                    fail_count += 1
                    print(f"[실패] {candidate['symbol']} 매도 주문 실패")

                # API 호출 간격 (초당 최대 20회 제한)
                time.sleep(0.1)

            # 7. 결과 요약
            print("\n" + "="*60)
            print("*** 긴급 손절 실행 결과 ***")
            print("="*60)
            print(f"[성공] 성공: {success_count}건")
            print(f"[실패] 실패: {fail_count}건")
            print(f"[총계] 총 시도: {len(stop_loss_candidates)}건")
            print(f"[손실] 예상 손실 금액: {total_loss:+,.0f}원")

            if success_count > 0:
                print("\n[주의사항]")
                print("- 시장가 매도 주문이므로 실제 체결가는 다를 수 있습니다.")
                print("- HTS에서 주문 체결 상황을 확인하세요.")
                print("- 체결되지 않은 주문은 수동으로 취소 또는 수정하세요.")

        except Exception as e:
            print(f"[오류] 긴급 손절 시스템 오류: {e}")
            import traceback
            traceback.print_exc()

def main():
    """메인 실행 함수"""
    try:
        emergency_system = EmergencyStopLoss()
        emergency_system.execute_emergency_stop_loss()

    except KeyboardInterrupt:
        print("\n[중단] 사용자가 중단했습니다.")
    except Exception as e:
        print(f"[오류] 시스템 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*60)
        print("*** 긴급 손절 시스템 종료 ***")
        print("="*60)

if __name__ == "__main__":
    main()