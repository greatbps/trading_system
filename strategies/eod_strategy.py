#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/eod_strategy.py

장 마감 동시호가(EOD, End of Day) 전략
"""

from .base_strategy import BaseStrategy
from typing import Dict, Any, List
import pandas as pd

class EodStrategy(BaseStrategy):
    """
    장 마감(EOD) 데이터를 기반으로 다음 날 시초가 매매를 결정하는 전략
    - 장 막판에 강한 상승 마감 시 다음 날 갭 상승을 기대하고 매수
    """

    def __init__(self, config):
        super().__init__(config)
        self.name = "EodStrategy"
        self.params = {
            'min_closing_strength': 0.02,  # 종가 강세 최소 기준 (시가 대비 2% 이상 상승)
            'min_volume_ratio': 1.5,       # 최소 거래량 비율 (평균 대비)
        }
        self.logger.info("📈 EOD 전략 초기화 완료")

    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """장 마감 데이터 기반 매매 신호 생성"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"📊 {symbol} EOD 신호 생성 중...")

            # 분석 결과에서 필요한 데이터 추출
            technical_details = analysis_result.get('technical_details', {})
            
            open_price = technical_details.get('open', 0)
            close_price = technical_details.get('close', 0)
            volume_ratio = technical_details.get('volume_ratio', 0)

            if not all([open_price, close_price, volume_ratio]):
                 self.logger.warning(f"⚠️ {symbol}에 대한 데이터 부족. EOD 신호를 생성할 수 없습니다.")
                 return self._create_empty_signal()

            # 신호 점수 계산
            score = 50
            
            # 1. 종가 강세 확인 (양봉 크기)
            closing_strength = (close_price - open_price) / open_price
            is_strong_close = closing_strength >= self.params['min_closing_strength']
            
            if is_strong_close:
                score += 30
            
            # 2. 거래량 확인
            is_volume_surge = volume_ratio >= self.params['min_volume_ratio']
            if is_volume_surge:
                score += 20

            # 3. 강한 마감 + 거래량 동시 충족 시 보너스
            if is_strong_close and is_volume_surge:
                score += 15

            final_score = max(0, min(100, score))

            # 신호 결정 (EOD 전략은 보통 다음날 시초가 매수를 의미)
            if final_score >= 75:
                signal_type = "BUY_TOMORROW_OPEN"
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
                    'open_price': open_price,
                    'close_price': close_price,
                    'closing_strength': closing_strength,
                    'is_strong_close': is_strong_close,
                    'volume_ratio': volume_ratio,
                    'is_volume_surge': is_volume_surge,
                },
                'risk_level': "MEDIUM",
                'timestamp': pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} EOD 신호 생성 실패: {e}")
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
