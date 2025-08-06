#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/market_regime_detector.py

시장 체제 감지 시스템 - Phase 4 Advanced AI Features
"""

import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass
from collections import deque

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer


@dataclass
class MarketRegime:
    """시장 체제 정보"""
    regime_type: str  # BULL_TREND, BEAR_TREND, SIDEWAYS, HIGH_VOLATILITY, LOW_VOLATILITY
    sub_regime: str   # STRONG, MODERATE, WEAK
    confidence: float  # 0-100
    start_date: datetime
    duration_days: int
    expected_duration: int  # 예상 지속 기간 (일)
    key_indicators: List[str]
    recommended_strategies: List[str]
    risk_factors: List[str]
    market_characteristics: Dict[str, Any]
    transition_probability: Dict[str, float]  # 다른 체제로 전환 확률


@dataclass
class RegimeTransition:
    """체제 전환 정보"""
    from_regime: str
    to_regime: str
    transition_date: datetime
    transition_strength: float  # 0-100
    catalyst: str  # 전환 요인
    confirmation_indicators: List[str]
    expected_impact: str  # POSITIVE, NEGATIVE, NEUTRAL


@dataclass
class MarketState:
    """현재 시장 상태"""
    volatility_level: str  # VERY_LOW, LOW, MEDIUM, HIGH, VERY_HIGH
    trend_strength: float  # -100 to 100 (음수=하락, 양수=상승)
    volume_regime: str  # LOW, NORMAL, HIGH, SURGE
    breadth_indicator: float  # 시장 폭 지표
    momentum_score: float  # 모멘텀 점수
    fear_greed_index: float  # 공포/탐욕 지수 (0-100)
    correlation_level: float  # 종목간 상관관계
    timestamp: datetime


class MarketRegimeDetector:
    """시장 체제 감지기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("MarketRegimeDetector")
        self.gemini_analyzer = GeminiAnalyzer(config)
        
        # 체제 분류 임계값
        self.regime_thresholds = {
            'volatility': {
                'very_low': 0.10,
                'low': 0.15,
                'medium': 0.25,
                'high': 0.35,
                'very_high': 0.50
            },
            'trend': {
                'strong_bull': 2.0,
                'moderate_bull': 1.0,
                'weak_bull': 0.3,
                'sideways': 0.3,
                'weak_bear': -0.3,
                'moderate_bear': -1.0,
                'strong_bear': -2.0
            },
            'volume': {
                'low': 0.5,
                'normal': 1.5,
                'high': 2.5,
                'surge': 4.0
            }
        }
        
        # 이동 평균 기간
        self.lookback_periods = {
            'short': 5,
            'medium': 20,
            'long': 60
        }
        
        # 체제별 추천 전략
        self.regime_strategies = {
            'BULL_TREND': ['momentum', 'breakout', 'scalping_3m'],
            'BEAR_TREND': ['rsi', 'supertrend_ema_rsi'],
            'SIDEWAYS': ['eod', 'vwap'],
            'HIGH_VOLATILITY': ['scalping_3m', 'breakout'],
            'LOW_VOLATILITY': ['momentum', 'eod']
        }
        
        # 과거 체제 기록 (최근 100개)
        self.regime_history = deque(maxlen=100)
        self.current_regime = None
        
        self.logger.info("✅ 시장 체제 감지기 초기화 완료")
    
    async def detect_current_regime(self, market_data: List[Dict], 
                                  individual_stocks: List[Dict] = None) -> MarketRegime:
        """현재 시장 체제 감지"""
        try:
            self.logger.info("🌐 현재 시장 체제 감지 시작")
            
            # 1. 시장 상태 분석
            market_state = await self._analyze_market_state(market_data)
            
            # 2. 변동성 체제 분석
            volatility_regime = await self._analyze_volatility_regime(market_data)
            
            # 3. 트렌드 체제 분석
            trend_regime = await self._analyze_trend_regime(market_data)
            
            # 4. 거래량 체제 분석
            volume_regime = await self._analyze_volume_regime(market_data)
            
            # 5. 개별 주식 분석 (시장 폭 지표)
            breadth_analysis = await self._analyze_market_breadth(individual_stocks or [])
            
            # 6. AI 기반 종합 체제 판단
            regime_assessment = await self._ai_regime_classification(
                market_state, volatility_regime, trend_regime, volume_regime, breadth_analysis
            )
            
            # 7. 체제 전환 확률 계산
            transition_probabilities = await self._calculate_transition_probabilities(
                regime_assessment, market_state
            )
            
            # 8. 최종 체제 결정
            current_regime = await self._determine_final_regime(
                regime_assessment, transition_probabilities, market_state
            )
            
            # 9. 체제 기록 업데이트
            self._update_regime_history(current_regime)
            
            self.logger.info(f"✅ 시장 체제 감지 완료: {current_regime.regime_type} ({current_regime.confidence:.1f}%)")
            return current_regime
            
        except Exception as e:
            self.logger.error(f"❌ 시장 체제 감지 실패: {e}")
            return self._create_default_regime()
    
    async def predict_regime_transition(self, current_regime: MarketRegime, 
                                      leading_indicators: Dict) -> List[RegimeTransition]:
        """체제 전환 예측"""
        try:
            self.logger.info("🔄 시장 체제 전환 예측 시작")
            
            # 1. 선행 지표 분석
            leading_analysis = await self._analyze_leading_indicators(leading_indicators)
            
            # 2. 과거 체제 전환 패턴 분석
            historical_patterns = await self._analyze_historical_transitions()
            
            # 3. AI 기반 전환 예측
            ai_transition_analysis = await self._ai_transition_prediction(
                current_regime, leading_analysis, historical_patterns
            )
            
            # 4. 전환 시나리오 생성
            transition_scenarios = await self._generate_transition_scenarios(
                current_regime, ai_transition_analysis
            )
            
            # 5. 확률 기반 정렬
            ranked_transitions = sorted(
                transition_scenarios, 
                key=lambda x: x.transition_strength, 
                reverse=True
            )
            
            self.logger.info(f"✅ 체제 전환 예측 완료: {len(ranked_transitions)}개 시나리오")
            return ranked_transitions[:3]  # 상위 3개 시나리오 반환
            
        except Exception as e:
            self.logger.error(f"❌ 체제 전환 예측 실패: {e}")
            return []
    
    async def get_regime_based_recommendations(self, current_regime: MarketRegime,
                                             portfolio_context: Dict) -> Dict[str, Any]:
        """체제 기반 추천"""
        try:
            self.logger.info(f"📋 {current_regime.regime_type} 체제 기반 추천 생성")
            
            # 1. 기본 전략 추천
            recommended_strategies = self.regime_strategies.get(
                current_regime.regime_type, ['momentum']
            )
            
            # 2. 포지션 사이징 조정
            position_sizing_advice = await self._get_regime_position_sizing(
                current_regime, portfolio_context
            )
            
            # 3. 리스크 관리 조정
            risk_management_advice = await self._get_regime_risk_management(
                current_regime, portfolio_context
            )
            
            # 4. 시간대별 거래 조언
            timing_advice = await self._get_regime_timing_advice(current_regime)
            
            # 5. AI 기반 맞춤형 조언
            ai_recommendations = await self._ai_regime_recommendations(
                current_regime, portfolio_context
            )
            
            recommendations = {
                'primary_strategies': recommended_strategies,
                'position_sizing': position_sizing_advice,
                'risk_management': risk_management_advice,
                'timing_advice': timing_advice,
                'ai_insights': ai_recommendations,
                'regime_confidence': current_regime.confidence,
                'adaptation_frequency': self._get_adaptation_frequency(current_regime),
                'warning_signals': current_regime.risk_factors,
                'timestamp': datetime.now()
            }
            
            self.logger.info("✅ 체제 기반 추천 생성 완료")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"❌ 체제 기반 추천 실패: {e}")
            return {}
    
    async def monitor_regime_stability(self, current_regime: MarketRegime,
                                     recent_data: List[Dict]) -> Dict[str, Any]:
        """체제 안정성 모니터링"""
        try:
            self.logger.info("🔍 체제 안정성 모니터링 시작")
            
            # 1. 체제 지속 기간 분석
            duration_analysis = await self._analyze_regime_duration(current_regime)
            
            # 2. 체제 강도 변화 감지
            strength_analysis = await self._analyze_regime_strength_changes(
                current_regime, recent_data
            )
            
            # 3. 불안정 신호 감지
            instability_signals = await self._detect_instability_signals(
                current_regime, recent_data
            )
            
            # 4. 체제 신뢰도 업데이트
            updated_confidence = await self._update_regime_confidence(
                current_regime, duration_analysis, strength_analysis, instability_signals
            )
            
            stability_report = {
                'regime_stability': self._categorize_stability(updated_confidence),
                'stability_score': updated_confidence,
                'duration_status': duration_analysis.get('status', 'NORMAL'),
                'strength_changes': strength_analysis,
                'warning_signals': instability_signals,
                'confidence_trend': self._calculate_confidence_trend(),
                'recommended_monitoring_frequency': self._get_monitoring_frequency(updated_confidence),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 체제 안정성 모니터링 완료: {stability_report['regime_stability']}")
            return stability_report
            
        except Exception as e:
            self.logger.error(f"❌ 체제 안정성 모니터링 실패: {e}")
            return {}
    
    # === 내부 분석 메서드들 ===
    
    async def _analyze_market_state(self, market_data: List[Dict]) -> MarketState:
        """시장 상태 분석"""
        try:
            if not market_data:
                return self._create_default_market_state()
            
            # 최근 데이터 추출
            recent_data = market_data[-20:] if len(market_data) >= 20 else market_data
            
            # 변동성 계산
            price_changes = [item.get('change_rate', 0) for item in recent_data]
            volatility = np.std(price_changes) if price_changes else 0.02
            
            # 트렌드 강도 계산
            if len(recent_data) >= 5:
                recent_changes = price_changes[-5:]
                trend_strength = sum(recent_changes) / len(recent_changes) * 100
            else:
                trend_strength = 0
            
            # 거래량 분석
            volumes = [item.get('volume', 0) for item in recent_data]
            avg_volume = np.mean(volumes) if volumes else 1000000
            volume_ratio = (volumes[-1] / avg_volume) if volumes and avg_volume > 0 else 1.0
            
            return MarketState(
                volatility_level=self._categorize_volatility(volatility),
                trend_strength=trend_strength,
                volume_regime=self._categorize_volume(volume_ratio),
                breadth_indicator=60.0,  # 기본값
                momentum_score=trend_strength,
                fear_greed_index=50.0,  # 기본값 (중립)
                correlation_level=0.6,  # 기본값
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ 시장 상태 분석 실패: {e}")
            return self._create_default_market_state()
    
    async def _analyze_volatility_regime(self, market_data: List[Dict]) -> Dict:
        """변동성 체제 분석"""
        try:
            if not market_data:
                return {'regime': 'MEDIUM', 'confidence': 50}
            
            # 변동성 계산
            price_changes = [item.get('change_rate', 0) for item in market_data[-20:]]
            current_volatility = np.std(price_changes) if price_changes else 0.02
            
            # 체제 분류
            volatility_regime = self._categorize_volatility(current_volatility)
            
            # 신뢰도 계산
            confidence = min(90, max(50, 100 - abs(current_volatility - 0.20) * 200))
            
            return {
                'regime': volatility_regime,
                'current_volatility': current_volatility,
                'confidence': confidence,
                'trend': 'STABLE'  # 간단한 구현
            }
            
        except Exception as e:
            self.logger.error(f"❌ 변동성 체제 분석 실패: {e}")
            return {'regime': 'MEDIUM', 'confidence': 50}
    
    async def _analyze_trend_regime(self, market_data: List[Dict]) -> Dict:
        """트렌드 체제 분석"""
        try:
            if not market_data:
                return {'regime': 'SIDEWAYS', 'confidence': 50}
            
            # 단기, 중기, 장기 트렌드 분석
            short_term = self._calculate_trend(market_data, self.lookback_periods['short'])
            medium_term = self._calculate_trend(market_data, self.lookback_periods['medium'])
            long_term = self._calculate_trend(market_data, self.lookback_periods['long'])
            
            # 종합 트렌드 판단
            avg_trend = (short_term + medium_term + long_term) / 3
            
            if avg_trend > self.regime_thresholds['trend']['moderate_bull']:
                trend_regime = 'BULL_TREND'
            elif avg_trend < self.regime_thresholds['trend']['moderate_bear']:
                trend_regime = 'BEAR_TREND'
            else:
                trend_regime = 'SIDEWAYS'
            
            # 신뢰도 계산 (트렌드 일관성 기반)
            trend_consistency = 1 - np.std([short_term, medium_term, long_term]) / 2
            confidence = max(50, min(95, trend_consistency * 100))
            
            return {
                'regime': trend_regime,
                'strength': abs(avg_trend),
                'short_term_trend': short_term,
                'medium_term_trend': medium_term,
                'long_term_trend': long_term,
                'confidence': confidence
            }
            
        except Exception as e:
            self.logger.error(f"❌ 트렌드 체제 분석 실패: {e}")
            return {'regime': 'SIDEWAYS', 'confidence': 50}
    
    async def _analyze_volume_regime(self, market_data: List[Dict]) -> Dict:
        """거래량 체제 분석"""
        try:
            if not market_data:
                return {'regime': 'NORMAL', 'confidence': 50}
            
            volumes = [item.get('volume', 0) for item in market_data[-20:]]
            if not volumes:
                return {'regime': 'NORMAL', 'confidence': 50}
            
            avg_volume = np.mean(volumes)
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            volume_regime = self._categorize_volume(volume_ratio)
            
            # 거래량 트렌드
            if len(volumes) >= 5:
                recent_avg = np.mean(volumes[-5:])
                earlier_avg = np.mean(volumes[-10:-5]) if len(volumes) >= 10 else avg_volume
                volume_trend = 'INCREASING' if recent_avg > earlier_avg * 1.1 else 'STABLE'
            else:
                volume_trend = 'STABLE'
            
            confidence = min(90, max(50, 100 - abs(volume_ratio - 1.0) * 50))
            
            return {
                'regime': volume_regime,
                'volume_ratio': volume_ratio,
                'trend': volume_trend,
                'confidence': confidence
            }
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 체제 분석 실패: {e}")
            return {'regime': 'NORMAL', 'confidence': 50}
    
    async def _analyze_market_breadth(self, individual_stocks: List[Dict]) -> Dict:
        """시장 폭 분석"""
        try:
            if not individual_stocks:
                return {'breadth_score': 50, 'advancing_ratio': 0.5}
            
            advancing_stocks = len([s for s in individual_stocks if s.get('change_rate', 0) > 0])
            total_stocks = len(individual_stocks)
            
            advancing_ratio = advancing_stocks / total_stocks if total_stocks > 0 else 0.5
            breadth_score = advancing_ratio * 100
            
            return {
                'breadth_score': breadth_score,
                'advancing_ratio': advancing_ratio,
                'advancing_stocks': advancing_stocks,
                'declining_stocks': total_stocks - advancing_stocks,
                'breadth_momentum': 'POSITIVE' if advancing_ratio > 0.6 else 'NEGATIVE' if advancing_ratio < 0.4 else 'NEUTRAL'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 시장 폭 분석 실패: {e}")
            return {'breadth_score': 50, 'advancing_ratio': 0.5}
    
    async def _ai_regime_classification(self, market_state: MarketState, 
                                      volatility_regime: Dict, trend_regime: Dict,
                                      volume_regime: Dict, breadth_analysis: Dict) -> Dict:
        """AI 기반 체제 분류"""
        try:
            # Gemini AI를 통한 종합 분석
            analysis_prompt = f"""
            다음 시장 데이터를 바탕으로 현재 시장 체제를 분석해주세요:
            
            변동성: {volatility_regime['regime']} (신뢰도: {volatility_regime['confidence']:.1f}%)
            트렌드: {trend_regime['regime']} (강도: {trend_regime.get('strength', 0):.2f})
            거래량: {volume_regime['regime']} (비율: {volume_regime.get('volume_ratio', 1.0):.2f})
            시장 폭: {breadth_analysis.get('breadth_score', 50):.1f}점
            
            다음 형식으로 답변해주세요:
            {{
                "primary_regime": "BULL_TREND/BEAR_TREND/SIDEWAYS/HIGH_VOLATILITY/LOW_VOLATILITY",
                "secondary_regime": "STRONG/MODERATE/WEAK",
                "confidence": 85,
                "key_indicators": ["지표1", "지표2", "지표3"],
                "risk_factors": ["리스크1", "리스크2"],
                "expected_duration": 14
            }}
            """
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(analysis_prompt)
            
            return ai_result if ai_result else self._create_default_regime_assessment()
            
        except Exception as e:
            self.logger.error(f"❌ AI 체제 분류 실패: {e}")
            return self._create_default_regime_assessment()
    
    def _calculate_trend(self, market_data: List[Dict], period: int) -> float:
        """트렌드 계산"""
        try:
            if len(market_data) < period:
                return 0.0
            
            recent_data = market_data[-period:]
            price_changes = [item.get('change_rate', 0) for item in recent_data]
            
            return sum(price_changes) / len(price_changes) if price_changes else 0.0
            
        except Exception:
            return 0.0
    
    def _categorize_volatility(self, volatility: float) -> str:
        """변동성 분류"""
        thresholds = self.regime_thresholds['volatility']
        
        if volatility <= thresholds['very_low']:
            return 'VERY_LOW'
        elif volatility <= thresholds['low']:
            return 'LOW'
        elif volatility <= thresholds['medium']:
            return 'MEDIUM'
        elif volatility <= thresholds['high']:
            return 'HIGH'
        else:
            return 'VERY_HIGH'
    
    def _categorize_volume(self, volume_ratio: float) -> str:
        """거래량 분류"""
        thresholds = self.regime_thresholds['volume']
        
        if volume_ratio <= thresholds['low']:
            return 'LOW'
        elif volume_ratio <= thresholds['normal']:
            return 'NORMAL'
        elif volume_ratio <= thresholds['high']:
            return 'HIGH'
        else:
            return 'SURGE'
    
    def _create_default_market_state(self) -> MarketState:
        """기본 시장 상태 생성"""
        return MarketState(
            volatility_level='MEDIUM',
            trend_strength=0.0,
            volume_regime='NORMAL',
            breadth_indicator=50.0,
            momentum_score=0.0,
            fear_greed_index=50.0,
            correlation_level=0.6,
            timestamp=datetime.now()
        )
    
    def _create_default_regime(self) -> MarketRegime:
        """기본 체제 생성"""
        return MarketRegime(
            regime_type='SIDEWAYS',
            sub_regime='MODERATE',
            confidence=60.0,
            start_date=datetime.now(),
            duration_days=0,
            expected_duration=30,
            key_indicators=['데이터 부족'],
            recommended_strategies=['momentum', 'eod'],
            risk_factors=['불확실한 시장 상황'],
            market_characteristics={'volatility': 'MEDIUM', 'trend': 'NEUTRAL'},
            transition_probability={'BULL_TREND': 0.3, 'BEAR_TREND': 0.3, 'SIDEWAYS': 0.4}
        )
    
    def _create_default_regime_assessment(self) -> Dict:
        """기본 체제 평가 생성"""
        return {
            'primary_regime': 'SIDEWAYS',
            'secondary_regime': 'MODERATE',
            'confidence': 60,
            'key_indicators': ['데이터 부족'],
            'risk_factors': ['불확실성'],
            'expected_duration': 30
        }
    
    # 추가 헬퍼 메서드들 (간단한 구현)
    async def _calculate_transition_probabilities(self, regime_assessment: Dict, market_state: MarketState) -> Dict:
        return {'BULL_TREND': 0.3, 'BEAR_TREND': 0.3, 'SIDEWAYS': 0.4}
    
    async def _determine_final_regime(self, assessment: Dict, probabilities: Dict, market_state: MarketState) -> MarketRegime:
        regime_type = assessment.get('primary_regime', 'SIDEWAYS')
        return MarketRegime(
            regime_type=regime_type,
            sub_regime=assessment.get('secondary_regime', 'MODERATE'),
            confidence=assessment.get('confidence', 60),
            start_date=datetime.now(),
            duration_days=0,
            expected_duration=assessment.get('expected_duration', 30),
            key_indicators=assessment.get('key_indicators', []),
            recommended_strategies=self.regime_strategies.get(regime_type, ['momentum']),
            risk_factors=assessment.get('risk_factors', []),
            market_characteristics={'volatility': market_state.volatility_level},
            transition_probability=probabilities
        )
    
    def _update_regime_history(self, regime: MarketRegime):
        """체제 기록 업데이트"""
        self.regime_history.append(regime)
        self.current_regime = regime
    
    # 추가 메서드들 (간단한 구현)
    async def _analyze_leading_indicators(self, indicators: Dict) -> Dict:
        return {'signal_strength': 60, 'direction': 'NEUTRAL'}
    
    async def _analyze_historical_transitions(self) -> Dict:
        return {'average_duration': 30, 'common_patterns': []}
    
    async def _ai_transition_prediction(self, current_regime: MarketRegime, leading: Dict, historical: Dict) -> Dict:
        return {'transition_probability': 0.3, 'most_likely_target': 'BULL_TREND'}
    
    async def _generate_transition_scenarios(self, current_regime: MarketRegime, ai_analysis: Dict) -> List[RegimeTransition]:
        return [
            RegimeTransition(
                from_regime=current_regime.regime_type,
                to_regime='BULL_TREND',
                transition_date=datetime.now() + timedelta(days=7),
                transition_strength=60.0,
                catalyst='긍정적 시장 신호',
                confirmation_indicators=['거래량 증가', '변동성 감소'],
                expected_impact='POSITIVE'
            )
        ]
    
    def _categorize_stability(self, confidence: float) -> str:
        if confidence >= 80:
            return 'VERY_STABLE'
        elif confidence >= 60:
            return 'STABLE'
        elif confidence >= 40:
            return 'MODERATE'
        else:
            return 'UNSTABLE'
    
    def _get_adaptation_frequency(self, regime: MarketRegime) -> str:
        if regime.confidence < 60:
            return 'DAILY'
        elif regime.confidence < 80:
            return 'WEEKLY'
        else:
            return 'MONTHLY'
    
    def _get_monitoring_frequency(self, confidence: float) -> str:
        if confidence < 50:
            return 'HOURLY'
        elif confidence < 70:
            return 'DAILY'
        else:
            return 'WEEKLY'
    
    def _calculate_confidence_trend(self) -> str:
        return 'STABLE'  # 간단한 구현
    
    # 추가 구현 필요한 메서드들
    async def _get_regime_position_sizing(self, regime: MarketRegime, portfolio: Dict) -> Dict:
        return {'recommendation': 'MODERATE', 'max_single_position': 0.10}
    
    async def _get_regime_risk_management(self, regime: MarketRegime, portfolio: Dict) -> Dict:
        return {'stop_loss_tightness': 'NORMAL', 'position_limits': 'STANDARD'}
    
    async def _get_regime_timing_advice(self, regime: MarketRegime) -> Dict:
        return {'optimal_entry_time': '장 초반', 'optimal_exit_time': '장 마감 전'}
    
    async def _ai_regime_recommendations(self, regime: MarketRegime, portfolio: Dict) -> Dict:
        return {'key_advice': '현재 체제 유지', 'attention_points': ['변동성 모니터링']}
    
    async def _analyze_regime_duration(self, regime: MarketRegime) -> Dict:
        return {'status': 'NORMAL', 'expected_remaining': 20}
    
    async def _analyze_regime_strength_changes(self, regime: MarketRegime, data: List[Dict]) -> Dict:
        return {'strength_trend': 'STABLE', 'change_rate': 0}
    
    async def _detect_instability_signals(self, regime: MarketRegime, data: List[Dict]) -> List[str]:
        return []
    
    async def _update_regime_confidence(self, regime: MarketRegime, duration: Dict, strength: Dict, signals: List[str]) -> float:
        return max(30, regime.confidence - len(signals) * 5)