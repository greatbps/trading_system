#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading System Optimization Recommendations
==========================================

실시간 매매 로직 최적화 방안 제시
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from utils.logger import get_logger


class TradingOptimizer:
    """매매 시스템 최적화 도구"""

    def __init__(self):
        self.logger = get_logger("TradingOptimizer")

    def generate_optimization_plan(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """성능 데이터 기반 최적화 계획 생성"""

        optimization_plan = {
            "timestamp": datetime.now().isoformat(),
            "current_performance": self._analyze_current_performance(performance_data),
            "bottlenecks": self._identify_bottlenecks(performance_data),
            "optimization_strategies": self._generate_optimization_strategies(performance_data),
            "implementation_roadmap": self._create_implementation_roadmap(performance_data),
            "expected_improvements": self._calculate_expected_improvements(performance_data)
        }

        return optimization_plan

    def _analyze_current_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """현재 성능 분석"""
        results = data.get('results', {})

        current_perf = {
            "종목당_평균_처리시간": {
                "현재가_조회": round(results.get('current_price', {}).get('avg_time', 0) * 1000, 2),  # ms
                "차트_데이터": round(results.get('chart_data', {}).get('avg_time', 0) * 1000, 2),
                "기술적_분석": round(results.get('technical_analysis', {}).get('avg_time', 0) * 1000, 2),
                "전체_사이클": round(results.get('full_cycle', {}).get('avg_time', 0) * 1000, 2)
            },
            "성공률": {
                "현재가_조회": results.get('current_price', {}).get('success_rate', 0),
                "차트_데이터": results.get('chart_data', {}).get('success_rate', 0),
                "기술적_분석": results.get('technical_analysis', {}).get('success_rate', 0)
            },
            "처리_용량": {
                "순차_처리": data.get('summary', {}).get('estimated_capacity', {}).get('sequential_processing', 0),
                "병렬_처리": data.get('summary', {}).get('estimated_capacity', {}).get('parallel_processing', 0)
            }
        }

        return current_perf

    def _identify_bottlenecks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """병목 지점 식별"""
        results = data.get('results', {})
        bottlenecks = []

        # 1. 현재가 조회 병목
        current_price_time = results.get('current_price', {}).get('avg_time', 0)
        if current_price_time > 0.05:  # 50ms 이상
            bottlenecks.append({
                "component": "현재가 조회 (KIS API)",
                "current_time_ms": round(current_price_time * 1000, 2),
                "severity": "HIGH" if current_price_time > 0.1 else "MEDIUM",
                "impact": "API 호출 대기시간으로 인한 전체 처리 지연",
                "optimization_potential": "40-60% 성능 향상 가능"
            })

        # 2. 차트 데이터 수집 병목
        chart_data_time = results.get('chart_data', {}).get('avg_time', 0)
        if chart_data_time > 0.02:  # 20ms 이상
            bottlenecks.append({
                "component": "차트 데이터 수집",
                "current_time_ms": round(chart_data_time * 1000, 2),
                "severity": "LOW",  # 현재는 빠름
                "impact": "데이터 처리량 증가 시 병목 가능성",
                "optimization_potential": "캐싱으로 90% 성능 향상 가능"
            })

        # 3. 기술적 분석 병목
        technical_time = results.get('technical_analysis', {}).get('avg_time', 0)
        if technical_time > 0.02:  # 20ms 이상
            bottlenecks.append({
                "component": "기술적 분석 계산",
                "current_time_ms": round(technical_time * 1000, 2),
                "severity": "LOW",  # 현재는 빠름
                "impact": "복잡한 지표 계산 시 처리 지연",
                "optimization_potential": "알고리즘 최적화로 30% 향상 가능"
            })

        # 4. 전체 사이클 시간 평가
        full_cycle_time = results.get('full_cycle', {}).get('avg_time', 0)
        if full_cycle_time > 0.1:  # 100ms 이상
            bottlenecks.append({
                "component": "전체 매매 사이클",
                "current_time_ms": round(full_cycle_time * 1000, 2),
                "severity": "MEDIUM" if full_cycle_time > 0.2 else "LOW",
                "impact": "종목 수 증가 시 모니터링 주기 지연",
                "optimization_potential": "병렬 처리로 70% 향상 가능"
            })

        return bottlenecks

    def _generate_optimization_strategies(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """최적화 전략 생성"""
        strategies = []

        # 1. API 호출 최적화
        strategies.append({
            "strategy": "API 호출 최적화",
            "priority": "HIGH",
            "techniques": [
                {
                    "name": "배치 API 호출",
                    "description": "여러 종목의 현재가를 한 번에 조회",
                    "implementation": "KIS API의 batch 엔드포인트 활용",
                    "expected_improvement": "API 호출 수 80% 감소"
                },
                {
                    "name": "비동기 병렬 처리",
                    "description": "asyncio.gather()를 활용한 동시 API 호출",
                    "implementation": "현재 순차 처리를 병렬 처리로 변경",
                    "expected_improvement": "처리 시간 60% 단축"
                },
                {
                    "name": "API 연결 풀링",
                    "description": "HTTP 연결 재사용으로 오버헤드 감소",
                    "implementation": "aiohttp.ClientSession의 connector 최적화",
                    "expected_improvement": "연결 오버헤드 50% 감소"
                }
            ]
        })

        # 2. 데이터 캐싱 시스템
        strategies.append({
            "strategy": "데이터 캐싱 시스템",
            "priority": "MEDIUM",
            "techniques": [
                {
                    "name": "메모리 캐싱",
                    "description": "자주 조회되는 데이터의 메모리 캐싱",
                    "implementation": "Redis 또는 in-memory cache 구현",
                    "expected_improvement": "반복 조회 95% 속도 향상"
                },
                {
                    "name": "스마트 캐시 무효화",
                    "description": "시간 기반 및 이벤트 기반 캐시 갱신",
                    "implementation": "TTL 및 실시간 업데이트 감지",
                    "expected_improvement": "데이터 일관성 + 성능 유지"
                },
                {
                    "name": "차트 데이터 프리로딩",
                    "description": "백그라운드에서 미리 데이터 수집",
                    "implementation": "스케줄러 기반 백그라운드 작업",
                    "expected_improvement": "실시간 조회 시간 90% 단축"
                }
            ]
        })

        # 3. 알고리즘 최적화
        strategies.append({
            "strategy": "알고리즘 최적화",
            "priority": "MEDIUM",
            "techniques": [
                {
                    "name": "기술적 지표 계산 최적화",
                    "description": "NumPy/Pandas 벡터화 연산 활용",
                    "implementation": "반복문을 벡터 연산으로 변경",
                    "expected_improvement": "계산 속도 40% 향상"
                },
                {
                    "name": "점진적 계산",
                    "description": "전체 재계산 대신 증분 업데이트",
                    "implementation": "이동평균 등의 점진적 계산 방식",
                    "expected_improvement": "계산 복잡도 70% 감소"
                },
                {
                    "name": "불필요한 계산 제거",
                    "description": "조건부 계산으로 연산량 최소화",
                    "implementation": "early exit 패턴 적용",
                    "expected_improvement": "불필요한 연산 50% 제거"
                }
            ]
        })

        # 4. 시스템 아키텍처 개선
        strategies.append({
            "strategy": "시스템 아키텍처 개선",
            "priority": "LOW",
            "techniques": [
                {
                    "name": "마이크로서비스 분리",
                    "description": "데이터 수집, 분석, 실행 모듈 분리",
                    "implementation": "독립적인 서비스로 분리 및 메시지 큐 연동",
                    "expected_improvement": "확장성 및 안정성 향상"
                },
                {
                    "name": "이벤트 기반 아키텍처",
                    "description": "실시간 데이터 스트리밍 처리",
                    "implementation": "WebSocket 또는 Server-Sent Events",
                    "expected_improvement": "실시간성 향상"
                },
                {
                    "name": "로드 밸런싱",
                    "description": "다중 인스턴스 기반 분산 처리",
                    "implementation": "종목별 샤딩 및 인스턴스 분산",
                    "expected_improvement": "처리 용량 N배 확장"
                }
            ]
        })

        return strategies

    def _create_implementation_roadmap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """구현 로드맵 생성"""

        roadmap = {
            "Phase_1_즉시_적용": {
                "기간": "1-2주",
                "우선순위": "HIGH",
                "작업_목록": [
                    {
                        "task": "비동기 병렬 처리 구현",
                        "description": "현재 순차 처리를 asyncio.gather()로 변경",
                        "effort": "Medium",
                        "impact": "High",
                        "implementation_file": "trading/db_auto_trader.py",
                        "code_changes": [
                            "_analyze_stocks_parallel() 메서드 개선",
                            "asyncio.gather() 최적화",
                            "세마포어 기반 동시성 제어"
                        ]
                    },
                    {
                        "task": "API 호출 최적화",
                        "description": "불필요한 재시도 로직 제거 및 타임아웃 조정",
                        "effort": "Low",
                        "impact": "Medium",
                        "implementation_file": "data_collectors/kis_collector.py",
                        "code_changes": [
                            "API 타임아웃 최적화 (15초 → 5초)",
                            "효율적인 재시도 로직",
                            "연결 풀 크기 조정"
                        ]
                    }
                ],
                "예상_성능_향상": "종목당 처리시간 40-50% 단축"
            },
            "Phase_2_중기_개선": {
                "기간": "3-4주",
                "우선순위": "MEDIUM",
                "작업_목록": [
                    {
                        "task": "메모리 캐싱 시스템 구현",
                        "description": "Redis 기반 캐싱 레이어 추가",
                        "effort": "High",
                        "impact": "High",
                        "implementation_file": "새로운 caching/ 모듈",
                        "code_changes": [
                            "Redis 연동 캐시 매니저",
                            "스마트 캐시 무효화",
                            "캐시 히트율 모니터링"
                        ]
                    },
                    {
                        "task": "백그라운드 데이터 프리로딩",
                        "description": "스케줄러 기반 사전 데이터 수집",
                        "effort": "Medium",
                        "impact": "Medium",
                        "implementation_file": "background_services/",
                        "code_changes": [
                            "백그라운드 스케줄러",
                            "데이터 프리로딩 로직",
                            "캐시와 연동"
                        ]
                    }
                ],
                "예상_성능_향상": "반복 조회 80-90% 속도 향상"
            },
            "Phase_3_장기_혁신": {
                "기간": "2-3개월",
                "우선순위": "LOW",
                "작업_목록": [
                    {
                        "task": "실시간 스트리밍 아키텍처",
                        "description": "WebSocket 기반 실시간 데이터 처리",
                        "effort": "Very High",
                        "impact": "Very High",
                        "implementation_file": "streaming/ 모듈",
                        "code_changes": [
                            "WebSocket 클라이언트",
                            "실시간 이벤트 처리",
                            "스트림 데이터 파이프라인"
                        ]
                    },
                    {
                        "task": "ML 기반 성능 예측",
                        "description": "머신러닝으로 시장 상황별 최적 파라미터",
                        "effort": "Very High",
                        "impact": "Medium",
                        "implementation_file": "ml_optimization/",
                        "code_changes": [
                            "성능 예측 모델",
                            "동적 파라미터 조정",
                            "A/B 테스트 프레임워크"
                        ]
                    }
                ],
                "예상_성능_향상": "전체 시스템 효율성 2-3배 개선"
            }
        }

        return roadmap

    def _calculate_expected_improvements(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """예상 성능 개선 효과 계산"""
        current_times = data.get('results', {})

        improvements = {
            "현재_성능": {
                "종목당_처리시간_ms": round(current_times.get('full_cycle', {}).get('avg_time', 0) * 1000, 2),
                "30초_주기_최대_종목수": data.get('summary', {}).get('estimated_capacity', {}).get('sequential_processing', 0)
            },
            "Phase_1_적용후": {
                "종목당_처리시간_ms": round(current_times.get('full_cycle', {}).get('avg_time', 0) * 1000 * 0.5, 2),  # 50% 단축
                "30초_주기_최대_종목수": int(data.get('summary', {}).get('estimated_capacity', {}).get('sequential_processing', 0) * 2),
                "개선율": "100% 향상"
            },
            "Phase_2_적용후": {
                "종목당_처리시간_ms": round(current_times.get('full_cycle', {}).get('avg_time', 0) * 1000 * 0.2, 2),  # 80% 단축
                "30초_주기_최대_종목수": int(data.get('summary', {}).get('estimated_capacity', {}).get('sequential_processing', 0) * 5),
                "개선율": "500% 향상"
            },
            "Phase_3_적용후": {
                "종목당_처리시간_ms": "실시간 스트리밍 (즉시 반응)",
                "30초_주기_최대_종목수": "무제한 (이벤트 기반)",
                "개선율": "실시간 처리 체계로 전환"
            }
        }

        return improvements

    def generate_implementation_code(self) -> Dict[str, str]:
        """구현 코드 샘플 생성"""

        code_samples = {
            "병렬_처리_최적화": '''
# trading/db_auto_trader.py - 개선된 병렬 처리

async def _analyze_stocks_parallel_optimized(self, stock_list: List) -> List:
    """최적화된 병렬 종목 분석"""
    # 동적 세마포어 - 시스템 리소스에 따라 조정
    optimal_concurrent = min(len(stock_list), self.max_concurrent_analysis)
    semaphore = asyncio.Semaphore(optimal_concurrent)

    async def analyze_with_optimized_semaphore(stock_data):
        async with semaphore:
            start_time = time.time()
            try:
                # 타임아웃을 더 짧게 설정하여 빠른 실패
                analyze_task = asyncio.create_task(
                    self._analyze_stock_by_id(stock_data.id, stock_data.symbol, stock_data.name)
                )
                await asyncio.wait_for(analyze_task, timeout=10.0)  # 15초 → 10초

                analysis_time = time.time() - start_time
                self.analysis_times.append(analysis_time)
                return {'symbol': stock_data.symbol, 'success': True, 'time': analysis_time}

            except asyncio.TimeoutError:
                analysis_time = time.time() - start_time
                self.analysis_times.append(analysis_time)
                self.logger.warning(f"⏰ {stock_data.symbol} 분석 타임아웃 (10초)")
                return {'symbol': stock_data.symbol, 'success': False, 'error': 'timeout', 'time': analysis_time}
            except Exception as e:
                analysis_time = time.time() - start_time
                self.analysis_times.append(analysis_time)
                return {'symbol': stock_data.symbol, 'success': False, 'error': str(e), 'time': analysis_time}

    # 청크 단위로 처리하여 메모리 사용량 제어
    chunk_size = 10
    all_results = []

    for i in range(0, len(stock_list), chunk_size):
        chunk = stock_list[i:i + chunk_size]
        chunk_tasks = [analyze_with_optimized_semaphore(stock) for stock in chunk]
        chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
        all_results.extend(chunk_results)

        # 청크 간 짧은 휴식으로 시스템 부하 분산
        if i + chunk_size < len(stock_list):
            await asyncio.sleep(0.1)

    return all_results
            ''',

            "API_배치_호출": '''
# data_collectors/kis_collector.py - 배치 API 호출

async def get_multiple_current_prices(self, symbols: List[str]) -> Dict[str, Optional[int]]:
    """여러 종목 현재가 배치 조회"""
    if not symbols:
        return {}

    # 10개씩 청크로 나누어 처리 (API 한도 고려)
    chunk_size = 10
    all_results = {}

    for i in range(0, len(symbols), chunk_size):
        chunk_symbols = symbols[i:i + chunk_size]

        # 병렬 API 호출 (하지만 rate limit 준수)
        await self.rate_limiter.acquire()

        tasks = []
        for symbol in chunk_symbols:
            task = asyncio.create_task(self.get_current_price(symbol))
            tasks.append((symbol, task))

        # 배치 실행
        for symbol, task in tasks:
            try:
                price = await asyncio.wait_for(task, timeout=3.0)  # 짧은 타임아웃
                all_results[symbol] = price
            except Exception as e:
                self.logger.warning(f"❌ {symbol} 현재가 조회 실패: {e}")
                all_results[symbol] = None

        # API rate limit 준수를 위한 대기
        if i + chunk_size < len(symbols):
            await asyncio.sleep(0.1)  # 100ms 대기

    return all_results
            ''',

            "캐싱_시스템": '''
# caching/cache_manager.py - Redis 캐싱 시스템

import redis.asyncio as redis
import json
from datetime import timedelta

class TradingCacheManager:
    """매매 시스템용 캐싱 매니저"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

        # 캐시 TTL 설정
        self.cache_ttl = {
            'current_price': 5,      # 현재가: 5초
            'chart_data': 300,       # 차트 데이터: 5분
            'technical_analysis': 60, # 기술적 분석: 1분
            'market_status': 30      # 시장 상태: 30초
        }

    async def get_current_price(self, symbol: str) -> Optional[int]:
        """캐시된 현재가 조회"""
        cache_key = f"current_price:{symbol}"
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return data['price']
        except Exception as e:
            self.logger.warning(f"캐시 조회 실패: {e}")
        return None

    async def set_current_price(self, symbol: str, price: int):
        """현재가 캐시 저장"""
        cache_key = f"current_price:{symbol}"
        data = {
            'price': price,
            'timestamp': datetime.now().isoformat()
        }
        try:
            await self.redis.setex(
                cache_key,
                self.cache_ttl['current_price'],
                json.dumps(data, default=str)
            )
        except Exception as e:
            self.logger.warning(f"캐시 저장 실패: {e}")

    async def get_or_fetch_current_price(self, symbol: str, fetch_func) -> Optional[int]:
        """캐시 우선 조회, 없으면 API 호출"""
        # 1. 캐시에서 조회
        cached_price = await self.get_current_price(symbol)
        if cached_price is not None:
            return cached_price

        # 2. API에서 조회
        try:
            fresh_price = await fetch_func(symbol)
            if fresh_price:
                # 3. 캐시에 저장
                await self.set_current_price(symbol, fresh_price)
                return fresh_price
        except Exception as e:
            self.logger.error(f"API 조회 실패: {e}")

        return None
            ''',

            "성능_모니터링": '''
# monitoring/performance_monitor.py - 실시간 성능 모니터링

import time
import statistics
from collections import deque
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    operation: str
    avg_time: float
    max_time: float
    min_time: float
    success_rate: float
    throughput: float  # 초당 처리량

class RealTimePerformanceMonitor:
    """실시간 성능 모니터링"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics = {
            'current_price': deque(maxlen=window_size),
            'chart_data': deque(maxlen=window_size),
            'technical_analysis': deque(maxlen=window_size),
            'full_cycle': deque(maxlen=window_size)
        }
        self.start_time = time.time()

    def record_execution(self, operation: str, execution_time: float, success: bool):
        """실행 기록"""
        self.metrics[operation].append({
            'time': execution_time,
            'success': success,
            'timestamp': time.time()
        })

    def get_current_metrics(self) -> Dict[str, PerformanceMetrics]:
        """현재 성능 메트릭 계산"""
        current_metrics = {}

        for operation, records in self.metrics.items():
            if not records:
                continue

            times = [r['time'] for r in records]
            successes = [r['success'] for r in records]

            # 처리량 계산 (최근 1분간)
            now = time.time()
            recent_records = [r for r in records if now - r['timestamp'] <= 60]
            throughput = len(recent_records) / 60.0 if recent_records else 0

            current_metrics[operation] = PerformanceMetrics(
                operation=operation,
                avg_time=statistics.mean(times),
                max_time=max(times),
                min_time=min(times),
                success_rate=sum(successes) / len(successes) * 100,
                throughput=throughput
            )

        return current_metrics

    def should_enable_parallel_processing(self) -> bool:
        """병렬 처리 활성화 여부 결정"""
        metrics = self.get_current_metrics()
        full_cycle = metrics.get('full_cycle')

        if not full_cycle:
            return False

        # 평균 처리시간이 50ms 이상이거나 처리량이 낮으면 병렬 처리 권장
        return full_cycle.avg_time > 0.05 or full_cycle.throughput < 10

    def get_optimization_recommendations(self) -> List[str]:
        """최적화 권장사항"""
        metrics = self.get_current_metrics()
        recommendations = []

        for operation, metric in metrics.items():
            if metric.avg_time > 0.1:  # 100ms 이상
                recommendations.append(f"{operation} 처리시간 최적화 필요 ({metric.avg_time*1000:.1f}ms)")

            if metric.success_rate < 95:
                recommendations.append(f"{operation} 성공률 개선 필요 ({metric.success_rate:.1f}%)")

            if metric.throughput < 5:  # 초당 5개 미만
                recommendations.append(f"{operation} 처리량 증대 필요 ({metric.throughput:.1f}/sec)")

        return recommendations
            '''
        }

        return code_samples

    def save_optimization_plan(self, plan: Dict[str, Any], filename: str = None):
        """최적화 계획 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optimization_plan_{timestamp}.json"

        output_path = Path(f"D:/trading_system/optimization_plans/{filename}")
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"📋 최적화 계획 저장: {output_path}")
        return output_path


async def main():
    """최적화 계획 생성"""
    try:
        # 성능 분석 결과 로드
        performance_file = Path("D:/trading_system/performance_reports/performance_analysis_20250921_172606.json")

        if not performance_file.exists():
            print("❌ 성능 분석 결과 파일을 찾을 수 없습니다.")
            print("먼저 performance_analysis_tool.py를 실행하세요.")
            return

        with open(performance_file, 'r', encoding='utf-8') as f:
            performance_data = json.load(f)

        # 최적화 도구 초기화
        optimizer = TradingOptimizer()

        # 최적화 계획 생성
        optimization_plan = optimizer.generate_optimization_plan(performance_data)

        # 구현 코드 샘플 추가
        code_samples = optimizer.generate_implementation_code()
        optimization_plan['code_samples'] = code_samples

        # 결과 저장
        output_file = optimizer.save_optimization_plan(optimization_plan)

        # 요약 출력
        print("\n" + "="*80)
        print("🚀 매매 로직 최적화 계획")
        print("="*80)

        print(f"📊 현재 성능: {optimization_plan['current_performance']['종목당_평균_처리시간']['전체_사이클']}ms/종목")

        if optimization_plan['bottlenecks']:
            print("\n🔍 주요 병목 지점:")
            for bottleneck in optimization_plan['bottlenecks']:
                print(f"  - {bottleneck['component']}: {bottleneck['current_time_ms']}ms ({bottleneck['severity']})")

        print("\n💡 최적화 전략:")
        for i, strategy in enumerate(optimization_plan['optimization_strategies'], 1):
            print(f"  {i}. {strategy['strategy']} (우선순위: {strategy['priority']})")

        print("\n📈 예상 성능 개선:")
        improvements = optimization_plan['expected_improvements']
        for phase, metrics in improvements.items():
            if phase.startswith('Phase'):
                print(f"  {phase}: {metrics.get('개선율', 'N/A')}")

        print(f"\n📄 상세 계획: {output_file}")
        print("="*80)

    except Exception as e:
        print(f"❌ 최적화 계획 생성 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())