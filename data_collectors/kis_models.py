#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/kis_models.py

Enhanced data models for KIS API Collector

These models provide comprehensive data structures for all KIS API responses
with validation, serialization, and database integration capabilities.

Author: AI Trading System
Version: 2.0.0
Last Updated: 2025-01-04
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from decimal import Decimal
import json
import math


# Enums for type safety and validation
class Market(Enum):
    """Korean stock market classification"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"

class OrderType(Enum):
    """Order types supported by KIS API"""
    MARKET = "MARKET"      # 시장가
    LIMIT = "LIMIT"        # 지정가  
    STOP = "STOP"          # 손절가
    STOP_LIMIT = "STOP_LIMIT"  # 손절지정가

class TradeType(Enum):
    """Trade direction"""
    BUY = "BUY"           # 매수
    SELL = "SELL"         # 매도

class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "PENDING"         # 대기
    PARTIAL = "PARTIAL"         # 부분체결
    FILLED = "FILLED"           # 체결완료
    CANCELLED = "CANCELLED"     # 취소
    REJECTED = "REJECTED"       # 거부
    EXPIRED = "EXPIRED"         # 만료

class APIStatus(Enum):
    """API connection status"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"

class TimeFrame(Enum):
    """Chart data time frames"""
    MINUTE_1 = "1m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Base model with common functionality
