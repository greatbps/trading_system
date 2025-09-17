#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/models.py

SQLAlchemy 데이터베이스 모델 정의
AI 주식 트레이딩 시스템용 완전한 데이터베이스 모델
"""

import enum
from datetime import datetime, timedelta
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

class MonitoringStatus(enum.Enum):
    """모니터링 상태"""
    ACTIVE = "ACTIVE"      # 활성 모니터링
    INACTIVE = "INACTIVE"  # 비활성
    PAUSED = "PAUSED"      # 일시정지
    COMPLETED = "COMPLETED" # 완료 (매도됨)
    REMOVED = "REMOVED"     # 수동 제거

class MonitoringType(enum.Enum):
    """모니터링 유형"""
    TRADING = "TRADING"           # 매매용 모니터링
    REMOVAL_WATCH = "REMOVAL_WATCH" # 감시 제거용 모니터링
    PORTFOLIO = "PORTFOLIO"       # 보유 종목 모니터링

class NewsPeriodType(enum.Enum):
    """뉴스 재료 기간 분류"""
    SHORT_TERM = "SHORT_TERM"    # 단기 (1일~1주일)
    MID_TERM = "MID_TERM"        # 중기 (1주일~1개월) 
    LONG_TERM = "LONG_TERM"      # 장기 (1개월 이상)
    NEUTRAL = "NEUTRAL"          # 중립

class AnalysisSessionType(enum.Enum):
    """분석 세션 유형"""
    COMPREHENSIVE = "COMPREHENSIVE"      # 종합 분석
    NEWS_ONLY = "NEWS_ONLY"             # 뉴스 분석만
    SUPPLY_DEMAND = "SUPPLY_DEMAND"     # 수급 분석
    TECHNICAL = "TECHNICAL"             # 기술적 분석
    FUNDAMENTAL = "FUNDAMENTAL"         # 펀더멘탈 분석


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


# ==================== 뉴스 분석 캐싱 테이블 ====================

class NewsAnalysisSession(BaseModel):
    """뉴스 분석 세션 - 분석 요청 단위별 관리"""
    __tablename__ = 'news_analysis_sessions'
    
    session_id = Column(String(50), nullable=False, unique=True, index=True, comment="세션 UUID")
    analysis_type = Column(Enum(AnalysisSessionType), nullable=False, comment="분석 유형")
    
    # 분석 범위
    total_stocks = Column(Integer, nullable=False, default=0, comment="총 분석 대상 종목 수")
    analyzed_stocks = Column(Integer, nullable=False, default=0, comment="완료된 분석 종목 수")
    
    # 세션 상태
    status = Column(String(20), nullable=False, default='RUNNING', comment="세션 상태")
    
    # 타임스탬프는 BaseModel에서 상속받음
    completed_at = Column(DateTime, nullable=True, comment="완료 시간")
    
    # 관계 설정
    stock_analyses = relationship('StockNewsAnalysis', back_populates='session', cascade='all, delete-orphan')
    
    # 인덱스
    __table_args__ = (
        Index('idx_news_session_created', 'created_at'),
        Index('idx_news_session_status', 'status'),
    )

    @classmethod
    def create_session(cls, session_db: Session, session_id: str, analysis_type: AnalysisSessionType, total_stocks: int) -> 'NewsAnalysisSession':
        """새로운 뉴스 분석 세션 생성"""
        analysis_session = cls(
            session_id=session_id,
            analysis_type=analysis_type,
            total_stocks=total_stocks,
            status='RUNNING'
        )
        analysis_session.save(session_db)
        return analysis_session
    
    def complete_session(self):
        """세션 완료 처리"""
        self.status = 'COMPLETED'
        self.completed_at = datetime.utcnow()
    
    def __repr__(self):
        return f"<NewsAnalysisSession(session_id='{self.session_id}', status='{self.status}', analyzed={self.analyzed_stocks}/{self.total_stocks})>"


class StockNewsAnalysis(BaseModel):
    """종목별 뉴스 분석 결과 - 캐싱 핵심 테이블"""
    __tablename__ = 'stock_news_analysis'
    
    # 세션 정보
    session_id = Column(String(50), ForeignKey('news_analysis_sessions.session_id'), nullable=False)
    
    # 종목 정보
    symbol = Column(String(10), nullable=False, index=True, comment="종목코드")
    name = Column(String(100), nullable=False, comment="종목명")
    
    # 분석 결과
    total_news_count = Column(Integer, nullable=False, default=0, comment="총 뉴스 개수")
    
    # 기간별 뉴스 분석
    short_term_score = Column(Float, nullable=False, default=0.0, comment="단기 점수")
    short_term_count = Column(Integer, nullable=False, default=0, comment="단기 뉴스 개수")
    short_term_weight = Column(Float, nullable=False, default=0.0, comment="단기 가중치")
    
    mid_term_score = Column(Float, nullable=False, default=0.0, comment="중기 점수")
    mid_term_count = Column(Integer, nullable=False, default=0, comment="중기 뉴스 개수")
    mid_term_weight = Column(Float, nullable=False, default=0.0, comment="중기 가중치")
    
    long_term_score = Column(Float, nullable=False, default=0.0, comment="장기 점수")
    long_term_count = Column(Integer, nullable=False, default=0, comment="장기 뉴스 개수")
    long_term_weight = Column(Float, nullable=False, default=0.0, comment="장기 가중치")
    
    # 종합 점수
    final_news_score = Column(Float, nullable=False, default=0.0, comment="최종 뉴스 점수")
    sentiment_score = Column(Float, nullable=True, comment="AI 감성분석 점수")
    
    # 키워드 분석
    positive_keywords = Column(Text, nullable=True, comment="긍정 키워드 (JSON)")
    negative_keywords = Column(Text, nullable=True, comment="부정 키워드 (JSON)")
    neutral_keywords = Column(Text, nullable=True, comment="중립 키워드 (JSON)")
    
    # 뉴스 요약
    news_summary = Column(Text, nullable=True, comment="주요 뉴스 요약")
    
    # 타임스탬프는 BaseModel에서 상속받음
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="분석 시간")
    expires_at = Column(DateTime, nullable=False, comment="캐시 만료 시간")
    
    # 관계 설정
    session = relationship('NewsAnalysisSession', back_populates='stock_analyses')
    news_articles = relationship('NewsArticle', back_populates='stock_analysis', cascade='all, delete-orphan')
    
    # 인덱스
    __table_args__ = (
        Index('idx_stock_news_symbol', 'symbol'),
        Index('idx_stock_news_analyzed', 'analyzed_at'),
        Index('idx_stock_news_expires', 'expires_at'),
        Index('idx_stock_news_symbol_session', 'symbol', 'session_id'),
    )

    @classmethod
    def get_cached_analysis(cls, session: Session, symbol: str, hours: int = 6) -> Optional['StockNewsAnalysis']:
        """캐시된 뉴스 분석 결과 조회 (6시간 이내)"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return session.query(cls).filter(
            cls.symbol == symbol,
            cls.analyzed_at >= cutoff_time,
            cls.expires_at > datetime.utcnow()
        ).order_by(cls.analyzed_at.desc()).first()
    
    @classmethod
    def create_analysis(cls, session: Session, session_id: str, symbol: str, name: str, 
                       cache_hours: int = 6) -> 'StockNewsAnalysis':
        """새로운 뉴스 분석 결과 생성"""
        expires_at = datetime.utcnow() + timedelta(hours=cache_hours)
        analysis = cls(
            session_id=session_id,
            symbol=symbol,
            name=name,
            expires_at=expires_at
        )
        analysis.save(session)
        return analysis
    
    def update_analysis_results(self, total_count: int, short_score: float, short_count: int,
                              mid_score: float, mid_count: int, long_score: float, long_count: int,
                              final_score: float, sentiment: float = None):
        """분석 결과 업데이트"""
        self.total_news_count = total_count
        self.short_term_score = short_score
        self.short_term_count = short_count
        self.mid_term_score = mid_score
        self.mid_term_count = mid_count
        self.long_term_score = long_score
        self.long_term_count = long_count
        self.final_news_score = final_score
        self.sentiment_score = sentiment
    
    def is_expired(self) -> bool:
        """캐시 만료 여부 확인"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<StockNewsAnalysis(symbol='{self.symbol}', final_score={self.final_news_score}, news_count={self.total_news_count})>"


class NewsArticle(BaseModel):
    """개별 뉴스 기사 정보"""
    __tablename__ = 'news_articles'
    
    # 연결 정보
    stock_analysis_id = Column(Integer, ForeignKey('stock_news_analysis.id', ondelete='CASCADE'), nullable=False)
    
    # 뉴스 메타데이터
    news_id = Column(String(100), nullable=False, comment="뉴스 고유 ID")
    title = Column(String(500), nullable=False, comment="뉴스 제목")
    content = Column(Text, nullable=True, comment="뉴스 내용")
    
    # 뉴스 분류
    period_type = Column(Enum(NewsPeriodType), nullable=False, comment="기간 분류")
    
    # 점수
    base_score = Column(Float, nullable=False, default=0.0, comment="기본 점수")
    weighted_score = Column(Float, nullable=False, default=0.0, comment="가중치 적용 점수")
    
    # 키워드
    matched_keywords = Column(Text, nullable=True, comment="매칭된 키워드들 (JSON)")
    
    # 메타 정보
    published_at = Column(DateTime, nullable=False, comment="발행 시간")
    source = Column(String(100), nullable=True, comment="뉴스 출처")
    url = Column(String(500), nullable=True, comment="뉴스 URL")
    
    # 타임스탬프는 BaseModel에서 상속받음
    
    # 관계 설정
    stock_analysis = relationship('StockNewsAnalysis', back_populates='news_articles')
    
    # 인덱스
    __table_args__ = (
        Index('idx_news_article_stock_analysis', 'stock_analysis_id'),
        Index('idx_news_article_published', 'published_at'),
        Index('idx_news_article_period', 'period_type'),
        Index('idx_news_article_news_id', 'news_id'),
    )

    @classmethod
    def create_article(cls, session: Session, stock_analysis_id: int, news_id: str, title: str,
                      period_type: NewsPeriodType, base_score: float, weighted_score: float,
                      published_at: datetime, content: str = None, source: str = None,
                      url: str = None, matched_keywords: str = None) -> 'NewsArticle':
        """새로운 뉴스 기사 생성"""
        article = cls(
            stock_analysis_id=stock_analysis_id,
            news_id=news_id,
            title=title,
            content=content,
            period_type=period_type,
            base_score=base_score,
            weighted_score=weighted_score,
            published_at=published_at,
            source=source,
            url=url,
            matched_keywords=matched_keywords
        )
        article.save(session)
        return article
    
    def __repr__(self):
        return f"<NewsArticle(news_id='{self.news_id}', title='{self.title[:50]}...', score={self.weighted_score})>"


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
    trade_history = relationship("TradeHistory", back_populates="stock", cascade="all, delete-orphan")
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
        return session.query(cls).filter(
            cls.strategy_name == strategy_name,
            cls.filtered_date >= filtered_date.date(),
            cls.filtered_date < (filtered_date.date() + timedelta(days=1))
        ).all()
    
    @classmethod
    def get_recent_filtered(cls, session: Session, days: int = 7) -> List['FilteredStock']:
        """최근 N일 필터링 결과 조회"""
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
                              unique=True, nullable=True, index=True, comment="1:1 관계")
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=True, index=True)
    
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
    supply_demand_details = Column(JSON, comment="수급 분석 상세")
    
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
        CheckConstraint('technical_score >= 0 AND technical_score <= 100', name='check_technical_score_range'),
        CheckConstraint('supply_demand_score >= 0 AND supply_demand_score <= 100', name='check_supply_demand_score_range'),
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
    
    @classmethod
    def get_by_symbol_and_date(cls, session: Session, symbol: str, analysis_date: datetime) -> Optional['AnalysisResult']:
        """종목과 날짜로 분석 결과 조회"""
        # 날짜의 시작과 끝을 정확히 지정하여 해당 날짜의 모든 분석 결과를 포함
        start_of_day = analysis_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

        return session.query(cls).join(Stock).filter(
            Stock.symbol == symbol,
            cls.analysis_datetime >= start_of_day,
            cls.analysis_datetime <= end_of_day
        ).order_by(cls.analysis_datetime.desc()).first()

    def __repr__(self):
        return f"<AnalysisResult(stock_id={self.stock_id}, total_score={self.total_score}, grade='{self.final_grade.value if self.final_grade else None}')>"


class Trade(BaseModel):
    """매매 내역 테이블"""
    __tablename__ = 'trades'
    
    analysis_result_id = Column(Integer, ForeignKey('analysis_results.id'), nullable=True, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    
    # 주문 정보
    order_id = Column(String(50), comment="KIS 주문번호")
    trade_type = Column(Enum(TradeType), nullable=False, comment="BUY/SELL")
    order_type = Column(Enum(OrderType), nullable=False, comment="MARKET/LIMIT")
    
    # 가격/수량 정보 (한국 원화 - 정수)
    order_price = Column(Integer, comment="주문가격")
    order_quantity = Column(Integer, nullable=False, comment="주문수량")
    executed_price = Column(Integer, comment="체결가격")
    executed_quantity = Column(Integer, default=0, comment="체결수량")
    
    # 상태 정보
    order_status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, comment="주문상태")
    
    # 수수료 및 세금 (한국 원화 - 정수)
    commission = Column(Integer, default=0, comment="수수료")
    tax = Column(Integer, default=0, comment="세금")
    
    # 타이밍 정보
    order_time = Column(DateTime, nullable=False, index=True, comment="주문시간")
    execution_time = Column(DateTime, comment="체결시간")
    
    # 전략 정보
    strategy_name = Column(String(50), comment="사용된 전략")
    trigger_reason = Column(Text, comment="매매 사유")
    
    # 관계
    stock = relationship("Stock", back_populates="trades")
    analysis_result = relationship("AnalysisResult", back_populates="trades")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('order_quantity > 0', name='check_order_quantity_positive'),
        CheckConstraint('executed_quantity >= 0', name='check_executed_quantity_non_negative'),
        CheckConstraint('executed_quantity <= order_quantity', name='check_executed_not_exceed_order'),
        CheckConstraint('order_price IS NULL OR order_price > 0', name='check_order_price_positive'),
        CheckConstraint('executed_price IS NULL OR executed_price > 0', name='check_executed_price_positive'),
        Index('idx_trades_symbol_order_time', 'stock_id', 'order_time'),
        Index('idx_trades_order_time', 'order_time'),
        Index('idx_trades_status', 'order_status'),
        Index('idx_trades_order_id', 'order_id'),
    )
    
    @validates('order_quantity', 'executed_quantity')
    def validate_quantities(self, key, value):
        """수량 유효성 검사"""
        if key == 'order_quantity' and (value is None or value <= 0):
            raise ValueError("Order quantity must be positive")
        if key == 'executed_quantity' and value is not None and value < 0:
            raise ValueError("Executed quantity cannot be negative")
        return value
    
    @classmethod
    def get_by_status(cls, session: Session, status: OrderStatus) -> List['Trade']:
        """상태별 거래 조회"""
        return session.query(cls).filter(cls.order_status == status).all()
    
    @classmethod
    def get_recent_trades(cls, session: Session, days: int = 30) -> List['Trade']:
        """최근 거래 내역 조회"""
        cutoff_date = datetime.now() - timedelta(days=days)
        return session.query(cls).filter(cls.order_time >= cutoff_date).order_by(cls.order_time.desc()).all()
    
    def get_total_amount(self) -> int:
        """총 거래 금액 계산"""
        if self.executed_price and self.executed_quantity:
            return self.executed_price * self.executed_quantity + (self.commission or 0) + (self.tax or 0)
        return 0
    
    def is_completed(self) -> bool:
        """체결 완료 여부"""
        return self.order_status == OrderStatus.FILLED
    
    def __repr__(self):
        return f"<Trade(stock_id={self.stock_id}, type='{self.trade_type.value}', status='{self.order_status.value}', price={self.executed_price})>"


class TradeExecution(BaseModel):
    """실제 체결 내역 테이블 (하나의 주문이 여러 번 체결될 수 있음)"""
    __tablename__ = 'trade_executions'
    
    order_id = Column(Integer, ForeignKey('trades.id', ondelete='CASCADE'), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    
    # 체결 정보
    execution_type = Column(String(10), nullable=False, comment="BUY, SELL")
    quantity = Column(Integer, nullable=False, comment="체결수량")
    price = Column(Integer, nullable=False, comment="체결가격")
    commission = Column(Integer, default=0, comment="수수료")
    
    # 시간 정보
    trade_datetime = Column(DateTime, nullable=False, default=func.now(), index=True, comment="체결시간")
    
    # 관계
    order = relationship("Trade", backref="trade_executions")
    stock = relationship("Stock")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_execution_quantity_positive'),
        CheckConstraint('price > 0', name='check_execution_price_positive'),
        CheckConstraint('commission >= 0', name='check_execution_commission_non_negative'),
        Index('idx_trade_execution_order_id', 'order_id'),
        Index('idx_trade_execution_datetime', 'trade_datetime'),
    )
    
    def __repr__(self):
        return f"<TradeExecution(id={self.id}, order_id={self.order_id}, type='{self.execution_type}', price={self.price}, qty={self.quantity})>"





class AccountInfo(BaseModel):
    """계좌 정보 테이블"""
    __tablename__ = 'account_info'
    
    account_number = Column(String(20), nullable=False, unique=True, comment="계좌번호")
    
    # 잔고 정보 (한국 원화 - 정수)
    cash_balance = Column(BigInteger, nullable=False, comment="예수금")
    total_assets = Column(BigInteger, nullable=False, comment="총 자산")
    stock_value = Column(BigInteger, nullable=False, comment="주식 평가금액")
    
    # 주문 가능 정보
    available_cash = Column(BigInteger, nullable=False, comment="주문가능현금")
    loan_amount = Column(BigInteger, default=0, comment="대출금액")
    
    # 손익 정보 
    daily_pnl = Column(BigInteger, default=0, comment="일일손익")
    total_pnl = Column(BigInteger, default=0, comment="누적손익")
    
    # 업데이트 시간
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment="업데이트시간")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('cash_balance >= 0', name='check_cash_balance_non_negative'),
        CheckConstraint('available_cash >= 0', name='check_available_cash_non_negative'),
        CheckConstraint('loan_amount >= 0', name='check_loan_amount_non_negative'),
        Index('idx_account_number', 'account_number'),
    )
    
    @classmethod
    def get_by_account_number(cls, session: Session, account_number: str) -> Optional['AccountInfo']:
        """계좌번호로 조회"""
        return session.query(cls).filter(cls.account_number == account_number).first()
    
    def get_buying_power(self) -> int:
        """매수가능금액 계산"""
        return self.available_cash
    
    def update_balances(self, cash_balance: int, stock_value: int, available_cash: int):
        """잔고 정보 업데이트"""
        self.cash_balance = cash_balance
        self.stock_value = stock_value
        self.total_assets = cash_balance + stock_value
        self.available_cash = available_cash
        self.update_time = datetime.now()
    
    def __repr__(self):
        return f"<AccountInfo(account='{self.account_number}', total_assets={self.total_assets}, available_cash={self.available_cash})>"


class MarketScheduleCache(BaseModel):
    """시장 일정 캐시 테이블"""
    __tablename__ = 'market_schedule_cache'
    
    date = Column(String(8), nullable=False, unique=True, comment="날짜(YYYYMMDD)")
    is_market_open = Column(Boolean, nullable=False, comment="시장 개장 여부 (opnd_yn)")
    is_business_day = Column(Boolean, nullable=False, comment="영업일 여부 (bzdy_yn)")
    is_trading_day = Column(Boolean, nullable=False, comment="거래일 여부 (tr_day_yn)")
    is_settlement_day = Column(Boolean, nullable=False, comment="결제일 여부 (sttl_day_yn)")
    weekday_code = Column(String(2), comment="요일 구분 코드 (wday_dvsn_cd)")
    
    # 캐시 메타데이터
    fetched_at = Column(DateTime, default=func.now(), comment="KIS API에서 가져온 시간")
    expires_at = Column(DateTime, nullable=False, comment="만료 시간")
    
    # 제약 조건
    __table_args__ = (
        Index('idx_market_schedule_date', 'date'),
        Index('idx_market_schedule_expires', 'expires_at'),
    )
    
    @classmethod
    def get_valid_schedule(cls, session: Session, date: str) -> Optional['MarketScheduleCache']:
        """유효한 시장 일정 조회"""
        now = datetime.now()
        return session.query(cls).filter(
            cls.date == date,
            cls.expires_at > now
        ).first()
    
    @classmethod
    def create_from_api(cls, session: Session, date: str, api_data: Dict) -> 'MarketScheduleCache':
        """KIS API 데이터로 캐시 생성"""
        now = datetime.now()
        expires_at = now + timedelta(hours=24)  # 24시간 후 만료
        
        schedule = cls(
            date=date,
            is_market_open=api_data.get('opnd_yn') == 'Y',
            is_business_day=api_data.get('bzdy_yn') == 'Y',
            is_trading_day=api_data.get('tr_day_yn') == 'Y',
            is_settlement_day=api_data.get('sttl_day_yn') == 'Y',
            weekday_code=api_data.get('wday_dvsn_cd'),
            fetched_at=now,
            expires_at=expires_at
        )
        session.add(schedule)
        session.commit()
        return schedule
    
    @classmethod
    def upsert_from_api(cls, session: Session, date: str, api_data: Dict) -> 'MarketScheduleCache':
        """KIS API 데이터로 캐시 UPSERT (INSERT or UPDATE)"""
        now = datetime.now()
        expires_at = now + timedelta(hours=24)  # 24시간 후 만료
        
        # 기존 레코드 조회
        existing_schedule = session.query(cls).filter(cls.date == date).first()
        
        if existing_schedule:
            # UPDATE: 기존 레코드 업데이트
            existing_schedule.is_market_open = api_data.get('opnd_yn') == 'Y'
            existing_schedule.is_business_day = api_data.get('bzdy_yn') == 'Y'
            existing_schedule.is_trading_day = api_data.get('tr_day_yn') == 'Y'
            existing_schedule.is_settlement_day = api_data.get('sttl_day_yn') == 'Y'
            existing_schedule.weekday_code = api_data.get('wday_dvsn_cd')
            existing_schedule.fetched_at = now
            existing_schedule.expires_at = expires_at
            existing_schedule.updated_at = now
            
            session.commit()
            return existing_schedule
        else:
            # INSERT: 새 레코드 생성
            schedule = cls(
                date=date,
                is_market_open=api_data.get('opnd_yn') == 'Y',
                is_business_day=api_data.get('bzdy_yn') == 'Y',
                is_trading_day=api_data.get('tr_day_yn') == 'Y',
                is_settlement_day=api_data.get('sttl_day_yn') == 'Y',
                weekday_code=api_data.get('wday_dvsn_cd'),
                fetched_at=now,
                expires_at=expires_at
            )
            session.add(schedule)
            session.commit()
            return schedule
    
    def to_market_schedule(self):
        """MarketSchedule 데이터클래스로 변환"""
        from utils.market_schedule_manager import MarketSchedule
        return MarketSchedule(
            date=self.date,
            is_market_open=self.is_market_open,
            is_business_day=self.is_business_day,
            is_trading_day=self.is_trading_day,
            is_settlement_day=self.is_settlement_day,
            weekday_code=self.weekday_code
        )
    
    def __repr__(self):
        return f"<MarketScheduleCache(date='{self.date}', is_open={self.is_market_open}, expires={self.expires_at})>"


class SystemLog(BaseModel):
    """시스템 로그 테이블"""
    __tablename__ = 'system_logs'
    
    log_level = Column(Enum(LogLevel), nullable=False, index=True, comment="로그 레벨")
    module_name = Column(String(50), comment="모듈명")
    function_name = Column(String(50), comment="함수명")
    message = Column(Text, nullable=False, comment="로그 메시지")
    error_details = Column(Text, comment="오류 상세")
    execution_time = Column(DECIMAL(10, 6), comment="실행시간(초)")
    
    # 추가 정보
    extra_data = Column(JSON, comment="추가 데이터")
    
    # 제약 조건
    __table_args__ = (
        Index('idx_system_logs_level', 'log_level'),
        Index('idx_system_logs_time', 'created_at'),
        Index('idx_system_logs_module', 'module_name'),
    )
    
    @classmethod
    def log_info(cls, session: Session, module: str, function: str, message: str, extra_data: Dict = None):
        """INFO 레벨 로그 생성"""
        log = cls(
            log_level=LogLevel.INFO,
            module_name=module,
            function_name=function,
            message=message,
            extra_data=extra_data
        )
        log.save(session)
        return log
    
    @classmethod
    def log_error(cls, session: Session, module: str, function: str, message: str, error_details: str = None, extra_data: Dict = None):
        """ERROR 레벨 로그 생성"""
        log = cls(
            log_level=LogLevel.ERROR,
            module_name=module,
            function_name=function,
            message=message,
            error_details=error_details,
            extra_data=extra_data
        )
        log.save(session)
        return log
    
    @classmethod
    def get_recent_logs(cls, session: Session, level: LogLevel = None, hours: int = 24) -> List['SystemLog']:
        """최근 로그 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        query = session.query(cls).filter(cls.created_at >= cutoff_time)
        if level:
            query = query.filter(cls.log_level == level)
        return query.order_by(cls.created_at.desc()).all()
    
    def __repr__(self):
        return f"<SystemLog(level='{self.log_level.value}', module='{self.module_name}', message='{self.message[:50]}...')>"


