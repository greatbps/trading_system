#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/async_processing/async_engine.py

고급 비동기 처리 엔진 - Phase 7 Async Processing Enhancement
"""

import asyncio
import threading
import time
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Coroutine, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
import functools
import traceback
import gc
from enum import Enum

from utils.logger import get_logger


class TaskPriority(Enum):
    """작업 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """비동기 작업 정의"""
    task_id: str
    name: str
    coro_func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    callback: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AsyncTaskGroup:
    """비동기 작업 그룹"""
    group_id: str
    name: str
    tasks: List[AsyncTask] = field(default_factory=list)
    execution_mode: str = "parallel"  # parallel, sequential, pipeline
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: Optional[float] = None
    callback: Optional[Callable] = None


@dataclass
class WorkerStats:
    """워커 통계"""
    worker_id: str
    tasks_processed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    current_task: Optional[str] = None
    last_active: datetime = field(default_factory=datetime.now)


class AsyncTaskQueue:
    """우선순위 기반 비동기 작업 큐"""
    
    def __init__(self):
        self.queues = {
            TaskPriority.CRITICAL: deque(),
            TaskPriority.HIGH: deque(), 
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque()
        }
        self.lock = asyncio.Lock()
        self.not_empty = asyncio.Condition(self.lock)
    
    async def put(self, task: AsyncTask):
        """작업 추가"""
        async with self.not_empty:
            self.queues[task.priority].append(task)
            self.not_empty.notify()
    
    async def get(self) -> Optional[AsyncTask]:
        """우선순위에 따라 작업 가져오기"""
        async with self.not_empty:
            # 우선순위 순서로 확인
            for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, 
                           TaskPriority.NORMAL, TaskPriority.LOW]:
                queue = self.queues[priority]
                if queue:
                    return queue.popleft()
            
            # 큐가 비어있으면 대기
            await self.not_empty.wait()
            return await self.get()
    
    async def size(self) -> int:
        """총 큐 크기"""
        async with self.lock:
            return sum(len(queue) for queue in self.queues.values())
    
    async def clear(self):
        """모든 큐 비우기"""
        async with self.lock:
            for queue in self.queues.values():
                queue.clear()


