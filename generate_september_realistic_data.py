#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/generate_september_realistic_data.py

9월 실제 주문 종목 기반 현실적 트레이딩 데이터 생성기
- 실제 KIS API 주문 종목 반영
- 현실적인 가격대와 수익률 반영
- 로직 준수/미준수 시나리오 구현
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, List, Any
from utils.logger import get_logger

class SeptemberRealisticDataGenerator:
    """9월 실제 종목 기반 데이터 생성기"""

    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.logger = get_logger("SeptemberDataGenerator")

        # 9월 실제 주문 종목 (보고서 기반)
        self.september_stocks = [
            # 매수 위주 종목들
            {"symbol": "000240", "name": "한국앤컴퍼니", "market": "KOSDAQ", "price_range": (2000, 3000)},
            {"symbol": "263860", "name": "지니언스", "market": "KOSDAQ", "price_range": (15000, 25000)},
            {"symbol": "080580", "name": "오킨스전자", "market": "KOSDAQ", "price_range": (3000, 5000)},
            {"symbol": "092040", "name": "아미코젠", "market": "KOSDAQ", "price_range": (8000, 12000)},
            {"symbol": "047820", "name": "초록뱀미디어", "market": "KOSDAQ", "price_range": (5000, 8000)},
            {"symbol": "205100", "name": "엑셈", "market": "KOSDAQ", "price_range": (30000, 45000)},
            {"symbol": "364950", "name": "에이아이코리아", "market": "KOSDAQ", "price_range": (8000, 15000)},
            {"symbol": "013360", "name": "일성건설", "market": "KOSPI", "price_range": (3000, 5000)},
            {"symbol": "114810", "name": "한솔아이원스", "market": "KOSDAQ", "price_range": (10000, 15000)},
            {"symbol": "130740", "name": "티피씨글로벌", "market": "KOSDAQ", "price_range": (8000, 12000)},
            {"symbol": "131890", "name": "ACE 삼성그룹동일가중", "market": "ETF", "price_range": (10000, 12000)},
            {"symbol": "099440", "name": "스맥", "market": "KOSDAQ", "price_range": (12000, 18000)},
            {"symbol": "004140", "name": "동방", "market": "KOSPI", "price_range": (8000, 12000)},
            {"symbol": "065500", "name": "오리엔트정공", "market": "KOSDAQ", "price_range": (6000, 10000)},
            {"symbol": "025890", "name": "한국주강", "market": "KOSPI", "price_range": (4000, 7000)},
            {"symbol": "044180", "name": "KD", "market": "KOSDAQ", "price_range": (5000, 8000)},
            {"symbol": "045340", "name": "토탈소프트", "market": "KOSDAQ", "price_range": (3000, 6000)},
            # 매도 시도 종목들 (기보유)
            {"symbol": "363260", "name": "모비데이즈", "market": "KOSDAQ", "price_range": (8000, 15000)},
            {"symbol": "321370", "name": "센서뷰", "market": "KOSDAQ", "price_range": (6000, 10000)},
            {"symbol": "018500", "name": "동원금속", "market": "KOSPI", "price_range": (8000, 12000)},
            {"symbol": "013310", "name": "아진산업", "market": "KOSPI", "price_range": (6000, 10000)},
            {"symbol": "010170", "name": "대한광통신", "market": "KOSDAQ", "price_range": (4000, 8000)}
        ]

        # 현실적인 거래 시나리오 (9월 시장 상황 반영)
        self.realistic_scenarios = {
            "logic_compliant_small_profit": {
                "buy_logic_compliant": True,
                "sell_logic_compliant": True,
                "profit_range": (0.03, 0.12),  # 3~12% 현실적 수익
                "holding_days_range": (2, 15),
                "weight": 0.25
            },
            "logic_compliant_quick_cut": {
                "buy_logic_compliant": True,
                "sell_logic_compliant": True,
                "profit_range": (-0.05, -0.02),  # 빠른 손절
                "holding_days_range": (1, 5),
                "weight": 0.15
            },
            "buy_logic_good_manual_sell": {
                "buy_logic_compliant": True,
                "sell_logic_compliant": False,
                "profit_range": (0.05, 0.20),  # 좋은 매수, 수동 매도
                "holding_days_range": (3, 25),
                "weight": 0.20
            },
            "bad_buy_lucky_sell": {
                "buy_logic_compliant": False,
                "sell_logic_compliant": True,
                "profit_range": (-0.02, 0.08),  # 나쁜 매수, 운 좋은 매도
                "holding_days_range": (5, 20),
                "weight": 0.15
            },
            "both_non_compliant_loss": {
                "buy_logic_compliant": False,
                "sell_logic_compliant": False,
                "profit_range": (-0.15, -0.03),  # 둘 다 안 지켜서 손실
                "holding_days_range": (10, 40),
                "weight": 0.20
            },
            "both_non_compliant_lucky": {
                "buy_logic_compliant": False,
                "sell_logic_compliant": False,
                "profit_range": (0.02, 0.15),  # 둘 다 안 지켰는데 운좋게
                "holding_days_range": (7, 30),
                "weight": 0.05
            }
        }

    def connect_db(self) -> sqlite3.Connection:
        """데이터베이스 연결"""
        return sqlite3.connect(self.db_path)

    def clear_sample_data(self) -> None:
        """기존 샘플 데이터 정리"""
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()

                # 기존 샘플 데이터 삭제
                cursor.execute("DELETE FROM trades WHERE strategy_name = 'september_realistic'")
                cursor.execute("DELETE FROM trade_history WHERE strategy_name = 'september_realistic'")
                cursor.execute("DELETE FROM filter_history WHERE strategy = 'september_realistic'")

                conn.commit()
                self.logger.info("기존 샘플 데이터 정리 완료")

        except Exception as e:
            self.logger.error(f"데이터 정리 실패: {e}")

    def ensure_september_stocks(self) -> Dict[str, int]:
        """9월 종목 데이터 확인 및 생성"""
        try:
            stock_ids = {}

            with self.connect_db() as conn:
                cursor = conn.cursor()

                for stock in self.september_stocks:
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
                self.logger.info(f"9월 종목 {len(stock_ids)}개 준비 완료")
                return stock_ids

        except Exception as e:
            self.logger.error(f"9월 종목 생성 실패: {e}")
            return {}

    def generate_realistic_trading_pair(self, stock_symbol: str, stock_id: int,
                                      scenario: Dict[str, Any], base_date: datetime) -> tuple:
        """현실적인 매수-매도 거래 쌍 생성"""
        try:
            # 종목별 가격대 찾기
            stock_info = next((s for s in self.september_stocks if s["symbol"] == stock_symbol), None)
            if not stock_info:
                return None, None

            price_range = stock_info["price_range"]
            buy_price = random.randint(price_range[0], price_range[1])

            # 수익률 및 보유기간 설정
            profit_rate = random.uniform(*scenario["profit_range"])
            holding_days = random.randint(*scenario["holding_days_range"])

            # 매도가 계산 (현실적인 가격 단위 고려)
            sell_price = int(buy_price * (1 + profit_rate))

            # 가격 단위 조정 (호가 단위 반영)
            if buy_price < 1000:
                buy_price = round(buy_price / 5) * 5
                sell_price = round(sell_price / 5) * 5
            elif buy_price < 5000:
                buy_price = round(buy_price / 10) * 10
                sell_price = round(sell_price / 10) * 10
            elif buy_price < 10000:
                buy_price = round(buy_price / 50) * 50
                sell_price = round(sell_price / 50) * 50
            else:
                buy_price = round(buy_price / 100) * 100
                sell_price = round(sell_price / 100) * 100

            # 현실적인 거래량 (소액 투자 반영)
            max_amount = 200000  # 최대 20만원
            max_quantity = max_amount // buy_price
            quantity = min(random.choice([10, 20, 30, 50]), max_quantity)
            if quantity == 0:
                quantity = 1

            # 날짜 설정 (9월 중)
            september_start = datetime(2025, 9, 1)
            september_end = datetime(2025, 9, 30)

            # 매수일은 9월 중 랜덤
            days_in_september = (september_end - september_start).days
            buy_offset = random.randint(0, days_in_september - holding_days)
            buy_date = september_start + timedelta(days=buy_offset)
            sell_date = buy_date + timedelta(days=holding_days)

            # 매도일이 9월을 넘어가면 조정
            if sell_date > september_end:
                sell_date = september_end
                holding_days = (sell_date - buy_date).days

            # 수수료 및 세금 계산
            buy_amount = buy_price * quantity
            sell_amount = sell_price * quantity

            buy_commission = max(int(buy_amount * 0.00015), 100)  # 최소 수수료 100원
            sell_commission = max(int(sell_amount * 0.00015), 100)
            sell_tax = int(sell_amount * 0.0023)  # 증권거래세

            # 로직 준수 관련 trigger_reason 생성
            buy_trigger = f"buy_signal_{scenario['buy_logic_compliant']}"
            sell_trigger = f"sell_signal_{scenario['sell_logic_compliant']}"

            # 매수 거래 데이터
            buy_trade = {
                "stock_id": stock_id,
                "order_id": f"SEP_BUY_{stock_symbol}_{buy_date.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
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
                "strategy_name": "september_realistic",
                "trigger_reason": buy_trigger,
                "analysis_result_id": None,
                "created_at": buy_date,
                "updated_at": buy_date
            }

            # 매도 거래 데이터
            sell_trade = {
                "stock_id": stock_id,
                "order_id": f"SEP_SELL_{stock_symbol}_{sell_date.strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
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
                "strategy_name": "september_realistic",
                "trigger_reason": sell_trigger,
                "analysis_result_id": None,
                "created_at": sell_date,
                "updated_at": sell_date
            }

            return buy_trade, sell_trade

        except Exception as e:
            self.logger.error(f"거래 쌍 생성 실패: {e}")
            return None, None

    def insert_trades_and_history(self, all_trades: List[Dict[str, Any]]) -> bool:
        """거래 데이터 및 이력 저장"""
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()

                # 거래 데이터 저장
                trade_ids = []
                for trade in all_trades:
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

                # 거래 이력 저장 (매수-매도 쌍)
                for i in range(0, len(trade_ids), 2):
                    if i + 1 < len(trade_ids):
                        buy_trade_id = trade_ids[i]
                        sell_trade_id = trade_ids[i + 1]

                        # 매수/매도 거래 정보 조회
                        cursor.execute("SELECT * FROM trades WHERE id = ?", (buy_trade_id,))
                        buy_data = cursor.fetchone()
                        cursor.execute("SELECT * FROM trades WHERE id = ?", (sell_trade_id,))
                        sell_data = cursor.fetchone()

                        if buy_data and sell_data:
                            # 손익 계산
                            profit_loss = (sell_data[7] - buy_data[7]) * sell_data[8]  # (매도가 - 매수가) * 수량
                            profit_loss -= (buy_data[10] + sell_data[10] + sell_data[11])  # 수수료, 세금 차감

                            profit_loss_rate = (profit_loss / (buy_data[7] * buy_data[8])) * 100

                            # 보유 기간
                            buy_time = datetime.fromisoformat(buy_data[12])
                            sell_time = datetime.fromisoformat(sell_data[12])
                            holding_period = (sell_time - buy_time).days

                            # trade_history 저장
                            cursor.execute("""
                                INSERT INTO trade_history (
                                    stock_id, strategy_name, buy_trade_id, sell_trade_id,
                                    buy_date, sell_date, buy_price, sell_price, quantity,
                                    profit_loss, profit_loss_rate, holding_period_days, status,
                                    created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                buy_data[1], "september_realistic", buy_trade_id, sell_trade_id,
                                buy_data[12], sell_data[12], buy_data[7], sell_data[7], buy_data[8],
                                profit_loss, round(profit_loss_rate, 2), holding_period, "DONE",
                                datetime.now(), datetime.now()
                            ))

                conn.commit()
                self.logger.info(f"거래 데이터 {len(all_trades)}건 및 이력 {len(trade_ids)//2}건 저장 완료")
                return True

        except Exception as e:
            self.logger.error(f"데이터 저장 실패: {e}")
            return False

    def generate_september_realistic_data(self, total_trades: int = 100) -> bool:
        """9월 현실적 데이터 생성"""
        try:
            self.logger.info("9월 현실적 트레이딩 데이터 생성 시작")

            # 1. 기존 데이터 정리
            self.clear_sample_data()

            # 2. 9월 종목 준비
            stock_ids = self.ensure_september_stocks()
            if not stock_ids:
                return False

            # 3. 시나리오별 거래 생성
            all_trades = []
            stocks_list = list(stock_ids.keys())

            for scenario_name, scenario_config in self.realistic_scenarios.items():
                # 시나리오별 거래 수 계산
                scenario_trades = int(total_trades * scenario_config["weight"])

                for _ in range(scenario_trades):
                    # 랜덤 종목 선택 (9월 실제 주문 종목 중)
                    stock_symbol = random.choice(stocks_list)
                    stock_id = stock_ids[stock_symbol]

                    # 거래 쌍 생성
                    buy_trade, sell_trade = self.generate_realistic_trading_pair(
                        stock_symbol, stock_id, scenario_config, datetime(2025, 9, 1)
                    )

                    if buy_trade and sell_trade:
                        all_trades.extend([buy_trade, sell_trade])

            # 4. 데이터 저장
            if all_trades:
                success = self.insert_trades_and_history(all_trades)
                if success:
                    self.logger.info(f"9월 현실적 데이터 생성 완료: {len(all_trades)}건")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"9월 데이터 생성 실패: {e}")
            return False

    def generate_summary_report(self) -> str:
        """생성 요약 보고서"""
        try:
            with self.connect_db() as conn:
                # 거래 통계
                trade_stats = pd.read_sql_query("""
                    SELECT
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN trade_type = 'BUY' THEN 1 END) as buy_count,
                        COUNT(CASE WHEN trade_type = 'SELL' THEN 1 END) as sell_count
                    FROM trades
                    WHERE strategy_name = 'september_realistic'
                """, conn)

                # 거래 이력 통계
                history_stats = pd.read_sql_query("""
                    SELECT
                        COUNT(*) as completed_pairs,
                        AVG(profit_loss_rate) as avg_profit_rate,
                        SUM(profit_loss) as total_profit_loss,
                        AVG(holding_period_days) as avg_holding_days,
                        COUNT(CASE WHEN profit_loss_rate > 0 THEN 1 END) as winning_trades
                    FROM trade_history
                    WHERE strategy_name = 'september_realistic'
                """, conn)

                # 종목별 통계
                stock_stats = pd.read_sql_query("""
                    SELECT
                        s.symbol, s.name,
                        COUNT(t.id) as trade_count,
                        AVG(th.profit_loss_rate) as avg_profit_rate
                    FROM trades t
                    JOIN stocks s ON t.stock_id = s.id
                    LEFT JOIN trade_history th ON t.stock_id = th.stock_id
                    WHERE t.strategy_name = 'september_realistic' AND t.trade_type = 'BUY'
                    GROUP BY s.symbol, s.name
                    ORDER BY trade_count DESC
                """, conn)

                # 보고서 생성
                stats = history_stats.iloc[0]
                win_rate = (stats['winning_trades'] / stats['completed_pairs'] * 100) if stats['completed_pairs'] > 0 else 0

                report = f"""# 9월 현실적 트레이딩 데이터 생성 보고서

