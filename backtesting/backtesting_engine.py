#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/backtesting_engine.py

백테스팅 엔진 - AI 강화 전략 성능 검증
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import pandas as pd
import numpy as np

from database.models import AnalysisResult, Trade
# Note: Some database functions need to be implemented for full functionality
from analyzers.ai_controller import AIController
from strategies.base_strategy import BaseStrategy
from strategies.momentum_strategy import MomentumStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.eod_strategy import EodStrategy
from strategies.supertrend_ema_rsi_strategy import SupertrendEmaRsiStrategy
from strategies.vwap_strategy import VwapStrategy
from strategies.scalping_3m_strategy import Scalping3mStrategy
from strategies.rsi_strategy import RsiStrategy

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """백테스팅 성능 지표"""
    total_return: float = 0.0
    annual_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_trade_duration: float = 0.0
    
    # AI 관련 지표
    ai_accuracy: float = 0.0
    ai_confidence_correlation: float = 0.0
    regime_detection_accuracy: float = 0.0
    risk_adjusted_return: float = 0.0

@dataclass
class BacktestResult:
    """백테스팅 결과"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    metrics: PerformanceMetrics
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    ai_predictions: List[Dict[str, Any]] = field(default_factory=list)
    market_regimes: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def total_return_pct(self) -> float:
        """총 수익률 (%)"""
        return ((self.final_capital - self.initial_capital) / self.initial_capital) * 100

class BacktestingEngine:
    """백테스팅 엔진 - AI 기반 전략 성능 검증"""
    
    def __init__(self, config=None):
        """백테스팅 엔진 초기화"""
        try:
            if config:
                self.ai_controller = AIController(config)
                strategy_config = config
            else:
                # 기본 설정으로 초기화
                import config
                default_config = config.Config()
                self.ai_controller = AIController(default_config)
                strategy_config = default_config
            self.strategies = {
                'momentum': MomentumStrategy(strategy_config),
                'breakout': BreakoutStrategy(strategy_config), 
                'eod': EodStrategy(strategy_config),
                'supertrend_ema_rsi': SupertrendEmaRsiStrategy(strategy_config),
                'vwap': VwapStrategy(strategy_config),
                'scalping_3m': Scalping3mStrategy(strategy_config),
                'rsi': RsiStrategy(strategy_config)
            }
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"백테스팅 엔진 초기화 실패: {e}")
            self.ai_controller = None
            self.strategies = {}
    
    async def run_backtest(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        initial_capital: float = 1000000.0,
        use_ai: bool = True,
        commission: float = 0.0015
    ) -> BacktestResult:
        """
        백테스팅 실행
        
        Args:
            strategy_name: 전략 이름
            start_date: 백테스팅 시작일
            end_date: 백테스팅 종료일
            symbols: 백테스팅 대상 종목 리스트
            initial_capital: 초기 자본
            use_ai: AI 분석 사용 여부
            commission: 수수료율
        
        Returns:
            BacktestResult: 백테스팅 결과
        """
        try:
            self.logger.info(f"백테스팅 시작: {strategy_name} ({start_date} ~ {end_date})")
            
            if strategy_name not in self.strategies:
                raise ValueError(f"지원하지 않는 전략: {strategy_name}")
            
            strategy = self.strategies[strategy_name]
            
            # 결과 초기화
            result = BacktestResult(
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=initial_capital,
                metrics=PerformanceMetrics()
            )
            
            # 포지션 및 자본 추적
            current_capital = initial_capital
            positions = {}  # symbol -> quantity
            cash = initial_capital
            
            # 일별 백테스팅 실행
            current_date = start_date
            while current_date <= end_date:
                
                # 주말 제외
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue
                
                # 해당 날짜의 주식 데이터 및 분석 결과 가져오기
                daily_data = await self._get_daily_data(symbols, current_date)
                
                if not daily_data:
                    current_date += timedelta(days=1)
                    continue
                
                # AI 분석 수행 (선택적)
                ai_insights = None
                if use_ai:
                    ai_insights = await self._get_ai_insights(daily_data, current_date)
                    result.ai_predictions.extend(ai_insights.get('predictions', []))
                    result.market_regimes.extend(ai_insights.get('regimes', []))
                
                # 각 종목에 대해 전략 실행
                for symbol, stock_data in daily_data.items():
                    
                    # 전략 시그널 생성
                    signal = await strategy.analyze(stock_data, ai_insights)
                    
                    if signal and signal.action in ['BUY', 'SELL']:
                        # 거래 실행
                        trade_result = await self._execute_trade(
                            symbol, signal, stock_data, 
                            positions, cash, commission
                        )
                        
                        if trade_result:
                            positions = trade_result['positions']
                            cash = trade_result['cash']
                            result.trades.append(trade_result['trade'])
                
                # 일일 포트폴리오 가치 계산
                portfolio_value = await self._calculate_portfolio_value(
                    positions, cash, daily_data
                )
                
                result.equity_curve.append({
                    'date': current_date,
                    'portfolio_value': portfolio_value,
                    'cash': cash,
                    'positions_value': portfolio_value - cash
                })
                
                current_date += timedelta(days=1)
            
            # 최종 포트폴리오 가치 계산
            final_data = await self._get_daily_data(symbols, end_date)
            result.final_capital = await self._calculate_portfolio_value(
                positions, cash, final_data
            )
            
            # 성능 지표 계산
            result.metrics = await self._calculate_metrics(result, use_ai)
            
            # 결과 저장
            await save_backtest_result(result)
            
            self.logger.info(f"백테스팅 완료: {strategy_name} (수익률: {result.total_return_pct:.2f}%)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"백테스팅 오류: {e}")
            raise
    
    async def _get_daily_data(self, symbols: List[str], date: datetime) -> Dict[str, Dict]:
        """특정 날짜의 주식 데이터 가져오기"""
        try:
            daily_data = {}
            
            for symbol in symbols:
                # 데이터베이스에서 해당 날짜의 분석 결과 가져오기
                analysis_data = await get_historical_analysis(symbol, date)
                
                if analysis_data:
                    # 주식 데이터 형식으로 변환
                    stock_data = {
                        'symbol': symbol,
                        'date': date,
                        'price': analysis_data.get('current_price', 0),
                        'volume': analysis_data.get('volume', 0),
                        'technical_score': analysis_data.get('technical_score', 0),
                        'sentiment_score': analysis_data.get('sentiment_score', 0),
                        'final_score': analysis_data.get('final_score', 0),
                        'analysis_data': analysis_data
                    }
                    daily_data[symbol] = stock_data
            
            return daily_data
            
        except Exception as e:
            self.logger.error(f"일일 데이터 가져오기 오류: {e}")
            return {}
    
    async def _get_ai_insights(self, daily_data: Dict, date: datetime) -> Dict[str, Any]:
        """AI 인사이트 생성"""
        try:
            # 시장 데이터 준비
            market_data = []
            individual_stocks = []
            
            for symbol, data in daily_data.items():
                individual_stocks.append(data)
                market_data.append({
                    'symbol': symbol,
                    'price': data['price'],
                    'volume': data['volume'],
                    'technical_score': data['technical_score']
                })
            
            # 포트폴리오 데이터 (간단화)
            portfolio_data = {
                'total_value': sum(d['price'] for d in daily_data.values()),
                'positions': len(daily_data)
            }
            
            # AI 종합 분석 수행
            ai_analysis = await self.ai_controller.comprehensive_market_analysis(
                market_data, individual_stocks, portfolio_data
            )
            
            return {
                'predictions': ai_analysis.get('market_prediction', []),
                'regimes': ai_analysis.get('market_regime', []),
                'risk_assessment': ai_analysis.get('risk_assessment', {}),
                'strategy_optimization': ai_analysis.get('strategy_optimization', {})
            }
            
        except Exception as e:
            self.logger.error(f"AI 인사이트 생성 오류: {e}")
            return {}
    
    async def _execute_trade(
        self,
        symbol: str,
        signal: Signal,
        stock_data: Dict,
        positions: Dict,
        cash: float,
        commission: float
    ) -> Optional[Dict]:
        """거래 실행 시뮬레이션"""
        try:
            price = stock_data['price']
            if price <= 0:
                return None
            
            trade = {
                'symbol': symbol,
                'date': stock_data['date'],
                'action': signal.action,
                'price': price,
                'confidence': signal.confidence,
                'quantity': 0,
                'amount': 0,
                'commission': 0,
                'net_amount': 0
            }
            
            if signal.action == 'BUY':
                # 가용 현금의 일정 비율로 매수 (리스크 관리)
                max_investment = cash * 0.1  # 최대 10%
                quantity = int(max_investment / price)
                
                if quantity > 0:
                    amount = quantity * price
                    commission_fee = amount * commission
                    total_cost = amount + commission_fee
                    
                    if total_cost <= cash:
                        positions[symbol] = positions.get(symbol, 0) + quantity
                        cash -= total_cost
                        
                        trade.update({
                            'quantity': quantity,
                            'amount': amount,
                            'commission': commission_fee,
                            'net_amount': total_cost
                        })
                        
                        return {
                            'positions': positions,
                            'cash': cash,
                            'trade': trade
                        }
            
            elif signal.action == 'SELL':
                # 보유 수량 전체 매도
                quantity = positions.get(symbol, 0)
                
                if quantity > 0:
                    amount = quantity * price
                    commission_fee = amount * commission
                    net_amount = amount - commission_fee
                    
                    positions[symbol] = 0
                    cash += net_amount
                    
                    trade.update({
                        'quantity': -quantity,  # 매도는 음수
                        'amount': amount,
                        'commission': commission_fee,
                        'net_amount': net_amount
                    })
                    
                    return {
                        'positions': positions,
                        'cash': cash,
                        'trade': trade
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"거래 실행 오류: {e}")
            return None
    
    async def _calculate_portfolio_value(
        self,
        positions: Dict,
        cash: float,
        daily_data: Dict
    ) -> float:
        """포트폴리오 가치 계산"""
        try:
            portfolio_value = cash
            
            for symbol, quantity in positions.items():
                if quantity > 0 and symbol in daily_data:
                    current_price = daily_data[symbol]['price']
                    portfolio_value += quantity * current_price
            
            return portfolio_value
            
        except Exception as e:
            self.logger.error(f"포트폴리오 가치 계산 오류: {e}")
            return cash
    
    async def _calculate_metrics(self, result: BacktestResult, use_ai: bool) -> PerformanceMetrics:
        """성능 지표 계산"""
        try:
            metrics = PerformanceMetrics()
            
            if not result.trades or not result.equity_curve:
                return metrics
            
            # 기본 지표 계산
            total_return = result.final_capital - result.initial_capital
            metrics.total_return = total_return
            
            # 기간 계산 (연단위)
            days = (result.end_date - result.start_date).days
            years = days / 365.25
            
            if years > 0:
                metrics.annual_return = ((result.final_capital / result.initial_capital) ** (1/years) - 1) * 100
            
            # 거래 분석
            profits = []
            losses = []
            
            for trade in result.trades:
                if trade['action'] == 'SELL' and trade['net_amount'] > 0:
                    # 매도시 수익/손실 계산 (간단화)
                    pnl = trade['net_amount'] - (abs(trade['quantity']) * trade['price'])
                    
                    if pnl > 0:
                        profits.append(pnl)
                        metrics.winning_trades += 1
                    else:
                        losses.append(abs(pnl))
                        metrics.losing_trades += 1
            
            metrics.total_trades = len(result.trades)
            
            if metrics.total_trades > 0:
                metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
            
            if profits:
                metrics.avg_win = np.mean(profits)
                metrics.largest_win = max(profits)
            
            if losses:
                metrics.avg_loss = np.mean(losses)
                metrics.largest_loss = max(losses)
            
            # 수익 팩터
            total_profit = sum(profits) if profits else 0
            total_loss = sum(losses) if losses else 0
            
            if total_loss > 0:
                metrics.profit_factor = total_profit / total_loss
            
            # 변동성 및 샤프 비율
            if len(result.equity_curve) > 1:
                returns = []
                for i in range(1, len(result.equity_curve)):
                    prev_value = result.equity_curve[i-1]['portfolio_value']
                    curr_value = result.equity_curve[i]['portfolio_value']
                    if prev_value > 0:
                        daily_return = (curr_value - prev_value) / prev_value
                        returns.append(daily_return)
                
                if returns:
                    metrics.volatility = np.std(returns) * np.sqrt(252) * 100  # 연변동성
                    
                    avg_return = np.mean(returns)
                    if metrics.volatility > 0:
                        metrics.sharpe_ratio = (avg_return * 252) / (metrics.volatility / 100)
            
            # 최대 낙폭 (Max Drawdown)
            max_value = result.initial_capital
            max_drawdown = 0
            
            for point in result.equity_curve:
                value = point['portfolio_value']
                if value > max_value:
                    max_value = value
                else:
                    drawdown = (max_value - value) / max_value
                    max_drawdown = max(max_drawdown, drawdown)
            
            metrics.max_drawdown = max_drawdown * 100
            
            # AI 관련 지표 (AI 사용시에만)
            if use_ai and result.ai_predictions:
                # AI 예측 정확도 계산 (간단화)
                correct_predictions = 0
                total_predictions = len(result.ai_predictions)
                
                for prediction in result.ai_predictions:
                    # 실제 구현에서는 예측과 실제 결과를 비교
                    confidence = prediction.get('confidence', 0)
                    if confidence > 0.7:  # 높은 신뢰도 예측이 맞았다고 가정
                        correct_predictions += 1
                
                if total_predictions > 0:
                    metrics.ai_accuracy = (correct_predictions / total_predictions) * 100
            
            # 리스크 조정 수익률
            if metrics.volatility > 0:
                metrics.risk_adjusted_return = metrics.annual_return / (metrics.volatility / 100)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"성능 지표 계산 오류: {e}")
            return PerformanceMetrics()
    
    async def compare_strategies(
        self,
        strategies: List[str],
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        initial_capital: float = 1000000.0
    ) -> Dict[str, BacktestResult]:
        """여러 전략 비교 백테스팅"""
        try:
            results = {}
            
            for strategy_name in strategies:
                self.logger.info(f"전략 백테스팅: {strategy_name}")
                
                # AI 사용 버전
                result_with_ai = await self.run_backtest(
                    strategy_name, start_date, end_date, symbols,
                    initial_capital, use_ai=True
                )
                
                # AI 미사용 버전
                result_without_ai = await self.run_backtest(
                    strategy_name, start_date, end_date, symbols,
                    initial_capital, use_ai=False
                )
                
                results[f"{strategy_name}_with_ai"] = result_with_ai
                results[f"{strategy_name}_without_ai"] = result_without_ai
            
            return results
            
        except Exception as e:
            self.logger.error(f"전략 비교 백테스팅 오류: {e}")
            raise

    async def run_walk_forward_analysis(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str],
        window_months: int = 6,
        step_months: int = 1
    ) -> List[BacktestResult]:
        """워크 포워드 분석 실행"""
        try:
            results = []
            current_start = start_date
            
            while current_start < end_date:
                # 분석 기간 설정
                window_end = current_start + timedelta(days=window_months * 30)
                if window_end > end_date:
                    window_end = end_date
                
                # 백테스팅 실행
                result = await self.run_backtest(
                    strategy_name, current_start, window_end, symbols
                )
                
                results.append(result)
                
                # 다음 기간으로 이동
                current_start += timedelta(days=step_months * 30)
            
            return results
            
        except Exception as e:
            self.logger.error(f"워크 포워드 분석 오류: {e}")
            raise