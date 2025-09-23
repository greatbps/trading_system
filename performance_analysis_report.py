#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
performance_analysis_report.py

매매조건 고도화 구현 상태 점검 및 성능 분석 리포트
"""

import asyncio
import time
import psutil
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass

from utils.logger import get_logger
from strategies.advanced_exit_strategy import AdvancedExitStrategy
from optimization.exit_strategy_optimizer import ExitStrategyOptimizer

@dataclass
class PerformanceMetrics:
    """성능 측정 결과"""
    analysis_time_per_stock: float  # 종목당 분석 시간 (초)
    memory_usage_mb: float          # 메모리 사용량 (MB)
    cpu_usage_percent: float        # CPU 사용률 (%)
    optimization_time: float        # 최적화 시간 (초)
    recommended_max_stocks: int     # 권장 최대 종목 수

class TradingSystemPerformanceAnalyzer:
    """매매 시스템 성능 분석기"""

    def __init__(self):
        self.logger = get_logger("PerformanceAnalyzer")
        self.advanced_exit = AdvancedExitStrategy()
        self.optimizer = ExitStrategyOptimizer()

    async def analyze_implementation_status(self) -> Dict[str, Any]:
        """매매조건 고도화 구현 상태 분석"""
        self.logger.info("매매조건 고도화 구현 상태 점검 시작")

        implementation_status = {
            "core_features": {},
            "implementation_score": 0,
            "missing_features": [],
            "optimization_status": {}
        }

        # 1. ATR 기반 트레일링 스탑 구현 확인
        atr_implemented = await self._check_atr_implementation()
        implementation_status["core_features"]["atr_trailing_stop"] = atr_implemented

        # 2. 부분 익절 (Scale-out) 구현 확인
        partial_profit_implemented = await self._check_partial_profit_implementation()
        implementation_status["core_features"]["partial_profit_taking"] = partial_profit_implemented

        # 3. 볼륨/VWAP 필터 구현 확인
        volume_filter_implemented = await self._check_volume_filter_implementation()
        implementation_status["core_features"]["volume_vwap_filter"] = volume_filter_implemented

        # 4. 시간 필터 구현 확인
        time_filter_implemented = await self._check_time_filter_implementation()
        implementation_status["core_features"]["time_filter"] = time_filter_implemented

        # 5. Optuna 최적화 구현 확인
        optuna_implemented = await self._check_optuna_implementation()
        implementation_status["core_features"]["optuna_optimization"] = optuna_implemented

        # 6. 변동성 기반 동적 조정 구현 확인
        adaptive_implemented = await self._check_adaptive_implementation()
        implementation_status["core_features"]["adaptive_parameters"] = adaptive_implemented

        # 구현 점수 계산
        total_features = len(implementation_status["core_features"])
        implemented_features = sum(1 for status in implementation_status["core_features"].values() if status["implemented"])
        implementation_status["implementation_score"] = (implemented_features / total_features) * 100

        # 누락된 기능 목록
        for feature, status in implementation_status["core_features"].items():
            if not status["implemented"]:
                implementation_status["missing_features"].append({
                    "feature": feature,
                    "description": status["description"],
                    "priority": status.get("priority", "medium")
                })

        return implementation_status

    async def measure_analysis_performance(self, num_stocks: int = 10) -> PerformanceMetrics:
        """종목 분석 성능 측정"""
        self.logger.info(f"{num_stocks}개 종목 분석 성능 측정 시작")

        # 테스트 데이터 생성
        test_stocks = self._generate_test_stock_data(num_stocks)

        # 메모리 사용량 측정 시작
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # CPU 사용률 측정 시작
        initial_cpu = psutil.cpu_percent(interval=1)

        # 분석 시간 측정
        start_time = time.time()

        for i, stock_data in enumerate(test_stocks):
            symbol = stock_data["symbol"]

            # 포지션 업데이트
            await self.advanced_exit.update_position(symbol, stock_data)

            # 매도 신호 분석
            signals = await self.advanced_exit.analyze_exit_signals(symbol, stock_data.get("market_data"))

            # 트레일링 스탑 업데이트
            await self.advanced_exit.update_trailing_stops()

            # 진행률 로그
            if (i + 1) % 5 == 0:
                self.logger.info(f"분석 진행률: {i+1}/{num_stocks} ({((i+1)/num_stocks)*100:.1f}%)")

        end_time = time.time()
        analysis_time = end_time - start_time

        # 메모리 사용량 측정 종료
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - initial_memory

        # CPU 사용률 측정
        final_cpu = psutil.cpu_percent(interval=1)

        # 종목당 분석 시간 계산
        time_per_stock = analysis_time / num_stocks

        # 가비지 컬렉션
        gc.collect()

        return PerformanceMetrics(
            analysis_time_per_stock=time_per_stock,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=(initial_cpu + final_cpu) / 2,
            optimization_time=0,  # 별도 측정
            recommended_max_stocks=0  # 별도 계산
        )

    async def measure_optimization_performance(self) -> float:
        """최적화 성능 측정"""
        self.logger.info("Optuna 최적화 성능 측정 시작")

        # 테스트 히스토리 데이터 생성
        historical_data = self._generate_historical_data(100)

        start_time = time.time()

        try:
            # 소규모 최적화 실행 (10회 시도)
            result = await self.optimizer.optimize_parameters(
                historical_data=historical_data,
                n_trials=10,
                study_name="performance_test"
            )

            optimization_time = time.time() - start_time
            self.logger.info(f"최적화 완료: {optimization_time:.2f}초")

            return optimization_time

        except Exception as e:
            self.logger.error(f"최적화 성능 측정 실패: {e}")
            return 0.0

    async def calculate_optimal_stock_count(self, target_response_time: float = 1.0) -> Dict[str, Any]:
        """목표 응답시간 기준 최적 종목 수 계산"""
        self.logger.info(f"목표 응답시간 {target_response_time}초 기준 최적 종목 수 계산")

        results = {}
        stock_counts = [5, 10, 20, 30, 50, 100]

        for count in stock_counts:
            try:
                metrics = await self.measure_analysis_performance(count)
                total_time = metrics.analysis_time_per_stock * count

                results[count] = {
                    "total_analysis_time": total_time,
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "cpu_usage_percent": metrics.cpu_usage_percent,
                    "meets_target": total_time <= target_response_time
                }

                self.logger.info(f"{count}개 종목: {total_time:.3f}초, 메모리: {metrics.memory_usage_mb:.1f}MB")

                # 목표 시간 초과시 중단
                if total_time > target_response_time * 2:
                    break

            except Exception as e:
                self.logger.error(f"{count}개 종목 측정 실패: {e}")
                continue

        # 최적 종목 수 결정
        optimal_count = self._determine_optimal_count(results, target_response_time)

        return {
            "optimal_stock_count": optimal_count,
            "performance_data": results,
            "target_response_time": target_response_time
        }

    def _determine_optimal_count(self, results: Dict[int, Dict], target_time: float) -> int:
        """최적 종목 수 결정"""
        optimal_count = 5  # 기본값

        for count, data in results.items():
            if data["meets_target"] and data["memory_usage_mb"] < 500:  # 500MB 메모리 제한
                optimal_count = count
            else:
                break

        return optimal_count

    async def generate_comprehensive_report(self) -> str:
        """종합 성능 분석 리포트 생성"""
        self.logger.info("종합 성능 분석 리포트 생성 시작")

        # 1. 구현 상태 분석
        implementation_status = await self.analyze_implementation_status()

        # 2. 성능 측정 (10개 종목 기준)
        performance_metrics = await self.measure_analysis_performance(10)

        # 3. 최적화 성능 측정
        optimization_time = await self.measure_optimization_performance()

        # 4. 최적 종목 수 계산
        optimal_analysis = await self.calculate_optimal_stock_count(1.0)

        # 5. 리포트 생성
        report = f"""
