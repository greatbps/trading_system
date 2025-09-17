#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/multi_timeframe_analyzer.py

다중 시간대 분석 시스템 - 여러 시간대에서의 종합적 시장 분석
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger


class TimeframeSignal(Enum):
    """시간대별 신호"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    NEUTRAL = "neutral"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TrendDirection(Enum):
    """트렌드 방향"""
    STRONG_UPTREND = "strong_uptrend"
    UPTREND = "uptrend"
    WEAK_UPTREND = "weak_uptrend"
    SIDEWAYS = "sideways"
    WEAK_DOWNTREND = "weak_downtrend"
    DOWNTREND = "downtrend"
    STRONG_DOWNTREND = "strong_downtrend"


@dataclass
class TimeframeAnalysis:
    """시간대별 분석 결과"""
    timeframe: str
    signal: TimeframeSignal
    trend_direction: TrendDirection
    trend_strength: float  # 0.0 - 1.0
    momentum_score: float  # -1.0 to 1.0
    volatility_score: float  # 0.0 - 1.0
    volume_score: float  # 0.0 - 1.0
    support_resistance: Dict[str, float]
    key_levels: List[float]
    confidence: float  # 0.0 - 1.0
    reasoning: List[str]


@dataclass
class MultiTimeframeSignal:
    """다중 시간대 종합 신호"""
    overall_signal: TimeframeSignal
    primary_trend: TrendDirection
    trend_alignment: float  # 시간대 간 트렌드 정렬도
    momentum_consensus: float  # 모멘텀 합의도
    risk_level: str  # LOW, MEDIUM, HIGH
    entry_timing: str  # IMMEDIATE, WAIT, AVOID
    position_sizing_factor: float  # 포지션 크기 조정 팩터
    timeframe_analyses: List[TimeframeAnalysis]
    composite_confidence: float
    recommendation: str


class MultiTimeframeAnalyzer:
    """다중 시간대 분석기"""
    
    def __init__(self, config, data_collector):
        self.config = config
        self.data_collector = data_collector
        self.logger = get_logger("MultiTimeframeAnalyzer")
        
        # 분석할 시간대들
        self.timeframes = {
            '15m': {'period': '1M', 'weight': 0.15, 'name': '15분봉'},
            '1H': {'period': '3M', 'weight': 0.25, 'name': '1시간봉'},
            '4H': {'period': '6M', 'weight': 0.30, 'name': '4시간봉'},
            '1D': {'period': '1Y', 'weight': 0.30, 'name': '일봉'}
        }
        
        # 기술적 지표 파라미터
        self.sma_periods = [10, 20, 50]
        self.ema_periods = [12, 26]
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        
        # 임계값 설정
        self.trend_strength_threshold = 0.6
        self.momentum_threshold = 0.3
        self.alignment_threshold = 0.7
        
        self.logger.info("📊 다중 시간대 분석기 초기화 완료")
    
    async def analyze_symbol(self, symbol: str, use_fallback_data: bool = False) -> MultiTimeframeSignal:
        """심볼에 대한 다중 시간대 분석"""
        try:
            self.logger.info(f"🔍 {symbol} 다중 시간대 분석 시작")
            
            timeframe_analyses = []
            
            # 각 시간대별 분석
            for timeframe, config in self.timeframes.items():
                try:
                    if use_fallback_data:
                        # 폴백 데이터 사용 (기본 종목들)
                        analysis = await self._analyze_timeframe_with_fallback(symbol, timeframe, config)
                    else:
                        # 정상적인 데이터 수집
                        analysis = await self._analyze_timeframe(symbol, timeframe, config)
                    
                    if analysis:
                        timeframe_analyses.append(analysis)
                        self.logger.debug(f"✅ {symbol} {timeframe} 분석 완료: {analysis.signal.value}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} {timeframe} 분석 실패: {e}")
                    # 실패 시 기본 분석 추가
                    fallback_analysis = self._create_fallback_analysis(timeframe, config)
                    timeframe_analyses.append(fallback_analysis)
            
            # 종합 신호 생성
            composite_signal = await self._generate_composite_signal(timeframe_analyses)
            
            self.logger.info(f"✅ {symbol} 다중 시간대 분석 완료: {composite_signal.overall_signal.value}")
            
            return composite_signal
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 다중 시간대 분석 실패: {e}")
            return self._create_fallback_composite_signal()
    
    async def _analyze_timeframe(self, symbol: str, timeframe: str, tf_config: Dict) -> TimeframeAnalysis:
        """특정 시간대 분석"""
        try:
            # 가격 데이터 수집
            price_data = await self.data_collector.get_historical_data(
                symbol, period=tf_config['period'], interval=timeframe
            )
            
            if not price_data or len(price_data) < 50:
                self.logger.warning(f"⚠️ {symbol} {timeframe} 데이터 부족")
                return self._create_fallback_analysis(timeframe, tf_config)
            
            return await self._perform_timeframe_analysis(price_data, timeframe, tf_config)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} {timeframe} 분석 실패: {e}")
            return self._create_fallback_analysis(timeframe, tf_config)
    
    async def _analyze_timeframe_with_fallback(self, symbol: str, timeframe: str, tf_config: Dict) -> TimeframeAnalysis:
        """폴백 데이터를 사용한 시간대 분석"""
        try:
            # 기본 종목들 중 하나 사용 (예: 삼성전자)
            fallback_symbols = ['005930', '000660', '035420', '051910', '005490']
            
            for fallback_symbol in fallback_symbols:
                try:
                    price_data = await self.data_collector.get_historical_data(
                        fallback_symbol, period=tf_config['period'], interval=timeframe
                    )
                    
                    if price_data and len(price_data) >= 50:
                        self.logger.debug(f"📊 {symbol} 대신 {fallback_symbol} 데이터로 {timeframe} 분석")
                        analysis = await self._perform_timeframe_analysis(price_data, timeframe, tf_config)
                        # 신뢰도를 낮춤 (폴백 데이터 사용)
                        analysis.confidence *= 0.7
                        analysis.reasoning.append(f"폴백 데이터 사용 ({fallback_symbol})")
                        return analysis
                        
                except Exception as e:
                    continue
            
            # 모든 폴백 시도 실패 시 기본 분석
            return self._create_fallback_analysis(timeframe, tf_config)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} {timeframe} 폴백 분석 실패: {e}")
            return self._create_fallback_analysis(timeframe, tf_config)
    
    async def _perform_timeframe_analysis(self, price_data: List[Dict], timeframe: str, tf_config: Dict) -> TimeframeAnalysis:
        """실제 시간대 분석 수행"""
        try:
            closes = np.array([float(item['close']) for item in price_data])
            highs = np.array([float(item['high']) for item in price_data])
            lows = np.array([float(item['low']) for item in price_data])
            volumes = np.array([float(item['volume']) for item in price_data])
            
            # 1. 트렌드 분석
            trend_direction, trend_strength = self._analyze_trend(closes)
            
            # 2. 모멘텀 분석
            momentum_score = self._calculate_momentum(closes, volumes)
            
            # 3. 변동성 분석
            volatility_score = self._calculate_volatility_score(closes)
            
            # 4. 거래량 분석
            volume_score = self._analyze_volume(volumes, closes)
            
            # 5. 지지/저항 레벨 계산
            support_resistance = self._calculate_support_resistance(highs, lows, closes)
            
            # 6. 주요 레벨 식별
            key_levels = self._identify_key_levels(highs, lows, closes)
            
            # 7. 시간대별 신호 생성
            signal = self._generate_timeframe_signal(
                trend_direction, trend_strength, momentum_score, volatility_score
            )
            
            # 8. 신뢰도 계산
            confidence = self._calculate_timeframe_confidence(
                trend_strength, momentum_score, len(price_data)
            )
            
            # 9. 추론 생성
            reasoning = self._generate_timeframe_reasoning(
                trend_direction, trend_strength, momentum_score, volatility_score, volume_score
            )
            
            return TimeframeAnalysis(
                timeframe=timeframe,
                signal=signal,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                volume_score=volume_score,
                support_resistance=support_resistance,
                key_levels=key_levels,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            self.logger.error(f"❌ {timeframe} 분석 수행 실패: {e}")
            return self._create_fallback_analysis(timeframe, tf_config)
    
    def _analyze_trend(self, closes: np.ndarray) -> Tuple[TrendDirection, float]:
        """트렌드 분석"""
        try:
            # 다양한 기간의 이동평균 계산
            sma_10 = np.convolve(closes, np.ones(10), 'valid') / 10
            sma_20 = np.convolve(closes, np.ones(20), 'valid') / 20
            sma_50 = np.convolve(closes, np.ones(50), 'valid') / 50
            
            current_price = closes[-1]
            
            # 이동평균과의 위치 관계
            above_sma10 = current_price > sma_10[-1] if len(sma_10) > 0 else False
            above_sma20 = current_price > sma_20[-1] if len(sma_20) > 0 else False
            above_sma50 = current_price > sma_50[-1] if len(sma_50) > 0 else False
            
            # 이동평균 정렬 상태
            mas_aligned_up = False
            mas_aligned_down = False
            
            if len(sma_10) > 0 and len(sma_20) > 0 and len(sma_50) > 0:
                mas_aligned_up = sma_10[-1] > sma_20[-1] > sma_50[-1]
                mas_aligned_down = sma_10[-1] < sma_20[-1] < sma_50[-1]
            
            # 가격 모멘텀
            short_momentum = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
            long_momentum = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
            
            # 트렌드 강도 계산
            bullish_signals = sum([above_sma10, above_sma20, above_sma50, mas_aligned_up, short_momentum > 0, long_momentum > 0])
            bearish_signals = sum([not above_sma10, not above_sma20, not above_sma50, mas_aligned_down, short_momentum < 0, long_momentum < 0])
            
            trend_strength = abs(bullish_signals - bearish_signals) / 6.0
            
            # 트렌드 방향 결정
            if bullish_signals >= 5:
                trend_direction = TrendDirection.STRONG_UPTREND
            elif bullish_signals >= 4:
                trend_direction = TrendDirection.UPTREND
            elif bullish_signals >= 3:
                trend_direction = TrendDirection.WEAK_UPTREND
            elif bearish_signals >= 5:
                trend_direction = TrendDirection.STRONG_DOWNTREND
            elif bearish_signals >= 4:
                trend_direction = TrendDirection.DOWNTREND
            elif bearish_signals >= 3:
                trend_direction = TrendDirection.WEAK_DOWNTREND
            else:
                trend_direction = TrendDirection.SIDEWAYS
            
            return trend_direction, trend_strength
            
        except Exception as e:
            self.logger.error(f"❌ 트렌드 분석 실패: {e}")
            return TrendDirection.SIDEWAYS, 0.5
    
    def _calculate_momentum(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """모멘텀 계산"""
        try:
            # RSI 계산
            rsi = self._calculate_rsi(closes)
            rsi_momentum = (rsi[-1] - 50) / 50 if len(rsi) > 0 else 0
            
            # 가격 모멘텀
            price_momentum = 0
            if len(closes) >= 14:
                price_momentum = (closes[-1] - closes[-14]) / closes[-14]
            
            # 거래량 가중 모멘텀
            volume_weighted_momentum = 0
            if len(closes) >= 10 and len(volumes) >= 10:
                recent_avg_volume = np.mean(volumes[-5:])
                historical_avg_volume = np.mean(volumes[-20:-5]) if len(volumes) >= 20 else np.mean(volumes[:-5])
                volume_ratio = recent_avg_volume / (historical_avg_volume + 1e-10)
                volume_weighted_momentum = price_momentum * min(volume_ratio, 2.0)
            
            # 종합 모멘텀
            momentum_score = (rsi_momentum * 0.3 + price_momentum * 0.4 + volume_weighted_momentum * 0.3)
            
            return np.clip(momentum_score, -1.0, 1.0)
            
        except Exception as e:
            self.logger.error(f"❌ 모멘텀 계산 실패: {e}")
            return 0.0
    
    def _calculate_volatility_score(self, closes: np.ndarray) -> float:
        """변동성 점수 계산"""
        try:
            if len(closes) < 20:
                return 0.5
            
            # 가격 변화율
            returns = np.diff(np.log(closes))
            
            # 현재 변동성
            current_volatility = np.std(returns[-10:]) if len(returns) >= 10 else np.std(returns)
            
            # 역사적 변동성
            historical_volatility = np.std(returns)
            
            # 변동성 비율
            volatility_ratio = current_volatility / (historical_volatility + 1e-10)
            
            # 0-1 스케일로 변환
            volatility_score = min(volatility_ratio / 2.0, 1.0)
            
            return volatility_score
            
        except Exception as e:
            self.logger.error(f"❌ 변동성 계산 실패: {e}")
            return 0.5
    
    def _analyze_volume(self, volumes: np.ndarray, closes: np.ndarray) -> float:
        """거래량 분석"""
        try:
            if len(volumes) < 20:
                return 0.5
            
            # 평균 거래량 비교
            recent_avg_volume = np.mean(volumes[-5:])
            historical_avg_volume = np.mean(volumes[:-5])
            volume_ratio = recent_avg_volume / (historical_avg_volume + 1e-10)
            
            # 가격-거래량 관계
            price_changes = np.diff(closes)
            volume_changes = np.diff(volumes)
            
            if len(price_changes) >= 10 and len(volume_changes) >= 10:
                # 상승시 거래량 증가, 하락시 거래량 감소가 이상적
                up_days = price_changes[-10:] > 0
                down_days = price_changes[-10:] < 0
                
                up_volume_avg = np.mean(volume_changes[-10:][up_days]) if np.any(up_days) else 0
                down_volume_avg = np.mean(volume_changes[-10:][down_days]) if np.any(down_days) else 0
                
                volume_quality = (up_volume_avg - down_volume_avg) / (abs(up_volume_avg) + abs(down_volume_avg) + 1e-10)
            else:
                volume_quality = 0
            
            # 종합 거래량 점수
            volume_score = (min(volume_ratio / 2.0, 1.0) * 0.7 + (volume_quality + 1) / 2 * 0.3)
            
            return np.clip(volume_score, 0.0, 1.0)
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 분석 실패: {e}")
            return 0.5
    
    def _calculate_support_resistance(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Dict[str, float]:
        """지지/저항 레벨 계산"""
        try:
            current_price = closes[-1]
            
            # 최근 고점/저점들
            recent_highs = highs[-20:] if len(highs) >= 20 else highs
            recent_lows = lows[-20:] if len(lows) >= 20 else lows
            
            # 저항선 (현재가 위의 고점들)
            resistance_candidates = recent_highs[recent_highs > current_price]
            resistance = np.min(resistance_candidates) if len(resistance_candidates) > 0 else current_price * 1.05
            
            # 지지선 (현재가 아래의 저점들)
            support_candidates = recent_lows[recent_lows < current_price]
            support = np.max(support_candidates) if len(support_candidates) > 0 else current_price * 0.95
            
            return {
                'support': float(support),
                'resistance': float(resistance),
                'current_price': float(current_price)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 지지/저항 계산 실패: {e}")
            current_price = float(closes[-1]) if len(closes) > 0 else 10000
            return {
                'support': current_price * 0.95,
                'resistance': current_price * 1.05,
                'current_price': current_price
            }
    
    def _identify_key_levels(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> List[float]:
        """주요 레벨 식별"""
        try:
            key_levels = []
            
            # 최근 중요한 고점/저점들
            if len(highs) >= 10:
                # 지역 최대값 찾기
                for i in range(5, len(highs) - 5):
                    if all(highs[i] >= highs[i-j] and highs[i] >= highs[i+j] for j in range(1, 6)):
                        key_levels.append(float(highs[i]))
            
            if len(lows) >= 10:
                # 지역 최소값 찾기
                for i in range(5, len(lows) - 5):
                    if all(lows[i] <= lows[i-j] and lows[i] <= lows[i+j] for j in range(1, 6)):
                        key_levels.append(float(lows[i]))
            
            # 중복 제거 및 정렬
            key_levels = sorted(list(set(key_levels)))
            
            # 현재 가격 근처의 레벨들만 선택
            current_price = closes[-1]
            relevant_levels = [level for level in key_levels 
                             if abs(level - current_price) / current_price < 0.1]
            
            return relevant_levels[:5]  # 최대 5개
            
        except Exception as e:
            self.logger.error(f"❌ 주요 레벨 식별 실패: {e}")
            return []
    
    def _generate_timeframe_signal(self, trend_direction: TrendDirection, trend_strength: float,
                                 momentum_score: float, volatility_score: float) -> TimeframeSignal:
        """시간대별 신호 생성"""
        try:
            # 강한 상승 트렌드 + 강한 모멘텀
            if trend_direction in [TrendDirection.STRONG_UPTREND] and momentum_score > 0.5:
                return TimeframeSignal.STRONG_BUY
            
            # 상승 트렌드 + 양의 모멘텀
            elif trend_direction in [TrendDirection.UPTREND, TrendDirection.WEAK_UPTREND] and momentum_score > 0.2:
                return TimeframeSignal.BUY if momentum_score > 0.4 else TimeframeSignal.WEAK_BUY
            
            # 강한 하락 트렌드 + 강한 음의 모멘텀
            elif trend_direction in [TrendDirection.STRONG_DOWNTREND] and momentum_score < -0.5:
                return TimeframeSignal.STRONG_SELL
            
            # 하락 트렌드 + 음의 모멘텀
            elif trend_direction in [TrendDirection.DOWNTREND, TrendDirection.WEAK_DOWNTREND] and momentum_score < -0.2:
                return TimeframeSignal.SELL if momentum_score < -0.4 else TimeframeSignal.WEAK_SELL
            
            # 나머지는 중립
            else:
                return TimeframeSignal.NEUTRAL
                
        except Exception as e:
            self.logger.error(f"❌ 시간대 신호 생성 실패: {e}")
            return TimeframeSignal.NEUTRAL
    
    def _calculate_timeframe_confidence(self, trend_strength: float, momentum_score: float, data_length: int) -> float:
        """시간대별 신뢰도 계산"""
        try:
            confidence = 0.5  # 기본 신뢰도
            
            # 트렌드 강도 기여
            confidence += trend_strength * 0.3
            
            # 모멘텀 명확성 기여
            confidence += abs(momentum_score) * 0.2
            
            # 데이터 충분성 기여
            data_quality = min(data_length / 100, 1.0)
            confidence += data_quality * 0.2
            
            return min(1.0, confidence)
            
        except Exception as e:
            self.logger.error(f"❌ 신뢰도 계산 실패: {e}")
            return 0.5
    
    def _generate_timeframe_reasoning(self, trend_direction: TrendDirection, trend_strength: float,
                                    momentum_score: float, volatility_score: float, volume_score: float) -> List[str]:
        """시간대별 추론 생성"""
        reasoning = []
        
        reasoning.append(f"트렌드: {trend_direction.value} (강도: {trend_strength:.2f})")
        reasoning.append(f"모멘텀: {momentum_score:+.2f}")
        reasoning.append(f"변동성: {volatility_score:.2f}")
        reasoning.append(f"거래량: {volume_score:.2f}")
        
        return reasoning
    
    async def _generate_composite_signal(self, timeframe_analyses: List[TimeframeAnalysis]) -> MultiTimeframeSignal:
        """종합 신호 생성"""
        try:
            if not timeframe_analyses:
                return self._create_fallback_composite_signal()
            
            # 가중 평균 계산
            weighted_signals = []
            weighted_trends = []
            weighted_momentum = 0
            total_weight = 0
            
            for analysis in timeframe_analyses:
                weight = self.timeframes.get(analysis.timeframe, {}).get('weight', 0.25)
                
                # 신호를 숫자로 변환
                signal_value = self._signal_to_numeric(analysis.signal)
                weighted_signals.append(signal_value * weight * analysis.confidence)
                
                # 트렌드 강도
                trend_value = self._trend_to_numeric(analysis.trend_direction)
                weighted_trends.append(trend_value * weight * analysis.confidence)
                
                # 모멘텀
                weighted_momentum += analysis.momentum_score * weight * analysis.confidence
                
                total_weight += weight * analysis.confidence
            
            if total_weight == 0:
                return self._create_fallback_composite_signal()
            
            # 종합 점수
            composite_signal_score = sum(weighted_signals) / total_weight
            composite_trend_score = sum(weighted_trends) / total_weight
            composite_momentum = weighted_momentum / total_weight
            
            # 시간대 간 정렬도 계산
            trend_alignment = self._calculate_trend_alignment(timeframe_analyses)
            momentum_consensus = self._calculate_momentum_consensus(timeframe_analyses)
            
            # 최종 신호 결정
            overall_signal = self._numeric_to_signal(composite_signal_score)
            primary_trend = self._numeric_to_trend(composite_trend_score)
            
            # 리스크 레벨 결정
            risk_level = self._determine_risk_level(timeframe_analyses, trend_alignment)
            
            # 진입 타이밍 결정
            entry_timing = self._determine_entry_timing(
                overall_signal, trend_alignment, momentum_consensus
            )
            
            # 포지션 사이징 팩터
            position_sizing_factor = self._calculate_position_sizing_factor(
                composite_signal_score, trend_alignment, momentum_consensus
            )
            
            # 종합 신뢰도
            composite_confidence = np.mean([analysis.confidence for analysis in timeframe_analyses])
            
            # 추천 생성
            recommendation = self._generate_recommendation(
                overall_signal, primary_trend, risk_level, entry_timing
            )
            
            return MultiTimeframeSignal(
                overall_signal=overall_signal,
                primary_trend=primary_trend,
                trend_alignment=trend_alignment,
                momentum_consensus=momentum_consensus,
                risk_level=risk_level,
                entry_timing=entry_timing,
                position_sizing_factor=position_sizing_factor,
                timeframe_analyses=timeframe_analyses,
                composite_confidence=composite_confidence,
                recommendation=recommendation
            )
            
        except Exception as e:
            self.logger.error(f"❌ 종합 신호 생성 실패: {e}")
            return self._create_fallback_composite_signal()
    
    # 헬퍼 메서드들
    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI 계산"""
        try:
            deltas = np.diff(closes)
            gain = np.where(deltas > 0, deltas, 0)
            loss = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.convolve(gain, np.ones(period), 'valid') / period
            avg_loss = np.convolve(loss, np.ones(period), 'valid') / period
            
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return np.array([50])
    
    def _signal_to_numeric(self, signal: TimeframeSignal) -> float:
        """신호를 숫자로 변환"""
        mapping = {
            TimeframeSignal.STRONG_SELL: -1.0,
            TimeframeSignal.SELL: -0.7,
            TimeframeSignal.WEAK_SELL: -0.3,
            TimeframeSignal.NEUTRAL: 0.0,
            TimeframeSignal.WEAK_BUY: 0.3,
            TimeframeSignal.BUY: 0.7,
            TimeframeSignal.STRONG_BUY: 1.0
        }
        return mapping.get(signal, 0.0)
    
    def _trend_to_numeric(self, trend: TrendDirection) -> float:
        """트렌드를 숫자로 변환"""
        mapping = {
            TrendDirection.STRONG_DOWNTREND: -1.0,
            TrendDirection.DOWNTREND: -0.7,
            TrendDirection.WEAK_DOWNTREND: -0.3,
            TrendDirection.SIDEWAYS: 0.0,
            TrendDirection.WEAK_UPTREND: 0.3,
            TrendDirection.UPTREND: 0.7,
            TrendDirection.STRONG_UPTREND: 1.0
        }
        return mapping.get(trend, 0.0)
    
    def _numeric_to_signal(self, value: float) -> TimeframeSignal:
        """숫자를 신호로 변환"""
        if value >= 0.8:
            return TimeframeSignal.STRONG_BUY
        elif value >= 0.5:
            return TimeframeSignal.BUY
        elif value >= 0.2:
            return TimeframeSignal.WEAK_BUY
        elif value <= -0.8:
            return TimeframeSignal.STRONG_SELL
        elif value <= -0.5:
            return TimeframeSignal.SELL
        elif value <= -0.2:
            return TimeframeSignal.WEAK_SELL
        else:
            return TimeframeSignal.NEUTRAL
    
    def _numeric_to_trend(self, value: float) -> TrendDirection:
        """숫자를 트렌드로 변환"""
        if value >= 0.8:
            return TrendDirection.STRONG_UPTREND
        elif value >= 0.5:
            return TrendDirection.UPTREND
        elif value >= 0.2:
            return TrendDirection.WEAK_UPTREND
        elif value <= -0.8:
            return TrendDirection.STRONG_DOWNTREND
        elif value <= -0.5:
            return TrendDirection.DOWNTREND
        elif value <= -0.2:
            return TrendDirection.WEAK_DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _calculate_trend_alignment(self, analyses: List[TimeframeAnalysis]) -> float:
        """트렌드 정렬도 계산"""
        if not analyses:
            return 0.0
        
        trend_values = [self._trend_to_numeric(analysis.trend_direction) for analysis in analyses]
        trend_std = np.std(trend_values)
        alignment = max(0, 1 - trend_std)  # 표준편차가 낮을수록 정렬도 높음
        
        return alignment
    
    def _calculate_momentum_consensus(self, analyses: List[TimeframeAnalysis]) -> float:
        """모멘텀 합의도 계산"""
        if not analyses:
            return 0.0
        
        momentum_values = [analysis.momentum_score for analysis in analyses]
        momentum_std = np.std(momentum_values)
        consensus = max(0, 1 - momentum_std)
        
        return consensus
    
    def _determine_risk_level(self, analyses: List[TimeframeAnalysis], trend_alignment: float) -> str:
        """리스크 레벨 결정"""
        avg_volatility = np.mean([analysis.volatility_score for analysis in analyses])
        
        if trend_alignment < 0.3 or avg_volatility > 0.8:
            return "HIGH"
        elif trend_alignment < 0.6 or avg_volatility > 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _determine_entry_timing(self, signal: TimeframeSignal, trend_alignment: float, momentum_consensus: float) -> str:
        """진입 타이밍 결정"""
        if signal in [TimeframeSignal.STRONG_BUY, TimeframeSignal.STRONG_SELL] and trend_alignment > 0.7:
            return "IMMEDIATE"
        elif signal in [TimeframeSignal.BUY, TimeframeSignal.SELL] and momentum_consensus > 0.6:
            return "IMMEDIATE"
        elif signal == TimeframeSignal.NEUTRAL or trend_alignment < 0.4:
            return "AVOID"
        else:
            return "WAIT"
    
    def _calculate_position_sizing_factor(self, signal_score: float, trend_alignment: float, momentum_consensus: float) -> float:
        """포지션 사이징 팩터 계산"""
        base_factor = abs(signal_score)
        alignment_bonus = trend_alignment * 0.3
        consensus_bonus = momentum_consensus * 0.2
        
        factor = base_factor + alignment_bonus + consensus_bonus
        return min(1.0, factor)
    
    def _generate_recommendation(self, signal: TimeframeSignal, trend: TrendDirection, 
                               risk_level: str, entry_timing: str) -> str:
        """추천 생성"""
        recommendations = {
            (TimeframeSignal.STRONG_BUY, "IMMEDIATE"): "강력 매수 추천 - 즉시 진입",
            (TimeframeSignal.BUY, "IMMEDIATE"): "매수 추천 - 즉시 진입",
            (TimeframeSignal.WEAK_BUY, "WAIT"): "약한 매수 - 진입 시점 대기",
            (TimeframeSignal.STRONG_SELL, "IMMEDIATE"): "강력 매도 추천 - 즉시 진입",
            (TimeframeSignal.SELL, "IMMEDIATE"): "매도 추천 - 즉시 진입",
            (TimeframeSignal.WEAK_SELL, "WAIT"): "약한 매도 - 진입 시점 대기",
            (TimeframeSignal.NEUTRAL, "AVOID"): "중립 - 진입 회피"
        }
        
        key = (signal, entry_timing)
        recommendation = recommendations.get(key, "관망 권장")
        
        if risk_level == "HIGH":
            recommendation += " (고위험)"
        
        return recommendation
    
    def _create_fallback_analysis(self, timeframe: str, tf_config: Dict) -> TimeframeAnalysis:
        """폴백 분석"""
        return TimeframeAnalysis(
            timeframe=timeframe,
            signal=TimeframeSignal.NEUTRAL,
            trend_direction=TrendDirection.SIDEWAYS,
            trend_strength=0.5,
            momentum_score=0.0,
            volatility_score=0.5,
            volume_score=0.5,
            support_resistance={'support': 10000, 'resistance': 11000, 'current_price': 10500},
            key_levels=[10000, 10500, 11000],
            confidence=0.3,
            reasoning=[f"{timeframe} 데이터 부족으로 기본값 사용"]
        )
    
    def _create_fallback_composite_signal(self) -> MultiTimeframeSignal:
        """폴백 종합 신호"""
        fallback_analyses = [
            self._create_fallback_analysis(tf, config) 
            for tf, config in self.timeframes.items()
        ]
        
        return MultiTimeframeSignal(
            overall_signal=TimeframeSignal.NEUTRAL,
            primary_trend=TrendDirection.SIDEWAYS,
            trend_alignment=0.5,
            momentum_consensus=0.5,
            risk_level="MEDIUM",
            entry_timing="AVOID",
            position_sizing_factor=0.5,
            timeframe_analyses=fallback_analyses,
            composite_confidence=0.3,
            recommendation="데이터 부족으로 관망 권장"
        )