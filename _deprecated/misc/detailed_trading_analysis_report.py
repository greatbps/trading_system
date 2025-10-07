#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/detailed_trading_analysis_report.py

상세 트레이딩 성과 분석 보고서 생성기
- 매수/매도 로직 준수 여부별 상세 분석
- 시나리오별 성과 비교
- 실제 데이터 기반 개선 방안 제시
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import json
from pathlib import Path
from utils.logger import get_logger

class DetailedTradingAnalyzer:
    """상세 트레이딩 분석기"""

    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.logger = get_logger("DetailedTradingAnalyzer")

        # 출력 디렉토리
        self.output_dir = Path("analysis_results")
        self.output_dir.mkdir(exist_ok=True)

    def connect_db(self) -> sqlite3.Connection:
        """데이터베이스 연결"""
        return sqlite3.connect(self.db_path)

    def load_comprehensive_trading_data(self) -> pd.DataFrame:
        """종합 거래 데이터 로드"""
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
                WHERE t.strategy_name = 'sample_trading'
                ORDER BY t.stock_id, t.order_time
                """

                df = pd.read_sql_query(query, conn)
                if not df.empty:
                    df['order_time'] = pd.to_datetime(df['order_time'])
                    df['execution_time'] = pd.to_datetime(df['execution_time'])

                self.logger.info(f"종합 거래 데이터 로드: {len(df)}건")
                return df

        except Exception as e:
            self.logger.error(f"거래 데이터 로드 실패: {e}")
            return pd.DataFrame()

    def load_trade_history_data(self) -> pd.DataFrame:
        """거래 이력 데이터 로드"""
        try:
            with self.connect_db() as conn:
                query = """
                SELECT
                    th.*,
                    s.symbol,
                    s.name as stock_name,
                    bt.trigger_reason as buy_trigger_reason,
                    st.trigger_reason as sell_trigger_reason
                FROM trade_history th
                LEFT JOIN stocks s ON th.stock_id = s.id
                LEFT JOIN trades bt ON th.buy_trade_id = bt.id
                LEFT JOIN trades st ON th.sell_trade_id = st.id
                WHERE th.strategy_name = 'sample_trading'
                ORDER BY th.buy_date
                """

                df = pd.read_sql_query(query, conn)
                if not df.empty:
                    df['buy_date'] = pd.to_datetime(df['buy_date'])
                    df['sell_date'] = pd.to_datetime(df['sell_date'])

                self.logger.info(f"거래 이력 데이터 로드: {len(df)}건")
                return df

        except Exception as e:
            self.logger.error(f"거래 이력 로드 실패: {e}")
            return pd.DataFrame()

    def classify_trades_by_logic_compliance(self, history_df: pd.DataFrame) -> pd.DataFrame:
        """로직 준수 여부별 거래 분류"""
        try:
            if history_df.empty:
                return pd.DataFrame()

            # 매수 로직 준수 여부 판단
            history_df['buy_logic_compliant'] = history_df['buy_trigger_reason'].str.contains('True', case=False, na=False)

            # 매도 로직 준수 여부 판단
            history_df['sell_logic_compliant'] = history_df['sell_trigger_reason'].str.contains('True', case=False, na=False)

            # 전체 로직 준수 여부
            history_df['both_logic_compliant'] = history_df['buy_logic_compliant'] & history_df['sell_logic_compliant']

            # 로직 준수 카테고리 분류
            def classify_compliance(row):
                if row['buy_logic_compliant'] and row['sell_logic_compliant']:
                    return 'both_compliant'
                elif row['buy_logic_compliant'] and not row['sell_logic_compliant']:
                    return 'buy_only_compliant'
                elif not row['buy_logic_compliant'] and row['sell_logic_compliant']:
                    return 'sell_only_compliant'
                else:
                    return 'neither_compliant'

            history_df['compliance_category'] = history_df.apply(classify_compliance, axis=1)

            self.logger.info("로직 준수 여부별 거래 분류 완료")
            return history_df

        except Exception as e:
            self.logger.error(f"로직 준수 분류 실패: {e}")
            return pd.DataFrame()

    def analyze_performance_by_compliance(self, classified_df: pd.DataFrame) -> Dict[str, Any]:
        """로직 준수 여부별 성과 분석"""
        try:
            if classified_df.empty:
                return {}

            results = {}

            # 카테고리별 분석
            categories = ['both_compliant', 'buy_only_compliant', 'sell_only_compliant', 'neither_compliant']

            for category in categories:
                category_df = classified_df[classified_df['compliance_category'] == category]

                if len(category_df) > 0:
                    # 기본 통계
                    total_trades = len(category_df)
                    winning_trades = len(category_df[category_df['profit_loss_rate'] > 0])
                    losing_trades = len(category_df[category_df['profit_loss_rate'] <= 0])
                    win_rate = (winning_trades / total_trades) * 100

                    # 수익률 통계
                    avg_profit_rate = category_df['profit_loss_rate'].mean()
                    max_profit_rate = category_df['profit_loss_rate'].max()
                    min_profit_rate = category_df['profit_loss_rate'].min()
                    std_profit_rate = category_df['profit_loss_rate'].std()

                    # 손익 통계
                    total_profit_loss = category_df['profit_loss'].sum()
                    avg_profit_loss = category_df['profit_loss'].mean()

                    # 보유기간 통계
                    avg_holding_period = category_df['holding_period_days'].mean()
                    max_holding_period = category_df['holding_period_days'].max()
                    min_holding_period = category_df['holding_period_days'].min()

                    # 샤프 비율 근사 계산 (일간 수익률 기준)
                    daily_returns = category_df['profit_loss_rate'] / category_df['holding_period_days']
                    sharpe_ratio = daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0

                    results[category] = {
                        'total_trades': total_trades,
                        'winning_trades': winning_trades,
                        'losing_trades': losing_trades,
                        'win_rate': win_rate,
                        'avg_profit_rate': avg_profit_rate,
                        'max_profit_rate': max_profit_rate,
                        'min_profit_rate': min_profit_rate,
                        'std_profit_rate': std_profit_rate,
                        'total_profit_loss': total_profit_loss,
                        'avg_profit_loss': avg_profit_loss,
                        'avg_holding_period': avg_holding_period,
                        'max_holding_period': max_holding_period,
                        'min_holding_period': min_holding_period,
                        'sharpe_ratio': sharpe_ratio
                    }
                else:
                    results[category] = {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'win_rate': 0,
                        'avg_profit_rate': 0,
                        'max_profit_rate': 0,
                        'min_profit_rate': 0,
                        'std_profit_rate': 0,
                        'total_profit_loss': 0,
                        'avg_profit_loss': 0,
                        'avg_holding_period': 0,
                        'max_holding_period': 0,
                        'min_holding_period': 0,
                        'sharpe_ratio': 0
                    }

            self.logger.info("로직 준수별 성과 분석 완료")
            return results

        except Exception as e:
            self.logger.error(f"성과 분석 실패: {e}")
            return {}

    def analyze_stock_level_performance(self, classified_df: pd.DataFrame) -> Dict[str, Any]:
        """종목별 성과 분석"""
        try:
            if classified_df.empty:
                return {}

            stock_performance = {}

            for symbol in classified_df['symbol'].unique():
                stock_df = classified_df[classified_df['symbol'] == symbol]
                stock_name = stock_df.iloc[0]['stock_name']

                # 종목별 통계
                total_trades = len(stock_df)
                total_profit_loss = stock_df['profit_loss'].sum()
                avg_profit_rate = stock_df['profit_loss_rate'].mean()
                win_rate = len(stock_df[stock_df['profit_loss_rate'] > 0]) / total_trades * 100

                # 로직 준수별 분석
                compliant_df = stock_df[stock_df['both_logic_compliant'] == True]
                non_compliant_df = stock_df[stock_df['both_logic_compliant'] == False]

                compliant_performance = {
                    'trades': len(compliant_df),
                    'avg_profit_rate': compliant_df['profit_loss_rate'].mean() if len(compliant_df) > 0 else 0,
                    'total_profit_loss': compliant_df['profit_loss'].sum() if len(compliant_df) > 0 else 0
                }

                non_compliant_performance = {
                    'trades': len(non_compliant_df),
                    'avg_profit_rate': non_compliant_df['profit_loss_rate'].mean() if len(non_compliant_df) > 0 else 0,
                    'total_profit_loss': non_compliant_df['profit_loss'].sum() if len(non_compliant_df) > 0 else 0
                }

                stock_performance[symbol] = {
                    'name': stock_name,
                    'total_trades': total_trades,
                    'total_profit_loss': total_profit_loss,
                    'avg_profit_rate': avg_profit_rate,
                    'win_rate': win_rate,
                    'compliant': compliant_performance,
                    'non_compliant': non_compliant_performance
                }

            self.logger.info(f"종목별 성과 분석 완료: {len(stock_performance)}개 종목")
            return stock_performance

        except Exception as e:
            self.logger.error(f"종목별 분석 실패: {e}")
            return {}

    def calculate_risk_metrics(self, classified_df: pd.DataFrame) -> Dict[str, Any]:
        """리스크 지표 계산"""
        try:
            if classified_df.empty:
                return {}

            risk_metrics = {}

            # 전체 포트폴리오 리스크
            returns = classified_df['profit_loss_rate'].values

            # Value at Risk (95% 신뢰구간)
            var_95 = np.percentile(returns, 5)

            # Conditional Value at Risk (Expected Shortfall)
            cvar_95 = returns[returns <= var_95].mean()

            # Maximum Drawdown 근사계산
            cumulative_returns = (1 + returns/100).cumprod()
            peak = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - peak) / peak
            max_drawdown = drawdown.min()

            # 변동성 (수익률 표준편차)
            volatility = returns.std()

            risk_metrics['portfolio'] = {
                'var_95': var_95,
                'cvar_95': cvar_95,
                'max_drawdown': max_drawdown * 100,
                'volatility': volatility
            }

            # 로직 준수별 리스크
            for compliance in [True, False]:
                subset_df = classified_df[classified_df['both_logic_compliant'] == compliance]
                if len(subset_df) > 0:
                    subset_returns = subset_df['profit_loss_rate'].values

                    subset_var = np.percentile(subset_returns, 5)
                    subset_cvar = subset_returns[subset_returns <= subset_var].mean()
                    subset_vol = subset_returns.std()

                    label = 'compliant' if compliance else 'non_compliant'
                    risk_metrics[label] = {
                        'var_95': subset_var,
                        'cvar_95': subset_cvar,
                        'volatility': subset_vol
                    }

            self.logger.info("리스크 지표 계산 완료")
            return risk_metrics

        except Exception as e:
            self.logger.error(f"리스크 지표 계산 실패: {e}")
            return {}

    def generate_comprehensive_report(self) -> str:
        """종합 분석 보고서 생성"""
        try:
            self.logger.info("종합 상세 분석 보고서 생성 시작")

            # 데이터 로드
            trades_df = self.load_comprehensive_trading_data()
            history_df = self.load_trade_history_data()

            if history_df.empty:
                return self._create_no_data_report()

            # 분석 수행
            classified_df = self.classify_trades_by_logic_compliance(history_df)
            performance_analysis = self.analyze_performance_by_compliance(classified_df)
            stock_analysis = self.analyze_stock_level_performance(classified_df)
            risk_analysis = self.calculate_risk_metrics(classified_df)

            # 보고서 생성
            report = self._create_detailed_report(
                classified_df, performance_analysis, stock_analysis, risk_analysis
            )

            # 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.output_dir / f"detailed_trading_analysis_{timestamp}.md"

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)

            self.logger.info(f"상세 분석 보고서 생성 완료: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"종합 보고서 생성 실패: {e}")
            return ""

    def _create_detailed_report(self, classified_df: pd.DataFrame,
                              performance_analysis: Dict[str, Any],
                              stock_analysis: Dict[str, Any],
                              risk_analysis: Dict[str, Any]) -> str:
        """상세 보고서 생성"""

        report = f"""# 트레이딩 로직 성과 상세 분석 보고서

