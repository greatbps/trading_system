#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자동 손절 실행 스크립트 (확인 없이 바로 실행)
"""

import sys
import os
import time
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.kis_api import KISAPI
from config import KIS_CONFIG

class AutoStopLossExecutor:
    def __init__(self):
        """자동 손절 실행기 초기화"""
        self.kis_api = KISAPI(KIS_CONFIG)

    def get_portfolio(self):
        """실제 보유 종목 조회"""
        try:
            portfolio_data = self.kis_api.get_balance()
            portfolio = []

            if portfolio_data and portfolio_data.get('output1'):
                for item in portfolio_data['output1']:
                    if int(item.get('hldg_qty', 0)) > 0:
                        portfolio.append({
                            'symbol': item['pdno'],
                            'name': item['prdt_name'],
                            'quantity': int(item['hldg_qty']),
                            'avg_price': float(item['pchs_avg_pric']),
                            'current_price': float(item['prpr']),
                            'profit_loss_rate': float(item['evlu_pfls_rt']),
                            'profit_loss_amount': int(item['evlu_pfls_amt'])
                        })

            return portfolio

        except Exception as e:
            print(f"[오류] 포트폴리오 조회 실패: {e}")
            return []

    def place_sell_order(self, symbol, quantity, name):
        """시장가 매도 주문"""
        try:
            order_data = {
                'CANO': KIS_CONFIG['CANO'],
                'ACNT_PRDT_CD': KIS_CONFIG['ACNT_PRDT_CD'],
                'PDNO': symbol,
                'ORD_DVSN': '01',  # 시장가
                'ORD_QTY': str(quantity),
                'ORD_UNPR': '0'
            }

            response = self.kis_api.place_order(order_data, is_buy=False)

            if response and response.get('rt_cd') == '0':
                print(f"[성공] {symbol}({name}) {quantity}주 매도 주문 완료")
                return True
            else:
                error_msg = response.get('msg1', '알 수 없는 오류') if response else '응답 없음'
                print(f"[실패] {symbol}({name}) 매도 주문 실패: {error_msg}")
                return False

        except Exception as e:
            print(f"[오류] {symbol}({name}) 매도 주문 예외: {e}")
            return False

    def execute_auto_stop_loss(self):
        """자동 손절 실행 (확인 없이)"""
        try:
            print("*** 자동 손절 시스템 시작 ***")
            print("="*60)

            # 1. 토큰 발급
            print("[토큰] KIS API 토큰 발급 중...")
            token_result = self.kis_api.get_access_token()
            if not token_result:
                print("[오류] 토큰 발급 실패")
                return
            print("[성공] 새 토큰 발급 완료")

            # 2. 보유 종목 조회
            print("[조회] 실제 보유 종목 조회 중...")
            portfolio = self.get_portfolio()

            if not portfolio:
                print("[정보] 보유 종목이 없습니다.")
                return

            print(f"[성공] 보유 종목 {len(portfolio)}개 조회 완료")

            # 3. 손절 대상 분석
            print("\n[분석] 손절 대상 종목 분석 중...")
            print("-"*60)

            stop_loss_candidates = []
            total_loss = 0

            for stock in portfolio:
                profit_loss_rate = stock['profit_loss_rate']

                print(f"\n[종목] {stock['symbol']} ({stock['name']})")
                print(f"   매수가: {stock['avg_price']:,.0f}원 -> 현재가: {stock['current_price']:,.0f}원")
                print(f"   수량: {stock['quantity']}주")
                print(f"   손익률: {profit_loss_rate:+.2f}%")
                print(f"   손익금액: {stock['profit_loss_amount']:+,.0f}원")

                # 손절 기준: -3.0% 이하
                if profit_loss_rate <= -3.0:
                    stop_loss_candidates.append(stock)
                    total_loss += stock['profit_loss_amount']
                    print(f"   *** 손절 대상! (기준: -3.0% 이하)")
                else:
                    print(f"   [정상] 정상 범위")

            # 4. 손절 대상이 없으면 종료
            if not stop_loss_candidates:
                print("\n[정보] 손절 대상 종목이 없습니다.")
                return

            # 5. 손절 대상 요약
            print("\n" + "="*60)
            print("*** 자동 손절 대상 종목 요약 ***")
            print("="*60)

            for i, stock in enumerate(stop_loss_candidates, 1):
                print(f"\n{i}. {stock['symbol']} ({stock['name']})")
                print(f"   손실률: {stock['profit_loss_rate']:.2f}%")
                print(f"   손실금액: {stock['profit_loss_amount']:+,.0f}원")
                print(f"   수량: {stock['quantity']}주")
                print(f"   매수가: {stock['avg_price']:,.0f}원 -> 현재가: {stock['current_price']:,.0f}원")

            print(f"\n[손실] 총 예상 손실: {total_loss:+,.0f}원")
            print(f"[개수] 손절 대상 종목 수: {len(stop_loss_candidates)}개")

            # 6. 자동 실행 (확인 없이)
            print("\n[실행] 자동 손절 매도 주문 실행 시작...")
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
                else:
                    fail_count += 1

                # API 호출 간격
                time.sleep(0.1)

            # 7. 결과 요약
            print("\n" + "="*60)
            print("*** 자동 손절 실행 결과 ***")
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
            print(f"[오류] 자동 손절 시스템 오류: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("\n" + "="*60)
            print("*** 자동 손절 시스템 종료 ***")
            print("="*60)

def main():
    """메인 함수"""
    executor = AutoStopLossExecutor()
    executor.execute_auto_stop_loss()

if __name__ == "__main__":
    main()