class AsyncEngine:
    """고급 비동기 처리 엔진"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("AsyncEngine")
        
        # 엔진 설정
        self.max_workers = 8
        self.task_timeout = 300  # 5분
        self.heartbeat_interval = 30  # 30초
        self.cleanup_interval = 600  # 10분
        
        # 비동기 구성 요소
        self.task_queue = AsyncTaskQueue()
        self.active_tasks = {}  # task_id -> asyncio.Task
        self.completed_tasks = {}  # task_id -> AsyncTask
        self.task_groups = {}  # group_id -> AsyncTaskGroup
        
        # 워커 관리
        self.workers = {}  # worker_id -> WorkerStats
        self.worker_tasks = {}  # worker_id -> asyncio.Task
        
        # 모니터링
        self.task_history = deque(maxlen=1000)
        self.performance_stats = defaultdict(float)
        self.error_stats = defaultdict(int)
        
        # 실행 상태
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # 콜백 관리
        self.task_callbacks = {}
        self.global_callbacks = {
            'on_task_start': [],
            'on_task_complete': [],
            'on_task_error': [],
            'on_worker_error': []
        }
        
        # 의존성 그래프
        self.dependency_graph = defaultdict(set)  # task_id -> dependent_tasks
        self.reverse_dependencies = defaultdict(set)  # task_id -> dependency_tasks
        
        # 메모리 관리
        self.weak_refs = set()
        
        self.logger.info("✅ 고급 비동기 처리 엔진 초기화 완료")
    
    async def start(self):
        """엔진 시작"""
        if self.is_running:
            self.logger.warning("비동기 엔진이 이미 실행 중입니다")
            return
        
        self.is_running = True
        self.shutdown_event.clear()
        
        # 워커 시작
        for i in range(self.max_workers):
            worker_id = f"worker_{i}"
            worker_stats = WorkerStats(worker_id)
            self.workers[worker_id] = worker_stats
            
            # 워커 태스크 생성
            worker_task = asyncio.create_task(
                self._worker_loop(worker_id),
                name=f"AsyncWorker_{worker_id}"
            )
            self.worker_tasks[worker_id] = worker_task
        
        # 관리 태스크들 시작
        asyncio.create_task(self._heartbeat_loop(), name="AsyncHeartbeat")
        asyncio.create_task(self._cleanup_loop(), name="AsyncCleanup")
        asyncio.create_task(self._dependency_resolver_loop(), name="DependencyResolver")
        
        self.logger.info(f"🚀 비동기 엔진 시작 (워커 {self.max_workers}개)")
    
    async def stop(self):
        """엔진 중지"""
        if not self.is_running:
            return
        
        self.logger.info("⏹️ 비동기 엔진 중지 중...")
        
        self.is_running = False
        self.shutdown_event.set()
        
        # 활성 작업들 대기
        if self.active_tasks:
            self.logger.info(f"활성 작업 {len(self.active_tasks)}개 완료 대기...")
            active_tasks = list(self.active_tasks.values())
            await asyncio.gather(*active_tasks, return_exceptions=True)
        
        # 워커들 중지
        for worker_id, worker_task in self.worker_tasks.items():
            if not worker_task.done():
                worker_task.cancel()
        
        # 워커들 완료 대기
        worker_tasks = list(self.worker_tasks.values())
        if worker_tasks:
            await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        # 큐 정리
        await self.task_queue.clear()
        
        self.logger.info("✅ 비동기 엔진 중지 완료")
    
    async def submit_task(self, 
                         coro_func: Callable, 
                         *args,
                         name: Optional[str] = None,
                         priority: TaskPriority = TaskPriority.NORMAL,
                         timeout: Optional[float] = None,
                         max_retries: int = 3,
                         callback: Optional[Callable] = None,
                         dependencies: Optional[List[str]] = None,
                         **kwargs) -> str:
        """작업 제출"""
        task_id = f"{name or coro_func.__name__}_{int(time.time() * 1000000)}"
        
        task = AsyncTask(
            task_id=task_id,
            name=name or coro_func.__name__,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout_seconds=timeout or self.task_timeout,
            max_retries=max_retries,
            callback=callback,
            dependencies=dependencies or []
        )
        
        # 의존성 그래프 업데이트
        if task.dependencies:
            for dep_task_id in task.dependencies:
                self.dependency_graph[dep_task_id].add(task_id)
                self.reverse_dependencies[task_id].add(dep_task_id)
        
        await self.task_queue.put(task)
        
        self.logger.debug(f"작업 제출: {task_id} (우선순위: {priority.name})")
        return task_id
    
    async def submit_task_group(self, 
                               group: AsyncTaskGroup) -> str:
        """작업 그룹 제출"""
        self.task_groups[group.group_id] = group
        
        if group.execution_mode == "parallel":
            # 병렬 실행 - 모든 작업을 동시에 큐에 추가
            for task in group.tasks:
                await self.task_queue.put(task)
        elif group.execution_mode == "sequential":
            # 순차 실행 - 의존성 설정
            for i in range(len(group.tasks) - 1):
                current_task = group.tasks[i]
                next_task = group.tasks[i + 1]
                next_task.dependencies.append(current_task.task_id)
                self.dependency_graph[current_task.task_id].add(next_task.task_id)
                self.reverse_dependencies[next_task.task_id].add(current_task.task_id)
            
            # 첫 번째 작업만 큐에 추가
            if group.tasks:
                await self.task_queue.put(group.tasks[0])
        elif group.execution_mode == "pipeline":
            # 파이프라인 실행 - 이전 작업 결과를 다음 작업의 입력으로 사용
            await self._setup_pipeline(group)
        
        self.logger.info(f"작업 그룹 제출: {group.group_id} ({group.execution_mode}, {len(group.tasks)}개 작업)")
        return group.group_id
    
    async def _worker_loop(self, worker_id: str):
        """워커 메인 루프"""
        worker = self.workers[worker_id]
        
        while self.is_running:
            try:
                # 작업 가져오기
                task = await self.task_queue.get()
                if not task:
                    continue
                
                # 의존성 확인
                if not await self._check_dependencies(task):
                    # 의존성이 충족되지 않으면 다시 큐에 추가
                    await asyncio.sleep(0.1)  # 짧은 대기
                    await self.task_queue.put(task)
                    continue
                
                # 작업 실행
                await self._execute_task(task, worker_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 워커 {worker_id} 에러: {e}")
                self.error_stats['worker_errors'] += 1
                
                # 에러 콜백 실행
                for callback in self.global_callbacks['on_worker_error']:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(worker_id, e)
                        else:
                            callback(worker_id, e)
                    except Exception as cb_error:
                        self.logger.error(f"워커 에러 콜백 실패: {cb_error}")
        
        self.logger.debug(f"워커 {worker_id} 종료")
    
    async def _execute_task(self, task: AsyncTask, worker_id: str):
        """작업 실행"""
        worker = self.workers[worker_id]
        start_time = time.time()
        
        try:
            # 작업 시작
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            worker.current_task = task.task_id
            worker.last_active = datetime.now()
            
            self.active_tasks[task.task_id] = task
            
            # 시작 콜백 실행
            await self._execute_callbacks('on_task_start', task)
            
            # 작업 실행 (타임아웃 적용)
            if asyncio.iscoroutinefunction(task.coro_func):
                coro = task.coro_func(*task.args, **task.kwargs)
            else:
                # 일반 함수를 코루틴으로 래핑
                coro = self._wrap_sync_function(task.coro_func, *task.args, **task.kwargs)
            
            if task.timeout_seconds:
                task.result = await asyncio.wait_for(coro, timeout=task.timeout_seconds)
            else:
                task.result = await coro
            
            # 성공 처리
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            execution_time = time.time() - start_time
            worker.tasks_processed += 1
            worker.total_processing_time += execution_time
            worker.avg_processing_time = worker.total_processing_time / worker.tasks_processed
            
            self.performance_stats['total_tasks'] += 1
            self.performance_stats['total_execution_time'] += execution_time
            
            # 완료 콜백 실행
            await self._execute_callbacks('on_task_complete', task)
            
            self.logger.debug(f"작업 완료: {task.task_id} ({execution_time:.2f}초)")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = TimeoutError(f"작업 타임아웃 ({task.timeout_seconds}초)")
            await self._handle_task_failure(task, worker)
            
        except Exception as e:
            task.status = TaskStatus.FAILED 
            task.error = e
            await self._handle_task_failure(task, worker)
            
        finally:
            # 정리
            task.completed_at = datetime.now()
            worker.current_task = None
            
            # 활성 작업에서 제거, 완료 작업에 추가
            self.active_tasks.pop(task.task_id, None)
            self.completed_tasks[task.task_id] = task
            self.task_history.append(task)
            
            # 의존성 해결
            await self._resolve_dependencies(task.task_id)
    
    async def _handle_task_failure(self, task: AsyncTask, worker: WorkerStats):
        """작업 실패 처리"""
        worker.tasks_failed += 1
        self.error_stats['task_failures'] += 1
        
        # 재시도 확인
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            
            # 지연 후 재시도
            await asyncio.sleep(task.retry_delay * task.retry_count)
            await self.task_queue.put(task)
            
            self.logger.warning(f"작업 재시도 {task.retry_count}/{task.max_retries}: {task.task_id}")
        else:
            # 최대 재시도 횟수 초과
            self.logger.error(f"❌ 작업 실패 (최대 재시도 초과): {task.task_id}")
            self.logger.error(f"에러: {task.error}")
            
            # 에러 콜백 실행
            await self._execute_callbacks('on_task_error', task)
    
    async def _check_dependencies(self, task: AsyncTask) -> bool:
        """의존성 확인"""
        if not task.dependencies:
            return True
        
        for dep_task_id in task.dependencies:
            dep_task = self.completed_tasks.get(dep_task_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    async def _resolve_dependencies(self, completed_task_id: str):
        """완료된 작업의 의존성 해결"""
        dependent_tasks = self.dependency_graph.get(completed_task_id, set())
        
        for dep_task_id in dependent_tasks:
            # 해당 작업의 모든 의존성이 완료되었는지 확인
            dep_task = None
            
            # 큐에서 작업 찾기 (비효율적이지만 간단한 구현)
            # 실제 환경에서는 별도 인덱스 구조 사용 권장
            await asyncio.sleep(0)  # 다른 작업들에게 실행 기회 제공
    
    async def _setup_pipeline(self, group: AsyncTaskGroup):
        """파이프라인 설정"""
        # 파이프라인은 순차 실행과 유사하지만 결과 전달 방식이 다름
        # 현재는 간단한 순차 실행으로 구현
        for i in range(len(group.tasks) - 1):
            current_task = group.tasks[i]
            next_task = group.tasks[i + 1]
            next_task.dependencies.append(current_task.task_id)
        
        if group.tasks:
            await self.task_queue.put(group.tasks[0])
    
    async def _wrap_sync_function(self, func, *args, **kwargs):
        """동기 함수를 비동기로 래핑"""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, func, *args, **kwargs)
    
    async def _execute_callbacks(self, callback_type: str, task: AsyncTask):
        """콜백 실행"""
        # 글로벌 콜백
        for callback in self.global_callbacks.get(callback_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                self.logger.error(f"콜백 실행 실패: {e}")
        
        # 작업별 콜백
        if task.callback:
            try:
                if asyncio.iscoroutinefunction(task.callback):
                    await task.callback(task)
                else:
                    task.callback(task)
            except Exception as e:
                self.logger.error(f"작업 콜백 실행 실패: {e}")
    
    async def _heartbeat_loop(self):
        """하트비트 루프"""
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if not self.is_running:
                    break
                
                # 워커 상태 확인
                now = datetime.now()
                for worker_id, worker in self.workers.items():
                    if worker.current_task:
                        idle_time = (now - worker.last_active).total_seconds()
                        if idle_time > self.heartbeat_interval * 2:
                            self.logger.warning(f"워커 {worker_id} 응답 없음 ({idle_time:.1f}초)")
                
                # 통계 로깅
                queue_size = await self.task_queue.size()
                active_tasks = len(self.active_tasks)
                completed_tasks = len(self.completed_tasks)
                
                self.logger.info(f"📊 비동기 엔진 상태 - 큐: {queue_size}, 활성: {active_tasks}, 완료: {completed_tasks}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"하트비트 에러: {e}")
    
    async def _cleanup_loop(self):
        """정리 루프"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.is_running:
                    break
                
                # 오래된 완료 작업 정리
                cutoff_time = datetime.now() - timedelta(hours=1)
                old_tasks = [
                    task_id for task_id, task in self.completed_tasks.items()
                    if task.completed_at and task.completed_at < cutoff_time
                ]
                
                for task_id in old_tasks:
                    del self.completed_tasks[task_id]
                
                # 가비지 컬렉션
                collected = gc.collect()
                
                if old_tasks or collected:
                    self.logger.info(f"🧹 정리 완료: 작업 {len(old_tasks)}개, GC {collected}개 객체")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"정리 루프 에러: {e}")
    
    async def _dependency_resolver_loop(self):
        """의존성 해결 루프"""
        while self.is_running:
            try:
                await asyncio.sleep(1)  # 1초마다 확인
                
                if not self.is_running:
                    break
                
                # 의존성이 해결된 작업들을 큐에 추가
                # 실제 구현에서는 더 효율적인 방법 사용 권장
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"의존성 해결 루프 에러: {e}")
    
    # === 외부 API 메서드들 ===
    
    def add_global_callback(self, callback_type: str, callback: Callable):
        """글로벌 콜백 추가"""
        if callback_type in self.global_callbacks:
            self.global_callbacks[callback_type].append(callback)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """작업 상태 조회"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].status
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id].status
        return None
    
    async def get_task_result(self, task_id: str, timeout: Optional[float] = None):
        """작업 결과 조회 (대기)"""
        start_time = time.time()
        
        while True:
            if task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    return task.result
                elif task.status == TaskStatus.FAILED:
                    raise task.error
                elif task.status == TaskStatus.CANCELLED:
                    raise asyncio.CancelledError("작업이 취소되었습니다")
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"작업 결과 대기 타임아웃: {task_id}")
            
            await asyncio.sleep(0.1)
    
    async def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            
            # asyncio.Task 취소 시도
            if hasattr(task, '_asyncio_task') and task._asyncio_task:
                task._asyncio_task.cancel()
            
            return True
        
        return False
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """엔진 통계 정보"""
        return {
            'is_running': self.is_running,
            'max_workers': self.max_workers,
            'active_workers': len([w for w in self.workers.values() if w.current_task]),
            'queue_size': len(self.task_queue.queues),  # 근사치
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'performance_stats': dict(self.performance_stats),
            'error_stats': dict(self.error_stats),
            'worker_stats': {
                worker_id: {
                    'tasks_processed': worker.tasks_processed,
                    'tasks_failed': worker.tasks_failed,
                    'avg_processing_time': worker.avg_processing_time,
                    'current_task': worker.current_task,
                    'last_active': worker.last_active
                }
                for worker_id, worker in self.workers.items()
            }
        }