## 📊 분석 개요
- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **분석 기간**: {classified_df['buy_date'].min()} ~ {classified_df['sell_date'].max()}
- **총 완료 거래**: {len(classified_df)}건
- **분석 전략**: sample_trading

## 🎯 1. 로직 준수 여부별 성과 분석

### 1.1 전체 로직 준수 (매수 + 매도)
"""

        both_compliant = performance_analysis.get('both_compliant', {})
        if both_compliant.get('total_trades', 0) > 0:
            report += f"""
- **거래 건수**: {both_compliant['total_trades']}건
- **승률**: {both_compliant['win_rate']:.1f}%
- **평균 수익률**: {both_compliant['avg_profit_rate']:.2f}%
- **총 손익**: {both_compliant['total_profit_loss']:,.0f}원
- **평균 보유기간**: {both_compliant['avg_holding_period']:.1f}일
- **최대 수익률**: {both_compliant['max_profit_rate']:.2f}%
- **최대 손실률**: {both_compliant['min_profit_rate']:.2f}%
- **수익률 변동성**: {both_compliant['std_profit_rate']:.2f}%
- **샤프 비율**: {both_compliant['sharpe_ratio']:.3f}
"""
        else:
            report += "\n- 로직을 완전히 준수한 거래가 없습니다.\n"

        report += """
