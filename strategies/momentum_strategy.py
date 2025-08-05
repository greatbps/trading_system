#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/momentum_strategy.py

모멘텀 전략 - 추세 추종 및 모멘텀 기반 매매
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
# momentum_strategy.py 상단에 추가
import logging

from .base_strategy import BaseStrategy
#from utils.logger import get_logger

def create_logger(name: str = "TradingSystem"):
    """안전한 로거 생성 함수"""
    try:
        # 로거 생성
        logger = logging.getLogger(name)
        
        # 이미 설정된 로거라면 그대로 반환
        if logger.handlers:
            return logger
        
        # 로그 레벨 설정
        logger.setLevel(logging.INFO)
        
        # 콘솔 핸들러 생성 및 설정
        try:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 포맷터 설정
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"Warning: 콘솔 핸들러 설정 실패: {e}")
        
        # 파일 핸들러 추가 (선택사항)
        try:
            import os
            log_dir = "logs" 
            os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / f"{name.lower()}.log", 
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: 파일 핸들러 설정 실패: {e}")
        
        return logger
        
    except Exception as e:
        print(f"Error: 로거 생성 실패: {e}")
        # 최후의 수단: 기본 print 함수를 사용하는 더미 로거
        class DummyLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
        
        return DummyLogger()

class MomentumStrategy(BaseStrategy):
    """모멘텀 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        #self.logger = get_logger("MomentumStrategy")
        self.logger = create_logger("MomentumStrategy")
        
        # 모멘텀 전략 파라미터
        self.params = {
            'ma_short': 5,           # 단기 이동평균
            'ma_medium': 10,         # 중기 이동평균
            'ma_long': 20,           # 장기 이동평균
            'rsi_period': 14,        # RSI 기간
            'rsi_oversold': 30,      # RSI 과매도
            'rsi_overbought': 70,    # RSI 과매수
            'volume_threshold': 1.5, # 거래량 임계값 (평균 대비)
            'momentum_period': 12,   # 모멘텀 계산 기간
            'breakout_period': 20,   # 돌파 확인 기간
            'min_gain_threshold': 0.02,  # 최소 수익률 임계값 (2%)
            'max_loss_threshold': 0.05   # 최대 손실률 임계값 (5%)
        }
        
        self.logger.info("📈 모멘텀 전략 초기화 완료")


    def get_logger(name: str) -> logging.Logger:
        """로거 생성 함수 (momentum_strategy용)"""
        logger = logging.getLogger(name)
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def safe_get_attr(self, data, attr_name, default=None):
        """안전한 속성 접근 유틸리티"""
        try:
            if isinstance(data, dict):
                return data.get(attr_name, default)
            else:
                return getattr(data, attr_name, default)
        except (AttributeError, TypeError):
            return default
    
    async def generate_signals(self, stock_data: Any, analysis_result: Dict, price_data: List[Dict] = None) -> Dict[str, Any]:
        """모멘텀 기반 매매 신호 생성 - 실제 가격 데이터 사용"""
        try:
            # 안전한 symbol 추출
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"📊 {symbol} 모멘텀 신호 생성 중...")
            
            # 가격 데이터 확인
            if not price_data or len(price_data) < self.params['ma_long']:
                self.logger.warning(f"⚠️ {symbol} 가격 데이터 부족 - 필요: {self.params['ma_long']}개, 보유: {len(price_data) if price_data else 0}개")
                return self._create_empty_signal()
            
            # DataFrame 변환
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(int)
            
            # 1. 이동평균 분석
            ma_signals = self._analyze_moving_averages(df)
            
            # 2. RSI 분석
            rsi_signals = self._analyze_rsi(df)
            
            # 3. 거래량 분석
            volume_signals = self._analyze_volume(df)
            
            # 4. 가격 모멘텀 분석
            momentum_signals = self._analyze_price_momentum(df)
            
            # 5. 돌파 패턴 분석
            breakout_signals = self._analyze_breakout_patterns(df)
            
            # 6. 종합 신호 생성
            final_signal = self._combine_signals(
                ma_signals, rsi_signals, volume_signals, 
                momentum_signals, breakout_signals, stock_data
            )
            
            self.logger.info(f"✅ {symbol} 모멘텀 신호 완료 - 강도: {final_signal['signal_strength']:.1f}%")
            
            return final_signal
            
        except Exception as e:
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} 모멘텀 신호 생성 실패: {e}")
            return self._create_empty_signal()
    
    def _analyze_moving_averages(self, df: pd.DataFrame) -> Dict[str, Any]:
        """이동평균 분석"""
        try:
            # 이동평균 계산
            df[f'ma_{self.params["ma_short"]}'] = df['close'].rolling(self.params['ma_short']).mean()
            df[f'ma_{self.params["ma_medium"]}'] = df['close'].rolling(self.params['ma_medium']).mean()
            df[f'ma_{self.params["ma_long"]}'] = df['close'].rolling(self.params['ma_long']).mean()
            
            # 현재값들
            current_price = df['close'].iloc[-1]
            ma_short = df[f'ma_{self.params["ma_short"]}'].iloc[-1]
            ma_medium = df[f'ma_{self.params["ma_medium"]}'].iloc[-1]
            ma_long = df[f'ma_{self.params["ma_long"]}'].iloc[-1]
            
            # 이전값들 (골든크로스/데드크로스 확인용)
            prev_ma_short = df[f'ma_{self.params["ma_short"]}'].iloc[-2]
            prev_ma_medium = df[f'ma_{self.params["ma_medium"]}'].iloc[-2]
            
            # 신호 점수 계산
            score = 50  # 기본값
            
            # 1. 현재가와 이동평균 관계
            if current_price > ma_short > ma_medium > ma_long:
                score += 20  # 강한 상승 추세
            elif current_price > ma_short > ma_medium:
                score += 15  # 상승 추세
            elif current_price > ma_short:
                score += 10  # 약한 상승 추세
            elif current_price < ma_short < ma_medium < ma_long:
                score -= 20  # 강한 하락 추세
            elif current_price < ma_short < ma_medium:
                score -= 15  # 하락 추세
            elif current_price < ma_short:
                score -= 10  # 약한 하락 추세
            
            # 2. 골든크로스/데드크로스
            golden_cross = (ma_short > ma_medium) and (prev_ma_short <= prev_ma_medium)
            dead_cross = (ma_short < ma_medium) and (prev_ma_short >= prev_ma_medium)
            
            if golden_cross:
                score += 15
            elif dead_cross:
                score -= 15
            
            # 3. 이동평균 기울기
            ma_slope_short = (ma_short - df[f'ma_{self.params["ma_short"]}'].iloc[-5]) / 5
            ma_slope_medium = (ma_medium - df[f'ma_{self.params["ma_medium"]}'].iloc[-5]) / 5
            
            if ma_slope_short > 0 and ma_slope_medium > 0:
                score += 10  # 상승 기울기
            elif ma_slope_short < 0 and ma_slope_medium < 0:
                score -= 10  # 하락 기울기
            
            return {
                'score': max(0, min(100, score)),
                'golden_cross': golden_cross,
                'dead_cross': dead_cross,
                'trend_direction': 'up' if ma_short > ma_medium > ma_long else 'down' if ma_short < ma_medium < ma_long else 'sideways',
                'ma_alignment': current_price > ma_short > ma_medium > ma_long,
                'current_price': current_price,
                'ma_short': ma_short,
                'ma_medium': ma_medium,
                'ma_long': ma_long
            }
            
        except Exception as e:
            self.logger.error(f"❌ 이동평균 분석 실패: {e}")
            return {'score': 50}
    
    def _analyze_rsi(self, df: pd.DataFrame) -> Dict[str, Any]:
        """RSI 분석"""
        try:
            # RSI 계산
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.params['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.params['rsi_period']).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            
            # RSI 신호 점수
            score = 50
            
            # 1. RSI 수준별 점수
            if 30 <= current_rsi <= 70:
                score += 10  # 정상 범위
            elif current_rsi < 30:
                score += 20  # 과매도 (매수 기회)
            elif current_rsi > 70:
                score -= 20  # 과매수 (매도 신호)
            
            # 2. RSI 다이버전스 (간단 버전)
            price_trend = df['close'].iloc[-5:].is_monotonic_increasing
            rsi_trend = rsi.iloc[-5:].is_monotonic_increasing
            
            if price_trend and not rsi_trend:
                score -= 10  # 베어리시 다이버전스
            elif not price_trend and rsi_trend:
                score += 10  # 불리시 다이버전스
            
            # 3. RSI 모멘텀
            rsi_momentum = current_rsi - prev_rsi
            if abs(rsi_momentum) > 5:
                if rsi_momentum > 0 and current_rsi < 70:
                    score += 5  # 상승 모멘텀
                elif rsi_momentum < 0 and current_rsi > 30:
                    score -= 5  # 하락 모멘텀
            
            return {
                'score': max(0, min(100, score)),
                'rsi': current_rsi,
                'rsi_trend': 'up' if rsi_momentum > 0 else 'down' if rsi_momentum < 0 else 'flat',
                'oversold': current_rsi < self.params['rsi_oversold'],
                'overbought': current_rsi > self.params['rsi_overbought'],
                'rsi_momentum': rsi_momentum
            }
            
        except Exception as e:
            self.logger.error(f"❌ RSI 분석 실패: {e}")
            return {'score': 50, 'rsi': 50}
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """거래량 분석"""
        try:
            # 평균 거래량 계산
            avg_volume = df['volume'].rolling(20).mean()
            current_volume = df['volume'].iloc[-1]
            prev_volume = df['volume'].iloc[-2]
            
            volume_ratio = current_volume / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1
            
            score = 50
            
            # 1. 거래량 증가율
            if volume_ratio >= 2.0:
                score += 20  # 거래량 폭증
            elif volume_ratio >= 1.5:
                score += 15  # 거래량 급증
            elif volume_ratio >= 1.2:
                score += 10  # 거래량 증가
            elif volume_ratio < 0.5:
                score -= 15  # 거래량 급감
            
            # 2. 가격-거래량 관계
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            volume_change = (current_volume - prev_volume) / prev_volume if prev_volume > 0 else 0
            
            # 상승 + 거래량 증가 = 긍정적
            if price_change > 0 and volume_change > 0:
                score += 10
            # 하락 + 거래량 증가 = 부정적
            elif price_change < 0 and volume_change > 0:
                score -= 10
            
            # 3. 거래량 패턴 (최근 5일)
            recent_volumes = df['volume'].tail(5)
            volume_trend = 'increasing' if recent_volumes.is_monotonic_increasing else \
                          'decreasing' if recent_volumes.is_monotonic_decreasing else 'mixed'
            
            if volume_trend == 'increasing':
                score += 5
            elif volume_trend == 'decreasing':
                score -= 5
            
            return {
                'score': max(0, min(100, score)),
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'volume_breakout': volume_ratio >= self.params['volume_threshold'],
                'current_volume': current_volume,
                'avg_volume': avg_volume.iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 분석 실패: {e}")
            return {'score': 50, 'volume_ratio': 1.0}
    
    def _analyze_price_momentum(self, df: pd.DataFrame) -> Dict[str, Any]:
        """가격 모멘텀 분석"""
        try:
            # 다양한 기간의 수익률 계산
            returns_1d = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            returns_5d = (df['close'].iloc[-1] - df['close'].iloc[-6]) / df['close'].iloc[-6]
            returns_10d = (df['close'].iloc[-1] - df['close'].iloc[-11]) / df['close'].iloc[-11]
            
            score = 50
            
            # 1. 단기 모멘텀 (1일)
            if returns_1d > 0.03:  # 3% 이상 상승
                score += 15
            elif returns_1d > 0.01:  # 1% 이상 상승
                score += 10
            elif returns_1d > 0:
                score += 5
            elif returns_1d < -0.03:  # 3% 이상 하락
                score -= 15
            elif returns_1d < -0.01:  # 1% 이상 하락
                score -= 10
            elif returns_1d < 0:
                score -= 5
            
            # 2. 중기 모멘텀 (5일)
            if returns_5d > 0.1:  # 10% 이상 상승
                score += 20
            elif returns_5d > 0.05:  # 5% 이상 상승
                score += 15
            elif returns_5d > 0:
                score += 10
            elif returns_5d < -0.1:  # 10% 이상 하락
                score -= 20
            elif returns_5d < -0.05:  # 5% 이상 하락
                score -= 15
            elif returns_5d < 0:
                score -= 10
            
            # 3. 모멘텀 지속성
            momentum_consistency = 0
            if returns_1d > 0 and returns_5d > 0 and returns_10d > 0:
                momentum_consistency = 1  # 일관된 상승
                score += 10
            elif returns_1d < 0 and returns_5d < 0 and returns_10d < 0:
                momentum_consistency = -1  # 일관된 하락
                score -= 10
            
            # 4. 모멘텀 가속도
            acceleration = returns_1d - returns_5d/5  # 최근 모멘텀이 평균보다 강한지
            if acceleration > 0.01:
                score += 5  # 모멘텀 가속
            elif acceleration < -0.01:
                score -= 5  # 모멘텀 감속
            
            return {
                'score': max(0, min(100, score)),
                'returns_1d': returns_1d,
                'returns_5d': returns_5d,
                'returns_10d': returns_10d,
                'momentum_strong': returns_5d > 0.05 and returns_1d > 0,
                'momentum_consistency': momentum_consistency,
                'acceleration': acceleration
            }
            
        except Exception as e:
            self.logger.error(f"❌ 가격 모멘텀 분석 실패: {e}")
            return {'score': 50, 'returns_1d': 0}
    
    def _analyze_breakout_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """돌파 패턴 분석"""
        try:
            # 저항선/지지선 계산 (최근 20일 고점/저점)
            period = min(self.params['breakout_period'], len(df))
            recent_data = df.tail(period)
            
            resistance = recent_data['high'].max()
            support = recent_data['low'].min()
            current_price = df['close'].iloc[-1]
            
            score = 50
            
            # 1. 저항선 돌파
            resistance_break = current_price > resistance * 0.995  # 0.5% 마진
            if resistance_break:
                score += 25
            
            # 2. 지지선 이탈
            support_break = current_price < support * 1.005  # 0.5% 마진
            if support_break:
                score -= 25
            
            # 3. 52주 신고가/신저가
            week_52_high = df['high'].max()
            week_52_low = df['low'].min()
            
            if current_price >= week_52_high * 0.98:  # 52주 신고가 근처
                score += 15
            elif current_price <= week_52_low * 1.02:  # 52주 신저가 근처
                score -= 15
            
            # 4. 볼린저 밴드 돌파 (간단 버전)
            bb_period = 20
            if len(df) >= bb_period:
                bb_middle = df['close'].rolling(bb_period).mean()
                bb_std = df['close'].rolling(bb_period).std()
                bb_upper = bb_middle + (bb_std * 2)
                bb_lower = bb_middle - (bb_std * 2)
                
                if current_price > bb_upper.iloc[-1]:
                    score += 10  # 상단 밴드 돌파
                elif current_price < bb_lower.iloc[-1]:
                    score -= 10  # 하단 밴드 이탈
            
            return {
                'score': max(0, min(100, score)),
                'resistance_break': resistance_break,
                'support_break': support_break,
                'resistance_level': resistance,
                'support_level': support,
                'near_52w_high': current_price >= week_52_high * 0.98,
                'near_52w_low': current_price <= week_52_low * 1.02
            }
            
        except Exception as e:
            self.logger.error(f"❌ 돌파 패턴 분석 실패: {e}")
            return {'score': 50}
    
    def _combine_signals(self, ma_signals: Dict, rsi_signals: Dict, volume_signals: Dict, 
                        momentum_signals: Dict, breakout_signals: Dict, stock_data: Any) -> Dict[str, Any]:
        """신호 통합"""
        try:
            # 각 신호의 가중치
            weights = {
                'ma': 0.3,
                'rsi': 0.2,
                'volume': 0.2,
                'momentum': 0.2,
                'breakout': 0.1
            }
            
            # 가중 평균 점수
            total_score = (
                ma_signals.get('score', 50) * weights['ma'] +
                rsi_signals.get('score', 50) * weights['rsi'] +
                volume_signals.get('score', 50) * weights['volume'] +
                momentum_signals.get('score', 50) * weights['momentum'] +
                breakout_signals.get('score', 50) * weights['breakout']
            )
            
            # 보너스/페널티
            bonus = 0
            
            # 강한 모멘텀 보너스
            if momentum_signals.get('momentum_strong', False):
                bonus += 10
            
            # 골든크로스 보너스
            if ma_signals.get('golden_cross', False):
                bonus += 8
            
            # 거래량 돌파 보너스
            if volume_signals.get('volume_breakout', False):
                bonus += 5
            
            # 저항선 돌파 보너스
            if breakout_signals.get('resistance_break', False):
                bonus += 5
            
            # 데드크로스 페널티
            if ma_signals.get('dead_cross', False):
                bonus -= 8
            
            # 과매수 페널티
            if rsi_signals.get('overbought', False):
                bonus -= 5
            
            # 최종 점수
            final_score = max(0, min(100, total_score + bonus))
            
            # 신호 타입 결정
            if final_score >= 80:
                signal_type = "STRONG_BUY"
                action = "BUY"
            elif final_score >= 65:
                signal_type = "BUY"
                action = "BUY"
            elif final_score >= 55:
                signal_type = "WEAK_BUY"
                action = "HOLD"
            elif final_score >= 45:
                signal_type = "HOLD"
                action = "HOLD"
            elif final_score >= 35:
                signal_type = "WEAK_SELL"
                action = "HOLD"
            elif final_score >= 20:
                signal_type = "SELL"
                action = "SELL"
            else:
                signal_type = "STRONG_SELL"
                action = "SELL"
            
            return {
                'signal_strength': round(final_score, 1),
                'signal_type': signal_type,
                'action': action,
                'confidence': min(1.0, final_score / 100),
                'details': {
                    'ma_signals': ma_signals,
                    'rsi_signals': rsi_signals,
                    'volume_signals': volume_signals,
                    'momentum_signals': momentum_signals,
                    'breakout_signals': breakout_signals
                },
                'risk_level': self._assess_risk_level(final_score, stock_data),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 신호 통합 실패: {e}")
            return self._create_empty_signal()
    
    def _assess_risk_level(self, score: float, stock_data: Any) -> str:
        """리스크 레벨 평가 - 안전한 버전"""
        try:
            risk_factors = 0
            
            # 안전한 속성 접근
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            market_cap = self.safe_get_attr(stock_data, 'market_cap', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            
            # 변동성 (전일 대비 등락률로 추정)
            if abs(change_rate) > 5:
                risk_factors += 2
            elif abs(change_rate) > 3:
                risk_factors += 1
            
            # 시가총액
            if market_cap > 0:
                if market_cap < 1000:  # 1000억 미만
                    risk_factors += 2
                elif market_cap < 5000:  # 5000억 미만
                    risk_factors += 1
            
            # 거래량 (평소보다 너무 적으면 위험)
            if volume < 100000:  # 10만주 미만
                risk_factors += 1
            
            # 점수가 극단적이면 위험
            if score > 90 or score < 10:
                risk_factors += 1
            
            if risk_factors >= 4:
                return "HIGH"
            elif risk_factors >= 2:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception:
            return "MEDIUM"
    
    async def _get_chart_data(self, symbol: str) -> List[Dict]:
        """차트 데이터 조회 - 실제 데이터 수집기 사용"""
        try:
            # 실제 데이터 수집기에서 가져옴 (analysis_engine에서 전달받은 가격 데이터 사용)
            # 이 메서드는 더 이상 사용되지 않고, generate_signals에서 직접 price_data를 받아야 함
            self.logger.warning(f"⚠️ {symbol} 차트 데이터 조회 - 실제 구현 필요")
            return []
        except Exception as e:
            self.logger.error(f"❌ {symbol} 차트 데이터 조회 실패: {e}")
            return []
    
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
    
    async def calculate_stop_loss(self, stock_data: Dict, entry_price: float) -> float:
        """손절가 계산 - 안전한 버전"""
        try:
            # 안전한 속성 접근
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 2)
            
            # ATR 기반 손절가 (여기서는 간단히 변동성 기반으로 계산)
            volatility = abs(change_rate) / 100
            
            # 최소 2%, 최대 8% 손절
            stop_loss_ratio = max(0.02, min(0.08, volatility * 2))
            
            return entry_price * (1 - stop_loss_ratio)
            
        except Exception as e:
            self.logger.error(f"❌ 손절가 계산 실패: {e}")
            return entry_price * 0.95  # 기본 5% 손절
    
    async def calculate_take_profit(self, stock_data: Dict, entry_price: float) -> float:
        """익절가 계산 - 안전한 버전"""
        try:
            # 손익비 2:1 기준
            stop_loss = await self.calculate_stop_loss(stock_data, entry_price)
            loss_amount = entry_price - stop_loss
            
            # 익절가 = 진입가 + (손절 금액 * 2)
            take_profit = entry_price + (loss_amount * 2)
            
            return take_profit
            
        except Exception as e:
            self.logger.error(f"❌ 익절가 계산 실패: {e}")
            return entry_price * 1.10  # 기본 10% 익절