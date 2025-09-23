#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/generate_sample_trading_data.py

샘플 트레이딩 데이터 생성기
- 매수/매도 로직 준수/미준수 시나리오별 데이터 생성
- 성과 분석을 위한 다양한 케이스 포함
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, List, Any
from utils.logger import get_logger

class SampleTradingDataGenerator:
    """샘플 트레이딩 데이터 생성기"""

    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.logger = get_logger("SampleDataGenerator")

        # 샘플 종목 데이터
        self.sample_stocks = [
            {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"},
            {"symbol": "035420", "name": "NAVER", "market": "KOSPI"},
            {"symbol": "051910", "name": "LG화학", "market": "KOSPI"},
            {"symbol": "006400", "name": "삼성SDI", "market": "KOSPI"},
            {"symbol": "207940", "name": "삼성바이오로직스", "market": "KOSPI"},
            {"symbol": "068270", "name": "셀트리온", "market": "KOSPI"},
            {"symbol": "323410", "name": "카카오뱅크", "market": "KOSPI"},
            {"symbol": "035720", "name": "카카오", "market": "KOSPI"},
            {"symbol": "028260", "name": "삼성물산", "market": "KOSPI"}
        ]

        # 거래 시나리오 정의
        self.trading_scenarios = {
            "logic_compliant_profit": {
                "buy_logic_compliant": True,
                "sell_logic_compliant": True,
                "profit_range": (0.05, 0.25),  # 5~25% 수익
                "holding_days_range": (3, 20)
            },
            "logic_compliant_loss": {
                "buy_logic_compliant": True,
                "sell_logic_compliant": True,
                "profit_range": (-0.08, -0.02),  # 2~8% 손실 (손절)
                "holding_days_range": (1, 10)
            },
            "non_compliant_lucky": {
                "buy_logic_compliant": False,
                "sell_logic_compliant": False,
                "profit_range": (0.02, 0.15),  # 우연히 수익
                "holding_days_range": (5, 30)
            },
            "non_compliant_loss": {
                "buy_logic_compliant": False,
                "sell_logic_compliant": False,
                "profit_range": (-0.20, -0.05),  # 큰 손실
                "holding_days_range": (10, 60)
            },
            "mixed_scenario": {
                "buy_logic_compliant": True,
                "sell_logic_compliant": False,
                "profit_range": (-0.05, 0.10),  # 혼재된 결과
                "holding_days_range": (5, 45)
            }
        }

    def connect_db(self) -> sqlite3.Connection:
        """데이터베이스 연결"""
        return sqlite3.connect(self.db_path)

    def clear_existing_data(self) -> None:
        """기존 테스트 데이터 삭제"""
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()

                # 기존 테스트 데이터 삭제
                cursor.execute("DELETE FROM trades WHERE strategy_name LIKE 'test_%' OR strategy_name = 'sample_trading'")
                cursor.execute("DELETE FROM trade_history WHERE strategy_name = 'sample_trading'")
                cursor.execute("DELETE FROM stocks WHERE symbol LIKE 'TEST_%'")

                conn.commit()
                self.logger.info("기존 테스트 데이터 삭제 완료")

        except Exception as e:
            self.logger.error(f"기존 데이터 삭제 실패: {e}")

    def ensure_sample_stocks(self) -> Dict[str, int]:
        """샘플 종목 데이터 확인 및 생성"""
        try:
            stock_ids = {}

            with self.connect_db() as conn:
                cursor = conn.cursor()

                for stock in self.sample_stocks:
                    # 기존 종목 확인
                    cursor.execute("SELECT id FROM stocks WHERE symbol = ?", (stock["symbol"],))
                    result = cursor.fetchone()

                    if result:
                        stock_ids[stock["symbol"]] = result[0]
                    else:
                        # 새 종목 추가
                        cursor.execute("""
                            INSERT INTO stocks (symbol, name, market, is_active, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (stock["symbol"], stock["name"], stock["market"], True,
                             datetime.now(), datetime.now()))

                        stock_ids[stock["symbol"]] = cursor.lastrowid

                conn.commit()
                self.logger.info(f"샘플 종목 {len(stock_ids)}개 준비 완료")
                return stock_ids

        except Exception as e:
            self.logger.error(f"샘플 종목 생성 실패: {e}")
            return {}

    def generate_trading_pair(self, stock_symbol: str, stock_id: int, scenario: Dict[str, Any],
                            base_date: datetime) -> tuple:
        """매수-매도 거래 쌍 생성"""
        try:
            # 기본 가격 설정 (종목별 다른 가격대)
            price_ranges = {
                "005930": (65000, 75000),   # 삼성전자
                "000660": (80000, 90000),   # SK하이닉스
                "035420": (180000, 220000), # NAVER
                "051910": (650000, 750000), # LG화학
                "006400": (550000, 650000), # 삼성SDI
                "207940": (800000, 900000), # 삼성바이오로직스
                "068270": (180000, 220000), # 셀트리온
                "323410": (45000, 55000),   # 카카오뱅크
                "035720": (45000, 55000),   # 카카오
                "028260": (120000, 140000)  # 삼성물산
            }

            price_range = price_ranges.get(stock_symbol, (50000, 100000))
            buy_price = random.randint(price_range[0], price_range[1])

            # 수익률 및 보유기간 설정
            profit_rate = random.uniform(*scenario["profit_range"])
            holding_days = random.randint(*scenario["holding_days_range"])

            # 매도가 계산
            sell_price = int(buy_price * (1 + profit_rate))

            # 거래량
            quantity = random.choice([10, 20, 30, 50, 100])

            # 날짜 설정
            buy_date = base_date
            sell_date = buy_date + timedelta(days=holding_days)

            # 수수료 및 세금 계산
            buy_amount = buy_price * quantity
            sell_amount = sell_price * quantity

            buy_commission = int(buy_amount * 0.00015)
            sell_commission = int(sell_amount * 0.00015)
            sell_tax = int(sell_amount * 0.0023)

            # 매수 거래 데이터
            buy_trade = {
                "stock_id": stock_id,
                "order_id": f"BUY_{stock_symbol}_{buy_date.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
                "trade_type": "BUY",
                "order_type": "LIMIT",
                "order_price": buy_price,
                "order_quantity": quantity,
                "executed_price": buy_price,
                "executed_quantity": quantity,
                "order_status": "FILLED",
                "commission": buy_commission,
                "tax": 0,
                "order_time": buy_date,
                "execution_time": buy_date,
                "strategy_name": "sample_trading",
                "trigger_reason": f"buy_signal_{scenario.get('buy_logic_compliant', 'unknown')}",
                "analysis_result_id": None,
                "created_at": buy_date,
                "updated_at": buy_date
            }

            # 매도 거래 데이터
            sell_trade = {
                "stock_id": stock_id,
                "order_id": f"SELL_{stock_symbol}_{sell_date.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
                "trade_type": "SELL",
                "order_type": "LIMIT",
                "order_price": sell_price,
                "order_quantity": quantity,
                "executed_price": sell_price,
                "executed_quantity": quantity,
                "order_status": "FILLED",
                "commission": sell_commission,
                "tax": sell_tax,
                "order_time": sell_date,
                "execution_time": sell_date,
                "strategy_name": "sample_trading",
                "trigger_reason": f"sell_signal_{scenario.get('sell_logic_compliant', 'unknown')}",
                "analysis_result_id": None,
                "created_at": sell_date,
                "updated_at": sell_date
            }

            return buy_trade, sell_trade

        except Exception as e:
            self.logger.error(f"거래 쌍 생성 실패: {e}")
            return None, None

    def insert_trades(self, trades: List[Dict[str, Any]]) -> List[int]:
        """거래 데이터 DB 삽입"""
        try:
            trade_ids = []

            with self.connect_db() as conn:
                cursor = conn.cursor()

                for trade in trades:
                    cursor.execute("""
                        INSERT INTO trades (
                            stock_id, order_id, trade_type, order_type,
                            order_price, order_quantity, executed_price, executed_quantity,
                            order_status, commission, tax, order_time, execution_time,
                            strategy_name, trigger_reason, analysis_result_id,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade["stock_id"], trade["order_id"], trade["trade_type"], trade["order_type"],
                        trade["order_price"], trade["order_quantity"], trade["executed_price"], trade["executed_quantity"],
                        trade["order_status"], trade["commission"], trade["tax"], trade["order_time"], trade["execution_time"],
                        trade["strategy_name"], trade["trigger_reason"], trade["analysis_result_id"],
                        trade["created_at"], trade["updated_at"]
                    ))

                    trade_ids.append(cursor.lastrowid)

                conn.commit()
                self.logger.info(f"거래 데이터 {len(trades)}건 삽입 완료")
                return trade_ids

        except Exception as e:
            self.logger.error(f"거래 데이터 삽입 실패: {e}")
            return []

    def generate_filter_history(self, stock_ids: Dict[str, int]) -> None:
        """필터링 이력 데이터 생성"""
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()

                # 최근 30일간의 필터링 이력 생성
                for i in range(30):
                    filter_date = datetime.now() - timedelta(days=i)

                    # 일부 종목만 필터링 통과하도록 설정
                    passed_symbols = random.sample(list(stock_ids.keys()), k=random.randint(3, 7))

                    cursor.execute("""
                        INSERT INTO filter_history (
                            filter_date, strategy, filter_type, hts_condition,
                            hts_result_count, hts_symbols, ai_analyzed_count, ai_passed_count,
                            final_symbols, final_count, execution_time, hts_time, ai_time,
                            avg_score, max_score, min_score, status, market_condition,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        filter_date, "sample_strategy", "hts_ai_combined", "상승추세+AI분석",
                        len(stock_ids), str(list(stock_ids.keys())), len(passed_symbols), len(passed_symbols),
                        str(passed_symbols), len(passed_symbols), 2.5, 1.2, 1.3,
                        0.75, 0.95, 0.55, "SUCCESS", "NORMAL",
                        filter_date, filter_date
                    ))

                conn.commit()
                self.logger.info("필터링 이력 데이터 30건 생성 완료")

        except Exception as e:
            self.logger.error(f"필터링 이력 생성 실패: {e}")

    def generate_sample_data(self, num_trades_per_scenario: int = 20) -> bool:
        """샘플 데이터 생성"""
        try:
            self.logger.info("샘플 트레이딩 데이터 생성 시작")

            # 1. 기존 데이터 정리
            self.clear_existing_data()

            # 2. 샘플 종목 준비
            stock_ids = self.ensure_sample_stocks()
            if not stock_ids:
                self.logger.error("샘플 종목 준비 실패")
                return False

            # 3. 필터링 이력 생성
            self.generate_filter_history(stock_ids)

            # 4. 거래 데이터 생성
            all_trades = []
            base_date = datetime.now() - timedelta(days=60)  # 60일 전부터 시작

            for scenario_name, scenario_config in self.trading_scenarios.items():
                for i in range(num_trades_per_scenario):
                    # 랜덤 종목 선택
                    stock_symbol = random.choice(list(stock_ids.keys()))
                    stock_id = stock_ids[stock_symbol]

                    # 거래 날짜 (시나리오별로 다른 기간)
                    days_offset = random.randint(0, 50)
                    trade_date = base_date + timedelta(days=days_offset)

                    # 거래 쌍 생성
                    buy_trade, sell_trade = self.generate_trading_pair(
                        stock_symbol, stock_id, scenario_config, trade_date
                    )

                    if buy_trade and sell_trade:
                        all_trades.extend([buy_trade, sell_trade])

            # 5. 거래 데이터 저장
            if all_trades:
                trade_ids = self.insert_trades(all_trades)

                # 6. 거래 이력 테이블도 업데이트
                self.generate_trade_history_records(trade_ids)

                self.logger.info(f"샘플 데이터 생성 완료: {len(all_trades)}건의 거래")
                return True
            else:
                self.logger.error("거래 데이터 생성 실패")
                return False

        except Exception as e:
            self.logger.error(f"샘플 데이터 생성 실패: {e}")
            return False

    def generate_trade_history_records(self, trade_ids: List[int]) -> None:
        """거래 이력 레코드 생성"""
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()

                # 매수-매도 쌍으로 묶어서 trade_history 테이블에 저장
                for i in range(0, len(trade_ids), 2):
                    if i + 1 < len(trade_ids):
                        buy_trade_id = trade_ids[i]
                        sell_trade_id = trade_ids[i + 1]

                        # 매수/매도 거래 정보 조회
                        cursor.execute("""
                            SELECT t.*, s.symbol FROM trades t
                            JOIN stocks s ON t.stock_id = s.id
                            WHERE t.id = ?
                        """, (buy_trade_id,))
                        buy_trade = cursor.fetchone()

                        cursor.execute("""
                            SELECT t.*, s.symbol FROM trades t
                            JOIN stocks s ON t.stock_id = s.id
                            WHERE t.id = ?
                        """, (sell_trade_id,))
                        sell_trade = cursor.fetchone()

                        if buy_trade and sell_trade:
                            # 손익 계산
                            profit_loss = (sell_trade[7] - buy_trade[7]) * sell_trade[8]  # (매도가 - 매수가) * 수량
                            profit_loss -= (buy_trade[10] + sell_trade[10] + sell_trade[11])  # 수수료, 세금 차감

                            profit_loss_rate = (profit_loss / (buy_trade[7] * buy_trade[8])) * 100

                            # 보유 기간 계산
                            buy_date = datetime.fromisoformat(buy_trade[13])
                            sell_date = datetime.fromisoformat(sell_trade[13])
                            holding_period = (sell_date - buy_date).days

                            # trade_history 테이블에 삽입
                            cursor.execute("""
                                INSERT INTO trade_history (
                                    stock_id, strategy_name, buy_trade_id, sell_trade_id,
                                    buy_date, sell_date, buy_price, sell_price, quantity,
                                    profit_loss, profit_loss_rate, holding_period_days, status,
                                    created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                buy_trade[1], buy_trade[14], buy_trade_id, sell_trade_id,
                                buy_trade[13], sell_trade[13], buy_trade[7], sell_trade[7], buy_trade[8],
                                profit_loss, round(profit_loss_rate, 2), holding_period, "DONE",
                                datetime.now(), datetime.now()
                            ))

                conn.commit()
                self.logger.info(f"거래 이력 {len(trade_ids)//2}건 생성 완료")

        except Exception as e:
            self.logger.error(f"거래 이력 생성 실패: {e}")

    def generate_summary_report(self) -> str:
        """생성된 데이터 요약 보고서"""
        try:
            with self.connect_db() as conn:
                # 전체 거래 통계
                df_trades = pd.read_sql_query("""
                    SELECT COUNT(*) as total_trades,
                           SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                           SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_count
                    FROM trades WHERE strategy_name = 'sample_trading'
                """, conn)

                # 거래 이력 통계
                df_history = pd.read_sql_query("""
                    SELECT COUNT(*) as completed_pairs,
                           AVG(profit_loss_rate) as avg_profit_rate,
                           SUM(profit_loss) as total_profit_loss,
                           AVG(holding_period_days) as avg_holding_days
                    FROM trade_history WHERE strategy_name = 'sample_trading'
                """, conn)

                # 종목별 통계
                df_stocks = pd.read_sql_query("""
                    SELECT s.symbol, s.name, COUNT(t.id) as trade_count
                    FROM trades t
                    JOIN stocks s ON t.stock_id = s.id
                    WHERE t.strategy_name = 'sample_trading'
                    GROUP BY s.symbol, s.name
                    ORDER BY trade_count DESC
                """, conn)

                report = f"""# 샘플 트레이딩 데이터 생성 보고서

## 생성 개요
- 생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 전략명: sample_trading

## 거래 데이터 통계
- 총 거래 건수: {df_trades.iloc[0]['total_trades']}건
- 매수 거래: {df_trades.iloc[0]['buy_count']}건
- 매도 거래: {df_trades.iloc[0]['sell_count']}건

## 완료된 거래 분석
- 완료된 거래 쌍: {df_history.iloc[0]['completed_pairs']}건
- 평균 수익률: {df_history.iloc[0]['avg_profit_rate']:.2f}%
- 총 손익: {df_history.iloc[0]['total_profit_loss']:,.0f}원
- 평균 보유기간: {df_history.iloc[0]['avg_holding_days']:.1f}일

## 종목별 거래 현황
"""
                for _, row in df_stocks.iterrows():
                    report += f"- {row['symbol']} ({row['name']}): {row['trade_count']}건\n"

                report += f"""
## 시나리오별 분포
- 로직 준수 수익: {self.trading_scenarios['logic_compliant_profit']}
- 로직 준수 손절: {self.trading_scenarios['logic_compliant_loss']}
- 로직 미준수 우연 수익: {self.trading_scenarios['non_compliant_lucky']}
- 로직 미준수 손실: {self.trading_scenarios['non_compliant_loss']}
- 혼합 시나리오: {self.trading_scenarios['mixed_scenario']}

---
*생성 도구: SampleTradingDataGenerator v1.0*
"""

                return report

        except Exception as e:
            self.logger.error(f"요약 보고서 생성 실패: {e}")
            return "요약 보고서 생성 실패"


def main():
    """메인 실행 함수"""
    generator = SampleTradingDataGenerator()

    print("=" * 60)
    print("샘플 트레이딩 데이터 생성 시작")
    print("=" * 60)

    # 샘플 데이터 생성 (시나리오별 20건씩)
    success = generator.generate_sample_data(num_trades_per_scenario=20)

    if success:
        print("\n✅ 샘플 데이터 생성 완료!")

        # 요약 보고서 출력
        report = generator.generate_summary_report()
        print(report)
    else:
        print("❌ 샘플 데이터 생성 실패")

    print("\n" + "=" * 60)
    print("데이터 생성 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()