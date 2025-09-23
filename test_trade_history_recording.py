#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
거래 이력 자동 기록 시스템 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from datetime import datetime
from trading.trade_history_manager import TradeHistoryManager
import pandas as pd

def test_trade_history_manager():
    """거래 이력 관리자 테스트"""
    print("=" * 80)
    print("🧪 거래 이력 자동 기록 시스템 테스트")
    print("=" * 80)

    # 초기화
    trade_history_manager = TradeHistoryManager()

    # 테스트 데이터
    test_symbol = "005930"  # 삼성전자
    test_quantity = 10
    test_buy_price = 70000
    test_sell_price = 72000
    test_order_id_buy = f"TEST_BUY_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_order_id_sell = f"TEST_SELL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n📊 테스트 데이터:")
    print(f"종목: {test_symbol} (삼성전자)")
    print(f"수량: {test_quantity}주")
    print(f"매수가: {test_buy_price:,}원")
    print(f"매도가: {test_sell_price:,}원")
    print(f"예상 수익: {(test_sell_price - test_buy_price) * test_quantity:,}원")

    # 1. 먼저 종목이 stocks 테이블에 있는지 확인하고 없으면 추가
    print(f"\n🔍 종목 정보 확인 중...")
    stock_id = trade_history_manager._get_stock_id(test_symbol)
    if not stock_id:
        print(f"⚠️ 종목 {test_symbol}이 stocks 테이블에 없습니다. 수동으로 추가하겠습니다.")
        try:
            with trade_history_manager.get_session() as session:
                # 종목 정보 추가
                insert_stock_query = """
                INSERT INTO stocks (symbol, name, market)
                VALUES (:symbol, :name, :market)
                """
                session.execute(insert_stock_query, {
                    'symbol': test_symbol,
                    'name': '삼성전자',
                    'market': 'KOSPI'
                })
                session.commit()
                print(f"✅ 종목 {test_symbol} 추가 완료")
                stock_id = trade_history_manager._get_stock_id(test_symbol)
        except Exception as e:
            print(f"❌ 종목 추가 실패: {e}")
            return False

    print(f"✅ 종목 ID: {stock_id}")

    # 2. 매수 거래 기록 테스트
    print(f"\n💰 매수 거래 기록 테스트...")
    buy_success = trade_history_manager.record_buy_trade(
        symbol=test_symbol,
        quantity=test_quantity,
        price=test_buy_price,
        order_id=test_order_id_buy,
        strategy_name="test_strategy",
        trigger_reason="test_buy_signal"
    )

    if buy_success:
        print("✅ 매수 거래 기록 성공")
    else:
        print("❌ 매수 거래 기록 실패")
        return False

    # 3. 매도 거래 기록 테스트
    print(f"\n💸 매도 거래 기록 테스트...")
    sell_success = trade_history_manager.record_sell_trade(
        symbol=test_symbol,
        quantity=test_quantity,
        price=test_sell_price,
        order_id=test_order_id_sell,
        strategy_name="test_strategy",
        trigger_reason="test_sell_signal"
    )

    if sell_success:
        print("✅ 매도 거래 기록 성공")
    else:
        print("❌ 매도 거래 기록 실패")
        return False

    # 4. 거래 기록 조회 테스트
    print(f"\n📋 최근 거래 기록 조회...")
    recent_trades = trade_history_manager.get_recent_trades(5)
    if recent_trades:
        df = pd.DataFrame(recent_trades)
        print(df[['symbol', 'trade_type', 'executed_quantity', 'executed_price', 'execution_time']].to_string(index=False))
    else:
        print("조회된 거래 기록이 없습니다.")

    # 5. 거래 요약 통계 테스트
    print(f"\n📊 거래 요약 통계...")
    today = datetime.now().strftime('%Y-%m-%d')
    summary = trade_history_manager.get_trading_summary(today, today)
    if summary:
        print(f"총 거래 건수: {summary.get('total_trades', 0)}건")
        print(f"매수 건수: {summary.get('buy_count', 0)}건")
        print(f"매도 건수: {summary.get('sell_count', 0)}건")
        print(f"매수 총액: {summary.get('total_buy_amount', 0):,}원")
        print(f"매도 총액: {summary.get('total_sell_amount', 0):,}원")

    # 6. 데이터베이스에서 직접 확인
    print(f"\n🔍 데이터베이스 직접 확인...")
    try:
        with trade_history_manager.get_session() as session:
            # 오늘 추가된 거래 기록 조회
            query = """
            SELECT t.*, s.symbol, s.name
            FROM trades t
            JOIN stocks s ON t.stock_id = s.id
            WHERE DATE(t.created_at) = DATE('now')
            ORDER BY t.created_at DESC
            LIMIT 5
            """

            result = session.execute(query).fetchall()
            if result:
                print(f"✅ 데이터베이스에서 {len(result)}건의 오늘 거래 기록 확인됨")
                for row in result:
                    print(f"  - {row.symbol} {row.trade_type} {row.executed_quantity}주 @ {row.executed_price:,}원")
            else:
                print("❌ 데이터베이스에서 거래 기록을 찾을 수 없습니다.")

    except Exception as e:
        print(f"❌ 데이터베이스 조회 실패: {e}")

    print(f"\n✅ 거래 이력 자동 기록 시스템 테스트 완료!")
    return True

def test_integration_with_executor():
    """거래 실행기와의 통합 테스트 (시뮬레이션)"""
    print(f"\n" + "=" * 80)
    print("🔗 거래 실행기 통합 테스트 (시뮬레이션)")
    print("=" * 80)

    print("📝 통합 시나리오:")
    print("1. TradingExecutor 초기화 시 TradeHistoryManager 자동 생성됨")
    print("2. execute_buy_order/execute_sell_order 호출 시 자동으로 이력 저장됨")
    print("3. 매수/매도 쌍이 완료되면 trade_history 테이블에도 기록됨")
    print("4. 실시간으로 거래 통계를 조회할 수 있음")

    print(f"\n✅ 통합 테스트는 실제 거래 발생 시 자동으로 검증됩니다.")

def cleanup_test_data():
    """테스트 데이터 정리"""
    print(f"\n🧹 테스트 데이터 정리...")
    try:
        trade_history_manager = TradeHistoryManager()
        with trade_history_manager.get_session() as session:
            # 테스트 주문 ID로 시작하는 거래 기록 삭제
            delete_query = """
            DELETE FROM trades
            WHERE order_id LIKE 'TEST_%'
            """
            result = session.execute(delete_query)
            session.commit()
            print(f"✅ {result.rowcount}건의 테스트 거래 기록 삭제됨")
    except Exception as e:
        print(f"❌ 테스트 데이터 정리 실패: {e}")

if __name__ == "__main__":
    try:
        # 거래 이력 관리자 테스트
        success = test_trade_history_manager()

        if success:
            # 통합 테스트
            test_integration_with_executor()

            # 정리할지 물어보기
            cleanup = input(f"\n테스트 데이터를 정리하시겠습니까? (y/N): ").lower().strip()
            if cleanup == 'y':
                cleanup_test_data()
            else:
                print("테스트 데이터를 유지합니다.")

    except KeyboardInterrupt:
        print(f"\n\n⏹️ 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")