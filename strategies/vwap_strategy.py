#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/vwap_strategy.py

VWAP (Volume-Weighted Average Price) 기반 전략
"""

from .base_strategy import BaseStrategy
from typing import Dict, Any, List
import pandas as pd

class VwapStrategy(BaseStrategy):
    """VWAP 기반 매매 전략"""

    def __init__(self, config):
        super().__init__(config)
        self.name = "VwapStrategy"
        self.params = {
            'vwap_period': 'D',  # 'D' for daily, 'W' for weekly
        }
        self.logger.info("📈 VWAP 전략 초기화 완료")

    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """
        VWAP을 기반으로 매매 신호를 생성합니다.
        - 현재가가 VWAP 위에 있으면 매수 신호
        - 현재가가 VWAP 아래에 있으면 매도 신호
        """
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"📊 {symbol} VWAP 신호 생성 중...")

            # 필요한 데이터 가져오기
            current_price = getattr(stock_data, 'current_price', 0)
            vwap = getattr(stock_data, 'vwap', 0)

            if not current_price or not vwap:
                self.logger.warning(f"⚠️ {symbol}에 대한 현재가 또는 VWAP 데이터가 부족하여 신호를 생성할 수 없습니다.")
                return self._create_empty_signal()

            # 신호 점수 계산
            score = 50
            price_above_vwap = current_price > vwap
            price_below_vwap = current_price < vwap

            if price_above_vwap:
                # VWAP 대비 얼마나 위에 있는지에 따라 점수 가산
                score += min(25, ((current_price - vwap) / vwap) * 100)
            elif price_below_vwap:
                # VWAP 대비 얼마나 아래에 있는지에 따라 점수 감산
                score -= min(25, ((vwap - current_price) / vwap) * 100)

            final_score = max(0, min(100, score))

            # 신호 결정
            if final_score >= 65:
                signal_type = "BUY"
                action = "BUY"
            elif final_score > 50:
                signal_type = "WEAK_BUY"
                action = "HOLD"
            elif final_score <= 35:
                signal_type = "SELL"
                action = "SELL"
            elif final_score < 50:
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
                    'current_price': current_price,
                    'vwap': vwap,
                    'price_above_vwap': price_above_vwap,
                },
                'risk_level': "MEDIUM", # VWAP만으로는 리스크 평가가 어려움
                'timestamp': pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} VWAP 신호 생성 실패: {e}")
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