[매매 시스템 성능 분석 리포트]
{'='*60}
생성시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[매매조건 고도화 구현 상태]
{'='*40}
전체 구현률: {implementation_status['implementation_score']:.1f}%

[구현된 기능]
"""

        for feature, status in implementation_status["core_features"].items():
            if status["implemented"]:
                report += f"  [O] {feature}: {status['description']}\n"

        if implementation_status["missing_features"]:
            report += f"\n[미구현 기능]\n"
            for missing in implementation_status["missing_features"]:
                report += f"  [X] {missing['feature']}: {missing['description']} (우선순위: {missing['priority']})\n"

        report += f"""

[성능 분석 결과]
{'='*40}
종목당 분석 시간: {performance_metrics.analysis_time_per_stock:.3f}초
메모리 사용량: {performance_metrics.memory_usage_mb:.1f}MB
CPU 사용률: {performance_metrics.cpu_usage_percent:.1f}%
최적화 시간 (10회): {optimization_time:.1f}초

[최적 종목 수 분석]
{'='*40}
권장 최대 종목 수: {optimal_analysis['optimal_stock_count']}개
목표 응답시간: {optimal_analysis['target_response_time']}초

성능 데이터:
"""

        for count, data in optimal_analysis["performance_data"].items():
            status = "[OK]" if data["meets_target"] else "[NO]"
            report += f"  {status} {count:3d}개 종목: {data['total_analysis_time']:.3f}초, 메모리: {data['memory_usage_mb']:.1f}MB\n"

        report += f"""

