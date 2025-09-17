#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/async_processing/task_scheduler.py

고급 작업 스케줄러 - Phase 7 Async Processing Enhancement
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import croniter
import threading

from utils.logger import get_logger
from async_processing.async_engine import AsyncEngine, TaskPriority


class ScheduleType(Enum):
    """스케줄 타입"""
    ONCE = "once"           # 한 번만 실행
    INTERVAL = "interval"   # 일정 간격으로 반복
    CRON = "cron"          # CRON 표현식
    DELAY = "delay"        # 지연 후 실행


@dataclass
class ScheduledTask:
    """스케줄된 작업"""
    schedule_id: str
    name: str
    coro_func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    schedule_type: ScheduleType = ScheduleType.ONCE
    
    # 스케줄링 옵션
    execute_at: Optional[datetime] = None      # 특정 시간 실행
    interval_seconds: Optional[float] = None    # 간격 (초)
    cron_expression: Optional[str] = None       # CRON 표현식
    delay_seconds: Optional[float] = None       # 지연 시간 (초)
    
    # 실행 제어
    max_executions: Optional[int] = None        # 최대 실행 횟수
    timeout_seconds: Optional[float] = None     # 작업 타임아웃
    priority: TaskPriority = TaskPriority.NORMAL
    
    # 상태 관리
    is_active: bool = True
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    
    # 에러 처리
    max_retries: int = 3
    retry_delay: float = 60.0  # 1분
    
    # 콜백
    on_success: Optional[Callable] = None
    on_error: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    
    created_at: datetime = field(default_factory=datetime.now)


