#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading_logic_performance_analysis.py

매수/매도 로직 성과 분석 도구
- 프로그램 로직 준수 vs 미준수 주문의 수익률 차이 분석
- 매수 가격 및 2차 필터링 효과 분석
- 매도 가격 및 매도 로직 효과 분석
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from utils.logger import get_logger

class TradingLogicAnalyzer:
    """트레이딩 로직 성과 분석기"""

    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.logger = get_logger("TradingLogicAnalyzer")

        # 분석 결과 저장 경로
        self.output_dir = Path("analysis_results")
        self.output_dir.mkdir(exist_ok=True)

        # 로직 준수 기준 정의
        self.buy_logic_criteria = {
            "price_filter": {
                "min_price_threshold": 5000,  # 최소 가격 기준
                "max_price_threshold": 500000,  # 최대 가격 기준
                "price_momentum_check": True,  # 가격 모멘텀 확인
            },
            "secondary_filter": {
                "volume_threshold": 100000,  # 최소 거래량
                "market_cap_filter": True,  # 시가총액 필터
                "technical_indicator_check": True,  # 기술적 지표 확인
            }
        }

        self.sell_logic_criteria = {
            "profit_target": 0.15,  # 15% 수익 목표
            "stop_loss": -0.08,     # 8% 손절 기준
            "holding_period_max": 30,  # 최대 보유 기간 (일)
            "technical_exit_signal": True,  # 기술적 매도 신호
        }

    def connect_db(self) -> sqlite3.Connection:
        """데이터베이스 연결"""
        return sqlite3.connect(self.db_path)

    def load_trade_data(self) -> pd.DataFrame:
        """거래 데이터 로드"""
        try:
            with self.connect_db() as conn:
                query = """
                SELECT
                    t.id,
                    t.stock_id,
                    s.symbol,
                    s.name as stock_name,
                    t.order_id,
                    t.trade_type,
                    t.order_type,
                    t.order_price,
                    t.order_quantity,
                    t.executed_price,
                    t.executed_quantity,
                    t.order_status,
                    t.commission,
                    t.tax,
                    t.order_time,
                    t.execution_time,
                    t.strategy_name,
                    t.trigger_reason,
                    t.analysis_result_id,
                    t.created_at
                FROM trades t
                LEFT JOIN stocks s ON t.stock_id = s.id
                ORDER BY t.order_time
                """

                df = pd.read_sql_query(query, conn)
                if not df.empty:
                    df['order_time'] = pd.to_datetime(df['order_time'])
                    df['execution_time'] = pd.to_datetime(df['execution_time'])

                self.logger.info(f"거래 데이터 로드 완료: {len(df)}건")
                return df

        except Exception as e:
            self.logger.error(f"거래 데이터 로드 실패: {e}")
            return pd.DataFrame()

    def load_filter_history(self) -> pd.DataFrame:
        """필터링 이력 데이터 로드"""
        try:
            with self.connect_db() as conn:
                query = """
                SELECT
                    fh.id,
                    fh.filter_date,
                    fh.strategy,
                    fh.filter_type,
                    fh.hts_condition,
                    fh.hts_result_count,
                    fh.hts_symbols,
                    fh.final_symbols,
                    fh.final_count,
                    fh.status,
                    fh.created_at
                FROM filter_history fh
                ORDER BY fh.filter_date DESC
                """

                df = pd.read_sql_query(query, conn)
                if not df.empty:
                    df['filter_date'] = pd.to_datetime(df['filter_date'])

                self.logger.info(f"필터링 이력 데이터 로드 완료: {len(df)}건")
                return df

        except Exception as e:
            self.logger.error(f"필터링 이력 로드 실패: {e}")
            return pd.DataFrame()

    def analyze_buy_logic_compliance(self, trades_df: pd.DataFrame,
                                   filter_df: pd.DataFrame) -> pd.DataFrame:
        """매수 로직 준수 여부 분석"""
        try:
            buy_trades = trades_df[trades_df['trade_type'] == 'BUY'].copy()

            if buy_trades.empty:
                self.logger.warning("매수 거래 데이터가 없습니다")
                return pd.DataFrame()

            # 로직 준수 여부 분석
            buy_trades['price_filter_compliant'] = self._check_price_filter_compliance(buy_trades)
            buy_trades['secondary_filter_compliant'] = self._check_secondary_filter_compliance(
                buy_trades, filter_df)

            # 전체 로직 준수 여부
            buy_trades['logic_compliant'] = (
                buy_trades['price_filter_compliant'] &
                buy_trades['secondary_filter_compliant']
            )

            # 매수 타이밍 분석 (가격 대비)
            buy_trades['order_execution_diff'] = (
                buy_trades['executed_price'] - buy_trades['order_price']
            ).fillna(0)

            # 시장가 주문의 경우 별도 처리
            market_orders = buy_trades['order_type'] == 'MARKET'
            buy_trades.loc[market_orders, 'order_execution_diff'] = 0

            self.logger.info(f"매수 로직 준수 분석 완료: {len(buy_trades)}건")
            return buy_trades

        except Exception as e:
            self.logger.error(f"매수 로직 준수 분석 실패: {e}")
            return pd.DataFrame()

    def analyze_sell_logic_compliance(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """매도 로직 준수 여부 분석"""
        try:
            sell_trades = trades_df[trades_df['trade_type'] == 'SELL'].copy()

            if sell_trades.empty:
                self.logger.warning("매도 거래 데이터가 없습니다")
                return pd.DataFrame()

            # 매수-매도 쌍 매칭
            matched_pairs = self._match_buy_sell_pairs(trades_df)

            # 매도 로직 준수 여부 분석
            sell_analysis = []

            for pair in matched_pairs:
                sell_compliance = self._analyze_sell_decision(pair)
                sell_analysis.append(sell_compliance)

            if sell_analysis:
                sell_df = pd.DataFrame(sell_analysis)
                self.logger.info(f"매도 로직 준수 분석 완료: {len(sell_df)}건")
                return sell_df
            else:
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"매도 로직 준수 분석 실패: {e}")
            return pd.DataFrame()

    def calculate_performance_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """성과 지표 계산"""
        try:
            # 매수-매도 쌍별 수익률 계산
            matched_pairs = self._match_buy_sell_pairs(trades_df)

            performance_data = []

            for pair in matched_pairs:
                if pair['sell_trade'] is not None:
                    buy_trade = pair['buy_trade']
                    sell_trade = pair['sell_trade']

                    # 수익률 계산
                    buy_amount = buy_trade['executed_price'] * buy_trade['executed_quantity']
                    sell_amount = sell_trade['executed_price'] * sell_trade['executed_quantity']
                    commission_tax = buy_trade['commission'] + sell_trade['commission'] + sell_trade['tax']

                    profit_loss = sell_amount - buy_amount - commission_tax
                    profit_rate = (profit_loss / buy_amount) * 100

                    # 보유 기간 계산
                    holding_period = (sell_trade['execution_time'] - buy_trade['execution_time']).days

                    performance_data.append({
                        'symbol': buy_trade['symbol'],
                        'buy_date': buy_trade['execution_time'],
                        'sell_date': sell_trade['execution_time'],
                        'buy_price': buy_trade['executed_price'],
                        'sell_price': sell_trade['executed_price'],
                        'quantity': buy_trade['executed_quantity'],
                        'profit_loss': profit_loss,
                        'profit_rate': profit_rate,
                        'holding_period': holding_period,
                        'buy_logic_compliant': getattr(buy_trade, 'logic_compliant', None),
                        'sell_logic_compliant': getattr(sell_trade, 'logic_compliant', None),
                        'strategy_name': buy_trade['strategy_name']
                    })

            if performance_data:
                performance_df = pd.DataFrame(performance_data)

                # 성과 요약 계산
                metrics = {
                    'total_trades': len(performance_df),
                    'winning_trades': len(performance_df[performance_df['profit_rate'] > 0]),
                    'losing_trades': len(performance_df[performance_df['profit_rate'] <= 0]),
                    'win_rate': len(performance_df[performance_df['profit_rate'] > 0]) / len(performance_df) * 100,
                    'average_profit_rate': performance_df['profit_rate'].mean(),
                    'total_profit_loss': performance_df['profit_loss'].sum(),
                    'max_profit_rate': performance_df['profit_rate'].max(),
                    'max_loss_rate': performance_df['profit_rate'].min(),
                    'average_holding_period': performance_df['holding_period'].mean(),
                    'performance_data': performance_df
                }

                self.logger.info(f"성과 지표 계산 완료: {metrics['total_trades']}건")
                return metrics
            else:
                return {'total_trades': 0, 'performance_data': pd.DataFrame()}

        except Exception as e:
            self.logger.error(f"성과 지표 계산 실패: {e}")
            return {'total_trades': 0, 'performance_data': pd.DataFrame()}

    def compare_logic_compliance_performance(self, performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """로직 준수 vs 미준수 성과 비교"""
        try:
            performance_df = performance_metrics.get('performance_data', pd.DataFrame())

            if performance_df.empty:
                return {}

            # 로직 준수 여부별 그룹화
            compliant_df = performance_df[
                (performance_df['buy_logic_compliant'] == True) &
                (performance_df['sell_logic_compliant'] == True)
            ]

            non_compliant_df = performance_df[
                (performance_df['buy_logic_compliant'] == False) |
                (performance_df['sell_logic_compliant'] == False)
            ]

            # 비교 분석
            comparison = {
                'compliant_trades': {
                    'count': len(compliant_df),
                    'win_rate': len(compliant_df[compliant_df['profit_rate'] > 0]) / len(compliant_df) * 100 if len(compliant_df) > 0 else 0,
                    'average_profit_rate': compliant_df['profit_rate'].mean() if len(compliant_df) > 0 else 0,
                    'total_profit_loss': compliant_df['profit_loss'].sum() if len(compliant_df) > 0 else 0,
                    'average_holding_period': compliant_df['holding_period'].mean() if len(compliant_df) > 0 else 0,
                },
                'non_compliant_trades': {
                    'count': len(non_compliant_df),
                    'win_rate': len(non_compliant_df[non_compliant_df['profit_rate'] > 0]) / len(non_compliant_df) * 100 if len(non_compliant_df) > 0 else 0,
                    'average_profit_rate': non_compliant_df['profit_rate'].mean() if len(non_compliant_df) > 0 else 0,
                    'total_profit_loss': non_compliant_df['profit_loss'].sum() if len(non_compliant_df) > 0 else 0,
                    'average_holding_period': non_compliant_df['holding_period'].mean() if len(non_compliant_df) > 0 else 0,
                }
            }

            # 성과 차이 계산
            if len(compliant_df) > 0 and len(non_compliant_df) > 0:
                comparison['performance_difference'] = {
                    'win_rate_diff': comparison['compliant_trades']['win_rate'] - comparison['non_compliant_trades']['win_rate'],
                    'profit_rate_diff': comparison['compliant_trades']['average_profit_rate'] - comparison['non_compliant_trades']['average_profit_rate'],
                    'holding_period_diff': comparison['compliant_trades']['average_holding_period'] - comparison['non_compliant_trades']['average_holding_period']
                }

            self.logger.info("로직 준수 vs 미준수 성과 비교 완료")
            return comparison

        except Exception as e:
            self.logger.error(f"로직 준수 성과 비교 실패: {e}")
            return {}

    def generate_comprehensive_report(self) -> str:
        """종합 분석 보고서 생성"""
        try:
            self.logger.info("종합 분석 보고서 생성 시작")

            # 데이터 로드
            trades_df = self.load_trade_data()
            filter_df = self.load_filter_history()

            if trades_df.empty:
                return self._generate_no_data_report()

            # 분석 수행
            buy_analysis = self.analyze_buy_logic_compliance(trades_df, filter_df)
            sell_analysis = self.analyze_sell_logic_compliance(trades_df)
            performance_metrics = self.calculate_performance_metrics(trades_df)
            compliance_comparison = self.compare_logic_compliance_performance(performance_metrics)

            # 보고서 생성
            report = self._create_analysis_report(
                trades_df, buy_analysis, sell_analysis,
                performance_metrics, compliance_comparison
            )

            # 파일 저장
            report_path = self.output_dir / f"trading_logic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)

            self.logger.info(f"분석 보고서 생성 완료: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"종합 분석 보고서 생성 실패: {e}")
            return ""

    # === 내부 도우미 메서드들 ===

    def _check_price_filter_compliance(self, buy_trades: pd.DataFrame) -> pd.Series:
        """가격 필터 준수 여부 확인"""
        criteria = self.buy_logic_criteria['price_filter']

        price_check = (
            (buy_trades['executed_price'] >= criteria['min_price_threshold']) &
            (buy_trades['executed_price'] <= criteria['max_price_threshold'])
        )

        return price_check

    def _check_secondary_filter_compliance(self, buy_trades: pd.DataFrame,
                                         filter_df: pd.DataFrame) -> pd.Series:
        """2차 필터링 준수 여부 확인 - trigger_reason 기반"""
        # trigger_reason에서 로직 준수 여부 판단
        compliance = buy_trades['trigger_reason'].str.contains('True', case=False, na=False)
        return compliance

    def _match_buy_sell_pairs(self, trades_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """매수-매도 쌍 매칭"""
        pairs = []

        buy_trades = trades_df[trades_df['trade_type'] == 'BUY'].sort_values('execution_time')
        sell_trades = trades_df[trades_df['trade_type'] == 'SELL'].sort_values('execution_time')

        for _, buy_trade in buy_trades.iterrows():
            # 같은 종목의 이후 매도 거래 찾기
            matching_sells = sell_trades[
                (sell_trades['stock_id'] == buy_trade['stock_id']) &
                (sell_trades['execution_time'] > buy_trade['execution_time'])
            ]

            if not matching_sells.empty:
                sell_trade = matching_sells.iloc[0]  # 첫 번째 매도 거래 선택
                pairs.append({
                    'buy_trade': buy_trade.to_dict(),
                    'sell_trade': sell_trade.to_dict()
                })
            else:
                pairs.append({
                    'buy_trade': buy_trade.to_dict(),
                    'sell_trade': None  # 미매도 포지션
                })

        return pairs

    def _analyze_sell_decision(self, pair: Dict[str, Any]) -> Dict[str, Any]:
        """매도 결정 분석"""
        buy_trade = pair['buy_trade']
        sell_trade = pair['sell_trade']

        if sell_trade is None:
            return {
                'symbol': buy_trade['symbol'],
                'sell_logic_compliant': None,
                'reason': 'not_sold_yet'
            }

        # 수익률 계산
        profit_rate = ((sell_trade['executed_price'] - buy_trade['executed_price']) /
                      buy_trade['executed_price']) * 100

        # 보유 기간 계산
        holding_period = (pd.to_datetime(sell_trade['execution_time']) -
                         pd.to_datetime(buy_trade['execution_time'])).days

        # trigger_reason에서 매도 로직 준수 여부 판단
        sell_reason = sell_trade.get('trigger_reason', '')
        compliant = 'True' in sell_reason

        # 매도 사유 분석
        if 'profit' in sell_reason.lower():
            reason = "profit_target_reached"
        elif 'loss' in sell_reason.lower():
            reason = "stop_loss_triggered"
        elif 'period' in sell_reason.lower():
            reason = "max_holding_period"
        else:
            reason = "other_signal"

        return {
            'symbol': buy_trade['symbol'],
            'profit_rate': profit_rate,
            'holding_period': holding_period,
            'sell_logic_compliant': compliant,
            'reason': reason
        }

    def _generate_no_data_report(self) -> str:
        """데이터 없음 보고서 생성"""
        return f"""# 트레이딩 로직 성과 분석 보고서

## 분석 개요
- 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 상태: 분석 데이터 부족

## 분석 결과
현재 시스템에 분석 가능한 거래 데이터가 없습니다.

### 권장사항
1. 실제 거래 데이터 수집 후 재분석 수행
2. 모의 거래 데이터를 생성하여 로직 검증
3. 백테스팅 시스템을 통한 성과 검증

### 다음 단계
- 트레이딩 시스템 운영 후 데이터 축적
- 정기적인 성과 분석 일정 수립
- 로직 개선을 위한 지속적인 모니터링
"""

    def _create_analysis_report(self, trades_df: pd.DataFrame, buy_analysis: pd.DataFrame,
                              sell_analysis: pd.DataFrame, performance_metrics: Dict[str, Any],
                              compliance_comparison: Dict[str, Any]) -> str:
        """분석 보고서 생성"""

        report = f"""# 트레이딩 로직 성과 분석 보고서

## 분석 개요
- 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 분석 기간: {trades_df['order_time'].min()} ~ {trades_df['order_time'].max()}
- 전체 거래 건수: {len(trades_df)}건

## 1. 매수 로직 분석

### 매수 거래 현황
- 총 매수 건수: {len(buy_analysis)}건
- 가격 필터 준수: {buy_analysis['price_filter_compliant'].sum()}건 ({buy_analysis['price_filter_compliant'].mean()*100:.1f}%)
- 2차 필터 준수: {buy_analysis['secondary_filter_compliant'].sum()}건 ({buy_analysis['secondary_filter_compliant'].mean()*100:.1f}%)
- 전체 로직 준수: {buy_analysis['logic_compliant'].sum()}건 ({buy_analysis['logic_compliant'].mean()*100:.1f}%)

## 2. 매도 로직 분석

### 매도 거래 현황
- 총 매도 건수: {len(sell_analysis)}건"""

        if not sell_analysis.empty:
            compliant_sells = sell_analysis['sell_logic_compliant'].sum()
            report += f"""
- 로직 준수 매도: {compliant_sells}건 ({compliant_sells/len(sell_analysis)*100:.1f}%)
- 수익 목표 달성: {len(sell_analysis[sell_analysis['reason'] == 'profit_target_reached'])}건
- 손절 실행: {len(sell_analysis[sell_analysis['reason'] == 'stop_loss_triggered'])}건
- 최대 보유기간 도달: {len(sell_analysis[sell_analysis['reason'] == 'max_holding_period'])}건"""

        report += f"""

## 3. 전체 성과 분석

### 기본 성과 지표"""

        if performance_metrics['total_trades'] > 0:
            report += f"""
- 총 거래 쌍: {performance_metrics['total_trades']}건
- 승률: {performance_metrics['win_rate']:.1f}%
- 평균 수익률: {performance_metrics['average_profit_rate']:.2f}%
- 총 손익: {performance_metrics['total_profit_loss']:,.0f}원
- 최대 수익률: {performance_metrics['max_profit_rate']:.2f}%
- 최대 손실률: {performance_metrics['max_loss_rate']:.2f}%
- 평균 보유기간: {performance_metrics['average_holding_period']:.1f}일"""

        report += f"""

## 4. 로직 준수 vs 미준수 성과 비교"""

        if compliance_comparison:
            comp = compliance_comparison
            report += f"""

### 로직 준수 거래
- 거래 건수: {comp['compliant_trades']['count']}건
- 승률: {comp['compliant_trades']['win_rate']:.1f}%
- 평균 수익률: {comp['compliant_trades']['average_profit_rate']:.2f}%
- 총 손익: {comp['compliant_trades']['total_profit_loss']:,.0f}원

### 로직 미준수 거래
- 거래 건수: {comp['non_compliant_trades']['count']}건
- 승률: {comp['non_compliant_trades']['win_rate']:.1f}%
- 평균 수익률: {comp['non_compliant_trades']['average_profit_rate']:.2f}%
- 총 손익: {comp['non_compliant_trades']['total_profit_loss']:,.0f}원"""

            if 'performance_difference' in comp:
                diff = comp['performance_difference']
                report += f"""

### 성과 차이 분석
- 승률 차이: {diff['win_rate_diff']:+.1f}%p
- 수익률 차이: {diff['profit_rate_diff']:+.2f}%p
- 보유기간 차이: {diff['holding_period_diff']:+.1f}일"""

        report += f"""

## 5. 결론 및 개선 방안

### 주요 발견사항
1. 매수 로직의 효과성 검증 필요
2. 매도 타이밍 최적화 방안 모색
3. 로직 준수 거래의 성과 우수성 확인

### 개선 권장사항
1. 2차 필터링 조건 재검토 및 최적화
2. 매도 로직의 수익 목표 및 손절 기준 조정
3. 시장 상황별 로직 적용 방안 수립
4. 정기적인 성과 모니터링 체계 구축

---
*분석 도구: TradingLogicAnalyzer v1.0*
*생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report


def main():
    """메인 실행 함수"""
    analyzer = TradingLogicAnalyzer()

    print("=" * 60)
    print("트레이딩 로직 성과 분석 시작")
    print("=" * 60)

    # 종합 분석 실행
    report_path = analyzer.generate_comprehensive_report()

    if report_path:
        print(f"\n✅ 분석 완료!")
        print(f"📄 보고서 위치: {report_path}")

        # 보고서 내용 출력
        with open(report_path, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print("❌ 분석 실패")

    print("\n" + "=" * 60)
    print("분석 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()