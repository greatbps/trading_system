"""
거래량 분석 시스템 (Volume Analyzer)
==================================

실제 매매에서 가장 중요한 거래량 평가 지표들을 종합 분석
현재 시스템에서 부족한 거래량 평가 항목을 보완

주요 기능:
- 거래량 급증/감소 패턴 분석
- 평균 거래량 대비 상대적 평가
- 가격-거래량 상관관계 분석
- 거래량 기반 신호 강도 평가
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from analyzers.technical_indicators import PriceData
import logging


@dataclass
class VolumeAnalysisResult:
    """거래량 분석 결과"""
    symbol: str
    current_volume: int
    avg_volume_5d: float
    avg_volume_20d: float
    
    # 거래량 비율 지표
    volume_ratio_5d: float    # 5일 평균 대비
    volume_ratio_20d: float   # 20일 평균 대비
    
    # 거래량 패턴
    volume_trend: str         # 'increasing', 'decreasing', 'stable'
    volume_surge: bool        # 거래량 급증 (20일 평균 대비 2배 이상)
    volume_breakout: bool     # 거래량 돌파 (최근 고점 돌파)
    
    # 가격-거래량 분석
    price_volume_confirm: bool  # 가격 상승 + 거래량 증가
    distribution_pattern: bool  # 가격 상승 + 거래량 감소 (분산 패턴)
    accumulation_pattern: bool  # 가격 하락 + 거래량 증가 (수집 패턴)
    
    # 종합 점수
    volume_score: float       # 0~100점 거래량 종합 점수
    signal_strength: str      # 'strong', 'moderate', 'weak'
    
    calculation_time: datetime


class VolumeAnalyzer:
    """
    거래량 분석 전문 시스템
    
    실제 매매에서 가장 중요하지만 현재 시스템에서 부족한
    거래량 분석 기능을 전문적으로 제공
    """
    
    def __init__(self):
        self.logger = logging.getLogger("VolumeAnalyzer")
        
        # 거래량 분석 임계값
        self.volume_surge_threshold = 2.0      # 20일 평균 대비 2배
        self.volume_breakout_threshold = 1.5   # 5일 평균 대비 1.5배
        self.high_volume_threshold = 3.0       # 20일 평균 대비 3배 (극도 급증)
        
    def analyze_volume(self, symbol: str, price_data: List[PriceData]) -> Optional[VolumeAnalysisResult]:
        """
        종합 거래량 분석
        
        Args:
            symbol: 종목 코드
            price_data: 과거 가격/거래량 데이터 (최소 20일 권장)
            
        Returns:
            VolumeAnalysisResult: 종합 거래량 분석 결과
        """
        
        try:
            if not price_data or len(price_data) < 5:
                self.logger.warning(f"{symbol}: 거래량 분석용 데이터 부족 ({len(price_data) if price_data else 0}일)")
                return None
            
            # 거래량 데이터 추출
            volumes = [data.volume for data in price_data]
            prices = [data.close for data in price_data]
            
            current_volume = volumes[-1]
            current_price = prices[-1]
            
            # 평균 거래량 계산
            avg_volume_5d = self._calculate_average_volume(volumes, 5)
            avg_volume_20d = self._calculate_average_volume(volumes, 20)
            
            # 거래량 비율
            volume_ratio_5d = current_volume / avg_volume_5d if avg_volume_5d > 0 else 0
            volume_ratio_20d = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
            
            # 거래량 패턴 분석
            volume_trend = self._analyze_volume_trend(volumes)
            volume_surge = volume_ratio_20d >= self.volume_surge_threshold
            volume_breakout = self._check_volume_breakout(volumes)
            
            # 가격-거래량 상관관계 분석
            price_volume_confirm = self._check_price_volume_confirmation(prices, volumes)
            distribution_pattern = self._check_distribution_pattern(prices, volumes)
            accumulation_pattern = self._check_accumulation_pattern(prices, volumes)
            
            # 종합 점수 계산
            volume_score = self._calculate_volume_score(
                volume_ratio_20d, volume_trend, volume_surge, 
                price_volume_confirm, distribution_pattern, accumulation_pattern
            )
            
            # 신호 강도 결정
            if volume_score >= 80:
                signal_strength = 'strong'
            elif volume_score >= 60:
                signal_strength = 'moderate'
            else:
                signal_strength = 'weak'
            
            result = VolumeAnalysisResult(
                symbol=symbol,
                current_volume=current_volume,
                avg_volume_5d=avg_volume_5d,
                avg_volume_20d=avg_volume_20d,
                volume_ratio_5d=volume_ratio_5d,
                volume_ratio_20d=volume_ratio_20d,
                volume_trend=volume_trend,
                volume_surge=volume_surge,
                volume_breakout=volume_breakout,
                price_volume_confirm=price_volume_confirm,
                distribution_pattern=distribution_pattern,
                accumulation_pattern=accumulation_pattern,
                volume_score=volume_score,
                signal_strength=signal_strength,
                calculation_time=datetime.now()
            )
            
            self.logger.debug(f"{symbol}: 거래량 분석 완료 (점수: {volume_score:.1f}, 강도: {signal_strength})")
            return result
            
        except Exception as e:
            self.logger.error(f"{symbol}: 거래량 분석 실패 - {e}")
            return None
    
    def _calculate_average_volume(self, volumes: List[int], period: int) -> float:
        """평균 거래량 계산"""
        
        if len(volumes) < period:
            period = len(volumes)
        
        if period == 0:
            return 0.0
            
        return sum(volumes[-period:]) / period
    
    def _analyze_volume_trend(self, volumes: List[int], period: int = 5) -> str:
        """거래량 트렌드 분석"""
        
        if len(volumes) < period * 2:
            return 'stable'
        
        # 최근 N일과 이전 N일 평균 비교
        recent_avg = sum(volumes[-period:]) / period
        previous_avg = sum(volumes[-period*2:-period]) / period
        
        if recent_avg > previous_avg * 1.2:
            return 'increasing'
        elif recent_avg < previous_avg * 0.8:
            return 'decreasing'
        else:
            return 'stable'
    
    def _check_volume_breakout(self, volumes: List[int], lookback: int = 10) -> bool:
        """거래량 돌파 확인"""
        
        if len(volumes) < lookback + 1:
            return False
        
        current_volume = volumes[-1]
        recent_max = max(volumes[-lookback-1:-1])
        
        return current_volume > recent_max * 1.1  # 10% 이상 돌파
    
    def _check_price_volume_confirmation(self, prices: List[float], volumes: List[int]) -> bool:
        """가격-거래량 확인 패턴"""
        
        if len(prices) < 3 or len(volumes) < 3:
            return False
        
        # 최근 3일 가격 상승 + 거래량 증가
        price_rising = prices[-1] > prices[-2] > prices[-3]
        volume_rising = volumes[-1] > volumes[-2] > volumes[-3]
        
        return price_rising and volume_rising
    
    def _check_distribution_pattern(self, prices: List[float], volumes: List[int]) -> bool:
        """분산 패턴 (가격 상승 + 거래량 감소)"""
        
        if len(prices) < 3 or len(volumes) < 3:
            return False
        
        # 가격은 상승하지만 거래량은 감소 (분산 신호)
        price_rising = prices[-1] > prices[-2] and prices[-2] > prices[-3]
        volume_declining = volumes[-1] < volumes[-2] < volumes[-3]
        
        return price_rising and volume_declining
    
    def _check_accumulation_pattern(self, prices: List[float], volumes: List[int]) -> bool:
        """수집 패턴 (가격 하락 + 거래량 증가)"""
        
        if len(prices) < 3 or len(volumes) < 3:
            return False
        
        # 가격은 하락하지만 거래량은 증가 (수집 신호)
        price_declining = prices[-1] < prices[-2] and prices[-2] < prices[-3]
        volume_rising = volumes[-1] > volumes[-2] > volumes[-3]
        
        return price_declining and volume_rising
    
    def _calculate_volume_score(self, volume_ratio: float, trend: str, surge: bool,
                              confirm: bool, distribution: bool, accumulation: bool) -> float:
        """거래량 종합 점수 계산 (0-100점)"""
        
        score = 0.0
        
        # 1. 거래량 비율 점수 (40점)
        if volume_ratio >= 3.0:
            score += 40
        elif volume_ratio >= 2.0:
            score += 30
        elif volume_ratio >= 1.5:
            score += 20
        elif volume_ratio >= 1.0:
            score += 10
        
        # 2. 거래량 트렌드 점수 (20점)
        if trend == 'increasing':
            score += 20
        elif trend == 'stable':
            score += 10
        # decreasing은 0점
        
        # 3. 패턴 점수 (40점)
        if confirm:  # 가격-거래량 확인
            score += 25
        if accumulation:  # 수집 패턴
            score += 15
        if distribution:  # 분산 패턴 (부정적)
            score -= 10
        
        # 보너스
        if surge:  # 거래량 급증
            score += 10
        
        return max(0, min(100, score))


class MonitoringScoreCalculator:
    """
    모니터링 종목 종합 점수 계산기
    
    1시간마다 실행하여 Buy 신호 유지 여부를 판단
    """
    
    def __init__(self, technical_indicators, volume_analyzer):
        self.technical_indicators = technical_indicators
        self.volume_analyzer = volume_analyzer
        self.logger = logging.getLogger("MonitoringScoreCalculator")
        
        # 점수 가중치
        self.weights = {
            'technical_score': 0.4,     # 기술적 지표 40%
            'volume_score': 0.3,        # 거래량 분석 30%
            'trend_score': 0.2,         # 추세 분석 20%
            'momentum_score': 0.1       # 모멘텀 분석 10%
        }
        
        # 감시 제외 임계점
        self.removal_threshold = 40.0  # 40점 이하 시 감시 제외
        
    async def calculate_monitoring_score(self, symbol: str, chart_data: List[PriceData]) -> Dict[str, any]:
        """
        모니터링 종목 종합 점수 계산
        
        Returns:
            Dict: {
                'total_score': float,     # 종합 점수 (0-100)
                'keep_monitoring': bool,  # 계속 모니터링 여부  
                'detailed_scores': dict,  # 세부 점수들
                'reason': str            # 판단 근거
            }
        """
        
        try:
            # 1. 기술적 지표 분석
            tech_result = self.technical_indicators.calculate_all_indicators(symbol, chart_data)
            tech_score = self._calculate_technical_score(tech_result)
            
            # 2. 거래량 분석
            volume_result = self.volume_analyzer.analyze_volume(symbol, chart_data)
            volume_score = volume_result.volume_score if volume_result else 0
            
            # 3. 추세 분석
            trend_score = self._calculate_trend_score(chart_data)
            
            # 4. 모멘텀 분석  
            momentum_score = self._calculate_momentum_score(chart_data)
            
            # 5. 종합 점수 계산
            detailed_scores = {
                'technical_score': tech_score,
                'volume_score': volume_score,
                'trend_score': trend_score,
                'momentum_score': momentum_score
            }
            
            total_score = (
                tech_score * self.weights['technical_score'] +
                volume_score * self.weights['volume_score'] +
                trend_score * self.weights['trend_score'] +
                momentum_score * self.weights['momentum_score']
            )
            
            # 6. 감시 계속 여부 판단
            keep_monitoring = total_score >= self.removal_threshold
            
            # 7. 판단 근거
            if not keep_monitoring:
                reason = f"종합점수 {total_score:.1f}점으로 임계점 {self.removal_threshold}점 미달"
            else:
                reason = f"종합점수 {total_score:.1f}점으로 감시 조건 유지"
            
            # 추가 제외 조건들
            if tech_result and tech_result.get('signals', {}).get('composite_signal') == 'sell':
                keep_monitoring = False
                reason += " + 매도 신호 발생"
            
            if volume_result and volume_result.distribution_pattern:
                total_score -= 10  # 분산 패턴 페널티
                reason += " + 분산 패턴 감지"
            
            result = {
                'total_score': round(total_score, 1),
                'keep_monitoring': keep_monitoring,
                'detailed_scores': detailed_scores,
                'reason': reason,
                'calculation_time': datetime.now().isoformat()
            }
            
            self.logger.info(f"{symbol}: 모니터링 점수 {total_score:.1f} ({'유지' if keep_monitoring else '제외'})")
            return result
            
        except Exception as e:
            self.logger.error(f"{symbol}: 모니터링 점수 계산 실패 - {e}")
            return {
                'total_score': 0.0,
                'keep_monitoring': False,
                'detailed_scores': {},
                'reason': f"계산 실패: {str(e)}",
                'calculation_time': datetime.now().isoformat()
            }
    
    def _calculate_technical_score(self, tech_result: Dict) -> float:
        """기술적 지표 점수 계산"""
        
        if not tech_result or not tech_result.get('signals'):
            return 0.0
        
        signals = tech_result['signals']
        composite_signal = signals.get('composite_signal', 'hold')
        composite_confidence = signals.get('composite_confidence', 0.0)
        
        if composite_signal == 'buy':
            return 60 + (composite_confidence * 40)  # 60-100점
        elif composite_signal == 'hold':
            return 30 + (composite_confidence * 30)  # 30-60점
        else:  # sell
            return 0 + (composite_confidence * 20)   # 0-20점
    
    def _calculate_trend_score(self, chart_data: List[PriceData]) -> float:
        """추세 점수 계산"""
        
        if len(chart_data) < 10:
            return 50.0  # 중립
        
        prices = [data.close for data in chart_data]
        
        # 단기 추세 (5일)
        short_trend = (prices[-1] - prices[-5]) / prices[-5] * 100
        
        # 장기 추세 (10일)  
        long_trend = (prices[-1] - prices[-10]) / prices[-10] * 100
        
        trend_score = 50  # 기본 점수
        
        if short_trend > 5 and long_trend > 3:
            trend_score = 90  # 강한 상승
        elif short_trend > 2 and long_trend > 1:
            trend_score = 70  # 상승
        elif short_trend > -2 and long_trend > -1:
            trend_score = 50  # 중립
        elif short_trend > -5 and long_trend > -3:
            trend_score = 30  # 하락
        else:
            trend_score = 10  # 강한 하락
        
        return trend_score
    
    def _calculate_momentum_score(self, chart_data: List[PriceData]) -> float:
        """모멘텀 점수 계산"""
        
        if len(chart_data) < 5:
            return 50.0
        
        prices = [data.close for data in chart_data]
        volumes = [data.volume for data in chart_data]
        
        # 가격 모멘텀
        price_momentum = (prices[-1] - prices[-3]) / prices[-3] * 100
        
        # 거래량 모멘텀
        volume_momentum = (volumes[-1] - volumes[-3]) / volumes[-3] * 100
        
        momentum_score = 50  # 기본 점수
        
        if price_momentum > 3 and volume_momentum > 20:
            momentum_score = 90  # 강한 모멘텀
        elif price_momentum > 1 and volume_momentum > 0:
            momentum_score = 70  # 양호한 모멘텀
        elif price_momentum > -1 and volume_momentum > -20:
            momentum_score = 50  # 중립
        else:
            momentum_score = 20  # 약한 모멘텀
        
        return momentum_score


# 테스트 함수
async def test_volume_analyzer():
    """거래량 분석기 테스트"""
    
    print("=== Volume Analyzer Test ===")
    
    # 테스트 데이터 생성
    test_data = []
    base_volume = 10000000  # 1천만주
    
    for i in range(25):
        # 최근 5일간 거래량 급증 시뮬레이션
        if i >= 20:
            volume = base_volume * (2.0 + i * 0.1)  # 급증
        else:
            volume = base_volume * (0.8 + i * 0.01)  # 점진적 증가
        
        price_data = PriceData(
            timestamp=datetime.now() - timedelta(days=24-i),
            open=50000,
            high=52000,
            low=48000,
            close=50000 + i * 100,  # 가격도 상승
            volume=int(volume)
        )
        test_data.append(price_data)
    
    # 거래량 분석 실행
    analyzer = VolumeAnalyzer()
    result = analyzer.analyze_volume("TEST", test_data)
    
    if result:
        print(f"Current Volume: {result.current_volume:,}")
        print(f"20-day Average: {result.avg_volume_20d:,.0f}")
        print(f"Volume Ratio (20d): {result.volume_ratio_20d:.1f}x")
        print(f"Volume Surge: {result.volume_surge}")
        print(f"Price-Volume Confirm: {result.price_volume_confirm}")
        print(f"Volume Score: {result.volume_score:.1f}/100")
        print(f"Signal Strength: {result.signal_strength}")
        print("[SUCCESS] Volume analyzer is working!")
    else:
        print("[ERROR] Volume analysis failed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_volume_analyzer())