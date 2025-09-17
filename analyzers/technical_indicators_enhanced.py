#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/technical_indicators_enhanced.py

강화된 기술적 지표 - Williams %R, VWMA, 기타 매수 신호 지표
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from utils.logger import get_logger


@dataclass
class WilliamsRSignal:
    """Williams %R 매수 신호"""
    current_value: float
    signal_strength: float  # 0-100
    is_oversold: bool
    is_buy_signal: bool
    divergence_detected: bool
    trend_direction: str
    confidence: float
    support_level: float


@dataclass
class VWMASignal:
    """VWMA (Volume Weighted Moving Average) 매수 신호"""
    current_vwma: float
    current_price: float
    price_above_vwma: bool
    vwma_slope: str  # 'rising', 'falling', 'flat'
    volume_support: float  # 거래량 지지도
    signal_strength: float  # 0-100
    is_buy_signal: bool
    confidence: float


@dataclass
class EnhancedTechnicalSignals:
    """종합 기술적 매수 신호"""
    williams_r: WilliamsRSignal
    vwma: VWMASignal
    combined_score: float
    overall_signal: str  # 'STRONG_BUY', 'BUY', 'HOLD', 'SELL'
    confidence: float
    key_factors: List[str]
    risk_factors: List[str]
    timestamp: datetime


