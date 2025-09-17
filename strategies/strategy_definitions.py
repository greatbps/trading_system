#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1-8번 전략 정의 및 관리 시스템
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict

class StrategyType(Enum):
    """8가지 핵심 전략 정의"""
    AI_ANALYSIS = "1"
    MOMENTUM = "2" 
    BREAKOUT = "3"
    RSI_STRATEGY = "4"
    SUPERTREND_EMA = "5"
    VWAP_STRATEGY = "6"
    SCALPING_3M = "7"
    SMART_MONEY = "8"

@dataclass
class StrategyInfo:
    """전략 기본 정보"""
    strategy_id: str
    name: str
    description: str
    timeframe: str
    risk_level: str
    expected_win_rate: float

# 전략별 상세 정보
STRATEGY_INFO_MAP: Dict[StrategyType, StrategyInfo] = {
    StrategyType.AI_ANALYSIS: StrategyInfo("1", "AI_ANALYSIS", "AI 분석 기반 종목 추천", "1D", "MEDIUM", 0.65),
    StrategyType.MOMENTUM: StrategyInfo("2", "MOMENTUM", "모멘텀 지표 기반 추세 추종", "1H", "HIGH", 0.60),
    StrategyType.BREAKOUT: StrategyInfo("3", "BREAKOUT", "저항선/지지선 돌파", "30M", "HIGH", 0.55),
    StrategyType.RSI_STRATEGY: StrategyInfo("4", "RSI_STRATEGY", "RSI 과매수/과매도 역추세", "1H", "MEDIUM", 0.58),
    StrategyType.SUPERTREND_EMA: StrategyInfo("5", "SUPERTREND_EMA", "슈퍼트렌드 + EMA 조합", "15M", "MEDIUM", 0.62),
    StrategyType.VWAP_STRATEGY: StrategyInfo("6", "VWAP_STRATEGY", "VWAP 기준 매매", "5M", "LOW", 0.68),
    StrategyType.SCALPING_3M: StrategyInfo("7", "SCALPING_3M", "3분봉 단타 스캘핑", "3M", "HIGH", 0.52),
    StrategyType.SMART_MONEY: StrategyInfo("8", "SMART_MONEY", "스마트머니 움직임 추적", "1D", "MEDIUM", 0.70)
}

class StrategyManager:
    """전략 관리 시스템"""
    
    def __init__(self):
        self.strategies = STRATEGY_INFO_MAP
    
    def get_all_strategies(self):
        return self.strategies
    
    def validate_strategy_name(self, strategy_name: str) -> bool:
        return any(info.name == strategy_name for info in self.strategies.values())
    
    def get_strategy_display_name(self, strategy_name: str) -> str:
        for info in self.strategies.values():
            if info.name == strategy_name:
                return f"{info.strategy_id}번. {info.name}"
        return strategy_name

    def get_strategy_by_name(self, strategy_name: str):
        for info in self.strategies.values():
            if info.name == strategy_name:
                return info
        return None
