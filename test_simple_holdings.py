#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 계좌 보유 종목 간단 모니터링 테스트 (인코딩 문제 해결)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent))

from data_collectors.kis_collector import KISCollector
from config import Config

class SimpleHoldingsMonitor:
    """간단한 실제 계좌 보유 종목 모니터링"""

    def __init__(self):
        self.config = Config()
        self.kis_collector = None

    async def initialize(self):
        """초기화"""
        try:
            self.kis_collector = KISCollector(self.config)
            await self.kis_collector.initialize()
            print("[SUCCESS] KIS 컬렉터 초기화 완료")
            return True
        except Exception as e:
            print(f"[ERROR] 초기화 실패: {e}")
            return False

    async def get_and_display_holdings(self):
        """실제 계좌 보유 종목 조회 및 표시"""
        try:
            print("\n=== 실제 계좌 보유 종목 조회 ===")
            print(f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # 보유 종목 조회
            holdings = await self.kis_collector.get_holdings()
            balance = await self.kis_collector.get_account_balance()

            if holdings:
                print(f"보유 종목 수: {len(holdings)}개")
                print("-" * 100)
                print(f"{'종목코드':<8} {'종목명':<15} {'보유수량':<10} {'평단가':<12} {'현재가':<12} {'평가금액':<12} {'손익률':<10}")
                print("-" * 100)

                total_evaluation = 0
                total_profit_loss = 0

                for symbol, data in holdings.items():
                    name = data['name'][:12] + '...' if len(data['name']) > 12 else data['name']
                    quantity = data['quantity']
                    avg_price = data['avg_price']
                    current_price = data['current_price']
                    evaluation = data['evaluation']
                    profit_rate = data['profit_rate']
                    profit_loss = data['profit_loss']

                    total_evaluation += evaluation
                    total_profit_loss += profit_loss

                    profit_symbol = "+" if profit_rate >= 0 else ""

                    print(f"{symbol:<8} {name:<15} {quantity:<10,} {avg_price:<12,.0f} {current_price:<12,} {evaluation:<12,} {profit_symbol}{profit_rate:<10.2f}%")

                print("-" * 100)
                print(f"총 평가금액: {total_evaluation:,}원")
                print(f"총 손익금액: {total_profit_loss:+,}원")
                print(f"총 손익률: {(total_profit_loss / (total_evaluation - total_profit_loss) * 100) if (total_evaluation - total_profit_loss) > 0 else 0:+.2f}%")

                if balance:
                    print(f"사용가능 현금: {balance.get('available_cash', 0):,}원")
                    total_assets = balance.get('available_cash', 0) + total_evaluation
                    print(f"총 자산: {total_assets:,}원")

                return holdings, balance
            else:
                print("보유 종목이 없습니다.")
                return None, balance

        except Exception as e:
            print(f"[ERROR] 보유 종목 조회 실패: {e}")
            return None, None

    async def run_periodic_monitor(self, interval_seconds=30, max_iterations=10):
        """주기적 모니터링 실행"""
        print(f"\n=== 주기적 모니터링 시작 ===")
        print(f"갱신 주기: {interval_seconds}초")
        print(f"최대 실행 횟수: {max_iterations}회")
        print("Ctrl+C로 중단 가능")

        try:
            for i in range(max_iterations):
                print(f"\n[{i+1}/{max_iterations}] 보유 종목 조회 중...")

                holdings, balance = await self.get_and_display_holdings()

                if i < max_iterations - 1:  # 마지막이 아니면 대기
                    print(f"\n{interval_seconds}초 후 다음 조회...")
                    await asyncio.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n[INFO] 사용자가 모니터링을 중단했습니다.")
        except Exception as e:
            print(f"[ERROR] 모니터링 중 오류: {e}")

async def main():
    """메인 실행 함수"""
    monitor = SimpleHoldingsMonitor()

    if await monitor.initialize():
        # 1회 조회 테스트
        holdings, balance = await monitor.get_and_display_holdings()

        if holdings:
            print("\n=== 모니터링 옵션 ===")
            print("1. 한 번만 조회")
            print("2. 주기적 모니터링 (30초마다 10회)")
            print("3. 주기적 모니터링 (사용자 설정)")

            try:
                choice = input("\n선택하세요 (1-3): ").strip()

                if choice == "2":
                    await monitor.run_periodic_monitor(30, 10)
                elif choice == "3":
                    interval = int(input("갱신 주기(초): ") or "30")
                    iterations = int(input("실행 횟수: ") or "10")
                    await monitor.run_periodic_monitor(interval, iterations)
                else:
                    print("[INFO] 1회 조회 완료")

            except (ValueError, KeyboardInterrupt):
                print("[INFO] 입력 오류 또는 사용자 중단")

        else:
            print("[ERROR] 보유 종목 조회에 실패했습니다.")
    else:
        print("[ERROR] 모니터링 시스템 초기화에 실패했습니다.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] 프로그램이 종료되었습니다.")
    except Exception as e:
        print(f"[ERROR] 프로그램 실행 중 오류: {e}")