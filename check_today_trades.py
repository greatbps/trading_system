#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오늘 매매 내역 DB 조회
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from database.models import TradeExecution, Trade, TradingHistory
from datetime import datetime, date

def check_today_trades():
    try:
        db = DatabaseManager()
        session = db.get_session()

        # 오늘 날짜 거래 내역 조회
        today = date.today()
        print(f"=== 오늘({today}) 매매 내역 조회 ===")

        # TradeExecution 테이블에서 오늘 거래 확인
        executions = session.query(TradeExecution).filter(
            TradeExecution.executed_at >= datetime.combine(today, datetime.min.time())
        ).all()

        print(f"\n📊 TradeExecution 테이블: {len(executions)}건")
        for i, exec in enumerate(executions, 1):
            print(f"  {i}. {exec.symbol}: {exec.executed_quantity}주, {exec.executed_price}원")
            print(f"     상태: {exec.status}, 시간: {exec.executed_at}")

        # Trade 테이블에서 오늘 거래 확인
        trades = session.query(Trade).filter(
            Trade.created_at >= datetime.combine(today, datetime.min.time())
        ).all()

        print(f"\n📈 Trade 테이블: {len(trades)}건")
        for i, trade in enumerate(trades, 1):
            print(f"  {i}. {trade.symbol}: {trade.quantity}주, {trade.price}원")
            print(f"     타입: {trade.trade_type}, 시간: {trade.created_at}")

        # TradingHistory 테이블 확인
        try:
            histories = session.query(TradingHistory).filter(
                TradingHistory.created_at >= datetime.combine(today, datetime.min.time())
            ).all()

            print(f"\n📋 TradingHistory 테이블: {len(histories)}건")
            for i, hist in enumerate(histories, 1):
                print(f"  {i}. {hist.symbol}: 매수 {hist.buy_quantity}주@{hist.buy_price}원")
                if hist.sell_quantity and hist.sell_price:
                    print(f"     매도 {hist.sell_quantity}주@{hist.sell_price}원")
                    profit_pct = ((hist.sell_price - hist.buy_price) / hist.buy_price * 100) if hist.buy_price else 0
                    print(f"     수익률: {profit_pct:.2f}%")
                print(f"     손익: {hist.profit_loss}원, 시간: {hist.created_at}")
        except Exception as e:
            print(f"TradingHistory 조회 오류: {e}")

        # 최근 일주일 거래 요약
        week_ago = datetime.now() - datetime.timedelta(days=7)
        recent_trades = session.query(Trade).filter(
            Trade.created_at >= week_ago
        ).all()

        print(f"\n📅 최근 7일 거래: {len(recent_trades)}건")
        buy_count = len([t for t in recent_trades if t.trade_type == 'BUY'])
        sell_count = len([t for t in recent_trades if t.trade_type == 'SELL'])
        print(f"   매수: {buy_count}건, 매도: {sell_count}건")

        session.close()
        print("\n✅ DB 조회 완료")

    except Exception as e:
        print(f"❌ DB 조회 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_today_trades()