class TradingSession(BaseModel):
    """거래 세션 테이블"""
    __tablename__ = 'trading_sessions'
    
    # 세션 정보
    session_id = Column(String(100), unique=True, nullable=False, index=True, comment="세션 ID")
    start_time = Column(DateTime, nullable=False, default=func.now(), comment="시작 시간")
    end_time = Column(DateTime, comment="종료 시간")
    
    # 설정 정보
    strategy = Column(String(50), comment="사용된 전략")
    initial_capital = Column(BigInteger, comment="초기 자본")
    max_positions = Column(Integer, comment="최대 포지션 수")
    
    # 성과 정보
    total_trades = Column(Integer, default=0, comment="총 거래 수")
    winning_trades = Column(Integer, default=0, comment="수익 거래 수")
    total_pnl = Column(BigInteger, default=0, comment="총 손익")
    max_drawdown = Column(BigInteger, default=0, comment="최대 손실")
    
    # 상태
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True, comment="세션 상태")
    
    # 메타 정보
    is_live_trading = Column(Boolean, default=False, comment="실거래 여부")
    notes = Column(Text, comment="비고")
    
    # 제약 조건
    __table_args__ = (
        CheckConstraint('initial_capital IS NULL OR initial_capital > 0', name='check_initial_capital_positive'),
        CheckConstraint('max_positions IS NULL OR max_positions > 0', name='check_max_positions_positive'),
        CheckConstraint('total_trades >= 0', name='check_total_trades_non_negative'),
        CheckConstraint('winning_trades >= 0', name='check_winning_trades_non_negative'),
        CheckConstraint('winning_trades <= total_trades', name='check_winning_not_exceed_total'),
        Index('idx_trading_session_id', 'session_id'),
        Index('idx_trading_session_status', 'status'),
    )
    
    @classmethod
    def get_active_session(cls, session: Session) -> Optional['TradingSession']:
        """활성 세션 조회"""
        return session.query(cls).filter(cls.status == SessionStatus.ACTIVE).first()
    
    @classmethod
    def create_new_session(cls, session: Session, session_id: str, strategy: str, initial_capital: int, max_positions: int = 5) -> 'TradingSession':
        """새 거래 세션 생성"""
        trading_session = cls(
            session_id=session_id,
            strategy=strategy,
            initial_capital=initial_capital,
            max_positions=max_positions,
            status=SessionStatus.ACTIVE
        )
        trading_session.save(session)
        return trading_session
    
    def end_session(self):
        """세션 종료"""
        self.end_time = datetime.now()
        self.status = SessionStatus.COMPLETED
    
    def update_performance(self, total_trades: int, winning_trades: int, total_pnl: int, max_drawdown: int):
        """성과 정보 업데이트"""
        self.total_trades = total_trades
        self.winning_trades = winning_trades
        self.total_pnl = total_pnl
        self.max_drawdown = max_drawdown
    
    def get_win_rate(self) -> float:
        """승률 계산"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def __repr__(self):
        return f"<TradingSession(session_id='{self.session_id}', strategy='{self.strategy}', status='{self.status.value}')>"


class WinLossStatus(enum.Enum):
    """승패 여부"""
    WIN = "WIN"
    LOSS = "LOSS"
    DRAW = "DRAW"


class TradeHistory(BaseModel):
    """매매 기록 테이블 (전략 분석용)"""
    __tablename__ = 'trade_history'

    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    strategy_name = Column(String(50), nullable=False, index=True, comment="전략명")
    
    buy_trade_id = Column(Integer, ForeignKey('trades.id'), nullable=False, comment="매수 주문 ID")
    sell_trade_id = Column(Integer, ForeignKey('trades.id'), nullable=False, comment="매도 주문 ID")

    buy_date = Column(DateTime, nullable=False, comment="매수 체결일")
    sell_date = Column(DateTime, nullable=False, comment="매도 체결일")
    
    buy_price = Column(Integer, nullable=False, comment="평균 매수가")
    sell_price = Column(Integer, nullable=False, comment="평균 매도가")
    quantity = Column(Integer, nullable=False, comment="수량")
    
    profit_loss = Column(BigInteger, nullable=False, comment="실현 손익금")
    profit_loss_rate = Column(DECIMAL(10, 2), nullable=False, comment="수익률 (%)")
    
    holding_period_days = Column(Integer, comment="보유기간 (일)")
    
    status = Column(Enum(WinLossStatus), nullable=False, comment="승패 (WIN/LOSS/DRAW)")

    stock = relationship("Stock", foreign_keys=[stock_id])
    buy_trade = relationship("Trade", foreign_keys=[buy_trade_id])
    sell_trade = relationship("Trade", foreign_keys=[sell_trade_id])

    __table_args__ = (
        Index('idx_trade_history_stock_strategy', 'stock_id', 'strategy_name'),
        Index('idx_trade_history_sell_date', 'sell_date'),
    )

    def __repr__(self):
        return f"<TradeHistory(stock_id={self.stock_id}, strategy='{self.strategy_name}', pnl_rate={self.profit_loss_rate})>"


# ========== 모니터링 시스템 모델 ==========
class MonitoringStock(BaseModel):
    """모니터링 종목 테이블 - 매매 및 감시 제거용"""
    __tablename__ = 'monitoring_stocks'
    
    # 종목 기본 정보
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=True, index=True)
    symbol = Column(String(10), nullable=False, index=True, comment="종목코드")
    name = Column(String(100), nullable=False, comment="종목명")
    
    # 모니터링 설정
    monitoring_type = Column(String(20), nullable=False, default=MonitoringType.TRADING.value, comment="모니터링 유형")
    strategy_name = Column(String(50), nullable=False, comment="전략명")

    # 가격 정보
    target_price = Column(Integer, comment="목표가")
    stop_loss_price = Column(Integer, comment="손절가")
    current_price = Column(Integer, comment="현재가")

    # 상태 정보
    status = Column(String(20), nullable=False, default=MonitoringStatus.ACTIVE, index=True, comment="모니터링 상태")
    monitoring_active = Column(Boolean, default=True, nullable=False, index=True, comment="활성화 여부")
    
    # 매수 관련 정보
    buy_price = Column(Integer, comment="매수가")
    buy_quantity = Column(Integer, comment="매수수량")
    buy_amount = Column(Integer, comment="매수금액")
    avg_price = Column(Integer, comment="평단가")
    profit_loss = Column(Integer, comment="손익금액")
    profit_rate = Column(Float, comment="손익률")
    buy_time = Column(DateTime, comment="매수시간")
    sell_time = Column(DateTime, comment="매도시간")
    holding_quantity = Column(Integer, comment="보유수량")
    
    # 시간 정보
    recommendation_time = Column(DateTime, nullable=False, default=func.now(), comment="추천/추가 시간")
    last_check_time = Column(DateTime, comment="마지막 체크 시간")
    completed_time = Column(DateTime, comment="완료 시간")
    
    # 매매 기록 연결
    buy_trade_id = Column(Integer, ForeignKey('trades.id'), nullable=True, comment="매수 거래 ID")
    
    # 메타 정보
    add_reason = Column(Text, comment="추가 사유")
    remove_reason = Column(Text, comment="제거/완료 사유")

    # --- 정밀 분석 결과 컬럼 추가 ---
    precision_score = Column(Float, nullable=True, comment="정밀 분석 점수 (0.0 ~ 1.0)")
    precision_signal = Column(String(10), nullable=True, comment="정밀 분석 예측 신호 (BUY/SELL)")
    precision_features = Column(JSON, nullable=True, comment="정밀 분석 주요 특성 (JSON)")
    # --- 컬럼 추가 완료 ---

    # 관계
    stock = relationship("Stock", foreign_keys=[stock_id])
    
    # 인덱스 및 제약조건
    __table_args__ = (
        Index('idx_monitoring_stocks_symbol', 'symbol'),
        Index('idx_monitoring_stocks_type', 'monitoring_type'),
        Index('idx_monitoring_stocks_status', 'status'),
        Index('idx_monitoring_stocks_active', 'monitoring_active'),
        Index('idx_monitoring_stocks_strategy', 'strategy_name'),
        Index('idx_monitoring_stocks_recommendation_time', 'recommendation_time'),
        CheckConstraint('target_price IS NULL OR target_price > 0', name='check_target_price_positive'),
        CheckConstraint('stop_loss_price IS NULL OR stop_loss_price > 0', name='check_stop_loss_positive'),
        CheckConstraint('current_price IS NULL OR current_price > 0', name='check_current_price_positive'),
        CheckConstraint('buy_price IS NULL OR buy_price > 0', name='check_buy_price_positive'),
        CheckConstraint('buy_quantity IS NULL OR buy_quantity > 0', name='check_buy_quantity_positive'),
        CheckConstraint('buy_amount IS NULL OR buy_amount > 0', name='check_buy_amount_positive'),
        CheckConstraint('avg_price IS NULL OR avg_price > 0', name='check_avg_price_positive'),
        CheckConstraint('holding_quantity IS NULL OR holding_quantity >= 0', name='check_holding_quantity_non_negative'),
    )
    
    @classmethod
    def get_active_monitoring(cls, session: Session, monitoring_type: MonitoringType = None) -> List['MonitoringStock']:
        """활성 모니터링 종목 조회"""
        query = session.query(cls).filter(
            cls.status == MonitoringStatus.ACTIVE.value,
            cls.monitoring_active == True
        )
        if monitoring_type:
            query = query.filter(cls.monitoring_type == monitoring_type)
        return query.order_by(cls.recommendation_time.asc()).all()
    
    @classmethod
    def get_by_symbol_and_type(cls, session: Session, symbol: str, monitoring_type: MonitoringType) -> Optional['MonitoringStock']:
        """종목코드와 타입으로 조회"""
        return session.query(cls).filter(
            cls.symbol == symbol,
            cls.monitoring_type == monitoring_type,
            cls.status == MonitoringStatus.ACTIVE.value
        ).first()
    
    @classmethod
    def add_monitoring_stock(cls, session: Session, symbol: str, name: str, 
                           monitoring_type: MonitoringType, strategy_name: str,
                           target_price: int = None, stop_loss_price: int = None,
                           add_reason: str = None) -> 'MonitoringStock':
        """모니터링 종목 추가"""
        monitoring_stock = cls(
            symbol=symbol,
            name=name,
            monitoring_type=monitoring_type,
            strategy_name=strategy_name,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            add_reason=add_reason,
            status=MonitoringStatus.ACTIVE.value,
            monitoring_active=True
        )
        monitoring_stock.save(session)
        return monitoring_stock
    
    # update_current_price 메서드 제거됨 - 현재가는 실시간 API 조회만 사용
    
    def complete_monitoring(self, reason: str = None):
        """모니터링 완료 처리"""
        self.status = MonitoringStatus.COMPLETED
        self.monitoring_active = False
        self.completed_time = datetime.now()
        if reason:
            self.remove_reason = reason
    
    def remove_monitoring(self, reason: str = None):
        """모니터링 제거 처리"""
        self.status = MonitoringStatus.REMOVED
        self.monitoring_active = False
        self.completed_time = datetime.now()
        if reason:
            self.remove_reason = reason
    
    def is_trading_type(self) -> bool:
        """매매용 모니터링인지 확인"""
        return self.monitoring_type == MonitoringType.TRADING
    
    def is_removal_watch_type(self) -> bool:
        """감시 제거용 모니터링인지 확인"""
        return self.monitoring_type == MonitoringType.REMOVAL_WATCH
    
    def __repr__(self):
        return f"<MonitoringStock(symbol='{self.symbol}', name='{self.name}', type='{self.monitoring_type.value}', status='{self.status.value}')>"




class Portfolio(BaseModel):
    """포트폴리오 테이블"""
    __tablename__ = 'portfolios'
    
    # 포트폴리오 기본 정보
    name = Column(String(100), nullable=False, comment="포트폴리오명")
    description = Column(Text, comment="설명")
    status = Column(Enum(PortfolioStatus), nullable=False, default=PortfolioStatus.OPEN, comment="상태")
    
    # 투자 정보
    initial_capital = Column(Integer, nullable=False, comment="초기 자본금")
    current_capital = Column(Integer, nullable=False, comment="현재 자본금")
    cash_balance = Column(Integer, nullable=False, comment="현금 잔고")
    
    # 성과 정보
    total_profit_loss = Column(Integer, default=0, comment="총 손익")
    profit_rate = Column(Float, default=0.0, comment="수익률(%)")
    
    # 리스크 관리
    max_position_ratio = Column(Float, default=0.1, comment="최대 단일종목 비중")
    stop_loss_ratio = Column(Float, default=0.05, comment="손절 비율")
    
    # 전략 정보
    strategy_name = Column(String(50), comment="적용 전략")
    
    # 시간 정보
    created_date = Column(DateTime, nullable=False, default=func.now(), comment="생성일")
    last_updated = Column(DateTime, default=func.now(), comment="마지막 업데이트")
    
    # 인덱스
    __table_args__ = (
        Index('idx_portfolio_name', 'name'),
        Index('idx_portfolio_status', 'status'),
        Index('idx_portfolio_strategy', 'strategy_name'),
    )
    
    def update_capital(self, new_capital: int):
        """자본금 업데이트"""
        self.current_capital = new_capital
        self.profit_rate = ((new_capital - self.initial_capital) / self.initial_capital) * 100
        self.total_profit_loss = new_capital - self.initial_capital
        self.last_updated = datetime.now()
    
    def __repr__(self):
        return f"<Portfolio(name='{self.name}', capital={self.current_capital:,}, profit_rate={self.profit_rate:.2f}%)>"

class MonitoringSchedulerState(BaseModel):
    """모니터링 스케줄러 상태 테이블"""
    __tablename__ = 'monitoring_scheduler_states'
    
    # 스케줄러 정보
    scheduler_type = Column(String(50), nullable=False, unique=True, index=True, comment="스케줄러 유형")
    is_running = Column(Boolean, default=False, nullable=False, comment="실행 상태")
    
    # 설정 정보
    interval_seconds = Column(Integer, default=1800, comment="실행 간격(초)")  # 기본 30분
    last_run_time = Column(DateTime, comment="마지막 실행 시간")
    next_run_time = Column(DateTime, comment="다음 실행 시간")
    
    # 실행 통계
    total_runs = Column(Integer, default=0, comment="총 실행 횟수")
    successful_runs = Column(Integer, default=0, comment="성공 실행 횟수")
    failed_runs = Column(Integer, default=0, comment="실패 실행 횟수")
    
    # 상태 정보
    last_error = Column(Text, comment="마지막 오류")
    config_data = Column(JSON, comment="설정 데이터")
    
    # 인덱스
    __table_args__ = (
        Index('idx_scheduler_state_type', 'scheduler_type'),
        Index('idx_scheduler_state_running', 'is_running'),
    )
    
    @classmethod
    def get_scheduler_state(cls, session: Session, scheduler_type: str) -> Optional['MonitoringSchedulerState']:
        """스케줄러 상태 조회"""
        return session.query(cls).filter(cls.scheduler_type == scheduler_type).first()
    
    @classmethod
    def create_or_update_scheduler(cls, session: Session, scheduler_type: str, 
                                 interval_seconds: int = 1800) -> 'MonitoringSchedulerState':
        """스케줄러 상태 생성 또는 업데이트"""
        state = cls.get_scheduler_state(session, scheduler_type)
        if not state:
            state = cls(
                scheduler_type=scheduler_type,
                interval_seconds=interval_seconds,
                is_running=False
            )
            session.add(state)
            session.commit()
            session.refresh(state)
        else:
            state.interval_seconds = interval_seconds
            session.commit()
        return state
    
    def start_scheduler(self):
        """스케줄러 시작"""
        self.is_running = True
        self.next_run_time = datetime.now() + timedelta(seconds=self.interval_seconds)
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        self.next_run_time = None
    
    def record_run_success(self):
        """실행 성공 기록"""
        self.total_runs += 1
        self.successful_runs += 1
        self.last_run_time = datetime.now()
        self.next_run_time = datetime.now() + timedelta(seconds=self.interval_seconds)
        self.last_error = None
    
    def record_run_failure(self, error_msg: str):
        """실행 실패 기록"""
        self.total_runs += 1
        self.failed_runs += 1
        self.last_run_time = datetime.now()
        self.next_run_time = datetime.now() + timedelta(seconds=self.interval_seconds)
        self.last_error = error_msg
    
    def get_success_rate(self) -> float:
        """성공률 계산"""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100
    
    def __repr__(self):
        return f"<MonitoringSchedulerState(type='{self.scheduler_type}', running={self.is_running}, success_rate={self.get_success_rate():.1f}%)>"


# ========== 필터링 기록 모델 ==========
class FilterHistory(BaseModel):
    """HTS 조건검색 및 AI 분석 필터링 기록"""
    __tablename__ = 'filter_history'
    
    # 필터링 기본 정보
    filter_date = Column(DateTime, nullable=False, index=True, comment="필터링 실행 날짜")
    strategy = Column(String(50), nullable=False, index=True, comment="적용 전략명")
    filter_type = Column(String(50), nullable=False, comment="필터 유형 (HTS/AI/COMBINED)")
    
    # 1차 HTS 필터링 결과
    hts_condition = Column(String(200), comment="HTS 조건검색 조건")
    hts_result_count = Column(Integer, default=0, comment="HTS 조건검색 결과 종목 수")
    hts_symbols = Column(JSON, comment="HTS 필터링 통과 종목 리스트")
    
    # 2차 AI 분석 결과
    ai_analyzed_count = Column(Integer, default=0, comment="AI 분석 대상 종목 수")
    ai_passed_count = Column(Integer, default=0, comment="AI 분석 통과 종목 수")
    
    # 최종 결과
    final_symbols = Column(JSON, comment="최종 선정 종목 리스트")
    final_count = Column(Integer, default=0, comment="최종 선정 종목 수")
    
    # 성능 메트릭
    execution_time = Column(Float, comment="전체 실행 시간(초)")
    hts_time = Column(Float, comment="HTS 필터링 시간(초)")
    ai_time = Column(Float, comment="AI 분석 시간(초)")
    
    # 분석 통계
    avg_score = Column(Float, comment="평균 분석 점수")
    max_score = Column(Float, comment="최고 분석 점수")
    min_score = Column(Float, comment="최저 분석 점수")
    
    # 결과 상태
    status = Column(String(20), default='COMPLETED', comment="필터링 상태")
    error_message = Column(Text, comment="오류 메시지 (있을 경우)")
    
    # 메타 정보
    market_condition = Column(String(50), comment="시장 상황")
    notes = Column(Text, comment="비고")
    
    # 인덱스
    __table_args__ = (
        Index('idx_filter_history_date', 'filter_date'),
        Index('idx_filter_history_strategy', 'strategy'),
        Index('idx_filter_history_type', 'filter_type'),
        Index('idx_filter_history_status', 'status'),
    )
    
    @classmethod
    def create_filter_record(cls, session: Session, strategy: str, filter_type: str = 'COMBINED') -> 'FilterHistory':
        """새 필터링 기록 생성"""
        filter_record = cls(
            filter_date=datetime.now(),
            strategy=strategy,
            filter_type=filter_type,
            status='STARTED'
        )
        session.add(filter_record)
        session.commit()
        session.refresh(filter_record)
        return filter_record
        
    def update_hts_results(self, condition: str, symbols: List[str], execution_time: float):
        """HTS 필터링 결과 업데이트"""
        self.hts_condition = condition
        self.hts_symbols = symbols
        self.hts_result_count = len(symbols) if symbols else 0
        self.hts_time = execution_time
        
    def update_ai_results(self, analyzed_count: int, passed_symbols: List[str], 
                         execution_time: float, avg_score: float = None,
                         max_score: float = None, min_score: float = None):
        """AI 분석 결과 업데이트"""
        self.ai_analyzed_count = analyzed_count
        self.final_symbols = passed_symbols
        self.ai_passed_count = len(passed_symbols) if passed_symbols else 0
        self.final_count = self.ai_passed_count
        self.ai_time = execution_time
        
        if avg_score is not None:
            self.avg_score = avg_score
        if max_score is not None:
            self.max_score = max_score
        if min_score is not None:
            self.min_score = min_score
            
    def complete_filtering(self, total_time: float, status: str = 'COMPLETED', error: str = None):
        """필터링 완료 처리"""
        self.execution_time = total_time
        self.status = status
        if error:
            self.error_message = error
            self.status = 'FAILED'
            
    def get_efficiency_ratio(self) -> float:
        """필터링 효율성 비율 계산 (최종 선정 / HTS 결과)"""
        if self.hts_result_count == 0:
            return 0.0
        return (self.final_count / self.hts_result_count) * 100
        
    def get_ai_pass_rate(self) -> float:
        """AI 분석 통과율 계산"""
        if self.ai_analyzed_count == 0:
            return 0.0
        return (self.ai_passed_count / self.ai_analyzed_count) * 100
        
    def __repr__(self):
        return f"<FilterHistory(strategy='{self.strategy}', date='{self.filter_date}', final_count={self.final_count})>"


class BacktestResults(BaseModel):
    """백테스트 결과 저장 테이블"""
    __tablename__ = 'backtest_results'
    
    # 백테스트 기본 정보
    strategy = Column(String(50), nullable=False, comment="전략 이름")
    start_date = Column(DateTime, nullable=False, comment="백테스트 시작일")
    end_date = Column(DateTime, nullable=False, comment="백테스트 종료일")
    
    # 자본 및 수익률
    initial_capital = Column(Float, nullable=False, comment="초기 자본")
    final_capital = Column(Float, nullable=False, comment="최종 자본")
    total_return = Column(Float, nullable=False, comment="총 수익률(%)")
    
    # 성과 지표
    max_drawdown = Column(Float, nullable=False, default=0.0, comment="최대 낙폭(%)")
    sharpe_ratio = Column(Float, nullable=False, default=0.0, comment="샤프 비율")
    total_trades = Column(Integer, nullable=False, default=0, comment="총 거래 수")
    win_rate = Column(Float, nullable=False, default=0.0, comment="승률(%)")
    
    # 상세 결과 데이터 (JSON)
    results_data = Column(JSON, comment="상세 백테스트 결과 데이터")
    
    def __repr__(self):
        return f"<BacktestResults(strategy='{self.strategy}', return={self.total_return:.2f}%, trades={self.total_trades})>"


# 데이터베이스 연결 및 설정
def create_database_engine(database_url: str, echo: bool = False) -> Engine:
    """데이터베이스 엔진 생성"""
    engine = create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "options": "-c timezone=Asia/Seoul"
        } if "postgresql" in database_url else {}
    )
    return engine

def create_all_tables(engine: Engine):
    """모든 테이블 생성"""
    # PostgreSQL ENUM 타입들을 명시적으로 생성
    if "postgresql" in str(engine.url):
        from sqlalchemy import text
        with engine.connect() as conn:
            # ENUM 타입들을 명시적으로 생성 (존재하지 않는 경우만)
            enum_types = [
                ("tradetype", ["BUY", "SELL"]),
                ("orderstatus", ["PENDING", "FILLED", "PARTIAL", "CANCELLED", "FAILED"]),
                ("ordertype", ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]),
                ("portfoliostatus", ["OPEN", "CLOSED", "CLOSING"]),
                ("analysisgrade", ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]),
                ("risklevel", ["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                ("loglevel", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
                ("market", ["KOSPI", "KOSDAQ", "KONEX"]),
                ("sessionstatus", ["ACTIVE", "COMPLETED", "STOPPED", "PAUSED"]),
                ("monitoringstatus", ["ACTIVE", "INACTIVE", "PAUSED", "COMPLETED", "REMOVED"]),
                ("monitoringtype", ["TRADING", "REMOVAL_WATCH", "PORTFOLIO"]),
                ("newsperiodtype", ["SHORT_TERM", "MID_TERM", "LONG_TERM", "NEUTRAL"]),
                ("analysissessiontype", ["COMPREHENSIVE", "NEWS_ONLY", "SUPPLY_DEMAND", "TECHNICAL", "FUNDAMENTAL"]),
                ("winlossstatus", ["WIN", "LOSS", "DRAW"])
            ]

            for enum_name, values in enum_types:
                try:
                    # ENUM 타입이 존재하는지 확인
                    result = conn.execute(text(f"SELECT 1 FROM pg_type WHERE typname = '{enum_name}'"))
                    if not result.fetchone():
                        # ENUM 타입 생성
                        values_str = "', '".join(values)
                        create_enum_sql = f"CREATE TYPE {enum_name} AS ENUM ('{values_str}')"
                        conn.execute(text(create_enum_sql))
                        print(f"Created ENUM type: {enum_name}")
                except Exception as e:
                    print(f"Warning: Could not create ENUM type {enum_name}: {e}")

            conn.commit()

    Base.metadata.create_all(engine)

def get_session_factory(engine: Engine) -> sessionmaker:
    """세션 팩토리 생성"""
    return sessionmaker(bind=engine)

def get_session(session_factory: sessionmaker) -> Session:
    """세션 생성"""
    return session_factory()

# 이벤트 리스너 설정
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 설정 (필요시)"""
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# 초기 데이터 설정 함수
def insert_initial_data(session: Session):
    """초기 데이터 삽입"""
    # 주요 지수 및 ETF 데이터
    initial_stocks = [
        {'symbol': '005930', 'name': '삼성전자', 'market': Market.KOSPI, 'sector': 'IT'},
        {'symbol': '000660', 'name': 'SK하이닉스', 'market': Market.KOSPI, 'sector': 'IT'},
        {'symbol': '035420', 'name': 'NAVER', 'market': Market.KOSPI, 'sector': 'IT'},
        {'symbol': '005490', 'name': 'POSCO홀딩스', 'market': Market.KOSPI, 'sector': '철강'},
        {'symbol': '068270', 'name': '셀트리온', 'market': Market.KOSPI, 'sector': '바이오'},
    ]
    
    for stock_data in initial_stocks:
        existing = session.query(Stock).filter(Stock.symbol == stock_data['symbol']).first()
        if not existing:
            stock = Stock(**stock_data)
            session.add(stock)
    
    try:
        session.commit()
        print("Initial data inserted successfully")
    except Exception as e:
        session.rollback()
        print(f"Error inserting initial data: {e}")

# 사용 예시
if __name__ == "__main__":
    # 설정 파일에서 데이터베이스 URL 가져오기
    from config import DatabaseConfig
    
    # 엔진 생성
    engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)
    
    # 테이블 생성
    create_all_tables(engine)
    
    # 세션 팩토리 생성
    SessionFactory = get_session_factory(engine)
    
    # 초기 데이터 삽입
    with get_session(SessionFactory) as session:
        insert_initial_data(session)
    
    print("Database setup completed successfully!")