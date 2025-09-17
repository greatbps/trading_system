#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 시장 체제 분석기
Market Regime Analysis with AI Integration
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """시장 체제 유형"""
    BULL = "bull"           # 강세장
    BEAR = "bear"           # 약세장
    SIDEWAYS = "sideways"   # 횡보장
    VOLATILE = "volatile"   # 고변동성
    RECOVERY = "recovery"   # 회복장


@dataclass
class MarketRegimeAnalysis:
    """시장 체제 분석 결과"""
    regime: MarketRegime
    confidence: float  # 0.0 ~ 1.0
    volatility: float  # 변동성 수준
    trend_strength: float  # 추세 강도
    risk_level: str  # LOW, MEDIUM, HIGH
    duration_days: int  # 현재 체제 지속 기간
    expected_duration: int  # 예상 지속 기간
    key_indicators: Dict[str, float]
    recommendations: List[str]
    created_at: datetime


class MarketRegimeAnalyzer:
    """AI 기반 시장 체제 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 시장 체제 판단 임계값
        self.thresholds = {
            'bull_trend': 0.15,      # 15% 이상 상승추세
            'bear_trend': -0.15,     # 15% 이상 하락추세
            'high_volatility': 0.25,  # 25% 이상 변동성
            'sideways_range': 0.05,   # 5% 이내 횡보
            'volume_surge': 1.5,      # 평균 거래량 1.5배 이상
        }
        
        # 기술적 지표 가중치
        self.indicator_weights = {
            'price_trend': 0.30,      # 가격 추세
            'volume_analysis': 0.25,   # 거래량 분석
            'volatility': 0.20,       # 변동성
            'momentum': 0.15,         # 모멘텀
            'market_breadth': 0.10    # 시장 폭
        }

    async def analyze_market_regime(
        self, 
        market_data: pd.DataFrame,
        lookback_days: int = 60
    ) -> MarketRegimeAnalysis:
        """종합적인 시장 체제 분석"""
        try:
            self.logger.info("🔍 시장 체제 분석 시작...")
            
            # 1. 기술적 지표 계산
            indicators = await self._calculate_technical_indicators(market_data, lookback_days)
            
            # 2. 각 체제별 점수 계산
            regime_scores = await self._calculate_regime_scores(indicators)
            
            # 3. 최적 시장 체제 결정
            best_regime, confidence = self._determine_best_regime(regime_scores)
            
            # 4. 상세 분석
            analysis_details = await self._analyze_regime_details(
                best_regime, indicators, market_data
            )
            
            # 5. 추천사항 생성
            recommendations = await self._generate_recommendations(
                best_regime, analysis_details
            )
            
            result = MarketRegimeAnalysis(
                regime=best_regime,
                confidence=confidence,
                volatility=analysis_details['volatility'],
                trend_strength=analysis_details['trend_strength'],
                risk_level=analysis_details['risk_level'],
                duration_days=analysis_details['duration_days'],
                expected_duration=analysis_details['expected_duration'],
                key_indicators=indicators,
                recommendations=recommendations,
                created_at=datetime.now()
            )
            
            self.logger.info(
                f"✅ 시장 체제 분석 완료: {best_regime.value.upper()} "
                f"(신뢰도: {confidence:.1%})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 시장 체제 분석 실패: {e}")
            raise

    async def _calculate_technical_indicators(
        self, 
        data: pd.DataFrame, 
        lookback_days: int
    ) -> Dict[str, float]:
        """기술적 지표 계산"""
        try:
            if len(data) < lookback_days:
                lookback_days = len(data)
            
            recent_data = data.tail(lookback_days).copy()
            
            # 가격 관련 지표
            price_change = (recent_data['close'].iloc[-1] / recent_data['close'].iloc[0] - 1)
            sma_20 = recent_data['close'].rolling(20).mean().iloc[-1]
            sma_60 = recent_data['close'].rolling(60).mean().iloc[-1] if len(recent_data) >= 60 else sma_20
            
            # 변동성 지표
            volatility = recent_data['close'].pct_change().std() * np.sqrt(252)
            
            # 거래량 지표  
            avg_volume = recent_data['volume'].mean()
            recent_volume = recent_data['volume'].tail(5).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            # 모멘텀 지표
            rsi = self._calculate_rsi(recent_data['close'])
            macd_signal = self._calculate_macd_signal(recent_data['close'])
            
            # 추세 강도
            trend_strength = abs(price_change)
            price_above_sma20 = 1.0 if recent_data['close'].iloc[-1] > sma_20 else 0.0
            price_above_sma60 = 1.0 if recent_data['close'].iloc[-1] > sma_60 else 0.0
            
            return {
                'price_change_pct': price_change * 100,
                'volatility': volatility,
                'volume_ratio': volume_ratio,
                'rsi': rsi,
                'macd_signal': macd_signal,
                'trend_strength': trend_strength,
                'price_above_sma20': price_above_sma20,
                'price_above_sma60': price_above_sma60,
                'sma20_slope': self._calculate_sma_slope(recent_data['close'], 20),
                'sma60_slope': self._calculate_sma_slope(recent_data['close'], 60)
            }
            
        except Exception as e:
            self.logger.error(f"기술적 지표 계산 실패: {e}")
            return {}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not rsi.empty else 50.0
        except:
            return 50.0

    def _calculate_macd_signal(self, prices: pd.Series) -> float:
        """MACD 신호 계산"""
        try:
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            return (macd.iloc[-1] - signal.iloc[-1]) if len(macd) > 0 else 0.0
        except:
            return 0.0

    def _calculate_sma_slope(self, prices: pd.Series, period: int) -> float:
        """이동평균선 기울기 계산"""
        try:
            if len(prices) < period:
                return 0.0
            sma = prices.rolling(period).mean()
            if len(sma) >= 2:
                return (sma.iloc[-1] / sma.iloc[-2] - 1) * 100
            return 0.0
        except:
            return 0.0

    async def _calculate_regime_scores(self, indicators: Dict[str, float]) -> Dict[MarketRegime, float]:
        """각 시장 체제별 점수 계산"""
        scores = {}
        
        try:
            price_change = indicators.get('price_change_pct', 0)
            volatility = indicators.get('volatility', 0)
            volume_ratio = indicators.get('volume_ratio', 1)
            rsi = indicators.get('rsi', 50)
            trend_strength = indicators.get('trend_strength', 0)
            sma20_slope = indicators.get('sma20_slope', 0)
            sma60_slope = indicators.get('sma60_slope', 0)
            
            # BULL (강세장) 점수
            bull_score = 0.0
            if price_change > self.thresholds['bull_trend'] * 100:  # 15% 이상 상승
                bull_score += 0.4
            if sma20_slope > 0 and sma60_slope > 0:  # 이평선 상승
                bull_score += 0.3
            if rsi > 50:  # RSI 강세
                bull_score += 0.2
            if volume_ratio > self.thresholds['volume_surge']:  # 거래량 증가
                bull_score += 0.1
            
            # BEAR (약세장) 점수
            bear_score = 0.0
            if price_change < self.thresholds['bear_trend'] * 100:  # 15% 이상 하락
                bear_score += 0.4
            if sma20_slope < 0 and sma60_slope < 0:  # 이평선 하락
                bear_score += 0.3
            if rsi < 50:  # RSI 약세
                bear_score += 0.2
            if volume_ratio > self.thresholds['volume_surge']:  # 거래량 증가 (공포 매도)
                bear_score += 0.1
            
            # SIDEWAYS (횡보장) 점수
            sideways_score = 0.0
            if abs(price_change) < self.thresholds['sideways_range'] * 100:  # 5% 이내
                sideways_score += 0.4
            if volatility < 0.15:  # 낮은 변동성
                sideways_score += 0.3
            if 45 < rsi < 55:  # RSI 중립
                sideways_score += 0.2
            if volume_ratio < 1.2:  # 평균 거래량
                sideways_score += 0.1
            
            # VOLATILE (고변동성) 점수
            volatile_score = 0.0
            if volatility > self.thresholds['high_volatility']:  # 25% 이상
                volatile_score += 0.5
            if volume_ratio > 2.0:  # 거래량 급증
                volatile_score += 0.3
            if abs(price_change) > 20:  # 큰 가격 변동
                volatile_score += 0.2
            
            # RECOVERY (회복장) 점수
            recovery_score = 0.0
            if -10 < price_change < 15:  # 점진적 회복
                recovery_score += 0.3
            if rsi > 40 and trend_strength < 0.15:  # 완만한 상승
                recovery_score += 0.3
            if sma20_slope > 0 > sma60_slope:  # 단기 상승, 장기 하락
                recovery_score += 0.4
            
            scores = {
                MarketRegime.BULL: bull_score,
                MarketRegime.BEAR: bear_score,
                MarketRegime.SIDEWAYS: sideways_score,
                MarketRegime.VOLATILE: volatile_score,
                MarketRegime.RECOVERY: recovery_score
            }
            
            return scores
            
        except Exception as e:
            self.logger.error(f"체제 점수 계산 실패: {e}")
            return {regime: 0.0 for regime in MarketRegime}

    def _determine_best_regime(self, scores: Dict[MarketRegime, float]) -> Tuple[MarketRegime, float]:
        """최적 시장 체제 결정"""
        if not scores:
            return MarketRegime.SIDEWAYS, 0.5
        
        best_regime = max(scores.keys(), key=lambda x: scores[x])
        max_score = scores[best_regime]
        confidence = min(max_score * 2, 1.0)  # 점수를 신뢰도로 변환
        
        return best_regime, confidence

    async def _analyze_regime_details(
        self,
        regime: MarketRegime,
        indicators: Dict[str, float],
        market_data: pd.DataFrame
    ) -> Dict:
        """시장 체제 상세 분석"""
        try:
            volatility = indicators.get('volatility', 0.15)
            trend_strength = indicators.get('trend_strength', 0.05)
            
            # 리스크 레벨 결정
            if volatility > 0.3 or regime == MarketRegime.VOLATILE:
                risk_level = "HIGH"
            elif volatility > 0.2 or regime == MarketRegime.BEAR:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            # 체제 지속 기간 추정 (간단한 휴리스틱)
            duration_days = min(len(market_data), 30)  # 최근 30일 기준
            
            expected_duration = {
                MarketRegime.BULL: 90,      # 3개월
                MarketRegime.BEAR: 120,     # 4개월
                MarketRegime.SIDEWAYS: 60,  # 2개월
                MarketRegime.VOLATILE: 30,  # 1개월
                MarketRegime.RECOVERY: 45   # 1.5개월
            }.get(regime, 60)
            
            return {
                'volatility': volatility,
                'trend_strength': trend_strength,
                'risk_level': risk_level,
                'duration_days': duration_days,
                'expected_duration': expected_duration
            }
            
        except Exception as e:
            self.logger.error(f"상세 분석 실패: {e}")
            return {
                'volatility': 0.15,
                'trend_strength': 0.05,
                'risk_level': 'MEDIUM',
                'duration_days': 30,
                'expected_duration': 60
            }

    async def _generate_recommendations(
        self,
        regime: MarketRegime,
        details: Dict
    ) -> List[str]:
        """시장 체제별 매매 추천사항 생성"""
        try:
            recommendations = []
            risk_level = details.get('risk_level', 'MEDIUM')
            
            if regime == MarketRegime.BULL:
                recommendations.extend([
                    "📈 공격적 매수 전략 적용",
                    "🎯 성장주 및 모멘텀 주식 선호",
                    "📊 포지션 사이즈 확대 (계좌의 15-25%)",
                    "⏰ 추세 추종 전략 활용",
                    "💰 단기 차익 실현보다 장기 보유 선호"
                ])
            
            elif regime == MarketRegime.BEAR:
                recommendations.extend([
                    "🛡️ 방어적 전략 적용",
                    "💵 현금 비중 확대 (50-70%)",
                    "📉 숏 포지션 또는 인버스 ETF 고려",
                    "🎯 가치주 및 배당주 선별 매수",
                    "⚡ 빠른 손절 및 리스크 관리 강화"
                ])
            
            elif regime == MarketRegime.SIDEWAYS:
                recommendations.extend([
                    "🔄 레인지 트레이딩 전략",
                    "📊 지지/저항선 기반 매매",
                    "⚖️ 균형잡힌 포트폴리오 구성",
                    "💹 변동성 매매 (Swing Trading)",
                    "🎯 섹터 로테이션 전략 활용"
                ])
            
            elif regime == MarketRegime.VOLATILE:
                recommendations.extend([
                    "⚠️ 포지션 사이즈 축소 (계좌의 5-10%)",
                    "🛡️ 엄격한 손절 설정 (3-5%)",
                    "⏰ 단기 매매 위주",
                    "💰 현금 비중 확대",
                    "📈 변동성 지표 활용"
                ])
            
            elif regime == MarketRegime.RECOVERY:
                recommendations.extend([
                    "🌱 점진적 매수 전략",
                    "🎯 질 좋은 우량주 선별",
                    "📊 분할 매수 적용",
                    "⏳ 중장기 관점 유지",
                    "🔄 리밸런싱 주기적 실행"
                ])
            
            # 리스크 레벨별 공통 추천사항
            if risk_level == "HIGH":
                recommendations.append("🚨 고위험: 포지션 축소 및 엄격한 리스크 관리 필수")
            elif risk_level == "MEDIUM":
                recommendations.append("⚖️ 중위험: 균형잡힌 리스크 관리")
            else:
                recommendations.append("✅ 저위험: 공격적 전략 고려 가능")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"추천사항 생성 실패: {e}")
            return ["⚠️ 신중한 매매 전략 권장"]

    def get_strategy_parameters(self, regime_analysis: MarketRegimeAnalysis) -> Dict:
        """시장 체제별 전략 파라미터 반환"""
        try:
            regime = regime_analysis.regime
            risk_level = regime_analysis.risk_level
            volatility = regime_analysis.volatility
            
            # 기본 파라미터
            params = {
                'max_position_size': 0.15,  # 15%
                'stop_loss_pct': 0.05,      # 5%
                'take_profit_pct': 0.10,    # 10%
                'entry_threshold': 0.7,     # 70%
                'min_confidence': 0.6       # 60%
            }
            
            # 체제별 조정
            if regime == MarketRegime.BULL:
                params.update({
                    'max_position_size': 0.25,  # 25%
                    'stop_loss_pct': 0.08,      # 8%
                    'take_profit_pct': 0.15,    # 15%
                    'entry_threshold': 0.6,     # 60%
                })
            
            elif regime == MarketRegime.BEAR:
                params.update({
                    'max_position_size': 0.08,  # 8%
                    'stop_loss_pct': 0.03,      # 3%
                    'take_profit_pct': 0.06,    # 6%
                    'entry_threshold': 0.8,     # 80%
                })
            
            elif regime == MarketRegime.VOLATILE:
                params.update({
                    'max_position_size': 0.10,  # 10%
                    'stop_loss_pct': 0.04,      # 4%
                    'take_profit_pct': 0.08,    # 8%
                    'entry_threshold': 0.8,     # 80%
                    'min_confidence': 0.7       # 70%
                })
            
            # 변동성 기반 추가 조정
            if volatility > 0.3:  # 고변동성
                params['max_position_size'] *= 0.7
                params['stop_loss_pct'] *= 0.8
            
            return params
            
        except Exception as e:
            self.logger.error(f"전략 파라미터 생성 실패: {e}")
            return {
                'max_position_size': 0.10,
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.08,
                'entry_threshold': 0.7,
                'min_confidence': 0.6
            }