@dataclass
class BaseKISModel:
    """Base class for all KIS data models"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for JSON serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, (list, tuple)):
                result[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item 
                    for item in value
                ]
            elif hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result
    
    def to_json(self) -> str:
        """Convert model to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model instance from dictionary"""
        # This would need specific implementation for each model
        # Based on the model's field types and validation requirements
        raise NotImplementedError("Subclasses must implement from_dict")


# Core stock data models
@dataclass
class StockData(BaseKISModel):
    """
    Comprehensive stock data model with validation
    
    Represents all essential information about a Korean stock
    including price, volume, financial metrics, and metadata.
    """
    symbol: str                    # 6-digit stock code
    name: str                      # Stock name (Korean)
    current_price: int             # Current price in KRW (no decimals)
    change_rate: float             # Daily change percentage
    volume: int                    # Trading volume
    trading_value: float           # Trading value in millions KRW
    market_cap: float              # Market cap in billions KRW
    market: Market                 # KOSPI/KOSDAQ/KONEX
    
    # Extended price data
    price_change: Optional[int] = None          # Price change in KRW
    high_price: Optional[int] = None            # Daily high
    low_price: Optional[int] = None             # Daily low
    open_price: Optional[int] = None            # Opening price
    prev_close_price: Optional[int] = None      # Previous close
    
    # 52-week range
    high_52w: Optional[int] = None              # 52-week high
    low_52w: Optional[int] = None               # 52-week low
    
    # Volume metrics
    volume_ratio: Optional[float] = None        # Volume vs average
    value_ratio: Optional[float] = None         # Trading value vs average
    
    # Financial ratios
    pe_ratio: Optional[float] = None            # Price-to-Earnings
    pbr: Optional[float] = None                 # Price-to-Book
    roe: Optional[float] = None                 # Return on Equity
    eps: Optional[int] = None                   # Earnings per Share (KRW)
    bps: Optional[int] = None                   # Book value per Share (KRW)
    
    # Market data
    shares_outstanding: Optional[int] = None     # Total shares
    foreign_ownership: Optional[float] = None    # Foreign ownership %
    institutional_ownership: Optional[float] = None  # Institutional ownership %
    
    # Classification
    sector: Optional[str] = "기타"              # Business sector
    industry: Optional[str] = None              # Industry classification
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    data_source: str = "KIS_API"
    api_response_time: Optional[float] = None    # Response time in seconds
    
    def __post_init__(self):
        """Validate data after initialization"""
        # Validate symbol format
        if not self.symbol or len(self.symbol) != 6 or not self.symbol.isdigit():
            raise ValueError(f"Invalid symbol format: {self.symbol}")
        
        # Validate price data
        if self.current_price <= 0:
            raise ValueError(f"Invalid current price: {self.current_price}")
        
        # Validate volume
        if self.volume < 0:
            raise ValueError(f"Invalid volume: {self.volume}")
        
        # Auto-calculate missing fields
        if not self.price_change and self.prev_close_price:
            self.price_change = self.current_price - self.prev_close_price
        
        # Set reasonable defaults for 52w range if missing
        if not self.high_52w:
            self.high_52w = int(self.current_price * 1.5)
        if not self.low_52w: 
            self.low_52w = int(self.current_price * 0.7)
    
    @property
    def change_percentage(self) -> float:
        """Get change percentage (alias for change_rate)"""
        return self.change_rate
    
    @property
    def market_value(self) -> float:
        """Get market capitalization in billions KRW"""
        return self.market_cap
    
    @property
    def is_kospi(self) -> bool:
        """Check if stock is listed on KOSPI"""
        return self.market == Market.KOSPI
    
    @property
    def is_kosdaq(self) -> bool:
        """Check if stock is listed on KOSDAQ"""
        return self.market == Market.KOSDAQ
    
    def calculate_position_size(self, portfolio_value: int, risk_percentage: float = 2.0) -> int:
        """
        Calculate position size based on portfolio value and risk
        
        Args:
            portfolio_value: Total portfolio value in KRW
            risk_percentage: Risk as percentage of portfolio
            
        Returns:
            Number of shares to buy
        """
        risk_amount = portfolio_value * (risk_percentage / 100)
        shares = int(risk_amount / self.current_price)
        return max(1, shares)  # At least 1 share
    
    def get_support_resistance_levels(self) -> Dict[str, int]:
        """Get basic support and resistance levels"""
        return {
            'support_1': int(self.current_price * 0.98),
            'support_2': int(self.current_price * 0.95),
            'resistance_1': int(self.current_price * 1.02),
            'resistance_2': int(self.current_price * 1.05),
            'stop_loss': int(self.current_price * 0.95),
            'take_profit': int(self.current_price * 1.10)
        }


@dataclass  
class OHLCVData(BaseKISModel):
    """
    OHLCV (Open, High, Low, Close, Volume) candlestick data
    
    Represents price and volume data for a specific time period.
    Used for technical analysis and charting.
    """
    symbol: str
    datetime: datetime
    timeframe: str              # e.g., "1d", "1h", "5m"
    open_price: int             # Opening price
    high_price: int             # Highest price
    low_price: int              # Lowest price  
    close_price: int            # Closing price
    volume: int                 # Trading volume
    
    # Additional data
    trade_amount: Optional[int] = None          # Trading amount in KRW
    trade_count: Optional[int] = None           # Number of trades
    vwap: Optional[float] = None                # Volume-weighted average price
    
    # Calculated fields
    price_range: Optional[int] = field(init=False, default=None)
    body_size: Optional[int] = field(init=False, default=None)
    upper_shadow: Optional[int] = field(init=False, default=None)
    lower_shadow: Optional[int] = field(init=False, default=None)
    
    def __post_init__(self):
        """Validate and calculate derived fields"""
        # Validate price data
        prices = [self.open_price, self.high_price, self.low_price, self.close_price]
        if not all(p > 0 for p in prices):
            raise ValueError("All prices must be positive")
        
        if self.high_price < self.low_price:
            raise ValueError("High price cannot be less than low price")
        
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        
        # Calculate derived fields
        self.price_range = self.high_price - self.low_price
        self.body_size = abs(self.close_price - self.open_price)
        self.upper_shadow = self.high_price - max(self.open_price, self.close_price)
        self.lower_shadow = min(self.open_price, self.close_price) - self.low_price
        
        # Calculate VWAP if trade_amount is available
        if self.trade_amount and self.volume > 0:
            self.vwap = self.trade_amount / self.volume
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)"""
        return self.close_price > self.open_price
    
    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)"""
        return self.close_price < self.open_price
    
    @property
    def is_doji(self) -> bool:
        """Check if candle is a doji (open ≈ close)"""
        return self.body_size <= (self.price_range * 0.1)
    
    @property
    def change_percentage(self) -> float:
        """Get percentage change for this period"""
        if self.open_price == 0:
            return 0.0
        return ((self.close_price - self.open_price) / self.open_price) * 100


@dataclass
class AccountInfo(BaseKISModel):
    """
    Account balance and position information
    
    Represents the current state of a trading account including
    cash balance, positions, and profit/loss information.
    """
    account_number: str                    # Masked account number for security
    account_name: Optional[str] = None     # Account name/description
    
    # Cash balances (all in KRW)
    cash_balance: int = 0                  # Available cash
    total_assets: int = 0                  # Total account value
    stock_value: int = 0                   # Current stock holdings value
    available_cash: int = 0                # Available for trading
    
    # Profit/Loss tracking
    daily_pnl: int = 0                     # Daily profit/loss
    total_pnl: int = 0                     # Total profit/loss
    realized_pnl: int = 0                  # Realized profit/loss
    unrealized_pnl: int = 0                # Unrealized profit/loss
    
    # Trading limits and margins
    buying_power: int = 0                  # Maximum buying power
    margin_balance: int = 0                # Margin balance
    loan_amount: int = 0                   # Outstanding loans
    
    # Account status
    account_type: str = "CASH"             # CASH, MARGIN, etc.
    is_active: bool = True                 # Account active status
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def total_equity(self) -> int:
        """Calculate total equity (assets - loans)"""
        return self.total_assets - self.loan_amount
    
    @property
    def cash_ratio(self) -> float:
        """Get cash as percentage of total assets"""
        if self.total_assets == 0:
            return 0.0
        return (self.cash_balance / self.total_assets) * 100
    
    @property
    def daily_return_percentage(self) -> float:
        """Get daily return as percentage"""
        if self.total_assets == 0:
            return 0.0
        return (self.daily_pnl / (self.total_assets - self.daily_pnl)) * 100
    
    def can_buy(self, stock_price: int, quantity: int) -> bool:
        """Check if account has sufficient funds for purchase"""
        required_amount = stock_price * quantity
        return self.available_cash >= required_amount


@dataclass
class OrderRequest(BaseKISModel):
    """
    Trading order request data structure
    
    Represents a request to place a trading order with all
    necessary parameters and validation.
    """
    symbol: str                            # 6-digit stock code
    order_type: OrderType                  # MARKET, LIMIT, etc.
    trade_type: TradeType                  # BUY or SELL
    quantity: int                          # Number of shares
    
    # Price information (None for market orders)
    price: Optional[int] = None            # Order price
    stop_price: Optional[int] = None       # Stop price for stop orders
    
    # Order conditions
    condition: Optional[str] = None        # Special conditions
    validity: str = "DAY"                  # Order validity (DAY, GTC, etc.)
    
    # Metadata
    client_order_id: Optional[str] = None  # Client-side order ID
    order_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate order parameters"""
        # Validate symbol
        if not self.symbol or len(self.symbol) != 6 or not self.symbol.isdigit():
            raise ValueError(f"Invalid symbol: {self.symbol}")
        
        # Validate quantity
        if self.quantity <= 0:
            raise ValueError(f"Invalid quantity: {self.quantity}")
        
        # Validate price for limit orders
        if self.order_type == OrderType.LIMIT and (not self.price or self.price <= 0):
            raise ValueError("Limit orders require a valid price")
        
        # Validate stop price for stop orders
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and (not self.stop_price or self.stop_price <= 0):
            raise ValueError("Stop orders require a valid stop price")
    
    @property
    def estimated_value(self) -> Optional[int]:
        """Get estimated order value"""
        if self.price:
            return self.price * self.quantity
        return None
    
    @property
    def is_market_order(self) -> bool:
        """Check if this is a market order"""
        return self.order_type == OrderType.MARKET
    
    @property
    def is_buy_order(self) -> bool:
        """Check if this is a buy order"""
        return self.trade_type == TradeType.BUY


