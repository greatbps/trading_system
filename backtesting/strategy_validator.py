#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/strategy_validator.py

전략 검증기 - AI vs 비-AI 전략 성능 비교 및 검증
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats

from .backtesting_engine import BacktestingEngine, BacktestResult, PerformanceMetrics

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    """검증 상태"""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

@dataclass
class ValidationCriteria:
    """검증 기준"""
    min_return: float = 5.0  # 최소 연수익률 (%)
    max_drawdown: float = 20.0  # 최대 낙폭 (%)
    min_sharpe: float = 1.0  # 최소 샤프 비율
    min_win_rate: float = 45.0  # 최소 승률 (%)
    min_trades: int = 50  # 최소 거래 수
    min_profit_factor: float = 1.2  # 최소 수익 팩터
    
    # AI 관련 기준
    min_ai_accuracy: float = 60.0  # 최소 AI 예측 정확도 (%)
    min_ai_improvement: float = 2.0  # AI 사용시 최소 성능 개선 (%)

@dataclass
class ValidationResult:
    """검증 결과"""
    strategy_name: str
    status: ValidationStatus
    criteria: ValidationCriteria
    
    # 성능 검증 결과
    return_check: bool = False
    drawdown_check: bool = False
    sharpe_check: bool = False
    win_rate_check: bool = False
    trades_check: bool = False
    profit_factor_check: bool = False
    
    # AI 검증 결과
    ai_accuracy_check: bool = False
    ai_improvement_check: bool = False
    
    # 상세 메시지
    messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def overall_score(self) -> float:
        """전체 검증 점수 (0-100)"""
        checks = [
            self.return_check, self.drawdown_check, self.sharpe_check,
            self.win_rate_check, self.trades_check, self.profit_factor_check,
            self.ai_accuracy_check, self.ai_improvement_check
        ]
        return (sum(checks) / len(checks)) * 100

@dataclass
class StrategyComparison:
    """전략 비교 결과"""
    strategy_name: str
    with_ai_result: BacktestResult
    without_ai_result: BacktestResult
    
    # 성능 개선 지표
    return_improvement: float = 0.0
    sharpe_improvement: float = 0.0
    drawdown_improvement: float = 0.0
    win_rate_improvement: float = 0.0
    
    # 통계적 유의성
    statistical_significance: bool = False
    p_value: float = 1.0
    
    # AI 효과성
    ai_effectiveness_score: float = 0.0

