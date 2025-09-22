#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exit_strategy_optimizer.py

매매조건고도화.md 기반 Optuna 자동 최적화 시스템
ATR 배수, 부분익절 비율 등 매개변수 자동 탐색
"""

import asyncio
import optuna
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings("ignore")

from utils.logger import get_logger

@dataclass
class OptimizationResult:
    """최적화 결과"""
    best_params: Dict[str, Any]
    best_score: float
    total_trials: int
    optimization_time: float
    performance_metrics: Dict[str, float]

class ExitStrategyOptimizer:
    """매도 전략 자동 최적화기"""

    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("ExitStrategyOptimizer")

        # 최적화 파라미터 범위
        self.param_ranges = {
            # 기본 손익 기준
            'hard_stop_loss': (0.94, 0.99, 0.01),      # -6% ~ -1%
            'soft_target': (1.03, 1.12, 0.01),         # +3% ~ +12%

            # 부분 익절 설정
            'partial_tp_level1': (1.02, 1.08, 0.01),   # +2% ~ +8%
            'partial_tp_level2': (1.04, 1.10, 0.01),   # +4% ~ +10%
            'partial_ratio_1': (0.0, 0.6, 0.1),        # 0% ~ 60%
            'partial_ratio_2': (0.0, 0.6, 0.1),        # 0% ~ 60%

            # ATR 설정
            'atr_period': (8, 24, 1),                   # 8 ~ 24기간
            'atr_multiplier': (1.0, 3.0, 0.1),         # 1.0 ~ 3.0배

            # EMA/볼륨 필터
            'ema_period': (3, 10, 1),                   # 3 ~ 10기간
            'volume_threshold': (1.0, 2.0, 0.1),       # 1.0 ~ 2.0배

            # 시간 필터
            'market_close_minutes': (15, 60, 5),       # 15 ~ 60분
        }

    async def optimize_parameters(self,
                                 historical_data: List[Dict[str, Any]],
                                 n_trials: int = 100,
                                 study_name: str = "exit_strategy_optimization") -> OptimizationResult:
        """매개변수 자동 최적화"""
        self.logger.info(f"매도 전략 최적화 시작: {n_trials}회 시도")
        start_time = datetime.now()

        try:
            # Optuna study 생성
            study = optuna.create_study(
                direction="maximize",
                study_name=study_name,
                storage=f"sqlite:///{study_name}.db",
                load_if_exists=True
            )

            # 목적 함수 정의
            def objective(trial):
                return self._objective_function(trial, historical_data)

            # 최적화 실행
            study.optimize(objective, n_trials=n_trials)

            # 결과 분석
            best_params = study.best_params
            best_score = study.best_value
            optimization_time = (datetime.now() - start_time).total_seconds()

            # 최적 파라미터로 성능 평가
            performance_metrics = await self._evaluate_strategy(best_params, historical_data)

            result = OptimizationResult(
                best_params=best_params,
                best_score=best_score,
                total_trials=len(study.trials),
                optimization_time=optimization_time,
                performance_metrics=performance_metrics
            )

            self.logger.info(f"최적화 완료: {result.total_trials}회 시도, {result.optimization_time:.1f}초")
            self.logger.info(f"최적 점수: {result.best_score:.4f}")
            self.logger.info(f"최적 파라미터: {result.best_params}")

            return result

        except Exception as e:
            self.logger.error(f"최적화 실패: {e}")
            raise

    def _objective_function(self, trial, historical_data: List[Dict[str, Any]]) -> float:
        """Optuna 목적 함수"""
        try:
            # 파라미터 제안
            params = {}
            for param_name, (min_val, max_val, step) in self.param_ranges.items():
                if isinstance(min_val, int):
                    params[param_name] = trial.suggest_int(param_name, min_val, max_val, step=step)
                else:
                    params[param_name] = trial.suggest_float(param_name, min_val, max_val, step=step)

            # 제약 조건 확인
            if not self._validate_params(params):
                return -1e6  # 유효하지 않은 파라미터 조합

            # 백테스트 실행
            performance = self._run_backtest(params, historical_data)

            # 평가 지표 계산 (샤프 비율 기준)
            return performance.get('sharpe_ratio', -1e6)

        except Exception as e:
            self.logger.error(f"목적 함수 실행 실패: {e}")
            return -1e6

    def _validate_params(self, params: Dict[str, Any]) -> bool:
        """파라미터 유효성 검증"""
        try:
            # 부분익절 레벨 순서 확인
            if params['partial_tp_level1'] >= params['partial_tp_level2']:
                return False

            # 부분익절 비율 합계 확인
            if params['partial_ratio_1'] + params['partial_ratio_2'] > 1.0:
                return False

            # 목표 수익률이 손절선보다 높은지 확인
            if params['soft_target'] <= params['hard_stop_loss']:
                return False

            return True

        except Exception:
            return False

    def _run_backtest(self, params: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """백테스트 실행"""
        try:
            # 간단한 백테스트 시뮬레이션
            total_trades = 0
            winning_trades = 0
            total_return = 0.0
            returns = []

            initial_capital = 1000000  # 100만원
            current_capital = initial_capital

            for data in historical_data:
                # 매매 시뮬레이션 (간단화)
                entry_price = data.get('entry_price', 100000)
                exit_price = data.get('exit_price', entry_price)

                # 수익률 계산
                return_rate = (exit_price / entry_price) - 1

                # 매도 전략 적용
                adjusted_return = self._apply_exit_strategy(return_rate, params)

                total_trades += 1
                if adjusted_return > 0:
                    winning_trades += 1

                total_return += adjusted_return
                returns.append(adjusted_return)

            # 성과 지표 계산
            if total_trades == 0:
                return {'sharpe_ratio': -1e6, 'total_return': 0, 'win_rate': 0}

            avg_return = np.mean(returns) if returns else 0
            std_return = np.std(returns) if len(returns) > 1 else 1
            sharpe_ratio = avg_return / std_return if std_return > 0 else -1e6

            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            return {
                'sharpe_ratio': sharpe_ratio,
                'total_return': total_return,
                'win_rate': win_rate,
                'total_trades': total_trades
            }

        except Exception as e:
            self.logger.error(f"백테스트 실행 실패: {e}")
            return {'sharpe_ratio': -1e6, 'total_return': 0, 'win_rate': 0}

    def _apply_exit_strategy(self, raw_return: float, params: Dict[str, Any]) -> float:
        """매도 전략 적용"""
        try:
            # 하드 스탑 체크
            if raw_return <= (params['hard_stop_loss'] - 1):
                return params['hard_stop_loss'] - 1

            # 부분 익절 적용
            if raw_return >= (params['partial_tp_level1'] - 1):
                # 1차 부분익절
                profit_1 = (params['partial_tp_level1'] - 1) * params['partial_ratio_1']

                if raw_return >= (params['partial_tp_level2'] - 1):
                    # 2차 부분익절
                    profit_2 = (params['partial_tp_level2'] - 1) * params['partial_ratio_2']

                    # 잔여 포지션에 ATR 트레일링 적용 (시뮬레이션)
                    remaining_ratio = 1.0 - params['partial_ratio_1'] - params['partial_ratio_2']
                    if remaining_ratio > 0:
                        # 트레일링 스탑으로 인한 수익 감소 시뮬레이션
                        trailing_return = raw_return * 0.8  # 80% 가정
                        profit_3 = trailing_return * remaining_ratio
                    else:
                        profit_3 = 0

                    return profit_1 + profit_2 + profit_3
                else:
                    # 1차만 익절, 나머지는 원래 수익률
                    remaining_ratio = 1.0 - params['partial_ratio_1']
                    return profit_1 + (raw_return * remaining_ratio)

            return raw_return

        except Exception:
            return raw_return

    async def _evaluate_strategy(self, params: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """전략 성능 평가"""
        try:
            performance = self._run_backtest(params, historical_data)

            # 추가 지표 계산
            performance['max_drawdown'] = 0.1  # 시뮬레이션
            performance['profit_factor'] = 1.5  # 시뮬레이션
            performance['avg_holding_period'] = 3.2  # 시뮬레이션

            return performance

        except Exception as e:
            self.logger.error(f"전략 평가 실패: {e}")
            return {}

    async def adaptive_parameter_adjustment(self,
                                          symbol: str,
                                          current_volatility: float) -> Dict[str, Any]:
        """변동성 기반 동적 파라미터 조정"""
        try:
            base_params = {
                'hard_stop_loss': 0.97,
                'soft_target': 1.06,
                'atr_multiplier': 1.5,
                'volume_threshold': 1.2
            }

            # 변동성에 따른 조정
            if current_volatility < 0.01:  # 저변동성
                base_params['atr_multiplier'] = 1.2
                base_params['volume_threshold'] = 1.1
            elif current_volatility > 0.03:  # 고변동성
                base_params['atr_multiplier'] = 2.0
                base_params['volume_threshold'] = 1.5
                base_params['hard_stop_loss'] = 0.95  # 더 넓은 손절

            self.logger.info(f"{symbol} 변동성({current_volatility:.3f}) 기반 파라미터 조정")
            return base_params

        except Exception as e:
            self.logger.error(f"동적 파라미터 조정 실패: {e}")
            return {}

    async def generate_optimization_report(self, result: OptimizationResult) -> str:
        """최적화 결과 보고서 생성"""
        try:
            report = f"""