@dataclass
class OrderResponse(BaseKISModel):
    """
    Order response from KIS API
    
    Represents the response received after placing an order,
    including order ID, status, and any error messages.
    """
    order_id: str                          # KIS order ID
    client_order_id: Optional[str] = None  # Client order ID
    symbol: str = ""                       # Stock symbol
    status: OrderStatus = OrderStatus.PENDING  # Order status
    message: str = ""                      # Status message
    
    # Order details
    order_type: Optional[OrderType] = None
    trade_type: Optional[TradeType] = None
    quantity: Optional[int] = None
    price: Optional[int] = None
    
    # Execution details
    executed_quantity: int = 0             # Shares executed
    executed_price: Optional[int] = None   # Average execution price
    remaining_quantity: Optional[int] = None
    
    # Timestamps
    order_time: Optional[datetime] = None   # When order was placed
    execution_time: Optional[datetime] = None  # When order was executed
    timestamp: datetime = field(default_factory=datetime.now)  # Response time
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if order was successfully placed"""
        return self.status not in [OrderStatus.REJECTED] and not self.error_code
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partial(self) -> bool:
        """Check if order is partially filled"""
        return self.status == OrderStatus.PARTIAL
    
    @property
    def execution_value(self) -> Optional[int]:
        """Get total execution value"""
        if self.executed_price and self.executed_quantity:
            return self.executed_price * self.executed_quantity
        return None


@dataclass
class HTSCondition(BaseKISModel):
    """
    HTS (Home Trading System) conditional search condition
    
    Represents a pre-saved condition in the KIS HTS system
    that can be used to filter stocks based on technical or
    fundamental criteria.
    """
    condition_id: str                      # Condition ID (usually numeric)
    condition_name: str                    # Human-readable name
    description: Optional[str] = None      # Condition description
    
    # Condition metadata
    condition_type: Optional[str] = None   # Type of condition
    parameters: Optional[Dict[str, Any]] = None  # Condition parameters
    created_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    
    # Results tracking
    last_result_count: Optional[int] = None
    average_result_count: Optional[float] = None
    
    def __post_init__(self):
        """Validate condition data"""
        if not self.condition_id:
            raise ValueError("Condition ID is required")
        if not self.condition_name:
            raise ValueError("Condition name is required")


@dataclass
class MarketDepth(BaseKISModel):
    """
    Market depth (order book) data
    
    Represents the current bid/ask orders for a stock,
    showing price levels and quantities available.
    """
    symbol: str
    current_price: int
    
    # Bid side (buy orders)
    bid_prices: List[int] = field(default_factory=list)
    bid_volumes: List[int] = field(default_factory=list)
    
    # Ask side (sell orders)  
    ask_prices: List[int] = field(default_factory=list)
    ask_volumes: List[int] = field(default_factory=list)
    
    # Market statistics
    total_bid_volume: Optional[int] = None
    total_ask_volume: Optional[int] = None
    spread: Optional[int] = None           # Bid-ask spread
    spread_percentage: Optional[float] = None
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Calculate derived fields"""
        if self.bid_prices and self.ask_prices:
            # Calculate spread
            best_bid = max(self.bid_prices) if self.bid_prices else 0
            best_ask = min(self.ask_prices) if self.ask_prices else 0
            
            if best_bid > 0 and best_ask > 0:
                self.spread = best_ask - best_bid
                self.spread_percentage = (self.spread / best_bid) * 100
        
        # Calculate total volumes
        self.total_bid_volume = sum(self.bid_volumes)
        self.total_ask_volume = sum(self.ask_volumes)
    
    @property
    def best_bid(self) -> Optional[int]:
        """Get best bid price"""
        return max(self.bid_prices) if self.bid_prices else None
    
    @property
    def best_ask(self) -> Optional[int]:
        """Get best ask price"""
        return min(self.ask_prices) if self.ask_prices else None
    
    @property
    def mid_price(self) -> Optional[float]:
        """Get mid price between best bid and ask"""
        best_bid = self.best_bid
        best_ask = self.best_ask
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None


