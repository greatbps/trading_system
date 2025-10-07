#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/check_actual_holdings.py

실제 KIS 계좌 보유 현황 확인 및 긴급 손절 대상 식별
"""

import asyncio
import os
import sys
from datetime import datetime

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.logger import get_logger
from data_collectors.kis_collector import KISCollector

class ActualHoldingsChecker:
    """실제 계좌 보유 현황 확인기"""

    def __init__(self):
        self.logger = get_logger("ActualHoldingsChecker")
        self.config = config

        # 손절 기준
        self.stop_loss_ratio = getattr(config.TradingConfig, 'STOP_LOSS_RATIO', 0.03)  # 3%

        # KIS API 수집기
        try:
            # config를 APIConfig 객체로 변환
            class ConfigWrapper:
                def __init__(self):
                    self.api = config.APIConfig()

            wrapped_config = ConfigWrapper()
            self.kis_collector = KISCollector(wrapped_config)
            self.logger.info("KIS Collector 초기화 완료")
        except Exception as e:
            self.logger.error(f"KIS Collector 초기화 실패: {e}")
            self.kis_collector = None

    async def get_account_balance(self):
        """계좌 잔고 조회"""
        try:
            if not self.kis_collector:
                print("KIS API 연결 실패 - 계좌 조회 불가")
                return None

            print("계좌 잔고 조회 중...")
            balance_info = await self.kis_collector.get_account_balance()

            if balance_info:
                print(f"매수가능금액: {balance_info.get('available_cash', 0):,}원")
                print(f"총 자산: {balance_info.get('total_assets', 0):,}원")
                print(f"주식 평가금액: {balance_info.get('stock_value', 0):,}원")
                return balance_info
            else:
                print("계좌 정보 조회 실패")
                return None

        except Exception as e:
            print(f"계좌 조회 오류: {e}")
            return None

    async def get_current_holdings(self):
        """현재 보유 종목 조회"""
        try:
            if not self.kis_collector:
                print("KIS API 연결 실패 - 보유 종목 조회 불가")
                return []

            print("보유 종목 조회 중...")
            holdings = await self.kis_collector.get_holdings()

            if holdings:
                print(f"보유 종목 수: {len(holdings)}개")
                return holdings
            else:
                print("보유 종목 없음")
                return []

        except Exception as e:
            print(f"보유 종목 조회 오류: {e}")
            return []

    async def check_stop_loss_candidates(self, holdings):
        """손절 대상 확인"""
        try:
            if not holdings:
                print("손절 확인할 보유 종목이 없습니다.")
                return []

            print(f"\n손절 기준: {self.stop_loss_ratio * 100:.1f}% 손실")
            print("=" * 60)

            stop_loss_candidates = []

            for holding in holdings:
                symbol = holding.get('symbol', '')
                name = holding.get('name', '')
                quantity = int(holding.get('quantity', 0))
                avg_price = int(holding.get('avg_price', 0))
                current_price = int(holding.get('current_price', 0))

                if quantity <= 0 or avg_price <= 0 or current_price <= 0:
                    continue

                # 손익률 계산
                profit_loss = current_price - avg_price
                profit_rate = (profit_loss / avg_price) * 100
                total_profit_loss = profit_loss * quantity
                market_value = current_price * quantity

                print(f"{symbol} ({name})")
                print(f"  수량: {quantity:,}주")
                print(f"  평균단가: {avg_price:,}원")
                print(f"  현재가: {current_price:,}원")
                print(f"  손익률: {profit_rate:+.2f}%")
                print(f"  손익금액: {total_profit_loss:+,}원")
                print(f"  평가금액: {market_value:,}원")

                # 손절 대상 확인
                if profit_rate <= -self.stop_loss_ratio * 100:
                    candidate = {
                        'symbol': symbol,
                        'name': name,
                        'quantity': quantity,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'profit_rate': profit_rate,
                        'total_profit_loss': total_profit_loss,
                        'market_value': market_value,
                        'urgency': 'HIGH' if profit_rate <= -5.0 else 'MEDIUM'
                    }
                    stop_loss_candidates.append(candidate)
                    print(f"  *** 손절 대상! ***")
                else:
                    print(f"  정상 범위")

                print()

            return stop_loss_candidates

        except Exception as e:
            print(f"손절 대상 확인 오류: {e}")
            return []

    def display_emergency_action_plan(self, candidates):
        """긴급 조치 계획 출력"""
        if not candidates:
            print("현재 손절이 필요한 종목이 없습니다.")
            return

        print("*** 긴급 손절 대상 종목 ***")
        print("=" * 60)

        total_loss = 0
        for i, candidate in enumerate(candidates, 1):
            print(f"{i}. {candidate['symbol']} ({candidate['name']})")
            print(f"   수량: {candidate['quantity']:,}주")
            print(f"   손실률: {candidate['profit_rate']:.2f}%")
            print(f"   손실금액: {candidate['total_profit_loss']:,}원")
            print(f"   시급도: {candidate['urgency']}")
            total_loss += candidate['total_profit_loss']
            print()

        print(f"총 예상 손실: {total_loss:,}원")
        print()

        print("즉시 실행 권장사항:")
        print("1. KIS HTS/MTS에 로그인")
        print("2. 위 종목들의 현재가 재확인")
        print("3. 시장가 매도 주문 즉시 실행")
        print("4. 매도 체결 확인")
        print()

        print("자동 매도 실행:")
        print("- 이 스크립트로 자동 매도 가능")
        print("- KIS API 인증 및 거래 권한 필요")

    async def run_emergency_check(self):
        """긴급 손절 확인 실행"""
        try:
            print("긴급 손절 확인 시작")
            print("=" * 60)

            # 1. 계좌 잔고 확인
            balance = await self.get_account_balance()

            # 2. 보유 종목 조회
            holdings = await self.get_current_holdings()

            # 3. 손절 대상 확인
            candidates = await self.check_stop_loss_candidates(holdings)

            # 4. 긴급 조치 계획 출력
            self.display_emergency_action_plan(candidates)

            print("=" * 60)
            print("긴급 손절 확인 완료")

            return candidates

        except Exception as e:
            print(f"긴급 확인 실행 오류: {e}")
            return []


async def main():
    """메인 실행 함수"""
    checker = ActualHoldingsChecker()
    await checker.run_emergency_check()


if __name__ == "__main__":
    asyncio.run(main())