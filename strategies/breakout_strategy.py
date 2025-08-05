#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/breakout_strategy.py

돌파 매매 전략
"""

from .base_strategy import BaseStrategy
from typing import Dict, Any, List
import pandas as pd

class BreakoutStrategy(BaseStrategy):
    """
    가격 돌파 및 거래량 급증을 기반으로 한 매매 전략
    - N일 신고가 돌파 시 매수
    - 거래량 조건 충족 시 신호 강화
    """

    def __init__(self, config):
        super().__init__(config)
        self.name = "BreakoutStrategy"
        self.params = {
            'breakout_period': 20,  # 돌파 기간 (일)
            'volume_multiplier': 2.0,  # 거래량 배수 (평균 대비)
        }
        self.logger.info("📈 돌파 매매 전략 초기화 완료")

    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """돌파 기반 매매 신호 생성"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"📊 {symbol} 돌파 신호 생성 중...")

            # 차트 데이터 필요 (실제로는 데이터 수집기에서 가져와야 함)
            # 이 예제에서는 analysis_result에 필요한 데이터가 있다고 가정합니다.
            technical_details = analysis_result.get('technical_details', {})
            
            current_price = technical_details.get('current_price', 0)
            recent_high = technical_details.get('recent_high', 0) # N일 고가
            volume_ratio = technical_details.get('volume_ratio', 0) # 거래량 비율

            if not all([current_price, recent_high, volume_ratio]):
                 self.logger.warning(f"⚠️ {symbol}에 대한 데이터 부족. 돌파 신호를 생성할 수 없습니다.")
                 return self._create_empty_signal()

            # 신호 점수 계산
            score = 50
            
            # 1. 가격 돌파 확인
            is_breakout = current_price >= recent_high
            if is_breakout:
                score += 30
            
            # 2. 거래량 조건 확인
            is_volume_surge = volume_ratio >= self.params['volume_multiplier']
            if is_volume_surge:
                score += 20

            # 3. 돌파 + 거래량 동시 충족 시 보너스
            if is_breakout and is_volume_surge:
                score += 15

            final_score = max(0, min(100, score))

            # 신호 결정
            if final_score >= 80:
                signal_type = "STRONG_BUY"
                action = "BUY"
            elif final_score >= 65:
                signal_type = "BUY"
                action = "BUY"
            else:
                signal_type = "HOLD"
                action = "HOLD"

            return {
                'signal_strength': round(final_score, 1),
                'signal_type': signal_type,
                'action': action,
                'confidence': min(1.0, final_score / 100),
                'details': {
                    'current_price': current_price,
                    'breakout_target_price': recent_high,
                    'is_breakout': is_breakout,
                    'volume_ratio': volume_ratio,
                    'is_volume_surge': is_volume_surge,
                },
                'risk_level': "HIGH" if is_breakout else "MEDIUM",
                'timestamp': pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} 돌파 신호 생성 실패: {e}")
            return self._create_empty_signal()

    def _create_empty_signal(self) -> Dict[str, Any]:
        """빈 신호 생성"""
        return {
            'signal_strength': 50.0,
            'signal_type': "HOLD",
            'action': "HOLD",
            'confidence': 0.5,
            'details': {},
            'risk_level': "MEDIUM",
            'timestamp': pd.Timestamp.now().isoformat()
        }