@dataclass
class TechnicalIndicators(BaseKISModel):
    """
    Technical analysis indicators for a stock
    
    Contains commonly used technical indicators calculated
    from price and volume data.
    """
    symbol: str
    timeframe: str
    calculation_date: datetime = field(default_factory=datetime.now)
    
    # Price-based indicators
    sma_20: Optional[float] = None         # 20-period Simple Moving Average
    sma_50: Optional[float] = None         # 50-period Simple Moving Average  
    ema_12: Optional[float] = None         # 12-period Exponential Moving Average
    ema_26: Optional[float] = None         # 26-period Exponential Moving Average
    
    # Momentum indicators
    rsi_14: Optional[float] = None         # 14-period RSI
    macd: Optional[float] = None           # MACD line
    macd_signal: Optional[float] = None    # MACD signal line
    macd_histogram: Optional[float] = None # MACD histogram
    
    # Volatility indicators
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    
    # Volume indicators
    volume_sma_20: Optional[float] = None   # Volume moving average
    volume_ratio: Optional[float] = None    # Current vs average volume
    
    # Support/Resistance levels
    support_levels: List[int] = field(default_factory=list)
    resistance_levels: List[int] = field(default_factory=list)
    
    # Trend indicators
    trend_direction: Optional[str] = None   # UP, DOWN, SIDEWAYS
    trend_strength: Optional[float] = None  # 0.0 to 1.0
    
    @property
    def is_oversold(self) -> bool:
        """Check if RSI indicates oversold condition"""
        return self.rsi_14 is not None and self.rsi_14 < 30
    
    @property
    def is_overbought(self) -> bool:
        """Check if RSI indicates overbought condition"""
        return self.rsi_14 is not None and self.rsi_14 > 70
    
    @property
    def macd_bullish_crossover(self) -> bool:
        """Check if MACD shows bullish crossover"""
        return (self.macd is not None and self.macd_signal is not None and 
                self.macd > self.macd_signal and self.macd_histogram is not None and 
                self.macd_histogram > 0)


