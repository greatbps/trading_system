#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/quick_emergency_stop_loss.py

간단한 긴급 손절 스크립트 (의존성 최소화)
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Any

def check_emergency_stop_loss():
    """긴급 손절 대상 확인"""

    print("긴급 손절 시스템 시작")
    print("=" * 50)

    try:
        # DB 연결
        conn = sqlite3.connect("trading_system.db")
        cursor = conn.cursor()

        # 1. 현재 보유 포지션 확인
        cursor.execute("""
            SELECT
                symbol, name, buy_price, holding_quantity,
                current_price, profit_loss, profit_rate,
                buy_time, target_price, stop_loss_price
            FROM monitoring_stocks
            WHERE status = 'ACTIVE'
            AND holding_quantity > 0
            ORDER BY profit_rate ASC
        """)

        positions = cursor.fetchall()

        if not positions:
            print("현재 보유 포지션이 없습니다.")
            return

        print(f"현재 보유 포지션: {len(positions)}개")
        print("-" * 50)

        # 2. 손절 기준 (3% 손실)
        stop_loss_threshold = -0.03  # -3%
        emergency_candidates = []

        for pos in positions:
            symbol, name, buy_price, quantity, current_price, profit_loss, profit_rate = pos[:7]

            if buy_price and current_price and quantity:
                # 현재 손실률 계산
                actual_loss_rate = (current_price - buy_price) / buy_price
                loss_percentage = actual_loss_rate * 100
                loss_amount = (current_price - buy_price) * quantity

                print(f"{symbol} ({name})")
                print(f"   매수가: {buy_price:,}원 -> 현재가: {current_price:,}원")
                print(f"   수량: {quantity}주")
                print(f"   손익률: {loss_percentage:.2f}%")
                print(f"   손익금액: {loss_amount:,}원")

                # 손절 대상 확인
                if actual_loss_rate <= stop_loss_threshold:
                    emergency_candidates.append({
                        'symbol': symbol,
                        'name': name,
                        'buy_price': buy_price,
                        'current_price': current_price,
                        'quantity': quantity,
                        'loss_rate': actual_loss_rate,
                        'loss_percentage': loss_percentage,
                        'loss_amount': loss_amount
                    })

                    print(f"   *** 손절 대상! (기준: {stop_loss_threshold*100:.1f}%)")
                else:
                    print(f"   정상 범위")

                print()

        # 3. 긴급 손절 대상 요약
        if emergency_candidates:
            print("*** 긴급 손절 대상 종목 ***")
            print("=" * 50)

            total_loss = 0
            for i, candidate in enumerate(emergency_candidates, 1):
                print(f"{i}. {candidate['symbol']} ({candidate['name']})")
                print(f"   손실률: {candidate['loss_percentage']:.2f}%")
                print(f"   손실금액: {candidate['loss_amount']:,}원")
                print(f"   수량: {candidate['quantity']}주")
                total_loss += candidate['loss_amount']
                print()

            print(f"총 예상 손실: {total_loss:,}원")
            print()

            # 4. 사용자 확인
            print("실제 매도 주문을 실행하려면 다음 단계를 수행하세요:")
            print("1. KIS 계좌에 로그인하여 실제 보유 종목 확인")
            print("2. 각 종목의 현재가 재확인")
            print("3. 수동으로 시장가 매도 주문 실행")
            print()
            print("자동 매도를 원한다면 KIS API 연동이 필요합니다.")

            # 5. 모니터링 상태 업데이트 (선택사항)
            response = input("모니터링 DB에서 해당 종목들을 완료 상태로 변경하시겠습니까? (y/N): ")

            if response.lower() == 'y':
                for candidate in emergency_candidates:
                    cursor.execute("""
                        UPDATE monitoring_stocks
                        SET status = 'COMPLETED',
                            remove_reason = ?,
                            updated_at = ?
                        WHERE symbol = ? AND status = 'ACTIVE'
                    """, (
                        f"긴급손절: {candidate['loss_percentage']:.2f}% 손실",
                        datetime.now(),
                        candidate['symbol']
                    ))

                conn.commit()
                print("모니터링 상태가 업데이트되었습니다.")

        else:
            print("손절 대상 종목이 없습니다.")
            print("모든 포지션이 손절 기준(-3%) 이내입니다.")

        conn.close()

    except Exception as e:
        print(f"오류 발생: {e}")

    print("=" * 50)
    print("긴급 손절 확인 완료")

if __name__ == "__main__":
    check_emergency_stop_loss()