#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/models.py

SQLAlchemy 데이터베이스 모델 정의
AI 주식 트레이딩 시스템용 완전한 데이터베이스 모델
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any, Dict

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Boolean, Text,
    ForeignKey, Index, JSON, BigInteger, Numeric, Enum, DECIMAL,
    UniqueConstraint, CheckConstraint, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session, validates
from sqlalchemy.sql import func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Base 클래스 정의
Base = declarative_base()

# 상태 열거형 정의
class TradeType(enum.Enum):
    """거래 유형"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(enum.Enum):
    """주문 상태"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class OrderType(enum.Enum):
    """주문 유형"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class PortfolioStatus(enum.Enum):
    """포트폴리오 상태"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CLOSING = "CLOSING"

class AnalysisGrade(enum.Enum):
    """분석 등급"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class RiskLevel(enum.Enum):
    """리스크 레벨"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class LogLevel(enum.Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Market(enum.Enum):
    """시장 구분"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"

class SessionStatus(enum.Enum):
    """세션 상태"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"

# 기본 모델 클래스
class BaseModel(Base):
    """모든 모델의 기본 클래스"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """모델을 딕셔너리로 변환"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, enum.Enum):
                result[column.name] = value.value
            elif isinstance(value, Decimal):
                result[column.name] = float(value)
            else:
                result[column.name] = value
        return result
    
    @classmethod
    def get_by_id(cls, session: Session, id: int):
        """ID로 레코드 조회"""
        return session.query(cls).filter(cls.id == id).first()
    
    def save(self, session: Session) -> 'BaseModel':
        """레코드 저장"""
        try:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self
        except Exception as e:
            session.rollback()
            raise e
    
    def delete(self, session: Session) -> bool:
        """레코드 삭제"""
        try:
            session.delete(self)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e

class Stock(BaseModel):
    """종목 기본 정보 테이블"""
    __tablename__ = 'stocks'
    
    # 기본 정보
    symbol = Column(String(10), unique=True, nullable=False, index=True, comment="종목코드 (6자리)")
    name = Column(String(100), nullable=False, comment="종목명")
    market = Column(Enum(Market), nullable=False, index=True, comment="시장구분")
    sector = Column(String(50), comment="업종")
    industry = Column(String(100), comment="산업")
    
    # 가격 정보 (한국 원화 - 정수)
    current_price = Column(Integer, comment="현재가")
    market_cap = Column(BigInteger, comment="시가총액 (원)")
    shares_outstanding = Column(BigInteger, comment="발행주식수")
    
    # 52주 고저
    high_52w = Column(Integer, comment="52주 최고가")
    low_52w = Column(Integer, comment="52주 최저가")
    
    # 재무 지표
    pe_ratio = Column(DECIMAL(10, 2), comment="PER")
    pbr = Column(DECIMAL(10, 2), comment="PBR")
    eps = Column(Integer, comment="주당순이익")
    bps = Column(Integer, comment="주당순자산")
    roe = Column(DECIMAL(5, 2), comment="ROE (%)")
    debt_ratio = Column(DECIMAL(5, 2), comment="부채비율 (%)")
    
    # 메타 정보
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="활성 상태")
    
    # 관계
    filtered_stocks = relationship("FilteredStock", back_populates="stock", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="stock", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="stock")
    portfolio_positions = relationship("Portfolio", back_populates="stock")
    market_data = relationship("MarketData", back_populates="stock", cascade="all, delete-orphan")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('LENGTH(symbol) = 6', name='check_symbol_length'),
        CheckConstraint('current_price IS NULL OR current_price > 0', name='check_current_price_positive'),
        CheckConstraint('market_cap IS NULL OR market_cap > 0', name='check_market_cap_positive'),
        Index('idx_stock_symbol', 'symbol'),
        Index('idx_stock_market', 'market'),
        Index('idx_stock_active', 'is_active'),
    )
    
    @validates('symbol')
    def validate_symbol(self, key, symbol):
        """종목코드 유효성 검사"""
        if symbol and (len(symbol) != 6 or not symbol.isdigit()):
            raise ValueError(f"Invalid stock symbol: {symbol}. Must be 6 digits.")
        return symbol
    
    @validates('current_price', 'market_cap')
    def validate_positive_values(self, key, value):
        """양수 값 검사"""
        if value is not None and value <= 0:
            raise ValueError(f"{key} must be positive, got {value}")
        return value
    
    @classmethod
    def get_by_symbol(cls, session: Session, symbol: str) -> Optional['Stock']:
        """종목코드로 조회"""
        return session.query(cls).filter(cls.symbol == symbol).first()
    
    @classmethod
    def get_active_stocks(cls, session: Session, market: Optional[Market] = None) -> List['Stock']:
        """활성 상태 종목 조회"""
        query = session.query(cls).filter(cls.is_active == True)
        if market:
            query = query.filter(cls.market == market)
        return query.all()
    
    def get_latest_price(self, session: Session) -> Optional[int]:
        """최신 가격 조회"""
        latest_data = session.query(MarketData).filter(
            MarketData.stock_id == self.id,
            MarketData.timeframe == '1d'
        ).order_by(MarketData.datetime.desc()).first()
        return latest_data.close_price if latest_data else self.current_price
    
    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', name='{self.name}', market='{self.market.value if self.market else None}')>"