class StrategyValidator:
    """전략 검증기 - AI 기반 전략 성능 검증"""
    
    def __init__(self, config=None):
        """전략 검증기 초기화"""
        try:
            if config:
                self.backtesting_engine = BacktestingEngine(config)
            else:
                # 기본 설정으로 초기화
                from config import get_config
                default_config = get_config()
                self.backtesting_engine = BacktestingEngine(default_config)
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"백테스팅 엔진 초기화 실패: {e}")
            self.backtesting_engine = None
    
    async def validate_strategy(
        self,
        strategy_name: str,
        backtest_result: BacktestResult,
        criteria: Optional[ValidationCriteria] = None
    ) -> ValidationResult:
        """
        전략 검증 수행
        
        Args:
            strategy_name: 전략 이름
            backtest_result: 백테스팅 결과
            criteria: 검증 기준 (None이면 기본값 사용)
        
        Returns:
            ValidationResult: 검증 결과
        """
        try:
            if criteria is None:
                criteria = ValidationCriteria()
            
            result = ValidationResult(
                strategy_name=strategy_name,
                status=ValidationStatus.PASSED,
                criteria=criteria
            )
            
            metrics = backtest_result.metrics
            
            # 1. 수익률 검증
            if metrics.annual_return >= criteria.min_return:
                result.return_check = True
                result.messages.append(f"✅ 연수익률: {metrics.annual_return:.2f}% (기준: {criteria.min_return}%)")
            else:
                result.return_check = False
                result.messages.append(f"❌ 연수익률: {metrics.annual_return:.2f}% (기준: {criteria.min_return}%)")
            
            # 2. 최대 낙폭 검증
            if metrics.max_drawdown <= criteria.max_drawdown:
                result.drawdown_check = True
                result.messages.append(f"✅ 최대 낙폭: {metrics.max_drawdown:.2f}% (기준: {criteria.max_drawdown}%)")
            else:
                result.drawdown_check = False
                result.messages.append(f"❌ 최대 낙폭: {metrics.max_drawdown:.2f}% (기준: {criteria.max_drawdown}%)")
            
            # 3. 샤프 비율 검증
            if metrics.sharpe_ratio >= criteria.min_sharpe:
                result.sharpe_check = True
                result.messages.append(f"✅ 샤프 비율: {metrics.sharpe_ratio:.2f} (기준: {criteria.min_sharpe})")
            else:
                result.sharpe_check = False
                result.messages.append(f"❌ 샤프 비율: {metrics.sharpe_ratio:.2f} (기준: {criteria.min_sharpe})")
            
            # 4. 승률 검증
            if metrics.win_rate >= criteria.min_win_rate:
                result.win_rate_check = True
                result.messages.append(f"✅ 승률: {metrics.win_rate:.2f}% (기준: {criteria.min_win_rate}%)")
            else:
                result.win_rate_check = False
                result.messages.append(f"❌ 승률: {metrics.win_rate:.2f}% (기준: {criteria.min_win_rate}%)")
            
            # 5. 거래 수 검증
            if metrics.total_trades >= criteria.min_trades:
                result.trades_check = True
                result.messages.append(f"✅ 총 거래 수: {metrics.total_trades} (기준: {criteria.min_trades})")
            else:
                result.trades_check = False
                result.messages.append(f"❌ 총 거래 수: {metrics.total_trades} (기준: {criteria.min_trades})")
                if metrics.total_trades < 10:
                    result.status = ValidationStatus.INSUFFICIENT_DATA
            
            # 6. 수익 팩터 검증
            if metrics.profit_factor >= criteria.min_profit_factor:
                result.profit_factor_check = True
                result.messages.append(f"✅ 수익 팩터: {metrics.profit_factor:.2f} (기준: {criteria.min_profit_factor})")
            else:
                result.profit_factor_check = False
                result.messages.append(f"❌ 수익 팩터: {metrics.profit_factor:.2f} (기준: {criteria.min_profit_factor})")
            
            # 7. AI 정확도 검증 (AI 사용시에만)
            if metrics.ai_accuracy > 0:
                if metrics.ai_accuracy >= criteria.min_ai_accuracy:
                    result.ai_accuracy_check = True
                    result.messages.append(f"✅ AI 예측 정확도: {metrics.ai_accuracy:.2f}% (기준: {criteria.min_ai_accuracy}%)")
                else:
                    result.ai_accuracy_check = False
                    result.messages.append(f"❌ AI 예측 정확도: {metrics.ai_accuracy:.2f}% (기준: {criteria.min_ai_accuracy}%)")
            else:
                result.ai_accuracy_check = True  # AI 미사용시 통과
                result.messages.append("ℹ️ AI 예측 정확도: 미사용")
            
            # 전체 검증 상태 결정
            basic_checks = [
                result.return_check, result.drawdown_check, result.sharpe_check,
                result.win_rate_check, result.trades_check, result.profit_factor_check
            ]
            
            if result.status != ValidationStatus.INSUFFICIENT_DATA:
                if all(basic_checks):
                    if result.ai_accuracy_check:
                        result.status = ValidationStatus.PASSED
                    else:
                        result.status = ValidationStatus.WARNING
                        result.warnings.append("AI 예측 정확도가 기준에 미달")
                elif sum(basic_checks) >= 4:  # 6개 중 4개 이상 통과
                    result.status = ValidationStatus.WARNING
                    result.warnings.append("일부 검증 기준 미달")
                else:
                    result.status = ValidationStatus.FAILED
            
            return result
            
        except Exception as e:
            self.logger.error(f"전략 검증 오류: {e}")
            return ValidationResult(
                strategy_name=strategy_name,
                status=ValidationStatus.FAILED,
                criteria=criteria or ValidationCriteria(),
                messages=[f"검증 중 오류 발생: {e}"]
            )
    
    async def compare_ai_vs_traditional(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        initial_capital: float = 1000000.0
    ) -> StrategyComparison:
        """
        AI vs 전통적 전략 비교
        
        Args:
            strategy_name: 전략 이름
            start_date: 시작일
            end_date: 종료일
            symbols: 대상 종목
            initial_capital: 초기 자본
        
        Returns:
            StrategyComparison: 비교 결과
        """
        try:
            self.logger.info(f"AI vs 전통적 전략 비교: {strategy_name}")
            
            # AI 사용 백테스팅
            with_ai_result = await self.backtesting_engine.run_backtest(
                strategy_name, start_date, end_date, symbols,
                initial_capital, use_ai=True
            )
            
            # AI 미사용 백테스팅
            without_ai_result = await self.backtesting_engine.run_backtest(
                strategy_name, start_date, end_date, symbols,
                initial_capital, use_ai=False
            )
            
            # 비교 결과 생성
            comparison = StrategyComparison(
                strategy_name=strategy_name,
                with_ai_result=with_ai_result,
                without_ai_result=without_ai_result
            )
            
            # 성능 개선 지표 계산
            ai_metrics = with_ai_result.metrics
            traditional_metrics = without_ai_result.metrics
            
            comparison.return_improvement = ai_metrics.annual_return - traditional_metrics.annual_return
            comparison.sharpe_improvement = ai_metrics.sharpe_ratio - traditional_metrics.sharpe_ratio
            comparison.drawdown_improvement = traditional_metrics.max_drawdown - ai_metrics.max_drawdown  # 낙폭 감소가 개선
            comparison.win_rate_improvement = ai_metrics.win_rate - traditional_metrics.win_rate
            
            # 통계적 유의성 검증
            comparison.statistical_significance, comparison.p_value = await self._test_statistical_significance(
                with_ai_result, without_ai_result
            )
            
            # AI 효과성 점수 계산 (0-100)
            comparison.ai_effectiveness_score = await self._calculate_ai_effectiveness(
                comparison
            )
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"AI vs 전통적 전략 비교 오류: {e}")
            raise
    
    async def _test_statistical_significance(
        self,
        with_ai_result: BacktestResult,
        without_ai_result: BacktestResult
    ) -> Tuple[bool, float]:
        """통계적 유의성 검증"""
        try:
            # 일일 수익률 계산
            ai_returns = self._calculate_daily_returns(with_ai_result.equity_curve)
            traditional_returns = self._calculate_daily_returns(without_ai_result.equity_curve)
            
            if len(ai_returns) < 30 or len(traditional_returns) < 30:
                return False, 1.0
            
            # t-검정 수행
            t_stat, p_value = stats.ttest_ind(ai_returns, traditional_returns)
            
            # 유의수준 5%에서 검증
            is_significant = p_value < 0.05 and np.mean(ai_returns) > np.mean(traditional_returns)
            
            return is_significant, p_value
            
        except Exception as e:
            self.logger.error(f"통계적 유의성 검증 오류: {e}")
            return False, 1.0
    
    def _calculate_daily_returns(self, equity_curve: List[Dict]) -> List[float]:
        """일일 수익률 계산"""
        try:
            returns = []
            
            for i in range(1, len(equity_curve)):
                prev_value = equity_curve[i-1]['portfolio_value']
                curr_value = equity_curve[i]['portfolio_value']
                
                if prev_value > 0:
                    daily_return = (curr_value - prev_value) / prev_value
                    returns.append(daily_return)
            
            return returns
            
        except Exception as e:
            self.logger.error(f"일일 수익률 계산 오류: {e}")
            return []
    
    async def _calculate_ai_effectiveness(self, comparison: StrategyComparison) -> float:
        """AI 효과성 점수 계산 (0-100)"""
        try:
            score = 0.0
            weight_sum = 0.0
            
            # 수익률 개선 (가중치: 30%)
            if comparison.return_improvement > 0:
                return_score = min(comparison.return_improvement / 10.0, 1.0) * 100
                score += return_score * 0.3
            weight_sum += 0.3
            
            # 샤프 비율 개선 (가중치: 25%)
            if comparison.sharpe_improvement > 0:
                sharpe_score = min(comparison.sharpe_improvement / 0.5, 1.0) * 100
                score += sharpe_score * 0.25
            weight_sum += 0.25
            
            # 낙폭 개선 (가중치: 20%)
            if comparison.drawdown_improvement > 0:
                drawdown_score = min(comparison.drawdown_improvement / 5.0, 1.0) * 100
                score += drawdown_score * 0.2
            weight_sum += 0.2
            
            # 승률 개선 (가중치: 15%)
            if comparison.win_rate_improvement > 0:
                winrate_score = min(comparison.win_rate_improvement / 10.0, 1.0) * 100
                score += winrate_score * 0.15
            weight_sum += 0.15
            
            # 통계적 유의성 (가중치: 10%)
            if comparison.statistical_significance:
                score += 100 * 0.1
            weight_sum += 0.1
            
            return score / weight_sum if weight_sum > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"AI 효과성 점수 계산 오류: {e}")
            return 0.0
    
    async def validate_multiple_strategies(
        self,
        strategies: List[str],
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        criteria: Optional[ValidationCriteria] = None
    ) -> Dict[str, ValidationResult]:
        """여러 전략 일괄 검증"""
        try:
            results = {}
            
            for strategy_name in strategies:
                self.logger.info(f"전략 검증: {strategy_name}")
                
                # 백테스팅 실행
                backtest_result = await self.backtesting_engine.run_backtest(
                    strategy_name, start_date, end_date, symbols
                )
                
                # 검증 수행
                validation_result = await self.validate_strategy(
                    strategy_name, backtest_result, criteria
                )
                
                results[strategy_name] = validation_result
            
            return results
            
        except Exception as e:
            self.logger.error(f"다중 전략 검증 오류: {e}")
            raise
    
    async def generate_validation_report(
        self,
        validation_results: Dict[str, ValidationResult],
        comparison_results: Optional[Dict[str, StrategyComparison]] = None
    ) -> str:
        """검증 보고서 생성"""
        try:
            report = []
            report.append("=" * 80)
            report.append("🔍 전략 검증 보고서")
            report.append("=" * 80)
            report.append(f"📅 보고서 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # 검증 결과 요약
            passed_count = sum(1 for r in validation_results.values() if r.status == ValidationStatus.PASSED)
            warning_count = sum(1 for r in validation_results.values() if r.status == ValidationStatus.WARNING)
            failed_count = sum(1 for r in validation_results.values() if r.status == ValidationStatus.FAILED)
            
            report.append("📊 검증 결과 요약")
            report.append("-" * 40)
            report.append(f"✅ 통과: {passed_count}개")
            report.append(f"⚠️ 경고: {warning_count}개")
            report.append(f"❌ 실패: {failed_count}개")
            report.append(f"📈 총 전략: {len(validation_results)}개")
            report.append("")
            
            # 개별 전략 결과
            for strategy_name, result in validation_results.items():
                report.append(f"🎯 전략: {strategy_name}")
                report.append(f"📊 상태: {result.status.value}")
                report.append(f"🔢 전체 점수: {result.overall_score:.1f}점")
                report.append("")
                
                for msg in result.messages:
                    report.append(f"   {msg}")
                
                if result.warnings:
                    report.append("   ⚠️ 경고:")
                    for warning in result.warnings:
                        report.append(f"     - {warning}")
                
                report.append("")
            
            # AI vs 전통적 전략 비교 (있는 경우)
            if comparison_results:
                report.append("🤖 AI vs 전통적 전략 비교")
                report.append("-" * 40)
                
                for strategy_name, comparison in comparison_results.items():
                    report.append(f"📈 전략: {strategy_name}")
                    report.append(f"🎯 AI 효과성 점수: {comparison.ai_effectiveness_score:.1f}점")
                    report.append(f"📊 수익률 개선: {comparison.return_improvement:+.2f}%")
                    report.append(f"📈 샤프 비율 개선: {comparison.sharpe_improvement:+.2f}")
                    report.append(f"📉 낙폭 개선: {comparison.drawdown_improvement:+.2f}%")
                    report.append(f"🎯 승률 개선: {comparison.win_rate_improvement:+.2f}%")
                    
                    if comparison.statistical_significance:
                        report.append(f"✅ 통계적 유의성: 유의함 (p-value: {comparison.p_value:.4f})")
                    else:
                        report.append(f"❌ 통계적 유의성: 유의하지 않음 (p-value: {comparison.p_value:.4f})")
                    
                    report.append("")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"검증 보고서 생성 오류: {e}")
            return f"보고서 생성 중 오류 발생: {e}"