### 1.2 매수만 로직 준수
"""

        buy_only = performance_analysis.get('buy_only_compliant', {})
        if buy_only.get('total_trades', 0) > 0:
            report += f"""
- **거래 건수**: {buy_only['total_trades']}건
- **승률**: {buy_only['win_rate']:.1f}%
- **평균 수익률**: {buy_only['avg_profit_rate']:.2f}%
- **총 손익**: {buy_only['total_profit_loss']:,.0f}원
- **평균 보유기간**: {buy_only['avg_holding_period']:.1f}일
"""
        else:
            report += "\n- 매수만 로직을 준수한 거래가 없습니다.\n"

        report += """
### 1.3 매도만 로직 준수
"""

        sell_only = performance_analysis.get('sell_only_compliant', {})
        if sell_only.get('total_trades', 0) > 0:
            report += f"""
- **거래 건수**: {sell_only['total_trades']}건
- **승률**: {sell_only['win_rate']:.1f}%
- **평균 수익률**: {sell_only['avg_profit_rate']:.2f}%
- **총 손익**: {sell_only['total_profit_loss']:,.0f}원
- **평균 보유기간**: {sell_only['avg_holding_period']:.1f}일
"""
        else:
            report += "\n- 매도만 로직을 준수한 거래가 없습니다.\n"

        report += """
