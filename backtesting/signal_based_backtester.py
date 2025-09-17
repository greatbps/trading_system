#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/signal_based_backtester.py

실제 매매 신호 기반 백테스팅 시스템
매매조건.md의 기준에 따른 실제 매수/매도 타이밍 적용
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import logging

from config import Config


@dataclass
class TradingSignal:
    """매매 신호 데이터 클래스"""
    timestamp: datetime
    signal_type: str  # 'BUY', 'SELL', 'PARTIAL_SELL'
    price: float
    volume: int
    confidence: float
    reasons: List[str]
    indicators: Dict[str, float]
    partial_ratio: float = 0.0  # 부분 매도 비율 (1/3, 2/3 등)


@dataclass
class Trade:
    """거래 기록 데이터 클래스"""
    symbol: str
    strategy: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: int = 0
    trade_type: str = "LONG"  # LONG, SHORT
    status: str = "OPEN"  # OPEN, CLOSED, PARTIAL
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    exit_reason: str = ""
    partial_exits: List[Dict] = None
    
    def __post_init__(self):
        if self.partial_exits is None:
            self.partial_exits = []


@dataclass
class BacktestResult:
    """백테스팅 결과 데이터 클래스"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_loss: float
    profit_loss_pct: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade]
    daily_returns: List[float]
    metrics: Dict[str, Any]


class SignalBasedBacktester:
    """실제 매매 신호 기반 백테스터"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 백테스팅 설정
        self.initial_capital = 10000000  # 1천만원
        self.commission_rate = 0.0015    # 0.15% 수수료
        self.slippage_rate = 0.001       # 0.1% 슬리피지
        
        self.logger.info("✅ Signal-Based Backtester 초기화 완료")
    
    async def run_strategy_backtest(
        self,
        strategy_name: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        chart_data: List[Dict],
        optimize_params: bool = True
    ) -> BacktestResult:
        """전략별 백테스팅 실행"""
        try:
            self.logger.info(f"📊 {strategy_name} 전략 백테스팅 시작: {symbol} ({start_date} ~ {end_date})")
            
            # 1. 차트 데이터 전처리
            df = self._prepare_chart_data(chart_data)
            if df.empty:
                raise ValueError("차트 데이터가 없습니다.")
            
            # 2. 기술적 지표 계산
            df = await self._calculate_technical_indicators(df, strategy_name)
            
            # 3. 매매 신호 생성
            signals = await self._generate_trading_signals(df, strategy_name, symbol)
            
            # 4. 파라미터 최적화 (옵션)
            if optimize_params:
                optimized_params = await self._optimize_parameters(df, signals, strategy_name)
                self.logger.info(f"🎯 최적화된 파라미터: {optimized_params}")
                
                # 최적화된 파라미터로 신호 재생성
                signals = await self._generate_trading_signals(df, strategy_name, symbol, optimized_params)
            
            # 5. 백테스팅 실행
            trades = await self._execute_backtest(df, signals, symbol, strategy_name)
            
            # 6. 결과 계산
            result = await self._calculate_backtest_results(
                strategy_name, symbol, start_date, end_date, trades, df
            )
            
            self.logger.info(f"✅ {strategy_name} 백테스팅 완료: 수익률 {result.profit_loss_pct:.2f}%, 승률 {result.win_rate:.1f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 백테스팅 실행 오류: {e}")
            raise
    
    def _prepare_chart_data(self, chart_data: List[Dict]) -> pd.DataFrame:
        """차트 데이터 전처리"""
        try:
            df = pd.DataFrame(chart_data)
            
            # 필수 컬럼 확인
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"필수 컬럼 누락: {col}")
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            # 정렬 및 인덱스 설정
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 결측값 처리
            df = df.fillna(method='ffill').dropna()
            
            self.logger.debug(f"📈 차트 데이터 전처리 완료: {len(df)}개 봉")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ 차트 데이터 전처리 오류: {e}")
            return pd.DataFrame()
    
    async def _calculate_technical_indicators(self, df: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
        """기술적 지표 계산"""
        try:
            # 공통 지표
            df = self._calculate_moving_averages(df)
            df = self._calculate_rsi(df)
            df = self._calculate_macd(df)
            df = self._calculate_bollinger_bands(df)
            df = self._calculate_volume_indicators(df)
            
            # 전략별 특화 지표
            if strategy_name == "scalping_3m":
                df = self._calculate_scalping_indicators(df)
            elif strategy_name == "rsi":
                df = self._calculate_rsi_strategy_indicators(df)
            
            self.logger.debug(f"📊 기술적 지표 계산 완료: {len(df.columns)}개 지표")
            return df
            
        except Exception as e:
            self.logger.error(f"❌ 기술적 지표 계산 오류: {e}")
            return df
    
    def _calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 계산"""
        df['ema_5'] = df['close'].ewm(span=5).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_60'] = df['close'].ewm(span=60).mean()
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 계산"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD 계산"""
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """볼린저 밴드 계산"""
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        bb_std = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        return df
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """거래량 지표 계산"""
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['price_volume'] = df['close'] * df['volume']
        return df
    
    def _calculate_scalping_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """스캘핑 전용 지표"""
        # 단기 모멘텀
        df['momentum_3'] = (df['close'] / df['close'].shift(3) - 1) * 100
        
        # 거래량 급증 감지
        df['volume_spike'] = df['volume'] / df['volume'].rolling(window=5).mean()
        
        # 가격 변동성
        df['volatility'] = (df['high'] - df['low']) / df['close'] * 100
        
        return df
    
    def _calculate_rsi_strategy_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI 전략 전용 지표"""
        # RSI 다양한 기간
        for period in [7, 14, 21]:
            df[f'rsi_{period}'] = self._calculate_rsi_period(df, period)
        
        # RSI 과매수/과매도 신호
        df['rsi_oversold'] = df['rsi'] < 30
        df['rsi_overbought'] = df['rsi'] > 70
        
        return df
    
    def _calculate_rsi_period(self, df: pd.DataFrame, period: int) -> pd.Series:
        """특정 기간 RSI 계산"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def _generate_trading_signals(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        symbol: str,
        params: Optional[Dict] = None
    ) -> List[TradingSignal]:
        """매매 신호 생성"""
        try:
            signals = []
            
            if strategy_name == "scalping_3m":
                signals = await self._generate_scalping_signals(df, symbol, params)
            elif strategy_name == "rsi":
                signals = await self._generate_rsi_signals(df, symbol, params)
            
            self.logger.debug(f"📈 매매 신호 생성 완료: {len(signals)}개 신호")
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ 매매 신호 생성 오류: {e}")
            return []
    
    async def _generate_scalping_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        params: Optional[Dict] = None
    ) -> List[TradingSignal]:
        """3분봉 스캘핑 신호 생성 (매매조건.md 기준)"""
        signals = []
        
        # 기본 파라미터
        volume_threshold = params.get('volume_threshold', 2.0) if params else 2.0
        momentum_threshold = params.get('momentum_threshold', 1.0) if params else 1.0
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            # 매수 신호 - 매매조건.md 단기 기준
            buy_conditions = []
            
            # 1. 이평선 돌파 (5EMA > 20EMA)
            if row['ema_5'] > row['ema_20']:
                buy_conditions.append("5EMA > 20EMA 돌파")
            
            # 2. 거래량 동반한 양봉 발생
            if row['close'] > row['open'] and row['volume_ratio'] > volume_threshold:
                buy_conditions.append("거래량 동반 양봉")
            
            # 3. 단기 모멘텀 상승
            if row['momentum_3'] > momentum_threshold:
                buy_conditions.append("단기 모멘텀 상승")
            
            # 4. 볼린저 밴드 하단에서 반등
            if row['close'] > row['bb_lower'] and df.iloc[i-1]['close'] <= df.iloc[i-1]['bb_lower']:
                buy_conditions.append("볼린저 하단 반등")
            
            # 매수 신호 생성 (2개 이상 조건 만족)
            if len(buy_conditions) >= 2:
                signal = TradingSignal(
                    timestamp=row['timestamp'],
                    signal_type='BUY',
                    price=row['close'],
                    volume=row['volume'],
                    confidence=len(buy_conditions) / 4.0,
                    reasons=buy_conditions,
                    indicators={
                        'ema_5': row['ema_5'],
                        'ema_20': row['ema_20'],
                        'rsi': row['rsi'],
                        'volume_ratio': row['volume_ratio']
                    }
                )
                signals.append(signal)
            
            # 매도 신호 - 매매조건.md 단기 기준
            sell_conditions = []
            
            # 1. 5EMA 이탈 (분할 매도)
            if row['ema_5'] < row['ema_20'] and df.iloc[i-1]['ema_5'] >= df.iloc[i-1]['ema_20']:
                signal = TradingSignal(
                    timestamp=row['timestamp'],
                    signal_type='PARTIAL_SELL',
                    price=row['close'],
                    volume=row['volume'],
                    confidence=0.7,
                    reasons=["5EMA 이탈"],
                    indicators={'ema_5': row['ema_5'], 'ema_20': row['ema_20']},
                    partial_ratio=0.33  # 1/3 매도
                )
                signals.append(signal)
            
            # 2. 거래량 급감한 음봉 출현
            if row['close'] < row['open'] and row['volume_ratio'] < 0.5:
                sell_conditions.append("거래량 급감 음봉")
            
            # 3. 고점에서 거래량 없이 음봉
            if (row['close'] < row['open'] and 
                row['high'] == max(df.iloc[max(0, i-5):i+1]['high']) and 
                row['volume_ratio'] < 1.0):
                sell_conditions.append("고점 거래량 부족 음봉")
            
            # 전량 매도 신호
            if len(sell_conditions) >= 1:
                signal = TradingSignal(
                    timestamp=row['timestamp'],
                    signal_type='SELL',
                    price=row['close'],
                    volume=row['volume'],
                    confidence=len(sell_conditions) / 2.0,
                    reasons=sell_conditions,
                    indicators={
                        'volume_ratio': row['volume_ratio'],
                        'close': row['close'],
                        'open': row['open']
                    }
                )
                signals.append(signal)
        
        return signals
    
    async def _generate_rsi_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        params: Optional[Dict] = None
    ) -> List[TradingSignal]:
        """RSI 전략 신호 생성 (매매조건.md 기준)"""
        signals = []
        
        # 기본 파라미터
        rsi_oversold = params.get('rsi_oversold', 30) if params else 30
        rsi_overbought = params.get('rsi_overbought', 70) if params else 70
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # 매수 신호 - RSI 30 이하에서 반등
            if (prev_row['rsi'] <= rsi_oversold and row['rsi'] > rsi_oversold and
                row['close'] > row['open']):  # 양봉 확인
                
                buy_conditions = ["RSI 과매도 반등"]
                
                # 추가 확인 조건
                if row['macd'] > row['macd_signal']:
                    buy_conditions.append("MACD 골든크로스")
                
                if row['volume_ratio'] > 1.2:
                    buy_conditions.append("거래량 증가")
                
                signal = TradingSignal(
                    timestamp=row['timestamp'],
                    signal_type='BUY',
                    price=row['close'],
                    volume=row['volume'],
                    confidence=len(buy_conditions) / 3.0,
                    reasons=buy_conditions,
                    indicators={
                        'rsi': row['rsi'],
                        'macd': row['macd'],
                        'macd_signal': row['macd_signal'],
                        'volume_ratio': row['volume_ratio']
                    }
                )
                signals.append(signal)
            
            # 매도 신호 - RSI 70 이상에서 하락 반전
            if (prev_row['rsi'] >= rsi_overbought and row['rsi'] < rsi_overbought and
                row['close'] < row['open']):  # 음봉 확인
                
                sell_conditions = ["RSI 과매수 하락 반전"]
                
                # 추가 확인 조건
                if row['macd'] < row['macd_signal']:
                    sell_conditions.append("MACD 데드크로스")
                
                signal = TradingSignal(
                    timestamp=row['timestamp'],
                    signal_type='SELL',
                    price=row['close'],
                    volume=row['volume'],
                    confidence=len(sell_conditions) / 2.0,
                    reasons=sell_conditions,
                    indicators={
                        'rsi': row['rsi'],
                        'macd': row['macd'],
                        'macd_signal': row['macd_signal']
                    }
                )
                signals.append(signal)
        
        return signals
    
    async def _optimize_parameters(
        self,
        df: pd.DataFrame,
        signals: List[TradingSignal],
        strategy_name: str
    ) -> Dict[str, Any]:
        """파라미터 최적화"""
        try:
            self.logger.info(f"🎯 {strategy_name} 파라미터 최적화 시작...")
            
            best_params = {}
            best_score = -float('inf')
            
            if strategy_name == "scalping_3m":
                # 스캘핑 파라미터 최적화
                for volume_threshold in [1.5, 2.0, 2.5, 3.0]:
                    for momentum_threshold in [0.5, 1.0, 1.5, 2.0]:
                        params = {
                            'volume_threshold': volume_threshold,
                            'momentum_threshold': momentum_threshold
                        }
                        score = await self._evaluate_parameters(df, params, strategy_name)
                        
                        if score > best_score:
                            best_score = score
                            best_params = params
            
            elif strategy_name == "rsi":
                # RSI 파라미터 최적화
                for oversold in [25, 30, 35]:
                    for overbought in [65, 70, 75]:
                        params = {
                            'rsi_oversold': oversold,
                            'rsi_overbought': overbought
                        }
                        score = await self._evaluate_parameters(df, params, strategy_name)
                        
                        if score > best_score:
                            best_score = score
                            best_params = params
            
            self.logger.info(f"✅ 최적화 완료: 점수 {best_score:.4f}, 파라미터 {best_params}")
            return best_params
            
        except Exception as e:
            self.logger.error(f"❌ 파라미터 최적화 오류: {e}")
            return {}
    
    async def _evaluate_parameters(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
        strategy_name: str
    ) -> float:
        """파라미터 평가 점수 계산"""
        try:
            # 임시 신호 생성
            temp_signals = await self._generate_trading_signals(df, strategy_name, "TEST", params)
            
            # 간단한 백테스팅
            temp_trades = await self._execute_simple_backtest(df, temp_signals)
            
            # 평가 점수 계산 (수익률 * 승률)
            if not temp_trades:
                return 0
            
            total_return = sum(trade.profit_loss_pct for trade in temp_trades if trade.status == "CLOSED")
            win_rate = len([t for t in temp_trades if t.profit_loss > 0]) / len(temp_trades)
            
            # 위험 조정 수익률
            score = total_return * win_rate - (len(temp_trades) * 0.1)  # 거래 빈도 페널티
            
            return score
            
        except Exception as e:
            self.logger.error(f"❌ 파라미터 평가 오류: {e}")
            return 0
    
    async def _execute_simple_backtest(self, df: pd.DataFrame, signals: List[TradingSignal]) -> List[Trade]:
        """간단한 백테스팅 (최적화용)"""
        trades = []
        position = None
        
        for signal in signals:
            if signal.signal_type == 'BUY' and position is None:
                position = Trade(
                    symbol="TEST",
                    strategy="TEST",
                    entry_time=signal.timestamp,
                    entry_price=signal.price,
                    quantity=1000
                )
            
            elif signal.signal_type == 'SELL' and position is not None:
                position.exit_time = signal.timestamp
                position.exit_price = signal.price
                position.profit_loss_pct = (signal.price / position.entry_price - 1) * 100
                position.status = "CLOSED"
                trades.append(position)
                position = None
        
        return trades
    
    async def _execute_backtest(
        self,
        df: pd.DataFrame,
        signals: List[TradingSignal],
        symbol: str,
        strategy_name: str
    ) -> List[Trade]:
        """실제 백테스팅 실행"""
        try:
            trades = []
            current_position = None
            capital = self.initial_capital
            
            for signal in signals:
                
                if signal.signal_type == 'BUY' and current_position is None:
                    # 매수 진입
                    position_size = capital * 0.95  # 95% 투자
                    quantity = int(position_size / signal.price)
                    
                    if quantity > 0:
                        current_position = Trade(
                            symbol=symbol,
                            strategy=strategy_name,
                            entry_time=signal.timestamp,
                            entry_price=signal.price * (1 + self.slippage_rate),  # 슬리피지 적용
                            quantity=quantity,
                            status="OPEN"
                        )
                        
                        # 수수료 차감
                        commission = position_size * self.commission_rate
                        capital -= commission
                
                elif signal.signal_type == 'PARTIAL_SELL' and current_position is not None:
                    # 부분 매도
                    sell_quantity = int(current_position.quantity * signal.partial_ratio)
                    if sell_quantity > 0:
                        sell_price = signal.price * (1 - self.slippage_rate)
                        sell_amount = sell_quantity * sell_price
                        commission = sell_amount * self.commission_rate
                        
                        # 부분 매도 기록
                        partial_exit = {
                            'time': signal.timestamp,
                            'price': sell_price,
                            'quantity': sell_quantity,
                            'ratio': signal.partial_ratio
                        }
                        current_position.partial_exits.append(partial_exit)
                        current_position.quantity -= sell_quantity
                        
                        capital += sell_amount - commission
                
                elif signal.signal_type == 'SELL' and current_position is not None:
                    # 전량 매도
                    exit_price = signal.price * (1 - self.slippage_rate)
                    exit_amount = current_position.quantity * exit_price
                    commission = exit_amount * self.commission_rate
                    
                    # 거래 완료
                    current_position.exit_time = signal.timestamp
                    current_position.exit_price = exit_price
                    current_position.status = "CLOSED"
                    current_position.exit_reason = ", ".join(signal.reasons)
                    
                    # 손익 계산
                    total_cost = current_position.quantity * current_position.entry_price
                    current_position.profit_loss = exit_amount - total_cost - commission
                    current_position.profit_loss_pct = (current_position.profit_loss / total_cost) * 100
                    
                    capital += exit_amount - commission
                    trades.append(current_position)
                    current_position = None
            
            # 미청산 포지션 처리
            if current_position is not None:
                last_price = df.iloc[-1]['close']
                current_position.exit_time = df.iloc[-1]['timestamp']
                current_position.exit_price = last_price
                current_position.status = "CLOSED"
                current_position.exit_reason = "백테스팅 종료"
                
                exit_amount = current_position.quantity * last_price
                total_cost = current_position.quantity * current_position.entry_price
                current_position.profit_loss = exit_amount - total_cost
                current_position.profit_loss_pct = (current_position.profit_loss / total_cost) * 100
                
                trades.append(current_position)
            
            self.logger.info(f"📊 백테스팅 실행 완료: {len(trades)}건 거래")
            return trades
            
        except Exception as e:
            self.logger.error(f"❌ 백테스팅 실행 오류: {e}")
            return []
    
    async def _calculate_backtest_results(
        self,
        strategy_name: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        trades: List[Trade],
        df: pd.DataFrame
    ) -> BacktestResult:
        """백테스팅 결과 계산"""
        try:
            if not trades:
                return BacktestResult(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=self.initial_capital,
                    final_capital=self.initial_capital,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    profit_loss=0.0,
                    profit_loss_pct=0.0,
                    max_drawdown=0.0,
                    sharpe_ratio=0.0,
                    trades=[],
                    daily_returns=[],
                    metrics={}
                )
            
            # 기본 통계
            closed_trades = [t for t in trades if t.status == "CLOSED"]
            winning_trades = [t for t in closed_trades if t.profit_loss > 0]
            losing_trades = [t for t in closed_trades if t.profit_loss <= 0]
            
            total_profit_loss = sum(t.profit_loss for t in closed_trades)
            total_profit_loss_pct = (total_profit_loss / self.initial_capital) * 100
            win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
            
            # 최대 손실 계산
            max_drawdown = self._calculate_max_drawdown(closed_trades)
            
            # 샤프 비율 계산
            daily_returns = self._calculate_daily_returns(closed_trades, df)
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
            
            # 추가 지표
            avg_win = np.mean([t.profit_loss_pct for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t.profit_loss_pct for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(sum(t.profit_loss for t in winning_trades) / 
                               sum(t.profit_loss for t in losing_trades)) if losing_trades else float('inf')
            
            metrics = {
                'avg_win_pct': avg_win,
                'avg_loss_pct': avg_loss,
                'profit_factor': profit_factor,
                'total_days': (end_date - start_date).days,
                'trades_per_month': len(closed_trades) / max(1, (end_date - start_date).days / 30),
                'max_consecutive_losses': self._calculate_max_consecutive_losses(closed_trades)
            }
            
            return BacktestResult(
                strategy_name=strategy_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital + total_profit_loss,
                total_trades=len(closed_trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                win_rate=win_rate * 100,
                profit_loss=total_profit_loss,
                profit_loss_pct=total_profit_loss_pct,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                trades=trades,
                daily_returns=daily_returns,
                metrics=metrics
            )
            
        except Exception as e:
            self.logger.error(f"❌ 백테스팅 결과 계산 오류: {e}")
            raise
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """최대 손실폭 계산"""
        if not trades:
            return 0.0
        
        cumulative = 0
        peak = 0
        max_dd = 0
        
        for trade in trades:
            cumulative += trade.profit_loss
            if cumulative > peak:
                peak = cumulative
            drawdown = (peak - cumulative) / self.initial_capital * 100
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_daily_returns(self, trades: List[Trade], df: pd.DataFrame) -> List[float]:
        """일별 수익률 계산"""
        if not trades:
            return []
        
        # 간단한 구현: 거래별 수익률 반환
        return [trade.profit_loss_pct for trade in trades if trade.profit_loss_pct is not None]
    
    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """샤프 비율 계산"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0
        
        returns_array = np.array(daily_returns)
        return np.mean(returns_array) / np.std(returns_array) if np.std(returns_array) != 0 else 0.0
    
    def _calculate_max_consecutive_losses(self, trades: List[Trade]) -> int:
        """최대 연속 손실 계산"""
        if not trades:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in trades:
            if trade.profit_loss <= 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive