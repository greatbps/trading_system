#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/utils/performance_optimizer.py

시스템 성능 최적화 유틸리티
"""

import asyncio
import time
import psutil
import gc
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import threading
import weakref

@dataclass
class PerformanceMetrics:
    """성능 지표 데이터 클래스"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    active_threads: int
    async_tasks: int
    response_time_ms: float = 0.0
    throughput_ops_sec: float = 0.0
    error_rate: float = 0.0

class PerformanceOptimizer:
    """시스템 성능 최적화 관리자"""
    
    def __init__(self, max_history: int = 1000):
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = max_history
        self.optimization_enabled = True
        self.gc_threshold = 85.0  # 메모리 85% 사용 시 가비지 컬렉션
        self.task_cache = weakref.WeakValueDictionary()
        self._lock = threading.Lock()
        
    def collect_metrics(self) -> PerformanceMetrics:
        """현재 시스템 성능 지표 수집"""
        try:
            # 시스템 리소스 정보
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # 스레드 및 태스크 정보
            active_threads = threading.active_count()
            
            # 비동기 태스크 수 (현재 이벤트 루프가 있는 경우)
            async_tasks = 0
            try:
                loop = asyncio.get_running_loop()
                async_tasks = len([task for task in asyncio.all_tasks(loop) if not task.done()])
            except RuntimeError:
                pass
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                active_threads=active_threads,
                async_tasks=async_tasks
            )
            
            # 히스토리에 추가
            with self._lock:
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
            
            # 자동 최적화 실행
            if self.optimization_enabled:
                self._auto_optimize(metrics)
            
            return metrics
            
        except Exception as e:
            print(f"Error collecting performance metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                active_threads=0,
                async_tasks=0
            )
    
    def _auto_optimize(self, metrics: PerformanceMetrics):
        """자동 최적화 실행"""
        # 메모리 최적화
        if metrics.memory_percent > self.gc_threshold:
            self._optimize_memory()
        
        # 태스크 정리
        if metrics.async_tasks > 100:
            self._cleanup_async_tasks()
    
    def _optimize_memory(self):
        """메모리 최적화"""
        try:
            # 가비지 컬렉션 강제 실행
            collected = gc.collect()
            print(f"Memory optimization: Collected {collected} objects")
            
            # 약한 참조 캐시 정리
            self.task_cache.clear()
            
        except Exception as e:
            print(f"Error in memory optimization: {e}")
    
    def _cleanup_async_tasks(self):
        """비동기 태스크 정리"""
        try:
            loop = asyncio.get_running_loop()
            tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
            
            # 완료된 태스크 정리
            completed_tasks = [task for task in asyncio.all_tasks(loop) if task.done()]
            for task in completed_tasks[:50]:  # 최대 50개씩 정리
                if task.exception() is None:
                    task.result()  # 결과를 가져와서 정리
                    
        except Exception as e:
            print(f"Error in async task cleanup: {e}")
    
    def get_performance_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """성능 요약 정보 반환"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {"error": "No recent metrics available"}
        
        # 통계 계산
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            "period_minutes": minutes,
            "sample_count": len(recent_metrics),
            "cpu_usage": {
                "current": recent_metrics[-1].cpu_percent,
                "average": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_usage": {
                "current": recent_metrics[-1].memory_percent,
                "average": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values),
                "used_mb": recent_metrics[-1].memory_used_mb
            },
            "tasks": {
                "threads": recent_metrics[-1].active_threads,
                "async_tasks": recent_metrics[-1].async_tasks
            },
            "optimization_status": "enabled" if self.optimization_enabled else "disabled"
        }
    
    def print_performance_report(self):
        """성능 보고서 출력"""
        summary = self.get_performance_summary()
        
        if "error" in summary:
            print(f"Performance Report Error: {summary['error']}")
            return
        
        print("\n" + "="*60)
        print("           SYSTEM PERFORMANCE REPORT")
        print("="*60)
        
        print(f"Period: Last {summary['period_minutes']} minutes ({summary['sample_count']} samples)")
        print()
        
        cpu = summary['cpu_usage']
        print(f"CPU Usage:")
        print(f"  Current: {cpu['current']:.1f}%")
        print(f"  Average: {cpu['average']:.1f}%")
        print(f"  Range: {cpu['min']:.1f}% - {cpu['max']:.1f}%")
        print()
        
        mem = summary['memory_usage']
        print(f"Memory Usage:")
        print(f"  Current: {mem['current']:.1f}% ({mem['used_mb']:.0f} MB)")
        print(f"  Average: {mem['average']:.1f}%")
        print(f"  Range: {mem['min']:.1f}% - {mem['max']:.1f}%")
        print()
        
        tasks = summary['tasks']
        print(f"Active Tasks:")
        print(f"  Threads: {tasks['threads']}")
        print(f"  Async Tasks: {tasks['async_tasks']}")
        print()
        
        print(f"Optimization: {summary['optimization_status'].upper()}")
        print("="*60)

def performance_monitor(interval_seconds: float = 1.0):
    """성능 모니터링 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                print(f"[PERF] {func.__name__}: {response_time:.2f}ms")
                return result
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                print(f"[PERF] {func.__name__}: {response_time:.2f}ms (ERROR: {e})")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                print(f"[PERF] {func.__name__}: {response_time:.2f}ms")
                return result
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                print(f"[PERF] {func.__name__}: {response_time:.2f}ms (ERROR: {e})")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

class ResourceManager:
    """리소스 관리자"""
    
    def __init__(self):
        self.connection_pools = {}
        self.cache_objects = weakref.WeakValueDictionary()
        self.active_connections = 0
        self.max_connections = 100
    
    async def get_connection(self, service_name: str):
        """연결 풀에서 연결 가져오기"""
        if self.active_connections >= self.max_connections:
            await self._cleanup_connections()
        
        if service_name not in self.connection_pools:
            self.connection_pools[service_name] = []
        
        pool = self.connection_pools[service_name]
        if pool:
            self.active_connections += 1
            return pool.pop()
        
        # 새 연결 생성 (구현 필요)
        return None
    
    async def _cleanup_connections(self):
        """유휴 연결 정리"""
        cleaned = 0
        for service_name, pool in self.connection_pools.items():
            # 오래된 연결 제거 (구현 필요)
            while pool and cleaned < 10:
                pool.pop()
                cleaned += 1
                self.active_connections -= 1
        
        print(f"Cleaned up {cleaned} idle connections")

# 전역 성능 최적화 인스턴스
global_optimizer = PerformanceOptimizer()
global_resource_manager = ResourceManager()

def start_performance_monitoring(interval: float = 5.0):
    """백그라운드 성능 모니터링 시작"""
    async def monitor_loop():
        while True:
            global_optimizer.collect_metrics()
            await asyncio.sleep(interval)
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(monitor_loop())
        print(f"Performance monitoring started (interval: {interval}s)")
    except RuntimeError:
        print("No running event loop. Performance monitoring not started.")

if __name__ == "__main__":
    # 테스트
    optimizer = PerformanceOptimizer()
    
    # 성능 지표 수집
    metrics = optimizer.collect_metrics()
    print(f"Current metrics: CPU {metrics.cpu_percent}%, Memory {metrics.memory_percent}%")
    
    # 성능 보고서
    time.sleep(1)
    optimizer.collect_metrics()
    optimizer.print_performance_report()