@dataclass
class PerformanceMetrics(BaseKISModel):
    """
    Performance metrics for the KIS collector
    
    Tracks API performance, reliability, and usage statistics.
    """
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Timing metrics
    average_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    
    # Rate limiting
    rate_limit_hits: int = 0
    rate_limit_wait_time: float = 0.0
    
    # Error tracking
    authentication_errors: int = 0
    network_errors: int = 0
    server_errors: int = 0
    validation_errors: int = 0
    
    # Circuit breaker
    circuit_breaker_opens: int = 0
    circuit_breaker_state: str = "CLOSED"
    
    # Cache performance
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Timestamps
    start_time: datetime = field(default_factory=datetime.now)
    last_request_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage"""
        return 100.0 - self.success_rate
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100
    
    @property
    def uptime(self) -> timedelta:
        """Calculate uptime since start"""
        return datetime.now() - self.start_time
    
    @property
    def requests_per_minute(self) -> float:
        """Calculate average requests per minute"""
        uptime_minutes = self.uptime.total_seconds() / 60
        if uptime_minutes == 0:
            return 0.0
        return self.total_requests / uptime_minutes


# Utility functions for model operations
def validate_korean_symbol(symbol: str) -> bool:
    """
    Validate Korean stock symbol format
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        True if valid, False otherwise
    """
    return (isinstance(symbol, str) and 
            len(symbol) == 6 and 
            symbol.isdigit())


def parse_kis_datetime(date_str: str, time_str: Optional[str] = None) -> datetime:
    """
    Parse KIS API date/time strings to datetime object
    
    Args:
        date_str: Date string in YYYYMMDD format
        time_str: Optional time string in HHMMSS format
        
    Returns:
        Parsed datetime object
    """
    if len(date_str) == 8:
        date_part = datetime.strptime(date_str, "%Y%m%d")
    else:
        raise ValueError(f"Invalid date format: {date_str}")
    
    if time_str and len(time_str) == 6:
        time_part = datetime.strptime(time_str, "%H%M%S").time()
        return datetime.combine(date_part.date(), time_part)
    
    return date_part


def calculate_portfolio_metrics(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate portfolio-level metrics from individual positions
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        Dictionary of portfolio metrics
    """
    if not positions:
        return {}
    
    total_value = sum(pos.get('market_value', 0) for pos in positions)
    total_cost = sum(pos.get('cost_basis', 0) for pos in positions)
    total_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_pnl': total_pnl,
        'total_return_pct': (total_pnl / total_cost * 100) if total_cost > 0 else 0.0,
        'position_count': len(positions),
        'largest_position_pct': max((pos.get('market_value', 0) / total_value * 100) 
                                  for pos in positions) if total_value > 0 else 0.0
    }


