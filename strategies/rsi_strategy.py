#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/rsi_strategy.py

RSI (Relative Strength Index) 기반 전략 - 상대강도지수를 활용한 매매 전략
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_strategy import BaseStrategy


class RsiStrategy(BaseStrategy):
    """RSI (상대강도지수) 기반 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = "rsi"
        self.description = "RSI 상대강도지수 기반 매매 전략"
        
        # RSI 파라미터
        self.rsi_period = 14              # RSI 계산 기간
        self.oversold_threshold = 30      # 과매도 임계값
        self.overbought_threshold = 70    # 과매수 임계값
        self.extreme_oversold = 20        # 극도 과매도
        self.extreme_overbought = 80      # 극도 과매수
        
        # 추가 필터
        self.volume_threshold = 1.2       # 거래량 임계값 (평균 대비)
        self.trend_confirmation_days = 5  # 추세 확인 기간
        
        self.logger.info("✅ RSI 전략 초기화 완료")

    def _safe_get(self, data, key, default=None):
        """StockData 객체 또는 dict에서 안전하게 값을 가져오는 유틸리티 함수"""
        if hasattr(data, key):
            return getattr(data, key, default)
        elif isinstance(data, dict):
            return data.get(key, default)
        else:
            return default

    async def generate_signals(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """RSI 기반 신호 생성"""
        try:
            # StockData 객체 또는 dict에서 안전하게 symbol을 가져옴
            symbol = self._safe_get(stock_data, 'symbol', 'Unknown')
            
            # 1. 기본 데이터 검증
            if not self._validate_basic_data(stock_data):
                return self._create_hold_signal(symbol, "기본 데이터 부족")
            
            # 2. RSI 계산 및 분석
            rsi_signal = await self._analyze_rsi(stock_data)
            
            # 3. 거래량 확인
            volume_signal = await self._analyze_volume_confirmation(stock_data)
            
            # 4. 추세 분석
            trend_signal = await self._analyze_trend_context(stock_data)
            
            # 5. 다이버전스 분석
            divergence_signal = await self._analyze_divergence(stock_data)
            
            # 6. 종합 신호 생성
            final_signal = await self._generate_rsi_signal(
                rsi_signal, volume_signal, trend_signal, divergence_signal, stock_data
            )
            
            return final_signal
            
        except Exception as e:
            self.logger.error(f"❌ RSI 신호 생성 실패 ({symbol}): {e}")
            return self._create_hold_signal(symbol, f"분석 오류: {str(e)}")
    
    async def _analyze_rsi(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """실제 RSI 계산 및 분석"""
        try:
            # 실제 RSI 값이 있는지 확인 (기술적 지표 엔진에서 계산된 값)
            technical_data = self._safe_get(stock_data, 'technical_indicators', {})
            actual_rsi = technical_data.get('rsi', None) if isinstance(technical_data, dict) else None

            if actual_rsi is not None:
                # 실제 계산된 RSI 사용
                estimated_rsi = actual_rsi
                self.logger.debug(f"✅ 실제 RSI 값 사용: {estimated_rsi:.1f}")
            else:
                # 폴백: 기존 추정 방식 사용
                change_rate = self._safe_get(stock_data, 'change_rate', 0)
                current_price = self._safe_get(stock_data, 'current_price', 0)
                high_52w = self._safe_get(stock_data, 'high_52w', current_price)
                low_52w = self._safe_get(stock_data, 'low_52w', current_price)
                
                # 52주 고저점 기준 RSI 근사치 계산
                if high_52w > low_52w:
                    price_position = (current_price - low_52w) / (high_52w - low_52w)
                    estimated_rsi = price_position * 100
                else:
                    estimated_rsi = 50
                
                # 최근 변동률로 RSI 조정
                if change_rate > 0:
                    estimated_rsi = min(estimated_rsi + change_rate * 2, 100)
                else:
                    estimated_rsi = max(estimated_rsi + change_rate * 2, 0)
                
                self.logger.debug(f"⚠️ 추정 RSI 값 사용: {estimated_rsi:.1f}")
            
            signal_strength = 0
            signal_type = "NEUTRAL"
            reasons = []
            
            # RSI 기반 신호 생성 (더 정교한 임계값 적용)
            if estimated_rsi <= self.extreme_oversold:
                signal_strength = 40
                signal_type = "STRONG_BUY"
                reasons.append(f"극도 과매도 구간 (RSI: {estimated_rsi:.1f})")
                reasons.append("강력한 반등 기대")
            elif estimated_rsi <= self.oversold_threshold:
                signal_strength = 30
                signal_type = "BUY"
                reasons.append(f"과매도 구간 (RSI: {estimated_rsi:.1f})")
                reasons.append("반등 신호")
            elif estimated_rsi >= self.extreme_overbought:
                signal_strength = -40
                signal_type = "STRONG_SELL"
                reasons.append(f"극도 과매수 구간 (RSI: {estimated_rsi:.1f})")
                reasons.append("강한 조정 위험")
            elif estimated_rsi >= self.overbought_threshold:
                signal_strength = -30
                signal_type = "SELL"
                reasons.append(f"과매수 구간 (RSI: {estimated_rsi:.1f})")
                reasons.append("조정 신호")
            elif 35 <= estimated_rsi <= 45:
                signal_strength = 15
                signal_type = "WEAK_BUY"
                reasons.append(f"약한 과매도 (RSI: {estimated_rsi:.1f})")
            elif 55 <= estimated_rsi <= 65:
                signal_strength = -15
                signal_type = "WEAK_SELL"
                reasons.append(f"약한 과매수 (RSI: {estimated_rsi:.1f})")
            elif 45 <= estimated_rsi <= 55:
                signal_strength = 5
                signal_type = "NEUTRAL"
                reasons.append(f"중립 구간 (RSI: {estimated_rsi:.1f})")
            
            # RSI 추세 분석 추가
            rsi_trend = self._analyze_rsi_trend(estimated_rsi, technical_data)
            if rsi_trend:
                signal_strength += rsi_trend['strength_adjustment']
                reasons.extend(rsi_trend['reasons'])
            
            return {
                'strength': signal_strength,
                'rsi_value': estimated_rsi,
                'signal_type': signal_type,
                'is_actual_rsi': actual_rsi is not None,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ RSI 분석 실패: {e}")
            return {'strength': 0, 'rsi_value': 50, 'signal_type': 'NEUTRAL', 'reasons': ['RSI 분석 실패']}
    
    def _analyze_rsi_trend(self, current_rsi: float, technical_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """RSI 추세 분석"""
        try:
            # EMA와 MACD를 활용한 RSI 신호 강화
            ema_5 = technical_data.get('ema_5', 0)
            ema_20 = technical_data.get('ema_20', 0)
            macd_line = technical_data.get('macd_line', 0)
            macd_signal = technical_data.get('macd_signal', 0)
            
            strength_adjustment = 0
            reasons = []
            
            # EMA 골든크로스/데드크로스와 RSI 조합
            if ema_5 > ema_20 and current_rsi <= 40:
                strength_adjustment += 10
                reasons.append("EMA 상승추세 + RSI 과매도 = 강화된 매수신호")
            elif ema_5 < ema_20 and current_rsi >= 60:
                strength_adjustment -= 10
                reasons.append("EMA 하락추세 + RSI 과매수 = 강화된 매도신호")
            
            # MACD와 RSI 조합
            if macd_line > macd_signal and current_rsi <= 35:
                strength_adjustment += 8
                reasons.append("MACD 상승전환 + RSI 과매도")
            elif macd_line < macd_signal and current_rsi >= 65:
                strength_adjustment -= 8
                reasons.append("MACD 하락전환 + RSI 과매수")
            
            # RSI 다이버전스 패턴 감지 (간단한 버전)
            if 20 <= current_rsi <= 25:
                strength_adjustment += 5
                reasons.append("RSI 극한 과매도 - 반등 임박")
            elif 75 <= current_rsi <= 80:
                strength_adjustment -= 5
                reasons.append("RSI 극한 과매수 - 조정 임박")
            
            if strength_adjustment != 0 or reasons:
                return {
                    'strength_adjustment': strength_adjustment,
                    'reasons': reasons
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ RSI 추세 분석 실패: {e}")
            return None
    
    async def _analyze_volume_confirmation(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """거래량 확인"""
        try:
            current_volume = self._safe_get(stock_data, 'volume', 0)
            avg_volume = self._safe_get(stock_data, 'avg_volume_30d', current_volume)
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            signal_strength = 0
            reasons = []
            
            if volume_ratio >= 2.0:
                signal_strength = 20
                reasons.append(f"높은 거래량 확인 ({volume_ratio:.1f}배)")
            elif volume_ratio >= self.volume_threshold:
                signal_strength = 10
                reasons.append(f"적정 거래량 ({volume_ratio:.1f}배)")
            elif volume_ratio < 0.8:
                signal_strength = -5
                reasons.append("거래량 부족")
            
            return {
                'strength': signal_strength,
                'volume_ratio': volume_ratio,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 분석 실패: {e}")
            return {'strength': 0, 'volume_ratio': 1.0, 'reasons': ['거래량 분석 실패']}
    
    async def _analyze_trend_context(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """추세 맥락 분석"""
        try:
            change_rate = stock_data.get('change_rate', 0)
            current_price = stock_data.get('current_price', 0)
            high_52w = stock_data.get('high_52w', current_price)
            low_52w = stock_data.get('low_52w', current_price)
            
            # 장기 추세 판단
            if high_52w > low_52w:
                price_trend = (current_price - low_52w) / (high_52w - low_52w)
            else:
                price_trend = 0.5
            
            signal_strength = 0
            reasons = []
            
            # 상승 추세에서 RSI 과매도는 더 강한 매수 신호
            if price_trend > 0.6:
                signal_strength = 10
                reasons.append("상승 추세 확인")
            elif price_trend < 0.4:
                signal_strength = -5
                reasons.append("하락 추세")
            else:
                reasons.append("횡보 추세")
            
            # 단기 모멘텀 추가 고려
            if change_rate > 3.0:
                signal_strength += 10
                reasons.append("강한 단기 상승")
            elif change_rate < -3.0:
                signal_strength -= 10
                reasons.append("강한 단기 하락")
            
            return {
                'strength': min(max(signal_strength, -15), 20),
                'trend_position': price_trend,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 추세 분석 실패: {e}")
            return {'strength': 0, 'trend_position': 0.5, 'reasons': ['추세 분석 실패']}
    
    async def _analyze_divergence(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """다이버전스 분석 (간소화된 버전)"""
        try:
            # 실제로는 과거 가격과 RSI 데이터가 필요하지만,
            # 여기서는 현재 데이터만으로 간접적으로 추정
            change_rate = stock_data.get('change_rate', 0)
            volume = stock_data.get('volume', 0)
            avg_volume = stock_data.get('avg_volume_30d', volume)
            
            signal_strength = 0
            reasons = []
            
            # 가격 하락 + 거래량 증가 = 강세 다이버전스 신호
            if change_rate < -2.0 and volume > avg_volume * 1.5:
                signal_strength = 15
                reasons.append("강세 다이버전스 가능성")
            
            # 가격 상승 + 거래량 감소 = 약세 다이버전스 신호
            elif change_rate > 2.0 and volume < avg_volume * 0.8:
                signal_strength = -10
                reasons.append("약세 다이버전스 가능성")
            
            return {
                'strength': signal_strength,
                'reasons': reasons
            }
            
        except Exception as e:
            self.logger.error(f"❌ 다이버전스 분석 실패: {e}")
            return {'strength': 0, 'reasons': ['다이버전스 분석 실패']}
    
    async def _generate_rsi_signal(self, rsi_signal: Dict, volume_signal: Dict, 
                                 trend_signal: Dict, divergence_signal: Dict, 
                                 stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 RSI 신호 생성"""
        try:
            symbol = stock_data.get('symbol', 'Unknown')
            current_price = stock_data.get('current_price', 0)
            
            # 신호 강도 합산
            total_strength = (
                rsi_signal['strength'] +
                volume_signal['strength'] +
                trend_signal['strength'] +
                divergence_signal['strength']
            )
            
            # 모든 분석 결과 합치기
            all_reasons = []
            all_reasons.extend(rsi_signal.get('reasons', []))
            all_reasons.extend(volume_signal.get('reasons', []))
            all_reasons.extend(trend_signal.get('reasons', []))
            all_reasons.extend(divergence_signal.get('reasons', []))
            
            # RSI 기반 매매 신호 결정
            rsi_value = rsi_signal.get('rsi_value', 50)
            
            if total_strength >= 40 and rsi_value <= self.oversold_threshold:
                action = "STRONG_BUY"
                confidence = min(80 + (50 - rsi_value) * 0.5, 95)
            elif total_strength >= 20 and rsi_value <= self.oversold_threshold:
                action = "BUY"
                confidence = min(70 + (40 - rsi_value) * 0.3, 85)
            elif total_strength <= -30 and rsi_value >= self.overbought_threshold:
                action = "STRONG_SELL"
                confidence = min(80 + (rsi_value - 70) * 0.5, 95)
            elif total_strength <= -15 and rsi_value >= self.overbought_threshold:
                action = "SELL"
                confidence = min(70 + (rsi_value - 60) * 0.3, 85)
            else:
                action = "HOLD"
                confidence = 50 + abs(total_strength) * 0.3
            
            # 목표가 설정
            if action in ["STRONG_BUY", "BUY"]:
                target_profit_rate = 3.0 if rsi_value <= self.extreme_oversold else 2.0
                stop_loss_rate = 2.0
            elif action in ["STRONG_SELL", "SELL"]:
                target_profit_rate = 0
                stop_loss_rate = 1.5
            else:
                target_profit_rate = 0
                stop_loss_rate = 2.0
            
            stop_loss_price = current_price * (1 - stop_loss_rate / 100)
            take_profit_price = current_price * (1 + target_profit_rate / 100) if target_profit_rate > 0 else 0
            
            return {
                'symbol': symbol,
                'action': action,
                'confidence': min(confidence, 95),
                'score': total_strength,
                'current_price': current_price,
                'target_profit_rate': target_profit_rate,
                'stop_loss_price': int(stop_loss_price),
                'take_profit_price': int(take_profit_price) if take_profit_price > 0 else 0,
                'holding_period': '1-2주 (단기)',
                'reasons': all_reasons[:5],  # 상위 5개 이유만
                'analysis_details': {
                    'rsi_analysis': rsi_signal,
                    'volume_analysis': volume_signal,
                    'trend_analysis': trend_signal,
                    'divergence_analysis': divergence_signal,
                    'strategy_type': 'RSI 기반'
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ RSI 신호 생성 실패: {e}")
            return self._create_hold_signal(symbol, f"신호 생성 오류: {str(e)}")
    
    def _validate_basic_data(self, stock_data: Dict[str, Any]) -> bool:
        """기본 데이터 검증"""
        required_fields = ['symbol', 'current_price', 'change_rate']
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
            'strategy_type': 'RSI 기반'
        }