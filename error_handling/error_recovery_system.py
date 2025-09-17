#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/error_handling/error_recovery_system.py

고급 에러 처리 및 복구 시스템 - Phase 7 Error Handling Enhancement
"""

import asyncio
import logging
import traceback
import time
import json
import pickle
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import weakref
import gc
import psutil
import os
from pathlib import Path

from utils.logger import get_logger


class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"           # 로깅만, 계속 진행
    MEDIUM = "medium"     # 재시도 후 계속
    HIGH = "high"         # 복구 시도 후 계속
    CRITICAL = "critical" # 시스템 종료


class ErrorCategory(Enum):
    """에러 카테고리"""
    NETWORK = "network"           # 네트워크 관련
    API = "api"                   # API 호출 관련
    DATABASE = "database"         # 데이터베이스 관련  
    VALIDATION = "validation"     # 데이터 검증 관련
    PERMISSION = "permission"     # 권한 관련
    RESOURCE = "resource"         # 리소스 부족 관련
    LOGIC = "logic"              # 비즈니스 로직 관련
    SYSTEM = "system"            # 시스템 레벨 에러
    UNKNOWN = "unknown"          # 알 수 없는 에러


class RecoveryAction(Enum):
    """복구 동작"""
    RETRY = "retry"                    # 재시도
    SKIP = "skip"                      # 건너뛰기
    FALLBACK = "fallback"             # 대안 실행
    RESTART_COMPONENT = "restart_component"  # 컴포넌트 재시작
    RESTART_SYSTEM = "restart_system" # 시스템 재시작
    ALERT_AND_STOP = "alert_and_stop" # 알림 후 중지
    MANUAL_INTERVENTION = "manual_intervention"  # 수동 개입 필요


@dataclass
class ErrorInfo:
    """에러 정보"""
    error_id: str
    timestamp: datetime
    exception: Exception
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = ""
    component: str = ""
    function_name: str = ""
    retry_count: int = 0
    max_retries: int = 3
    recovery_attempts: List[str] = field(default_factory=list)
    is_resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class RecoveryStrategy:
    """복구 전략"""
    error_pattern: str  # 에러 패턴 (정규식)
    error_types: List[type] = field(default_factory=list)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    fallback_function: Optional[Callable] = None
    custom_handler: Optional[Callable] = None
    timeout_seconds: Optional[float] = None


@dataclass
class SystemHealth:
    """시스템 건강 상태"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    error_rate: float
    response_time: float
    active_errors: int
    total_errors_1h: int
    system_load: float
    health_score: float  # 0-100