### 1.4 로직 미준수 거래
"""

        neither = performance_analysis.get('neither_compliant', {})
        if neither.get('total_trades', 0) > 0:
            report += f"""
- **거래 건수**: {neither['total_trades']}건
- **승률**: {neither['win_rate']:.1f}%
- **평균 수익률**: {neither['avg_profit_rate']:.2f}%
- **총 손익**: {neither['total_profit_loss']:,.0f}원
- **평균 보유기간**: {neither['avg_holding_period']:.1f}일
- **최대 수익률**: {neither['max_profit_rate']:.2f}%
- **최대 손실률**: {neither['min_profit_rate']:.2f}%
"""
        else:
            report += "\n- 로직을 전혀 준수하지 않은 거래가 없습니다.\n"

        report += """
## 📈 2. 종목별 성과 분석

| 종목 | 종목명 | 총거래 | 총손익(원) | 평균수익률(%) | 승률(%) | 로직준수거래 | 미준수거래 |
|------|--------|--------|------------|---------------|---------|-------------|-----------|"""

        for symbol, data in stock_analysis.items():
            compliant_trades = data['compliant']['trades']
            non_compliant_trades = data['non_compliant']['trades']

            report += f"""
| {symbol} | {data['name'][:8]} | {data['total_trades']} | {data['total_profit_loss']:,.0f} | {data['avg_profit_rate']:.2f} | {data['win_rate']:.1f} | {compliant_trades} | {non_compliant_trades} |"""

        report += """

### 2.1 종목별 로직 준수 효과
"""

        for symbol, data in stock_analysis.items():
            if data['compliant']['trades'] > 0 and data['non_compliant']['trades'] > 0:
                profit_diff = data['compliant']['avg_profit_rate'] - data['non_compliant']['avg_profit_rate']
                report += f"""
**{symbol} ({data['name']})**
- 로직 준수: 평균 {data['compliant']['avg_profit_rate']:.2f}% (총 {data['compliant']['total_profit_loss']:,.0f}원)
- 로직 미준수: 평균 {data['non_compliant']['avg_profit_rate']:.2f}% (총 {data['non_compliant']['total_profit_loss']:,.0f}원)
- **효과**: {profit_diff:+.2f}%p
"""

        report += """
## ⚠️ 3. 리스크 분석

### 3.1 포트폴리오 리스크 지표
"""

        portfolio_risk = risk_analysis.get('portfolio', {})
        if portfolio_risk:
            report += f"""
- **VaR (95% 신뢰구간)**: {portfolio_risk.get('var_95', 0):.2f}%
- **CVaR (조건부 위험가치)**: {portfolio_risk.get('cvar_95', 0):.2f}%
- **최대 낙폭**: {portfolio_risk.get('max_drawdown', 0):.2f}%
- **변동성**: {portfolio_risk.get('volatility', 0):.2f}%
"""

        report += """
### 3.2 로직 준수별 리스크 비교
"""

        compliant_risk = risk_analysis.get('compliant', {})
        non_compliant_risk = risk_analysis.get('non_compliant', {})

        if compliant_risk and non_compliant_risk:
            report += f"""
| 구분 | VaR(95%) | CVaR | 변동성 |
|------|----------|------|--------|
| 로직 준수 | {compliant_risk.get('var_95', 0):.2f}% | {compliant_risk.get('cvar_95', 0):.2f}% | {compliant_risk.get('volatility', 0):.2f}% |
| 로직 미준수 | {non_compliant_risk.get('var_95', 0):.2f}% | {non_compliant_risk.get('cvar_95', 0):.2f}% | {non_compliant_risk.get('volatility', 0):.2f}% |
"""

        # 성과 비교 및 결론
        report += """
