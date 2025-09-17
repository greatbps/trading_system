#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/enhanced_multi_timeframe_strategy.py

향상된 다중 시간대 통합 전략 - 요청하신 모든 시간대 지원
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_strategy import BaseStrategy

class TimeFrame(Enum):
    """시간 프레임 정의"""
    M1 = "1m"   # 1분
    M3 = "3m"   # 3분  
    M5 = "5m"   # 5분
    M15 = "15m" # 15분
    M30 = "30m" # 30분
    H1 = "1h"   # 1시간
    D1 = "1d"   # 일봉

@dataclass
class TimeFrameWeight:
    """시간대별 가중치"""
    frame: TimeFrame
    trend_weight: float      # 추세 분석 가중치
    signal_weight: float     # 신호 생성 가중치
    filter_weight: float     # 필터링 가중치
    description: str

class EnhancedMultiTimeframeStrategy(BaseStrategy):
    """향상된 다중 시간대 통합 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = "EnhancedMultiTimeframeStrategy"
        
        # 시간대별 가중치 설정 (요청하신 조건 반영)
        self.timeframe_weights = {
            TimeFrame.D1: TimeFrameWeight(TimeFrame.D1, 0.35, 0.15, 0.40, "일봉 - 주 추세"),
            TimeFrame.H1: TimeFrameWeight(TimeFrame.H1, 0.30, 0.25, 0.30, "1시간 - 중간 추세"),
            TimeFrame.M30: TimeFrameWeight(TimeFrame.M30, 0.20, 0.30, 0.20, "30분 - 단기 추세"),
            TimeFrame.M15: TimeFrameWeight(TimeFrame.M15, 0.10, 0.20, 0.08, "15분 - 진입 타이밍"),
            TimeFrame.M5: TimeFrameWeight(TimeFrame.M5, 0.03, 0.08, 0.02, "5분 - 정밀 진입"),
            TimeFrame.M3: TimeFrameWeight(TimeFrame.M3, 0.01, 0.02, 0.00, "3분 - 스캘핑"),
            TimeFrame.M1: TimeFrameWeight(TimeFrame.M1, 0.01, 0.00, 0.00, "1분 - 체결")
        }
        
        # 기술적 지표 파라미터 (시간대별 최적화)
        self.indicator_params = {
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26, 
            'macd_signal': 9,
            'ema_short': 20,
            'ema_long': 60,
            'supertrend_period': 10,
            'supertrend_multiplier': 2.5,
            'atr_period': 14,
            'bb_period': 20,
            'bb_std': 2.0
        }
        
        # 매매 조건 임계값
        self.trading_thresholds = {
            'min_trend_alignment': 0.7,    # 최소 추세 정렬도
            'min_signal_strength': 0.6,    # 최소 신호 강도
            'volume_spike_threshold': 1.5,  # 거래량 급증 임계값
            'volatility_threshold': 0.8,    # 변동성 임계값
            'trend_change_threshold': 0.3   # 추세 변화 감지 임계값
        }
        
        self.logger.info("🚀 향상된 다중 시간대 전략 초기화 완료")

    async def generate_signals(self, stock_data: Any, analysis_result: Dict, price_data: Dict = None) -> Dict[str, Any]:
        """다중 시간대 종합 매매 신호 생성"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"📊 {symbol} 다중 시간대 분석 시작")
            
            # 1. 시간대별 데이터 수집 및 분석
            timeframe_analyses = await self._analyze_all_timeframes(symbol, price_data)
            
            if not timeframe_analyses:
                self.logger.warning(f"⚠️ {symbol} 시간대 분석 데이터 부족")
                return self._create_empty_signal()
            
            # 2. 추세 정렬도 분석
            trend_alignment = self._calculate_trend_alignment(timeframe_analyses)
            
            # 3. 신호 강도 계산
            signal_strength = self._calculate_signal_strength(timeframe_analyses)
            
            # 4. 진입 조건 검증
            entry_conditions = self._check_entry_conditions(timeframe_analyses, trend_alignment, signal_strength)
            
            # 5. 최종 신호 생성
            final_signal = self._generate_final_signal(
                timeframe_analyses, trend_alignment, signal_strength, entry_conditions, stock_data
            )
            
            self.logger.info(f"✅ {symbol} 다중 시간대 분석 완료 - 신호: {final_signal['signal_type']}")
            
            return final_signal
            
        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} 다중 시간대 분석 실패: {e}")
            return self._create_empty_signal()

    async def _analyze_all_timeframes(self, symbol: str, price_data: Dict) -> Dict[TimeFrame, Dict]:
        """모든 시간대 분석"""
        analyses = {}
        
        for timeframe in self.timeframe_weights.keys():
            try:
                # 시간대별 데이터 가져오기
                tf_data = await self._get_timeframe_data(symbol, timeframe, price_data)
                
                if tf_data and len(tf_data) >= 50:
                    # 기술적 지표 계산
                    indicators = self._calculate_all_indicators(tf_data)
                    
                    # 추세 분석
                    trend_analysis = self._analyze_trend(tf_data, indicators)
                    
                    # 신호 분석
                    signal_analysis = self._analyze_signals(tf_data, indicators)
                    
                    # 종합 분석 결과
                    analyses[timeframe] = {
                        'data': tf_data,
                        'indicators': indicators,
                        'trend': trend_analysis,
                        'signals': signal_analysis,
                        'weight': self.timeframe_weights[timeframe]
                    }
                    
                else:
                    self.logger.debug(f"⚠️ {symbol} {timeframe.value} 데이터 부족")
                    
            except Exception as e:
                self.logger.error(f"❌ {symbol} {timeframe.value} 분석 실패: {e}")
                continue
        
        return analyses

    def _calculate_all_indicators(self, data: List[Dict]) -> Dict[str, Any]:
        """모든 기술적 지표 계산"""
        try:
            df = pd.DataFrame(data)
            df = self._ensure_numeric_columns(df)
            
            indicators = {}
            
            # 1. RSI
            indicators['rsi'] = self._calculate_rsi(df['close'])
            
            # 2. MACD
            indicators['macd'] = self._calculate_macd(df['close'])
            
            # 3. EMA
            indicators['ema'] = self._calculate_ema(df['close'])
            
            # 4. Supertrend
            indicators['supertrend'] = self._calculate_supertrend(df)
            
            # 5. ATR (신규 추가)
            indicators['atr'] = self._calculate_atr(df)
            
            # 6. 볼린저 밴드 (향상된 버전)
            indicators['bollinger'] = self._calculate_bollinger_bands(df['close'])
            
            # 7. 거래량 지표
            indicators['volume'] = self._calculate_volume_indicators(df)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ 기술적 지표 계산 실패: {e}")
            return {}

    def _calculate_atr(self, df: pd.DataFrame) -> Dict[str, float]:
        """ATR (Average True Range) 계산"""
        try:
            period = self.indicator_params['atr_period']
            
            # True Range 계산
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift(1))
            low_close = np.abs(df['low'] - df['close'].shift(1))
            
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(period).mean()
            
            current_atr = atr.iloc[-1] if len(atr) > 0 else 0
            atr_ratio = current_atr / df['close'].iloc[-1] if df['close'].iloc[-1] > 0 else 0
            
            return {
                'current_atr': current_atr,
                'atr_ratio': atr_ratio,
                'volatility_level': 'high' if atr_ratio > 0.03 else 'medium' if atr_ratio > 0.015 else 'low'
            }
            
        except Exception as e:
            self.logger.error(f"❌ ATR 계산 실패: {e}")
            return {'current_atr': 0, 'atr_ratio': 0, 'volatility_level': 'medium'}

    def _calculate_bollinger_bands(self, close_prices: pd.Series) -> Dict[str, float]:
        """향상된 볼린저 밴드 계산"""
        try:
            period = self.indicator_params['bb_period']
            std_mult = self.indicator_params['bb_std']
            
            # 볼린저 밴드 계산
            sma = close_prices.rolling(period).mean()
            std = close_prices.rolling(period).std()
            
            upper_band = sma + (std * std_mult)
            lower_band = sma - (std * std_mult)
            
            current_price = close_prices.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = sma.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # 밴드 내 위치 계산 (0~1)
            band_position = (current_price - current_lower) / (current_upper - current_lower) if current_upper > current_lower else 0.5
            
            # 밴드 폭 (변동성 지표)
            band_width = (current_upper - current_lower) / current_middle if current_middle > 0 else 0
            
            return {
                'upper_band': current_upper,
                'middle_band': current_middle,
                'lower_band': current_lower,
                'band_position': band_position,
                'band_width': band_width,
                'squeeze': band_width < 0.1,  # 밴드 수축
                'expansion': band_width > 0.2  # 밴드 확장
            }
            
        except Exception as e:
            self.logger.error(f"❌ 볼린저 밴드 계산 실패: {e}")
            return {'band_position': 0.5, 'band_width': 0.1, 'squeeze': False, 'expansion': False}

    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """거래량 지표 계산"""
        try:
            # 거래량 이동평균
            volume_ma_20 = df['volume'].rolling(20).mean()
            current_volume = df['volume'].iloc[-1]
            avg_volume = volume_ma_20.iloc[-1]
            
            # 거래량 비율
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # 가격-거래량 관계
            price_change = df['close'].pct_change()
            volume_change = df['volume'].pct_change()
            
            # 최근 10일 상관관계
            pv_correlation = price_change[-10:].corr(volume_change[-10:]) if len(price_change) >= 10 else 0
            
            return {
                'volume_ratio': volume_ratio,
                'volume_trend': 'increasing' if volume_ratio > 1.2 else 'decreasing' if volume_ratio < 0.8 else 'stable',
                'volume_spike': volume_ratio > self.trading_thresholds['volume_spike_threshold'],
                'price_volume_correlation': pv_correlation
            }
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 지표 계산 실패: {e}")
            return {'volume_ratio': 1.0, 'volume_trend': 'stable', 'volume_spike': False, 'price_volume_correlation': 0}

    def _check_entry_conditions(self, analyses: Dict, trend_alignment: float, signal_strength: float) -> Dict[str, bool]:
        """진입 조건 검증 (요청하신 조건들)"""
        try:
            conditions = {
                'trend_alignment_ok': False,
                'volume_confirmation': False,
                'technical_signals_aligned': False,
                'risk_acceptable': False,
                'timing_good': False
            }
            
            # 1. 추세 정렬도 검증
            conditions['trend_alignment_ok'] = trend_alignment >= self.trading_thresholds['min_trend_alignment']
            
            # 2. 거래량 확인 (다중 시간대)
            volume_confirmations = 0
            for timeframe, analysis in analyses.items():
                if analysis['indicators'].get('volume', {}).get('volume_spike', False):
                    volume_confirmations += 1
            conditions['volume_confirmation'] = volume_confirmations >= 2  # 최소 2개 시간대
            
            # 3. 기술적 지표 동조성
            bullish_signals = 0
            total_signals = 0
            
            for timeframe, analysis in analyses.items():
                indicators = analysis['indicators']
                weight = analysis['weight'].signal_weight
                
                # RSI 신호
                rsi = indicators.get('rsi', {}).get('current', 50)
                if 30 < rsi < 70:
                    bullish_signals += weight
                total_signals += weight
                
                # MACD 신호
                macd = indicators.get('macd', {})
                if macd.get('histogram', 0) > 0:
                    bullish_signals += weight
                total_signals += weight
                
                # EMA 신호
                ema = indicators.get('ema', {})
                if ema.get('bullish', False):
                    bullish_signals += weight
                total_signals += weight
            
            alignment_ratio = bullish_signals / total_signals if total_signals > 0 else 0
            conditions['technical_signals_aligned'] = alignment_ratio >= 0.6
            
            # 4. 리스크 수준 검증
            risk_factors = self._assess_risk_factors(analyses)
            conditions['risk_acceptable'] = risk_factors['total_risk'] <= 0.7
            
            # 5. 타이밍 검증 (단기 시간대 신호)
            short_term_signals = [
                analyses.get(TimeFrame.M15, {}).get('signals', {}).get('strength', 0),
                analyses.get(TimeFrame.M5, {}).get('signals', {}).get('strength', 0)
            ]
            avg_short_term = np.mean([s for s in short_term_signals if s > 0])
            conditions['timing_good'] = avg_short_term >= 0.6
            
            return conditions
            
        except Exception as e:
            self.logger.error(f"❌ 진입 조건 검증 실패: {e}")
            return {key: False for key in ['trend_alignment_ok', 'volume_confirmation', 'technical_signals_aligned', 'risk_acceptable', 'timing_good']}

    def _assess_risk_factors(self, analyses: Dict) -> Dict[str, float]:
        """리스크 요소 평가"""
        try:
            risk_factors = {
                'volatility_risk': 0,
                'trend_inconsistency': 0,
                'volume_risk': 0,
                'technical_divergence': 0
            }
            
            # 1. 변동성 리스크
            atr_values = []
            for analysis in analyses.values():
                atr_ratio = analysis['indicators'].get('atr', {}).get('atr_ratio', 0)
                atr_values.append(atr_ratio)
            
            avg_volatility = np.mean(atr_values) if atr_values else 0
            risk_factors['volatility_risk'] = min(avg_volatility / 0.05, 1.0)  # 5% 이상 변동성을 고위험으로
            
            # 2. 추세 불일치 리스크
            trend_directions = []
            for analysis in analyses.values():
                trend_score = analysis['trend'].get('direction_score', 0)
                trend_directions.append(trend_score)
            
            trend_std = np.std(trend_directions) if trend_directions else 0
            risk_factors['trend_inconsistency'] = min(trend_std / 0.5, 1.0)
            
            # 3. 거래량 리스크
            volume_ratios = []
            for analysis in analyses.values():
                vol_ratio = analysis['indicators'].get('volume', {}).get('volume_ratio', 1.0)
                volume_ratios.append(vol_ratio)
            
            avg_volume_ratio = np.mean(volume_ratios) if volume_ratios else 1.0
            risk_factors['volume_risk'] = 1.0 if avg_volume_ratio < 0.5 else 0.0  # 거래량 부족 시 고위험
            
            # 4. 기술적 다이버전스 리스크
            indicator_signals = []
            for analysis in analyses.values():
                signals = analysis['signals']
                signal_strength = signals.get('strength', 0.5)
                indicator_signals.append(signal_strength)
            
            signal_std = np.std(indicator_signals) if indicator_signals else 0
            risk_factors['technical_divergence'] = min(signal_std / 0.3, 1.0)
            
            # 총 리스크 계산
            total_risk = np.mean(list(risk_factors.values()))
            risk_factors['total_risk'] = total_risk
            
            return risk_factors
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 평가 실패: {e}")
            return {'total_risk': 0.8}  # 안전하게 높은 리스크로 설정

    async def calculate_stop_loss(self, stock_data: Dict, entry_price: float, analyses: Dict = None) -> float:
        """ATR 기반 동적 손절가 계산"""
        try:
            if not analyses:
                # 기본 손절 (5%)
                return entry_price * 0.95
            
            # 다중 시간대 ATR 평균 계산
            atr_values = []
            for timeframe, analysis in analyses.items():
                atr = analysis['indicators'].get('atr', {}).get('current_atr', 0)
                if atr > 0:
                    weight = analysis['weight'].filter_weight
                    atr_values.append(atr * weight)
            
            if not atr_values:
                return entry_price * 0.95
            
            # 가중 평균 ATR
            weighted_atr = sum(atr_values) / sum([a['weight'].filter_weight for a in analyses.values()])
            
            # ATR의 1.5배를 손절 기준으로 (보수적)
            stop_loss_distance = weighted_atr * 1.5
            stop_loss_price = entry_price - stop_loss_distance
            
            # 최소 2%, 최대 8% 제한
            min_stop = entry_price * 0.92
            max_stop = entry_price * 0.98
            
            return max(min_stop, min(max_stop, stop_loss_price))
            
        except Exception as e:
            self.logger.error(f"❌ ATR 기반 손절가 계산 실패: {e}")
            return entry_price * 0.95

    async def calculate_take_profit(self, stock_data: Dict, entry_price: float, stop_loss_price: float, analyses: Dict = None) -> float:
        """동적 익절가 계산 (1:2 또는 1:3 비율)"""
        try:
            # 손실 금액 계산
            loss_amount = entry_price - stop_loss_price
            
            # 리스크 레벨에 따른 익절 비율 결정
            if analyses:
                risk_factors = self._assess_risk_factors(analyses)
                total_risk = risk_factors['total_risk']
                
                # 저위험: 1:3, 중위험: 1:2.5, 고위험: 1:2
                if total_risk < 0.3:
                    ratio = 3.0
                elif total_risk < 0.6:
                    ratio = 2.5
                else:
                    ratio = 2.0
            else:
                ratio = 2.0  # 기본 1:2
            
            # 익절가 계산
            take_profit_price = entry_price + (loss_amount * ratio)
            
            return take_profit_price
            
        except Exception as e:
            self.logger.error(f"❌ 익절가 계산 실패: {e}")
            return entry_price * 1.06  # 기본 6% 익절

    # 기존 메서드들 (momentum_strategy.py에서 가져온 것들)
    def _calculate_rsi(self, close_prices: pd.Series) -> Dict[str, float]:
        """RSI 계산"""
        try:
            period = self.indicator_params['rsi_period']
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
            
            return {
                'current': current_rsi,
                'oversold': current_rsi < 30,
                'overbought': current_rsi > 70,
                'neutral': 30 <= current_rsi <= 70
            }
        except:
            return {'current': 50, 'oversold': False, 'overbought': False, 'neutral': True}

    def _calculate_macd(self, close_prices: pd.Series) -> Dict[str, float]:
        """MACD 계산"""
        try:
            fast = self.indicator_params['macd_fast']
            slow = self.indicator_params['macd_slow']
            signal = self.indicator_params['macd_signal']
            
            ema_fast = close_prices.ewm(span=fast).mean()
            ema_slow = close_prices.ewm(span=slow).mean()
            
            macd_line = ema_fast - ema_slow
            macd_signal = macd_line.ewm(span=signal).mean()
            macd_histogram = macd_line - macd_signal
            
            return {
                'line': macd_line.iloc[-1] if len(macd_line) > 0 else 0,
                'signal': macd_signal.iloc[-1] if len(macd_signal) > 0 else 0,
                'histogram': macd_histogram.iloc[-1] if len(macd_histogram) > 0 else 0,
                'bullish': macd_histogram.iloc[-1] > 0 if len(macd_histogram) > 0 else False
            }
        except:
            return {'line': 0, 'signal': 0, 'histogram': 0, 'bullish': False}

    def _calculate_ema(self, close_prices: pd.Series) -> Dict[str, float]:
        """EMA 계산"""
        try:
            short = self.indicator_params['ema_short']
            long = self.indicator_params['ema_long']
            
            ema_short = close_prices.ewm(span=short).mean()
            ema_long = close_prices.ewm(span=long).mean()
            
            current_short = ema_short.iloc[-1] if len(ema_short) > 0 else close_prices.iloc[-1]
            current_long = ema_long.iloc[-1] if len(ema_long) > 0 else close_prices.iloc[-1]
            
            return {
                'short': current_short,
                'long': current_long,
                'bullish': current_short > current_long,
                'gap_ratio': (current_short - current_long) / current_long if current_long > 0 else 0
            }
        except:
            return {'short': 0, 'long': 0, 'bullish': False, 'gap_ratio': 0}

    def _calculate_supertrend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Supertrend 계산"""
        try:
            period = self.indicator_params['supertrend_period']
            multiplier = self.indicator_params['supertrend_multiplier']
            
            # True Range
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift(1))
            low_close = np.abs(df['low'] - df['close'].shift(1))
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(period).mean()
            
            # Supertrend
            hl2 = (df['high'] + df['low']) / 2
            upper_band = hl2 + (multiplier * atr)
            lower_band = hl2 - (multiplier * atr)
            
            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # 간단한 방향 판단
            direction = current_price > (current_upper + current_lower) / 2
            
            return {
                'direction': direction,
                'upper_band': current_upper,
                'lower_band': current_lower,
                'trend': 'up' if direction else 'down'
            }
        except:
            return {'direction': True, 'trend': 'up', 'upper_band': 0, 'lower_band': 0}

    # 헬퍼 메서드들
    def _ensure_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """숫자형 컬럼 보장"""
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    async def _get_timeframe_data(self, symbol: str, timeframe: TimeFrame, price_data: Dict) -> List[Dict]:
        """시간대별 데이터 조회 (실제 구현 시 데이터 수집기 연동 필요)"""
        # 임시 구현 - 실제로는 KIS API에서 시간대별 데이터 수집
        return price_data.get(timeframe.value, []) if price_data else []

    def _analyze_trend(self, data: List[Dict], indicators: Dict) -> Dict[str, Any]:
        """추세 분석"""
        try:
            ema = indicators.get('ema', {})
            supertrend = indicators.get('supertrend', {})
            
            bullish_signals = 0
            total_signals = 0
            
            if ema.get('bullish', False):
                bullish_signals += 1
            total_signals += 1
            
            if supertrend.get('direction', False):
                bullish_signals += 1
            total_signals += 1
            
            direction_score = bullish_signals / total_signals if total_signals > 0 else 0.5
            
            return {
                'direction': 'up' if direction_score > 0.5 else 'down',
                'direction_score': direction_score,
                'strength': abs(direction_score - 0.5) * 2  # 0.5에서 얼마나 멀리 떨어져 있는지
            }
        except:
            return {'direction': 'neutral', 'direction_score': 0.5, 'strength': 0}

    def _analyze_signals(self, data: List[Dict], indicators: Dict) -> Dict[str, Any]:
        """신호 분석"""
        try:
            rsi = indicators.get('rsi', {})
            macd = indicators.get('macd', {})
            volume = indicators.get('volume', {})
            
            signal_strength = 0.5  # 기본값
            
            # RSI 신호
            if rsi.get('oversold', False):
                signal_strength += 0.2
            elif rsi.get('overbought', False):
                signal_strength -= 0.2
            elif rsi.get('neutral', False):
                signal_strength += 0.1
            
            # MACD 신호
            if macd.get('bullish', False):
                signal_strength += 0.15
            else:
                signal_strength -= 0.15
            
            # 거래량 신호
            if volume.get('volume_spike', False):
                signal_strength += 0.1
            
            signal_strength = max(0, min(1, signal_strength))
            
            return {
                'strength': signal_strength,
                'type': 'bullish' if signal_strength > 0.6 else 'bearish' if signal_strength < 0.4 else 'neutral'
            }
        except:
            return {'strength': 0.5, 'type': 'neutral'}

    def _calculate_trend_alignment(self, analyses: Dict) -> float:
        """추세 정렬도 계산"""
        if not analyses:
            return 0.0
        
        try:
            direction_scores = []
            weights = []
            
            for timeframe, analysis in analyses.items():
                direction_score = analysis['trend'].get('direction_score', 0.5)
                weight = analysis['weight'].trend_weight
                
                direction_scores.append(direction_score)
                weights.append(weight)
            
            if not direction_scores:
                return 0.0
            
            # 가중 평균
            weighted_avg = np.average(direction_scores, weights=weights)
            
            # 일관성 계산 (표준편차의 역수)
            consistency = 1.0 - min(np.std(direction_scores), 0.5) / 0.5
            
            # 최종 정렬도 = 방향성 강도 * 일관성
            alignment = abs(weighted_avg - 0.5) * 2 * consistency
            
            return min(1.0, alignment)
            
        except Exception as e:
            self.logger.error(f"❌ 추세 정렬도 계산 실패: {e}")
            return 0.0

    def _calculate_signal_strength(self, analyses: Dict) -> float:
        """신호 강도 계산"""
        if not analyses:
            return 0.0
        
        try:
            signal_strengths = []
            weights = []
            
            for timeframe, analysis in analyses.items():
                signal_strength = analysis['signals'].get('strength', 0.5)
                weight = analysis['weight'].signal_weight
                
                signal_strengths.append(signal_strength)
                weights.append(weight)
            
            if not signal_strengths:
                return 0.0
            
            # 가중 평균
            weighted_strength = np.average(signal_strengths, weights=weights)
            
            return weighted_strength
            
        except Exception as e:
            self.logger.error(f"❌ 신호 강도 계산 실패: {e}")
            return 0.0

    def _generate_final_signal(self, analyses: Dict, trend_alignment: float, signal_strength: float, 
                             entry_conditions: Dict, stock_data: Any) -> Dict[str, Any]:
        """최종 신호 생성"""
        try:
            # 조건 확인
            conditions_met = sum(entry_conditions.values())
            total_conditions = len(entry_conditions)
            
            condition_ratio = conditions_met / total_conditions if total_conditions > 0 else 0
            
            # 최종 점수 계산
            final_score = (
                trend_alignment * 0.4 +
                signal_strength * 0.3 +
                condition_ratio * 0.3
            ) * 100
            
            # 신호 타입 결정
            if final_score >= 80 and conditions_met >= 4:
                signal_type = "STRONG_BUY"
                action = "BUY"
            elif final_score >= 65 and conditions_met >= 3:
                signal_type = "BUY"
                action = "BUY"
            elif final_score >= 55:
                signal_type = "WEAK_BUY"
                action = "HOLD"
            elif final_score <= 20:
                signal_type = "STRONG_SELL"
                action = "SELL"
            elif final_score <= 35:
                signal_type = "SELL"
                action = "SELL"
            elif final_score <= 45:
                signal_type = "WEAK_SELL"
                action = "HOLD"
            else:
                signal_type = "HOLD"
                action = "HOLD"
            
            return {
                'signal_strength': round(final_score, 1),
                'signal_type': signal_type,
                'action': action,
                'confidence': min(1.0, final_score / 100),
                'details': {
                    'trend_alignment': trend_alignment,
                    'signal_strength': signal_strength,
                    'conditions_met': f"{conditions_met}/{total_conditions}",
                    'entry_conditions': entry_conditions,
                    'timeframe_count': len(analyses),
                    'risk_assessment': 'low' if condition_ratio > 0.8 else 'medium' if condition_ratio > 0.6 else 'high'
                },
                'risk_level': self._assess_risk_level(final_score, stock_data),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 최종 신호 생성 실패: {e}")
            return self._create_empty_signal()

    def _assess_risk_level(self, score: float, stock_data: Any) -> str:
        """리스크 레벨 평가"""
        try:
            risk_factors = 0
            
            # 점수 극단성
            if score > 90 or score < 10:
                risk_factors += 1
            
            # 기타 리스크 요소들
            change_rate = getattr(stock_data, 'change_rate', 0)
            if abs(change_rate) > 5:
                risk_factors += 1
            
            volume = getattr(stock_data, 'volume', 100000)
            if volume < 50000:
                risk_factors += 1
            
            if risk_factors >= 2:
                return "HIGH"
            elif risk_factors >= 1:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception:
            return "MEDIUM"

    def _create_empty_signal(self) -> Dict[str, Any]:
        """빈 신호 생성"""
        return {
            'signal_strength': 50.0,
            'signal_type': "HOLD",
            'action': "HOLD",
            'confidence': 0.5,
            'details': {},
            'risk_level': "MEDIUM",
            'timestamp': datetime.now().isoformat()
        }