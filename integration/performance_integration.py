#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/integration/performance_integration.py

성능 최적화 통합 시스템 - 즉시 실행 권장

병렬 처리, 성능 모니터링, API 타임아웃 최적화를 통합하여 높은 ROI 제공
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from utils.logger import get_logger
from async_processing.async_engine import AsyncEngine, TaskPriority
from monitoring.performance_monitor import PerformanceMonitor
from api_optimization.timeout_optimizer import TimeoutOptimizer, TimeoutStrategy


class PerformanceIntegrationSystem:
    """성능 최적화 통합 시스템"""

    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("PerformanceIntegration")

        # 핵심 구성 요소 초기화
        self.async_engine = AsyncEngine(config)
        self.performance_monitor = PerformanceMonitor(config)
        self.timeout_optimizer = None  # 비동기 초기화 필요

        # 통합 상태
        self.is_running = False
        self.optimization_enabled = True
        self.auto_scaling_enabled = True

        # 성능 메트릭
        self.integration_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'avg_response_time': 0.0,
            'system_efficiency': 0.0
        }

        self.logger.info("✅ 성능 최적화 통합 시스템 초기화 완료")

    async def start(self):
        """통합 시스템 시작"""
        if self.is_running:
            self.logger.warning("통합 시스템이 이미 실행 중입니다")
            return

        try:
            # 1. 비동기 엔진 시작
            await self.async_engine.start()

            # 2. 성능 모니터 시작
            self.performance_monitor.start_monitoring()

            # 3. 타임아웃 최적화기 시작
            self.timeout_optimizer = TimeoutOptimizer(self.config)
            await self.timeout_optimizer.start()

            # 4. KIS API 최적화 설정
            await self._setup_kis_api_optimization()

            # 5. 통합 모니터링 시작
            asyncio.create_task(self._integration_monitoring_loop())

            self.is_running = True
            self.logger.info("🚀 성능 최적화 통합 시스템 시작 완료")

        except Exception as e:
            self.logger.error(f"❌ 통합 시스템 시작 실패: {e}")
            await self.stop()
            raise

    async def stop(self):
        """통합 시스템 중지"""
        if not self.is_running:
            return

        try:
            self.is_running = False

            # 각 구성 요소 순차적으로 중지
            if self.timeout_optimizer:
                await self.timeout_optimizer.stop()

            self.performance_monitor.stop_monitoring()
            await self.async_engine.stop()

            self.logger.info("⏹️ 성능 최적화 통합 시스템 중지 완료")

        except Exception as e:
            self.logger.error(f"통합 시스템 중지 중 오류: {e}")

    async def _setup_kis_api_optimization(self):
        """KIS API 최적화 설정"""
        try:
            # 주요 KIS API 엔드포인트 등록
            kis_endpoints = [
                {
                    'name': 'oauth_token',
                    'url': 'https://openapi.koreainvestment.com:9443/oauth2/tokenP',
                    'strategy': TimeoutStrategy.AGGRESSIVE
                },
                {
                    'name': 'current_price',
                    'url': 'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price',
                    'strategy': TimeoutStrategy.BALANCED
                },
                {
                    'name': 'order_cash',
                    'url': 'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/order-cash',
                    'strategy': TimeoutStrategy.CONSERVATIVE
                },
                {
                    'name': 'balance',
                    'url': 'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance',
                    'strategy': TimeoutStrategy.BALANCED
                },
                {
                    'name': 'daily_chart',
                    'url': 'https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice',
                    'strategy': TimeoutStrategy.BALANCED
                }
            ]

            for endpoint_config in kis_endpoints:
                self.timeout_optimizer.register_endpoint(**endpoint_config)

            self.logger.info(f"KIS API 최적화 설정 완료: {len(kis_endpoints)}개 엔드포인트")

        except Exception as e:
            self.logger.error(f"KIS API 최적화 설정 실패: {e}")

    async def execute_optimized_operation(self,
                                        operation_func: Callable,
                                        *args,
                                        operation_name: str = None,
                                        priority: TaskPriority = TaskPriority.NORMAL,
                                        timeout: Optional[float] = None,
                                        **kwargs) -> Any:
        """최적화된 작업 실행"""
        op_name = operation_name or operation_func.__name__

        # 성능 모니터링 시작
        monitoring_id = self.performance_monitor.start_operation(op_name)

        try:
            # 비동기 엔진에 작업 제출
            task_id = await self.async_engine.submit_task(
                operation_func,
                *args,
                name=op_name,
                priority=priority,
                timeout=timeout,
                **kwargs
            )

            # 결과 대기
            result = await self.async_engine.get_task_result(task_id)

            # 성공 기록
            self.performance_monitor.end_operation(monitoring_id, success=True)
            self.integration_stats['successful_operations'] += 1

            return result

        except Exception as e:
            # 실패 기록
            self.performance_monitor.end_operation(monitoring_id, success=False)
            self.integration_stats['failed_operations'] += 1

            self.logger.error(f"최적화된 작업 실행 실패 {op_name}: {e}")
            raise

        finally:
            self.integration_stats['total_operations'] += 1

    async def execute_batch_operations(self,
                                     operations: List[Dict[str, Any]],
                                     batch_name: str = "batch_operation") -> List[Any]:
        """배치 작업 최적화 실행"""
        try:
            # 배치 작업을 비동기 엔진에 제출
            from async_processing.async_engine import AsyncTask

            tasks = []
            for i, op_config in enumerate(operations):
                task = AsyncTask(
                    task_id=f"{batch_name}_{i}",
                    name=op_config.get('name', f'batch_item_{i}'),
                    coro_func=op_config['function'],
                    args=op_config.get('args', ()),
                    kwargs=op_config.get('kwargs', {}),
                    priority=op_config.get('priority', TaskPriority.NORMAL),
                    timeout_seconds=op_config.get('timeout', 30.0)
                )
                tasks.append(task)

            # 배치 작업 제출
            task_ids = await self.async_engine.submit_batch_tasks(tasks)

            # 모든 결과 수집
            results = []
            for task_id in task_ids:
                try:
                    result = await self.async_engine.get_task_result(task_id)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"배치 작업 항목 실패 {task_id}: {e}")
                    results.append(None)

            self.logger.info(f"배치 작업 완료: {len(results)}/{len(operations)} 성공")
            return results

        except Exception as e:
            self.logger.error(f"배치 작업 실행 실패: {e}")
            raise

    async def make_optimized_api_call(self,
                                    endpoint_name: str,
                                    method: str = 'GET',
                                    data: Optional[Dict] = None,
                                    headers: Optional[Dict] = None,
                                    **kwargs) -> Any:
        """최적화된 API 호출"""
        try:
            result = await self.timeout_optimizer.make_request(
                endpoint_name=endpoint_name,
                method=method,
                data=data,
                headers=headers,
                **kwargs
            )

            if not result.success:
                self.logger.warning(f"API 호출 실패 {endpoint_name}: {result.error_message}")

            return result

        except Exception as e:
            self.logger.error(f"최적화된 API 호출 실패 {endpoint_name}: {e}")
            raise

    async def _integration_monitoring_loop(self):
        """통합 모니터링 루프"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 1분마다 모니터링

                if not self.is_running:
                    break

                # 통합 성능 분석
                await self._analyze_integrated_performance()

                # 자동 최적화 실행
                if self.optimization_enabled:
                    await self._auto_optimize()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"통합 모니터링 루프 에러: {e}")

    async def _analyze_integrated_performance(self):
        """통합 성능 분석"""
        try:
            # 1. 비동기 엔진 성능
            engine_stats = self.async_engine.get_engine_stats()

            # 2. 성능 모니터 데이터
            monitor_stats = self.performance_monitor.get_performance_summary()

            # 3. API 최적화 데이터
            api_stats = self.timeout_optimizer.get_system_stats()

            # 통합 효율성 계산
            efficiency = self._calculate_system_efficiency(
                engine_stats, monitor_stats, api_stats
            )

            self.integration_stats['system_efficiency'] = efficiency

            # 성능 트렌드 분석
            performance_trends = self.performance_monitor.analyze_performance_trends()

            # 이상 상황 감지
            anomalies = self.performance_monitor.detect_anomalies()

            # 예측 알림 생성
            predictive_alerts = self.performance_monitor.generate_predictive_alerts()

            # 종합 상태 로깅
            self.logger.info(
                f"📊 통합 성능 분석 - "
                f"효율성: {efficiency:.1%}, "
                f"활성 워커: {engine_stats.get('active_workers', 0)}, "
                f"API 건강: {api_stats.get('healthy_endpoints', 0)}/{api_stats.get('total_endpoints', 0)}"
            )

            # 알림 처리
            if anomalies:
                self.logger.warning(f"⚠️ 성능 이상 감지: {len(anomalies)}건")

            if predictive_alerts:
                self.logger.warning(f"🔮 예측 알림: {len(predictive_alerts)}건")

        except Exception as e:
            self.logger.error(f"통합 성능 분석 실패: {e}")

    def _calculate_system_efficiency(self,
                                   engine_stats: Dict,
                                   monitor_stats: Dict,
                                   api_stats: Dict) -> float:
        """시스템 효율성 계산"""
        try:
            # 각 구성 요소의 효율성 점수 (0-1)
            scores = []

            # 1. 비동기 엔진 효율성
            if engine_stats.get('performance_stats'):
                total_tasks = engine_stats['performance_stats'].get('total_tasks', 0)
                if total_tasks > 0:
                    engine_efficiency = 1.0 - (engine_stats.get('error_stats', {}).get('task_failures', 0) / total_tasks)
                    scores.append(engine_efficiency * 0.4)  # 40% 가중치

            # 2. 시스템 성능 효율성
            if monitor_stats.get('current_metrics'):
                cpu_efficiency = 1.0 - (monitor_stats['avg_cpu_percent'] / 100)
                memory_efficiency = 1.0 - (monitor_stats['avg_memory_percent'] / 100)
                response_efficiency = max(0, 1.0 - (monitor_stats['avg_response_time_ms'] / 5000))

                system_efficiency = (cpu_efficiency + memory_efficiency + response_efficiency) / 3
                scores.append(system_efficiency * 0.3)  # 30% 가중치

            # 3. API 최적화 효율성
            api_efficiency = api_stats.get('overall_success_rate', 0)
            scores.append(api_efficiency * 0.3)  # 30% 가중치

            return sum(scores) if scores else 0.0

        except Exception:
            return 0.0

    async def _auto_optimize(self):
        """자동 최적화 실행"""
        try:
            # 1. 비동기 엔진 최적화
            await self.async_engine.optimize_performance()

            # 2. 성능 모니터 최적화
            current_metrics = self.performance_monitor.get_current_metrics()
            if current_metrics and current_metrics.memory_percent > 85:
                self.performance_monitor.force_garbage_collection()

            # 3. API 타임아웃 최적화
            self.timeout_optimizer.force_optimization()

            # 4. 자동 스케일링 (필요시)
            if self.auto_scaling_enabled:
                await self._auto_scale_resources()

        except Exception as e:
            self.logger.error(f"자동 최적화 실패: {e}")

    async def _auto_scale_resources(self):
        """자동 리소스 스케일링"""
        try:
            # 현재 시스템 부하 확인
            current_metrics = self.performance_monitor.get_current_metrics()
            if not current_metrics:
                return

            engine_stats = self.async_engine.get_engine_stats()

            # CPU 사용률이 높고 대기 중인 작업이 많으면 워커 추가 고려
            if (current_metrics.cpu_percent < 70 and
                engine_stats.get('queue_size', 0) > 10 and
                engine_stats.get('max_workers', 0) < 32):

                # 비동기 엔진이 자동으로 워커를 추가할 것임
                self.logger.info("🔄 자동 스케일링: 리소스 확장 신호 감지")

            # 메모리 사용률이 높으면 정리 작업
            elif current_metrics.memory_percent > 80:
                self.performance_monitor.force_garbage_collection()
                self.logger.info("🧹 자동 스케일링: 메모리 정리 실행")

        except Exception as e:
            self.logger.error(f"자동 스케일링 실패: {e}")

    def get_integrated_status(self) -> Dict[str, Any]:
        """통합 상태 정보"""
        try:
            engine_stats = self.async_engine.get_engine_stats()
            monitor_summary = self.performance_monitor.get_performance_summary()
            api_stats = self.timeout_optimizer.get_system_stats() if self.timeout_optimizer else {}

            return {
                'system_status': 'running' if self.is_running else 'stopped',
                'integration_stats': self.integration_stats.copy(),
                'engine_stats': {
                    'active_workers': engine_stats.get('active_workers', 0),
                    'queue_size': engine_stats.get('queue_size', 0),
                    'completed_tasks': engine_stats.get('completed_tasks', 0)
                },
                'performance_stats': {
                    'cpu_percent': monitor_summary.get('avg_cpu_percent', 0),
                    'memory_percent': monitor_summary.get('avg_memory_percent', 0),
                    'response_time_ms': monitor_summary.get('avg_response_time_ms', 0),
                    'active_alerts': monitor_summary.get('active_alerts_count', 0)
                },
                'api_stats': {
                    'total_endpoints': api_stats.get('total_endpoints', 0),
                    'healthy_endpoints': api_stats.get('healthy_endpoints', 0),
                    'success_rate': api_stats.get('overall_success_rate', 0),
                    'circuit_breakers_open': api_stats.get('circuit_breakers_open', 0)
                },
                'optimization_enabled': self.optimization_enabled,
                'auto_scaling_enabled': self.auto_scaling_enabled,
                'timestamp': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"통합 상태 조회 실패: {e}")
            return {'error': str(e)}

    async def health_check(self) -> Dict[str, bool]:
        """전체 시스템 헬스 체크"""
        results = {
            'integration_system': self.is_running,
            'async_engine': self.async_engine.is_running,
            'performance_monitor': self.performance_monitor.is_monitoring,
            'timeout_optimizer': False
        }

        try:
            if self.timeout_optimizer:
                results['timeout_optimizer'] = self.timeout_optimizer.is_running

                # API 엔드포인트 헬스 체크
                api_health = await self.timeout_optimizer.health_check_all()
                results.update({f'api_{name}': status for name, status in api_health.items()})

        except Exception as e:
            self.logger.error(f"헬스 체크 실패: {e}")

        return results


# 전역 인스턴스 (선택적으로 사용)
_global_performance_system = None


async def get_global_performance_system(config=None) -> PerformanceIntegrationSystem:
    """전역 성능 시스템 인스턴스 가져오기"""
    global _global_performance_system

    if _global_performance_system is None:
        _global_performance_system = PerformanceIntegrationSystem(config)
        await _global_performance_system.start()

    return _global_performance_system


async def shutdown_global_performance_system():
    """전역 성능 시스템 종료"""
    global _global_performance_system

    if _global_performance_system:
        await _global_performance_system.stop()
        _global_performance_system = None