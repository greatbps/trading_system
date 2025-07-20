#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/models.py

데이터베이스 모델 정의
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Index, JSON, BigInteger, Numeric
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    """종목 정보 테이블"""
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    market = Column(String(20))  # KOSPI, KOSDAQ
    sector = Column(String(50))
    industry = Column(String(100))
    
    # 기본 정보
    current_price = Column(Float)
    market_cap = Column(BigInteger)  # 시가총액 (백만원)
    shares_outstanding = Column(BigInteger)  # 발행주식수
    
    # 52주 고저
    high_52w = Column(Float)
    low_52w = Column(Float)
    
    # 재무 지표
    pe_ratio = Column(Float)
    pbr = Column(Float)
    eps = Column(Float)
    bps = Column(Float)
    roe = Column(Float)
    debt_ratio = Column(Float)
    
    # 메타 정보
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    price_data = relationship("PriceData", back_populates="stock")
    analysis_results = relationship("AnalysisResult", back_populates="stock")
    trades = relationship("Trade", back_populates="stock")
    
    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', name='{self.name}')>"

class PriceData(Base):
    """가격 데이터 테이블"""
    __tablename__ = 'price_data'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    
    # 가격 정보
    date = Column(DateTime, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(BigInteger)
    trading_value = Column(BigInteger)  # 거래대금
    
    # 변화량
    change_amount = Column(Float)
    change_rate = Column(Float)
    
    # 기술적 지표 (계산된 값)
    ma_5 = Column(Float)
    ma_10 = Column(Float)
    ma_20 = Column(Float)
    ma_60 = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    bollinger_upper = Column(Float)
    bollinger_lower = Column(Float)
    
    created_at = Column(DateTime, default=func.now())
    
    # 관계
    stock = relationship("Stock", back_populates="price_data")
    
    # 인덱스
    __table_args__ = (
        Index('idx_stock_date', 'stock_id', 'date'),
        Index('idx_date', 'date'),
    )
    
    def __repr__(self):
        return f"<PriceData(stock_id={self.stock_id}, date='{self.date}', close={self.close_price})>"

class AnalysisResult(Base):
    """분석 결과 테이블"""
    __tablename__ = 'analysis_results'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    
    # 분석 기본 정보
    analysis_date = Column(DateTime, nullable=False, default=func.now())
    strategy = Column(String(50))  # momentum, breakout, etc.
    
    # 종합 점수
    comprehensive_score = Column(Float)
    recommendation = Column(String(20))  # BUY, SELL, HOLD 등
    confidence = Column(Float)
    
    # 세부 분석 점수
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    
    # 신호 정보
    signal_strength = Column(Float)
    signal_type = Column(String(20))
    action = Column(String(10))
    
    # 리스크 지표
    volatility = Column(Float)
    liquidity_risk = Column(Float)
    market_risk = Column(Float)
    risk_level = Column(String(10))  # LOW, MEDIUM, HIGH
    
    # 상세 분석 데이터 (JSON)
    technical_details = Column(JSON)
    fundamental_details = Column(JSON)
    sentiment_details = Column(JSON)
    
    # 가격 정보 (분석 당시)
    price_at_analysis = Column(Float)
    
    created_at = Column(DateTime, default=func.now())
    
    # 관계
    stock = relationship("Stock", back_populates="analysis_results")
    
    # 인덱스
    __table_args__ = (
        Index('idx_stock_analysis_date', 'stock_id', 'analysis_date'),
        Index('idx_analysis_date', 'analysis_date'),
        Index('idx_recommendation', 'recommendation'),
    )
    
    def __repr__(self):
        return f"<AnalysisResult(stock_id={self.stock_id}, score={self.comprehensive_score}, recommendation='{self.recommendation}')>"

class Trade(Base):
    """매매 기록 테이블"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    analysis_id = Column(Integer, ForeignKey('analysis_results.id'))
    
    # 매매 기본 정보
    trade_type = Column(String(10), nullable=False)  # BUY, SELL
    trade_date = Column(DateTime, nullable=False, default=func.now())
    
    # 가격 정보
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    commission = Column(Float, default=0)
    
    # 포지션 정보
    position_id = Column(String(50))  # 포지션 식별자
    
    # 손익 정보 (매도시)
    profit_loss = Column(Float)
    profit_loss_rate = Column(Float)
    
    # 주문 정보
    order_id = Column(String(100))  # 증권사 주문번호
    order_status = Column(String(20), default='PENDING')  # PENDING, FILLED, CANCELLED
    
    # 전략 정보
    strategy_name = Column(String(50))
    signal_strength = Column(Float)
    
    # 메타 정보
    is_simulated = Column(Boolean, default=False)  # 시뮬레이션 여부
    notes = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    stock = relationship("Stock", back_populates="trades")
    analysis_result = relationship("AnalysisResult")
    
    # 인덱스
    __table_args__ = (
        Index('idx_stock_trade_date', 'stock_id', 'trade_date'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_position_id', 'position_id'),
    )
    
    def __repr__(self):
        return f"<Trade(stock_id={self.stock_id}, type='{self.trade_type}', price={self.price}, quantity={self.quantity})>"

class Portfolio(Base):
    """포트폴리오 테이블"""
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    
    # 포지션 정보
    position_id = Column(String(50), unique=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # 현재 상태
    current_price = Column(Float)
    current_value = Column(Float)
    unrealized_pnl = Column(Float)
    unrealized_pnl_rate = Column(Float)
    
    # 매매 정보
    entry_date = Column(DateTime, nullable=False)
    entry_strategy = Column(String(50))
    entry_signal_strength = Column(Float)
    
    # 리스크 관리
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    
    # 상태
    status = Column(String(20), default='OPEN')  # OPEN, CLOSED
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    stock = relationship("Stock")
    
    # 인덱스
    __table_args__ = (
        Index('idx_position_id', 'position_id'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Portfolio(position_id='{self.position_id}', stock_id={self.stock_id}, quantity={self.quantity})>"

class NewsData(Base):
    """뉴스 데이터 테이블"""
    __tablename__ = 'news_data'
    
    id = Column(Integer, primary_key=True)
    
    # 뉴스 기본 정보
    title = Column(String(500), nullable=False)
    content = Column(Text)
    url = Column(String(1000))
    source = Column(String(100))
    published_at = Column(DateTime, nullable=False)
    
    # 관련 종목
    related_symbols = Column(JSON)  # 관련 종목 코드들
    
    # 감정 분석 결과
    sentiment_score = Column(Float)  # -1.0 ~ 1.0
    sentiment_label = Column(String(20))  # positive, negative, neutral
    confidence = Column(Float)
    
    # 키워드
    keywords = Column(JSON)
    categories = Column(JSON)
    
    # 영향도
    impact_score = Column(Float)  # 시장 영향도
    
    created_at = Column(DateTime, default=func.now())
    
    # 인덱스
    __table_args__ = (
        Index('idx_published_at', 'published_at'),
        Index('idx_sentiment_score', 'sentiment_score'),
    )
    
    def __repr__(self):
        return f"<NewsData(title='{self.title[:50]}...', sentiment={self.sentiment_label})>"

class SystemLog(Base):
    """시스템 로그 테이블"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    
    # 로그 정보
    timestamp = Column(DateTime, nullable=False, default=func.now())
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    module = Column(String(50))
    function = Column(String(50))
    message = Column(Text, nullable=False)
    
    # 추가 정보
    extra_data = Column(JSON)
    
    # 인덱스
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_level', 'level'),
    )
    
    def __repr__(self):
        return f"<SystemLog(level='{self.level}', module='{self.module}', message='{self.message[:50]}...')>"

class TradingSession(Base):
    """거래 세션 테이블"""
    __tablename__ = 'trading_sessions'
    
    id = Column(Integer, primary_key=True)
    
    # 세션 정보
    session_id = Column(String(100), unique=True, nullable=False)
    start_time = Column(DateTime, nullable=False, default=func.now())
    end_time = Column(DateTime)
    
    # 설정 정보
    strategy = Column(String(50))
    initial_capital = Column(Float)
    max_positions = Column(Integer)
    
    # 성과 정보
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)
    
    # 상태
    status = Column(String(20), default='ACTIVE')  # ACTIVE, COMPLETED, STOPPED
    
    # 메타 정보
    is_live_trading = Column(Boolean, default=False)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<TradingSession(session_id='{self.session_id}', strategy='{self.strategy}', status='{self.status}')>"