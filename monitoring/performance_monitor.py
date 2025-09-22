#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/monitoring/performance_monitor.py

고급 성능 모니터링 시스템 - Phase 7 System Optimization
"""

import asyncio
import psutil
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import gc
import tracemalloc
import sys
import os

from utils.logger import get_logger
from typing import Tuple
import statistics
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_threads: int
    open_files: int
    response_time_ms: float
    throughput_ops_per_sec: float
    error_rate_percent: float


@dataclass
class ComponentPerformance:
    """컴포넌트별 성능 데이터"""
    component_name: str
    avg_execution_time_ms: float
    max_execution_time_ms: float
    min_execution_time_ms: float
    total_calls: int
    error_count: int
    memory_usage_mb: float
    cpu_time_ms: float
    last_updated: datetime


@dataclass
class PerformanceAlert:
    """성능 경고"""
    alert_type: str  # CPU, MEMORY, RESPONSE_TIME, ERROR_RATE
    severity: str    # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    component: Optional[str] = None
    recommended_action: Optional[str] = None


class PerformanceMonitor:
    """고급 성능 모니터링 시스템"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("PerformanceMonitor")
        
        # 모니터링 설정
        self.monitoring_interval = 5.0  # 5초마다 메트릭 수집
        self.history_size = 1000        # 최대 1000개 메트릭 보관
        self.alert_cooldown = 300       # 5분 알림 쿨다운
        
        # 성능 임계값 - 강화된 모니터링
        self.thresholds = {
            'cpu_percent': {'medium': 60, 'high': 75, 'critical': 90},  # 더 엄격하게
            'memory_percent': {'medium': 70, 'high': 85, 'critical': 95},
            'response_time_ms': {'medium': 500, 'high': 1500, 'critical': 3000},  # 더 빠르게
            'error_rate_percent': {'medium': 0.5, 'high': 2, 'critical': 5},  # 더 엄격하게
            'disk_io_mb_per_sec': {'medium': 30, 'high': 60, 'critical': 100},
            'network_latency_ms': {'medium': 100, 'high': 300, 'critical': 500},
            'concurrent_connections': {'medium': 100, 'high': 200, 'critical': 300}
        }
        
        # 데이터 저장
        self.metrics_history = deque(maxlen=self.history_size)
        self.component_metrics = {}  # component_name -> ComponentPerformance
        self.active_alerts = {}      # alert_type -> PerformanceAlert
        self.alert_history = deque(maxlen=100)
        
        # 모니터링 상태
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_alert_time = {}    # alert_type -> timestamp
        
        # 성능 카운터 - 강화된 추적
        self.operation_counters = defaultdict(int)
        self.operation_times = defaultdict(list)
        self.start_times = {}        # operation_id -> start_time
        self.trend_analyzer = TrendAnalyzer()  # 트렌드 분석기
        self.anomaly_detector = AnomalyDetector()  # 이상 탐지기
        self.predictive_alerts = PredictiveAlerts()  # 예측 알림
        
        # 메모리 추적
        self.memory_tracker_enabled = False
        if hasattr(tracemalloc, 'start'):
            try:
                tracemalloc.start()
                self.memory_tracker_enabled = True
            except Exception as e:
                self.logger.warning(f"메모리 추적 시작 실패: {e}")
        
        # 시스템 정보
        self.system_info = self._get_system_info()
        
        self.logger.info("✅ 고급 성능 모니터링 시스템 초기화 완료")
        self.logger.info(f"📊 시스템 정보: CPU {self.system_info['cpu_count']}코어, "
                        f"메모리 {self.system_info['total_memory_gb']:.1f}GB")
    
    def start_monitoring(self):
        """성능 모니터링 시작"""
        if self.is_monitoring:
            self.logger.warning("성능 모니터링이 이미 실행 중입니다")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("🔍 성능 모니터링 시작")
    
    def stop_monitoring(self):
        """성능 모니터링 중지"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        self.logger.info("⏹️ 성능 모니터링 중지")
    
    def _monitoring_loop(self):
        """모니터링 메인 루프"""
        try:
            while self.is_monitoring:
                # 메트릭 수집
                metrics = self._collect_metrics()
                if metrics:
                    self.metrics_history.append(metrics)
                    
                    # 알림 검사
                    self._check_alerts(metrics)
                    
                    # 컴포넌트 메트릭 업데이트
                    self._update_component_metrics()
                
                time.sleep(self.monitoring_interval)
                
        except Exception as e:
            self.logger.error(f"❌ 성능 모니터링 루프 에러: {e}")
            self.logger.error(traceback.format_exc())
    
    def _collect_metrics(self) -> Optional[PerformanceMetrics]:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = (memory.total - memory.available) / 1024 / 1024
            
            # 디스크 I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / 1024 / 1024 if disk_io else 0
            disk_write_mb = disk_io.write_bytes / 1024 / 1024 if disk_io else 0
            
            # 네트워크 I/O
            network_io = psutil.net_io_counters()
            network_sent_mb = network_io.bytes_sent / 1024 / 1024 if network_io else 0
            network_recv_mb = network_io.bytes_recv / 1024 / 1024 if network_io else 0
            
            # 프로세스 정보
            current_process = psutil.Process()
            active_threads = current_process.num_threads()
            open_files = len(current_process.open_files())
            
            # 성능 지표 계산
            response_time_ms = self._calculate_avg_response_time()
            throughput_ops = self._calculate_throughput()
            error_rate = self._calculate_error_rate()
            
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                active_threads=active_threads,
                open_files=open_files,
                response_time_ms=response_time_ms,
                throughput_ops_per_sec=throughput_ops,
                error_rate_percent=error_rate
            )
            
        except Exception as e:
            self.logger.error(f"❌ 메트릭 수집 실패: {e}")
            return None
    
    def _calculate_avg_response_time(self) -> float:
        """평균 응답 시간 계산"""
        if not self.operation_times:
            return 0.0
        
        all_times = []
        for times_list in self.operation_times.values():
            all_times.extend(times_list)
        
        return sum(all_times) / len(all_times) if all_times else 0.0
    
    def _calculate_throughput(self) -> float:
        """처리량 계산 (초당 작업 수)"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        current_time = datetime.now()
        one_minute_ago = current_time - timedelta(minutes=1)
        
        recent_ops = sum(1 for metric in self.metrics_history 
                        if metric.timestamp >= one_minute_ago)
        
        return recent_ops / 60.0  # 초당 작업 수
    
    def _calculate_error_rate(self) -> float:
        """에러율 계산"""
        total_ops = sum(self.operation_counters.values())
        if total_ops == 0:
            return 0.0
        
        error_ops = self.operation_counters.get('errors', 0)
        return (error_ops / total_ops) * 100
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """성능 알림 검사"""
        alerts_to_send = []
        
        # CPU 사용률 체크
        cpu_alert = self._check_threshold_alert(
            'CPU', metrics.cpu_percent, self.thresholds['cpu_percent'],
            f"CPU 사용률이 {metrics.cpu_percent:.1f}%입니다"
        )
        if cpu_alert:
            alerts_to_send.append(cpu_alert)
        
        # 메모리 사용률 체크
        memory_alert = self._check_threshold_alert(
            'MEMORY', metrics.memory_percent, self.thresholds['memory_percent'],
            f"메모리 사용률이 {metrics.memory_percent:.1f}%입니다"
        )
        if memory_alert:
            alerts_to_send.append(memory_alert)
        
        # 응답 시간 체크
        response_alert = self._check_threshold_alert(
            'RESPONSE_TIME', metrics.response_time_ms, self.thresholds['response_time_ms'],
            f"평균 응답 시간이 {metrics.response_time_ms:.1f}ms입니다"
        )
        if response_alert:
            alerts_to_send.append(response_alert)
        
        # 에러율 체크
        error_alert = self._check_threshold_alert(
            'ERROR_RATE', metrics.error_rate_percent, self.thresholds['error_rate_percent'],
            f"에러율이 {metrics.error_rate_percent:.1f}%입니다"
        )
        if error_alert:
            alerts_to_send.append(error_alert)
        
        # 알림 발송
        for alert in alerts_to_send:
            self._send_alert(alert)
    
    def _check_threshold_alert(self, alert_type: str, current_value: float, 
                             thresholds: Dict, message: str) -> Optional[PerformanceAlert]:
        """임계값 기반 알림 체크"""
        severity = None
        threshold_value = 0
        
        if current_value >= thresholds['critical']:
            severity = 'CRITICAL'
            threshold_value = thresholds['critical']
        elif current_value >= thresholds['high']:
            severity = 'HIGH' 
            threshold_value = thresholds['high']
        elif current_value >= thresholds['medium']:
            severity = 'MEDIUM'
            threshold_value = thresholds['medium']
        
        if severity:
            # 쿨다운 체크
            last_alert = self.last_alert_time.get(alert_type)
            if last_alert and (datetime.now() - last_alert).seconds < self.alert_cooldown:
                return None
            
            return PerformanceAlert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                current_value=current_value,
                threshold_value=threshold_value,
                timestamp=datetime.now(),
                recommended_action=self._get_recommended_action(alert_type, severity)
            )
        
        return None
    
    def _get_recommended_action(self, alert_type: str, severity: str) -> str:
        """알림별 권장 조치"""
        actions = {
            'CPU': {
                'MEDIUM': '백그라운드 프로세스 확인',
                'HIGH': '불필요한 작업 중지',
                'CRITICAL': '시스템 재시작 고려'
            },
            'MEMORY': {
                'MEDIUM': '메모리 사용량 모니터링',
                'HIGH': '가비지 컬렉션 강제 실행',
                'CRITICAL': '메모리 누수 확인 필요'
            },
            'RESPONSE_TIME': {
                'MEDIUM': '처리 로직 최적화 검토',
                'HIGH': '비동기 처리 강화',
                'CRITICAL': '시스템 부하 분산 필요'
            },
            'ERROR_RATE': {
                'MEDIUM': '에러 로그 확인',
                'HIGH': '에러 원인 분석 필요',
                'CRITICAL': '서비스 중단 고려'
            }
        }
        
        return actions.get(alert_type, {}).get(severity, '모니터링 지속')
    
    def _send_alert(self, alert: PerformanceAlert):
        """알림 발송"""
        self.active_alerts[alert.alert_type] = alert
        self.alert_history.append(alert)
        self.last_alert_time[alert.alert_type] = alert.timestamp
        
        # 로그 출력
        severity_emoji = {
            'MEDIUM': '⚠️',
            'HIGH': '🚨',
            'CRITICAL': '🔥'
        }
        
        emoji = severity_emoji.get(alert.severity, '⚠️')
        self.logger.warning(f"{emoji} 성능 알림 [{alert.severity}]: {alert.message}")
        self.logger.info(f"권장 조치: {alert.recommended_action}")
    
    def _update_component_metrics(self):
        """컴포넌트별 메트릭 업데이트"""
        for component_name, times_list in self.operation_times.items():
            if not times_list:
                continue
            
            avg_time = sum(times_list) / len(times_list)
            max_time = max(times_list)
            min_time = min(times_list)
            total_calls = len(times_list)
            error_count = self.operation_counters.get(f'{component_name}_errors', 0)
            
            # 메모리 사용량 추정
            memory_usage = self._estimate_component_memory(component_name)
            
            self.component_metrics[component_name] = ComponentPerformance(
                component_name=component_name,
                avg_execution_time_ms=avg_time,
                max_execution_time_ms=max_time,
                min_execution_time_ms=min_time,
                total_calls=total_calls,
                error_count=error_count,
                memory_usage_mb=memory_usage,
                cpu_time_ms=avg_time * total_calls,  # 간략한 CPU 시간 추정
                last_updated=datetime.now()
            )
    
    def _estimate_component_memory(self, component_name: str) -> float:
        """컴포넌트 메모리 사용량 추정"""
        if not self.memory_tracker_enabled:
            return 0.0
        
        try:
            current, peak = tracemalloc.get_traced_memory()
            return current / 1024 / 1024  # MB로 변환
        except:
            return 0.0
    
    def _get_system_info(self) -> Dict:
        """시스템 정보 수집"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                'total_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'python_version': sys.version.split()[0],
                'platform': sys.platform,
                'pid': os.getpid()
            }
        except:
            return {}
    
    # === 외부 API 메서드들 ===
    
    def start_operation(self, operation_name: str) -> str:
        """작업 시작 기록"""
        operation_id = f"{operation_name}_{datetime.now().timestamp()}"
        self.start_times[operation_id] = time.time()
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True):
        """작업 종료 기록"""
        if operation_id not in self.start_times:
            return
        
        end_time = time.time()
        start_time = self.start_times.pop(operation_id)
        execution_time_ms = (end_time - start_time) * 1000
        
        # 작업명 추출
        operation_name = operation_id.split('_')[0]
        
        # 기록 저장
        self.operation_times[operation_name].append(execution_time_ms)
        self.operation_counters[operation_name] += 1
        
        if not success:
            self.operation_counters[f'{operation_name}_errors'] += 1
            self.operation_counters['errors'] += 1
        
        # 리스트 크기 제한
        if len(self.operation_times[operation_name]) > 100:
            self.operation_times[operation_name] = self.operation_times[operation_name][-100:]
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """현재 성능 메트릭 조회"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, minutes: int = 30) -> List[PerformanceMetrics]:
        """과거 메트릭 이력 조회"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_component_performance(self) -> Dict[str, ComponentPerformance]:
        """컴포넌트별 성능 정보 조회"""
        return self.component_metrics.copy()
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """현재 활성 알림 조회"""
        return list(self.active_alerts.values())
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-10:]  # 최근 10개
        
        return {
            'system_info': self.system_info,
            'current_metrics': asdict(recent_metrics[-1]) if recent_metrics else None,
            'avg_cpu_percent': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            'avg_memory_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            'avg_response_time_ms': sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics),
            'total_operations': sum(self.operation_counters.values()),
            'active_alerts_count': len(self.active_alerts),
            'top_slow_components': self._get_top_slow_components(),
            'monitoring_duration_minutes': self._get_monitoring_duration(),
            'timestamp': datetime.now()
        }
    
    def _get_top_slow_components(self) -> List[Dict]:
        """가장 느린 컴포넌트 상위 5개"""
        sorted_components = sorted(
            self.component_metrics.values(),
            key=lambda x: x.avg_execution_time_ms,
            reverse=True
        )
        
        return [
            {
                'name': comp.component_name,
                'avg_time_ms': comp.avg_execution_time_ms,
                'total_calls': comp.total_calls,
                'error_count': comp.error_count
            }
            for comp in sorted_components[:5]
        ]
    
    def _get_monitoring_duration(self) -> float:
        """모니터링 지속 시간 (분)"""
        if not self.metrics_history:
            return 0.0
        
        start_time = self.metrics_history[0].timestamp
        return (datetime.now() - start_time).total_seconds() / 60
    
    def force_garbage_collection(self):
        """강제 가비지 컬렉션"""
        collected = gc.collect()
        self.logger.info(f"🧹 가비지 컬렉션 완료: {collected}개 객체 정리")
        return collected
    
    def reset_metrics(self):
        """메트릭 초기화"""
        self.metrics_history.clear()
        self.component_metrics.clear()
        self.operation_counters.clear()
        self.operation_times.clear()
        self.active_alerts.clear()
        self.alert_history.clear()
        
        self.logger.info("📊 성능 메트릭 초기화 완료")


# 성능 모니터링 데코레이터
def monitor_performance(monitor: PerformanceMonitor, operation_name: str = None):
    """성능 모니터링 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            operation_id = monitor.start_operation(op_name)
            
            try:
                result = func(*args, **kwargs)
                monitor.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                monitor.end_operation(operation_id, success=False)
                raise
        
        return wrapper
    return decorator


# 비동기 성능 모니터링 데코레이터
def monitor_async_performance(monitor: PerformanceMonitor, operation_name: str = None):
    """비동기 성능 모니터링 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            operation_id = monitor.start_operation(op_name)
            
            try:
                result = await func(*args, **kwargs)
                monitor.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                monitor.end_operation(operation_id, success=False)
                raise
        
        return wrapper
    return decorator