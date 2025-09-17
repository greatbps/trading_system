#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Squeeze Momentum Pro 2차 필터링 엔진
Phase 1 품질 게이트를 활용한 고품질 종목 선별
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass

# Phase 1 모듈 import
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from signal_processing.consensus_engine import ConsensusEngine
from signal_processing.mtf_analyzer import MTFAnalyzer
from signal_processing.liquidity_gate import LiquidityGate
from signal_processing.news_gate import NewsGate
from signal_processing.regime_gate import RegimeGate
from monitoring.phase1_performance_monitor import phase1_monitor, SignalQualityMetrics
from configs.squeeze_momentum_config import squeeze_momentum_config

@dataclass
class SqueezeMomentumCandidate:
    """Squeeze Momentum 후보 종목"""
    symbol: str
    name: str
    current_price: float
    
    # Squeeze 관련 데이터
    squeeze_duration: int
    squeeze_release_signal: bool
    momentum_strength: float
    momentum_direction: str
    
    # 기술적 지표
    bb_squeeze_ratio: float
    kc_position: float
    volume_ratio: float
    atr_percentile: float
    
    # 추가 메타데이터
    sector: str = "Unknown"
    market_cap: float = 0.0
    trading_value: float = 0.0
    volatility: float = 0.0
    
@dataclass
class QualityAssessment:
    """품질 평가 결과"""
    consensus_score: float
    consensus_reached: bool
    mtf_score: float
    mtf_confluence: bool
    liquidity_pass: bool
    news_pass: bool
    regime: str
    overall_score: float
    quality_grade: str  # 'high', 'medium', 'low'
    risk_level: str

