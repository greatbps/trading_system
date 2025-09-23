#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 손절 주문 실행 스크립트
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.logger import get_logger
from data_collectors.kis_collector import KISCollector

class StopLossExecutor:
    """손절 주문 실행기"""

    def __init__(self):
        self.logger = get_logger("StopLossExecutor")

        # config를 APIConfig 객체로 변환
        class ConfigWrapper:
            def __init__(self):
                self.api = config.APIConfig()

        self.config = ConfigWrapper()
        self.kis_collector = KISCollector(self.config)

        # 손절 기준 (3% 손실)
        self.stop_loss_threshold = -0.03

    async def get_holdings_with_stop_loss_check(self) -> List[Dict]:
        """보유종목 조회 및 손절 대상 식별"""
        try:
            holdings = await self.kis_collector.get_holdings()

            if not holdings:
                self.logger.warning("보유종목이 없습니다.")
                return []

            stop_loss_candidates = []

            for symbol, data in holdings.items():
                profit_rate = data.get('profit_rate', 0) / 100  # 퍼센트를 소수로 변환

                if profit_rate <= self.stop_loss_threshold:
                    candidate = {
                        'symbol': symbol,
                        'name': data.get('name', ''),
                        'quantity': data.get('quantity', 0),
                        'avg_price': data.get('avg_price', 0),
                        'current_price': data.get('current_price', 0),
                        'profit_rate': profit_rate,
                        'profit_loss': data.get('profit_loss', 0),
                        'evaluation': data.get('evaluation', 0)
                    }
                    stop_loss_candidates.append(candidate)

            return stop_loss_candidates

        except Exception as e:
            self.logger.error(f"보유종목 조회 실패: {e}")
            return []

    async def execute_sell_order(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """매도 주문 실행"""
        try:
            self.logger.info(f"매도 주문 실행: {symbol} {quantity}주")

            # KIS API 매도 주문 (시장가)
            result = await self.kis_collector.place_order(
                symbol=symbol,
                quantity=quantity,
                price=0,  # 시장가
                order_type="01",  # 시장가
                side="SELL"  # 매도
            )

            if result.get('success'):
                self.logger.info(f"✅ 매도 주문 성공: {symbol} - 주문번호: {result.get('order_id', 'N/A')}")
                return {
                    'success': True,
                    'symbol': symbol,
                    'quantity': quantity,
                    'order_id': result.get('order_id'),
                    'message': '매도 주문 성공'
                }
            else:
                self.logger.error(f"❌ 매도 주문 실패: {symbol} - {result.get('error', '알 수 없는 오류')}")
                return {
                    'success': False,
                    'symbol': symbol,
                    'quantity': quantity,
                    'error': result.get('error', '알 수 없는 오류')
                }

        except Exception as e:
            self.logger.error(f"매도 주문 오류: {symbol} - {e}")
            return {
                'success': False,
                'symbol': symbol,
                'quantity': quantity,
                'error': str(e)
            }

    async def execute_stop_loss_orders(self) -> Dict[str, Any]:
        """손절 주문 일괄 실행"""
        try:
            print("Stop Loss Order Execution Started")
            print("=" * 60)

            # 1. 손절 대상 종목 조회
            candidates = await self.get_holdings_with_stop_loss_check()

            if not candidates:
                print("No stocks meet stop loss criteria.")
                return {'total_orders': 0, 'successful_orders': 0, 'results': []}

            print(f"Stop loss candidates: {len(candidates)} stocks")
            print("-" * 60)

            # 각 종목 정보 출력
            for i, candidate in enumerate(candidates, 1):
                print(f"{i}. {candidate['symbol']} ({candidate['name']})")
                print(f"   Quantity: {candidate['quantity']} shares")
                print(f"   Avg Price: {candidate['avg_price']:,} won")
                print(f"   Current Price: {candidate['current_price']:,} won")
                print(f"   Loss Rate: {candidate['profit_rate']*100:.2f}%")
                print(f"   Loss Amount: {candidate['profit_loss']:,} won")
                print()

            # 사용자 확인
            print("Do you want to sell these stocks at market price?")
            confirm = input("Type 'YES' to execute: ")

            if confirm != 'YES':
                print("Stop loss orders cancelled.")
                return {'total_orders': 0, 'successful_orders': 0, 'results': []}

            print("\nExecuting stop loss orders...")
            print("-" * 60)

            # 2. 매도 주문 실행
            results = []
            successful_count = 0

            for candidate in candidates:
                print(f"Sell Order: {candidate['symbol']} {candidate['quantity']} shares...")

                result = await self.execute_sell_order(
                    candidate['symbol'],
                    candidate['quantity']
                )

                result.update({
                    'name': candidate['name'],
                    'profit_rate': candidate['profit_rate'],
                    'profit_loss': candidate['profit_loss']
                })

                results.append(result)

                if result['success']:
                    successful_count += 1
                    print(f"SUCCESS: {candidate['symbol']}")
                else:
                    print(f"FAILED: {candidate['symbol']} - {result['error']}")

                # 주문 간격 (API 호출 제한 고려)
                await asyncio.sleep(1)

            # 3. 결과 요약
            print("\n" + "=" * 60)
            print("Stop Loss Order Execution Results")
            print("=" * 60)
            print(f"Total Orders: {len(results)}")
            print(f"Successful: {successful_count}")
            print(f"Failed: {len(results) - successful_count}")
            print()

            # 실패한 주문이 있으면 상세 출력
            failed_orders = [r for r in results if not r['success']]
            if failed_orders:
                print("Failed Orders:")
                for order in failed_orders:
                    print(f"- {order['symbol']}: {order['error']}")
                print()

            print("Next Steps:")
            print("1. Check order execution in KIS account")
            print("2. Verify balance and transaction history")
            print("3. Analyze and record stop loss reasons")

            return {
                'total_orders': len(results),
                'successful_orders': successful_count,
                'results': results
            }

        except Exception as e:
            self.logger.error(f"Stop loss order execution failed: {e}")
            print(f"Error occurred: {e}")
            return {'total_orders': 0, 'successful_orders': 0, 'results': []}

async def main():
    """메인 실행 함수"""
    executor = StopLossExecutor()

    print("Stop Loss Order Executor Started")
    print(f"Stop Loss Threshold: {executor.stop_loss_threshold*100:.1f}% or more loss")
    print("=" * 60)

    result = await executor.execute_stop_loss_orders()

    print("=" * 60)
    print(f"Stop Loss Execution Complete: {result['successful_orders']}/{result['total_orders']} successful")

if __name__ == "__main__":
    asyncio.run(main())