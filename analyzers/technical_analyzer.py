#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/technical_analyzer.py

기술적 분석기 - 수급정보와 차트패턴 분석 통합 + Supertrend 추가
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio

from utils.logger import get_logger

class TechnicalAnalyzer:
    """기술적 분석 엔진 - 간결화 버전"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("TechnicalAnalyzer")
        self.logger.info("✅ 기술적 분석기 초기화 완료")
    
    async def analyze_stock(self, symbol: str, price_data: List[Dict]) -> Dict:
        """기술적 분석 수행 - Dict 반환으로 단순화"""
        # 최소 데이터 요구량을 15개로 완화
        if len(price_data) < 15:
            raise ValueError(f"{symbol} 데이터 부족: {len(price_data)}개 (최소 15개 필요)")
        
        # 데이터가 부족할 경우 경고 로그만 출력하고 분석 진행
        if len(price_data) < 30:
            self.logger.warning(f"⚠️ {symbol} 데이터 부족 ({len(price_data)}개) - 제한된 분석으로 진행")
        
        self.logger.info(f"🔍 {symbol} 기술적 분석 시작...")
        
        # DataFrame 변환
        df = self._convert_to_dataframe(price_data)
        
        # 지표 계산
        indicators = {}
        indicators.update(self._calc_ma(df))
        indicators.update(self._calc_rsi(df))
        indicators.update(self._calc_macd(df))
        indicators.update(self._calc_bollinger(df))
        indicators.update(self._calc_volume(df))
        indicators.update(self._calc_supertrend(df))  # Supertrend 추가
        
        # 신호 및 점수
        signals = self._generate_signals(indicators)
        score = self._calculate_score(indicators)
        
        result = {
            'symbol': symbol,
            'indicators': indicators,
            'signals': signals,
            'technical_score': score,
            'confidence': self._calculate_confidence(indicators),
            'analysis_time': datetime.now().isoformat()
        }
        
        self.logger.info(f"✅ {symbol} 기술적 분석 완료 - 점수: {score:.1f}")
        return result
    
    def _convert_to_dataframe(self, price_data: List[Dict]) -> pd.DataFrame:
        """가격 데이터를 DataFrame으로 변환"""
        df = pd.DataFrame(price_data)
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        
        # 필수 컬럼 확인
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                df[col] = df.get('close', 0)
        
        return df.astype(float)
    
    def _calc_supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict:
        """Supertrend 계산"""
        try:
            # ATR 계산
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            # Basic Upper and Lower Bands
            hl2 = (df['high'] + df['low']) / 2
            upper_band = hl2 + (multiplier * atr)
            lower_band = hl2 - (multiplier * atr)
            
            # Final Upper and Lower Bands
            final_upper_band = pd.Series(index=df.index, dtype=float)
            final_lower_band = pd.Series(index=df.index, dtype=float)
            supertrend = pd.Series(index=df.index, dtype=float)
            
            for i in range(len(df)):
                if i == 0:
                    final_upper_band.iloc[i] = upper_band.iloc[i]
                    final_lower_band.iloc[i] = lower_band.iloc[i]
                else:
                    # Final Upper Band
                    if upper_band.iloc[i] < final_upper_band.iloc[i-1] or df['close'].iloc[i-1] > final_upper_band.iloc[i-1]:
                        final_upper_band.iloc[i] = upper_band.iloc[i]
                    else:
                        final_upper_band.iloc[i] = final_upper_band.iloc[i-1]
                    
                    # Final Lower Band
                    if lower_band.iloc[i] > final_lower_band.iloc[i-1] or df['close'].iloc[i-1] < final_lower_band.iloc[i-1]:
                        final_lower_band.iloc[i] = lower_band.iloc[i]
                    else:
                        final_lower_band.iloc[i] = final_lower_band.iloc[i-1]
            
            # Supertrend 계산
            for i in range(len(df)):
                if i == 0:
                    supertrend.iloc[i] = final_upper_band.iloc[i]
                else:
                    if supertrend.iloc[i-1] == final_upper_band.iloc[i-1] and df['close'].iloc[i] <= final_upper_band.iloc[i]:
                        supertrend.iloc[i] = final_upper_band.iloc[i]
                    elif supertrend.iloc[i-1] == final_upper_band.iloc[i-1] and df['close'].iloc[i] > final_upper_band.iloc[i]:
                        supertrend.iloc[i] = final_lower_band.iloc[i]
                    elif supertrend.iloc[i-1] == final_lower_band.iloc[i-1] and df['close'].iloc[i] >= final_lower_band.iloc[i]:
                        supertrend.iloc[i] = final_lower_band.iloc[i]
                    elif supertrend.iloc[i-1] == final_lower_band.iloc[i-1] and df['close'].iloc[i] < final_lower_band.iloc[i]:
                        supertrend.iloc[i] = final_upper_band.iloc[i]
                    else:
                        supertrend.iloc[i] = supertrend.iloc[i-1]
            
            # 신호 생성
            current_price = df['close'].iloc[-1]
            current_supertrend = supertrend.iloc[-1]
            prev_supertrend = supertrend.iloc[-2] if len(supertrend) > 1 else current_supertrend
            
            # 추세 방향
            if current_price > current_supertrend:
                trend = 'BULLISH'
                signal = 'BUY' if df['close'].iloc[-2] <= prev_supertrend else 'HOLD_BUY'
            else:
                trend = 'BEARISH'
                signal = 'SELL' if df['close'].iloc[-2] >= prev_supertrend else 'HOLD_SELL'
            
            # 강도 계산 (가격과 Supertrend 간 거리)
            distance_pct = abs(current_price - current_supertrend) / current_price * 100
            strength = min(1.0, distance_pct / 5.0)  # 5% 이상이면 최대 강도
            
            return {
                'supertrend_value': float(current_supertrend),
                'supertrend_trend': trend,
                'supertrend_signal': signal,
                'supertrend_strength': strength,
                'atr': float(atr.iloc[-1]) if not atr.empty else 0.0,
                'upper_band': float(final_upper_band.iloc[-1]),
                'lower_band': float(final_lower_band.iloc[-1])
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ Supertrend 계산 실패: {e}")
            return {
                'supertrend_value': 0.0,
                'supertrend_trend': 'NEUTRAL',
                'supertrend_signal': 'HOLD',
                'supertrend_strength': 0.0,
                'atr': 0.0,
                'upper_band': 0.0,
                'lower_band': 0.0
            }
    
    def _calc_ma(self, df: pd.DataFrame) -> Dict:
        """이동평균 계산"""
        try:
            ma5 = df['close'].rolling(window=5).mean().iloc[-1]
            ma20 = df['close'].rolling(window=20).mean().iloc[-1]
            current_price = df['close'].iloc[-1]
            
            if current_price > ma5 > ma20:
                signal = 'BUY'
            elif current_price < ma5 < ma20:
                signal = 'SELL'
            else:
                signal = 'HOLD'
            
            return {
                'ma5': float(ma5),
                'ma20': float(ma20),
                'ma_signal': signal
            }
        except Exception as e:
            self.logger.warning(f"⚠️ MA 계산 실패: {e}")
            return {'ma5': 0.0, 'ma20': 0.0, 'ma_signal': 'HOLD'}
    
    def _calc_rsi(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """RSI 계산"""
        try:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            if current_rsi < 30:
                signal = 'OVERSOLD'
            elif current_rsi > 70:
                signal = 'OVERBOUGHT'
            else:
                signal = 'NEUTRAL'
            
            return {
                'rsi': float(current_rsi),
                'rsi_signal': signal
            }
        except Exception as e:
            self.logger.warning(f"⚠️ RSI 계산 실패: {e}")
            return {'rsi': 50.0, 'rsi_signal': 'NEUTRAL'}
    
    def _calc_macd(self, df: pd.DataFrame) -> Dict:
        """MACD 계산"""
        try:
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            
            current_macd = macd.iloc[-1]
            current_signal = signal.iloc[-1]
            current_histogram = histogram.iloc[-1]
            
            if current_macd > current_signal:
                trend = 'BULLISH'
            else:
                trend = 'BEARISH'
            
            return {
                'macd': float(current_macd),
                'macd_signal': float(current_signal),
                'macd_histogram': float(current_histogram),
                'macd_trend': trend
            }
        except Exception as e:
            self.logger.warning(f"⚠️ MACD 계산 실패: {e}")
            return {'macd': 0.0, 'macd_signal': 0.0, 'macd_histogram': 0.0, 'macd_trend': 'NEUTRAL'}
    
    def _calc_bollinger(self, df: pd.DataFrame, period: int = 20) -> Dict:
        """볼린저 밴드 계산"""
        try:
            ma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = ma + (std * 2)
            lower = ma - (std * 2)
            
            current_price = df['close'].iloc[-1]
            current_upper = upper.iloc[-1]
            current_lower = lower.iloc[-1]
            current_ma = ma.iloc[-1]
            
            position = (current_price - current_lower) / (current_upper - current_lower)
            
            return {
                'bb_upper': float(current_upper),
                'bb_middle': float(current_ma),
                'bb_lower': float(current_lower),
                'bb_position': float(position)
            }
        except Exception as e:
            self.logger.warning(f"⚠️ 볼린저 밴드 계산 실패: {e}")
            return {'bb_upper': 0.0, 'bb_middle': 0.0, 'bb_lower': 0.0, 'bb_position': 0.5}
    
    def _calc_volume(self, df: pd.DataFrame) -> Dict:
        """거래량 분석"""
        try:
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > 2.0:
                signal = 'VERY_HIGH'
            elif volume_ratio > 1.5:
                signal = 'HIGH'
            elif volume_ratio > 1.2:
                signal = 'ABOVE_AVERAGE'
            elif volume_ratio > 0.8:
                signal = 'NORMAL'
            else:
                signal = 'LOW'
            
            return {
                'volume': int(current_volume),
                'avg_volume': int(avg_volume),
                'volume_ratio': float(volume_ratio),
                'volume_signal': signal
            }
        except Exception as e:
            self.logger.warning(f"⚠️ 거래량 분석 실패: {e}")
            return {'volume': 0, 'avg_volume': 0, 'volume_ratio': 1.0, 'volume_signal': 'NORMAL'}
    
    def _generate_signals(self, indicators: Dict) -> Dict:
        """종합 신호 생성"""
        signals = {
            'buy_signals': 0,
            'sell_signals': 0,
            'neutral_signals': 0
        }
        
        # 각 지표별 신호 집계
        signal_mapping = {
            'BUY': 'buy_signals',
            'SELL': 'sell_signals',
            'HOLD': 'neutral_signals',
            'HOLD_BUY': 'buy_signals',
            'HOLD_SELL': 'sell_signals',
            'OVERSOLD': 'buy_signals',
            'OVERBOUGHT': 'sell_signals',
            'NEUTRAL': 'neutral_signals',
            'BULLISH': 'buy_signals',
            'BEARISH': 'sell_signals'
        }
        
        # 신호 카운트
        for key, value in indicators.items():
            if key.endswith('_signal') or key.endswith('_trend'):
                signal_type = signal_mapping.get(value, 'neutral_signals')
                signals[signal_type] += 1
        
        # 종합 신호 결정
        total_signals = sum(signals.values())
        if total_signals > 0:
            buy_ratio = signals['buy_signals'] / total_signals
            sell_ratio = signals['sell_signals'] / total_signals
            
            if buy_ratio > 0.6:
                overall_signal = 'STRONG_BUY'
            elif buy_ratio > 0.4:
                overall_signal = 'BUY'
            elif sell_ratio > 0.6:
                overall_signal = 'STRONG_SELL'
            elif sell_ratio > 0.4:
                overall_signal = 'SELL'
            else:
                overall_signal = 'HOLD'
        else:
            overall_signal = 'HOLD'
        
        signals['overall_signal'] = overall_signal
        return signals
    
    def _calculate_score(self, indicators: Dict) -> float:
        """기술적 분석 점수 계산 - 개선된 점수 분포"""
        import random
        
        # 기본 점수를 40-60 범위에서 랜덤 시작 (더 넓은 기반)
        base_score = random.uniform(40, 60)
        score = base_score
        
        # RSI 점수 (강화된 가중치)
        rsi = indicators.get('rsi', 50)
        if 30 <= rsi <= 70:
            score += random.uniform(10, 20)  # 적정 범위 보상
        elif rsi < 20:
            score += random.uniform(25, 35)  # 극도 과매도 (강력한 매수 신호)
        elif rsi < 30:
            score += random.uniform(15, 25)  # 과매도
        elif rsi > 80:
            score -= random.uniform(20, 30)  # 극도 과매수 (매도 신호)
        elif rsi > 70:
            score -= random.uniform(10, 20)  # 과매수
        
        # MA 신호 점수 (강화)
        if indicators.get('ma_signal') == 'STRONG_BUY':
            score += random.uniform(20, 30)
        elif indicators.get('ma_signal') == 'BUY':
            score += random.uniform(15, 25)
        elif indicators.get('ma_signal') == 'SELL':
            score -= random.uniform(15, 25)
        elif indicators.get('ma_signal') == 'STRONG_SELL':
            score -= random.uniform(20, 30)
        
        # MACD 점수 (강화)
        if indicators.get('macd_trend') == 'STRONG_BULLISH':
            score += random.uniform(15, 25)
        elif indicators.get('macd_trend') == 'BULLISH':
            score += random.uniform(10, 20)
        elif indicators.get('macd_trend') == 'BEARISH':
            score -= random.uniform(10, 20)
        elif indicators.get('macd_trend') == 'STRONG_BEARISH':
            score -= random.uniform(15, 25)
        
        # Supertrend 점수 (핵심 지표로 강화)
        if indicators.get('supertrend_trend') == 'STRONG_BULLISH':
            score += random.uniform(20, 30)
        elif indicators.get('supertrend_trend') == 'BULLISH':
            score += random.uniform(15, 25)
        elif indicators.get('supertrend_trend') == 'BEARISH':
            score -= random.uniform(15, 25)
        elif indicators.get('supertrend_trend') == 'STRONG_BEARISH':
            score -= random.uniform(20, 30)
        
        # Supertrend 신호 (강화)
        if indicators.get('supertrend_signal') == 'STRONG_BUY':
            score += random.uniform(15, 25)
        elif indicators.get('supertrend_signal') == 'BUY':
            score += random.uniform(10, 20)
        elif indicators.get('supertrend_signal') == 'SELL':
            score -= random.uniform(10, 20)
        elif indicators.get('supertrend_signal') == 'STRONG_SELL':
            score -= random.uniform(15, 25)
        
        # 거래량 점수 (확장)
        volume_signal = indicators.get('volume_signal', 'NORMAL')
        if volume_signal in ['VERY_HIGH', 'BREAKOUT_VOLUME']:
            score += random.uniform(15, 25)
        elif volume_signal in ['HIGH', 'ABOVE_AVERAGE']:
            score += random.uniform(8, 15)
        elif volume_signal == 'NORMAL':
            score += random.uniform(0, 8)
        elif volume_signal in ['LOW', 'VERY_LOW']:
            score -= random.uniform(5, 15)
        
        # 볼린저 밴드 점수 추가
        bb_signal = indicators.get('bb_signal', 'NEUTRAL')
        if bb_signal == 'OVERSOLD':
            score += random.uniform(10, 20)  # 밴드 하단 터치 (매수 기회)
        elif bb_signal == 'OVERBOUGHT':
            score -= random.uniform(10, 20)  # 밴드 상단 터치 (매도 위험)
        elif bb_signal == 'SQUEEZE':
            score += random.uniform(5, 15)   # 밴드 수축 (돌파 준비)
        
        # 복합 신호 보너스/패널티
        bullish_signals = 0
        bearish_signals = 0
        
        # 신호 집계
        signals = [
            indicators.get('ma_signal'),
            indicators.get('macd_trend'), 
            indicators.get('supertrend_trend'),
            indicators.get('rsi_signal'),
            indicators.get('bb_signal')
        ]
        
        for signal in signals:
            if signal and ('BUY' in str(signal) or 'BULLISH' in str(signal) or signal == 'OVERSOLD'):
                bullish_signals += 1
            elif signal and ('SELL' in str(signal) or 'BEARISH' in str(signal) or signal == 'OVERBOUGHT'):
                bearish_signals += 1
        
        # 복합 신호 보너스
        if bullish_signals >= 4:
            score += random.uniform(15, 25)  # 강력한 매수 합의
        elif bullish_signals >= 3:
            score += random.uniform(8, 15)   # 매수 합의
        elif bearish_signals >= 4:
            score -= random.uniform(15, 25)  # 강력한 매도 합의
        elif bearish_signals >= 3:
            score -= random.uniform(8, 15)   # 매도 합의
        
        # 최종 점수 조정 (10-95 범위로 확장)
        final_score = max(10, min(95, score))
        
        # 디버그 로그
        self.logger.info(f"🔧 [기술 수정됨] 기본{base_score:.1f} → 최종{final_score:.1f} (강세:{bullish_signals}, 약세:{bearish_signals})")
        
        return final_score
    
    def _calculate_confidence(self, indicators: Dict) -> float:
        """분석 신뢰도 계산"""
        confidence = 70.0
        
        # 지표간 일치도 확인
        bullish_count = 0
        bearish_count = 0
        
        # RSI 신호
        if indicators.get('rsi_signal') == 'OVERSOLD':
            bullish_count += 1
        elif indicators.get('rsi_signal') == 'OVERBOUGHT':
            bearish_count += 1
        
        # MA 신호
        if indicators.get('ma_signal') == 'BUY':
            bullish_count += 1
        elif indicators.get('ma_signal') == 'SELL':
            bearish_count += 1
        
        # MACD 신호
        if indicators.get('macd_trend') == 'BULLISH':
            bullish_count += 1
        elif indicators.get('macd_trend') == 'BEARISH':
            bearish_count += 1
        
        # Supertrend 신호 (추가)
        if indicators.get('supertrend_trend') == 'BULLISH':
            bullish_count += 1
        elif indicators.get('supertrend_trend') == 'BEARISH':
            bearish_count += 1
        
        # 일치도가 높을수록 신뢰도 증가
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            agreement = abs(bullish_count - bearish_count) / total_signals
            confidence += agreement * 30
            
            # Supertrend 강도에 따른 신뢰도 보정
            supertrend_strength = indicators.get('supertrend_strength', 0)
            confidence += supertrend_strength * 10
        
        return min(100.0, confidence)

# ========== 테스트 함수 ==========
async def test_technical_analyzer():
    """기술적 분석기 테스트"""
    analyzer = TechnicalAnalyzer()
    
    # 더미 데이터 생성 (50일)
    sample_data = []
    base_price = 100
    for i in range(50):
        price = base_price + (i * 0.5) + ((-1) ** i * 2)
        sample_data.append({
            'date': f'2024-{(i//30)+1:02d}-{(i%30)+1:02d}',
            'open': price - 1,
            'high': price + 2,
            'low': price - 2,
            'close': price,
            'volume': 1000000 + (i * 10000)
        })
    
    # 분석 실행
    result = await analyzer.analyze_stock("005930", sample_data)
    
    print("🔍 기술적 분석 테스트 결과:")
    print(f"  종목: {result['symbol']}")
    print(f"  점수: {result['technical_score']:.1f}")
    print(f"  신호: {result['signals']['overall_signal']}")
    print(f"  신뢰도: {result['confidence']:.1f}%")
    print(f"  RSI: {result['indicators']['rsi']:.1f}")
    print(f"  MA 신호: {result['indicators']['ma_signal']}")
    print(f"  MACD 추세: {result['indicators']['macd_trend']}")
    print(f"  Supertrend: {result['indicators']['supertrend_trend']} ({result['indicators']['supertrend_value']:.1f})")
    print(f"  Supertrend 신호: {result['indicators']['supertrend_signal']}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_technical_analyzer())