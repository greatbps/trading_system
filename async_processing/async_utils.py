#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/async_processing/async_utils.py

비동기 처리 유틸리티 - Phase 7 Async Processing Enhancement
"""

import asyncio
import functools
import time
import weakref
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from utils.logger import get_logger


class AsyncCache:
    """비동기 캐시"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.lock = asyncio.Lock()
        
    async def get(self, key: str):
        """캐시에서 값 가져오기"""
        async with self.lock:
            if key not in self.cache:
                return None
                
            value, timestamp = self.cache[key]
            
            # TTL 확인
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                return None
                
            self.access_times[key] = time.time()
            return value
    
    async def set(self, key: str, value: Any):
        """캐시에 값 설정"""
        async with self.lock:
            current_time = time.time()
            
            # 용량 확인
            if len(self.cache) >= self.max_size:
                await self._evict_lru()
            
            self.cache[key] = (value, current_time)
            self.access_times[key] = current_time
    
    async def _evict_lru(self):
        """LRU 기반 제거"""
        if not self.access_times:
            return
            
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    async def clear(self):
        """캐시 비우기"""
        async with self.lock:
            self.cache.clear()
            self.access_times.clear()


class AsyncBatch:
    """비동기 배치 처리기"""
    
    def __init__(self, batch_size: int = 10, timeout_seconds: float = 5.0):
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.batch = []
        self.batch_futures = []
        self.lock = asyncio.Lock()
        self.timer_task = None
        
    async def add(self, item: Any) -> Any:
        """배치에 아이템 추가"""
        future = asyncio.Future()
        
        async with self.lock:
            self.batch.append(item)
            self.batch_futures.append(future)
            
            # 타이머 시작 (첫 번째 아이템)
            if len(self.batch) == 1:
                self.timer_task = asyncio.create_task(self._timer())
            
            # 배치 크기 도달 시 처리
            if len(self.batch) >= self.batch_size:
                await self._process_batch()
        
        return await future
    
    async def _timer(self):
        """타이머 - 타임아웃 시 배치 처리"""
        try:
            await asyncio.sleep(self.timeout_seconds)
            async with self.lock:
                if self.batch:
                    await self._process_batch()
        except asyncio.CancelledError:
            pass
    
    async def _process_batch(self):
        """배치 처리 (서브클래스에서 구현)"""
        # 기본 구현: 각 아이템을 그대로 반환
        current_batch = self.batch[:]
        current_futures = self.batch_futures[:]
        
        self.batch.clear()
        self.batch_futures.clear()
        
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None
        
        # 결과 설정
        for item, future in zip(current_batch, current_futures):
            future.set_result(item)


class AsyncRateLimit:
    """비동기 속도 제한기"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """속도 제한 획득"""
        async with self.lock:
            now = time.time()
            
            # 시간 윈도우 밖의 호출 제거
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            # 제한 확인
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.time_window - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            self.calls.append(now)


class AsyncCircuitBreaker:
    """비동기 서킷 브레이커"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: float = 60.0, success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        async with self.lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time < self.timeout_seconds:
                    raise Exception("Circuit breaker is OPEN")
                else:
                    self.state = "HALF_OPEN"
                    self.success_count = 0
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            async with self.lock:
                if self.state == "HALF_OPEN":
                    self.success_count += 1
                    if self.success_count >= self.success_threshold:
                        self.state = "CLOSED"
                        self.failure_count = 0
                elif self.state == "CLOSED":
                    self.failure_count = 0
            
            return result
            
        except Exception as e:
            async with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                elif self.state == "HALF_OPEN":
                    self.state = "OPEN"
            
            raise e


# 데코레이터들

def async_cache(ttl_seconds: int = 300, max_size: int = 1000):
    """비동기 캐시 데코레이터"""
    cache = AsyncCache(max_size=max_size, ttl_seconds=ttl_seconds)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key = f"{func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
            
            # 캐시에서 확인
            cached_result = await cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # 함수 실행
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 캐시에 저장
            await cache.set(key, result)
            return result
        
        return wrapper
    return decorator


def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """비동기 재시도 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception
            
            raise last_exception
        
        return wrapper
    return decorator


def async_timeout(timeout_seconds: float):
    """비동기 타임아웃 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            else:
                # 동기 함수를 비동기로 실행
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, func, *args, **kwargs),
                    timeout=timeout_seconds
                )
        
        return wrapper
    return decorator