class TechnicalIndicatorsEnhanced:
    """강화된 기술적 지표 분석기"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("TechnicalIndicatorsEnhanced")
        
        # Williams %R 파라미터
        self.williams_params = {
            'period': 14,           # 기본 14일
            'oversold_level': -80,  # -80% 이하 과매도
            'overbought_level': -20, # -20% 이상 과매수
            'buy_threshold': -60,   # -60% 돌파 시 매수 신호
            'sell_threshold': -40   # -40% 하향 이탈 시 매도 신호
        }
        
        # VWMA 파라미터
        self.vwma_params = {
            'short_period': 20,     # 단기 VWMA
            'long_period': 50,      # 장기 VWMA
            'volume_threshold': 1.2, # 거래량 임계값 (평균 대비)
            'trend_threshold': 0.5  # 추세 판단 임계값 (%)
        }
        
        self.logger.info("📊 강화된 기술적 지표 분석기 초기화 완료")
    
    async def analyze_williams_r_signals(self, symbol: str, price_data: List[Dict]) -> WilliamsRSignal:
        """Williams %R 매수 신호 분석"""
        try:
            if len(price_data) < self.williams_params['period'] + 10:
                self.logger.warning(f"⚠️ {symbol} Williams %R 분석 - 데이터 부족")
                return self._create_empty_williams_signal()
            
            df = pd.DataFrame(price_data)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            
            # Williams %R 계산
            williams_r = self._calculate_williams_r(df, self.williams_params['period'])
            current_wr = williams_r.iloc[-1]
            
            # 과매도 구간 판단
            is_oversold = current_wr <= self.williams_params['oversold_level']
            
            # 매수 신호 판단
            is_buy_signal = self._detect_williams_buy_signal(williams_r, df)
            
            # 다이버전스 감지
            divergence_detected = await self._detect_williams_divergence(williams_r, df)
            
            # 추세 방향
            trend_direction = self._determine_williams_trend(williams_r)
            
            # 지지선 레벨
            support_level = self._find_williams_support_level(williams_r, df)
            
            # 신호 강도 계산
            signal_strength = self._calculate_williams_signal_strength(
                current_wr, is_oversold, is_buy_signal, divergence_detected, trend_direction
            )
            
            # 신뢰도 계산
            confidence = self._calculate_williams_confidence(
                williams_r, signal_strength, len(price_data)
            )
            
            self.logger.debug(f"📉 {symbol} Williams %R: {current_wr:.1f}% (신호강도: {signal_strength:.1f})")
            
            return WilliamsRSignal(
                current_value=current_wr,
                signal_strength=signal_strength,
                is_oversold=is_oversold,
                is_buy_signal=is_buy_signal,
                divergence_detected=divergence_detected,
                trend_direction=trend_direction,
                confidence=confidence,
                support_level=support_level
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} Williams %R 분석 실패: {e}")
            return self._create_empty_williams_signal()
    
    def _calculate_williams_r(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Williams %R 계산"""
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        
        williams_r = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        
        return williams_r
    
    def _detect_williams_buy_signal(self, williams_r: pd.Series, df: pd.DataFrame) -> bool:
        """Williams %R 매수 신호 감지"""
        try:
            if len(williams_r) < 5:
                return False
            
            current_wr = williams_r.iloc[-1]
            prev_wr = williams_r.iloc[-2]
            
            # 신호 1: 과매도에서 반등
            oversold_bounce = (
                prev_wr <= self.williams_params['oversold_level'] and
                current_wr > self.williams_params['oversold_level']
            )
            
            # 신호 2: -60% 상향 돌파
            breakout_signal = (
                prev_wr <= self.williams_params['buy_threshold'] and
                current_wr > self.williams_params['buy_threshold']
            )
            
            # 신호 3: 상승 추세 중 일시적 하락 후 반등
            recent_trend = williams_r.iloc[-5:].diff().mean()
            temporary_dip = (
                recent_trend > 0 and  # 전체적 상승 추세
                williams_r.iloc[-3] < williams_r.iloc[-4] and  # 일시 하락
                current_wr > williams_r.iloc[-3]  # 반등
            )
            
            return oversold_bounce or breakout_signal or temporary_dip
            
        except Exception:
            return False
    
    async def _detect_williams_divergence(self, williams_r: pd.Series, df: pd.DataFrame) -> bool:
        """Williams %R 다이버전스 감지"""
        try:
            if len(williams_r) < 20:
                return False
            
            # 최근 20일간 가격과 Williams %R의 상관관계 확인
            recent_prices = df['close'].iloc[-20:].values
            recent_wr = williams_r.iloc[-20:].values
            
            # 가격 추세
            price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
            
            # Williams %R 추세
            wr_trend = np.polyfit(range(len(recent_wr)), recent_wr, 1)[0]
            
            # 불리시 다이버전스: 가격 하락, Williams %R 상승 (매수 신호)
            bullish_divergence = price_trend < 0 and wr_trend > 0
            
            # 다이버전스 강도 확인
            if bullish_divergence:
                price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                wr_change = recent_wr[-1] - recent_wr[0]
                
                # 충분한 크기의 다이버전스인지 확인
                return abs(price_change) > 0.02 and abs(wr_change) > 10  # 2% 가격변화, 10포인트 WR변화
            
            return False
            
        except Exception:
            return False
    
    def _determine_williams_trend(self, williams_r: pd.Series) -> str:
        """Williams %R 추세 방향 판단"""
        try:
            if len(williams_r) < 10:
                return 'unknown'
            
            # 최근 10일 추세
            recent_trend = williams_r.iloc[-10:].diff().mean()
            
            if recent_trend > 2:
                return 'strongly_rising'
            elif recent_trend > 0.5:
                return 'rising'
            elif recent_trend > -0.5:
                return 'sideways'
            elif recent_trend > -2:
                return 'falling'
            else:
                return 'strongly_falling'
                
        except Exception:
            return 'unknown'
    
    def _find_williams_support_level(self, williams_r: pd.Series, df: pd.DataFrame) -> float:
        """Williams %R 기준 가격 지지선 찾기"""
        try:
            # Williams %R이 -80% 근처였던 시점들의 가격 찾기
            oversold_mask = williams_r <= -75  # -75% 이하
            oversold_prices = df.loc[oversold_mask, 'close']
            
            if len(oversold_prices) > 0:
                return oversold_prices.quantile(0.8)  # 상위 20% 수준
            else:
                # 최근 저점
                return df['low'].iloc[-20:].min()
                
        except Exception:
            return 0
    
    def _calculate_williams_signal_strength(self, current_wr: float, is_oversold: bool,
                                          is_buy_signal: bool, divergence_detected: bool,
                                          trend_direction: str) -> float:
        """Williams %R 신호 강도 계산"""
        try:
            strength = 0
            
            # 과매도 구간 (30점)
            if is_oversold:
                strength += 30
                if current_wr <= -85:  # 극도 과매도
                    strength += 10
            elif current_wr <= -70:  # 과매도 근처
                strength += 20
            elif current_wr <= -60:  # 중간 수준
                strength += 10
            
            # 매수 신호 (25점)
            if is_buy_signal:
                strength += 25
            
            # 다이버전스 (20점)
            if divergence_detected:
                strength += 20
            
            # 추세 방향 (15점)
            trend_bonus = {
                'strongly_rising': 15,
                'rising': 10,
                'sideways': 5,
                'falling': 0,
                'strongly_falling': -5,
                'unknown': 2
            }
            strength += trend_bonus.get(trend_direction, 0)
            
            # Williams %R 위치에 따른 추가 점수 (10점)
            if -90 <= current_wr <= -80:  # 최적 매수 구간
                strength += 10
            elif -80 <= current_wr <= -70:
                strength += 8
            elif -70 <= current_wr <= -60:
                strength += 5
            elif current_wr >= -30:  # 과매수 구간 페널티
                strength -= 10
            
            return max(0, min(100, strength))
            
        except Exception:
            return 0
    
    def _calculate_williams_confidence(self, williams_r: pd.Series, 
                                     signal_strength: float, data_length: int) -> float:
        """Williams %R 신뢰도 계산"""
        try:
            confidence_factors = []
            
            # 데이터 충분성 (0.3 가중치)
            data_sufficiency = min(1.0, data_length / 50)  # 50일 기준
            confidence_factors.append(data_sufficiency * 0.3)
            
            # 신호 강도 (0.4 가중치)
            signal_confidence = signal_strength / 100
            confidence_factors.append(signal_confidence * 0.4)
            
            # Williams %R 일관성 (0.3 가중치)
            if len(williams_r) >= 5:
                recent_volatility = williams_r.iloc[-5:].std()
                consistency = max(0, 1 - recent_volatility / 30)  # 30포인트 기준
                confidence_factors.append(consistency * 0.3)
            else:
                confidence_factors.append(0.5 * 0.3)
            
            return sum(confidence_factors)
            
        except Exception:
            return 0.5
    
    def _create_empty_williams_signal(self) -> WilliamsRSignal:
        """빈 Williams %R 신호 생성"""
        return WilliamsRSignal(
            current_value=-50,
            signal_strength=0,
            is_oversold=False,
            is_buy_signal=False,
            divergence_detected=False,
            trend_direction='unknown',
            confidence=0.3,
            support_level=0
        )
    
    async def analyze_vwma_signals(self, symbol: str, price_data: List[Dict]) -> VWMASignal:
        """VWMA (Volume Weighted Moving Average) 매수 신호 분석"""
        try:
            if len(price_data) < self.vwma_params['long_period'] + 10:
                self.logger.warning(f"⚠️ {symbol} VWMA 분석 - 데이터 부족")
                return self._create_empty_vwma_signal()
            
            df = pd.DataFrame(price_data)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # VWMA 계산
            vwma_short = self._calculate_vwma(df, self.vwma_params['short_period'])
            vwma_long = self._calculate_vwma(df, self.vwma_params['long_period'])
            
            current_price = df['close'].iloc[-1]
            current_vwma = vwma_short.iloc[-1]
            
            # 가격이 VWMA 위에 있는지
            price_above_vwma = current_price > current_vwma
            
            # VWMA 기울기 판단
            vwma_slope = self._determine_vwma_slope(vwma_short)
            
            # 거래량 지지도
            volume_support = self._calculate_volume_support(df)
            
            # 매수 신호 판단
            is_buy_signal = self._detect_vwma_buy_signal(
                df, vwma_short, vwma_long, price_above_vwma, vwma_slope, volume_support
            )
            
            # 신호 강도 계산
            signal_strength = self._calculate_vwma_signal_strength(
                current_price, current_vwma, price_above_vwma, vwma_slope, 
                volume_support, is_buy_signal, vwma_short, vwma_long
            )
            
            # 신뢰도 계산
            confidence = self._calculate_vwma_confidence(
                signal_strength, volume_support, len(price_data)
            )
            
            self.logger.debug(f"📈 {symbol} VWMA: {current_vwma:.0f} vs 현재가: {current_price:.0f} (신호강도: {signal_strength:.1f})")
            
            return VWMASignal(
                current_vwma=current_vwma,
                current_price=current_price,
                price_above_vwma=price_above_vwma,
                vwma_slope=vwma_slope,
                volume_support=volume_support,
                signal_strength=signal_strength,
                is_buy_signal=is_buy_signal,
                confidence=confidence
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} VWMA 분석 실패: {e}")
            return self._create_empty_vwma_signal()
    
    def _calculate_vwma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """VWMA (Volume Weighted Moving Average) 계산"""
        try:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            price_volume = typical_price * df['volume']
            
            # 롤링 윈도우로 VWMA 계산
            vwma = price_volume.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
            
            return vwma
            
        except Exception as e:
            self.logger.error(f"❌ VWMA 계산 실패: {e}")
            return pd.Series([0] * len(df))
    
    def _determine_vwma_slope(self, vwma: pd.Series) -> str:
        """VWMA 기울기 판단"""
        try:
            if len(vwma) < 5:
                return 'unknown'
            
            # 최근 5일간 기울기
            recent_vwma = vwma.iloc[-5:].dropna()
            if len(recent_vwma) < 3:
                return 'unknown'
            
            slope = np.polyfit(range(len(recent_vwma)), recent_vwma.values, 1)[0]
            slope_percent = slope / recent_vwma.mean() * 100
            
            if slope_percent > self.vwma_params['trend_threshold']:
                return 'rising'
            elif slope_percent < -self.vwma_params['trend_threshold']:
                return 'falling'
            else:
                return 'flat'
                
        except Exception:
            return 'unknown'
    
    def _calculate_volume_support(self, df: pd.DataFrame) -> float:
        """거래량 지지도 계산"""
        try:
            # 평균 거래량 대비 최근 거래량
            avg_volume = df['volume'].iloc[-30:].mean() if len(df) >= 30 else df['volume'].mean()
            recent_volume = df['volume'].iloc[-5:].mean()
            
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            # 거래량 증가 추세
            if len(df) >= 10:
                volume_trend = df['volume'].iloc[-10:].rolling(3).mean()
                trend_strength = (volume_trend.iloc[-1] / volume_trend.iloc[0]) if volume_trend.iloc[0] > 0 else 1.0
            else:
                trend_strength = 1.0
            
            # 지지도 점수 (0-1)
            support_score = min(1.0, (volume_ratio * 0.7 + trend_strength * 0.3))
            
            return support_score
            
        except Exception:
            return 0.5
    
    def _detect_vwma_buy_signal(self, df: pd.DataFrame, vwma_short: pd.Series,
                              vwma_long: pd.Series, price_above_vwma: bool,
                              vwma_slope: str, volume_support: float) -> bool:
        """VWMA 매수 신호 감지"""
        try:
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[-2]
            
            current_vwma = vwma_short.iloc[-1]
            prev_vwma = vwma_short.iloc[-2]
            
            # 신호 1: 가격이 VWMA를 상향 돌파
            price_breakout = (prev_price <= prev_vwma and current_price > current_vwma)
            
            # 신호 2: VWMA 상승 중 + 가격이 VWMA 위 유지
            vwma_rising_support = (vwma_slope == 'rising' and price_above_vwma)
            
            # 신호 3: 단기 VWMA가 장기 VWMA를 상향 돌파 (골든크로스)
            golden_cross = False
            if len(vwma_long) >= 2:
                current_short = vwma_short.iloc[-1]
                current_long = vwma_long.iloc[-1]
                prev_short = vwma_short.iloc[-2]
                prev_long = vwma_long.iloc[-2]
                
                golden_cross = (prev_short <= prev_long and current_short > current_long)
            
            # 신호 4: 거래량 지지 + VWMA 반등
            volume_supported_bounce = (
                volume_support > self.vwma_params['volume_threshold'] and
                vwma_slope in ['rising', 'flat'] and
                current_price > current_vwma * 0.99  # VWMA 근처
            )
            
            return price_breakout or vwma_rising_support or golden_cross or volume_supported_bounce
            
        except Exception:
            return False
    
    def _calculate_vwma_signal_strength(self, current_price: float, current_vwma: float,
                                      price_above_vwma: bool, vwma_slope: str,
                                      volume_support: float, is_buy_signal: bool,
                                      vwma_short: pd.Series, vwma_long: pd.Series) -> float:
        """VWMA 신호 강도 계산"""
        try:
            strength = 0
            
            # 가격 위치 (25점)
            if price_above_vwma:
                price_distance = (current_price - current_vwma) / current_vwma
                if price_distance > 0.05:  # 5% 이상 상회
                    strength += 25
                elif price_distance > 0.02:  # 2% 이상 상회
                    strength += 20
                elif price_distance > 0:
                    strength += 15
            else:
                # 가격이 VWMA 아래 있으면 감점
                price_distance = (current_vwma - current_price) / current_vwma
                if price_distance > 0.05:
                    strength -= 10
                elif price_distance > 0.02:
                    strength -= 5
            
            # VWMA 기울기 (25점)
            slope_scores = {
                'rising': 25,
                'flat': 10,
                'falling': 0,
                'unknown': 5
            }
            strength += slope_scores.get(vwma_slope, 5)
            
            # 거래량 지지 (20점)
            strength += volume_support * 20
            
            # 매수 신호 (20점)
            if is_buy_signal:
                strength += 20
            
            # 단기/장기 VWMA 관계 (10점)
            if len(vwma_long) > 0 and vwma_short.iloc[-1] > vwma_long.iloc[-1]:
                strength += 10
            elif len(vwma_long) > 0 and vwma_short.iloc[-1] < vwma_long.iloc[-1]:
                strength -= 5
            
            return max(0, min(100, strength))
            
        except Exception:
            return 0
    
    def _calculate_vwma_confidence(self, signal_strength: float, 
                                 volume_support: float, data_length: int) -> float:
        """VWMA 신뢰도 계산"""
        try:
            confidence_factors = []
            
            # 신호 강도 (0.4 가중치)
            signal_confidence = signal_strength / 100
            confidence_factors.append(signal_confidence * 0.4)
            
            # 거래량 지지도 (0.4 가중치)
            confidence_factors.append(volume_support * 0.4)
            
            # 데이터 충분성 (0.2 가중치)
            data_sufficiency = min(1.0, data_length / 50)
            confidence_factors.append(data_sufficiency * 0.2)
            
            return sum(confidence_factors)
            
        except Exception:
            return 0.5
    
    def _create_empty_vwma_signal(self) -> VWMASignal:
        """빈 VWMA 신호 생성"""
        return VWMASignal(
            current_vwma=0,
            current_price=0,
            price_above_vwma=False,
            vwma_slope='unknown',
            volume_support=0,
            signal_strength=0,
            is_buy_signal=False,
            confidence=0.3
        )
    
    async def analyze_enhanced_technical_signals(self, symbol: str, 
                                               price_data: List[Dict]) -> EnhancedTechnicalSignals:
        """종합 기술적 매수 신호 분석"""
        try:
            self.logger.info(f"🔧 {symbol} 종합 기술적 분석 시작")
            
            # Williams %R 분석
            williams_r_signal = await self.analyze_williams_r_signals(symbol, price_data)
            
            # VWMA 분석
            vwma_signal = await self.analyze_vwma_signals(symbol, price_data)
            
            # 종합 점수 계산 (Williams %R 60%, VWMA 40%)
            combined_score = (
                williams_r_signal.signal_strength * 0.6 +
                vwma_signal.signal_strength * 0.4
            )
            
            # 전체 신호 결정
            overall_signal = self._determine_overall_signal(
                combined_score, williams_r_signal, vwma_signal
            )
            
            # 종합 신뢰도
            confidence = (
                williams_r_signal.confidence * 0.6 +
                vwma_signal.confidence * 0.4
            )
            
            # 주요 요인
            key_factors = self._extract_key_factors(williams_r_signal, vwma_signal)
            
            # 리스크 요인
            risk_factors = self._extract_risk_factors(williams_r_signal, vwma_signal, combined_score)
            
            result = EnhancedTechnicalSignals(
                williams_r=williams_r_signal,
                vwma=vwma_signal,
                combined_score=combined_score,
                overall_signal=overall_signal,
                confidence=confidence,
                key_factors=key_factors,
                risk_factors=risk_factors,
                timestamp=datetime.now()
            )
            
            self.logger.info(f"✅ {symbol} 종합 기술적 분석 완료 - {overall_signal} (점수: {combined_score:.1f}, 신뢰도: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 종합 기술적 분석 실패: {e}")
            return self._create_empty_enhanced_signals(symbol)
    
    def _determine_overall_signal(self, combined_score: float, 
                                williams_r: WilliamsRSignal, vwma: VWMASignal) -> str:
        """전체 신호 결정"""
        try:
            # 기본 점수 기준
            if combined_score >= 80:
                base_signal = 'STRONG_BUY'
            elif combined_score >= 65:
                base_signal = 'BUY'
            elif combined_score >= 45:
                base_signal = 'HOLD'
            else:
                base_signal = 'SELL'
            
            # 추가 조건 체크
            strong_signals = 0
            
            # Williams %R 강한 매수 신호
            if williams_r.is_buy_signal and williams_r.signal_strength > 70:
                strong_signals += 1
            
            # VWMA 강한 매수 신호
            if vwma.is_buy_signal and vwma.signal_strength > 70:
                strong_signals += 1
            
            # 다이버전스 보너스
            if williams_r.divergence_detected:
                strong_signals += 1
            
            # 강한 신호가 2개 이상이면 한 단계 상향
            if strong_signals >= 2 and base_signal == 'BUY':
                return 'STRONG_BUY'
            elif strong_signals >= 2 and base_signal == 'HOLD':
                return 'BUY'
            
            return base_signal
            
        except Exception:
            return 'HOLD'
    
    def _extract_key_factors(self, williams_r: WilliamsRSignal, vwma: VWMASignal) -> List[str]:
        """주요 요인 추출"""
        factors = []
        
        # Williams %R 요인
        if williams_r.is_oversold:
            factors.append('Williams %R 과매도 구간')
        if williams_r.is_buy_signal:
            factors.append('Williams %R 매수 신호')
        if williams_r.divergence_detected:
            factors.append('Williams %R 불리시 다이버전스')
        
        # VWMA 요인
        if vwma.price_above_vwma and vwma.vwma_slope == 'rising':
            factors.append('VWMA 상승 추세 + 가격 상회')
        if vwma.is_buy_signal:
            factors.append('VWMA 매수 신호')
        if vwma.volume_support > 1.2:
            factors.append('높은 거래량 지지')
        
        return factors[:5]  # 최대 5개
    
    def _extract_risk_factors(self, williams_r: WilliamsRSignal, 
                            vwma: VWMASignal, combined_score: float) -> List[str]:
        """리스크 요인 추출"""
        risks = []
        
        # 낮은 신뢰도
        if williams_r.confidence < 0.6 or vwma.confidence < 0.6:
            risks.append('신호 신뢰도 낮음')
        
        # Williams %R 리스크
        if williams_r.current_value > -30:  # 과매수 구간
            risks.append('Williams %R 과매수 구간')
        
        # VWMA 리스크
        if not vwma.price_above_vwma:
            risks.append('가격이 VWMA 하회')
        
        if vwma.vwma_slope == 'falling':
            risks.append('VWMA 하락 추세')
        
        if vwma.volume_support < 0.8:
            risks.append('거래량 지지 약함')
        
        # 종합 점수 리스크
        if combined_score < 40:
            risks.append('종합 기술적 신호 약함')
        
        return risks[:4]  # 최대 4개
    
    def _create_empty_enhanced_signals(self, symbol: str) -> EnhancedTechnicalSignals:
        """빈 종합 기술적 신호 생성"""
        return EnhancedTechnicalSignals(
            williams_r=self._create_empty_williams_signal(),
            vwma=self._create_empty_vwma_signal(),
            combined_score=0,
            overall_signal='HOLD',
            confidence=0.3,
            key_factors=['분석 실패'],
            risk_factors=['데이터 부족'],
            timestamp=datetime.now()
        )
    
    def get_williams_r_interpretation(self, value: float) -> str:
        """Williams %R 값 해석"""
        if value <= -80:
            return "극도 과매도 - 강한 매수 신호"
        elif value <= -60:
            return "과매도 구간 - 매수 고려"
        elif value <= -40:
            return "중립 하단 - 관망"
        elif value <= -20:
            return "과매수 구간 - 매도 고려"
        else:
            return "극도 과매수 - 강한 매도 신호"
    
    def get_vwma_interpretation(self, signal: VWMASignal) -> str:
        """VWMA 신호 해석"""
        if signal.is_buy_signal and signal.price_above_vwma and signal.vwma_slope == 'rising':
            return "강한 매수 신호 - VWMA 상승 추세 + 가격 돌파"
        elif signal.price_above_vwma and signal.vwma_slope == 'rising':
            return "매수 유지 - 상승 추세 지속"
        elif signal.is_buy_signal:
            return "매수 신호 - 단기적 기회"
        elif not signal.price_above_vwma and signal.vwma_slope == 'falling':
            return "매도 신호 - 하락 추세 + 가격 이탈"
        else:
            return "관망 - 명확한 방향성 부족"