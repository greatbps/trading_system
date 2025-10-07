#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Optimizer for Analysis Engine
=========================================

분석 성능 최적화 시스템
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from utils.logger import get_logger


class OptimizationLevel(Enum):
    """최적화 레벨"""
    CONSERVATIVE = "conservative"  # 안정성 우선
    BALANCED = "balanced"         # 균형
    AGGRESSIVE = "aggressive"     # 속도 우선


@dataclass
class PerformanceConfig:
    """성능 설정"""
    max_concurrent_stocks: int = 20      # 동시 분석 종목 수
    max_concurrent_analyzers: int = 6    # 종목당 동시 분석기 수
    llm_timeout: float = 30.0           # LLM 타임아웃 (45초 → 30초)
    price_timeout: float = 8.0          # 가격 데이터 타임아웃 (10초 → 8초)
    news_timeout: float = 4.0           # 뉴스 데이터 타임아웃 (5초 → 4초)
    enable_caching: bool = True         # 결과 캐싱
    enable_batching: bool = True        # 배치 처리
    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED


class AnalysisPerformanceOptimizer:
    """분석 성능 최적화기"""

    def __init__(self, config: PerformanceConfig = None):
        self.config = config or PerformanceConfig()
        self.logger = get_logger("PerformanceOptimizer")
        self.cache = {}
        self.batch_queue = []
        self.performance_stats = {
            "total_analyses": 0,
            "total_time": 0.0,
            "avg_time_per_stock": 0.0,
            "cache_hits": 0,
            "api_calls": 0
        }

    async def optimize_batch_analysis(self, stocks_data: List[Tuple[str, str, Dict]], strategy: str) -> List[Dict]:
        """배치 분석 최적화"""
        start_time = time.time()

        # 1. 캐시 확인으로 중복 분석 방지
        cached_results, pending_stocks = await self._check_cache(stocks_data, strategy)

        # 2. 배치 크기 최적화
        batch_size = min(self.config.max_concurrent_stocks, len(pending_stocks))

        # 3. 동시성 제어 세마포어
        semaphore = asyncio.Semaphore(batch_size)

        # 4. 최적화된 분석 작업 생성
        analysis_tasks = []
        for symbol, name, stock_data in pending_stocks:
            task = self._create_optimized_analysis_task(symbol, name, stock_data, strategy, semaphore)
            analysis_tasks.append(task)

        # 5. 병렬 실행 (청크 단위)
        results = []
        chunk_size = 10  # 한 번에 10개씩 처리

        for i in range(0, len(analysis_tasks), chunk_size):
            chunk = analysis_tasks[i:i + chunk_size]
            chunk_results = await asyncio.gather(*chunk, return_exceptions=True)
            results.extend(chunk_results)

            # 청크 간 짧은 대기 (API 부하 방지)
            if i + chunk_size < len(analysis_tasks):
                await asyncio.sleep(0.1)

        # 6. 캐시된 결과와 병합
        final_results = cached_results + [r for r in results if not isinstance(r, Exception)]

        # 7. 성능 통계 업데이트
        total_time = time.time() - start_time
        self._update_performance_stats(len(stocks_data), total_time, len(cached_results))

        self.logger.info(f"🚀 배치 분석 완료: {len(final_results)}개 종목, {total_time:.2f}초 "
                        f"(캐시: {len(cached_results)}개, 신규: {len(results)}개)")

        return final_results

    async def _create_optimized_analysis_task(self, symbol: str, name: str, stock_data: Dict,
                                            strategy: str, semaphore: asyncio.Semaphore):
        """최적화된 분석 작업 생성"""
        async with semaphore:
            return await self._analyze_with_optimization(symbol, name, stock_data, strategy)

    async def _analyze_with_optimization(self, symbol: str, name: str, stock_data: Dict, strategy: str) -> Dict:
        """최적화된 개별 종목 분석"""
        start_time = time.time()

        try:
            # 1. 데이터 수집 최적화 (타임아웃 단축)
            price_data, news_data = await self._gather_data_optimized(symbol, name)

            # 2. 분석기 병렬 실행 (우선순위 기반)
            analysis_results = await self._run_analyzers_optimized(symbol, name, stock_data,
                                                                  price_data, news_data, strategy)

            # 3. 결과 캐싱
            if self.config.enable_caching:
                cache_key = f"{symbol}_{strategy}_{int(time.time() / 3600)}"  # 1시간 캐시
                self.cache[cache_key] = analysis_results

            execution_time = time.time() - start_time
            self.logger.debug(f"✅ {symbol} 최적화 분석 완료: {execution_time:.2f}초")

            return analysis_results

        except Exception as e:
            self.logger.error(f"❌ {symbol} 최적화 분석 실패: {e}")
            return self._get_fallback_result(symbol, name, strategy)

    async def _gather_data_optimized(self, symbol: str, name: str) -> Tuple[Optional[List], Optional[List]]:
        """최적화된 데이터 수집"""
        tasks = []

        # 병렬 데이터 수집 (단축된 타임아웃)
        if hasattr(self, 'data_collector') and self.data_collector:
            price_task = asyncio.wait_for(
                self.data_collector.get_ohlcv_data(symbol, 'D', 100),
                timeout=self.config.price_timeout
            )
            news_task = asyncio.wait_for(
                self.data_collector.get_news_data(symbol, name),
                timeout=self.config.news_timeout
            )
            tasks = [price_task, news_task]

        if not tasks:
            return None, None

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 처리
        price_data = results[0] if not isinstance(results[0], Exception) else None
        news_data = results[1] if not isinstance(results[1], Exception) else None

        return price_data, news_data

    async def _run_analyzers_optimized(self, symbol: str, name: str, stock_data: Dict,
                                     price_data, news_data, strategy: str) -> Dict:
        """분석기 최적화 실행 (우선순위 기반)"""

        # 1. 필수 분석기들 (빠른 실행)
        essential_tasks = [
            ("technical", self._run_technical_analysis(symbol, price_data)),
            ("fundamental", self._run_fundamental_analysis(symbol, stock_data))
        ]

        # 2. 고급 분석기들 (느린 실행)
        advanced_tasks = [
            ("sentiment", self._run_sentiment_analysis(symbol, name, news_data)),
            ("supply_demand", self._run_supply_demand_analysis(symbol, stock_data))
        ]

        # 3. AI 분석기 (가장 느림, 최적화된 타임아웃)
        ai_tasks = [
            ("multi_llm", self._run_llm_analysis_optimized(symbol, name, stock_data, strategy))
        ]

        # 단계별 병렬 실행
        results = {}

        # 1단계: 필수 분석 (빠름)
        essential_results = await asyncio.gather(*[t[1] for t in essential_tasks], return_exceptions=True)
        for i, (name, _) in enumerate(essential_tasks):
            results[name] = essential_results[i] if not isinstance(essential_results[i], Exception) else {}

        # 2단계: 고급 분석 (중간)
        advanced_results = await asyncio.gather(*[t[1] for t in advanced_tasks], return_exceptions=True)
        for i, (name, _) in enumerate(advanced_tasks):
            results[name] = advanced_results[i] if not isinstance(advanced_results[i], Exception) else {}

        # 3단계: AI 분석 (느림, 단축된 타임아웃)
        ai_results = await asyncio.gather(*[t[1] for t in ai_tasks], return_exceptions=True)
        for i, (name, _) in enumerate(ai_tasks):
            results[name] = ai_results[i] if not isinstance(ai_results[i], Exception) else {}

        return results

    async def _run_llm_analysis_optimized(self, symbol: str, name: str, stock_data: Dict, strategy: str):
        """LLM 분석 최적화 (타임아웃 단축)"""
        try:
            # 단축된 타임아웃으로 LLM 호출
            return await asyncio.wait_for(
                self._call_llm_analyzer(symbol, name, stock_data, strategy),
                timeout=self.config.llm_timeout  # 45초 → 30초
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"⏰ {symbol} LLM 분석 타임아웃 ({self.config.llm_timeout}초)")
            return {"llm_analysis": "timeout", "buy_score": 50, "confidence": 30}
        except Exception as e:
            self.logger.error(f"❌ {symbol} LLM 분석 실패: {e}")
            return {"llm_analysis": "error", "buy_score": 50, "confidence": 20}

    async def _check_cache(self, stocks_data: List[Tuple], strategy: str) -> Tuple[List, List]:
        """캐시 확인으로 중복 분석 방지"""
        cached_results = []
        pending_stocks = []

        if not self.config.enable_caching:
            return [], stocks_data

        current_hour = int(time.time() / 3600)

        for symbol, name, stock_data in stocks_data:
            cache_key = f"{symbol}_{strategy}_{current_hour}"
            if cache_key in self.cache:
                cached_results.append(self.cache[cache_key])
                self.performance_stats["cache_hits"] += 1
                self.logger.debug(f"💾 {symbol} 캐시 히트")
            else:
                pending_stocks.append((symbol, name, stock_data))

        return cached_results, pending_stocks

    def _update_performance_stats(self, total_stocks: int, total_time: float, cache_hits: int):
        """성능 통계 업데이트"""
        self.performance_stats["total_analyses"] += total_stocks
        self.performance_stats["total_time"] += total_time
        self.performance_stats["avg_time_per_stock"] = (
            self.performance_stats["total_time"] / max(self.performance_stats["total_analyses"], 1)
        )

        if total_stocks > cache_hits:
            actual_analysis_time = total_time * (total_stocks - cache_hits) / total_stocks
            avg_per_new_stock = actual_analysis_time / max(total_stocks - cache_hits, 1)
            self.logger.info(f"📊 성능 통계: 신규분석 {avg_per_new_stock:.2f}초/종목, "
                           f"캐시율 {cache_hits/total_stocks*100:.1f}%")

    def get_performance_report(self) -> Dict:
        """성능 리포트 생성"""
        return {
            **self.performance_stats,
            "cache_size": len(self.cache),
            "optimization_level": self.config.optimization_level.value,
            "config": {
                "max_concurrent_stocks": self.config.max_concurrent_stocks,
                "llm_timeout": self.config.llm_timeout,
                "price_timeout": self.config.price_timeout,
                "news_timeout": self.config.news_timeout
            }
        }

    # 플레이스홀더 메서드들 (실제 분석기 연결 필요)
    async def _run_technical_analysis(self, symbol: str, price_data) -> Dict:
        await asyncio.sleep(0.1)  # 빠른 분석 시뮬레이션
        return {"technical_score": 70}

    async def _run_fundamental_analysis(self, symbol: str, stock_data: Dict) -> Dict:
        await asyncio.sleep(0.1)  # 빠른 분석 시뮬레이션
        return {"fundamental_score": 65}

    async def _run_sentiment_analysis(self, symbol: str, name: str, news_data) -> Dict:
        await asyncio.sleep(1.0)  # 중간 속도 분석 시뮬레이션
        return {"sentiment_score": 60}

    async def _run_supply_demand_analysis(self, symbol: str, stock_data: Dict) -> Dict:
        await asyncio.sleep(1.0)  # 중간 속도 분석 시뮬레이션
        return {"supply_demand_score": 75}

    async def _call_llm_analyzer(self, symbol: str, name: str, stock_data: Dict, strategy: str) -> Dict:
        await asyncio.sleep(5.0)  # LLM 분석 시뮬레이션 (실제 구현 필요)
        return {"llm_score": 80, "buy_score": 75, "confidence": 85}

    def _get_fallback_result(self, symbol: str, name: str, strategy: str) -> Dict:
        """폴백 결과"""
        return {
            "symbol": symbol,
            "name": name,
            "strategy": strategy,
            "comprehensive_score": 50,
            "recommendation": "HOLD",
            "analysis_results": {},
            "execution_time": 0.1,
            "fallback": True
        }


# 글로벌 최적화기 인스턴스
performance_optimizer = None

def get_performance_optimizer(config: PerformanceConfig = None):
    """글로벌 성능 최적화기 반환"""
    global performance_optimizer
    if performance_optimizer is None:
        performance_optimizer = AnalysisPerformanceOptimizer(config)
    return performance_optimizer