# Model factory functions
def create_stock_data_from_kis_response(response: Dict[str, Any]) -> StockData:
    """
    Create StockData model from KIS API response
    
    Args:
        response: Raw KIS API response
        
    Returns:
        StockData instance
    """
    output = response.get('output', {})
    
    # Extract basic data
    symbol = output.get('stck_cd', '').strip()
    if not validate_korean_symbol(symbol):
        raise ValueError(f"Invalid symbol in response: {symbol}")
    
    return StockData(
        symbol=symbol,
        name=output.get('hts_kor_isnm', '').strip() or f'종목{symbol}',
        current_price=int(output.get('stck_prpr', 0)),
        change_rate=float(output.get('prdy_ctrt', 0)),
        volume=int(output.get('acml_vol', 0)),
        trading_value=float(output.get('acml_tr_pbmn', 0)) / 1000000,
        market_cap=float(output.get('hts_avls', 0)) / 100,
        market=Market.KOSPI if output.get('mrkt_div_cd') == 'J' else Market.KOSDAQ,
        
        # Additional fields
        price_change=int(output.get('prdy_vrss', 0)),
        high_price=int(output.get('stck_hgpr', 0)),
        low_price=int(output.get('stck_lwpr', 0)),
        open_price=int(output.get('stck_oprc', 0)),
        high_52w=int(output.get('w52_hgpr', 0)) or None,
        low_52w=int(output.get('w52_lwpr', 0)) or None,
        pe_ratio=float(output.get('per', 0)) or None,
        pbr=float(output.get('pbr', 0)) or None,
        
        # Metadata
        last_updated=datetime.now(),
        data_source="KIS_API"
    )


def create_ohlcv_from_kis_response(symbol: str, response: Dict[str, Any], timeframe: str = "1d") -> List[OHLCVData]:
    """
    Create OHLCV data list from KIS API response
    
    Args:
        symbol: Stock symbol
        response: Raw KIS API response
        timeframe: Chart timeframe
        
    Returns:
        List of OHLCVData instances
    """
    output2 = response.get('output2', [])
    ohlcv_list = []
    
    for item in output2:
        try:
            date_str = item.get('stck_bsop_date', '')
            if not date_str or len(date_str) != 8:
                continue
            
            dt = parse_kis_datetime(date_str)
            
            ohlcv = OHLCVData(
                symbol=symbol,
                datetime=dt,
                timeframe=timeframe,
                open_price=int(item.get('stck_oprc', 0)),
                high_price=int(item.get('stck_hgpr', 0)),
                low_price=int(item.get('stck_lwpr', 0)),
                close_price=int(item.get('stck_clpr', 0)),
                volume=int(item.get('acml_vol', 0)),
                trade_amount=int(item.get('acml_tr_pbmn', 0)) if item.get('acml_tr_pbmn') else None
            )
            
            ohlcv_list.append(ohlcv)
            
        except (ValueError, TypeError) as e:
            # Skip invalid data items
            continue
    
    return sorted(ohlcv_list, key=lambda x: x.datetime)