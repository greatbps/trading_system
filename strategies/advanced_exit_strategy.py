#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
advanced_exit_strategy.py

매매조건고도화.md 기반 고도화된 매도 전략
- ATR 기반 트레일링 스탑
- 부분 익절 (Scale-out)
- 볼륨/VWAP 필터
- 시간 필터
"""

import asyncio
import numpy as np
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from utils.logger import get_logger

@dataclass
class ExitSignal:
    """매도 신호 정보"""
    symbol: str
    signal_type: str  # 'partial_profit', 'trailing_stop', 'hard_stop', 'time_filter', 'volume_break'
    quantity_ratio: float  # 매도할 비율 (0.0 ~ 1.0)
    price: Optional[float] = None
    reason: str = ""
    confidence: float = 0.0

@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    entry_price: float
    current_price: float
    quantity: int
    entry_time: datetime
    highest_price: float = 0.0
    trailing_stop: Optional[float] = None
    partial_sold: Dict[str, bool] = None  # {'level1': False, 'level2': False}

    def __post_init__(self):
        if self.partial_sold is None:
            self.partial_sold = {'level1': False, 'level2': False}
        if self.highest_price == 0.0:
            self.highest_price = self.current_price

class AdvancedExitStrategy:
    """고도화된 매도 전략"""

    def __init__(self, config=None):
        self.logger = get_logger("AdvancedExitStrategy")
        self.config = config

        # 매도 조건 파라미터 (매매조건고도화.md 기반)
        self.params = {
            # 기본 손익 기준
            'hard_stop_loss': 0.97,      # -3% 하드 스탑
            'soft_target': 1.06,         # +6% 소프트 타깃

            # 부분 익절 설정
            'partial_tp_level1': 1.04,   # +4% 1차 부분익절
            'partial_tp_level2': 1.06,   # +6% 2차 부분익절
            'partial_ratio_1': 0.4,      # 1차에서 40% 매도
            'partial_ratio_2': 0.4,      # 2차에서 40% 매도 (잔여 20%는 트레일링)

            # ATR 트레일링 설정
            'atr_period': 14,            # ATR 계산 기간
            'atr_multiplier': 1.5,       # ATR 배수

            # EMA/볼륨 필터
            'ema_period': 5,             # 3분봉 5기간 EMA
            'volume_threshold': 1.2,     # 평균 거래량 대비 배수

            # 시간 필터
            'market_close_minutes': 30,  # 장 마감 N분 전 청산
        }

        self.positions: Dict[str, PositionInfo] = {}

    async def update_position(self, symbol: str, holding_data: Dict[str, Any]) -> None:
        """포지션 정보 업데이트"""
        try:
            current_price = holding_data.get('current_price', 0)
            entry_price = holding_data.get('avg_price', 0)
            quantity = holding_data.get('quantity', 0)

            if symbol not in self.positions:
                self.positions[symbol] = PositionInfo(
                    symbol=symbol,
                    entry_price=entry_price,
                    current_price=current_price,
                    quantity=quantity,
                    entry_time=datetime.now(),
                    highest_price=current_price
                )
                self.logger.info(f"새 포지션 등록: {symbol} @ {entry_price}")
            else:
                pos = self.positions[symbol]
                pos.current_price = current_price
                pos.highest_price = max(pos.highest_price, current_price)
                pos.quantity = quantity

        except Exception as e:
            self.logger.error(f"포지션 업데이트 실패 {symbol}: {e}")

    async def analyze_exit_signals(self, symbol: str, market_data: Dict[str, Any] = None) -> List[ExitSignal]:
        """고도화된 매도 신호 분석"""
        if symbol not in self.positions:
            return []

        pos = self.positions[symbol]
        signals = []

        try:
            # 1. 하드 스탑 체크 (최우선)
            if pos.current_price <= pos.entry_price * self.params['hard_stop_loss']:
                signals.append(ExitSignal(
                    symbol=symbol,
                    signal_type='hard_stop',
                    quantity_ratio=1.0,  # 전량 매도
                    reason=f"하드스탑 ({self.params['hard_stop_loss']:.1%}) 도달",
                    confidence=0.95
                ))
                return signals  # 하드스탑은 즉시 실행

            # 2. 부분 익절 체크
            profit_rate = (pos.current_price / pos.entry_price) - 1

            # 1차 부분익절 (+4%)
            if (profit_rate >= (self.params['partial_tp_level1'] - 1) and
                not pos.partial_sold['level1']):
                signals.append(ExitSignal(
                    symbol=symbol,
                    signal_type='partial_profit',
                    quantity_ratio=self.params['partial_ratio_1'],
                    reason=f"1차 부분익절 (+{(self.params['partial_tp_level1']-1)*100:.1f}%)",
                    confidence=0.8
                ))
                pos.partial_sold['level1'] = True

            # 2차 부분익절 (+6%)
            if (profit_rate >= (self.params['partial_tp_level2'] - 1) and
                not pos.partial_sold['level2']):
                signals.append(ExitSignal(
                    symbol=symbol,
                    signal_type='partial_profit',
                    quantity_ratio=self.params['partial_ratio_2'],
                    reason=f"2차 부분익절 (+{(self.params['partial_tp_level2']-1)*100:.1f}%)",
                    confidence=0.85
                ))
                pos.partial_sold['level2'] = True

                # +6% 도달시 트레일링 스탑 활성화
                await self._activate_trailing_stop(pos, market_data)

            # 3. ATR 트레일링 스탑 체크 (부분익절 후)
            if pos.trailing_stop and pos.current_price <= pos.trailing_stop:
                signals.append(ExitSignal(
                    symbol=symbol,
                    signal_type='trailing_stop',
                    quantity_ratio=1.0,  # 잔여 전량
                    reason=f"ATR 트레일링 스탑 (${pos.trailing_stop:.2f}) 도달",
                    confidence=0.9
                ))

            # 4. EMA + 볼륨 브레이크다운 체크
            if await self._check_ema_volume_breakdown(symbol, pos, market_data):
                signals.append(ExitSignal(
                    symbol=symbol,
                    signal_type='volume_break',
                    quantity_ratio=1.0,
                    reason="EMA5 하향이탈 + 거래량 증가",
                    confidence=0.75
                ))

            # 5. 시간 필터 체크
            if self._check_time_filter():
                signals.append(ExitSignal(
                    symbol=symbol,
                    signal_type='time_filter',
                    quantity_ratio=1.0,
                    reason=f"장 마감 {self.params['market_close_minutes']}분 전 청산",
                    confidence=0.7
                ))

        except Exception as e:
            self.logger.error(f"매도 신호 분석 실패 {symbol}: {e}")

        return signals

    async def _activate_trailing_stop(self, pos: PositionInfo, market_data: Dict[str, Any] = None) -> None:
        """ATR 기반 트레일링 스탑 활성화"""
        try:
            # ATR 계산 (시뮬레이션 - 실제로는 차트 데이터 필요)
            atr_value = await self._calculate_atr(pos.symbol, market_data)
            if atr_value > 0:
                initial_trailing = pos.highest_price - (self.params['atr_multiplier'] * atr_value)
                pos.trailing_stop = max(pos.trailing_stop or 0, initial_trailing)
                self.logger.info(f"{pos.symbol} 트레일링 스탑 설정: ${pos.trailing_stop:.2f} (ATR: {atr_value:.2f})")

        except Exception as e:
            self.logger.error(f"트레일링 스탑 설정 실패 {pos.symbol}: {e}")

    async def _calculate_atr(self, symbol: str, market_data: Dict[str, Any] = None) -> float:
        """ATR 계산 (시뮬레이션)"""
        try:
            # 실제 구현시에는 차트 데이터에서 ATR 계산
            # 여기서는 현재가의 2% 정도로 시뮬레이션
            if symbol in self.positions:
                current_price = self.positions[symbol].current_price
                return current_price * 0.02  # 2% 가정
            return 0.0
        except Exception:
            return 0.0

    async def _check_ema_volume_breakdown(self, symbol: str, pos: PositionInfo, market_data: Dict[str, Any] = None) -> bool:
        """EMA + 볼륨 브레이크다운 체크"""
        try:
            # +6% 이상 수익 상태에서만 적용
            profit_rate = (pos.current_price / pos.entry_price) - 1
            if profit_rate < (self.params['soft_target'] - 1):
                return False

            # 실제 구현시에는 차트 데이터에서 EMA5, 거래량 계산
            # 여기서는 시뮬레이션
            if market_data:
                ema5 = market_data.get('ema5', pos.current_price)
                current_volume = market_data.get('volume', 0)
                avg_volume = market_data.get('avg_volume', 1)

                # EMA5 하향 이탈 + 거래량 1.2배 이상
                if (pos.current_price < ema5 and
                    current_volume > avg_volume * self.params['volume_threshold']):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"EMA/볼륨 체크 실패 {symbol}: {e}")
            return False

    def _check_time_filter(self) -> bool:
        """시간 필터 체크 (장 마감 전)"""
        try:
            now = datetime.now().time()
            # 한국 증시 마감시간 15:30 기준
            market_close = time(15, 30)
            close_threshold = time(15, 30 - self.params['market_close_minutes'])

            if now >= close_threshold:
                return True

        except Exception as e:
            self.logger.error(f"시간 필터 체크 실패: {e}")

        return False

    async def update_trailing_stops(self) -> None:
        """모든 포지션의 트레일링 스탑 업데이트"""
        for symbol, pos in self.positions.items():
            if pos.trailing_stop:
                try:
                    atr_value = await self._calculate_atr(symbol)
                    new_trailing = pos.highest_price - (self.params['atr_multiplier'] * atr_value)

                    # 트레일링 스탑은 상향만 조정
                    if new_trailing > pos.trailing_stop:
                        pos.trailing_stop = new_trailing
                        self.logger.debug(f"{symbol} 트레일링 스탑 업데이트: ${pos.trailing_stop:.2f}")

                except Exception as e:
                    self.logger.error(f"트레일링 스탑 업데이트 실패 {symbol}: {e}")

    def remove_position(self, symbol: str) -> None:
        """포지션 제거"""
        if symbol in self.positions:
            del self.positions[symbol]
            self.logger.info(f"포지션 제거: {symbol}")

    def get_position_summary(self) -> Dict[str, Dict[str, Any]]:
        """포지션 요약 정보"""
        summary = {}
        for symbol, pos in self.positions.items():
            profit_rate = (pos.current_price / pos.entry_price - 1) * 100
            summary[symbol] = {
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'profit_rate': profit_rate,
                'highest_price': pos.highest_price,
                'trailing_stop': pos.trailing_stop,
                'partial_sold': pos.partial_sold,
                'quantity': pos.quantity
            }
        return summary