def async_rate_limit(max_calls: int, time_window: float):
    """비동기 속도 제한 데코레이터"""
    rate_limiter = AsyncRateLimit(max_calls, time_window)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            await rate_limiter.acquire()
            
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def async_circuit_breaker(failure_threshold: int = 5, timeout_seconds: float = 60.0):
    """비동기 서킷 브레이커 데코레이터"""
    circuit_breaker = AsyncCircuitBreaker(failure_threshold, timeout_seconds)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


class AsyncTaskGroup:
    """비동기 작업 그룹 관리자"""
    
    def __init__(self, max_concurrency: int = 10):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.tasks = []
        self.results = []
        
    async def add_task(self, coro):
        """작업 추가"""
        async def wrapped_task():
            async with self.semaphore:
                return await coro
        
        task = asyncio.create_task(wrapped_task())
        self.tasks.append(task)
        return task
    
    async def wait_all(self, return_exceptions=True):
        """모든 작업 완료 대기"""
        if not self.tasks:
            return []
        
        results = await asyncio.gather(*self.tasks, return_exceptions=return_exceptions)
        self.results = results
        return results
    
    async def wait_any(self):
        """임의 작업 완료 대기"""
        if not self.tasks:
            return None, None
        
        done, pending = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # 완료된 작업 결과 반환
        for task in done:
            try:
                result = task.result()
                return task, result
            except Exception as e:
                return task, e
        
        return None, None
    
    def cancel_all(self):
        """모든 작업 취소"""
        for task in self.tasks:
            if not task.done():
                task.cancel()


class AsyncWorkerPool:
    """비동기 워커 풀"""
    
    def __init__(self, worker_count: int = 5):
        self.worker_count = worker_count
        self.queue = asyncio.Queue()
        self.workers = []
        self.results = {}
        self.running = False
        
    async def start(self):
        """워커 풀 시작"""
        self.running = True
        
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(f"worker_{i}"))
            self.workers.append(worker)
    
    async def stop(self):
        """워커 풀 중지"""
        self.running = False
        
        # 워커들에게 중지 신호
        for _ in self.workers:
            await self.queue.put(None)
        
        # 워커 완료 대기
        await asyncio.gather(*self.workers, return_exceptions=True)
    
    async def submit(self, coro, task_id: str = None):
        """작업 제출"""
        if not task_id:
            task_id = f"task_{int(time.time() * 1000000)}"
        
        await self.queue.put((task_id, coro))
        return task_id
    
    async def get_result(self, task_id: str, timeout: float = None):
        """결과 대기"""
        start_time = time.time()
        
        while task_id not in self.results:
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Task {task_id} timeout")
            
            await asyncio.sleep(0.1)
        
        return self.results.pop(task_id)
    
    async def _worker(self, worker_id: str):
        """워커 함수"""
        logger = get_logger(f"AsyncWorker.{worker_id}")
        
        while self.running:
            try:
                item = await self.queue.get()
                
                if item is None:  # 중지 신호
                    break
                
                task_id, coro = item
                
                try:
                    result = await coro
                    self.results[task_id] = result
                except Exception as e:
                    self.results[task_id] = e
                    logger.error(f"Task {task_id} failed: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")


# 편의 함수들

async def run_with_timeout(coro, timeout_seconds: float):
    """타임아웃과 함께 코루틴 실행"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"Operation timed out after {timeout_seconds} seconds")


async def run_in_parallel(tasks: List, max_concurrency: int = 10, return_exceptions: bool = True):
    """병렬로 작업 실행"""
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def bounded_task(task):
        async with semaphore:
            if asyncio.iscoroutine(task):
                return await task
            elif callable(task):
                return await task() if asyncio.iscoroutinefunction(task) else task()
            else:
                return task
    
    bounded_tasks = [bounded_task(task) for task in tasks]
    return await asyncio.gather(*bounded_tasks, return_exceptions=return_exceptions)


async def batch_process(items: List, processor_func: Callable, batch_size: int = 10, max_concurrency: int = 5):
    """배치 처리"""
    results = []
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def process_batch(batch):
        async with semaphore:
            if asyncio.iscoroutinefunction(processor_func):
                return await processor_func(batch)
            else:
                return processor_func(batch)
    
    # 배치 생성
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    # 병렬 처리
    batch_results = await asyncio.gather(
        *[process_batch(batch) for batch in batches],
        return_exceptions=True
    )
    
    # 결과 병합
    for batch_result in batch_results:
        if isinstance(batch_result, Exception):
            raise batch_result
        results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
    
    return results