## 생성 개요
- **생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **기반 데이터**: 2025년 9월 실제 KIS API 주문 종목
- **전략명**: september_realistic

## 거래 데이터 통계
- **총 거래 건수**: {trade_stats.iloc[0]['total_trades']}건
- **매수 거래**: {trade_stats.iloc[0]['buy_count']}건
- **매도 거래**: {trade_stats.iloc[0]['sell_count']}건

## 완료된 거래 성과
- **완료된 거래 쌍**: {int(stats['completed_pairs'])}건
- **평균 수익률**: {stats['avg_profit_rate']:.2f}%
- **승률**: {win_rate:.1f}%
- **총 손익**: {stats['total_profit_loss']:,.0f}원
- **평균 보유기간**: {stats['avg_holding_days']:.1f}일

## 9월 실제 주문 종목 ({len(self.september_stocks)}개)
"""

                for _, row in stock_stats.head(10).iterrows():
                    report += f"- **{row['symbol']}** ({row['name']}): {row['trade_count']}건"
                    if pd.notna(row['avg_profit_rate']):
                        report += f" (평균 {row['avg_profit_rate']:.2f}%)"
                    report += "\n"

                report += f"""
## 시나리오 구성
- **로직 준수 소액수익**: 25% (현실적 3-12% 수익)
- **로직 준수 빠른손절**: 15% (2-5% 손절)
- **매수만 준수**: 20% (좋은 매수, 수동 매도)
- **매도만 준수**: 15% (나쁜 매수, 운 좋은 매도)
- **둘 다 미준수 손실**: 20% (체계 없는 거래로 손실)
- **둘 다 미준수 운**: 5% (우연한 수익)

## 현실성 반영 요소
- ✅ 실제 9월 KIS API 주문 종목 사용
- ✅ 종목별 실제 가격대 반영
- ✅ 호가 단위 적용 (5원, 10원, 50원, 100원)
- ✅ 소액 투자 패턴 (최대 20만원)
- ✅ 9월 기간 내 거래일 설정
- ✅ 현실적 수익률 범위 (-15% ~ +20%)
- ✅ 실제 수수료 및 세금 계산

---
*생성 도구: SeptemberRealisticDataGenerator*
"""

                return report

        except Exception as e:
            self.logger.error(f"요약 보고서 생성 실패: {e}")
            return "요약 보고서 생성 실패"


def main():
    """메인 실행 함수"""
    generator = SeptemberRealisticDataGenerator()

    print("=" * 60)
    print("9월 현실적 트레이딩 데이터 생성 시작")
    print("=" * 60)

    # 현실적 데이터 생성
    success = generator.generate_september_realistic_data(total_trades=100)

    if success:
        print("\n데이터 생성 완료!")

        # 요약 보고서 출력
        report = generator.generate_summary_report()
        print(report)
    else:
        print("데이터 생성 실패")

    print("\n" + "=" * 60)
    print("9월 현실적 데이터 생성 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()