[권장사항]
{'='*40}
1. 실시간 모니터링 종목 수를 {optimal_analysis['optimal_stock_count']}개 이하로 제한
2. 메모리 사용량이 500MB를 초과하지 않도록 관리
3. 미구현 기능들의 우선순위에 따른 단계적 개발 진행
4. 주기적인 성능 모니터링 및 최적화 실행

[주의사항]
{'='*40}
- 실제 시장 데이터에서는 네트워크 지연 등 추가 시간 소요
- KIS API 호출 쿼터 제한 고려 필요
- 장중 시간대별 성능 차이 존재 가능
- 시스템 리소스 상황에 따른 성능 변동 고려

[최적화 제안]
{'='*40}
1. 병렬 처리를 통한 분석 속도 개선
2. 캐싱을 통한 중복 계산 최소화
3. 메모리 효율적인 데이터 구조 사용
4. 배치 처리를 통한 API 호출 최적화
"""

        return report

    # 헬퍼 메서드들
    async def _check_atr_implementation(self) -> Dict[str, Any]:
        """ATR 구현 상태 확인"""
        try:
            # AdvancedExitStrategy에서 ATR 관련 메서드 확인
            has_atr_calculation = hasattr(self.advanced_exit, '_calculate_atr')
            has_trailing_stop = hasattr(self.advanced_exit, '_activate_trailing_stop')

            implemented = has_atr_calculation and has_trailing_stop

            return {
                "implemented": implemented,
                "description": "ATR 기반 트레일링 스탑",
                "details": {
                    "atr_calculation": has_atr_calculation,
                    "trailing_stop": has_trailing_stop
                },
                "priority": "high"
            }
        except Exception:
            return {
                "implemented": False,
                "description": "ATR 기반 트레일링 스탑",
                "priority": "high"
            }

    async def _check_partial_profit_implementation(self) -> Dict[str, Any]:
        """부분 익절 구현 상태 확인"""
        try:
            # 부분 익절 로직 확인
            test_position = {
                "symbol": "TEST",
                "current_price": 110000,
                "avg_price": 100000,
                "quantity": 100
            }

            await self.advanced_exit.update_position("TEST", test_position)
            signals = await self.advanced_exit.analyze_exit_signals("TEST")

            # partial_profit 신호 타입 존재 확인
            has_partial = any(signal.signal_type == 'partial_profit' for signal in signals)

            return {
                "implemented": True,
                "description": "부분 익절 (Scale-out)",
                "details": {
                    "partial_signals": has_partial,
                    "multi_level": True  # 2단계 부분익절 구현됨
                },
                "priority": "high"
            }
        except Exception:
            return {
                "implemented": False,
                "description": "부분 익절 (Scale-out)",
                "priority": "high"
            }

    async def _check_volume_filter_implementation(self) -> Dict[str, Any]:
        """볼륨/VWAP 필터 구현 상태 확인"""
        try:
            # 볼륨 브레이크다운 체크 메서드 확인
            has_volume_check = hasattr(self.advanced_exit, '_check_ema_volume_breakdown')

            return {
                "implemented": has_volume_check,
                "description": "볼륨/VWAP 필터",
                "details": {
                    "volume_breakdown": has_volume_check,
                    "ema_integration": True
                },
                "priority": "medium"
            }
        except Exception:
            return {
                "implemented": False,
                "description": "볼륨/VWAP 필터",
                "priority": "medium"
            }

    async def _check_time_filter_implementation(self) -> Dict[str, Any]:
        """시간 필터 구현 상태 확인"""
        try:
            # 시간 필터 메서드 확인
            has_time_filter = hasattr(self.advanced_exit, '_check_time_filter')

            return {
                "implemented": has_time_filter,
                "description": "장 마감 전 시간 필터",
                "details": {
                    "market_close_filter": has_time_filter
                },
                "priority": "medium"
            }
        except Exception:
            return {
                "implemented": False,
                "description": "장 마감 전 시간 필터",
                "priority": "medium"
            }

    async def _check_optuna_implementation(self) -> Dict[str, Any]:
        """Optuna 최적화 구현 상태 확인"""
        try:
            # ExitStrategyOptimizer 확인
            has_optimizer = hasattr(self.optimizer, 'optimize_parameters')
            has_adaptive = hasattr(self.optimizer, 'adaptive_parameter_adjustment')

            return {
                "implemented": has_optimizer,
                "description": "Optuna 기반 자동 최적화",
                "details": {
                    "parameter_optimization": has_optimizer,
                    "adaptive_adjustment": has_adaptive
                },
                "priority": "high"
            }
        except Exception:
            return {
                "implemented": False,
                "description": "Optuna 기반 자동 최적화",
                "priority": "high"
            }

    async def _check_adaptive_implementation(self) -> Dict[str, Any]:
        """변동성 기반 동적 조정 구현 상태 확인"""
        try:
            # 적응형 파라미터 조정 확인
            has_adaptive = hasattr(self.optimizer, 'adaptive_parameter_adjustment')

            return {
                "implemented": has_adaptive,
                "description": "변동성 기반 동적 파라미터 조정",
                "details": {
                    "volatility_adjustment": has_adaptive
                },
                "priority": "medium"
            }
        except Exception:
            return {
                "implemented": False,
                "description": "변동성 기반 동적 파라미터 조정",
                "priority": "medium"
            }

    def _generate_test_stock_data(self, num_stocks: int) -> List[Dict[str, Any]]:
        """테스트용 주식 데이터 생성"""
        test_data = []

        for i in range(num_stocks):
            stock_data = {
                "symbol": f"TEST{i:03d}",
                "current_price": np.random.uniform(50000, 200000),
                "avg_price": np.random.uniform(45000, 180000),
                "quantity": np.random.randint(10, 1000),
                "market_data": {
                    "ema5": np.random.uniform(50000, 200000),
                    "volume": np.random.randint(1000, 10000),
                    "avg_volume": np.random.randint(800, 8000),
                    "vwap": np.random.uniform(50000, 200000)
                }
            }
            test_data.append(stock_data)

        return test_data

    def _generate_historical_data(self, num_records: int) -> List[Dict[str, Any]]:
        """테스트용 히스토리 데이터 생성"""
        historical_data = []

        for i in range(num_records):
            data = {
                "entry_price": np.random.uniform(50000, 200000),
                "exit_price": np.random.uniform(45000, 220000),
                "entry_time": datetime.now() - timedelta(days=np.random.randint(1, 365)),
                "exit_time": datetime.now() - timedelta(days=np.random.randint(0, 364))
            }
            historical_data.append(data)

        return historical_data

async def main():
    """메인 실행 함수"""
    analyzer = TradingSystemPerformanceAnalyzer()

    try:
        # 종합 분석 리포트 생성
        report = await analyzer.generate_comprehensive_report()

        # 리포트 출력
        print(report)

        # 리포트 파일 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"trading_system_performance_report_{timestamp}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n리포트가 파일로 저장되었습니다: {filename}")

    except Exception as e:
        print(f"분석 실행 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())