#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/trade_history_manager.py

거래 이력 관리 모듈 - 매수/매도 시마다 DB에 자동 기록
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Optional, Any
from decimal import Decimal
from utils.logger import get_logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

class TradeHistoryManager:
    """거래 이력 자동 저장 관리자"""

    def __init__(self, db_url: str = "sqlite:///trading_system.db"):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.logger = get_logger("TradeHistoryManager")

    @contextmanager
    def get_session(self):
        """데이터베이스 세션 컨텍스트 매니저"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def record_trade(self, trade_data: Dict[str, Any]) -> bool:
        """거래 기록을 데이터베이스에 저장"""
        try:
            with self.get_session() as session:
                # trades 테이블에 기록
                insert_query = text("""
                INSERT INTO trades (
                    stock_id, order_id, trade_type, order_type,
                    order_price, order_quantity, executed_price, executed_quantity,
                    order_status, commission, tax, order_time, execution_time,
                    strategy_name, trigger_reason, analysis_result_id,
                    created_at, updated_at
                ) VALUES (
                    :stock_id, :order_id, :trade_type, :order_type,
                    :order_price, :order_quantity, :executed_price, :executed_quantity,
                    :order_status, :commission, :tax, :order_time, :execution_time,
                    :strategy_name, :trigger_reason, :analysis_result_id,
                    :created_at, :updated_at
                )
                """)

                session.execute(insert_query, trade_data)
                session.commit()

                self.logger.info(f"✅ 거래 기록 저장 완료: {trade_data.get('trade_type')} {trade_data.get('order_quantity')}주")
                return True

        except Exception as e:
            self.logger.error(f"❌ 거래 기록 저장 실패: {e}")
            return False

    def record_buy_trade(self, symbol: str, quantity: int, price: int,
                        order_id: str, strategy_name: str = "manual",
                        trigger_reason: str = "manual_order") -> bool:
        """매수 거래 기록"""
        try:
            # price와 quantity 유효성 검사
            if price is None or quantity is None:
                self.logger.error(f"❌ 매수 거래 기록 실패: price={price}, quantity={quantity}")
                return False

            # 종목 ID 조회
            stock_id = self._get_stock_id(symbol)
            if not stock_id:
                self.logger.error(f"❌ 종목 ID 조회 실패: {symbol}")
                return False

            trade_data = {
                'stock_id': stock_id,
                'order_id': order_id,
                'trade_type': 'BUY',
                'order_type': 'MARKET',
                'order_price': price,
                'order_quantity': quantity,
                'executed_price': price,
                'executed_quantity': quantity,
                'order_status': 'FILLED',
                'commission': int(price * quantity * 0.00015),  # 수수료 추정
                'tax': 0,  # 매수시 세금 없음
                'order_time': datetime.now(),
                'execution_time': datetime.now(),
                'strategy_name': strategy_name,
                'trigger_reason': trigger_reason,
                'analysis_result_id': None,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            return self.record_trade(trade_data)

        except Exception as e:
            self.logger.error(f"❌ 매수 거래 기록 실패: {e}")
            return False

    def record_sell_trade(self, symbol: str, quantity: int, price: int,
                         order_id: str, strategy_name: str = "manual",
                         trigger_reason: str = "manual_order") -> bool:
        """매도 거래 기록"""
        try:
            # price와 quantity 유효성 검사
            if price is None or quantity is None:
                self.logger.error(f"❌ 매도 거래 기록 실패: price={price}, quantity={quantity}")
                return False

            # 종목 ID 조회
            stock_id = self._get_stock_id(symbol)
            if not stock_id:
                self.logger.error(f"❌ 종목 ID 조회 실패: {symbol}")
                return False

            trade_amount = price * quantity
            commission = int(trade_amount * 0.00015)  # 수수료
            tax = int(trade_amount * 0.0023)  # 증권거래세

            trade_data = {
                'stock_id': stock_id,
                'order_id': order_id,
                'trade_type': 'SELL',
                'order_type': 'MARKET',
                'order_price': price,
                'order_quantity': quantity,
                'executed_price': price,
                'executed_quantity': quantity,
                'order_status': 'FILLED',
                'commission': commission,
                'tax': tax,
                'order_time': datetime.now(),
                'execution_time': datetime.now(),
                'strategy_name': strategy_name,
                'trigger_reason': trigger_reason,
                'analysis_result_id': None,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            return self.record_trade(trade_data)

        except Exception as e:
            self.logger.error(f"❌ 매도 거래 기록 실패: {e}")
            return False

    def record_trade_history(self, buy_trade_id: int, sell_trade_id: int) -> bool:
        """매수-매도 쌍의 거래 이력 기록 (trade_history 테이블)"""
        try:
            with self.get_session() as session:
                # 매수/매도 거래 정보 조회
                buy_query = text("""
                SELECT t.*, s.symbol, s.name
                FROM trades t
                JOIN stocks s ON t.stock_id = s.id
                WHERE t.id = :trade_id AND t.trade_type = 'BUY'
                """)

                sell_query = text("""
                SELECT t.*, s.symbol, s.name
                FROM trades t
                JOIN stocks s ON t.stock_id = s.id
                WHERE t.id = :trade_id AND t.trade_type = 'SELL'
                """)

                buy_trade = session.execute(buy_query, {'trade_id': buy_trade_id}).fetchone()
                sell_trade = session.execute(sell_query, {'trade_id': sell_trade_id}).fetchone()

                if not buy_trade or not sell_trade:
                    self.logger.error("❌ 매수 또는 매도 거래 정보를 찾을 수 없습니다")
                    return False

                # 손익 계산
                profit_loss = (sell_trade.executed_price - buy_trade.executed_price) * sell_trade.executed_quantity
                profit_loss -= (buy_trade.commission + sell_trade.commission + sell_trade.tax)

                profit_loss_rate = (profit_loss / (buy_trade.executed_price * buy_trade.executed_quantity)) * 100

                # 보유 기간 계산
                holding_period = (sell_trade.execution_time - buy_trade.execution_time).days

                # trade_history 테이블에 기록
                history_data = {
                    'stock_id': buy_trade.stock_id,
                    'strategy_name': buy_trade.strategy_name,
                    'buy_trade_id': buy_trade_id,
                    'sell_trade_id': sell_trade_id,
                    'buy_date': buy_trade.execution_time,
                    'sell_date': sell_trade.execution_time,
                    'buy_price': buy_trade.executed_price,
                    'sell_price': sell_trade.executed_price,
                    'quantity': sell_trade.executed_quantity,
                    'profit_loss': profit_loss,
                    'profit_loss_rate': round(profit_loss_rate, 2),
                    'holding_period_days': holding_period,
                    'status': 'DONE'
                }

                insert_history_query = text("""
                INSERT INTO trade_history (
                    stock_id, strategy_name, buy_trade_id, sell_trade_id,
                    buy_date, sell_date, buy_price, sell_price, quantity,
                    profit_loss, profit_loss_rate, holding_period_days, status
                ) VALUES (
                    :stock_id, :strategy_name, :buy_trade_id, :sell_trade_id,
                    :buy_date, :sell_date, :buy_price, :sell_price, :quantity,
                    :profit_loss, :profit_loss_rate, :holding_period_days, :status
                )
                """)

                session.execute(insert_history_query, history_data)
                session.commit()

                self.logger.info(f"✅ 거래 이력 저장 완료: {buy_trade.symbol} "
                               f"손익 {profit_loss:,}원 ({profit_loss_rate:.2f}%)")
                return True

        except Exception as e:
            self.logger.error(f"❌ 거래 이력 저장 실패: {e}")
            return False

    def _get_stock_id(self, symbol: str) -> Optional[int]:
        """종목 코드로 stock_id 조회, 없으면 생성"""
        try:
            with self.get_session() as session:
                # 기존 종목 조회
                query = text("SELECT id FROM stocks WHERE symbol = :symbol")
                result = session.execute(query, {'symbol': symbol}).fetchone()

                if result:
                    return result.id

                # 종목이 없으면 새로 추가
                self.logger.info(f"📝 새 종목 추가: {symbol}")
                insert_query = text("""
                INSERT INTO stocks (symbol, name, market_type, created_at, updated_at)
                VALUES (:symbol, :name, :market_type, :created_at, :updated_at)
                """)

                now = datetime.now()
                session.execute(insert_query, {
                    'symbol': symbol,
                    'name': f'Stock_{symbol}',  # 임시 이름
                    'market_type': 'KOSPI',
                    'created_at': now,
                    'updated_at': now
                })
                session.commit()

                # 다시 조회
                result = session.execute(query, {'symbol': symbol}).fetchone()
                return result.id if result else None

        except Exception as e:
            self.logger.error(f"❌ 종목 ID 조회/생성 실패: {e}")
            return None

    def get_recent_trades(self, limit: int = 10) -> list:
        """최근 거래 기록 조회"""
        try:
            with self.get_session() as session:
                query = text("""
                SELECT
                    t.id, s.symbol, s.name, t.trade_type,
                    t.executed_quantity, t.executed_price, t.execution_time,
                    t.strategy_name, t.order_status
                FROM trades t
                JOIN stocks s ON t.stock_id = s.id
                ORDER BY t.execution_time DESC
                LIMIT :limit
                """)

                result = session.execute(query, {'limit': limit}).fetchall()
                return [dict(row._mapping) for row in result]

        except Exception as e:
            self.logger.error(f"❌ 최근 거래 조회 실패: {e}")
            return []

    def get_trading_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """거래 요약 통계 조회"""
        try:
            with self.get_session() as session:
                where_clause = ""
                params = {}

                if start_date and end_date:
                    where_clause = "WHERE DATE(t.execution_time) BETWEEN :start_date AND :end_date"
                    params = {'start_date': start_date, 'end_date': end_date}

                query = text(f"""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN t.trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN t.trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                    SUM(CASE WHEN t.trade_type = 'BUY' THEN t.executed_price * t.executed_quantity ELSE 0 END) as total_buy_amount,
                    SUM(CASE WHEN t.trade_type = 'SELL' THEN t.executed_price * t.executed_quantity ELSE 0 END) as total_sell_amount
                FROM trades t
                {where_clause}
                """)

                result = session.execute(query, params).fetchone()
                return dict(result._mapping) if result else {}

        except Exception as e:
            self.logger.error(f"❌ 거래 요약 조회 실패: {e}")
            return {}