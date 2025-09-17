#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매매 기록 및 분석 모델
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum, func, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Session
from .models import Base, BaseModel

class TradeResult(enum.Enum):
    """매매 결과"""
    WIN = "WIN"        # 승리 (수익)
    LOSS = "LOSS"      # 손실
    DRAW = "DRAW"      # 무승부

class TradeHistoryRecord(BaseModel):
    """매매 기록 테이블"""
    __tablename__ = 'trade_history_records'
    
    # 종목 정보
    symbol = Column(String(10), nullable=False, index=True, comment="종목코드")
    name = Column(String(100), nullable=False, comment="종목명")
    strategy_name = Column(String(50), nullable=False, index=True, comment="전략명")
    
    # 매매 정보
    buy_date = Column(DateTime, nullable=False, comment="매수일")
    sell_date = Column(DateTime, nullable=False, comment="매도일")
    buy_price = Column(Integer, nullable=False, comment="매수가")
    sell_price = Column(Integer, nullable=False, comment="매도가")
    quantity = Column(Integer, nullable=False, comment="거래 수량")
    
    # 수익률 및 결과
    profit_rate = Column(Float, nullable=False, comment="수익률")
    profit_amount = Column(Integer, nullable=False, comment="손익 금액")
    holding_days = Column(Integer, nullable=False, comment="보유 기간")
    trade_result = Column(Enum(TradeResult), nullable=False, index=True, comment="매매 결과")
    
    # 메타 정보
    notes = Column(Text, comment="매매 노트")
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    @classmethod
    def create_trade_record(cls, symbol: str, name: str, strategy_name: str,
                           buy_date: datetime, sell_date: datetime,
                           buy_price: int, sell_price: int, quantity: int,
                           notes: str = None):
        """매매 기록 생성"""
        profit_rate = ((sell_price - buy_price) / buy_price) * 100
        profit_amount = (sell_price - buy_price) * quantity
        holding_days = (sell_date - buy_date).days
        
        if profit_rate > 0.5:
            trade_result = TradeResult.WIN
        elif profit_rate < -0.5:
            trade_result = TradeResult.LOSS
        else:
            trade_result = TradeResult.DRAW
            
        return cls(
            symbol=symbol, name=name, strategy_name=strategy_name,
            buy_date=buy_date, sell_date=sell_date,
            buy_price=buy_price, sell_price=sell_price, quantity=quantity,
            profit_rate=profit_rate, profit_amount=profit_amount,
            holding_days=holding_days, trade_result=trade_result, notes=notes
        )

class StrategyPerformance(BaseModel):
    """전략별 성과 집계 테이블"""
    __tablename__ = 'strategy_performance'
    
    strategy_name = Column(String(50), nullable=False, unique=True, index=True)
    total_trades = Column(Integer, nullable=False, default=0)
    win_trades = Column(Integer, nullable=False, default=0)
    loss_trades = Column(Integer, nullable=False, default=0)
    draw_trades = Column(Integer, nullable=False, default=0)
    
    total_profit_rate = Column(Float, nullable=False, default=0.0)
    avg_profit_rate = Column(Float, nullable=False, default=0.0)
    win_rate = Column(Float, nullable=False, default=0.0)
    
    avg_holding_days = Column(Float, nullable=False, default=0.0)
    best_trade_rate = Column(Float)
    worst_trade_rate = Column(Float)
    
    last_updated = Column(DateTime, nullable=False, default=func.now())
    
    def update_performance(self, session: Session):
        """전략 성과 재계산"""
        trades = session.query(TradeHistoryRecord).filter(
            TradeHistoryRecord.strategy_name == self.strategy_name
        ).all()
        
        if not trades:
            return
        
        self.total_trades = len(trades)
        self.win_trades = len([t for t in trades if t.trade_result == TradeResult.WIN])
        self.loss_trades = len([t for t in trades if t.trade_result == TradeResult.LOSS])
        self.draw_trades = len([t for t in trades if t.trade_result == TradeResult.DRAW])
        
        profit_rates = [t.profit_rate for t in trades]
        self.total_profit_rate = sum(profit_rates)
        self.avg_profit_rate = self.total_profit_rate / self.total_trades
        self.win_rate = (self.win_trades / self.total_trades) * 100 if self.total_trades > 0 else 0.0
        
        self.avg_holding_days = sum([t.holding_days for t in trades]) / self.total_trades
        self.best_trade_rate = max(profit_rates) if profit_rates else 0.0
        self.worst_trade_rate = min(profit_rates) if profit_rates else 0.0
        
        self.last_updated = datetime.now()
    
    @classmethod
    def get_or_create(cls, session: Session, strategy_name: str):
        """전략 성과 레코드 가져오기 또는 생성"""
        performance = session.query(cls).filter(cls.strategy_name == strategy_name).first()
        if not performance:
            performance = cls(strategy_name=strategy_name)
            session.add(performance)
            session.flush()
        return performance

class MinimalMonitoringStock(BaseModel):
    """최소화된 모니터링 종목 테이블"""
    __tablename__ = 'minimal_monitoring_stocks'
    
    symbol = Column(String(10), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    strategy_name = Column(String(50), nullable=False, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    added_date = Column(DateTime, nullable=False, default=func.now())
    notes = Column(Text)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'strategy_name', name='uq_symbol_strategy'),
    )
    
    @classmethod
    def add_monitoring_stock(cls, session: Session, symbol: str, name: str, 
                           strategy_name: str, notes: str = None):
        """모니터링 종목 추가"""
        existing = session.query(cls).filter(
            cls.symbol == symbol,
            cls.strategy_name == strategy_name,
            cls.is_active == True
        ).first()
        
        if existing:
            return existing
        
        monitoring_stock = cls(
            symbol=symbol, name=name, strategy_name=strategy_name, notes=notes
        )
        session.add(monitoring_stock)
        return monitoring_stock
    
    @classmethod
    def get_active_stocks_by_strategy(cls, session: Session, strategy_name: str = None):
        """전략별 활성 모니터링 종목 조회"""
        query = session.query(cls).filter(cls.is_active == True)
        if strategy_name:
            query = query.filter(cls.strategy_name == strategy_name)
        return query.all()
    
    def deactivate(self):
        """모니터링 비활성화"""
        self.is_active = False
