#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 성능 모니터링: 승률 개선 추적
"""

import time
from datetime import datetime
from typing import Dict, List, Any
import json
from dataclasses import dataclass, asdict

@dataclass
class SignalQualityMetrics:
    """신호 품질 메트릭"""
    timestamp: str
    symbol: str
    
    # 멀티전략 합의 메트릭
    consensus_score: float
    participating_strategies: int
    consensus_time_ms: float
    
    # MTF 컨플루언스 메트릭  
    mtf_score: float
    timeframe_alignment: Dict[str, float]
    mtf_calculation_time_ms: float
    
    # 게이트 통과 메트릭
    liquidity_gate_passed: bool
    news_gate_passed: bool  
    regime_gate_passed: bool
    total_gate_time_ms: float
    
    # 최종 신호 품질
    final_signal_strength: float
    signal_confidence: float

class Phase1PerformanceMonitor:
    """Phase 1 성능 모니터링 시스템"""
    
    def __init__(self):
        self.metrics_history: List[SignalQualityMetrics] = []
        self.performance_targets = {
            'consensus_time_ms': 100,
            'mtf_calculation_time_ms': 50, 
            'gate_evaluation_time_ms': 20,
            'total_signal_time_ms': 200,
            'min_consensus_score': 2.0,
            'min_mtf_score': 0.6,
            'min_signal_confidence': 0.7
        }
    
    def start_signal_timing(self) -> Dict[str, float]:
        """신호 생성 시간 측정 시작"""
        return {
            'start_time': time.perf_counter(),
            'consensus_start': None,
            'mtf_start': None,
            'gate_start': None
        }
    
    def record_consensus_timing(self, timing_data: Dict[str, float]):
        """합의 단계 시간 기록"""
        timing_data['consensus_start'] = time.perf_counter()
    
    def record_mtf_timing(self, timing_data: Dict[str, float]):
        """MTF 단계 시간 기록"""
        timing_data['mtf_start'] = time.perf_counter()
    
    def record_gate_timing(self, timing_data: Dict[str, float]):
        """게이트 단계 시간 기록"""
        timing_data['gate_start'] = time.perf_counter()
    
    def record_signal_metrics(self, metrics: SignalQualityMetrics):
        """신호 품질 메트릭 기록"""
        self.metrics_history.append(metrics)
        
        # 성능 임계값 체크
        self._check_performance_thresholds(metrics)
    
    def _check_performance_thresholds(self, metrics: SignalQualityMetrics):
        """성능 임계값 검사"""
        alerts = []
        
        if metrics.consensus_time_ms > self.performance_targets['consensus_time_ms']:
            alerts.append(f"Consensus 시간 초과: {metrics.consensus_time_ms:.2f}ms")
        
        if metrics.mtf_calculation_time_ms > self.performance_targets['mtf_calculation_time_ms']:
            alerts.append(f"MTF 계산 시간 초과: {metrics.mtf_calculation_time_ms:.2f}ms")
        
        if metrics.total_gate_time_ms > self.performance_targets['gate_evaluation_time_ms']:
            alerts.append(f"게이트 평가 시간 초과: {metrics.total_gate_time_ms:.2f}ms")
        
        if metrics.consensus_score < self.performance_targets['min_consensus_score']:
            alerts.append(f"합의 점수 부족: {metrics.consensus_score:.2f}")
        
        if alerts:
            print(f"[PERFORMANCE ALERT] {metrics.symbol}: {', '.join(alerts)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 통계"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-100:]  # 최근 100개
        
        return {
            "total_signals": len(self.metrics_history),
            "recent_signals": len(recent_metrics),
            "avg_consensus_time": sum(m.consensus_time_ms for m in recent_metrics) / len(recent_metrics),
            "avg_mtf_time": sum(m.mtf_calculation_time_ms for m in recent_metrics) / len(recent_metrics),
            "avg_gate_time": sum(m.total_gate_time_ms for m in recent_metrics) / len(recent_metrics),
            "avg_signal_strength": sum(m.final_signal_strength for m in recent_metrics) / len(recent_metrics),
            "avg_confidence": sum(m.signal_confidence for m in recent_metrics) / len(recent_metrics),
            "gate_pass_rates": {
                "liquidity": sum(1 for m in recent_metrics if m.liquidity_gate_passed) / len(recent_metrics),
                "news": sum(1 for m in recent_metrics if m.news_gate_passed) / len(recent_metrics),
                "regime": sum(1 for m in recent_metrics if m.regime_gate_passed) / len(recent_metrics)
            }
        }
    
    def save_metrics_report(self, filepath: str):
        """메트릭 리포트 저장"""
        report = {
            "generation_time": datetime.now().isoformat(),
            "performance_targets": self.performance_targets,
            "summary": self.get_performance_summary(),
            "detailed_metrics": [asdict(m) for m in self.metrics_history]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

# 전역 모니터 인스턴스
phase1_monitor = Phase1PerformanceMonitor()