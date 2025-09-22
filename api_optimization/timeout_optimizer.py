#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/api_optimization/timeout_optimizer.py

API 타임아웃 최적화 시스템 - 높은 ROI 즉시 실행 권장
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import json
from enum import Enum

from utils.logger import get_logger


class TimeoutStrategy(Enum):
    """타임아웃 전략"""
    AGGRESSIVE = "aggressive"      # 빠른 응답, 짧은 타임아웃
    BALANCED = "balanced"          # 균형잡힌 설정
    CONSERVATIVE = "conservative"  # 안정성 우선
    ADAPTIVE = "adaptive"          # 적응형


@dataclass
class APIEndpoint:
    """API 엔드포인트 정보"""
    url: str
    name: str
    timeout_seconds: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5

    # 성능 통계
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0

    # 응답 시간 통계
    response_times: List[float] = field(default_factory=list)
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0

    # 상태 관리
    is_healthy: bool = True
    circuit_breaker_open: bool = False
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None

    # 최적화 설정
    strategy: TimeoutStrategy = TimeoutStrategy.BALANCED
    auto_optimization: bool = True


@dataclass
class RequestResult:
    """요청 결과"""
    endpoint: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timeout_occurred: bool = False
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class CircuitBreaker:
    """서킷 브레이커 패턴"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부 확인"""
        if self.last_failure_time is None:
            return False

        return (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout

    def _on_success(self):
        """성공 시 처리"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class TimeoutOptimizer:
    """API 타임아웃 최적화 시스템"""

    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("TimeoutOptimizer")

        # 엔드포인트 관리
        self.endpoints = {}  # endpoint_name -> APIEndpoint
        self.circuit_breakers = {}  # endpoint_name -> CircuitBreaker

        # 요청 이력
        self.request_history = deque(maxlen=10000)
        self.performance_stats = defaultdict(list)

        # 최적화 설정
        self.optimization_interval = 300  # 5분마다 최적화
        self.analysis_window = 3600      # 1시간 분석 윈도우
        self.min_requests_for_optimization = 50  # 최적화를 위한 최소 요청 수

        # 전략별 기본 타임아웃
        self.strategy_timeouts = {
            TimeoutStrategy.AGGRESSIVE: {
                'connect_timeout': 5.0,
                'read_timeout': 10.0,
                'total_timeout': 15.0
            },
            TimeoutStrategy.BALANCED: {
                'connect_timeout': 10.0,
                'read_timeout': 20.0,
                'total_timeout': 30.0
            },
            TimeoutStrategy.CONSERVATIVE: {
                'connect_timeout': 15.0,
                'read_timeout': 45.0,
                'total_timeout': 60.0
            }
        }

        # 비동기 세션
        self.session = None
        self.optimization_task = None
        self.is_running = False

        self.logger.info("✅ API 타임아웃 최적화 시스템 초기화 완료")

    async def start(self):
        """최적화 시스템 시작"""
        if self.is_running:
            self.logger.warning("타임아웃 최적화가 이미 실행 중입니다")
            return

        self.is_running = True

        # aiohttp 세션 생성
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # 최적화 태스크 시작
        self.optimization_task = asyncio.create_task(
            self._optimization_loop(),
            name="TimeoutOptimizer"
        )

        self.logger.info("🚀 API 타임아웃 최적화 시스템 시작")

    async def stop(self):
        """최적화 시스템 중지"""
        if not self.is_running:
            return

        self.is_running = False

        # 최적화 태스크 중지
        if self.optimization_task and not self.optimization_task.done():
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass

        # 세션 정리
        if self.session and not self.session.closed:
            await self.session.close()

        self.logger.info("⏹️ API 타임아웃 최적화 시스템 중지")

    def register_endpoint(self,
                         name: str,
                         url: str,
                         strategy: TimeoutStrategy = TimeoutStrategy.BALANCED,
                         custom_timeout: Optional[float] = None) -> APIEndpoint:
        """엔드포인트 등록"""
        # 전략에 따른 기본 타임아웃 설정
        default_timeouts = self.strategy_timeouts[strategy]
        timeout = custom_timeout or default_timeouts['total_timeout']

        endpoint = APIEndpoint(
            url=url,
            name=name,
            timeout_seconds=timeout,
            strategy=strategy
        )

        self.endpoints[name] = endpoint
        self.circuit_breakers[name] = CircuitBreaker()

        self.logger.info(f"엔드포인트 등록: {name} ({strategy.value}, {timeout}s)")
        return endpoint

    async def make_request(self,
                          endpoint_name: str,
                          method: str = 'GET',
                          data: Optional[Dict] = None,
                          headers: Optional[Dict] = None,
                          **kwargs) -> RequestResult:
        """최적화된 API 요청"""
        if endpoint_name not in self.endpoints:
            raise ValueError(f"등록되지 않은 엔드포인트: {endpoint_name}")

        endpoint = self.endpoints[endpoint_name]
        circuit_breaker = self.circuit_breakers[endpoint_name]

        start_time = time.time()

        try:
            # 서킷 브레이커 체크
            if circuit_breaker.state == "OPEN":
                if not circuit_breaker._should_attempt_reset():
                    return RequestResult(
                        endpoint=endpoint_name,
                        success=False,
                        response_time=0,
                        error_message="Circuit breaker is OPEN"
                    )
                else:
                    circuit_breaker.state = "HALF_OPEN"

            # 타임아웃 설정
            timeout = aiohttp.ClientTimeout(total=endpoint.timeout_seconds)

            # 요청 실행
            async with self.session.request(
                method=method.upper(),
                url=endpoint.url,
                json=data,
                headers=headers,
                timeout=timeout,
                **kwargs
            ) as response:
                response_time = time.time() - start_time

                # 성공 처리
                if response.status < 400:
                    result = RequestResult(
                        endpoint=endpoint_name,
                        success=True,
                        response_time=response_time,
                        status_code=response.status
                    )

                    self._record_success(endpoint, response_time)
                    circuit_breaker._on_success()

                else:
                    result = RequestResult(
                        endpoint=endpoint_name,
                        success=False,
                        response_time=response_time,
                        status_code=response.status,
                        error_message=f"HTTP {response.status}"
                    )

                    self._record_failure(endpoint, response_time)
                    circuit_breaker._on_failure()

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            result = RequestResult(
                endpoint=endpoint_name,
                success=False,
                response_time=response_time,
                timeout_occurred=True,
                error_message="Request timeout"
            )

            self._record_timeout(endpoint, response_time)
            circuit_breaker._on_failure()

        except Exception as e:
            response_time = time.time() - start_time
            result = RequestResult(
                endpoint=endpoint_name,
                success=False,
                response_time=response_time,
                error_message=str(e)
            )

            self._record_failure(endpoint, response_time)
            circuit_breaker._on_failure()

        # 요청 이력 저장
        self.request_history.append(result)

        return result

    def _record_success(self, endpoint: APIEndpoint, response_time: float):
        """성공 기록"""
        endpoint.total_requests += 1
        endpoint.success_requests += 1
        endpoint.response_times.append(response_time)
        endpoint.last_success_time = datetime.now()
        endpoint.is_healthy = True

        # 응답 시간 리스트 크기 제한
        if len(endpoint.response_times) > 1000:
            endpoint.response_times = endpoint.response_times[-1000:]

        self._update_response_time_stats(endpoint)

    def _record_failure(self, endpoint: APIEndpoint, response_time: float):
        """실패 기록"""
        endpoint.total_requests += 1
        endpoint.failed_requests += 1
        endpoint.last_failure_time = datetime.now()

        # 건강 상태 업데이트
        success_rate = endpoint.success_requests / endpoint.total_requests
        endpoint.is_healthy = success_rate > 0.8

    def _record_timeout(self, endpoint: APIEndpoint, response_time: float):
        """타임아웃 기록"""
        endpoint.total_requests += 1
        endpoint.failed_requests += 1
        endpoint.timeout_requests += 1
        endpoint.last_failure_time = datetime.now()

        # 건강 상태 업데이트
        success_rate = endpoint.success_requests / endpoint.total_requests
        endpoint.is_healthy = success_rate > 0.8

    def _update_response_time_stats(self, endpoint: APIEndpoint):
        """응답 시간 통계 업데이트"""
        if not endpoint.response_times:
            return

        times = endpoint.response_times
        endpoint.avg_response_time = statistics.mean(times)

        if len(times) >= 20:  # 충분한 데이터가 있을 때만 백분위수 계산
            sorted_times = sorted(times)
            n = len(sorted_times)
            endpoint.p95_response_time = sorted_times[int(n * 0.95)]
            endpoint.p99_response_time = sorted_times[int(n * 0.99)]

    async def _optimization_loop(self):
        """최적화 루프"""
        while self.is_running:
            try:
                await asyncio.sleep(self.optimization_interval)

                if not self.is_running:
                    break

                await self._optimize_timeouts()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"최적화 루프 에러: {e}")

    async def _optimize_timeouts(self):
        """타임아웃 최적화 실행"""
        try:
            optimized_count = 0

            for endpoint_name, endpoint in self.endpoints.items():
                if not endpoint.auto_optimization:
                    continue

                if endpoint.total_requests < self.min_requests_for_optimization:
                    continue

                # 최적화 수행
                if await self._optimize_endpoint_timeout(endpoint):
                    optimized_count += 1

            if optimized_count > 0:
                self.logger.info(f"타임아웃 최적화 완료: {optimized_count}개 엔드포인트")

        except Exception as e:
            self.logger.error(f"타임아웃 최적화 실패: {e}")

    async def _optimize_endpoint_timeout(self, endpoint: APIEndpoint) -> bool:
        """개별 엔드포인트 타임아웃 최적화"""
        try:
            if not endpoint.response_times:
                return False

            # 현재 성능 분석
            success_rate = endpoint.success_requests / endpoint.total_requests
            timeout_rate = endpoint.timeout_requests / endpoint.total_requests

            # 적응형 전략인 경우에만 자동 조정
            if endpoint.strategy != TimeoutStrategy.ADAPTIVE:
                return False

            # 새로운 타임아웃 계산
            new_timeout = self._calculate_optimal_timeout(endpoint)

            # 타임아웃 변경이 필요한지 확인
            current_timeout = endpoint.timeout_seconds
            threshold = 0.1  # 10% 이상 차이날 때만 변경

            if abs(new_timeout - current_timeout) / current_timeout > threshold:
                endpoint.timeout_seconds = new_timeout

                self.logger.info(
                    f"타임아웃 최적화: {endpoint.name} "
                    f"{current_timeout:.1f}s -> {new_timeout:.1f}s "
                    f"(성공률: {success_rate:.1%})"
                )

                return True

            return False

        except Exception as e:
            self.logger.error(f"엔드포인트 최적화 실패 {endpoint.name}: {e}")
            return False

    def _calculate_optimal_timeout(self, endpoint: APIEndpoint) -> float:
        """최적 타임아웃 계산"""
        try:
            # P99 응답 시간에 여유분 추가
            base_timeout = endpoint.p99_response_time * 1.5

            # 최소/최대 제한
            min_timeout = 5.0
            max_timeout = 120.0

            # 성공률에 따른 조정
            success_rate = endpoint.success_requests / endpoint.total_requests
            if success_rate < 0.9:
                base_timeout *= 1.2  # 성공률이 낮으면 여유있게
            elif success_rate > 0.95:
                base_timeout *= 0.9  # 성공률이 높으면 적극적으로

            # 타임아웃 비율에 따른 조정
            timeout_rate = endpoint.timeout_requests / endpoint.total_requests
            if timeout_rate > 0.05:  # 5% 이상 타임아웃
                base_timeout *= 1.3

            return max(min_timeout, min(max_timeout, base_timeout))

        except Exception:
            return 30.0  # 기본값

    def get_endpoint_stats(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """엔드포인트 통계 조회"""
        if endpoint_name not in self.endpoints:
            return None

        endpoint = self.endpoints[endpoint_name]
        circuit_breaker = self.circuit_breakers[endpoint_name]

        success_rate = 0
        timeout_rate = 0

        if endpoint.total_requests > 0:
            success_rate = endpoint.success_requests / endpoint.total_requests
            timeout_rate = endpoint.timeout_requests / endpoint.total_requests

        return {
            'name': endpoint.name,
            'url': endpoint.url,
            'strategy': endpoint.strategy.value,
            'timeout_seconds': endpoint.timeout_seconds,
            'total_requests': endpoint.total_requests,
            'success_rate': success_rate,
            'timeout_rate': timeout_rate,
            'avg_response_time': endpoint.avg_response_time,
            'p95_response_time': endpoint.p95_response_time,
            'p99_response_time': endpoint.p99_response_time,
            'is_healthy': endpoint.is_healthy,
            'circuit_breaker_state': circuit_breaker.state,
            'last_success_time': endpoint.last_success_time,
            'last_failure_time': endpoint.last_failure_time
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 전체 통계"""
        total_requests = sum(ep.total_requests for ep in self.endpoints.values())
        total_successes = sum(ep.success_requests for ep in self.endpoints.values())
        total_timeouts = sum(ep.timeout_requests for ep in self.endpoints.values())

        healthy_endpoints = sum(1 for ep in self.endpoints.values() if ep.is_healthy)
        total_endpoints = len(self.endpoints)

        # 최근 1시간 요청 분석
        recent_requests = [
            req for req in self.request_history
            if (datetime.now() - req.timestamp).total_seconds() < 3600
        ]

        recent_success_rate = 0
        if recent_requests:
            recent_successes = sum(1 for req in recent_requests if req.success)
            recent_success_rate = recent_successes / len(recent_requests)

        return {
            'total_endpoints': total_endpoints,
            'healthy_endpoints': healthy_endpoints,
            'total_requests': total_requests,
            'overall_success_rate': total_successes / max(1, total_requests),
            'overall_timeout_rate': total_timeouts / max(1, total_requests),
            'recent_requests_1h': len(recent_requests),
            'recent_success_rate_1h': recent_success_rate,
            'optimization_running': self.is_running,
            'circuit_breakers_open': sum(
                1 for cb in self.circuit_breakers.values()
                if cb.state == "OPEN"
            )
        }

    async def health_check_all(self) -> Dict[str, bool]:
        """모든 엔드포인트 헬스 체크"""
        results = {}

        for endpoint_name, endpoint in self.endpoints.items():
            try:
                result = await self.make_request(
                    endpoint_name=endpoint_name,
                    method='GET'
                )
                results[endpoint_name] = result.success

            except Exception as e:
                self.logger.error(f"헬스 체크 실패 {endpoint_name}: {e}")
                results[endpoint_name] = False

        return results

    def force_optimization(self, endpoint_name: Optional[str] = None):
        """강제 최적화 실행"""
        if endpoint_name:
            if endpoint_name in self.endpoints:
                asyncio.create_task(
                    self._optimize_endpoint_timeout(self.endpoints[endpoint_name])
                )
        else:
            asyncio.create_task(self._optimize_timeouts())

        self.logger.info(f"강제 최적화 실행: {endpoint_name or '전체'}")

    def reset_endpoint_stats(self, endpoint_name: str):
        """엔드포인트 통계 초기화"""
        if endpoint_name not in self.endpoints:
            return

        endpoint = self.endpoints[endpoint_name]
        endpoint.total_requests = 0
        endpoint.success_requests = 0
        endpoint.failed_requests = 0
        endpoint.timeout_requests = 0
        endpoint.response_times.clear()
        endpoint.avg_response_time = 0.0
        endpoint.p95_response_time = 0.0
        endpoint.p99_response_time = 0.0

        # 서킷 브레이커 리셋
        circuit_breaker = self.circuit_breakers[endpoint_name]
        circuit_breaker.failure_count = 0
        circuit_breaker.state = "CLOSED"

        self.logger.info(f"엔드포인트 통계 초기화: {endpoint_name}")


# 편의 함수들
async def create_optimized_session(config=None) -> TimeoutOptimizer:
    """최적화된 세션 생성"""
    optimizer = TimeoutOptimizer(config)
    await optimizer.start()
    return optimizer


def optimize_kis_api_timeouts(optimizer: TimeoutOptimizer):
    """KIS API 전용 타임아웃 최적화 설정"""
    # 주요 KIS API 엔드포인트 등록
    endpoints = [
        ("oauth_token", "/oauth2/tokenP", TimeoutStrategy.AGGRESSIVE),
        ("current_price", "/uapi/domestic-stock/v1/quotations/inquire-price", TimeoutStrategy.BALANCED),
        ("order_buy", "/uapi/domestic-stock/v1/trading/order-cash", TimeoutStrategy.CONSERVATIVE),
        ("order_sell", "/uapi/domestic-stock/v1/trading/order-cash", TimeoutStrategy.CONSERVATIVE),
        ("balance", "/uapi/domestic-stock/v1/trading/inquire-balance", TimeoutStrategy.BALANCED),
        ("daily_chart", "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", TimeoutStrategy.BALANCED),
    ]

    base_url = "https://openapi.koreainvestment.com:9443"

    for name, path, strategy in endpoints:
        optimizer.register_endpoint(
            name=name,
            url=f"{base_url}{path}",
            strategy=strategy
        )

    return optimizer