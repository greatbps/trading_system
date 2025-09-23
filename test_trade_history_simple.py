#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
거래 이력 자동 기록 시스템 간단 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from trading.trade_history_manager import TradeHistoryManager

def test_trade_history():
    print("=" * 60)
    print("거래 이력 자동 기록 시스템 테스트")
    print("=" * 60)

    # 초기화
    trade_history_manager = TradeHistoryManager()

    # 테스트 데이터
    test_symbol = "005930"  # 삼성전자
    test_quantity = 10
    test_buy_price = 70000
    test_sell_price = 72000
    test_order_id_buy = f"TEST_BUY_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_order_id_sell = f"TEST_SELL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n테스트 데이터:")
    print(f"종목: {test_symbol}")
    print(f"수량: {test_quantity}주")
    print(f"매수가: {test_buy_price:,}원")
    print(f"매도가: {test_sell_price:,}원")

    # 종목 확인 및 추가
    print(f"\n종목 정보 확인 중...")
    stock_id = trade_history_manager._get_stock_id(test_symbol)
    if not stock_id:
        print(f"종목 {test_symbol} 추가 중...")
        try:
            with trade_history_manager.get_session() as session:
                from sqlalchemy import text
                insert_stock_query = text("""
                INSERT INTO stocks (symbol, name, market)
                VALUES (:symbol, :name, :market)
                """)
                session.execute(insert_stock_query, {
                    'symbol': test_symbol,
                    'name': '삼성전자',
                    'market': 'KOSPI'
                })
                session.commit()
                print(f"종목 {test_symbol} 추가 완료")
                stock_id = trade_history_manager._get_stock_id(test_symbol)
        except Exception as e:
            print(f"종목 추가 실패: {e}")
            return False

    print(f"종목 ID: {stock_id}")

    # 매수 거래 기록 테스트
    print(f"\n매수 거래 기록 테스트...")
    buy_success = trade_history_manager.record_buy_trade(
        symbol=test_symbol,
        quantity=test_quantity,
        price=test_buy_price,
        order_id=test_order_id_buy,
        strategy_name="test_strategy",
        trigger_reason="test_buy_signal"
    )

    if buy_success:
        print("매수 거래 기록 성공")
    else:
        print("매수 거래 기록 실패")
        return False

    # 매도 거래 기록 테스트
    print(f"\n매도 거래 기록 테스트...")
    sell_success = trade_history_manager.record_sell_trade(
        symbol=test_symbol,
        quantity=test_quantity,
        price=test_sell_price,
        order_id=test_order_id_sell,
        strategy_name="test_strategy",
        trigger_reason="test_sell_signal"
    )

    if sell_success:
        print("매도 거래 기록 성공")
    else:
        print("매도 거래 기록 실패")
        return False

    # 거래 기록 조회
    print(f"\n최근 거래 기록 조회...")
    recent_trades = trade_history_manager.get_recent_trades(5)
    if recent_trades:
        for trade in recent_trades[-2:]:  # 최근 2건만 출력
            print(f"  - {trade['symbol']} {trade['trade_type']} {trade['executed_quantity']}주 @ {trade['executed_price']:,}원")
    else:
        print("조회된 거래 기록이 없습니다.")

    # 거래 요약 통계
    print(f"\n거래 요약 통계...")
    today = datetime.now().strftime('%Y-%m-%d')
    summary = trade_history_manager.get_trading_summary(today, today)
    if summary:
        print(f"총 거래 건수: {summary.get('total_trades', 0)}건")
        print(f"매수 건수: {summary.get('buy_count', 0)}건")
        print(f"매도 건수: {summary.get('sell_count', 0)}건")

    print(f"\n거래 이력 자동 기록 시스템 테스트 완료!")
    return True

if __name__ == "__main__":
    try:
        success = test_trade_history()
        if success:
            print("\n모든 테스트 통과!")
        else:
            print("\n테스트 실패")
    except Exception as e:
        print(f"\n테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()