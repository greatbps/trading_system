#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/utils/pattern_detector.py

패턴 감지기 - 기술적 패턴 감지 알고리즘
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import get_logger

class PatternDetector:
    """차트 패턴 감지기 - 강화된 버전"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("PatternDetector")
    
    def safe_get_attr(self, data, attr_name, default=None):
        """안전한 속성 접근"""
        try:
            if isinstance(data, dict):
                return data.get(attr_name, default)
            else:
                return getattr(data, attr_name, default)
        except (AttributeError, TypeError):
            return default

    async def detect_patterns(self, stock_data, symbol: str = None, name: str = None):
        """패턴 감지 - UNKNOWN 해결 + 실용 패턴 추가"""
        try:
            # === 종목 정보 확보 (UNKNOWN 문제 해결) ===
            if not symbol:
                symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            if not name:
                name = self.safe_get_attr(stock_data, 'name', symbol)
            
            # 종목명이 여전히 문제가 있으면 최소한 symbol 사용
            if name == 'UNKNOWN' or not name:
                name = symbol
            
            self.logger.info(f"🔍 패턴 감지 시작 - {symbol} ({name})")
            
            # === 기본 데이터 추출 ===
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            high_52w = self.safe_get_attr(stock_data, 'high_52w', 0)
            low_52w = self.safe_get_attr(stock_data, 'low_52w', 0)
            trading_value = self.safe_get_attr(stock_data, 'trading_value', 0)
            
            # 데이터 유효성 검사
            if current_price <= 0:
                self.logger.warning(f"⚠️ {symbol} ({name}) 유효하지 않은 가격 데이터")
                return self._create_empty_result(symbol, name, "가격 데이터 부족")
            
            # === 패턴 감지 실행 ===
            detected_patterns = []
            
            # 1. 거래량 돌파 패턴
            volume_pattern = self._detect_volume_breakout(volume, trading_value, change_rate)
            if volume_pattern:
                detected_patterns.append(volume_pattern)
            
            # 2. 연속 상승/하락 패턴 (단순화)
            momentum_pattern = self._detect_momentum_pattern(change_rate)
            if momentum_pattern:
                detected_patterns.append(momentum_pattern)
            
            # 3. 52주 고저점 관련 패턴
            price_level_pattern = self._detect_price_level_pattern(
                current_price, high_52w, low_52w, change_rate
            )
            if price_level_pattern:
                detected_patterns.append(price_level_pattern)
            
            # 4. 급등/급락 패턴
            volatility_pattern = self._detect_volatility_pattern(change_rate, volume)
            if volatility_pattern:
                detected_patterns.append(volatility_pattern)
            
            # 5. 반전 패턴 (단순화된 망치형/역망치형)
            reversal_pattern = self._detect_simple_reversal_pattern(change_rate, volume)
            if reversal_pattern:
                detected_patterns.append(reversal_pattern)
            
            # === 결과 생성 ===
            total_score = self._calculate_pattern_score(detected_patterns)
            
            self.logger.info(f"✅ 패턴 감지 완료 - {symbol} ({name}): {len(detected_patterns)}개 패턴, 점수: {total_score:.1f}")
            
            return {
                'detected_patterns': detected_patterns,
                'pattern_count': len(detected_patterns),
                'overall_score': total_score,
                'symbol': symbol,
                'name': name,
                'analysis_status': 'success'
            }
            
        except Exception as e:
            symbol = symbol or 'UNKNOWN'
            name = name or 'UNKNOWN'
            self.logger.error(f"❌ 패턴 감지 실패 - {symbol} ({name}): {e}")
            return self._create_empty_result(symbol, name, f"분석 오류: {e}")

    def _detect_volume_breakout(self, volume: int, trading_value: float, change_rate: float) -> dict:
        """거래량 돌파 패턴 감지"""
        try:
            # 거래량이 충분히 크고 상승세일 때
            if volume > 1000000 and change_rate > 2:  # 100만주 이상, 2% 이상 상승
                if trading_value > 50:  # 거래대금 50억 이상
                    return {
                        'name': '대량거래_돌파',
                        'type': 'bullish',
                        'description': f'대량 거래량({volume:,}주)과 함께 상승 돌파',
                        'score': min(90, 70 + change_rate * 2),
                        'confidence': 0.8,
                        'volume': volume,
                        'change_rate': change_rate
                    }
                else:
                    return {
                        'name': '거래량_증가',
                        'type': 'bullish',
                        'description': f'거래량 증가({volume:,}주)와 함께 상승',
                        'score': min(75, 60 + change_rate * 1.5),
                        'confidence': 0.6,
                        'volume': volume,
                        'change_rate': change_rate
                    }
            return None
        except:
            return None

    def _detect_momentum_pattern(self, change_rate: float) -> dict:
        """모멘텀 패턴 감지 (단순화)"""
        try:
            if change_rate > 5:
                return {
                    'name': '강한_상승_모멘텀',
                    'type': 'bullish',
                    'description': f'강한 상승 모멘텀 ({change_rate:.1f}%)',
                    'score': min(85, 70 + change_rate),
                    'confidence': 0.7,
                    'change_rate': change_rate
                }
            elif change_rate > 3:
                return {
                    'name': '상승_모멘텀',
                    'type': 'bullish',
                    'description': f'상승 모멘텀 ({change_rate:.1f}%)',
                    'score': min(75, 60 + change_rate * 2),
                    'confidence': 0.6,
                    'change_rate': change_rate
                }
            elif change_rate < -5:
                return {
                    'name': '급락_패턴',
                    'type': 'bearish',
                    'description': f'급락 패턴 ({change_rate:.1f}%)',
                    'score': max(15, 30 + change_rate),
                    'confidence': 0.7,
                    'change_rate': change_rate
                }
            return None
        except:
            return None

    def _detect_price_level_pattern(self, current_price: float, high_52w: float, 
                                   low_52w: float, change_rate: float) -> dict:
        """52주 고저점 관련 패턴"""
        try:
            if high_52w <= 0 or low_52w <= 0:
                return None
            
            # 52주 고점 대비 현재 위치
            high_ratio = current_price / high_52w
            low_ratio = (current_price - low_52w) / (high_52w - low_52w)
            
            if high_ratio >= 0.98 and change_rate > 1:  # 52주 고점 근처에서 상승
                return {
                    'name': '고점_돌파',
                    'type': 'bullish',
                    'description': f'52주 고점 근처 돌파 (고점 대비 {high_ratio*100:.1f}%)',
                    'score': min(85, 75 + change_rate * 2),
                    'confidence': 0.8,
                    'high_ratio': high_ratio,
                    'change_rate': change_rate
                }
            elif low_ratio <= 0.2 and change_rate > 2:  # 저점 근처에서 반등
                return {
                    'name': '저점_반등',
                    'type': 'bullish',
                    'description': f'52주 저점 근처 반등 (구간 하위 {low_ratio*100:.1f}%)',
                    'score': min(80, 65 + change_rate * 2.5),
                    'confidence': 0.7,
                    'low_ratio': low_ratio,
                    'change_rate': change_rate
                }
            elif high_ratio >= 0.85:  # 고점권
                return {
                    'name': '고점권_진입',
                    'type': 'neutral',
                    'description': f'52주 고점권 진입 (고점 대비 {high_ratio*100:.1f}%)',
                    'score': 55,
                    'confidence': 0.5,
                    'high_ratio': high_ratio
                }
            return None
        except:
            return None

    def _detect_volatility_pattern(self, change_rate: float, volume: int) -> dict:
        """변동성 패턴 감지"""
        try:
            abs_change = abs(change_rate)
            
            if abs_change > 7 and volume > 500000:  # 7% 이상 변동 + 거래량
                pattern_type = 'bullish' if change_rate > 0 else 'bearish'
                direction = '급등' if change_rate > 0 else '급락'
                
                return {
                    'name': f'{direction}_패턴',
                    'type': pattern_type,
                    'description': f'{direction} 패턴 ({change_rate:.1f}%, 거래량 {volume:,}주)',
                    'score': 70 if change_rate > 0 else 30,
                    'confidence': 0.6,
                    'change_rate': change_rate,
                    'volume': volume
                }
            return None
        except:
            return None

    def _detect_simple_reversal_pattern(self, change_rate: float, volume: int) -> dict:
        """단순 반전 패턴 (망치형 등 단순화)"""
        try:
            # 단순화된 반전 신호: 큰 변동 후 반대 방향 움직임
            if change_rate > 3 and volume > 800000:  # 상승 반전
                return {
                    'name': '상승_반전_신호',
                    'type': 'bullish',
                    'description': f'상승 반전 신호 ({change_rate:.1f}%, 거래량 확인)',
                    'score': min(75, 60 + change_rate * 1.5),
                    'confidence': 0.6,
                    'change_rate': change_rate
                }
            elif change_rate < -3 and volume > 800000:  # 하락 반전 (매도 신호)
                return {
                    'name': '하락_반전_신호',
                    'type': 'bearish',
                    'description': f'하락 반전 신호 ({change_rate:.1f}%, 거래량 확인)',
                    'score': max(25, 40 + change_rate),
                    'confidence': 0.6,
                    'change_rate': change_rate
                }
            return None
        except:
            return None

    def _calculate_pattern_score(self, patterns: list) -> float:
        """패턴 종합 점수 계산"""
        if not patterns:
            return 50.0  # 기본 점수
        
        # 패턴별 점수의 가중 평균
        total_score = 0
        total_weight = 0
        
        for pattern in patterns:
            score = pattern.get('score', 50)
            confidence = pattern.get('confidence', 0.5)
            weight = confidence
            
            total_score += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50.0
        
        final_score = total_score / total_weight
        
        # 패턴 개수 보너스 (최대 5점)
        pattern_bonus = min(5, len(patterns) * 1.5)
        final_score += pattern_bonus
        
        return max(0, min(100, final_score))

    def _create_empty_result(self, symbol: str, name: str, reason: str) -> dict:
        """빈 결과 생성"""
        self.logger.info(f"📊 {symbol} ({name}) 패턴 없음: {reason}")
        
        return {
            'detected_patterns': [],
            'pattern_count': 0,
            'overall_score': 50.0,
            'symbol': symbol,
            'name': name,
            'analysis_status': 'no_patterns',
            'reason': reason
        }