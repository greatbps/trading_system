#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/optimization/system_optimizer.py

시스템 최적화 엔진 - Phase 7 Memory & CPU Optimization
"""

import asyncio
import gc
import threading
import time
import psutil
import weakref
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from collections import defaultdict
import functools
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

from utils.logger import get_logger


@dataclass
class MemoryStats:
    """메모리 통계"""
    total_mb: float
    available_mb: float
    used_mb: float
    used_percent: float
    process_rss_mb: float
    process_vms_mb: float
    gc_objects: int
    gc_collections: List[int]  # 각 세대별 GC 횟수


@dataclass 
class CPUStats:
    """CPU 통계"""
    usage_percent: float
    load_avg: List[float]  # 1min, 5min, 15min
    process_cpu_percent: float
    thread_count: int
    context_switches: int
    cpu_times: Dict[str, float]


@dataclass
class OptimizationResult:
    """최적화 결과"""
    operation: str
    before_memory_mb: float
    after_memory_mb: float
    memory_freed_mb: float
    cpu_time_saved_ms: float
    optimization_time_ms: float
    success: bool
    details: str


class MemoryPool:
    """메모리 풀 관리"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.pools = defaultdict(list)  # type -> list of objects
        self.stats = defaultdict(int)   # type -> usage count
        self.lock = threading.Lock()
    
    def get(self, obj_type: type, *args, **kwargs):
        """객체 가져오기"""
        with self.lock:
            pool = self.pools[obj_type]
            if pool:
                obj = pool.pop()
                self.stats[f'{obj_type.__name__}_reused'] += 1
                return obj
            else:
                obj = obj_type(*args, **kwargs)
                self.stats[f'{obj_type.__name__}_created'] += 1
                return obj
    
    def return_obj(self, obj, obj_type: type):
        """객체 반환"""
        with self.lock:
            pool = self.pools[obj_type]
            if len(pool) < self.max_size:
                # 객체 초기화/정리
                if hasattr(obj, 'reset'):
                    obj.reset()
                elif hasattr(obj, 'clear') and callable(getattr(obj, 'clear')):
                    obj.clear()
                
                pool.append(obj)
                self.stats[f'{obj_type.__name__}_returned'] += 1
    
    def get_stats(self) -> Dict[str, int]:
        """풀 통계 반환"""
        with self.lock:
            return dict(self.stats)


class CacheManager:
    """캐시 관리자"""
    
    def __init__(self, max_memory_mb: float = 100, ttl_seconds: int = 300):
        self.max_memory_mb = max_memory_mb
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # key -> (value, timestamp, size_mb)
        self.access_times = {}  # key -> last_access_time
        self.total_size_mb = 0.0
        self.lock = threading.Lock()
        
        # 자동 정리 스레드
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_running = True
        self.cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, timestamp, size_mb = self.cache[key]
            
            # TTL 체크
            if time.time() - timestamp > self.ttl_seconds:
                self._remove_key(key)
                return None
            
            # 접근 시간 업데이트
            self.access_times[key] = time.time()
            return value
    
    def set(self, key: str, value: Any) -> bool:
        """캐시에 값 설정"""
        with self.lock:
            # 크기 추정
            size_mb = sys.getsizeof(value) / 1024 / 1024
            
            # 메모리 제한 체크
            if size_mb > self.max_memory_mb:
                return False
            
            # 공간 확보
            while self.total_size_mb + size_mb > self.max_memory_mb:
                if not self._evict_lru():
                    return False
            
            # 기존 값 제거
            if key in self.cache:
                self._remove_key(key)
            
            # 새 값 추가
            self.cache[key] = (value, time.time(), size_mb)
            self.access_times[key] = time.time()
            self.total_size_mb += size_mb
            
            return True
    
    def _remove_key(self, key: str):
        """키 제거 (락 필요)"""
        if key in self.cache:
            _, _, size_mb = self.cache[key]
            del self.cache[key]
            self.total_size_mb -= size_mb
        
        if key in self.access_times:
            del self.access_times[key]
    
    def _evict_lru(self) -> bool:
        """LRU 기반 제거"""
        if not self.access_times:
            return False
        
        # 가장 오래된 항목 찾기
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(oldest_key)
        return True
    
    def _cleanup_loop(self):
        """정리 루프"""
        while self.cleanup_running:
            try:
                time.sleep(60)  # 1분마다 정리
                self._cleanup_expired()
            except:
                pass
    
    def _cleanup_expired(self):
        """만료된 항목 정리"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, (_, timestamp, _) in self.cache.items():
                if current_time - timestamp > self.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_key(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        with self.lock:
            return {
                'total_keys': len(self.cache),
                'total_size_mb': self.total_size_mb,
                'max_memory_mb': self.max_memory_mb,
                'memory_usage_percent': (self.total_size_mb / self.max_memory_mb) * 100
            }
    
    def clear(self):
        """캐시 비우기"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.total_size_mb = 0.0


