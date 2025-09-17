#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/smart_money_strategy.py

스마트머니 추종 전략 - 세력 매집 감지 + 대장주 발굴 + 고급 기술적 지표 종합
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .base_strategy import BaseStrategy
from utils.logger import get_logger
from analyzers.institutional_flow_analyzer import InstitutionalFlowAnalyzer
from analyzers.technical_indicators_enhanced import TechnicalIndicatorsEnhanced
from analyzers.theme_sector_analyzer import ThemeSectorAnalyzer
from analyzers.gemini_analyzer import GeminiAnalyzer


@dataclass
class SmartMoneySignal:
    """스마트머니 종합 신호"""
    signal_strength: float  # 0-100
    signal_type: str  # 'STRONG_BUY', 'BUY', 'HOLD', 'SELL'
    action: str  # 'BUY', 'HOLD', 'SELL'
    confidence: float  # 0-1
    entry_price: float
    target_price: float
    stop_loss: float
    
    # 세부 분석 결과
    accumulation_analysis: Dict
    williams_r_analysis: Dict
    vwma_analysis: Dict
    theme_analysis: Dict
    ai_insights: Dict
    
    # 매매 조건
    position_size_ratio: float  # 0-1
    hold_period_days: int
    risk_level: str
    
    # 근거 및 리스크
    key_reasons: List[str]
    risk_factors: List[str]
    
    timestamp: datetime