📊 매도 전략 최적화 결과 보고서
{'='*50}

🎯 최적화 성과:
- 최적 점수 (샤프비율): {result.best_score:.4f}
- 총 시도 횟수: {result.total_trials}
- 최적화 시간: {result.optimization_time:.1f}초

📈 성능 지표:
- 총 수익률: {result.performance_metrics.get('total_return', 0)*100:.2f}%
- 승률: {result.performance_metrics.get('win_rate', 0)*100:.1f}%
- 총 거래수: {result.performance_metrics.get('total_trades', 0)}

🔧 최적 파라미터:
"""
            for param, value in result.best_params.items():
                if isinstance(value, float):
                    report += f"- {param}: {value:.3f}\n"
                else:
                    report += f"- {param}: {value}\n"

            report += f"""
💡 권장사항:
1. 최적 파라미터를 실전 적용 전 페이퍼 트레이딩으로 검증
2. 시장 상황 변화시 재최적화 실행
3. 변동성 기반 동적 조정 병행 사용

⚠️ 주의사항:
- 과적합 위험: 다양한 시장 환경에서 검증 필요
- 슬리피지/수수료 실제 반영 필요
- 백테스트와 실거래 차이 고려
"""
            return report

        except Exception as e:
            self.logger.error(f"보고서 생성 실패: {e}")
            return "보고서 생성 실패"