#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/scalping_3m_strategy.py

3분봉 스캘핑 전략 - 단기 매매를 위한 빠른 진입/청산 전략
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_strategy import BaseStrategy


class Scalping3mStrategy(BaseStrategy):
    """3분봉 스캘핑 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = "scalping_3m"
        self.description = "3분봉 기반 단기 스캘핑 전략"
        
        # 스캘핑 특화 파라미터
        self.quick_profit_threshold = 0.5  # 0.5% 빠른 수익 실현
        self.stop_loss_threshold = 0.3    # 0.3% 손절
        self.volume_spike_multiplier = 2.0  # 거래량 급증 임계값
        self.momentum_period = 5          # 단기 모멘텀 기간 (3분봉 5개 = 15분)
        
        self.logger.info("✅ 3분봉 스캘핑 전략 초기화 완료")
    
    async def generate_signals(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """3분봉 스캘핑 신호 생성"""
        try:
            symbol = stock_data.get('symbol', 'Unknown')
            
            # 1. 기본 데이터 검증
            if not self._validate_basic_data(stock_data):
                return self._create_hold_signal(symbol, "기본 데이터 부족")
            
            # 2. 거래량 분석 (스캘핑의 핵심)
            volume_signal = await self._analyze_volume_spike(stock_data)
            
            # 3. 단기 모멘텀 분석
            momentum_signal = await self._analyze_short_momentum(stock_data)
            
            # 4. 가격 변동성 분석
            volatility_signal = await self._analyze_volatility(stock_data)
            
            # 5. 지지/저항 레벨 분석
            support_resistance = await self._analyze_support_resistance(stock_data)
            
            # 6. 종합 신호 생성
            final_signal = await self._generate_scalping_signal(
                volume_signal, momentum_signal, volatility_signal, support_resistance, stock_data
            )
            
            return final_signal
            
        except Exception as e:
            self.logger.error(f"❌ 3분봉 스캘핑 신호 생성 실패 ({symbol}): {e}")
            return self._create_hold_signal(symbol, f"분석 오류: {str(e)}")
    
    async def _analyze_volume_spike(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """거래량 급증 분석"""
        try:
            current_volume = stock_data.get('volume', 0)
            avg_volume = stock_data.get('avg_volume_30d', current_volume)
            
            # 거래량 비율 계산
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            signal_strength = 0
            reasons = []
            
            if volume_ratio >= self.volume_spike_multiplier * 2:
                signal_strength += 30
                reasons.append(f"거래량 급증 {volume_ratio:.1f}배")
            elif volume_ratio >= self.volume_spike_multiplier:
                signal_strength += 20
                reasons.append(f"거래량 증가 {volume_ratio:.1f}배")
            elif volume_ratio < 0.5:
                signal_strength -= 10
                reasons.append("거래량 부족")
            
            return {
                'strength': min(signal_strength, 30),
                'volume_ratio': volume_ratio,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 분석 실패: {e}")
            return {'strength': 0, 'volume_ratio': 1.0, 'reasons': ['거래량 분석 실패']}
    
    async def _analyze_short_momentum(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """단기 모멘텀 분석 (실제 기술적 지표 활용)"""
        try:
            current_price = stock_data.get('current_price', 0)
            change_rate = stock_data.get('change_rate', 0)
            
            # 실제 기술적 지표 데이터 활용
            technical_data = stock_data.get('technical_indicators', {})
            ema_5 = technical_data.get('ema_5', current_price)
            ema_20 = technical_data.get('ema_20', current_price)
            rsi = technical_data.get('rsi', 50)
            macd_line = technical_data.get('macd_line', 0)
            macd_signal = technical_data.get('macd_signal', 0)
            
            signal_strength = 0
            reasons = []
            
            # 1. 가격 vs EMA 포지션 분석 (스캘핑 핵심)
            if current_price > ema_5 > ema_20:
                signal_strength += 20
                reasons.append("강한 상승 추세 (가격 > EMA5 > EMA20)")
            elif current_price > ema_5:
                signal_strength += 10
                reasons.append("단기 상승 추세 (가격 > EMA5)")
            elif current_price < ema_5 < ema_20:
                signal_strength -= 15
                reasons.append("하락 추세 (가격 < EMA5 < EMA20)")
            elif current_price < ema_5:
                signal_strength -= 5
                reasons.append("단기 하락 (가격 < EMA5)")
            
            # 2. MACD 단기 시그널 (스캘핑에 중요)
            if macd_line > macd_signal and macd_line > 0:
                signal_strength += 15
                reasons.append("MACD 강세 전환")
            elif macd_line > macd_signal:
                signal_strength += 8
                reasons.append("MACD 상승 전환")
            elif macd_line < macd_signal and macd_line < 0:
                signal_strength -= 15
                reasons.append("MACD 약세 지속")
            elif macd_line < macd_signal:
                signal_strength -= 8
                reasons.append("MACD 하락 전환")
            
            # 3. RSI 모멘텀 보조 지표
            if rsi > 70:
                signal_strength -= 10
                reasons.append(f"RSI 과매수 주의 ({rsi:.1f})")
            elif rsi < 30:
                signal_strength += 12
                reasons.append(f"RSI 과매도 반등 ({rsi:.1f})")
            elif 50 < rsi < 70:
                signal_strength += 5
                reasons.append("RSI 건전한 상승세")
            elif 30 < rsi < 50:
                signal_strength += 3
                reasons.append("RSI 중립-상승 구간")
            
            # 4. 단기 가격 변동률 (기존 로직 강화)
            if change_rate > 3.0:
                signal_strength += 20
                reasons.append(f"급등 모멘텀 {change_rate:.1f}%")
            elif change_rate > 1.5:
                signal_strength += 15
                reasons.append(f"강한 상승 모멘텀 {change_rate:.1f}%")
            elif change_rate > 0.8:
                signal_strength += 10
                reasons.append(f"상승 모멘텀 {change_rate:.1f}%")
            elif change_rate > 0.3:
                signal_strength += 5
                reasons.append(f"약한 상승세 {change_rate:.1f}%")
            elif change_rate < -3.0:
                signal_strength += 15  # 스캘핑은 급락 후 반등 노림
                reasons.append(f"급락 후 반등 기회 {change_rate:.1f}%")
            elif change_rate < -1.5:
                signal_strength += 8
                reasons.append(f"하락 후 반등 가능성 {change_rate:.1f}%")
            elif change_rate < -0.8:
                signal_strength -= 8
                reasons.append(f"하락 추세 {change_rate:.1f}%")
            
            # 5. 스캘핑 특화: 빠른 반전 신호 감지
            momentum_score = self._calculate_scalping_momentum_score(
                current_price, ema_5, ema_20, rsi, macd_line, macd_signal
            )
            signal_strength += momentum_score['adjustment']
            if momentum_score['reasons']:
                reasons.extend(momentum_score['reasons'])
            
            return {
                'strength': min(max(signal_strength, -25), 35),
                'change_rate': change_rate,
                'ema_trend': 'up' if ema_5 > ema_20 else 'down',
                'macd_signal_strength': macd_line - macd_signal,
                'rsi_position': rsi,
                'reasons': reasons[:4]  # 상위 4개만 유지
            }
            
        except Exception as e:
            self.logger.error(f"❌ 단기 모멘텀 분석 실패: {e}")
            return {'strength': 0, 'change_rate': 0, 'reasons': ['모멘텀 분석 실패']}
    
    def _calculate_scalping_momentum_score(self, current_price: float, ema_5: float, 
                                         ema_20: float, rsi: float, macd_line: float, 
                                         macd_signal: float) -> Dict[str, Any]:
        """스캘핑 특화 모멘텀 점수 계산"""
        try:
            adjustment = 0
            reasons = []
            
            # 1. 골든크로스/데드크로스 초기 신호 (스캘핑에 중요)
            ema_gap = (ema_5 - ema_20) / ema_20 * 100 if ema_20 > 0 else 0
            if 0.1 <= ema_gap <= 0.5:  # 초기 골든크로스 단계
                adjustment += 8
                reasons.append("EMA 골든크로스 초기 단계")
            elif -0.5 <= ema_gap <= -0.1:  # 초기 데드크로스 단계
                adjustment += 5  # 스캘핑에서는 반등 기회로 활용
                reasons.append("단기 조정 후 반등 기회")
            
            # 2. MACD 히스토그램 변화 패턴 (3분봉에서 중요)
            macd_histogram = macd_line - macd_signal
            if abs(macd_histogram) < 0.1:  # 신호선 교차 임박
                if macd_line > 0:
                    adjustment += 6
                    reasons.append("MACD 상승 신호 강화")
                else:
                    adjustment += 3
                    reasons.append("MACD 바닥 신호")
            
            # 3. RSI 단기 반전 패턴
            if 25 <= rsi <= 35:  # 과매도에서 회복 초기
                adjustment += 7
                reasons.append("RSI 과매도 회복 신호")
            elif 65 <= rsi <= 75:  # 과매수에서 조정 초기
                adjustment -= 4
                reasons.append("RSI 과매수 조정 신호")
            
            # 4. 가격 위치와 EMA 간격 분석 (스캘핑 진입점 판단)
            price_ema5_gap = (current_price - ema_5) / ema_5 * 100 if ema_5 > 0 else 0
            if 0.1 <= price_ema5_gap <= 0.3:  # 이상적인 스캘핑 진입점
                adjustment += 5
                reasons.append("이상적 스캘핑 진입점")
            elif price_ema5_gap > 1.0:  # 과도한 괴리
                adjustment -= 3
                reasons.append("가격 과도한 상승 - 조정 위험")
            elif price_ema5_gap < -0.5:  # 급락 상태
                adjustment += 4
                reasons.append("급락 후 반등 기회")
            
            return {
                'adjustment': adjustment,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 스캘핑 모멘텀 점수 계산 실패: {e}")
            return {'adjustment': 0, 'reasons': []}
    
    async def _analyze_volatility(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """변동성 분석 (스캘핑에 적합한 변동성 찾기)"""
        try:
            current_price = stock_data.get('current_price', 0)
            high_price = stock_data.get('high_52w', current_price)
            low_price = stock_data.get('low_52w', current_price)
            
            # 일간 변동률 추정
            daily_volatility = abs(stock_data.get('change_rate', 0))
            
            signal_strength = 0
            reasons = []
            
            # 스캘핑에 적합한 변동성 범위 (1-3%)
            if 1.0 <= daily_volatility <= 3.0:
                signal_strength += 15
                reasons.append(f"적정 변동성 {daily_volatility:.1f}%")
            elif 0.5 <= daily_volatility < 1.0:
                signal_strength += 10
                reasons.append(f"낮은 변동성 {daily_volatility:.1f}%")
            elif daily_volatility > 5.0:
                signal_strength -= 10
                reasons.append(f"과도한 변동성 {daily_volatility:.1f}%")
            elif daily_volatility < 0.2:
                signal_strength -= 5
                reasons.append("변동성 부족")
            
            return {
                'strength': min(max(signal_strength, -10), 15),
                'volatility': daily_volatility,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 변동성 분석 실패: {e}")
            return {'strength': 0, 'volatility': 0, 'reasons': ['변동성 분석 실패']}
    
    async def _analyze_support_resistance(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """지지/저항 레벨 분석"""
        try:
            current_price = stock_data.get('current_price', 0)
            high_52w = stock_data.get('high_52w', current_price)
            low_52w = stock_data.get('low_52w', current_price)
            
            # 52주 고저점 대비 현재 위치
            if high_52w > low_52w:
                price_position = (current_price - low_52w) / (high_52w - low_52w)
            else:
                price_position = 0.5
            
            signal_strength = 0
            reasons = []
            
            # 지지선 근처에서 매수, 저항선 근처에서 매도 시그널
            if price_position <= 0.2:
                signal_strength += 20
                reasons.append("지지선 근처 - 반등 기대")
            elif price_position <= 0.4:
                signal_strength += 10
                reasons.append("지지선 영역")
            elif price_position >= 0.8:
                signal_strength -= 15
                reasons.append("저항선 근처 - 조정 위험")
            elif price_position >= 0.6:
                signal_strength -= 5
                reasons.append("저항선 영역")
            else:
                signal_strength += 5
                reasons.append("중간 구간")
            
            return {
                'strength': min(max(signal_strength, -15), 20),
                'price_position': price_position,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 지지/저항 분석 실패: {e}")
            return {'strength': 0, 'price_position': 0.5, 'reasons': ['지지/저항 분석 실패']}
    
    async def _generate_scalping_signal(self, volume_signal: Dict, momentum_signal: Dict, 
                                      volatility_signal: Dict, support_resistance: Dict, 
                                      stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 스캘핑 신호 생성"""
        try:
            symbol = stock_data.get('symbol', 'Unknown')
            current_price = stock_data.get('current_price', 0)
            
            # 신호 강도 합산
            total_strength = (
                volume_signal['strength'] +
                momentum_signal['strength'] +
                volatility_signal['strength'] +
                support_resistance['strength']
            )
            
            # 모든 분석 결과 합치기
            all_reasons = []
            all_reasons.extend(volume_signal.get('reasons', []))
            all_reasons.extend(momentum_signal.get('reasons', []))
            all_reasons.extend(volatility_signal.get('reasons', []))
            all_reasons.extend(support_resistance.get('reasons', []))
            
            # 스캘핑 전략 특성상 빠른 결정
            if total_strength >= 40:
                action = "STRONG_BUY"
                confidence = min(85 + (total_strength - 40) * 0.5, 95)
                target_profit = self.quick_profit_threshold * 1.5  # 0.75%
            elif total_strength >= 25:
                action = "BUY"
                confidence = min(70 + (total_strength - 25) * 1.0, 85)
                target_profit = self.quick_profit_threshold  # 0.5%
            elif total_strength <= -20:
                action = "SELL"
                confidence = min(70 + abs(total_strength + 20) * 1.0, 85)
                target_profit = 0  # 손절 위주
            else:
                action = "HOLD"
                confidence = 50
                target_profit = 0
            
            # 스캘핑 특화 리스크 관리
            stop_loss_price = current_price * (1 - self.stop_loss_threshold / 100)
            take_profit_price = current_price * (1 + target_profit / 100) if target_profit > 0 else 0
            
            return {
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'score': total_strength,
                'current_price': current_price,
                'target_profit_rate': target_profit,
                'stop_loss_price': int(stop_loss_price),
                'take_profit_price': int(take_profit_price) if take_profit_price > 0 else 0,
                'holding_period': '3-15분 (초단기)',
                'reasons': all_reasons[:5],  # 상위 5개 이유만
                'analysis_details': {
                    'volume_analysis': volume_signal,
                    'momentum_analysis': momentum_signal,
                    'volatility_analysis': volatility_signal,
                    'support_resistance': support_resistance,
                    'strategy_type': '3분봉 스캘핑'
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 스캘핑 신호 생성 실패: {e}")
            return self._create_hold_signal(symbol, f"신호 생성 오류: {str(e)}")
    
    def _validate_basic_data(self, stock_data: Dict[str, Any]) -> bool:
        """기본 데이터 검증"""
        required_fields = ['symbol', 'current_price', 'volume']
        return all(stock_data.get(field) is not None for field in required_fields)
    
    def _create_hold_signal(self, symbol: str, reason: str) -> Dict[str, Any]:
        """HOLD 신호 생성"""
        return {
            'symbol': symbol,
            'action': 'HOLD',
            'confidence': 50,
            'score': 0,
            'reasons': [reason],
            'timestamp': datetime.now().isoformat(),
            'strategy_type': '3분봉 스캘핑'
        }