class SmartMoneyStrategy(BaseStrategy):
    """스마트머니 추종 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        self.logger = get_logger("SmartMoneyStrategy")
        
        # 분석기 초기화
        self.institutional_analyzer = InstitutionalFlowAnalyzer(config)
        self.technical_analyzer = TechnicalIndicatorsEnhanced(config)
        self.theme_analyzer = ThemeSectorAnalyzer(config)
        self.gemini_analyzer = GeminiAnalyzer(config)
        
        # 전략 파라미터
        self.strategy_params = {
            # 세력 매집 기준
            'accumulation_threshold': 70,       # 매집 강도 임계값
            'institutional_confidence': 0.7,    # 기관 신뢰도 임계값
            'avg_cost_margin': 0.05,           # 평균 매수가 대비 마진 (5%)
            
            # 기술적 지표 기준
            'williams_r_oversold': -70,        # Williams %R 과매도 기준
            'williams_r_buy_threshold': 60,    # Williams %R 매수 신호 임계값
            'vwma_signal_threshold': 65,       # VWMA 신호 임계값
            'technical_combined_threshold': 70, # 기술적 종합 점수 임계값
            
            # 테마/대장주 기준
            'theme_strength_threshold': 60,    # 테마 강도 임계값
            'leader_score_threshold': 70,      # 대장주 점수 임계값
            'theme_confidence_threshold': 0.6, # 테마 신뢰도 임계값
            
            # 리스크 관리
            'max_position_size': 0.15,         # 최대 포지션 크기 (15%)
            'base_position_size': 0.08,        # 기본 포지션 크기 (8%)
            'stop_loss_ratio': 0.08,           # 기본 손절 비율 (8%)
            'take_profit_ratio': 0.20,         # 기본 익절 비율 (20%)
            
            # AI 강화
            'ai_confidence_threshold': 0.7,    # AI 분석 신뢰도 임계값
            'ai_adjustment_range': 15          # AI 점수 조정 범위
        }
        
        self.logger.info("💰 스마트머니 추종 전략 초기화 완료")
    
    async def generate_signals(self, stock_data: Any, analysis_result: Dict, 
                             price_data: List[Dict] = None) -> Dict[str, Any]:
        """스마트머니 종합 매매 신호 생성"""
        try:
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"💎 {symbol} 스마트머니 분석 시작")
            
            if not price_data or len(price_data) < 30:
                self.logger.warning(f"⚠️ {symbol} 데이터 부족")
                return self._create_empty_signal()
            
            # 1. 세력 매집 분석
            accumulation_signal = await self.institutional_analyzer.detect_institutional_accumulation(
                symbol, price_data
            )
            
            # 2. 고급 기술적 지표 분석
            technical_signals = await self.technical_analyzer.analyze_enhanced_technical_signals(
                symbol, price_data
            )
            
            # 3. 테마/대장주 분석
            theme_analysis = await self._analyze_theme_leadership(symbol, price_data)
            
            # 4. AI 기반 종합 분석
            ai_insights = await self._get_ai_comprehensive_analysis(
                symbol, accumulation_signal, technical_signals, theme_analysis, price_data
            )
            
            # 5. 스마트머니 종합 점수 계산
            comprehensive_score = await self._calculate_comprehensive_score(
                accumulation_signal, technical_signals, theme_analysis, ai_insights
            )
            
            # 6. 매매 신호 생성
            smart_money_signal = await self._generate_smart_money_signal(
                symbol, comprehensive_score, accumulation_signal, technical_signals,
                theme_analysis, ai_insights, price_data
            )
            
            # 7. 리스크 조정 및 최적화
            optimized_signal = await self._optimize_signal_with_risk_management(
                smart_money_signal, stock_data, price_data
            )
            
            self.logger.info(f"✅ {symbol} 스마트머니 분석 완료 - {optimized_signal.signal_type} (강도: {optimized_signal.signal_strength:.1f})")
            
            return self._convert_to_standard_format(optimized_signal)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 스마트머니 분석 실패: {e}")
            return self._create_empty_signal()
    
    def safe_get_attr(self, data, attr_name, default=None):
        """안전한 속성 접근"""
        try:
            if isinstance(data, dict):
                return data.get(attr_name, default)
            else:
                return getattr(data, attr_name, default)
        except (AttributeError, TypeError):
            return default
    
    async def _analyze_theme_leadership(self, symbol: str, price_data: List[Dict]) -> Dict:
        """테마/대장주 분석"""
        try:
            # 간단한 테마 분석 (실제로는 더 복잡한 분석 필요)
            market_data = {symbol: price_data}
            
            # 핫 테마 감지
            themes = await self.theme_analyzer.detect_hot_themes(market_data)
            
            # 해당 종목의 테마 연관성 추정
            symbol_theme = None
            theme_strength = 0
            
            if themes:
                # 첫 번째 테마에 속한다고 가정 (실제로는 더 정교한 분류 필요)
                symbol_theme = themes[0]
                theme_strength = symbol_theme.theme_strength
            
            # 대장주 분석
            leadership_analysis = {
                'is_theme_leader': theme_strength > self.strategy_params['theme_strength_threshold'],
                'theme_strength': theme_strength,
                'theme_name': symbol_theme.theme_name if symbol_theme else 'UNKNOWN',
                'leader_potential': min(100, theme_strength * 0.8),  # 테마 강도의 80%
                'theme_confidence': symbol_theme.confidence if symbol_theme else 0.3
            }
            
            return leadership_analysis
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 테마 분석 실패: {e}")
            return {
                'is_theme_leader': False,
                'theme_strength': 0,
                'theme_name': 'UNKNOWN',
                'leader_potential': 0,
                'theme_confidence': 0.3
            }
    
    async def _get_ai_comprehensive_analysis(self, symbol: str, accumulation_signal, 
                                           technical_signals, theme_analysis: Dict,
                                           price_data: List[Dict]) -> Dict:
        """AI 기반 종합 분석"""
        try:
            current_price = price_data[-1]['close']
            
            # AI 분석을 위한 종합 프롬프트 생성
            analysis_prompt = f"""
다음 주식의 종합적인 투자 분석을 해주세요:

종목: {symbol}
현재가: {current_price:,.0f}원

세력 매집 분석:
- 매집 여부: {accumulation_signal.is_accumulating}
- 매집 강도: {accumulation_signal.accumulation_strength:.1f}/100
- 추정 평균가: {accumulation_signal.estimated_avg_cost:,.0f}원
- 신뢰도: {accumulation_signal.confidence_score:.2f}

기술적 지표:
- Williams %R: {technical_signals.williams_r.current_value:.1f}% (신호: {technical_signals.williams_r.is_buy_signal})
- VWMA 신호: {technical_signals.vwma.is_buy_signal} (강도: {technical_signals.vwma.signal_strength:.1f})
- 종합 점수: {technical_signals.combined_score:.1f}/100

