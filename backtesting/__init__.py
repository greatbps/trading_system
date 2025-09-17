#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/__init__.py

백테스팅 및 검증 프레임워크 - Phase 6 Backtesting & Validation Framework
AI 기반 전략 성능 검증 및 비교 분석
"""

from .backtesting_engine import BacktestingEngine, BacktestResult, PerformanceMetrics
from .strategy_validator import StrategyValidator, ValidationResult, StrategyComparison
from .historical_analyzer import HistoricalAnalyzer, HistoricalData, MarketCondition
from .performance_visualizer import PerformanceVisualizer, ReportGenerator

__all__ = [
    'BacktestingEngine', 'BacktestResult', 'PerformanceMetrics',
    'StrategyValidator', 'ValidationResult', 'StrategyComparison',
    'HistoricalAnalyzer', 'HistoricalData', 'MarketCondition',
    'PerformanceVisualizer', 'ReportGenerator'
]