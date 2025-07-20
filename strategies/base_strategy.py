#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/base_strategy.py

전략 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from utils.logger import get_logger

class BaseStrategy(ABC):
    """전략 기본 클래스"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(f"Strategy_{self.__class__.__name__}")
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """매매 신호 생성 (추상 메서드)"""
        pass
    
    async def calculate_position_size(self, signal: Dict, account_info: Dict) -> float:
        """포지션 크기 계산"""
        try:
            signal_strength = signal.get('signal_strength', 50)
            confidence = signal.get('confidence', 0.5)
            risk_level = signal.get('risk_level', 'MEDIUM')
            
            # 기본 포지션 크기
            base_size = self.config.trading.MAX_POSITION_SIZE
            
            # 신호 강도에 따른 조정
            strength_factor = signal_strength / 100
            
            # 신뢰도에 따른 조정
            confidence_factor = confidence
            
            # 리스크에 따른 조정
            risk_factors = {
                'LOW': 1.0,
                'MEDIUM': 0.7,
                'HIGH': 0.5
            }
            risk_factor = risk_factors.get(risk_level, 0.7)
            
            # 최종 포지션 크기 계산
            position_size = base_size * strength_factor * confidence_factor * risk_factor
            
            # 최소/최대 제한
            position_size = max(0.01, min(base_size, position_size))
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"❌ 포지션 크기 계산 실패: {e}")
            return 0.01  # 최소 포지션
    
    async def calculate_stop_loss(self, stock_data: Dict, entry_price: float) -> float:
        """손절가 계산 (기본 구현)"""
        return entry_price * (1 - self.config.trading.STOP_LOSS_RATIO)
    
    async def calculate_take_profit(self, stock_data: Dict, entry_price: float) -> float:
        """익절가 계산 (기본 구현)"""
        return entry_price * (1 + self.config.trading.TAKE_PROFIT_RATIO)
    
    def validate_signal(self, signal: Dict) -> bool:
        """신호 유효성 검사"""
        required_fields = ['signal_strength', 'signal_type', 'action', 'confidence']
        return all(field in signal for field in required_fields)