테마/대장주:
- 테마: {theme_analysis.get('theme_name', 'UNKNOWN')}
- 테마 강도: {theme_analysis.get('theme_strength', 0):.1f}
- 대장주 가능성: {theme_analysis.get('leader_potential', 0):.1f}

다음 JSON 형식으로 답변해주세요:
{{
    "overall_assessment": "strong_buy/buy/hold/sell/strong_sell",
    "score_adjustment": -20~+20,
    "target_price_ratio": 1.0~1.5,
    "optimal_entry_timing": "immediate/wait_for_dip/wait_for_breakout",
    "hold_period_recommendation": 5~60,
    "key_strengths": ["강점1", "강점2", "강점3"],
    "major_risks": ["리스크1", "리스크2"],
    "market_timing_score": 0~100,
    "ai_confidence": 0.0~1.0
}}

특별 고려사항:
- 세력 매집 신호의 중요성
- Williams %R과 VWMA의 조합 효과
- 테마주 리더십의 수익성 잠재력
- 현재 시장 환경에서의 적합성
"""
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(analysis_prompt)
            
            if ai_result and isinstance(ai_result, dict):
                # 결과 검증 및 기본값 설정
                validated_result = {
                    'overall_assessment': ai_result.get('overall_assessment', 'hold'),
                    'score_adjustment': max(-20, min(20, ai_result.get('score_adjustment', 0))),
                    'target_price_ratio': max(1.0, min(1.5, ai_result.get('target_price_ratio', 1.15))),
                    'optimal_entry_timing': ai_result.get('optimal_entry_timing', 'immediate'),
                    'hold_period_recommendation': max(5, min(60, ai_result.get('hold_period_recommendation', 14))),
                    'key_strengths': ai_result.get('key_strengths', ['AI 분석 완료'])[:3],
                    'major_risks': ai_result.get('major_risks', ['일반적 시장 리스크'])[:3],
                    'market_timing_score': max(0, min(100, ai_result.get('market_timing_score', 60))),
                    'ai_confidence': max(0.0, min(1.0, ai_result.get('ai_confidence', 0.6)))
                }
                
                return validated_result
            else:
                return self._get_default_ai_analysis()
                
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} AI 종합 분석 실패: {e}")
            return self._get_default_ai_analysis()
    
    def _get_default_ai_analysis(self) -> Dict:
        """기본 AI 분석 결과"""
        return {
            'overall_assessment': 'hold',
            'score_adjustment': 0,
            'target_price_ratio': 1.15,
            'optimal_entry_timing': 'immediate',
            'hold_period_recommendation': 14,
            'key_strengths': ['기본 분석'],
            'major_risks': ['AI 분석 실패'],
            'market_timing_score': 50,
            'ai_confidence': 0.4
        }
    
    async def _calculate_comprehensive_score(self, accumulation_signal, technical_signals,
                                           theme_analysis: Dict, ai_insights: Dict) -> float:
        """종합 점수 계산"""
        try:
            # 가중치 설정
            weights = {
                'accumulation': 0.35,    # 세력 매집 35%
                'technical': 0.30,       # 기술적 지표 30%
                'theme_leadership': 0.20, # 테마/대장주 20%
                'ai_adjustment': 0.15    # AI 조정 15%
            }
            
            # 1. 세력 매집 점수
            accumulation_score = 0
            if accumulation_signal.is_accumulating:
                accumulation_score = accumulation_signal.accumulation_strength
                # 신뢰도 가중
                accumulation_score *= accumulation_signal.confidence_score
            
            # 2. 기술적 지표 점수
            technical_score = technical_signals.combined_score
            
            # 3. 테마/대장주 점수
            theme_score = theme_analysis.get('leader_potential', 0)
            if theme_analysis.get('is_theme_leader', False):
                theme_score += 20  # 대장주 보너스
            
            # 4. AI 조정 점수
            base_score = (
                accumulation_score * weights['accumulation'] +
                technical_score * weights['technical'] +
                theme_score * weights['theme_leadership']
            )
            
            ai_adjustment = ai_insights.get('score_adjustment', 0)
            ai_adjusted_score = base_score + ai_adjustment
            
            # 최종 점수 (0-100 범위)
            final_score = max(0, min(100, ai_adjusted_score))
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"❌ 종합 점수 계산 실패: {e}")
            return 50.0
    
    async def _generate_smart_money_signal(self, symbol: str, comprehensive_score: float,
                                         accumulation_signal, technical_signals,
                                         theme_analysis: Dict, ai_insights: Dict,
                                         price_data: List[Dict]) -> SmartMoneySignal:
        """스마트머니 신호 생성"""
        try:
            current_price = price_data[-1]['close']
            
            # 신호 타입 결정
            if comprehensive_score >= 85:
                signal_type = "STRONG_BUY"
                action = "BUY"
            elif comprehensive_score >= 70:
                signal_type = "BUY"
                action = "BUY"
            elif comprehensive_score >= 55:
                signal_type = "WEAK_BUY"
                action = "HOLD"
            elif comprehensive_score >= 45:
                signal_type = "HOLD"
                action = "HOLD"
            elif comprehensive_score >= 30:
                signal_type = "WEAK_SELL"
                action = "HOLD"
            else:
                signal_type = "SELL"
                action = "SELL"
            
            # 진입가, 목표가, 손절가 계산
            entry_price = current_price
            
            # 세력 평균가 고려
            if accumulation_signal.is_accumulating and accumulation_signal.estimated_avg_cost > 0:
                # 세력 평균가 위에서만 매수
                margin = self.strategy_params['avg_cost_margin']
                min_entry_price = accumulation_signal.estimated_avg_cost * (1 + margin)
                if current_price < min_entry_price:
                    entry_price = min_entry_price
            
            # 목표가 (AI 추천 비율 적용)
            target_ratio = ai_insights.get('target_price_ratio', 1.15)
            target_price = entry_price * target_ratio
            
            # 손절가
            stop_loss_ratio = self.strategy_params['stop_loss_ratio']
            if accumulation_signal.is_accumulating:
                # 세력 평균가를 손절 기준으로 고려
                avg_cost_stop = accumulation_signal.estimated_avg_cost * 0.95
                calculated_stop = entry_price * (1 - stop_loss_ratio)
                stop_loss = max(avg_cost_stop, calculated_stop)
            else:
                stop_loss = entry_price * (1 - stop_loss_ratio)
            
            # 포지션 사이즈 결정
            position_size_ratio = self._calculate_position_size(
                comprehensive_score, accumulation_signal, theme_analysis, ai_insights
            )
            
            # 보유 기간
            hold_period = ai_insights.get('hold_period_recommendation', 14)
            
            # 리스크 레벨
            risk_level = self._assess_risk_level(
                comprehensive_score, accumulation_signal, technical_signals
            )
            
            # 주요 근거
            key_reasons = self._extract_key_reasons(
                accumulation_signal, technical_signals, theme_analysis, ai_insights
            )
            
            # 리스크 요인
            risk_factors = self._extract_risk_factors(
                accumulation_signal, technical_signals, theme_analysis, ai_insights
            )
            
            # 신뢰도 계산
            confidence_factors = [
                accumulation_signal.confidence_score,
                technical_signals.confidence,
                theme_analysis.get('theme_confidence', 0.5),
                ai_insights.get('ai_confidence', 0.6)
            ]
            confidence = np.mean(confidence_factors)
            
            return SmartMoneySignal(
                signal_strength=comprehensive_score,
                signal_type=signal_type,
                action=action,
                confidence=confidence,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                accumulation_analysis={
                    'is_accumulating': accumulation_signal.is_accumulating,
                    'strength': accumulation_signal.accumulation_strength,
                    'avg_cost': accumulation_signal.estimated_avg_cost,
                    'confidence': accumulation_signal.confidence_score
                },
                williams_r_analysis={
                    'current_value': technical_signals.williams_r.current_value,
                    'is_buy_signal': technical_signals.williams_r.is_buy_signal,
                    'signal_strength': technical_signals.williams_r.signal_strength
                },
                vwma_analysis={
                    'is_buy_signal': technical_signals.vwma.is_buy_signal,
                    'signal_strength': technical_signals.vwma.signal_strength,
                    'price_above_vwma': technical_signals.vwma.price_above_vwma
                },
                theme_analysis=theme_analysis,
                ai_insights=ai_insights,
                position_size_ratio=position_size_ratio,
                hold_period_days=hold_period,
                risk_level=risk_level,
                key_reasons=key_reasons,
                risk_factors=risk_factors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 스마트머니 신호 생성 실패: {e}")
            return self._create_empty_smart_money_signal()
    
    def _calculate_position_size(self, comprehensive_score: float, accumulation_signal,
                               theme_analysis: Dict, ai_insights: Dict) -> float:
        """포지션 사이즈 계산"""
        try:
            base_size = self.strategy_params['base_position_size']
            max_size = self.strategy_params['max_position_size']
            
            # 점수 기반 조정
            score_multiplier = comprehensive_score / 80  # 80점 기준
            
            # 세력 매집 보너스
            accumulation_bonus = 0
            if accumulation_signal.is_accumulating:
                accumulation_bonus = (accumulation_signal.accumulation_strength / 100) * 0.05
            
            # 테마 대장주 보너스
            theme_bonus = 0
            if theme_analysis.get('is_theme_leader', False):
                theme_bonus = 0.03
            
            # AI 신뢰도 조정
            ai_confidence = ai_insights.get('ai_confidence', 0.6)
            confidence_multiplier = 0.7 + (ai_confidence * 0.6)  # 0.7 ~ 1.3
            
            # 최종 포지션 사이즈
            position_size = base_size * score_multiplier * confidence_multiplier + accumulation_bonus + theme_bonus
            
            return max(0.02, min(max_size, position_size))  # 2% ~ 최대 사이즈
            
        except Exception:
            return self.strategy_params['base_position_size']
    
    def _assess_risk_level(self, comprehensive_score: float, accumulation_signal, 
                          technical_signals) -> str:
        """리스크 레벨 평가"""
        try:
            risk_factors = 0
            
            # 점수 기반 리스크
            if comprehensive_score < 60:
                risk_factors += 2
            elif comprehensive_score < 70:
                risk_factors += 1
            
            # 매집 신뢰도 리스크
            if not accumulation_signal.is_accumulating:
                risk_factors += 2
            elif accumulation_signal.confidence_score < 0.6:
                risk_factors += 1
            
            # 기술적 지표 리스크
            if technical_signals.confidence < 0.6:
                risk_factors += 1
            
            if technical_signals.williams_r.current_value > -30:  # 과매수 구간
                risk_factors += 1
            
            # 리스크 레벨 결정
            if risk_factors >= 4:
                return "HIGH"
            elif risk_factors >= 2:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception:
            return "MEDIUM"
    
    def _extract_key_reasons(self, accumulation_signal, technical_signals,
                           theme_analysis: Dict, ai_insights: Dict) -> List[str]:
        """주요 매수 근거 추출"""
        reasons = []
        
        # 세력 매집 근거
        if accumulation_signal.is_accumulating:
            reasons.append(f"세력 매집 진행 (강도: {accumulation_signal.accumulation_strength:.0f})")
            if accumulation_signal.estimated_avg_cost > 0:
                reasons.append(f"세력 평균가: {accumulation_signal.estimated_avg_cost:,.0f}원")
        
        # 기술적 지표 근거
        if technical_signals.williams_r.is_buy_signal:
            reasons.append(f"Williams %R 매수 신호 ({technical_signals.williams_r.current_value:.0f}%)")
        
        if technical_signals.vwma.is_buy_signal:
            reasons.append("VWMA 매수 신호 확인")
        
        if technical_signals.williams_r.divergence_detected:
            reasons.append("Williams %R 불리시 다이버전스")
        
        # 테마/대장주 근거
        if theme_analysis.get('is_theme_leader', False):
            theme_name = theme_analysis.get('theme_name', '핫테마')
            reasons.append(f"{theme_name} 대장주 포지션")
        
        # AI 근거
        ai_strengths = ai_insights.get('key_strengths', [])
        reasons.extend(ai_strengths[:2])  # 상위 2개만
        
        return reasons[:5]  # 최대 5개
    
    def _extract_risk_factors(self, accumulation_signal, technical_signals,
                            theme_analysis: Dict, ai_insights: Dict) -> List[str]:
        """리스크 요인 추출"""
        risks = []
        
        # 매집 관련 리스크
        if not accumulation_signal.is_accumulating:
            risks.append("세력 매집 신호 없음")
        elif accumulation_signal.confidence_score < 0.6:
            risks.append("매집 신호 신뢰도 낮음")
        
        # 기술적 지표 리스크
        if technical_signals.williams_r.current_value > -30:
            risks.append("Williams %R 과매수 구간")
        
        if not technical_signals.vwma.price_above_vwma:
            risks.append("가격이 VWMA 하회")
        
        if technical_signals.confidence < 0.6:
            risks.append("기술적 신호 신뢰도 낮음")
        
        # 테마 리스크
        if theme_analysis.get('theme_confidence', 1.0) < 0.6:
            risks.append("테마 신뢰도 부족")
        
        # AI 리스크
        ai_risks = ai_insights.get('major_risks', [])
        risks.extend(ai_risks[:2])  # 상위 2개만
        
        return risks[:4]  # 최대 4개
    
    async def _optimize_signal_with_risk_management(self, signal: SmartMoneySignal,
                                                   stock_data: Any, price_data: List[Dict]) -> SmartMoneySignal:
        """리스크 관리로 신호 최적화"""
        try:
            # 현재가 기준 안전성 체크
            current_price = price_data[-1]['close']
            
            # 과도한 상승 후 진입 리스크 체크
            if len(price_data) >= 10:
                recent_gain = (current_price - price_data[-10]['close']) / price_data[-10]['close']
                if recent_gain > 0.2:  # 10일간 20% 이상 상승
                    signal.risk_factors.append("최근 급등 후 고점 리스크")
                    signal.position_size_ratio *= 0.7  # 포지션 크기 축소
            
            # 거래량 부족 리스크 체크
            recent_volumes = [d['volume'] for d in price_data[-5:]]
            avg_volume = np.mean([d['volume'] for d in price_data[:-5]])
            if np.mean(recent_volumes) < avg_volume * 0.5:  # 거래량 급감
                signal.risk_factors.append("거래량 급감 위험")
                signal.confidence *= 0.8
            
            # 시가총액 고려 (소형주 리스크)
            market_cap = self.safe_get_attr(stock_data, 'market_cap', 0)
            if 0 < market_cap < 1000:  # 1000억 미만
                signal.risk_factors.append("소형주 변동성 위험")
                signal.position_size_ratio *= 0.8
            
            # 최종 신호 강도 재조정
            risk_penalty = len(signal.risk_factors) * 3  # 리스크 1개당 3점 감점
            signal.signal_strength = max(0, signal.signal_strength - risk_penalty)
            
            # 신호 타입 재평가
            if signal.signal_strength < 60 and signal.action == "BUY":
                signal.action = "HOLD"
                signal.signal_type = "HOLD"
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ 신호 최적화 실패: {e}")
            return signal
    
    def _convert_to_standard_format(self, smart_signal: SmartMoneySignal) -> Dict[str, Any]:
        """표준 신호 형식으로 변환"""
        return {
            'signal_strength': smart_signal.signal_strength,
            'signal_type': smart_signal.signal_type,
            'action': smart_signal.action,
            'confidence': smart_signal.confidence,
            'entry_price': smart_signal.entry_price,
            'target_price': smart_signal.target_price,
            'stop_loss': smart_signal.stop_loss,
            'position_size_ratio': smart_signal.position_size_ratio,
            'hold_period_days': smart_signal.hold_period_days,
            'risk_level': smart_signal.risk_level,
            'key_reasons': smart_signal.key_reasons,
            'risk_factors': smart_signal.risk_factors,
            'details': {
                'accumulation_analysis': smart_signal.accumulation_analysis,
                'williams_r_analysis': smart_signal.williams_r_analysis,
                'vwma_analysis': smart_signal.vwma_analysis,
                'theme_analysis': smart_signal.theme_analysis,
                'ai_insights': smart_signal.ai_insights
            },
            'timestamp': smart_signal.timestamp.isoformat()
        }
    
    def _create_empty_signal(self) -> Dict[str, Any]:
        """빈 신호 생성"""
        return {
            'signal_strength': 50.0,
            'signal_type': "HOLD",
            'action': "HOLD", 
            'confidence': 0.5,
            'entry_price': 0,
            'target_price': 0,
            'stop_loss': 0,
            'position_size_ratio': 0.05,
            'hold_period_days': 14,
            'risk_level': "MEDIUM",
            'key_reasons': ['분석 실패'],
            'risk_factors': ['데이터 부족'],
            'details': {},
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_empty_smart_money_signal(self) -> SmartMoneySignal:
        """빈 스마트머니 신호 생성"""
        return SmartMoneySignal(
            signal_strength=50.0,
            signal_type="HOLD",
            action="HOLD",
            confidence=0.5,
            entry_price=0,
            target_price=0,
            stop_loss=0,
            accumulation_analysis={},
            williams_r_analysis={},
            vwma_analysis={},
            theme_analysis={},
            ai_insights={},
            position_size_ratio=0.05,
            hold_period_days=14,
            risk_level="MEDIUM",
            key_reasons=['분석 실패'],
            risk_factors=['데이터 부족'],
            timestamp=datetime.now()
        )
    
    async def calculate_stop_loss(self, stock_data: Dict, entry_price: float) -> float:
        """스마트 손절가 계산"""
        try:
            # 기본 손절 비율
            base_stop_ratio = self.strategy_params['stop_loss_ratio']
            
            # 변동성 고려
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 2)
            volatility = abs(change_rate) / 100
            
            # 변동성에 따른 손절 비율 조정
            adjusted_ratio = base_stop_ratio + (volatility * 2)  # 변동성이 높을수록 손절 폭 확대
            adjusted_ratio = min(0.15, max(0.05, adjusted_ratio))  # 5%~15% 범위
            
            return entry_price * (1 - adjusted_ratio)
            
        except Exception as e:
            self.logger.error(f"❌ 스마트 손절가 계산 실패: {e}")
            return entry_price * 0.92  # 기본 8% 손절
    
    async def calculate_take_profit(self, stock_data: Dict, entry_price: float) -> float:
        """스마트 익절가 계산"""
        try:
            # 기본 익절 비율
            base_profit_ratio = self.strategy_params['take_profit_ratio']
            
            # 시가총액 고려
            market_cap = self.safe_get_attr(stock_data, 'market_cap', 5000)
            
            if market_cap < 1000:  # 소형주
                profit_ratio = base_profit_ratio + 0.10  # 30% 익절
            elif market_cap < 5000:  # 중형주
                profit_ratio = base_profit_ratio + 0.05  # 25% 익절
            else:  # 대형주
                profit_ratio = base_profit_ratio  # 20% 익절
            
            return entry_price * (1 + profit_ratio)
            
        except Exception as e:
            self.logger.error(f"❌ 스마트 익절가 계산 실패: {e}")
            return entry_price * 1.20  # 기본 20% 익절
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """전략 정보 반환"""
        return {
            'name': 'Smart Money Following Strategy',
            'version': '1.0',
            'description': '세력 매집 감지 + Williams %R + VWMA + 테마 대장주 발굴을 결합한 종합 전략',
            'key_features': [
                '세력 자금 흐름 추적',
                '평균 매수가 기반 진입',
                'Williams %R 과매도 매수',
                'VWMA 돌파 확인',
                '테마 대장주 식별',
                'Gemini AI 종합 분석'
            ],
            'risk_level': 'MEDIUM_HIGH',
            'recommended_timeframe': '1-4 weeks',
            'max_position_size': f"{self.strategy_params['max_position_size']*100}%"
        }