## 🎯 4. 핵심 발견사항

### 4.1 로직 준수의 효과
"""

        # 로직 준수 vs 미준수 비교
        if both_compliant.get('total_trades', 0) > 0 and neither.get('total_trades', 0) > 0:
            win_rate_diff = both_compliant['win_rate'] - neither['win_rate']
            profit_rate_diff = both_compliant['avg_profit_rate'] - neither['avg_profit_rate']

            report += f"""
1. **승률 차이**: 로직 완전 준수 시 {win_rate_diff:+.1f}%p 개선
2. **수익률 차이**: 로직 완전 준수 시 {profit_rate_diff:+.2f}%p 개선
3. **리스크 관리**: 로직 준수 시 변동성 개선 효과
"""

        # 분포 분석
        total_compliant = both_compliant.get('total_trades', 0) + buy_only.get('total_trades', 0) + sell_only.get('total_trades', 0)
        total_trades = len(classified_df)
        compliance_rate = (total_compliant / total_trades) * 100 if total_trades > 0 else 0

        report += f"""
### 4.2 로직 준수 현황
- **전체 거래 중 로직 준수 비율**: {compliance_rate:.1f}%
- **개선 여지**: {100 - compliance_rate:.1f}%p
"""

        report += """
## 💡 5. 개선 권장사항

### 5.1 매수 로직 개선
1. **가격 필터링 강화**: 과도한 고가 종목 매수 제한
2. **2차 필터링 정교화**: AI 분석 신뢰도 기준 상향
3. **시장 상황 고려**: 변동성 높은 구간에서 진입 기준 강화

### 5.2 매도 로직 개선
1. **수익 목표 설정**: 종목별 특성을 고려한 차등 목표
2. **손절 기준 최적화**: 변동성 기반 동적 손절선 적용
3. **보유 기간 관리**: 시장 사이클 고려한 기간 조정

### 5.3 리스크 관리 강화
1. **포지션 사이징**: 변동성 기반 포지션 크기 조정
2. **분산 투자**: 종목 집중도 관리 및 섹터 분산
3. **스톱로스 자동화**: 시스템적 손절 실행 체계 구축

### 5.4 모니터링 체계
1. **실시간 준수율 추적**: 로직 준수 여부 실시간 모니터링
2. **성과 알림**: 목표 대비 성과 편차 시 알림
3. **주기적 재검토**: 월간 로직 효과성 검증

## 📋 6. 액션 플랜

### 단기 (1개월)
- [ ] 매수 가격 필터링 기준 재설정
- [ ] 매도 손절 기준 자동화 구현
- [ ] 로직 준수율 모니터링 대시보드 구축

### 중기 (3개월)
- [ ] AI 분석 모델 정확도 개선
- [ ] 종목별 맞춤형 매도 전략 구현
- [ ] 리스크 지표 기반 포지션 사이징 도입

### 장기 (6개월)
- [ ] 시장 레짐별 적응형 로직 개발
- [ ] 백테스팅 기반 전략 최적화
- [ ] 완전 자동화된 리스크 관리 시스템 구축

---
**분석 도구**: DetailedTradingAnalyzer v1.0
**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**데이터 기간**: {classified_df['buy_date'].min().strftime('%Y-%m-%d')} ~ {classified_df['sell_date'].max().strftime('%Y-%m-%d')}
"""

        return report

    def _create_no_data_report(self) -> str:
        """데이터 없음 보고서"""
        return f"""# 트레이딩 로직 성과 분석 보고서

## ⚠️ 분석 불가
- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **상태**: 완료된 거래 데이터 없음

현재 시스템에 분석 가능한 완료된 거래 쌍이 없습니다.
샘플 데이터를 생성하거나 실제 거래 완료 후 분석을 재시도하세요.
"""


def main():
    """메인 실행 함수"""
    analyzer = DetailedTradingAnalyzer()

    print("=" * 60)
    print("상세 트레이딩 성과 분석 시작")
    print("=" * 60)

    # 상세 분석 실행
    report_path = analyzer.generate_comprehensive_report()

    if report_path:
        print(f"\n분석 완료!")
        print(f"보고서 위치: {report_path}")

        # 보고서 일부 출력
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 처음 100줄만 출력
                lines = content.split('\n')
                for i, line in enumerate(lines[:100]):
                    print(line)
                if len(lines) > 100:
                    print(f"\n... (나머지 {len(lines)-100}줄 생략)")
        except Exception as e:
            print(f"보고서 읽기 실패: {e}")
    else:
        print("분석 실패")

    print("\n" + "=" * 60)
    print("상세 분석 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()