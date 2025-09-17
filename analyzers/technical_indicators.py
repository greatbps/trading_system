"""
실제 기술적 지표 계산 엔진 (Real Technical Indicators Engine)
=====================================

Phase 2: 매매 신호 로직 최적화의 핵심 컴포넌트
기존 임시 계산식(auto_trader.py:256-261)을 실제 공식 기반 계산으로 교체

주요 지표:
- EMA (Exponential Moving Average): 지수 이동평균
- RSI (Relative Strength Index): 상대강도지수  
- MACD (Moving Average Convergence Divergence): 이동평균수렴확산
- Bollinger Bands: 볼린저 밴드
- Stochastic Oscillator: 스토캐스틱
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod


@dataclass
class TechnicalIndicatorResult:
    """기술적 지표 계산 결과"""
    indicator_name: str
    value: float
    signal: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0.0 ~ 1.0
    calculation_time: datetime
    period_used: int
    
    
@dataclass  
class PriceData:
    """가격 데이터 구조"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class TechnicalIndicatorBase(ABC):
    """기술적 지표 계산 기본 클래스"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"TechnicalIndicator.{name}")
        
    @abstractmethod
    def calculate(self, price_data: List[PriceData], **kwargs) -> TechnicalIndicatorResult:
        """지표 계산 추상 메소드"""
        pass
    
    def _validate_data(self, price_data: List[PriceData], min_periods: int) -> bool:
        """데이터 검증"""
        if not price_data:
            self.logger.error("가격 데이터가 비어있습니다")
            return False
            
        if len(price_data) < min_periods:
            self.logger.error(f"데이터 부족: 필요 {min_periods}개, 실제 {len(price_data)}개")
            return False
            
        return True


class EMAIndicator(TechnicalIndicatorBase):
    """
    EMA (Exponential Moving Average) 지수 이동평균 계산기
    
    기존 문제: ema_5 = current_price * 1.02 (완전히 잘못됨)
    실제 공식: EMA = (현재가 * 승수) + (전일 EMA * (1 - 승수))
    승수 = 2 / (기간 + 1)
    """
    
    def __init__(self):
        super().__init__("EMA")
        
    def calculate(self, price_data: List[PriceData], period: int = 5) -> TechnicalIndicatorResult:
        """EMA 계산 - 실제 지수 이동평균 공식 사용"""
        
        if not self._validate_data(price_data, period):
            return self._create_error_result(period)
            
        try:
            # 가격 리스트 추출 (최근 데이터가 마지막)
            prices = [data.close for data in price_data]
            
            # EMA 계산
            ema_value = self._calculate_ema(prices, period)
            
            # 매수/매도 신호 생성
            signal, confidence = self._generate_ema_signal(prices, ema_value, period)
            
            return TechnicalIndicatorResult(
                indicator_name=f"EMA_{period}",
                value=ema_value,
                signal=signal,
                confidence=confidence,
                calculation_time=datetime.now(),
                period_used=period
            )
            
        except Exception as e:
            self.logger.error(f"EMA 계산 오류: {e}")
            return self._create_error_result(period)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """실제 EMA 계산 로직"""
        
        if len(prices) == 0:
            return 0.0
            
        # 승수 계산: 2 / (period + 1)
        multiplier = 2.0 / (period + 1)
        
        # 초기값: SMA 사용
        if len(prices) < period:
            return sum(prices) / len(prices)  # SMA로 대체
            
        # 첫 번째 EMA는 SMA
        sma = sum(prices[:period]) / period
        ema = sma
        
        # 나머지는 EMA 공식 적용
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema * (1 - multiplier))
            
        return round(ema, 2)
    
    def _generate_ema_signal(self, prices: List[float], ema_value: float, period: int) -> Tuple[str, float]:
        """EMA 기반 매수/매도 신호 생성"""
        
        if len(prices) < 2:
            return 'hold', 0.0
            
        current_price = prices[-1]
        prev_price = prices[-2]
        
        # 가격이 EMA를 상향 돌파하면 매수 신호
        if prev_price <= ema_value and current_price > ema_value:
            confidence = min(0.8, abs(current_price - ema_value) / ema_value)
            return 'buy', confidence
            
        # 가격이 EMA를 하향 돌파하면 매도 신호  
        elif prev_price >= ema_value and current_price < ema_value:
            confidence = min(0.8, abs(ema_value - current_price) / ema_value)
            return 'sell', confidence
            
        else:
            return 'hold', 0.1
    
    def _create_error_result(self, period: int) -> TechnicalIndicatorResult:
        """에러 결과 생성"""
        return TechnicalIndicatorResult(
            indicator_name=f"EMA_{period}",
            value=0.0,
            signal='hold',
            confidence=0.0,
            calculation_time=datetime.now(),
            period_used=period
        )


class RSIIndicator(TechnicalIndicatorBase):
    """
    RSI (Relative Strength Index) 상대강도지수 계산기
    
    기존 문제: rsi = 50 + (change_rate * 2) (RSI 공식과 전혀 무관)
    실제 공식: RSI = 100 - (100 / (1 + RS))
    RS = 평균 상승폭 / 평균 하락폭 (일반적으로 14일)
    """
    
    def __init__(self):
        super().__init__("RSI")
        
    def calculate(self, price_data: List[PriceData], period: int = 14) -> TechnicalIndicatorResult:
        """RSI 계산 - 실제 상대강도지수 공식 사용"""
        
        if not self._validate_data(price_data, period + 1):  # 변화율 계산을 위해 +1
            return self._create_error_result(period)
            
        try:
            # 가격 리스트 추출
            prices = [data.close for data in price_data]
            
            # RSI 계산
            rsi_value = self._calculate_rsi(prices, period)
            
            # 매수/매도 신호 생성
            signal, confidence = self._generate_rsi_signal(rsi_value)
            
            return TechnicalIndicatorResult(
                indicator_name=f"RSI_{period}",
                value=rsi_value,
                signal=signal,
                confidence=confidence,
                calculation_time=datetime.now(),
                period_used=period
            )
            
        except Exception as e:
            self.logger.error(f"RSI 계산 오류: {e}")
            return self._create_error_result(period)
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """실제 RSI 계산 로직"""
        
        if len(prices) < period + 1:
            return 50.0  # 중립값 반환
            
        # 일별 변화율 계산
        changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            changes.append(change)
        
        if len(changes) < period:
            return 50.0
            
        # 상승/하락 분리
        gains = [change if change > 0 else 0 for change in changes]
        losses = [-change if change < 0 else 0 for change in changes]
        
        # 첫 번째 평균 상승/하락 (SMA)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # 나머지 기간은 지수 평활화 적용 (Wilder's Smoothing)
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # RS 계산
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        
        # RSI 계산
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        return round(rsi, 2)
    
    def _generate_rsi_signal(self, rsi_value: float) -> Tuple[str, float]:
        """RSI 기반 매수/매도 신호 생성"""
        
        # 과매도 구간 (30 이하) - 매수 신호
        if rsi_value <= 30:
            confidence = (30 - rsi_value) / 30  # 낮을수록 강한 신호
            return 'buy', min(0.9, confidence)
            
        # 과매수 구간 (70 이상) - 매도 신호
        elif rsi_value >= 70:
            confidence = (rsi_value - 70) / 30  # 높을수록 강한 신호  
            return 'sell', min(0.9, confidence)
            
        # 중립 구간
        else:
            return 'hold', 0.1
    
    def _create_error_result(self, period: int) -> TechnicalIndicatorResult:
        """에러 결과 생성"""
        return TechnicalIndicatorResult(
            indicator_name=f"RSI_{period}",
            value=50.0,
            signal='hold',
            confidence=0.0,
            calculation_time=datetime.now(),
            period_used=period
        )


class MACDIndicator(TechnicalIndicatorBase):
    """
    MACD (Moving Average Convergence Divergence) 이동평균수렴확산 계산기
    
    기존 문제: macd = (ema_5 - ema_20) * 0.1 (가짜 EMA 기반)
    실제 공식: 
    - MACD Line = EMA(12) - EMA(26)  
    - Signal Line = EMA(MACD, 9)
    - Histogram = MACD Line - Signal Line
    """
    
    def __init__(self):
        super().__init__("MACD")
        
    def calculate(self, price_data: List[PriceData], 
                 fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, TechnicalIndicatorResult]:
        """MACD 계산 - 실제 이동평균수렴확산 공식 사용"""
        
        if not self._validate_data(price_data, slow_period + signal_period):
            return self._create_error_results(fast_period, slow_period, signal_period)
            
        try:
            # 가격 리스트 추출
            prices = [data.close for data in price_data]
            
            # EMA 계산기 인스턴스
            ema_calc = EMAIndicator()
            
            # 빠른 EMA와 느린 EMA 계산
            fast_ema = ema_calc._calculate_ema(prices, fast_period)
            slow_ema = ema_calc._calculate_ema(prices, slow_period)
            
            # MACD Line 계산
            macd_line = fast_ema - slow_ema
            
            # Signal Line 계산 (MACD Line의 EMA)
            macd_values = self._calculate_macd_series(prices, fast_period, slow_period)
            signal_line = ema_calc._calculate_ema(macd_values, signal_period)
            
            # Histogram 계산
            histogram = macd_line - signal_line
            
            # 신호 생성
            signal, confidence = self._generate_macd_signal(macd_line, signal_line, histogram)
            
            # 결과 반환
            return {
                'macd_line': TechnicalIndicatorResult(
                    indicator_name="MACD_Line",
                    value=round(macd_line, 2),
                    signal=signal,
                    confidence=confidence,
                    calculation_time=datetime.now(),
                    period_used=fast_period
                ),
                'signal_line': TechnicalIndicatorResult(
                    indicator_name="MACD_Signal",
                    value=round(signal_line, 2),
                    signal=signal,
                    confidence=confidence * 0.5,
                    calculation_time=datetime.now(),
                    period_used=signal_period
                ),
                'histogram': TechnicalIndicatorResult(
                    indicator_name="MACD_Histogram", 
                    value=round(histogram, 2),
                    signal=signal,
                    confidence=confidence,
                    calculation_time=datetime.now(),
                    period_used=signal_period
                )
            }
            
        except Exception as e:
            self.logger.error(f"MACD 계산 오류: {e}")
            return self._create_error_results(fast_period, slow_period, signal_period)
    
    def _calculate_macd_series(self, prices: List[float], fast_period: int, slow_period: int) -> List[float]:
        """MACD 시리즈 계산 (Signal Line 계산용)"""
        
        ema_calc = EMAIndicator()
        macd_series = []
        
        # 충분한 데이터가 있는 구간부터 계산
        for i in range(slow_period - 1, len(prices)):
            sub_prices = prices[:i+1]
            fast_ema = ema_calc._calculate_ema(sub_prices, fast_period)
            slow_ema = ema_calc._calculate_ema(sub_prices, slow_period)
            macd_value = fast_ema - slow_ema
            macd_series.append(macd_value)
            
        return macd_series
    
    def _generate_macd_signal(self, macd_line: float, signal_line: float, histogram: float) -> Tuple[str, float]:
        """MACD 기반 매수/매도 신호 생성"""
        
        # MACD Line이 Signal Line을 상향 돌파 - 매수 신호
        if macd_line > signal_line and histogram > 0:
            confidence = min(0.8, abs(histogram) / abs(macd_line) if macd_line != 0 else 0)
            return 'buy', confidence
            
        # MACD Line이 Signal Line을 하향 돌파 - 매도 신호
        elif macd_line < signal_line and histogram < 0:
            confidence = min(0.8, abs(histogram) / abs(macd_line) if macd_line != 0 else 0)
            return 'sell', confidence
            
        else:
            return 'hold', 0.1
    
    def _create_error_results(self, fast_period: int, slow_period: int, signal_period: int) -> Dict[str, TechnicalIndicatorResult]:
        """에러 결과 생성"""
        error_time = datetime.now()
        return {
            'macd_line': TechnicalIndicatorResult("MACD_Line", 0.0, 'hold', 0.0, error_time, fast_period),
            'signal_line': TechnicalIndicatorResult("MACD_Signal", 0.0, 'hold', 0.0, error_time, signal_period),
            'histogram': TechnicalIndicatorResult("MACD_Histogram", 0.0, 'hold', 0.0, error_time, signal_period)
        }
    
    def _create_error_result(self, period: int) -> TechnicalIndicatorResult:
        """단일 에러 결과 생성"""
        return TechnicalIndicatorResult(
            indicator_name="MACD",
            value=0.0,
            signal='hold', 
            confidence=0.0,
            calculation_time=datetime.now(),
            period_used=period
        )


class RealTechnicalIndicators:
    """
    실제 기술적 지표 통합 계산 엔진
    
    기존 auto_trader.py의 임시 계산식을 완전히 대체하는 시스템
    """
    
    def __init__(self):
        self.logger = logging.getLogger("RealTechnicalIndicators")
        
        # 지표 계산기들
        self.ema_calculator = EMAIndicator()
        self.rsi_calculator = RSIIndicator() 
        self.macd_calculator = MACDIndicator()
        
        # 계산 결과 캐시 (성능 최적화)
        self.calculation_cache = {}
        
    def calculate_all_indicators(self, symbol: str, price_data: List[PriceData]) -> Dict[str, any]:
        """
        모든 기술적 지표를 한 번에 계산
        
        Args:
            symbol: 종목 코드
            price_data: 과거 가격 데이터 리스트 (최소 30일 권장)
            
        Returns:
            기존 auto_trader.py의 _get_technical_data() 형식과 호환되는 결과
        """
        
        try:
            if not price_data:
                self.logger.error(f"{symbol}: 가격 데이터가 없습니다")
                return self._get_fallback_result()
                
            # 현재가 정보
            current_price = price_data[-1].close
            volume = price_data[-1].volume
            
            # 변화율 계산 (전일 대비)
            if len(price_data) >= 2:
                prev_price = price_data[-2].close
                change_rate = (current_price - prev_price) / prev_price * 100
            else:
                change_rate = 0.0
            
            # 평균 거래량 계산 (최근 20일)
            volume_period = min(20, len(price_data))
            volume_avg = sum(data.volume for data in price_data[-volume_period:]) / volume_period
            
            # EMA 계산 (5일, 20일)
            ema_5_result = self.ema_calculator.calculate(price_data, period=5)
            ema_20_result = self.ema_calculator.calculate(price_data, period=20)
            
            # RSI 계산 (14일)
            rsi_result = self.rsi_calculator.calculate(price_data, period=14)
            
            # MACD 계산
            macd_results = self.macd_calculator.calculate(price_data)
            
            # 종합 신호 생성
            composite_signal = self._generate_composite_signal([
                ema_5_result, ema_20_result, rsi_result, macd_results['macd_line']
            ])
            
            # 결과 구성 (기존 형식 호환)
            result = {
                'current_price': current_price,
                'volume': volume,
                'volume_avg': volume_avg,  # 평균 거래량 추가
                'change_rate': change_rate,
                'ema_5': ema_5_result.value,
                'ema_20': ema_20_result.value,
                'rsi': rsi_result.value,
                'macd_line': macd_results['macd_line'].value,
                'macd_signal': macd_results['signal_line'].value,
                'macd_histogram': macd_results['histogram'].value,
                
                # 추가 정보 (신호 분석용)
                'signals': {
                    'ema_5_signal': ema_5_result.signal,
                    'ema_20_signal': ema_20_result.signal,
                    'rsi_signal': rsi_result.signal,
                    'macd_signal': macd_results['macd_line'].signal,
                    'composite_signal': composite_signal['signal'],
                    'composite_confidence': composite_signal['confidence']
                },
                
                'calculation_time': datetime.now().isoformat(),
                'data_quality': 'real_calculation'  # 실제 계산임을 표시
            }
            
            self.logger.info(f"{symbol}: 실제 기술적 지표 계산 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"{symbol}: 기술적 지표 계산 실패 - {e}")
            return self._get_fallback_result()
    
    def _generate_composite_signal(self, indicator_results: List[TechnicalIndicatorResult]) -> Dict[str, any]:
        """다중 지표 종합 신호 생성"""
        
        buy_signals = 0
        sell_signals = 0
        total_confidence = 0.0
        
        for result in indicator_results:
            if result.signal == 'buy':
                buy_signals += 1
                total_confidence += result.confidence
            elif result.signal == 'sell':
                sell_signals += 1
                total_confidence += result.confidence
        
        total_signals = buy_signals + sell_signals
        
        if total_signals == 0:
            return {'signal': 'hold', 'confidence': 0.0}
        
        # 신호 방향 결정
        if buy_signals > sell_signals:
            signal = 'buy'
            confidence = total_confidence / len(indicator_results) * (buy_signals / total_signals)
        elif sell_signals > buy_signals:
            signal = 'sell'
            confidence = total_confidence / len(indicator_results) * (sell_signals / total_signals)
        else:
            signal = 'hold'
            confidence = total_confidence / len(indicator_results) * 0.5
        
        return {
            'signal': signal,
            'confidence': min(0.9, confidence),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals
        }
    
    def _get_fallback_result(self) -> Dict[str, any]:
        """계산 실패 시 기본값 반환"""
        return {
            'current_price': 0,
            'volume': 0,
            'volume_avg': 0,  # 평균 거래량 추가
            'change_rate': 0,
            'ema_5': 0,
            'ema_20': 0,
            'rsi': 50,  # 중립값
            'macd_line': 0,
            'macd_signal': 0,
            'macd_histogram': 0,
            'signals': {
                'ema_5_signal': 'hold',
                'ema_20_signal': 'hold', 
                'rsi_signal': 'hold',
                'macd_signal': 'hold',
                'composite_signal': 'hold',
                'composite_confidence': 0.0
            },
            'calculation_time': datetime.now().isoformat(),
            'data_quality': 'fallback'  # 실패한 계산임을 표시
        }


# 사용 예제 및 테스트 함수
def test_technical_indicators():
    """기술적 지표 계산 테스트"""
    
    # 테스트용 가격 데이터 생성 (삼성전자 가상 데이터)
    test_prices = [65000, 65200, 64800, 66000, 66500, 65800, 67000, 
                  66800, 67500, 68000, 67200, 68500, 69000, 68800, 
                  69500, 70000, 69800, 70200, 71000, 70500, 71500]
    
    price_data = []
    base_date = datetime.now() - timedelta(days=len(test_prices)-1)
    
    for i, price in enumerate(test_prices):
        data = PriceData(
            timestamp=base_date + timedelta(days=i),
            open=price - 100,
            high=price + 200,
            low=price - 200, 
            close=price,
            volume=1000000
        )
        price_data.append(data)
    
    # 실제 계산 엔진 테스트
    calculator = RealTechnicalIndicators()
    result = calculator.calculate_all_indicators("005930", price_data)
    
    print("=== 실제 기술적 지표 계산 결과 ===")
    print(f"현재가: {result['current_price']:,}원")
    print(f"EMA 5일: {result['ema_5']:,.2f}원") 
    print(f"EMA 20일: {result['ema_20']:,.2f}원")
    print(f"RSI 14일: {result['rsi']:.2f}")
    print(f"MACD Line: {result['macd_line']:.2f}")
    print(f"종합 신호: {result['signals']['composite_signal']} (신뢰도: {result['signals']['composite_confidence']:.2f})")
    
    return result


if __name__ == "__main__":
    # 테스트 실행
    test_result = test_technical_indicators()