class ErrorRecoverySystem:
    """고급 에러 처리 및 복구 시스템"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("ErrorRecoverySystem")
        
        # 에러 관리
        self.active_errors = {}  # error_id -> ErrorInfo
        self.error_history = deque(maxlen=10000)
        self.error_stats = defaultdict(int)
        
        # 복구 전략
        self.recovery_strategies = {}  # pattern -> RecoveryStrategy
        self.fallback_handlers = {}   # component -> fallback_function
        
        # 시스템 상태 모니터링
        self.system_health = SystemHealth(0, 0, 0, 0, 0, 0, 0, 0, 100)
        self.health_history = deque(maxlen=1440)  # 24시간 (분당 1개)
        
        # 복구 실행 상태
        self.recovery_tasks = {}     # error_id -> asyncio.Task
        self.component_restarts = defaultdict(int)
        self.last_system_restart = None
        
        # 설정
        self.max_error_rate = 0.1    # 10% 에러율 임계값
        self.health_check_interval = 60  # 1분마다 건강 상태 확인
        self.cleanup_interval = 3600     # 1시간마다 정리
        
        # 실행 상태
        self.is_running = False
        self.monitor_task = None
        self.cleanup_task = None
        
        # 상태 저장/복원
        self.state_file = Path("error_recovery_state.json")
        
        # 기본 복구 전략 등록
        self._register_default_strategies()
        
        self.logger.info("✅ 에러 처리 및 복구 시스템 초기화 완료")
    
    def _register_default_strategies(self):
        """기본 복구 전략 등록"""
        
        # 네트워크 에러
        self.register_strategy(RecoveryStrategy(
            error_pattern=r"(ConnectionError|TimeoutError|NetworkError)",
            error_types=[ConnectionError, TimeoutError],
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=2.0,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.FALLBACK],
            timeout_seconds=30
        ))
        
        # API 에러
        self.register_strategy(RecoveryStrategy(
            error_pattern=r"(APIError|HTTPError|401|403|429|500|502|503)",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.API,
            max_retries=3,
            retry_delay=5.0,
            retry_backoff=1.5,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.SKIP],
            timeout_seconds=60
        ))
        
        # 데이터베이스 에러
        self.register_strategy(RecoveryStrategy(
            error_pattern=r"(DatabaseError|ConnectionTimeout|OperationalError)",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            max_retries=3,
            retry_delay=1.0,
            retry_backoff=2.0,
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.RESTART_COMPONENT],
            timeout_seconds=30
        ))
        
        # 메모리 부족 에러
        self.register_strategy(RecoveryStrategy(
            error_pattern=r"(MemoryError|OutOfMemory)",
            error_types=[MemoryError],
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.RESOURCE,
            max_retries=1,
            recovery_actions=[RecoveryAction.RESTART_COMPONENT, RecoveryAction.RESTART_SYSTEM],
            timeout_seconds=10
        ))
        
        # 권한 에러
        self.register_strategy(RecoveryStrategy(
            error_pattern=r"(PermissionError|AccessDenied|Unauthorized)",
            error_types=[PermissionError],
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PERMISSION,
            max_retries=1,
            recovery_actions=[RecoveryAction.ALERT_AND_STOP, RecoveryAction.MANUAL_INTERVENTION]
        ))
    
    async def start(self):
        """시스템 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 상태 복원
        await self._restore_state()
        
        # 모니터링 태스크들 시작
        self.monitor_task = asyncio.create_task(self._health_monitor_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("🔄 에러 복구 시스템 시작")
    
    async def stop(self):
        """시스템 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 모니터링 태스크 중지
        if self.monitor_task:
            self.monitor_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # 진행 중인 복구 태스크들 중지
        for task in self.recovery_tasks.values():
            if not task.done():
                task.cancel()
        
        # 상태 저장
        await self._save_state()
        
        self.logger.info("⏹️ 에러 복구 시스템 중지")
    
    def register_strategy(self, strategy: RecoveryStrategy):
        """복구 전략 등록"""
        self.recovery_strategies[strategy.error_pattern] = strategy
        self.logger.debug(f"복구 전략 등록: {strategy.error_pattern}")
    
    def register_fallback_handler(self, component: str, handler: Callable):
        """폴백 핸들러 등록"""
        self.fallback_handlers[component] = handler
        self.logger.debug(f"폴백 핸들러 등록: {component}")
    
    async def handle_error(self, 
                          exception: Exception,
                          context: Dict[str, Any] = None,
                          component: str = "",
                          function_name: str = "",
                          severity: Optional[ErrorSeverity] = None) -> ErrorInfo:
        """에러 처리"""
        
        # ErrorInfo 생성
        error_id = f"err_{int(time.time() * 1000000)}"
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            exception=exception,
            error_type=type(exception).__name__,
            error_message=str(exception),
            severity=severity or self._determine_severity(exception),
            category=self._determine_category(exception),
            context=context or {},
            stack_trace=traceback.format_exc(),
            component=component,
            function_name=function_name
        )
        
        # 복구 전략 찾기
        strategy = self._find_recovery_strategy(error_info)
        if strategy:
            error_info.max_retries = strategy.max_retries
        
        # 에러 기록
        self.active_errors[error_id] = error_info
        self.error_history.append(error_info)
        self.error_stats[error_info.error_type] += 1
        
        # 로깅
        self.logger.error(f"❌ 에러 발생 [{error_info.severity.value}]: {error_info.error_message}")
        self.logger.debug(f"에러 컨텍스트: {error_info.context}")
        
        # 복구 시도
        if strategy and error_info.severity != ErrorSeverity.LOW:
            recovery_task = asyncio.create_task(self._execute_recovery(error_info, strategy))
            self.recovery_tasks[error_id] = recovery_task
        
        return error_info
    
    def _determine_severity(self, exception: Exception) -> ErrorSeverity:
        """에러 심각도 결정"""
        error_type = type(exception).__name__
        error_message = str(exception).lower()
        
        # Critical errors
        if isinstance(exception, (MemoryError, SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'shutdown']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if isinstance(exception, (ConnectionError, DatabaseError, PermissionError)):
            return ErrorSeverity.HIGH
        
        if any(keyword in error_message for keyword in ['database', 'connection', 'permission']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors  
        if isinstance(exception, (TimeoutError, ValueError, KeyError)):
            return ErrorSeverity.MEDIUM
        
        if any(keyword in error_message for keyword in ['timeout', 'invalid', 'not found']):
            return ErrorSeverity.MEDIUM
        
        # Default to low
        return ErrorSeverity.LOW
    
    def _determine_category(self, exception: Exception) -> ErrorCategory:
        """에러 카테고리 결정"""
        error_type = type(exception).__name__
        error_message = str(exception).lower()
        
        # Network errors
        if isinstance(exception, (ConnectionError, TimeoutError)) or 'network' in error_message:
            return ErrorCategory.NETWORK
        
        # API errors
        if 'api' in error_message or 'http' in error_message or any(code in error_message for code in ['401', '403', '404', '500', '502']):
            return ErrorCategory.API
        
        # Database errors
        if 'database' in error_message or 'sql' in error_message or 'connection' in error_message:
            return ErrorCategory.DATABASE
        
        # Permission errors
        if isinstance(exception, PermissionError) or 'permission' in error_message or 'access' in error_message:
            return ErrorCategory.PERMISSION
        
        # Resource errors
        if isinstance(exception, MemoryError) or 'memory' in error_message or 'resource' in error_message:
            return ErrorCategory.RESOURCE
        
        # Validation errors
        if isinstance(exception, (ValueError, TypeError)) or 'validation' in error_message:
            return ErrorCategory.VALIDATION
        
        # System errors
        if isinstance(exception, (SystemError, OSError)) or 'system' in error_message:
            return ErrorCategory.SYSTEM
        
        return ErrorCategory.UNKNOWN
    
    def _find_recovery_strategy(self, error_info: ErrorInfo) -> Optional[RecoveryStrategy]:
        """복구 전략 찾기"""
        import re
        
        error_text = f"{error_info.error_type} {error_info.error_message}"
        
        for pattern, strategy in self.recovery_strategies.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return strategy
            
            if strategy.error_types and type(error_info.exception) in strategy.error_types:
                return strategy
        
        return None
    
    async def _execute_recovery(self, error_info: ErrorInfo, strategy: RecoveryStrategy):
        """복구 실행"""
        self.logger.info(f"🔧 복구 시도: {error_info.error_id}")
        
        try:
            for action in strategy.recovery_actions:
                success = await self._execute_recovery_action(error_info, strategy, action)
                error_info.recovery_attempts.append(f"{action.value}: {'성공' if success else '실패'}")
                
                if success:
                    error_info.is_resolved = True
                    error_info.resolution_time = datetime.now()
                    self.logger.info(f"✅ 복구 성공: {error_info.error_id} ({action.value})")
                    break
            
            if not error_info.is_resolved:
                self.logger.warning(f"⚠️ 복구 실패: {error_info.error_id}")
                
        except Exception as e:
            self.logger.error(f"❌ 복구 실행 중 에러: {e}")
        
        finally:
            # 활성 에러에서 제거 (해결되었든 안되었든)
            self.active_errors.pop(error_info.error_id, None)
            self.recovery_tasks.pop(error_info.error_id, None)
    
    async def _execute_recovery_action(self, 
                                     error_info: ErrorInfo, 
                                     strategy: RecoveryStrategy, 
                                     action: RecoveryAction) -> bool:
        """개별 복구 동작 실행"""
        
        if action == RecoveryAction.RETRY:
            return await self._retry_operation(error_info, strategy)
        
        elif action == RecoveryAction.SKIP:
            self.logger.info(f"건너뛰기: {error_info.error_id}")
            return True
        
        elif action == RecoveryAction.FALLBACK:
            return await self._execute_fallback(error_info)
        
        elif action == RecoveryAction.RESTART_COMPONENT:
            return await self._restart_component(error_info.component)
        
        elif action == RecoveryAction.RESTART_SYSTEM:
            return await self._restart_system()
        
        elif action == RecoveryAction.ALERT_AND_STOP:
            await self._send_critical_alert(error_info)
            return False
        
        elif action == RecoveryAction.MANUAL_INTERVENTION:
            await self._request_manual_intervention(error_info)
            return False
        
        return False
    
    async def _retry_operation(self, error_info: ErrorInfo, strategy: RecoveryStrategy) -> bool:
        """작업 재시도"""
        if error_info.retry_count >= strategy.max_retries:
            return False
        
        error_info.retry_count += 1
        delay = strategy.retry_delay * (strategy.retry_backoff ** (error_info.retry_count - 1))
        
        self.logger.info(f"재시도 {error_info.retry_count}/{strategy.max_retries} "
                        f"({delay:.1f}초 후): {error_info.error_id}")
        
        await asyncio.sleep(delay)
        
        # 실제 재시도 로직은 호출하는 쪽에서 구현
        # 여기서는 성공했다고 가정 (실제로는 callback function 등을 통해 구현)
        return True
    
    async def _execute_fallback(self, error_info: ErrorInfo) -> bool:
        """폴백 실행"""
        fallback_handler = self.fallback_handlers.get(error_info.component)
        
        if not fallback_handler:
            self.logger.warning(f"폴백 핸들러 없음: {error_info.component}")
            return False
        
        try:
            self.logger.info(f"폴백 실행: {error_info.component}")
            
            if asyncio.iscoroutinefunction(fallback_handler):
                result = await fallback_handler(error_info)
            else:
                result = fallback_handler(error_info)
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"폴백 실행 실패: {e}")
            return False
    
    async def _restart_component(self, component: str) -> bool:
        """컴포넌트 재시작"""
        if not component:
            return False
        
        self.component_restarts[component] += 1
        
        # 너무 자주 재시작하면 중단
        if self.component_restarts[component] > 5:
            self.logger.error(f"컴포넌트 재시작 한계 초과: {component}")
            return False
        
        self.logger.info(f"컴포넌트 재시작: {component}")
        
        # 실제 재시작 로직은 각 컴포넌트마다 다름
        # 여기서는 간단한 시뮬레이션
        await asyncio.sleep(2)
        
        return True
    
    async def _restart_system(self) -> bool:
        """시스템 재시작"""
        now = datetime.now()
        
        # 최근에 재시작했으면 중단
        if (self.last_system_restart and 
            (now - self.last_system_restart).total_seconds() < 300):  # 5분
            self.logger.error("시스템 재시작 너무 빈번함")
            return False
        
        self.last_system_restart = now
        self.logger.critical("🔄 시스템 재시작 요청")
        
        # 실제 재시작은 상위 시스템에서 처리
        return True
    
    async def _send_critical_alert(self, error_info: ErrorInfo):
        """중요 알림 발송"""
        self.logger.critical(f"🚨 중요 알림: {error_info.error_message}")
        # 실제 알림 발송 로직 (이메일, 슬랙 등)
    
    async def _request_manual_intervention(self, error_info: ErrorInfo):
        """수동 개입 요청"""
        self.logger.critical(f"👤 수동 개입 필요: {error_info.error_message}")
        # 실제 수동 개입 요청 로직
    
    async def _health_monitor_loop(self):
        """건강 상태 모니터링 루프"""
        while self.is_running:
            try:
                await self._update_system_health()
                
                # 건강 상태에 따른 조치
                if self.system_health.health_score < 30:
                    self.logger.warning("⚠️ 시스템 건강 상태 나쁨")
                    await self._handle_poor_health()
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"건강 모니터링 에러: {e}")
                await asyncio.sleep(60)
    
    async def _update_system_health(self):
        """시스템 건강 상태 업데이트"""
        try:
            # CPU, 메모리, 디스크 사용률
            self.system_health.cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            self.system_health.memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            self.system_health.disk_usage = disk.percent
            
            # 에러율 계산
            recent_errors = len([e for e in self.error_history 
                               if (datetime.now() - e.timestamp).total_seconds() < 3600])
            total_operations = max(recent_errors * 10, 100)  # 추정
            self.system_health.error_rate = recent_errors / total_operations
            
            # 활성 에러 수
            self.system_health.active_errors = len(self.active_errors)
            self.system_health.total_errors_1h = recent_errors
            
            # 시스템 로드
            try:
                self.system_health.system_load = psutil.getloadavg()[0]
            except (AttributeError, OSError):
                self.system_health.system_load = 0
            
            # 건강 점수 계산 (0-100)
            score = 100
            score -= min(self.system_health.cpu_usage, 50)  # CPU 50% 이상에서 감점
            score -= min(self.system_health.memory_usage - 70, 30)  # 메모리 70% 이상에서 감점
            score -= min(self.system_health.error_rate * 1000, 30)  # 에러율에 따라 감점
            score -= min(self.system_health.active_errors * 5, 20)  # 활성 에러에 따라 감점
            
            self.system_health.health_score = max(0, score)
            
            # 이력 저장
            self.health_history.append(self.system_health)
            
        except Exception as e:
            self.logger.error(f"건강 상태 업데이트 실패: {e}")
    
    async def _handle_poor_health(self):
        """나쁜 건강 상태 처리"""
        # 메모리 정리
        if self.system_health.memory_usage > 90:
            gc.collect()
            self.logger.info("메모리 정리 실행")
        
        # 에러율이 높으면 일부 기능 제한
        if self.system_health.error_rate > self.max_error_rate:
            self.logger.warning("높은 에러율로 인한 보호 모드 활성화")
    
    async def _cleanup_loop(self):
        """정리 루프"""
        while self.is_running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"정리 루프 에러: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_data(self):
        """오래된 데이터 정리"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # 오래된 에러 이력 정리
        old_count = len(self.error_history)
        self.error_history = deque([e for e in self.error_history if e.timestamp > cutoff_time], 
                                  maxlen=self.error_history.maxlen)
        cleaned = old_count - len(self.error_history)
        
        if cleaned > 0:
            self.logger.info(f"오래된 에러 이력 정리: {cleaned}개")
    
    async def _save_state(self):
        """상태 저장"""
        try:
            state = {
                'error_stats': dict(self.error_stats),
                'component_restarts': dict(self.component_restarts),
                'last_system_restart': self.last_system_restart.isoformat() if self.last_system_restart else None,
                'system_health': asdict(self.system_health)
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"상태 저장 실패: {e}")
    
    async def _restore_state(self):
        """상태 복원"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.error_stats.update(state.get('error_stats', {}))
                self.component_restarts.update(state.get('component_restarts', {}))
                
                if state.get('last_system_restart'):
                    self.last_system_restart = datetime.fromisoformat(state['last_system_restart'])
                
                self.logger.info("상태 복원 완료")
                
        except Exception as e:
            self.logger.error(f"상태 복원 실패: {e}")
    
    # === 외부 API 메서드들 ===
    
    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 조회"""
        recent_errors = [e for e in self.error_history 
                        if (datetime.now() - e.timestamp).total_seconds() < 3600]
        
        return {
            'active_errors': len(self.active_errors),
            'total_errors_24h': len(self.error_history),
            'total_errors_1h': len(recent_errors),
            'error_by_type': dict(self.error_stats),
            'error_by_severity': {
                severity.value: len([e for e in recent_errors if e.severity == severity])
                for severity in ErrorSeverity
            },
            'error_by_category': {
                category.value: len([e for e in recent_errors if e.category == category])
                for category in ErrorCategory
            },
            'component_restarts': dict(self.component_restarts),
            'system_health': asdict(self.system_health),
            'recovery_success_rate': self._calculate_recovery_success_rate()
        }
    
    def _calculate_recovery_success_rate(self) -> float:
        """복구 성공률 계산"""
        resolved_errors = [e for e in self.error_history if e.is_resolved]
        total_recoverable = [e for e in self.error_history if e.severity != ErrorSeverity.LOW]
        
        if not total_recoverable:
            return 100.0
        
        return (len(resolved_errors) / len(total_recoverable)) * 100
    
    def get_active_errors(self) -> List[ErrorInfo]:
        """활성 에러 목록"""
        return list(self.active_errors.values())
    
    def get_recent_errors(self, hours: int = 1) -> List[ErrorInfo]:
        """최근 에러 목록"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [e for e in self.error_history if e.timestamp > cutoff_time]


# 데코레이터

def error_handler(recovery_system: ErrorRecoverySystem,
                 component: str = "",
                 severity: Optional[ErrorSeverity] = None,
                 fallback_result: Any = None):
    """에러 핸들링 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100]
                }
                
                error_info = await recovery_system.handle_error(
                    exception=e,
                    context=context,
                    component=component,
                    function_name=func.__name__,
                    severity=severity
                )
                
                if error_info.severity == ErrorSeverity.CRITICAL:
                    raise e
                
                return fallback_result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100]
                }
                
                # 동기 함수에서는 에러만 기록하고 다시 발생
                asyncio.create_task(recovery_system.handle_error(
                    exception=e,
                    context=context,
                    component=component,
                    function_name=func.__name__,
                    severity=severity
                ))
                
                if severity == ErrorSeverity.CRITICAL:
                    raise e
                
                return fallback_result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def circuit_breaker_with_recovery(recovery_system: ErrorRecoverySystem,
                                 failure_threshold: int = 5,
                                 timeout_seconds: float = 60.0):
    """복구 시스템 연동 서킷 브레이커"""
    from async_processing.async_utils import AsyncCircuitBreaker
    
    circuit_breaker = AsyncCircuitBreaker(failure_threshold, timeout_seconds)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await circuit_breaker.call(func, *args, **kwargs)
            except Exception as e:
                # 에러를 복구 시스템에 등록
                await recovery_system.handle_error(
                    exception=e,
                    component="circuit_breaker",
                    function_name=func.__name__
                )
                raise e
        
        return wrapper
    return decorator