class SqueezeMomentumRecommendationEngine:
    """Squeeze Momentum Pro 2차 필터링 및 추천 엔진"""
    
    def __init__(self, config=None):
        self.config = config or squeeze_momentum_config
        self.logger = self._setup_logger()
        
        # Phase 1 품질 게이트 시스템 초기화
        self._initialize_phase1_systems()
        
        # 성능 메트릭
        self.processing_stats = {
            'total_processed': 0,
            'high_quality_count': 0,
            'processing_times': [],
            'recommendation_history': []
        }
        
        self.logger.info("🎯 Squeeze Momentum 추천 엔진 초기화 완료")
    
    def _setup_logger(self):
        """로거 설정"""
        import logging
        logger = logging.getLogger("SqueezeMomentumEngine")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _initialize_phase1_systems(self):
        """Phase 1 품질 게이트 시스템 초기화"""
        try:
            # 멀티전략 합의 엔진 (Squeeze Momentum을 포함한 전략들)
            strategies = ['squeeze_momentum', 'momentum', 'breakout', 'volume_spike']
            self.consensus_engine = ConsensusEngine(strategies, lookback_days=60)
            
            # MTF 컨플루언스 분석기
            timeframes = ['5m', '15m', '1h', '1d']
            self.mtf_analyzer = MTFAnalyzer(timeframes)
            
            # 게이트 시스템들
            self.liquidity_gate = LiquidityGate(
                atr_min_pct=2.0,
                trade_value_min=1000000000,  # 10억원
                spread_max_pct=0.5
            )
            
            self.news_gate = NewsGate(
                sentiment_threshold=-0.5,
                disclosure_cooldown_minutes=60
            )
            
            self.regime_gate = RegimeGate(adx_threshold=25)
            
            self.logger.info("✅ Phase 1 품질 게이트 시스템 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"❌ Phase 1 시스템 초기화 실패: {e}")
            raise
    
    async def apply_secondary_filter(self, primary_candidates: List[SqueezeMomentumCandidate]) -> List[Dict[str, Any]]:
        """2차 필터링 - Phase 1 품질 게이트 적용"""
        if not primary_candidates:
            return []
        
        start_time = time.perf_counter()
        self.logger.info(f"🔍 2차 필터링 시작 - 후보 수: {len(primary_candidates)}")
        
        high_quality_candidates = []
        
        for candidate in primary_candidates:
            try:
                # 각 후보에 대해 품질 평가 수행
                quality_assessment = await self._assess_candidate_quality(candidate)
                
                # 품질 기준 통과 여부 확인
                if self._meets_quality_criteria(quality_assessment):
                    recommendation = self._build_recommendation(candidate, quality_assessment)
                    high_quality_candidates.append(recommendation)
                    
            except Exception as e:
                self.logger.error(f"❌ 종목 {candidate.symbol} 품질 평가 실패: {e}")
                continue
        
        # 성능 통계 업데이트
        processing_time = (time.perf_counter() - start_time) * 1000
        self.processing_stats['total_processed'] += len(primary_candidates)
        self.processing_stats['high_quality_count'] += len(high_quality_candidates)
        self.processing_stats['processing_times'].append(processing_time)
        
        # 추천 등급별 정렬
        high_quality_candidates.sort(key=lambda x: x['overall_score'], reverse=True)
        
        self.logger.info(f"✅ 2차 필터링 완료 - 고품질 종목: {len(high_quality_candidates)}개 "
                        f"({processing_time:.1f}ms)")
        
        return high_quality_candidates
    
    async def _assess_candidate_quality(self, candidate: SqueezeMomentumCandidate) -> QualityAssessment:
        """후보 종목 품질 평가"""
        timing_data = phase1_monitor.start_signal_timing()
        
        try:
            # 1. 전략 신호를 Phase 1 형식으로 변환
            strategy_signals = self._convert_to_phase1_signals(candidate)
            
            # 2. 멀티전략 합의 계산
            phase1_monitor.record_consensus_timing(timing_data)
            consensus_start = time.perf_counter()
            
            consensus_score = self.consensus_engine.calculate_consensus_score(strategy_signals)
            consensus_reached = self.consensus_engine.is_consensus_reached(
                consensus_score, self.config.secondary_filter_criteria['consensus_threshold']
            )
            consensus_time = (time.perf_counter() - consensus_start) * 1000
            
            # 3. MTF 컨플루언스 분석
            phase1_monitor.record_mtf_timing(timing_data)
            mtf_signals = self._extract_mtf_signals(candidate)
            
            mtf_start = time.perf_counter()
            mtf_score = self.mtf_analyzer.calculate_confluence_score(mtf_signals)
            mtf_confluence = self.mtf_analyzer.is_confluence_met(
                mtf_score, self.config.secondary_filter_criteria['mtf_threshold']
            )
            mtf_time = (time.perf_counter() - mtf_start) * 1000
            
            # 4. 게이트 시스템 평가
            phase1_monitor.record_gate_timing(timing_data)
            gate_start = time.perf_counter()
            
            # 유동성 게이트
            market_data = self._prepare_market_data(candidate)
            liquidity_pass = self.liquidity_gate.evaluate(candidate.symbol, market_data)
            
            # 뉴스 게이트 (기본 중립 뉴스 가정)
            news_data = self._prepare_news_data(candidate)
            news_pass = self.news_gate.evaluate(candidate.symbol, news_data)
            
            # 레짐 게이트
            regime_data = self._prepare_regime_data(candidate)
            current_regime = self.regime_gate.detect_regime(regime_data)
            
            gate_time = (time.perf_counter() - gate_start) * 1000
            
            # 5. 전체 품질 점수 계산
            overall_score = self._calculate_overall_quality_score(
                consensus_score, mtf_score, liquidity_pass, news_pass, candidate
            )
            
            # 6. 품질 등급 결정
            quality_grade = self._determine_quality_grade(overall_score, consensus_reached, 
                                                        mtf_confluence, liquidity_pass, news_pass)
            
            # 7. 리스크 레벨 평가
            risk_level = self._assess_risk_level(candidate, quality_grade, current_regime)
            
            # 8. 성능 메트릭 기록
            total_time = (time.perf_counter() - timing_data['start_time']) * 1000
            
            metrics = SignalQualityMetrics(
                timestamp=datetime.now().isoformat(),
                symbol=candidate.symbol,
                consensus_score=consensus_score,
                participating_strategies=len(strategy_signals),
                consensus_time_ms=consensus_time,
                mtf_score=mtf_score,
                timeframe_alignment=mtf_signals,
                mtf_calculation_time_ms=mtf_time,
                liquidity_gate_passed=liquidity_pass,
                news_gate_passed=news_pass,
                regime_gate_passed=True,
                total_gate_time_ms=gate_time,
                final_signal_strength=overall_score,
                signal_confidence=min(1.0, overall_score / 100)
            )
            
            phase1_monitor.record_signal_metrics(metrics)
            
            return QualityAssessment(
                consensus_score=consensus_score,
                consensus_reached=consensus_reached,
                mtf_score=mtf_score,
                mtf_confluence=mtf_confluence,
                liquidity_pass=liquidity_pass,
                news_pass=news_pass,
                regime=current_regime,
                overall_score=overall_score,
                quality_grade=quality_grade,
                risk_level=risk_level
            )
            
        except Exception as e:
            self.logger.error(f"❌ {candidate.symbol} 품질 평가 실패: {e}")
            # 기본 품질 평가 반환
            return QualityAssessment(
                consensus_score=0.0, consensus_reached=False,
                mtf_score=0.0, mtf_confluence=False,
                liquidity_pass=False, news_pass=True,
                regime='SIDEWAYS', overall_score=0.0,
                quality_grade='low', risk_level='HIGH'
            )
    
    def _convert_to_phase1_signals(self, candidate: SqueezeMomentumCandidate) -> Dict[str, float]:
        """후보 종목의 Squeeze Momentum 데이터를 Phase 1 신호 형식으로 변환"""
        # Squeeze Momentum Pro의 강도를 기반으로 각 전략 신호 추정
        base_strength = candidate.momentum_strength
        
        # 방향성 고려 (+1: 상승, -1: 하락)
        direction_multiplier = 1.0 if candidate.momentum_direction == 'bullish' else -1.0
        
        # 볼륨 확인 가중치
        volume_weight = min(2.0, candidate.volume_ratio)
        
        # 각 전략별 신호 생성
        signals = {
            'squeeze_momentum': base_strength * direction_multiplier,
            'momentum': (base_strength * 0.8) * direction_multiplier * volume_weight,
            'breakout': (candidate.bb_squeeze_ratio * 0.9) * direction_multiplier,
            'volume_spike': (candidate.volume_ratio - 1.0) * direction_multiplier if candidate.volume_ratio > 1.0 else 0.0
        }
        
        # -1 ~ 1 범위로 정규화
        for key in signals:
            signals[key] = max(-1.0, min(1.0, signals[key]))
        
        return signals
    
    def _extract_mtf_signals(self, candidate: SqueezeMomentumCandidate) -> Dict[str, float]:
        """멀티 타임프레임 신호 추출 (Squeeze Momentum 기반)"""
        base_momentum = candidate.momentum_strength
        
        # 시간대별로 강도 차등 적용 (단기에서 장기로 갈수록 보수적)
        timeframe_weights = {'5m': 1.0, '15m': 0.9, '1h': 0.8, '1d': 0.7}
        
        mtf_signals = {}
        for timeframe, weight in timeframe_weights.items():
            # Squeeze duration이 길수록 장기 신호가 더 강함
            duration_factor = min(1.0, candidate.squeeze_duration / 10.0)
            
            if timeframe in ['1h', '1d']:
                signal_strength = base_momentum * weight * (0.5 + 0.5 * duration_factor)
            else:
                signal_strength = base_momentum * weight
            
            mtf_signals[timeframe] = max(0.0, min(1.0, signal_strength))
        
        return mtf_signals
    
    def _prepare_market_data(self, candidate: SqueezeMomentumCandidate) -> Dict:
        """게이트 평가용 시장 데이터 준비"""
        return {
            'price': candidate.current_price,
            'atr': candidate.current_price * candidate.volatility * 0.02,  # 변동성 기반 ATR 추정
            'avg_trade_value': candidate.trading_value,
            'spread_pct': max(0.1, min(1.0, 1.0 / candidate.volume_ratio)) * 0.3  # 거래량 역비례 스프레드
        }
    
    def _prepare_news_data(self, candidate: SqueezeMomentumCandidate) -> List[Dict]:
        """뉴스 데이터 준비 (기본 중립)"""
        return [{
            'type': 'news',
            'timestamp': datetime.now() - timedelta(hours=1),
            'sentiment': 0.1,  # 약간 긍정적
            'content': f'{candidate.name} Squeeze Momentum 신호 발생'
        }]
    
    def _prepare_regime_data(self, candidate: SqueezeMomentumCandidate) -> Dict:
        """레짐 데이터 준비"""
        # 변동성과 모멘텀 기반 ADX 추정
        estimated_adx = min(50, max(15, candidate.volatility * 100 + abs(candidate.momentum_strength) * 20))
        
        # 현재가 기준 이동평균 추정
        price_trend = 1.02 if candidate.momentum_direction == 'bullish' else 0.98
        
        return {
            'adx': estimated_adx,
            'sma_short': candidate.current_price * price_trend,
            'sma_long': candidate.current_price * (2 - price_trend)
        }
    
    def _calculate_overall_quality_score(self, consensus_score: float, mtf_score: float,
                                       liquidity_pass: bool, news_pass: bool,
                                       candidate: SqueezeMomentumCandidate) -> float:
        """전체 품질 점수 계산"""
        # 기본 점수 (합의 + MTF)
        base_score = (consensus_score * 15 + mtf_score * 70)  # 0-85 범위
        
        # 게이트 통과 보너스
        gate_bonus = 0
        if liquidity_pass:
            gate_bonus += 5
        if news_pass:
            gate_bonus += 5
        
        # Squeeze 품질 보너스
        squeeze_bonus = 0
        if candidate.squeeze_duration >= 7:  # 충분한 squeeze 지속
            squeeze_bonus += 3
        if candidate.volume_ratio >= 2.0:    # 강한 거래량 확인
            squeeze_bonus += 2
        
        # 최종 점수 계산
        final_score = base_score + gate_bonus + squeeze_bonus
        
        return max(0.0, min(100.0, final_score))
    
    def _determine_quality_grade(self, overall_score: float, consensus_reached: bool,
                               mtf_confluence: bool, liquidity_pass: bool, news_pass: bool) -> str:
        """품질 등급 결정"""
        if (overall_score >= 85 and consensus_reached and mtf_confluence and 
            liquidity_pass and news_pass):
            return 'high'
        elif overall_score >= 70 and (consensus_reached or mtf_confluence) and liquidity_pass:
            return 'medium'
        else:
            return 'low'
    
    def _assess_risk_level(self, candidate: SqueezeMomentumCandidate, 
                          quality_grade: str, regime: str) -> str:
        """리스크 레벨 평가"""
        risk_factors = []
        
        # 품질 등급별 리스크
        if quality_grade == 'low':
            risk_factors.append(1)
        
        # 변동성 리스크
        if candidate.volatility > 0.05:  # 5% 이상 변동성
            risk_factors.append(1)
        
        # 레짐별 리스크
        if regime == 'VOLATILE':
            risk_factors.append(1)
        elif regime == 'SIDEWAYS':
            risk_factors.append(0.5)
        
        # Squeeze 지속기간 리스크
        if candidate.squeeze_duration > 15:  # 너무 긴 squeeze
            risk_factors.append(0.5)
        
        # 전체 리스크 평가
        total_risk = sum(risk_factors)
        
        if total_risk >= 2:
            return 'HIGH'
        elif total_risk >= 1:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _meets_quality_criteria(self, assessment: QualityAssessment) -> bool:
        """품질 기준 통과 여부 확인"""
        criteria = self.config.secondary_filter_criteria
        
        # 필수 조건들
        if not assessment.liquidity_pass and criteria['liquidity_gate']:
            return False
        
        if not assessment.news_pass and criteria['news_gate']:
            return False
        
        if assessment.overall_score < (criteria['min_signal_confidence'] * 100):
            return False
        
        # 합의 또는 MTF 중 하나는 통과해야 함
        min_consensus = assessment.consensus_score >= criteria['consensus_threshold']
        min_mtf = assessment.mtf_score >= criteria['mtf_threshold']
        
        if not (min_consensus or min_mtf):
            return False
        
        return True
    
    def _build_recommendation(self, candidate: SqueezeMomentumCandidate, 
                            assessment: QualityAssessment) -> Dict[str, Any]:
        """최종 추천 구성"""
        # 추천 등급 결정
        recommendation_grade = self._get_recommendation_grade(assessment.overall_score, assessment.quality_grade)
        
        return {
            'symbol': candidate.symbol,
            'name': candidate.name,
            'current_price': candidate.current_price,
            'recommendation_grade': recommendation_grade,
            'overall_score': round(assessment.overall_score, 1),
            
            # Squeeze Momentum 정보
            'squeeze_info': {
                'duration': candidate.squeeze_duration,
                'momentum_strength': candidate.momentum_strength,
                'momentum_direction': candidate.momentum_direction,
                'volume_ratio': candidate.volume_ratio,
                'breakout_signal': candidate.squeeze_release_signal
            },
            
            # Phase 1 품질 정보
            'quality_assessment': {
                'grade': assessment.quality_grade,
                'consensus_score': round(assessment.consensus_score, 3),
                'consensus_reached': assessment.consensus_reached,
                'mtf_score': round(assessment.mtf_score, 3),
                'mtf_confluence': assessment.mtf_confluence,
                'liquidity_pass': assessment.liquidity_pass,
                'news_pass': assessment.news_pass,
                'regime': assessment.regime,
                'risk_level': assessment.risk_level
            },
            
            # 추가 메타 정보
            'metadata': {
                'sector': candidate.sector,
                'market_cap': candidate.market_cap,
                'volatility': candidate.volatility,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _get_recommendation_grade(self, overall_score: float, quality_grade: str) -> str:
        """추천 등급 결정"""
        if overall_score >= 85 and quality_grade == 'high':
            return 'STRONG_BUY'
        elif overall_score >= 70 and quality_grade in ['high', 'medium']:
            return 'BUY'
        elif overall_score >= 50:
            return 'HOLD'
        else:
            return 'WATCH'
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """처리 통계 조회"""
        if not self.processing_stats['processing_times']:
            return {'status': 'no_data'}
        
        times = self.processing_stats['processing_times']
        
        return {
            'total_processed': self.processing_stats['total_processed'],
            'high_quality_count': self.processing_stats['high_quality_count'],
            'success_rate': (self.processing_stats['high_quality_count'] / 
                           max(1, self.processing_stats['total_processed'])),
            'avg_processing_time_ms': np.mean(times),
            'max_processing_time_ms': np.max(times),
            'min_processing_time_ms': np.min(times),
            'processing_sessions': len(times)
        }