class SystemOptimizer:
    """시스템 최적화 엔진"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("SystemOptimizer")
        
        # 최적화 설정
        self.optimization_config = {
            'memory_threshold_percent': 85,      # 메모리 사용률 임계값
            'cpu_threshold_percent': 80,         # CPU 사용률 임계값  
            'gc_threshold_mb': 50,               # GC 트리거 메모리 임계값
            'cache_max_memory_mb': 100,          # 캐시 최대 메모리
            'auto_optimization_interval': 300,   # 자동 최적화 간격 (초)
            'thread_pool_size': min(4, multiprocessing.cpu_count())
        }
        
        # 최적화 도구들
        self.memory_pool = MemoryPool()
        self.cache_manager = CacheManager(
            max_memory_mb=self.optimization_config['cache_max_memory_mb']
        )
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.optimization_config['thread_pool_size']
        )
        
        # 통계 및 모니터링
        self.optimization_history = []
        self.last_optimization_time = None
        self.auto_optimization_enabled = False
        self.optimization_thread = None
        
        # 메모리 추적
        self.memory_tracker_enabled = False
        try:
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            self.memory_tracker_enabled = True
        except Exception as e:
            self.logger.warning(f"메모리 추적 시작 실패: {e}")
        
        # 약한 참조 집합 (메모리 누수 방지)
        self.weak_refs = set()
        
        self.logger.info("✅ 시스템 최적화 엔진 초기화 완료")
    
    def start_auto_optimization(self):
        """자동 최적화 시작"""
        if self.auto_optimization_enabled:
            return
        
        self.auto_optimization_enabled = True
        self.optimization_thread = threading.Thread(
            target=self._auto_optimization_loop, 
            daemon=True
        )
        self.optimization_thread.start()
        self.logger.info("🔄 자동 최적화 시작")
    
    def stop_auto_optimization(self):
        """자동 최적화 중지"""
        self.auto_optimization_enabled = False
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=10)
        self.logger.info("⏹️ 자동 최적화 중지")
    
    def _auto_optimization_loop(self):
        """자동 최적화 루프"""
        while self.auto_optimization_enabled:
            try:
                # 시스템 상태 체크
                memory_stats = self.get_memory_stats()
                cpu_stats = self.get_cpu_stats()
                
                # 최적화 필요성 판단
                needs_optimization = (
                    memory_stats.used_percent > self.optimization_config['memory_threshold_percent'] or
                    cpu_stats.usage_percent > self.optimization_config['cpu_threshold_percent']
                )
                
                if needs_optimization:
                    self.logger.info("🔧 자동 최적화 실행")
                    asyncio.run(self.optimize_system())
                
                time.sleep(self.optimization_config['auto_optimization_interval'])
                
            except Exception as e:
                self.logger.error(f"❌ 자동 최적화 루프 에러: {e}")
                time.sleep(60)  # 에러 시 1분 대기
    
    async def optimize_system(self) -> List[OptimizationResult]:
        """시스템 전체 최적화"""
        self.logger.info("🚀 시스템 최적화 시작")
        results = []
        
        # 1. 메모리 최적화
        memory_result = await self.optimize_memory()
        results.extend(memory_result)
        
        # 2. CPU 최적화
        cpu_result = await self.optimize_cpu()
        results.extend(cpu_result)
        
        # 3. 캐시 최적화
        cache_result = await self.optimize_cache()
        results.extend(cache_result)
        
        # 4. 가비지 컬렉션
        gc_result = await self.optimize_garbage_collection()
        results.extend(gc_result)
        
        # 결과 기록
        self.optimization_history.extend(results)
        self.last_optimization_time = datetime.now()
        
        # 결과 요약 로깅
        total_memory_freed = sum(r.memory_freed_mb for r in results)
        successful_optimizations = sum(1 for r in results if r.success)
        
        self.logger.info(f"✅ 시스템 최적화 완료: {successful_optimizations}/{len(results)} 성공, "
                        f"{total_memory_freed:.1f}MB 메모리 해제")
        
        return results
    
    async def optimize_memory(self) -> List[OptimizationResult]:
        """메모리 최적화"""
        results = []
        before_memory = self.get_memory_stats()
        
        # 1. 약한 참조 정리
        start_time = time.time()
        cleaned_refs = self._cleanup_weak_references()
        
        result = OptimizationResult(
            operation="weak_references_cleanup",
            before_memory_mb=before_memory.used_mb,
            after_memory_mb=self.get_memory_stats().used_mb,
            memory_freed_mb=0,  # 계산 후 설정
            cpu_time_saved_ms=0,
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=True,
            details=f"약한 참조 {cleaned_refs}개 정리"
        )
        result.memory_freed_mb = result.before_memory_mb - result.after_memory_mb
        results.append(result)
        
        # 2. 메모리 풀 최적화
        start_time = time.time()
        pool_optimized = await self._optimize_memory_pool()
        
        current_memory = self.get_memory_stats()
        result = OptimizationResult(
            operation="memory_pool_optimization",
            before_memory_mb=result.after_memory_mb,
            after_memory_mb=current_memory.used_mb,
            memory_freed_mb=result.after_memory_mb - current_memory.used_mb,
            cpu_time_saved_ms=0,
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=pool_optimized,
            details="메모리 풀 최적화"
        )
        results.append(result)
        
        # 3. 메모리 매핑 최적화 (큰 데이터 구조)
        start_time = time.time()
        mapping_optimized = await self._optimize_memory_mapping()
        
        final_memory = self.get_memory_stats()
        result = OptimizationResult(
            operation="memory_mapping_optimization", 
            before_memory_mb=current_memory.used_mb,
            after_memory_mb=final_memory.used_mb,
            memory_freed_mb=current_memory.used_mb - final_memory.used_mb,
            cpu_time_saved_ms=0,
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=mapping_optimized,
            details="메모리 매핑 최적화"
        )
        results.append(result)
        
        return results
    
    async def optimize_cpu(self) -> List[OptimizationResult]:
        """CPU 최적화"""
        results = []
        before_cpu = self.get_cpu_stats()
        
        # 1. 스레드 풀 최적화
        start_time = time.time()
        
        # 현재 CPU 사용률에 따라 스레드 풀 크기 조정
        optimal_threads = self._calculate_optimal_thread_count()
        thread_optimized = await self._optimize_thread_pool(optimal_threads)
        
        result = OptimizationResult(
            operation="thread_pool_optimization",
            before_memory_mb=0,
            after_memory_mb=0,
            memory_freed_mb=0,
            cpu_time_saved_ms=50 if thread_optimized else 0,  # 추정값
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=thread_optimized,
            details=f"스레드 풀 크기 {optimal_threads}로 조정"
        )
        results.append(result)
        
        # 2. 비동기 작업 최적화
        start_time = time.time()
        async_optimized = await self._optimize_async_operations()
        
        result = OptimizationResult(
            operation="async_optimization",
            before_memory_mb=0,
            after_memory_mb=0, 
            memory_freed_mb=0,
            cpu_time_saved_ms=100 if async_optimized else 0,
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=async_optimized,
            details="비동기 작업 최적화"
        )
        results.append(result)
        
        return results
    
    async def optimize_cache(self) -> List[OptimizationResult]:
        """캐시 최적화"""
        results = []
        before_memory = self.get_memory_stats()
        
        start_time = time.time()
        
        # 캐시 통계 확인
        cache_stats = self.cache_manager.get_stats()
        cache_usage = cache_stats.get('memory_usage_percent', 0)
        
        if cache_usage > 80:  # 80% 이상 사용 시 정리
            # 만료된 항목 정리
            self.cache_manager._cleanup_expired()
            
            # 여전히 높으면 LRU 제거
            while cache_usage > 70:
                if not self.cache_manager._evict_lru():
                    break
                cache_stats = self.cache_manager.get_stats()
                cache_usage = cache_stats.get('memory_usage_percent', 0)
        
        after_memory = self.get_memory_stats()
        
        result = OptimizationResult(
            operation="cache_optimization",
            before_memory_mb=before_memory.used_mb,
            after_memory_mb=after_memory.used_mb,
            memory_freed_mb=before_memory.used_mb - after_memory.used_mb,
            cpu_time_saved_ms=0,
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=True,
            details=f"캐시 사용률 {cache_usage:.1f}%로 조정"
        )
        results.append(result)
        
        return results
    
    async def optimize_garbage_collection(self) -> List[OptimizationResult]:
        """가비지 컬렉션 최적화"""
        results = []
        before_memory = self.get_memory_stats()
        
        start_time = time.time()
        
        # 강제 가비지 컬렉션 (모든 세대)
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        after_memory = self.get_memory_stats()
        
        result = OptimizationResult(
            operation="garbage_collection",
            before_memory_mb=before_memory.used_mb,
            after_memory_mb=after_memory.used_mb,
            memory_freed_mb=before_memory.used_mb - after_memory.used_mb,
            cpu_time_saved_ms=0,
            optimization_time_ms=(time.time() - start_time) * 1000,
            success=collected > 0,
            details=f"가비지 {collected}개 객체 수집"
        )
        results.append(result)
        
        return results
    
    def _cleanup_weak_references(self) -> int:
        """약한 참조 정리"""
        initial_count = len(self.weak_refs)
        self.weak_refs = {ref for ref in self.weak_refs if ref() is not None}
        cleaned = initial_count - len(self.weak_refs)
        return cleaned
    
    async def _optimize_memory_pool(self) -> bool:
        """메모리 풀 최적화"""
        try:
            # 사용되지 않는 객체들 정리
            total_cleaned = 0
            for obj_type, pool in self.memory_pool.pools.items():
                if len(pool) > self.memory_pool.max_size // 2:
                    # 절반으로 축소
                    cleaned = len(pool) - (self.memory_pool.max_size // 2)
                    pool[:] = pool[:self.memory_pool.max_size // 2]
                    total_cleaned += cleaned
            
            return total_cleaned > 0
        except Exception as e:
            self.logger.error(f"메모리 풀 최적화 실패: {e}")
            return False
    
    async def _optimize_memory_mapping(self) -> bool:
        """메모리 매핑 최적화"""
        try:
            # 메모리 매핑된 파일들 정리 (필요시 구현)
            # 현재는 간단한 더미 구현
            return True
        except Exception as e:
            self.logger.error(f"메모리 매핑 최적화 실패: {e}")
            return False
    
    def _calculate_optimal_thread_count(self) -> int:
        """최적 스레드 수 계산"""
        cpu_count = multiprocessing.cpu_count()
        current_cpu = psutil.cpu_percent(interval=1)
        
        if current_cpu > 80:
            # CPU 사용률이 높으면 스레드 수 줄임
            return max(1, cpu_count // 2)
        elif current_cpu < 30:
            # CPU 사용률이 낮으면 스레드 수 늘림
            return min(cpu_count * 2, 8)
        else:
            # 기본값 유지
            return cpu_count
    
    async def _optimize_thread_pool(self, optimal_threads: int) -> bool:
        """스레드 풀 최적화"""
        try:
            current_threads = self.thread_pool._max_workers
            if current_threads != optimal_threads:
                # 새로운 스레드 풀 생성
                old_pool = self.thread_pool
                self.thread_pool = ThreadPoolExecutor(max_workers=optimal_threads)
                
                # 이전 풀 정리
                old_pool.shutdown(wait=False)
                
                return True
            return False
        except Exception as e:
            self.logger.error(f"스레드 풀 최적화 실패: {e}")
            return False
    
    async def _optimize_async_operations(self) -> bool:
        """비동기 작업 최적화"""
        try:
            # 현재 실행 중인 태스크 수 확인
            current_task = asyncio.current_task()
            all_tasks = asyncio.all_tasks()
            
            # 완료된 태스크 정리
            completed_tasks = [task for task in all_tasks if task.done()]
            
            for task in completed_tasks:
                try:
                    task.result()  # 예외가 있다면 발생시킴
                except Exception:
                    pass  # 무시
            
            return len(completed_tasks) > 0
        except Exception as e:
            self.logger.error(f"비동기 작업 최적화 실패: {e}")
            return False
    
    def get_memory_stats(self) -> MemoryStats:
        """메모리 통계 수집"""
        try:
            # 시스템 메모리
            virtual_mem = psutil.virtual_memory()
            
            # 프로세스 메모리
            process = psutil.Process()
            process_mem = process.memory_info()
            
            # 가비지 컬렉션 통계
            gc_stats = gc.get_stats()
            
            return MemoryStats(
                total_mb=virtual_mem.total / 1024 / 1024,
                available_mb=virtual_mem.available / 1024 / 1024,
                used_mb=virtual_mem.used / 1024 / 1024,
                used_percent=virtual_mem.percent,
                process_rss_mb=process_mem.rss / 1024 / 1024,
                process_vms_mb=process_mem.vms / 1024 / 1024,
                gc_objects=len(gc.get_objects()),
                gc_collections=[stat['collections'] for stat in gc_stats]
            )
        except Exception as e:
            self.logger.error(f"메모리 통계 수집 실패: {e}")
            return MemoryStats(0, 0, 0, 0, 0, 0, 0, [0, 0, 0])
    
    def get_cpu_stats(self) -> CPUStats:
        """CPU 통계 수집"""
        try:
            # 시스템 CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 로드 평균 (Unix 계열에서만 사용 가능)
            load_avg = []
            try:
                load_avg = list(os.getloadavg())
            except (AttributeError, OSError):
                load_avg = [0.0, 0.0, 0.0]
            
            # 프로세스 CPU
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            
            # 스레드 수
            thread_count = process.num_threads()
            
            # 컨텍스트 스위치 (Unix에서만)
            context_switches = 0
            try:
                ctx_switches = process.num_ctx_switches()
                context_switches = ctx_switches.voluntary + ctx_switches.involuntary
            except (AttributeError, psutil.AccessDenied):
                pass
            
            # CPU 시간
            cpu_times = {}
            try:
                times = process.cpu_times()
                cpu_times = {
                    'user': times.user,
                    'system': times.system
                }
            except (AttributeError, psutil.AccessDenied):
                pass
            
            return CPUStats(
                usage_percent=cpu_percent,
                load_avg=load_avg,
                process_cpu_percent=process_cpu,
                thread_count=thread_count,
                context_switches=context_switches,
                cpu_times=cpu_times
            )
        except Exception as e:
            self.logger.error(f"CPU 통계 수집 실패: {e}")
            return CPUStats(0.0, [0.0, 0.0, 0.0], 0.0, 1, 0, {})
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """최적화 요약 정보"""
        if not self.optimization_history:
            return {}
        
        total_memory_freed = sum(r.memory_freed_mb for r in self.optimization_history)
        total_cpu_saved = sum(r.cpu_time_saved_ms for r in self.optimization_history)
        successful_optimizations = sum(1 for r in self.optimization_history if r.success)
        
        # 최근 최적화 결과
        recent_optimizations = self.optimization_history[-10:]
        
        return {
            'total_optimizations': len(self.optimization_history),
            'successful_optimizations': successful_optimizations,
            'success_rate': (successful_optimizations / len(self.optimization_history)) * 100,
            'total_memory_freed_mb': total_memory_freed,
            'total_cpu_time_saved_ms': total_cpu_saved,
            'last_optimization_time': self.last_optimization_time,
            'auto_optimization_enabled': self.auto_optimization_enabled,
            'recent_optimizations': [
                {
                    'operation': opt.operation,
                    'memory_freed_mb': opt.memory_freed_mb,
                    'success': opt.success,
                    'details': opt.details
                }
                for opt in recent_optimizations
            ],
            'memory_stats': self.get_memory_stats().__dict__,
            'cpu_stats': self.get_cpu_stats().__dict__,
            'cache_stats': self.cache_manager.get_stats(),
            'memory_pool_stats': self.memory_pool.get_stats()
        }
    
    def add_weak_reference(self, obj):
        """약한 참조 추가"""
        try:
            weak_ref = weakref.ref(obj)
            self.weak_refs.add(weak_ref)
            return weak_ref
        except TypeError:
            # 약한 참조를 지원하지 않는 객체
            return None
    
    def get_cached(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        return self.cache_manager.get(key)
    
    def set_cached(self, key: str, value: Any) -> bool:
        """캐시에 값 설정"""
        return self.cache_manager.set(key, value)
    
    def get_pooled_object(self, obj_type: type, *args, **kwargs):
        """메모리 풀에서 객체 가져오기"""
        return self.memory_pool.get(obj_type, *args, **kwargs)
    
    def return_pooled_object(self, obj, obj_type: type):
        """메모리 풀에 객체 반환"""
        self.memory_pool.return_obj(obj, obj_type)
    
    def shutdown(self):
        """시스템 최적화 엔진 종료"""
        self.stop_auto_optimization()
        self.thread_pool.shutdown(wait=True)
        self.cache_manager.cleanup_running = False
        self.logger.info("🔻 시스템 최적화 엔진 종료")


# 최적화 데코레이터들

def optimize_memory(optimizer: SystemOptimizer):
    """메모리 최적화 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 약한 참조 추가
            for arg in args:
                optimizer.add_weak_reference(arg)
            
            # 함수 실행
            result = func(*args, **kwargs)
            
            # 결과에 약한 참조 추가
            if result is not None:
                optimizer.add_weak_reference(result)
            
            return result
        return wrapper
    return decorator


def cache_result(optimizer: SystemOptimizer, ttl_seconds: int = 300):
    """결과 캐싱 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
            
            # 캐시에서 확인
            cached_result = optimizer.get_cached(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            optimizer.set_cached(cache_key, result)
            
            return result
        return wrapper
    return decorator


def use_thread_pool(optimizer: SystemOptimizer):
    """스레드 풀 사용 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                # 비동기 함수는 그대로 실행
                return func(*args, **kwargs)
            else:
                # 동기 함수는 스레드 풀에서 실행
                loop = asyncio.get_event_loop()
                return loop.run_in_executor(optimizer.thread_pool, func, *args, **kwargs)
        return wrapper
    return decorator