class FilteredStock(BaseModel):
    """1차 필터링 결과 테이블 (HTS 조건검색 결과)"""
    __tablename__ = 'filtered_stocks'
    
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    strategy_name = Column(String(50), nullable=False, index=True, comment="사용된 전략명")
    filtered_date = Column(DateTime, nullable=False, index=True, comment="필터링 날짜")
    hts_condition_name = Column(String(100), comment="HTS 조건명")
    
    # 필터링 당시 가격 정보
    current_price = Column(Integer, comment="현재가")
    price_change = Column(Integer, comment="전일대비")
    price_change_rate = Column(DECIMAL(5, 2), comment="등락률 (%)")
    volume = Column(BigInteger, comment="거래량")
    
    # 관계
    stock = relationship("Stock", back_populates="filtered_stocks")
    analysis_result = relationship("AnalysisResult", back_populates="filtered_stock", uselist=False, cascade="all, delete-orphan")
    
    # 제약 조건
    __table_args__ = (
        UniqueConstraint('stock_id', 'strategy_name', 'filtered_date', name='uq_filtered_stock_date'),
        CheckConstraint('current_price IS NULL OR current_price > 0', name='check_filtered_current_price_positive'),
        Index('idx_filtered_stocks_date', 'filtered_date'),
        Index('idx_filtered_stocks_strategy', 'strategy_name'),
    )
    
    @classmethod
    def get_by_strategy_date(cls, session: Session, strategy_name: str, filtered_date: datetime) -> List['FilteredStock']:
        """전략별 날짜별 필터링 결과 조회"""
        from datetime import timedelta
        return session.query(cls).filter(
            cls.strategy_name == strategy_name,
            cls.filtered_date >= filtered_date.date(),
            cls.filtered_date < (filtered_date.date() + timedelta(days=1))
        ).all()
    
    @classmethod
    def get_recent_filtered(cls, session: Session, days: int = 7) -> List['FilteredStock']:
        """최근 N일 필터링 결과 조회"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        return session.query(cls).filter(cls.filtered_date >= cutoff_date).all()
    
    def __repr__(self):
        return f"<FilteredStock(stock_id={self.stock_id}, strategy='{self.strategy_name}', date='{self.filtered_date}')>"

class MarketData(BaseModel):
    """시장 데이터 테이블 (OHLCV 차트 데이터)"""
    __tablename__ = 'market_data'
    
    stock_id = Column(Integer, ForeignKey('stocks.id', ondelete='CASCADE'), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True, comment="종목코드 (편의상 중복)")
    timeframe = Column(String(10), nullable=False, index=True, comment="시간프레임 (1m, 3m, 5m, 15m, 1h, 1d)")
    
    # OHLCV 데이터 (한국 원화 - 정수)
    open_price = Column(Integer, nullable=False, comment="시가")
    high_price = Column(Integer, nullable=False, comment="고가")
    low_price = Column(Integer, nullable=False, comment="저가")
    close_price = Column(Integer, nullable=False, comment="종가")
    volume = Column(BigInteger, nullable=False, comment="거래량")
    trade_amount = Column(BigInteger, comment="거래대금")
    
    # 시간 정보
    datetime = Column(DateTime, nullable=False, index=True, comment="데이터 시간")
    
    # 관계
    stock = relationship("Stock", back_populates="market_data")
    
    # 제약 조건
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'datetime', name='uq_market_data_symbol_time'),
        CheckConstraint('open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0', name='check_prices_positive'),
        CheckConstraint('volume >= 0', name='check_volume_non_negative'),
        CheckConstraint('high_price >= low_price', name='check_high_low_relationship'),
        Index('idx_market_data_symbol_timeframe_datetime', 'symbol', 'timeframe', 'datetime'),
        Index('idx_market_data_datetime', 'datetime'),
    )
    
    @classmethod
    def get_latest_data(cls, session: Session, symbol: str, timeframe: str = '1d') -> Optional['MarketData']:
        """최신 시장 데이터 조회"""
        return session.query(cls).filter(
            cls.symbol == symbol,
            cls.timeframe == timeframe
        ).order_by(cls.datetime.desc()).first()
    
    @classmethod
    def get_ohlcv_data(cls, session: Session, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> List['MarketData']:
        """기간별 OHLCV 데이터 조회"""
        return session.query(cls).filter(
            cls.symbol == symbol,
            cls.timeframe == timeframe,
            cls.datetime >= start_date,
            cls.datetime <= end_date
        ).order_by(cls.datetime.asc()).all()
    
    def __repr__(self):
        return f"<MarketData(symbol='{self.symbol}', timeframe='{self.timeframe}', datetime='{self.datetime}', close={self.close_price})>"

class AnalysisResult(BaseModel):
    """2차 필터링 (정량적 분석) 결과 테이블"""
    __tablename__ = 'analysis_results'
    
    filtered_stock_id = Column(Integer, ForeignKey('filtered_stocks.id', ondelete='CASCADE'), 
                              unique=True, nullable=False, index=True, comment="1:1 관계")
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    
    # 분석 기본 정보
    analysis_datetime = Column(DateTime, nullable=False, default=func.now(), index=True, comment="분석 실행 시간")
    strategy = Column(String(50), comment="사용된 전략")
    
    # 종합 점수 (0-100)
    total_score = Column(DECIMAL(5, 2), comment="종합 점수 (0-100)")
    score_threshold = Column(DECIMAL(5, 2), default=60.0, comment="통과 기준점")
    final_grade = Column(Enum(AnalysisGrade), comment="최종 등급")
    
    # 세부 분석 점수
    news_score = Column(DECIMAL(5, 2), default=0, comment="뉴스 점수 (-50 ~ +50)")
    technical_score = Column(DECIMAL(5, 2), default=0, comment="기술적 분석 점수 (0-50)")
    supply_demand_score = Column(DECIMAL(5, 2), default=0, comment="수급 점수 (0-50)")
    
    # 기술적 분석 상세
    rsi_14 = Column(DECIMAL(5, 2), comment="RSI(14)")
    macd_signal = Column(String(10), comment="MACD 신호 (BUY/SELL/HOLD)")
    supertrend_signal = Column(String(10), comment="Supertrend 신호")
    ema_5 = Column(Integer, comment="5일 지수이동평균")
    ema_20 = Column(Integer, comment="20일 지수이동평균")
    bollinger_position = Column(String(10), comment="볼린저밴드 위치 (UPPER/MIDDLE/LOWER)")
    
    # 뉴스 분석 상세
    positive_news_count = Column(Integer, default=0, comment="긍정 뉴스 개수")
    negative_news_count = Column(Integer, default=0, comment="부정 뉴스 개수")
    news_keywords = Column(JSON, comment="주요 키워드")
    
    # 수급 분석 상세  
    institution_net = Column(BigInteger, default=0, comment="기관 순매수")
    foreign_net = Column(BigInteger, default=0, comment="외국인 순매수")
    individual_net = Column(BigInteger, default=0, comment="개인 순매수")
    
    # 리스크 지표
    volatility = Column(DECIMAL(5, 2), comment="변동성")
    liquidity_risk = Column(DECIMAL(5, 2), comment="유동성 위험")
    market_risk = Column(DECIMAL(5, 2), comment="시장 위험")
    risk_level = Column(Enum(RiskLevel), comment="위험 수준")
    
    # 상세 분석 데이터 (JSON)
    technical_details = Column(JSON, comment="기술적 분석 상세")
    fundamental_details = Column(JSON, comment="기본 분석 상세")
    sentiment_details = Column(JSON, comment="감정 분석 상세")
    
    # 가격 정보 (분석 당시)
    price_at_analysis = Column(Integer, comment="분석 당시 가격")
    is_selected = Column(Boolean, default=False, nullable=False, index=True, comment="최종 선정 여부")
    
    # 관계
    stock = relationship("Stock", back_populates="analysis_results")
    filtered_stock = relationship("FilteredStock", back_populates="analysis_result")
    trades = relationship("Trade", back_populates="analysis_result")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('total_score >= 0 AND total_score <= 100', name='check_total_score_range'),
        CheckConstraint('news_score >= -50 AND news_score <= 50', name='check_news_score_range'),
        CheckConstraint('technical_score >= 0 AND technical_score <= 50', name='check_technical_score_range'),
        CheckConstraint('supply_demand_score >= 0 AND supply_demand_score <= 50', name='check_supply_demand_score_range'),
        CheckConstraint('rsi_14 IS NULL OR (rsi_14 >= 0 AND rsi_14 <= 100)', name='check_rsi_range'),
        Index('idx_analysis_filtered_stock_id', 'filtered_stock_id'),
        Index('idx_analysis_datetime', 'analysis_datetime'),
        Index('idx_total_score', 'total_score'),
        Index('idx_final_grade', 'final_grade'),
        Index('idx_is_selected', 'is_selected'),
    )
    
    @validates('total_score')
    def validate_total_score(self, key, score):
        """종합 점수 유효성 검사"""
        if score is not None and (score < 0 or score > 100):
            raise ValueError(f"Total score must be between 0 and 100, got {score}")
        return score
    
    @classmethod
    def get_selected_stocks(cls, session: Session, analysis_date: datetime = None) -> List['AnalysisResult']:
        """선정된 종목들 조회"""
        query = session.query(cls).filter(cls.is_selected == True)
        if analysis_date:
            query = query.filter(cls.analysis_datetime >= analysis_date.date())
        return query.order_by(cls.total_score.desc()).all()
    
    @classmethod
    def get_by_score_range(cls, session: Session, min_score: float, max_score: float = 100) -> List['AnalysisResult']:
        """점수 범위로 조회"""
        return session.query(cls).filter(
            cls.total_score >= min_score,
            cls.total_score <= max_score
        ).order_by(cls.total_score.desc()).all()
    
    def __repr__(self):
        return f"<AnalysisResult(stock_id={self.stock_id}, total_score={self.total_score}, grade='{self.final_grade.value if self.final_grade else None}')>"

class Order(Base):
    """주문 정보 테이블"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    filtered_stock_id = Column(Integer, ForeignKey('filtered_stocks.id'), nullable=True) # 어떤 필터링 결과로 주문이 발생했는지 연결
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    analysis_id = Column(Integer, ForeignKey('analysis_results.id'), nullable=True)
    
    # 주문 기본 정보
    order_type = Column(String(10), nullable=False)  # BUY, SELL
    order_datetime = Column(DateTime, nullable=False, default=func.now())
    
    # 가격 정보
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    
    # 증권사 주문 정보
    kis_order_id = Column(String(100))  # KIS API가 반환한 주문 ID
    status = Column(String(20), default='PENDING')  # PENDING, FILLED, CANCELED, FAILED
    
    # 전략 정보
    strategy_name = Column(String(50))
    signal_strength = Column(Float)
    
    # 메타 정보
    is_simulated = Column(Boolean, default=False)  # 시뮬레이션 여부
    notes = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 관계
    stock = relationship("Stock")
    filtered_stock = relationship("FilteredStock", back_populates="orders")
    analysis_result = relationship("AnalysisResult", back_populates="orders")
    trade_executions = relationship("TradeExecution", back_populates="order", cascade="all, delete-orphan")
    
    # 인덱스
    __table_args__ = (
        Index('idx_order_stock_datetime', 'stock_id', 'order_datetime'),
        Index('idx_order_datetime', 'order_datetime'),
        Index('idx_kis_order_id', 'kis_order_id'),
    )
    
    def __repr__(self):
        return f"<Order(stock_id={self.stock_id}, type='{self.order_type}', price={self.price}, quantity={self.quantity})>"

class TradeExecution(Base):
    """실제 체결 내역 테이블 (하나의 주문이 여러 번 체결될 수 있음)"""
    __tablename__ = 'trade_executions'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False) # 편의상 중복 저장

    execution_type = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    trade_datetime = Column(DateTime, nullable=False, default=func.now(), index=True)

    created_at = Column(DateTime, default=func.now())

    order = relationship("Order", back_populates="trade_executions")
    stock = relationship("Stock")

    def __repr__(self):
        return f"<TradeExecution(id={self.id}, order_id={self.order_id}, type='{self.execution_type}', price={self.price}, qty={self.quantity})>"

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