class TaskScheduler:
    """고급 작업 스케줄러"""
    
    def __init__(self, async_engine: AsyncEngine):
        self.async_engine = async_engine
        self.logger = get_logger("TaskScheduler")
        
        # 스케줄된 작업 관리
        self.scheduled_tasks = {}  # schedule_id -> ScheduledTask
        self.execution_queue = []  # (next_execution, schedule_id)
        
        # 스케줄러 상태
        self.is_running = False
        self.scheduler_task = None
        
        # 통계 및 모니터링
        self.execution_stats = defaultdict(int)
        self.error_stats = defaultdict(int)
        self.execution_history = deque(maxlen=1000)
        
        # 스레드 안전성
        self.lock = threading.Lock()
        
        self.logger.info("✅ 작업 스케줄러 초기화 완료")
    
    async def start(self):
        """스케줄러 시작"""
        if self.is_running:
            self.logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(
            self._scheduler_loop(), 
            name="TaskScheduler"
        )
        
        self.logger.info("🕐 작업 스케줄러 시작")
    
    async def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("⏹️ 작업 스케줄러 중지")
    
    def schedule_once(self, 
                     coro_func: Callable,
                     execute_at: datetime,
                     *args,
                     name: Optional[str] = None,
                     priority: TaskPriority = TaskPriority.NORMAL,
                     timeout: Optional[float] = None,
                     **kwargs) -> str:
        """일회성 작업 스케줄링"""
        schedule_id = f"once_{int(time.time() * 1000000)}"
        
        task = ScheduledTask(
            schedule_id=schedule_id,
            name=name or coro_func.__name__,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
            schedule_type=ScheduleType.ONCE,
            execute_at=execute_at,
            priority=priority,
            timeout_seconds=timeout,
            max_executions=1,
            next_execution=execute_at
        )
        
        self._add_scheduled_task(task)
        
        self.logger.info(f"일회성 작업 스케줄: {schedule_id} at {execute_at}")
        return schedule_id
    
    def schedule_interval(self,
                         coro_func: Callable,
                         interval_seconds: float,
                         *args,
                         name: Optional[str] = None,
                         start_at: Optional[datetime] = None,
                         max_executions: Optional[int] = None,
                         priority: TaskPriority = TaskPriority.NORMAL,
                         **kwargs) -> str:
        """간격 기반 작업 스케줄링"""
        schedule_id = f"interval_{int(time.time() * 1000000)}"
        
        start_time = start_at or datetime.now()
        
        task = ScheduledTask(
            schedule_id=schedule_id,
            name=name or coro_func.__name__,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=interval_seconds,
            priority=priority,
            max_executions=max_executions,
            next_execution=start_time
        )
        
        self._add_scheduled_task(task)
        
        self.logger.info(f"간격 작업 스케줄: {schedule_id} every {interval_seconds}s")
        return schedule_id
    
    def schedule_cron(self,
                     coro_func: Callable,
                     cron_expression: str,
                     *args,
                     name: Optional[str] = None,
                     max_executions: Optional[int] = None,
                     priority: TaskPriority = TaskPriority.NORMAL,
                     **kwargs) -> str:
        """CRON 표현식 기반 스케줄링"""
        schedule_id = f"cron_{int(time.time() * 1000000)}"
        
        # CRON 다음 실행 시간 계산
        try:
            cron = croniter.croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
        except Exception as e:
            self.logger.error(f"잘못된 CRON 표현식: {cron_expression}")
            raise ValueError(f"잘못된 CRON 표현식: {e}")
        
        task = ScheduledTask(
            schedule_id=schedule_id,
            name=name or coro_func.__name__,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            priority=priority,
            max_executions=max_executions,
            next_execution=next_run
        )
        
        self._add_scheduled_task(task)
        
        self.logger.info(f"CRON 작업 스케줄: {schedule_id} ({cron_expression})")
        return schedule_id
    
    def schedule_delay(self,
                      coro_func: Callable,
                      delay_seconds: float,
                      *args,
                      name: Optional[str] = None,
                      priority: TaskPriority = TaskPriority.NORMAL,
                      **kwargs) -> str:
        """지연 실행 스케줄링"""
        schedule_id = f"delay_{int(time.time() * 1000000)}"
        
        execute_at = datetime.now() + timedelta(seconds=delay_seconds)
        
        task = ScheduledTask(
            schedule_id=schedule_id,
            name=name or coro_func.__name__,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
            schedule_type=ScheduleType.DELAY,
            delay_seconds=delay_seconds,
            priority=priority,
            max_executions=1,
            next_execution=execute_at
        )
        
        self._add_scheduled_task(task)
        
        self.logger.info(f"지연 작업 스케줄: {schedule_id} after {delay_seconds}s")
        return schedule_id
    
    def _add_scheduled_task(self, task: ScheduledTask):
        """스케줄된 작업 추가"""
        with self.lock:
            self.scheduled_tasks[task.schedule_id] = task
            
            # 실행 큐에 추가 (정렬 유지)
            if task.next_execution:
                self.execution_queue.append((task.next_execution, task.schedule_id))
                self.execution_queue.sort(key=lambda x: x[0])
    
    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 실행할 작업들 확인
                tasks_to_execute = []
                
                with self.lock:
                    while (self.execution_queue and 
                           self.execution_queue[0][0] <= current_time):
                        _, schedule_id = self.execution_queue.pop(0)
                        
                        task = self.scheduled_tasks.get(schedule_id)
                        if task and task.is_active:
                            tasks_to_execute.append(task)
                
                # 작업 실행
                for task in tasks_to_execute:
                    await self._execute_scheduled_task(task)
                
                # 잠시 대기 (CPU 사용률 최적화)
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"스케줄러 루프 에러: {e}")
                await asyncio.sleep(5)  # 에러 발생 시 5초 대기
    
    async def _execute_scheduled_task(self, task: ScheduledTask):
        """스케줄된 작업 실행"""
        try:
            # 실행 전 처리
            task.execution_count += 1
            task.last_execution = datetime.now()
            
            self.execution_stats['total_executions'] += 1
            self.execution_stats[f'{task.name}_executions'] += 1
            
            # 비동기 엔진에 작업 제출
            task_id = await self.async_engine.submit_task(
                task.coro_func,
                *task.args,
                name=f"scheduled_{task.name}",
                priority=task.priority,
                timeout=task.timeout_seconds,
                **task.kwargs
            )
            
            # 결과 대기 (논블로킹)
            asyncio.create_task(self._handle_task_completion(task, task_id))
            
            # 다음 실행 시간 계산 및 스케줄링
            await self._schedule_next_execution(task)
            
        except Exception as e:
            self.logger.error(f"스케줄된 작업 실행 실패: {task.schedule_id}")
            self.error_stats[f'{task.name}_errors'] += 1
            
            if task.on_error:
                try:
                    if asyncio.iscoroutinefunction(task.on_error):
                        await task.on_error(task, e)
                    else:
                        task.on_error(task, e)
                except Exception as cb_error:
                    self.logger.error(f"에러 콜백 실행 실패: {cb_error}")
    
    async def _handle_task_completion(self, scheduled_task: ScheduledTask, task_id: str):
        """작업 완료 처리"""
        try:
            # 작업 결과 대기
            result = await self.async_engine.get_task_result(task_id)
            
            # 성공 콜백 실행
            if scheduled_task.on_success:
                try:
                    if asyncio.iscoroutinefunction(scheduled_task.on_success):
                        await scheduled_task.on_success(scheduled_task, result)
                    else:
                        scheduled_task.on_success(scheduled_task, result)
                except Exception as cb_error:
                    self.logger.error(f"성공 콜백 실행 실패: {cb_error}")
            
            # 실행 이력 저장
            self.execution_history.append({
                'schedule_id': scheduled_task.schedule_id,
                'name': scheduled_task.name,
                'executed_at': scheduled_task.last_execution,
                'success': True,
                'result': str(result)[:100] if result else None
            })
            
        except Exception as e:
            # 실패 처리
            self.error_stats[f'{scheduled_task.name}_task_errors'] += 1
            
            # 실행 이력 저장
            self.execution_history.append({
                'schedule_id': scheduled_task.schedule_id,
                'name': scheduled_task.name,
                'executed_at': scheduled_task.last_execution,
                'success': False,
                'error': str(e)[:100]
            })
            
            self.logger.error(f"스케줄된 작업 실행 실패: {scheduled_task.schedule_id}, 에러: {e}")
    
    async def _schedule_next_execution(self, task: ScheduledTask):
        """다음 실행 스케줄링"""
        # 최대 실행 횟수 확인
        if task.max_executions and task.execution_count >= task.max_executions:
            task.is_active = False
            
            # 완료 콜백 실행
            if task.on_complete:
                try:
                    if asyncio.iscoroutinefunction(task.on_complete):
                        await task.on_complete(task)
                    else:
                        task.on_complete(task)
                except Exception as cb_error:
                    self.logger.error(f"완료 콜백 실행 실패: {cb_error}")
            
            self.logger.info(f"스케줄된 작업 완료: {task.schedule_id}")
            return
        
        # 다음 실행 시간 계산
        next_execution = None
        
        if task.schedule_type == ScheduleType.INTERVAL:
            next_execution = datetime.now() + timedelta(seconds=task.interval_seconds)
        elif task.schedule_type == ScheduleType.CRON:
            try:
                cron = croniter.croniter(task.cron_expression, datetime.now())
                next_execution = cron.get_next(datetime)
            except Exception as e:
                self.logger.error(f"CRON 다음 실행 시간 계산 실패: {e}")
                task.is_active = False
                return
        
        if next_execution:
            task.next_execution = next_execution
            
            # 실행 큐에 추가
            with self.lock:
                self.execution_queue.append((next_execution, task.schedule_id))
                self.execution_queue.sort(key=lambda x: x[0])
    
    def unschedule_task(self, schedule_id: str) -> bool:
        """작업 스케줄 취소"""
        with self.lock:
            if schedule_id in self.scheduled_tasks:
                task = self.scheduled_tasks[schedule_id]
                task.is_active = False
                
                # 실행 큐에서 제거
                self.execution_queue = [
                    (time, sid) for time, sid in self.execution_queue 
                    if sid != schedule_id
                ]
                
                del self.scheduled_tasks[schedule_id]
                
                self.logger.info(f"작업 스케줄 취소: {schedule_id}")
                return True
        
        return False
    
    def get_scheduled_task(self, schedule_id: str) -> Optional[ScheduledTask]:
        """스케줄된 작업 조회"""
        return self.scheduled_tasks.get(schedule_id)
    
    def list_scheduled_tasks(self) -> List[ScheduledTask]:
        """모든 스케줄된 작업 목록"""
        return list(self.scheduled_tasks.values())
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """스케줄러 통계"""
        active_tasks = [t for t in self.scheduled_tasks.values() if t.is_active]
        
        return {
            'is_running': self.is_running,
            'total_scheduled_tasks': len(self.scheduled_tasks),
            'active_tasks': len(active_tasks),
            'pending_executions': len(self.execution_queue),
            'execution_stats': dict(self.execution_stats),
            'error_stats': dict(self.error_stats),
            'next_execution': (
                self.execution_queue[0][0].isoformat() 
                if self.execution_queue else None
            ),
            'recent_executions': list(self.execution_history)[-10:],
            'tasks_by_type': {
                schedule_type.value: len([
                    t for t in active_tasks 
                    if t.schedule_type == schedule_type
                ])
                for schedule_type in ScheduleType
            }
        }
    
    # === 편의 메서드들 ===
    
    def schedule_daily(self, coro_func: Callable, hour: int, minute: int = 0, **kwargs):
        """매일 특정 시간 실행"""
        cron_expr = f"{minute} {hour} * * *"
        return self.schedule_cron(coro_func, cron_expr, **kwargs)
    
    def schedule_hourly(self, coro_func: Callable, minute: int = 0, **kwargs):
        """매시간 특정 분 실행"""
        cron_expr = f"{minute} * * * *"
        return self.schedule_cron(coro_func, cron_expr, **kwargs)
    
    def schedule_weekly(self, coro_func: Callable, day: int, hour: int, minute: int = 0, **kwargs):
        """매주 특정 요일 실행 (0=일요일, 6=토요일)"""
        cron_expr = f"{minute} {hour} * * {day}"
        return self.schedule_cron(coro_func, cron_expr, **kwargs)
    
    def schedule_every_n_minutes(self, coro_func: Callable, minutes: int, **kwargs):
        """N분마다 실행"""
        return self.schedule_interval(coro_func, minutes * 60, **kwargs)
    
    def schedule_every_n_hours(self, coro_func: Callable, hours: int, **kwargs):
        """N시간마다 실행"""
        return self.schedule_interval(coro_func, hours * 3600, **kwargs)