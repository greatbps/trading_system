#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/chart_pattern_analyzer.py

차트패턴 분석기 - 캔들패턴 및 기술적 패턴 인식
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import get_logger

class ChartPatternAnalyzer:
    """차트패턴 분석기 - 캔들패턴 및 기술적 패턴 인식"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("ChartPatternAnalyzer")
        
        # 패턴 감지기 초기화
        try:
            from utils.pattern_detector import PatternDetector
            self.pattern_detector = PatternDetector(config)
            self.logger.info("✅ 패턴 감지기 초기화 완료")
        except ImportError as e:
            self.logger.warning(f"⚠️ 패턴 감지기 초기화 실패: {e}")
            self.pattern_detector = None
        
        # 패턴별 점수 매핑
        self.pattern_scores = {
            # 강세 패턴
            'hammer': 75,
            'inverted_hammer': 70,
            'bullish_engulfing': 80,
            'morning_star': 85,
            'piercing_line': 75,
            'three_white_soldiers': 85,
            'ascending_triangle': 75,
            'cup_and_handle': 80,
            'double_bottom': 75,
            'head_and_shoulders_inverse': 80,
            
            # 약세 패턴
            'hanging_man': 25,
            'shooting_star': 30,
            'bearish_engulfing': 20,
            'evening_star': 15,
            'dark_cloud_cover': 25,
            'three_black_crows': 15,
            'descending_triangle': 25,
            'double_top': 25,
            'head_and_shoulders': 20,
            
            # 중립 패턴
            'doji': 50,
            'spinning_top': 50,
            'inside_bar': 50,
            'outside_bar': 55,
            'rectangle': 50,
            'symmetrical_triangle': 50
        }
    
    def safe_get_attr(self, data, attr_name, default=None):
        """안전한 속성 접근 유틸리티 (chart_pattern_analyzer용)"""
        try:
            if isinstance(data, dict):
                return data.get(attr_name, default)
            else:
                return getattr(data, attr_name, default)
        except (AttributeError, TypeError):
            return default
        
    # chart_pattern_analyzer.py에서 수정

    def analyze(self, stock_data: Any) -> Dict[str, Any]:
        """차트패턴 종합 분석 - None 처리 강화"""
        try:
            # 안전한 속성 접근으로 종목 정보 추출
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            name = self.safe_get_attr(stock_data, 'name', symbol)
            
            # 종목명 보정
            if name == 'UNKNOWN' or not name or str(name).isdigit():
                name = symbol
            
            self.logger.info(f"📈 차트패턴 분석 시작 - {symbol} ({name})")
            
            # 차트 데이터 유효성 검사
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            
            if current_price <= 0:
                self.logger.warning(f"⚠️ {symbol} ({name}) 유효하지 않은 가격 데이터: {current_price}")
                return self._create_default_pattern_result(symbol, name, "가격 데이터 부족")
            
            # 패턴 감지기 호출
            if self.pattern_detector:
                try:
                    # 패턴 감지기가 async인 경우 동기적으로 처리
                    pattern_results = self.pattern_detector.detect_patterns(
                        stock_data, 
                        symbol=symbol, 
                        name=name
                    )
                    
                    # === 중요: None 체크 추가 ===
                    if pattern_results is None:
                        self.logger.warning(f"⚠️ {symbol} ({name}) 패턴 감지기가 None 반환")
                        return self._create_default_pattern_result(symbol, name, "패턴 감지 결과 없음")
                    
                    # detected_patterns 체크
                    detected_patterns = pattern_results.get('detected_patterns', [])
                    overall_score = pattern_results.get('overall_score', 50.0)
                    pattern_count = len(detected_patterns) if detected_patterns else 0
                    
                    if pattern_count > 0:
                        self.logger.info(f"✅ {symbol} ({name}) 패턴 분석 완료: {pattern_count}개 패턴, 점수: {overall_score:.1f}")
                        
                        return {
                            'overall_score': overall_score,
                            'candle_pattern_score': overall_score,
                            'technical_pattern_score': overall_score,
                            'trendline_score': 50.0,
                            'support_resistance_score': 50.0,
                            'pattern_strength': min(1.0, pattern_count / 3),
                            'confidence': min(0.9, 0.4 + pattern_count * 0.15),
                            'detected_patterns': [p.get('name', 'unknown') for p in detected_patterns],
                            'pattern_recommendation': self._get_pattern_recommendation(pattern_results),
                            'analysis_status': 'enhanced',
                            'symbol': symbol,
                            'name': name
                        }
                    else:
                        self.logger.info(f"📊 {symbol} ({name}) 패턴 감지 결과: 명확한 패턴 없음")
                        return self._create_basic_pattern_result(symbol, name, stock_data)
                        
                except Exception as e:
                    self.logger.error(f"❌ {symbol} ({name}) 패턴 감지 실패: {e}")
                    return self._create_default_pattern_result(symbol, name, f"패턴 감지 오류: {e}")
            else:
                self.logger.info(f"📊 {symbol} ({name}) 기본 패턴 분석 사용 (패턴 감지기 없음)")
                return self._create_basic_pattern_result(symbol, name, stock_data)
            
        except Exception as e:
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            name = self.safe_get_attr(stock_data, 'name', symbol)
            self.logger.error(f"❌ {symbol} ({name}) 차트패턴 분석 실패: {e}")
            return self._create_default_pattern_result(symbol, name, f"분석 오류: {e}")

    def _create_default_pattern_result(self, symbol: str, name: str, reason: str) -> Dict:
        """기본 패턴 분석 결과 생성"""
        self.logger.info(f"📊 {symbol} ({name}) 기본 패턴 결과 생성: {reason}")
        
        return {
            'overall_score': 50.0,
            'candle_pattern_score': 50.0,
            'technical_pattern_score': 50.0,
            'trendline_score': 50.0,
            'support_resistance_score': 50.0,
            'pattern_strength': 0.5,
            'confidence': 0.3,
            'detected_patterns': [],
            'pattern_recommendation': {'action': 'HOLD', 'reason': reason},
            'analysis_status': 'default',
            'symbol': symbol,
            'name': name
        }

    def _create_basic_pattern_result(self, symbol: str, name: str, stock_data) -> Dict:
        """기본 패턴 분석 (데이터 기반)"""
        try:
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            
            # 단순 패턴 분석
            if change_rate > 3 and volume > 1000000:
                score = 70
                patterns = ['상승_돌파']
                recommendation = 'BUY'
            elif change_rate < -3 and volume > 1000000:
                score = 30
                patterns = ['하락_패턴']
                recommendation = 'SELL'
            elif abs(change_rate) < 1:
                score = 50
                patterns = ['횡보_패턴']
                recommendation = 'HOLD'
            else:
                score = 50
                patterns = ['일반_패턴']
                recommendation = 'HOLD'
            
            self.logger.info(f"📊 {symbol} 기본 패턴 분석 완료: 점수 {score}, 패턴 {patterns}")
            
            return {
                'overall_score': score,
                'candle_pattern_score': score,
                'technical_pattern_score': score,
                'trendline_score': 50.0,
                'support_resistance_score': 50.0,
                'pattern_strength': abs(change_rate) / 10,
                'confidence': 0.6,
                'detected_patterns': patterns,
                'pattern_recommendation': {'action': recommendation, 'reason': '기본 분석'},
                'analysis_status': 'basic',
                'symbol': symbol,
                'name': name
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 기본 패턴 분석 실패: {e}")
            return self._create_default_pattern_result(symbol, name, f"기본 분석 오류: {e}")

    # pattern_detector.py에서 수정 (PatternDetector 클래스)
   
    async def _analyze_candle_patterns(self, stock_data: Any) -> Dict[str, Any]:
        """캔들패턴 분석 - 안전한 속성 접근"""
        try:
            # 안전한 속성 접근
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            
            detected_patterns = []
            pattern_scores = []
            
            # 1. 단일 캔들 패턴 분석
            single_candle_patterns = self._detect_single_candle_patterns(stock_data)
            detected_patterns.extend(single_candle_patterns)
            
            # 2. 다중 캔들 패턴 분석 (실제로는 과거 데이터 필요)
            multi_candle_patterns = self._detect_multi_candle_patterns(stock_data)
            detected_patterns.extend(multi_candle_patterns)
            
            # 3. 패턴별 점수 계산
            for pattern in detected_patterns:
                pattern_name = pattern.get('name', '')
                base_score = self.pattern_scores.get(pattern_name, 50)
                
                # 거래량 확인으로 신뢰도 조정
                volume_confirmation = self._check_volume_confirmation(volume, change_rate)
                adjusted_score = self._adjust_pattern_score(base_score, volume_confirmation, pattern)
                
                pattern_scores.append(adjusted_score)
                pattern['score'] = adjusted_score
            
            # 4. 전체 캔들패턴 점수 계산
            if pattern_scores:
                # 가장 강한 패턴의 가중평균
                sorted_scores = sorted(pattern_scores, reverse=True)
                if len(sorted_scores) >= 3:
                    overall_candle_score = (sorted_scores[0] * 0.5 + 
                                        sorted_scores[1] * 0.3 + 
                                        sorted_scores[2] * 0.2)
                elif len(sorted_scores) == 2:
                    overall_candle_score = (sorted_scores[0] * 0.7 + sorted_scores[1] * 0.3)
                else:
                    overall_candle_score = sorted_scores[0]
            else:
                overall_candle_score = 50.0
            
            return {
                'overall_score': overall_candle_score,
                'detected_patterns': detected_patterns,
                'pattern_count': len(detected_patterns),
                'strongest_pattern': max(detected_patterns, key=lambda x: x.get('score', 0)) if detected_patterns else None,
                'bullish_patterns': [p for p in detected_patterns if p.get('score', 50) > 60],
                'bearish_patterns': [p for p in detected_patterns if p.get('score', 50) < 40],
                'volume_confirmation': volume > 1000000  # 거래량 확인
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 캔들패턴 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'detected_patterns': [],
                'pattern_count': 0,
                'strongest_pattern': None,
                'bullish_patterns': [],
                'bearish_patterns': [],
                'volume_confirmation': False
            }
    
    def _detect_single_candle_patterns(self, stock_data: Any) -> List[Dict]:
        """단일 캔들 패턴 감지 - 안전한 속성 접근"""
        patterns = []
        
        try:
            # 안전한 속성 접근
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            high_52w = self.safe_get_attr(stock_data, 'high_52w', 0)
            low_52w = self.safe_get_attr(stock_data, 'low_52w', 0)
            
            # 간단한 패턴 감지 (실제로는 OHLC 데이터 필요)
            
            # 1. Hammer/Inverted Hammer (저점에서 긴 아래꼬리)
            if change_rate > 1 and volume > 1000000:
                if high_52w and low_52w:
                    position_ratio = (current_price - low_52w) / (high_52w - low_52w)
                    if position_ratio < 0.3:  # 저점 근처
                        patterns.append({
                            'name': 'hammer',
                            'type': 'bullish',
                            'description': '해머 패턴 - 저점 반등 신호',
                            'confidence': 0.7,
                            'timeframe': 'Daily'
                        })
            
            # 2. Shooting Star (고점에서 긴 위꼬리)
            elif change_rate < -1 and volume > 1000000:
                if high_52w and low_52w:
                    position_ratio = (current_price - low_52w) / (high_52w - low_52w)
                    if position_ratio > 0.7:  # 고점 근처
                        patterns.append({
                            'name': 'shooting_star',
                            'type': 'bearish',
                            'description': '유성 패턴 - 고점 하락 신호',
                            'confidence': 0.7,
                            'timeframe': 'Daily'
                        })
            
            # 3. Doji (변동폭 작음)
            elif abs(change_rate) < 0.5:
                patterns.append({
                    'name': 'doji',
                    'type': 'neutral',
                    'description': '도지 패턴 - 방향성 전환 신호',
                    'confidence': 0.5,
                    'timeframe': 'Daily'
                })
            
            # 4. 강한 상승 캔들
            elif change_rate > 3:
                patterns.append({
                    'name': 'bullish_marubozu',
                    'type': 'bullish',
                    'description': '강한 상승 캔들 - 상승 모멘텀',
                    'confidence': 0.6,
                    'timeframe': 'Daily'
                })
            
            # 5. 강한 하락 캔들
            elif change_rate < -3:
                patterns.append({
                    'name': 'bearish_marubozu',
                    'type': 'bearish',
                    'description': '강한 하락 캔들 - 하락 모멘텀',
                    'confidence': 0.6,
                    'timeframe': 'Daily'
                })
            
            return patterns
            
        except Exception as e:
            self.logger.debug(f"⚠️ 단일 캔들 패턴 감지 실패: {e}")
            return []
    
    def _detect_multi_candle_patterns(self, stock_data: Any) -> List[Dict]:
        """다중 캔들 패턴 감지 - 안전한 속성 접근"""
        patterns = []
        
        try:
            # 안전한 속성 접근
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            high_52w = self.safe_get_attr(stock_data, 'high_52w', 0)
            low_52w = self.safe_get_attr(stock_data, 'low_52w', 0)
            
            # 52주 고저점 기반 패턴 추정
            if high_52w and low_52w and current_price:
                position_ratio = (current_price - low_52w) / (high_52w - low_52w)
                
                # Double Bottom 패턴 추정
                if 0.1 <= position_ratio <= 0.3 and change_rate > 2:
                    patterns.append({
                        'name': 'double_bottom',
                        'type': 'bullish',
                        'description': '더블바텀 패턴 - 저점 근처 반등',
                        'confidence': 0.6,
                        'timeframe': 'Multi-day'
                    })
                
                # Double Top 패턴 추정
                elif 0.7 <= position_ratio <= 0.9 and change_rate < -2:
                    patterns.append({
                        'name': 'double_top',
                        'type': 'bearish',
                        'description': '더블탑 패턴 - 고점 근처 하락',
                        'confidence': 0.6,
                        'timeframe': 'Multi-day'
                    })
                
                # Breakout 패턴
                elif position_ratio > 0.9 and change_rate > 3 and volume > 2000000:
                    patterns.append({
                        'name': 'breakout',
                        'type': 'bullish',
                        'description': '돌파 패턴 - 52주 신고가 돌파',
                        'confidence': 0.8,
                        'timeframe': 'Multi-day'
                    })
            
            return patterns
            
        except Exception as e:
            self.logger.debug(f"⚠️ 다중 캔들 패턴 감지 실패: {e}")
            return []
    
    async def _analyze_technical_patterns(self, stock_data: Any) -> Dict[str, Any]:
        """기술적 패턴 분석"""
        try:
            if self.pattern_detector:
                return await self.pattern_detector.detect_patterns(stock_data)
            else:
                return self._basic_technical_pattern_analysis(stock_data)
                
        except Exception as e:
            self.logger.warning(f"⚠️ 기술적 패턴 분석 실패: {e}")
            return self._basic_technical_pattern_analysis(stock_data)
    
    def _basic_technical_pattern_analysis(self, stock_data: Any) -> Dict[str, Any]:
        """기본 기술적 패턴 분석 - 안전한 속성 접근"""
        try:
            # 안전한 속성 접근
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            high_52w = self.safe_get_attr(stock_data, 'high_52w', 0)
            low_52w = self.safe_get_attr(stock_data, 'low_52w', 0)
            
            patterns = []
            
            # 1. 추세 패턴 분석
            trend_pattern = self._analyze_trend_pattern(current_price, high_52w, low_52w, change_rate)
            if trend_pattern:
                patterns.append(trend_pattern)
            
            # 2. 모멘텀 패턴 분석
            momentum_pattern = self._analyze_momentum_pattern(change_rate, volume)
            if momentum_pattern:
                patterns.append(momentum_pattern)
            
            # 3. 볼륨 패턴 분석
            volume_pattern = self._analyze_volume_pattern(volume, change_rate)
            if volume_pattern:
                patterns.append(volume_pattern)
            
            # 전체 점수 계산
            if patterns:
                pattern_scores = [p.get('score', 50) for p in patterns]
                overall_score = sum(pattern_scores) / len(pattern_scores)
            else:
                overall_score = 50.0
            
            return {
                'overall_score': overall_score,
                'detected_patterns': patterns,
                'pattern_count': len(patterns),
                'trend_strength': abs(change_rate) / 10 if change_rate else 0,
                'volume_confirmation': volume > 1000000
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 기술적 패턴 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'detected_patterns': [],
                'pattern_count': 0,
                'trend_strength': 0,
                'volume_confirmation': False
            }
    
    def _analyze_trend_pattern(self, current_price: float, high_52w: float, 
                              low_52w: float, change_rate: float) -> Optional[Dict]:
        """추세 패턴 분석"""
        if high_52w <= 0 or low_52w <= 0:
            return None
        
        position_ratio = (current_price - low_52w) / (high_52w - low_52w)
        
        if position_ratio > 0.8:
            # 상승추세
            return {
                'name': 'uptrend',
                'type': 'bullish',
                'description': '강한 상승추세 - 52주 고점권',
                'score': 70 + min(20, change_rate * 2),
                'confidence': 0.8
            }
        elif position_ratio < 0.2:
            # 하락추세 또는 바닥권
            if change_rate > 0:
                return {
                    'name': 'bottom_reversal',
                    'type': 'bullish',
                    'description': '바닥권 반전 신호',
                    'score': 60 + min(20, change_rate * 3),
                    'confidence': 0.7
                }
            else:
                return {
                    'name': 'downtrend',
                    'type': 'bearish',
                    'description': '하락추세 지속',
                    'score': 30 + max(-20, change_rate * 2),
                    'confidence': 0.7
                }
        else:
            # 횡보
            return {
                'name': 'sideways',
                'type': 'neutral',
                'description': '횡보 구간',
                'score': 50,
                'confidence': 0.6
            }
    
    def _analyze_momentum_pattern(self, change_rate: float, volume: int) -> Optional[Dict]:
        """모멘텀 패턴 분석"""
        if abs(change_rate) < 1:
            return None
        
        # 거래량 동반 여부 확인
        volume_support = volume > 1000000
        
        if change_rate > 3:
            score = 70 + min(20, (change_rate - 3) * 2)
            if volume_support:
                score += 10
            
            return {
                'name': 'strong_momentum_up',
                'type': 'bullish',
                'description': f'강한 상승 모멘텀 ({change_rate:.1f}%)',
                'score': min(100, score),
                'confidence': 0.8 if volume_support else 0.6
            }
        elif change_rate < -3:
            score = 30 - min(20, abs(change_rate + 3) * 2)
            if volume_support:
                score -= 10
            
            return {
                'name': 'strong_momentum_down',
                'type': 'bearish',
                'description': f'강한 하락 모멘텀 ({change_rate:.1f}%)',
                'score': max(0, score),
                'confidence': 0.8 if volume_support else 0.6
            }
        
        return None
    
    def _analyze_breakout_pattern(self, current_price: float, high_52w: float, 
                                 change_rate: float, volume: int) -> Optional[Dict]:
        """돌파 패턴 분석"""
        if high_52w <= 0:
            return None
        
        # 52주 고점 대비 위치
        high_ratio = current_price / high_52w
        
        if high_ratio > 1.0 and change_rate > 2 and volume > 1500000:
            # 신고가 돌파
            return {
                'name': 'new_high_breakout',
                'type': 'bullish',
                'description': '52주 신고가 돌파',
                'score': 80 + min(15, change_rate),
                'confidence': 0.9
            }
        elif high_ratio > 0.98 and change_rate > 1 and volume > 1000000:
            # 고점 근접 돌파 시도
            return {
                'name': 'resistance_test',
                'type': 'bullish',
                'description': '고점 저항선 돌파 시도',
                'score': 65 + min(10, change_rate * 2),
                'confidence': 0.7
            }
        
        return None
    
    async def _analyze_trendlines(self, stock_data: Any) -> Dict[str, Any]:
        """추세선 분석"""
        try:
            # 실제로는 과거 가격 데이터로 추세선 계산
            # 현재는 간단한 추정
            
            current_price = getattr(stock_data, 'current_price', 0)
            change_rate = getattr(stock_data, 'change_rate', 0)
            high_52w = getattr(stock_data, 'high_52w', 0)
            low_52w = getattr(stock_data, 'low_52w', 0)
            
            trendlines = []
            
            if high_52w > 0 and low_52w > 0:
                position_ratio = (current_price - low_52w) / (high_52w - low_52w)
                
                # 상승 추세선
                if position_ratio > 0.6 and change_rate > 0:
                    trendlines.append({
                        'type': 'ascending',
                        'strength': 'strong' if position_ratio > 0.8 else 'moderate',
                        'slope': change_rate / 10,  # 간단한 기울기 추정
                        'support_level': low_52w * 1.1,
                        'confidence': 0.7
                    })
                
                # 하락 추세선
                elif position_ratio < 0.4 and change_rate < 0:
                    trendlines.append({
                        'type': 'descending',
                        'strength': 'strong' if position_ratio < 0.2 else 'moderate',
                        'slope': change_rate / 10,
                        'resistance_level': high_52w * 0.9,
                        'confidence': 0.7
                    })
                
                # 횡보 추세선
                else:
                    trendlines.append({
                        'type': 'sideways',
                        'strength': 'moderate',
                        'slope': 0,
                        'range_top': high_52w * 0.95,
                        'range_bottom': low_52w * 1.05,
                        'confidence': 0.6
                    })
            
            # 추세선 점수 계산
            if trendlines:
                main_trend = trendlines[0]
                if main_trend['type'] == 'ascending':
                    trend_score = 70 + (main_trend['slope'] * 100)
                elif main_trend['type'] == 'descending':
                    trend_score = 30 + (main_trend['slope'] * 100)
                else:
                    trend_score = 50
            else:
                trend_score = 50
                main_trend = None
            
            return {
                'overall_score': max(0, min(100, trend_score)),
                'trendlines': trendlines,
                'main_trend': main_trend,
                'trend_validity': len(trendlines) > 0,
                'breakout_potential': self._calculate_breakout_potential(trendlines, current_price)
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 추세선 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'trendlines': [],
                'main_trend': None,
                'trend_validity': False,
                'breakout_potential': 0.5
            }
    
    async def _analyze_support_resistance(self, stock_data: Any) -> Dict[str, Any]:
        """지지저항선 분석"""
        try:
            current_price = getattr(stock_data, 'current_price', 0)
            high_52w = getattr(stock_data, 'high_52w', 0)
            low_52w = getattr(stock_data, 'low_52w', 0)
            change_rate = getattr(stock_data, 'change_rate', 0)
            
            support_levels = []
            resistance_levels = []
            
            if high_52w > 0 and low_52w > 0:
                # 주요 지지저항선 계산
                range_size = high_52w - low_52w
                
                # 피보나치 되돌림 레벨
                fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
                
                for level in fib_levels:
                    price_level = low_52w + (range_size * level)
                    
                    if price_level < current_price:
                        support_levels.append({
                            'price': price_level,
                            'type': f'fibonacci_{level}',
                            'strength': 'strong' if level in [0.382, 0.618] else 'moderate',
                            'distance': (current_price - price_level) / current_price
                        })
                    else:
                        resistance_levels.append({
                            'price': price_level,
                            'type': f'fibonacci_{level}',
                            'strength': 'strong' if level in [0.382, 0.618] else 'moderate',
                            'distance': (price_level - current_price) / current_price
                        })
                
                # 52주 고저점도 주요 지지저항선
                resistance_levels.append({
                    'price': high_52w,
                    'type': '52w_high',
                    'strength': 'very_strong',
                    'distance': (high_52w - current_price) / current_price
                })
                
                support_levels.append({
                    'price': low_52w,
                    'type': '52w_low',
                    'strength': 'very_strong',
                    'distance': (current_price - low_52w) / current_price
                })
            
            # 현재 위치 분석
            near_support = any(level['distance'] < 0.05 for level in support_levels)
            near_resistance = any(level['distance'] < 0.05 for level in resistance_levels)
            
            # 지지저항선 점수 계산
            if near_support and change_rate > 0:
                sr_score = 75  # 지지선 근처 반등
            elif near_resistance and change_rate < 0:
                sr_score = 25  # 저항선 근처 하락
            elif near_resistance and change_rate > 3:
                sr_score = 80  # 저항선 돌파
            elif near_support and change_rate < -3:
                sr_score = 20  # 지지선 붕괴
            else:
                sr_score = 50  # 중립
            
            return {
                'overall_score': sr_score,
                'support_levels': sorted(support_levels, key=lambda x: x['distance'])[:3],
                'resistance_levels': sorted(resistance_levels, key=lambda x: x['distance'])[:3],
                'near_support': near_support,
                'near_resistance': near_resistance,
                'key_level_test': near_support or near_resistance,
                'breakout_direction': 'bullish' if near_resistance and change_rate > 0 else 'bearish' if near_support and change_rate < 0 else 'neutral'
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 지지저항선 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'support_levels': [],
                'resistance_levels': [],
                'near_support': False,
                'near_resistance': False,
                'key_level_test': False,
                'breakout_direction': 'neutral'
            }
    
    # 유틸리티 메서드들
    def _check_volume_confirmation(self, volume: int, change_rate: float) -> bool:
        """거래량 확인"""
        if abs(change_rate) > 3:
            return volume > 1500000  # 큰 변동은 대량거래 필요
        elif abs(change_rate) > 1:
            return volume > 800000   # 중간 변동은 중간 거래량
        else:
            return volume > 300000   # 작은 변동은 기본 거래량
    
    def _adjust_pattern_score(self, base_score: float, volume_confirmation: bool, pattern: Dict) -> float:
        """패턴 점수 조정"""
        adjusted_score = base_score
        
        # 거래량 확인 보너스/페널티
        if volume_confirmation:
            adjusted_score += 10
        else:
            adjusted_score -= 5
        
        # 패턴 신뢰도에 따른 조정
        confidence = pattern.get('confidence', 0.5)
        adjusted_score = adjusted_score * (0.5 + confidence * 0.5)
        
        return max(0, min(100, adjusted_score))
    
    def _check_near_support(self, current_price: float, low_52w: float) -> bool:
        """지지선 근처 여부 확인"""
        if low_52w <= 0:
            return False
        return (current_price - low_52w) / low_52w < 0.15  # 15% 이내
    
    def _check_near_resistance(self, current_price: float, high_52w: float) -> bool:
        """저항선 근처 여부 확인"""
        if high_52w <= 0:
            return False
        return (high_52w - current_price) / current_price < 0.15  # 15% 이내
    
    def _calculate_trend_strength(self, change_rate: float) -> float:
        """추세 강도 계산"""
        return min(1.0, abs(change_rate) / 10)
    
    def _calculate_momentum_strength(self, change_rate: float, volume: int) -> float:
        """모멘텀 강도 계산"""
        price_momentum = abs(change_rate) / 10
        volume_momentum = min(1.0, volume / 2000000)
        return (price_momentum + volume_momentum) / 2
    
    def _calculate_breakout_probability(self, current_price: float, high_52w: float, volume: int) -> float:
        """돌파 확률 계산"""
        if high_52w <= 0:
            return 0.5
        
        price_ratio = current_price / high_52w
        volume_factor = min(1.0, volume / 1000000)
        
        if price_ratio > 0.95:
            return min(1.0, 0.7 + volume_factor * 0.3)
        else:
            return 0.3 + price_ratio * 0.4
    
    def _calculate_breakout_potential(self, trendlines: List[Dict], current_price: float) -> float:
        """돌파 잠재력 계산"""
        if not trendlines:
            return 0.5
        
        main_trend = trendlines[0]
        if main_trend['type'] == 'ascending':
            return 0.7 + min(0.3, main_trend.get('slope', 0) * 10)
        elif main_trend['type'] == 'descending':
            return 0.3 - min(0.2, abs(main_trend.get('slope', 0)) * 10)
        else:
            return 0.5
    
    def _calculate_overall_pattern_score(self, candle_analysis: Dict,
                                       technical_pattern_analysis: Dict,
                                       trendline_analysis: Dict,
                                       support_resistance_analysis: Dict) -> float:
        """종합 패턴 점수 계산"""
        try:
            # 가중치 설정
            weights = {
                'candle': 0.3,           # 캔들패턴 30%
                'technical': 0.3,        # 기술적패턴 30%
                'trendline': 0.2,        # 추세선 20%
                'support_resistance': 0.2  # 지지저항선 20%
            }
            
            candle_score = candle_analysis.get('overall_score', 50)
            technical_score = technical_pattern_analysis.get('overall_score', 50)
            trendline_score = trendline_analysis.get('overall_score', 50)
            sr_score = support_resistance_analysis.get('overall_score', 50)
            
            overall_score = (
                candle_score * weights['candle'] +
                technical_score * weights['technical'] +
                trendline_score * weights['trendline'] +
                sr_score * weights['support_resistance']
            )
            
            return max(0, min(100, overall_score))
            
        except Exception as e:
            self.logger.warning(f"⚠️ 종합 패턴 점수 계산 실패: {e}")
            return 50.0
    
    def _calculate_pattern_confidence(self, candle_analysis: Dict,
                                    technical_pattern_analysis: Dict,
                                    trendline_analysis: Dict,
                                    support_resistance_analysis: Dict) -> float:
        """패턴 신뢰도 계산"""
        try:
            confidence_factors = []
            
            # 캔들패턴 신뢰도
            candle_patterns = candle_analysis.get('detected_patterns', [])
            if candle_patterns:
                avg_candle_confidence = sum(p.get('confidence', 0.5) for p in candle_patterns) / len(candle_patterns)
                confidence_factors.append(avg_candle_confidence)
            
            # 기술적 패턴 신뢰도
            technical_patterns = technical_pattern_analysis.get('detected_patterns', [])
            if technical_patterns:
                avg_tech_confidence = sum(p.get('confidence', 0.5) for p in technical_patterns) / len(technical_patterns)
                confidence_factors.append(avg_tech_confidence)
            
            # 추세선 신뢰도
            if trendline_analysis.get('trend_validity', False):
                main_trend = trendline_analysis.get('main_trend')
                if main_trend:
                    confidence_factors.append(main_trend.get('confidence', 0.5))
            
            # 지지저항선 신뢰도
            if support_resistance_analysis.get('key_level_test', False):
                confidence_factors.append(0.8)
            
            # 거래량 확인 보너스
            if candle_analysis.get('volume_confirmation', False):
                confidence_factors.append(0.8)
            
            if confidence_factors:
                return sum(confidence_factors) / len(confidence_factors)
            else:
                return 0.5
                
        except Exception as e:
            self.logger.warning(f"⚠️ 패턴 신뢰도 계산 실패: {e}")
            return 0.5
    
    def _calculate_pattern_strength(self, candle_analysis: Dict, technical_pattern_analysis: Dict) -> float:
        """패턴 강도 계산"""
        try:
            strength_factors = []
            
            # 캔들패턴 강도
            strongest_candle = candle_analysis.get('strongest_pattern')
            if strongest_candle:
                pattern_score = strongest_candle.get('score', 50)
                strength_factors.append(abs(pattern_score - 50) / 50)
            
            # 기술적 패턴 강도
            trend_strength = technical_pattern_analysis.get('trend_strength', 0.5)
            momentum_strength = technical_pattern_analysis.get('momentum_strength', 0.5)
            
            strength_factors.extend([trend_strength, momentum_strength])
            
            if strength_factors:
                return sum(strength_factors) / len(strength_factors)
            else:
                return 0.5
                
        except Exception as e:
            self.logger.warning(f"⚠️ 패턴 강도 계산 실패: {e}")
            return 0.5
    
    def _get_detected_patterns_summary(self, candle_analysis: Dict, technical_pattern_analysis: Dict) -> List[str]:
        """감지된 패턴 요약"""
        try:
            patterns = []
            
            # 캔들패턴 추가
            candle_patterns = candle_analysis.get('detected_patterns', [])
            for pattern in candle_patterns:
                if pattern.get('score', 50) > 60 or pattern.get('score', 50) < 40:  # 중요한 패턴만
                    patterns.append(f"{pattern.get('name', 'unknown')} ({pattern.get('type', 'neutral')})")
            
            # 기술적 패턴 추가
            tech_patterns = technical_pattern_analysis.get('detected_patterns', [])
            for pattern in tech_patterns:
                if pattern.get('score', 50) > 60 or pattern.get('score', 50) < 40:  # 중요한 패턴만
                    patterns.append(f"{pattern.get('name', 'unknown')} ({pattern.get('type', 'neutral')})")
            
            return patterns[:5]  # 최대 5개만 반환
            
        except Exception as e:
            self.logger.warning(f"⚠️ 패턴 요약 생성 실패: {e}")
            return []
    
    def _get_pattern_recommendation(self, pattern_results: dict) -> dict:
        """패턴 기반 추천 생성 - None 체크 강화"""
        try:
            if not pattern_results:
                return {'action': 'HOLD', 'reason': '패턴 결과 없음'}
            
            patterns = pattern_results.get('detected_patterns', [])
            overall_score = pattern_results.get('overall_score', 50)
            
            if overall_score >= 75:
                return {'action': 'BUY', 'reason': '강한 상승 패턴 감지'}
            elif overall_score >= 60:
                return {'action': 'WEAK_BUY', 'reason': '상승 패턴 감지'}
            elif overall_score <= 35:
                return {'action': 'SELL', 'reason': '하락 패턴 감지'}
            else:
                return {'action': 'HOLD', 'reason': '명확한 패턴 없음'}
        
        except Exception as e:
            self.logger.debug(f"패턴 추천 생성 실패: {e}")
            return {'action': 'HOLD', 'reason': '추천 생성 오류'}
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """분석 실패 시 기본값 반환"""
        return {
            'overall_score': 50.0,
            'candle_patterns': {
                'overall_score': 50.0,
                'detected_patterns': [],
                'pattern_count': 0,
                'strongest_pattern': None,
                'bullish_patterns': [],
                'bearish_patterns': [],
                'volume_confirmation': False
            },
            'technical_patterns': {
                'overall_score': 50.0,
                'detected_patterns': [],
                'trend_strength': 0.5,
                'momentum_strength': 0.5,
                'breakout_probability': 0.5
            },
            'trendlines': {
                'overall_score': 50.0,
                'trendlines': [],
                'main_trend': None,
                'trend_validity': False,
                'breakout_potential': 0.5
            },
            'support_resistance': {
                'overall_score': 50.0,
                'support_levels': [],
                'resistance_levels': [],
                'near_support': False,
                'near_resistance': False,
                'key_level_test': False,
                'breakout_direction': 'neutral'
            },
            'pattern_strength': 0.5,
            'confidence': 0.5,
            'detected_patterns': [],
            'pattern_recommendation': {
                'action': 'HOLD',
                'reason': '패턴 분석 불가',
                'risk_level': 'UNKNOWN',
                'expected_direction': 'neutral',
                'pattern_strength': 'unknown'
            },
            'analysis_time': datetime.now().isoformat()
        }