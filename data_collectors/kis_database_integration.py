#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/kis_database_integration.py

Database integration helper for KIS API Collector

This module provides seamless integration between the KIS API collector
and the existing SQLAlchemy database models, handling data conversion,
validation, and persistence operations.

Author: AI Trading System
Version: 2.0.0
Last Updated: 2025-01-04
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

# Import existing database models
from database.models import (
    Stock, FilteredStock, MarketData, AnalysisResult, Trade, Portfolio,
    AccountInfo as DBAccountInfo, SystemLog, TradingSession,
    Market as DBMarket, TradeType as DBTradeType, OrderStatus as DBOrderStatus,
    OrderType as DBOrderType, AnalysisGrade, RiskLevel, LogLevel
)

# Import KIS models
from .kis_models import (
    StockData, OHLCVData, AccountInfo, OrderRequest, OrderResponse,
    HTSCondition, MarketDepth, TechnicalIndicators, PerformanceMetrics,
    Market, TradeType, OrderStatus, OrderType
)

# Import exceptions
from .exceptions import KISAPIError, KISDataValidationError


class KISDatabaseIntegrator:
    """
    Database integration layer for KIS API Collector
    
    Handles conversion between KIS API data models and database models,
    provides CRUD operations, and manages data persistence.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    # Stock data operations
    async def save_stock_data(self, session: Session, stock_data: StockData) -> Optional[Stock]:
        """
        Save or update stock data in database
        
        Args:
            session: Database session
            stock_data: StockData instance from KIS API
            
        Returns:
            Stock database model instance
        """
        try:
            # Check if stock already exists
            existing_stock = session.query(Stock).filter(Stock.symbol == stock_data.symbol).first()
            
            if existing_stock:
                # Update existing stock
                self._update_stock_model(existing_stock, stock_data)
                stock = existing_stock
            else:
                # Create new stock
                stock = self._create_stock_model(stock_data)
                session.add(stock)
            
            session.commit()
            session.refresh(stock)
            
            self.logger.debug(f"Saved stock data for {stock_data.symbol}")
            return stock
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error saving stock {stock_data.symbol}: {e}")
            raise KISAPIError(f"Failed to save stock data: {e}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error saving stock {stock_data.symbol}: {e}")
            raise
    
    def _create_stock_model(self, stock_data: StockData) -> Stock:
        """Create Stock database model from StockData"""
        return Stock(
            symbol=stock_data.symbol,
            name=stock_data.name,
            market=self._convert_market_enum(stock_data.market),
            sector=stock_data.sector or "기타",
            current_price=stock_data.current_price,
            market_cap=int(stock_data.market_cap * 100) if stock_data.market_cap else None,
            shares_outstanding=stock_data.shares_outstanding,
            high_52w=stock_data.high_52w,
            low_52w=stock_data.low_52w,
            pe_ratio=stock_data.pe_ratio,
            pbr=stock_data.pbr,
            eps=stock_data.eps,
            bps=stock_data.bps,
            is_active=True
        )
    
    def _update_stock_model(self, stock: Stock, stock_data: StockData):
        """Update existing Stock model with new data"""
        stock.name = stock_data.name
        stock.current_price = stock_data.current_price
        stock.market_cap = int(stock_data.market_cap * 100) if stock_data.market_cap else stock.market_cap
        stock.shares_outstanding = stock_data.shares_outstanding or stock.shares_outstanding
        stock.high_52w = stock_data.high_52w or stock.high_52w
        stock.low_52w = stock_data.low_52w or stock.low_52w
        stock.pe_ratio = stock_data.pe_ratio or stock.pe_ratio
        stock.pbr = stock_data.pbr or stock.pbr
        stock.eps = stock_data.eps or stock.eps
        stock.bps = stock_data.bps or stock.bps
        stock.sector = stock_data.sector or stock.sector
        stock.updated_at = datetime.now()
    
    def _convert_market_enum(self, market: Market) -> DBMarket:
        """Convert KIS Market enum to database Market enum"""
        mapping = {
            Market.KOSPI: DBMarket.KOSPI,
            Market.KOSDAQ: DBMarket.KOSDAQ,
            Market.KONEX: DBMarket.KONEX
        }
        return mapping.get(market, DBMarket.KOSPI)
    
    # Market data operations
    async def save_ohlcv_data(
        self, 
        session: Session, 
        ohlcv_list: List[OHLCVData]
    ) -> List[MarketData]:
        """
        Save OHLCV data to database
        
        Args:
            session: Database session
            ohlcv_list: List of OHLCVData instances
            
        Returns:
            List of MarketData database models
        """
        try:
            if not ohlcv_list:
                return []
            
            # Get or create stock record
            symbol = ohlcv_list[0].symbol
            stock = await self._get_or_create_stock(session, symbol)
            
            saved_data = []
            
            for ohlcv in ohlcv_list:
                # Check if data already exists
                existing = session.query(MarketData).filter(
                    MarketData.symbol == ohlcv.symbol,
                    MarketData.timeframe == ohlcv.timeframe,
                    MarketData.datetime == ohlcv.datetime
                ).first()
                
                if existing:
                    # Update existing record
                    self._update_market_data_model(existing, ohlcv)
                    market_data = existing
                else:
                    # Create new record
                    market_data = self._create_market_data_model(stock.id, ohlcv)
                    session.add(market_data)
                
                saved_data.append(market_data)
            
            session.commit()
            
            self.logger.debug(f"Saved {len(saved_data)} OHLCV records for {symbol}")
            return saved_data
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error saving OHLCV data: {e}")
            raise KISAPIError(f"Failed to save OHLCV data: {e}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error saving OHLCV data: {e}")
            raise
    
    def _create_market_data_model(self, stock_id: int, ohlcv: OHLCVData) -> MarketData:
        """Create MarketData database model from OHLCVData"""
        return MarketData(
            stock_id=stock_id,
            symbol=ohlcv.symbol,
            timeframe=ohlcv.timeframe,
            datetime=ohlcv.datetime,
            open_price=ohlcv.open_price,
            high_price=ohlcv.high_price,
            low_price=ohlcv.low_price,
            close_price=ohlcv.close_price,
            volume=ohlcv.volume,
            trade_amount=ohlcv.trade_amount
        )
    
    def _update_market_data_model(self, market_data: MarketData, ohlcv: OHLCVData):
        """Update existing MarketData model"""
        market_data.open_price = ohlcv.open_price
        market_data.high_price = ohlcv.high_price
        market_data.low_price = ohlcv.low_price
        market_data.close_price = ohlcv.close_price
        market_data.volume = ohlcv.volume
        market_data.trade_amount = ohlcv.trade_amount
        market_data.updated_at = datetime.now()
    
    # Filtered stock operations (HTS results)
    async def save_filtered_stocks(
        self,
        session: Session,
        strategy_name: str,
        symbols: List[str],
        hts_condition_name: Optional[str] = None
    ) -> List[FilteredStock]:
        """
        Save HTS conditional search results as filtered stocks
        
        Args:
            session: Database session
            strategy_name: Strategy name used
            symbols: List of stock symbols from HTS condition
            hts_condition_name: Name of HTS condition used
            
        Returns:
            List of FilteredStock database models
        """
        try:
            filtered_stocks = []
            filtered_date = datetime.now()
            
            for symbol in symbols:
                # Get or create stock record
                stock = await self._get_or_create_stock(session, symbol)
                
                # Get current stock price for the filtered stock record
                current_price = None
                try:
                    # This would be provided by the collector
                    current_price = stock.current_price
                except:
                    pass
                
                # Create filtered stock record
                filtered_stock = FilteredStock(
                    stock_id=stock.id,
                    strategy_name=strategy_name,
                    filtered_date=filtered_date,
                    hts_condition_name=hts_condition_name,
                    current_price=current_price
                )
                
                session.add(filtered_stock)
                filtered_stocks.append(filtered_stock)
            
            session.commit()
            
            self.logger.info(f"Saved {len(filtered_stocks)} filtered stocks for strategy '{strategy_name}'")
            return filtered_stocks
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error saving filtered stocks: {e}")
            raise KISAPIError(f"Failed to save filtered stocks: {e}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error saving filtered stocks: {e}")
            raise
    
    # Account operations
    async def save_account_info(self, session: Session, account_info: AccountInfo) -> Optional[DBAccountInfo]:
        """
        Save account information to database
        
        Args:
            session: Database session
            account_info: AccountInfo instance from KIS API
            
        Returns:
            AccountInfo database model instance
        """
        try:
            # Check if account already exists
            existing_account = session.query(DBAccountInfo).filter(
                DBAccountInfo.account_number == account_info.account_number
            ).first()
            
            if existing_account:
                # Update existing account
                self._update_account_model(existing_account, account_info)
                account = existing_account
            else:
                # Create new account
                account = self._create_account_model(account_info)
                session.add(account)
            
            session.commit()
            session.refresh(account)
            
            self.logger.debug(f"Saved account info for {account_info.account_number}")
            return account
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error saving account info: {e}")
            raise KISAPIError(f"Failed to save account info: {e}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error saving account info: {e}")
            raise
    
    def _create_account_model(self, account_info: AccountInfo) -> DBAccountInfo:
        """Create AccountInfo database model"""
        return DBAccountInfo(
            account_number=account_info.account_number,
            cash_balance=account_info.cash_balance,
            total_assets=account_info.total_assets,
            stock_value=account_info.stock_value,
            available_cash=account_info.available_cash,
            daily_pnl=account_info.daily_pnl,
            total_pnl=account_info.total_pnl,
            loan_amount=getattr(account_info, 'loan_amount', 0)
        )
    
    def _update_account_model(self, account: DBAccountInfo, account_info: AccountInfo):
        """Update existing AccountInfo model"""
        account.cash_balance = account_info.cash_balance
        account.total_assets = account_info.total_assets
        account.stock_value = account_info.stock_value
        account.available_cash = account_info.available_cash
        account.daily_pnl = account_info.daily_pnl
        account.total_pnl = account_info.total_pnl
        account.loan_amount = getattr(account_info, 'loan_amount', account.loan_amount)
        account.update_time = datetime.now()
    
    # Portfolio operations
    async def update_portfolio_position(
        self,
        session: Session,
        symbol: str,
        quantity: int,
        avg_price: int,
        current_price: int
    ) -> Optional[Portfolio]:
        """
        Update portfolio position for a stock
        
        Args:
            session: Database session
            symbol: Stock symbol
            quantity: Current position quantity
            avg_price: Average purchase price
            current_price: Current market price
            
        Returns:
            Portfolio database model instance
        """
        try:
            # Get stock record
            stock = session.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                self.logger.warning(f"Stock {symbol} not found in database")
                return None
            
            # Get or create portfolio position
            position = session.query(Portfolio).filter(Portfolio.stock_id == stock.id).first()
            
            if position:
                # Update existing position
                position.quantity = quantity
                position.avg_price = avg_price
                position.total_cost = quantity * avg_price
                position.update_current_values(current_price)
            else:
                # Create new position
                position = Portfolio(
                    stock_id=stock.id,
                    quantity=quantity,
                    avg_price=avg_price,
                    total_cost=quantity * avg_price,
                    first_buy_date=datetime.now()
                )
                position.update_current_values(current_price)
                session.add(position)
            
            session.commit()
            session.refresh(position)
            
            self.logger.debug(f"Updated portfolio position for {symbol}")
            return position
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error updating portfolio: {e}")
            raise KISAPIError(f"Failed to update portfolio: {e}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error updating portfolio: {e}")
            raise
    
    # Trade operations
    async def save_trade_order(
        self,
        session: Session,
        order_request: OrderRequest,
        order_response: OrderResponse
    ) -> Optional[Trade]:
        """
        Save trade order to database
        
        Args:
            session: Database session
            order_request: Original order request
            order_response: Order response from KIS API
            
        Returns:
            Trade database model instance
        """
        try:
            # Get stock record
            stock = await self._get_or_create_stock(session, order_request.symbol)
            
            # Convert enums
            trade_type = self._convert_trade_type_enum(order_request.trade_type)
            order_type = self._convert_order_type_enum(order_request.order_type)
            order_status = self._convert_order_status_enum(order_response.status)
            
            # Create trade record
            trade = Trade(
                stock_id=stock.id,
                order_id=order_response.order_id,
                trade_type=trade_type,
                order_type=order_type,
                order_price=order_request.price,
                order_quantity=order_request.quantity,
                executed_price=order_response.executed_price,
                executed_quantity=order_response.executed_quantity,
                order_status=order_status,
                order_time=order_request.order_time,
                execution_time=order_response.execution_time,
                strategy_name="KIS_API",
                trigger_reason=f"Order placed via KIS API: {order_response.message}"
            )
            
            session.add(trade)
            session.commit()
            session.refresh(trade)
            
            self.logger.info(f"Saved trade order {order_response.order_id} for {order_request.symbol}")
            return trade
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error saving trade: {e}")
            raise KISAPIError(f"Failed to save trade: {e}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error saving trade: {e}")
            raise
    
    def _convert_trade_type_enum(self, trade_type: TradeType) -> DBTradeType:
        """Convert KIS TradeType to database TradeType"""
        mapping = {
            TradeType.BUY: DBTradeType.BUY,
            TradeType.SELL: DBTradeType.SELL
        }
        return mapping.get(trade_type, DBTradeType.BUY)
    
    def _convert_order_type_enum(self, order_type: OrderType) -> DBOrderType:
        """Convert KIS OrderType to database OrderType"""
        mapping = {
            OrderType.MARKET: DBOrderType.MARKET,
            OrderType.LIMIT: DBOrderType.LIMIT,
            OrderType.STOP: DBOrderType.STOP,
            OrderType.STOP_LIMIT: DBOrderType.STOP_LIMIT
        }
        return mapping.get(order_type, DBOrderType.MARKET)
    
    def _convert_order_status_enum(self, order_status: OrderStatus) -> DBOrderStatus:
        """Convert KIS OrderStatus to database OrderStatus"""
        mapping = {
            OrderStatus.PENDING: DBOrderStatus.PENDING,
            OrderStatus.PARTIAL: DBOrderStatus.PARTIAL,
            OrderStatus.FILLED: DBOrderStatus.FILLED,
            OrderStatus.CANCELLED: DBOrderStatus.CANCELLED,
            OrderStatus.REJECTED: DBOrderStatus.FAILED,
            OrderStatus.EXPIRED: DBOrderStatus.CANCELLED
        }
        return mapping.get(order_status, DBOrderStatus.PENDING)
    
    # System logging
    async def log_api_operation(
        self,
        session: Session,
        operation: str,
        level: str,
        message: str,
        execution_time: Optional[float] = None,
        error_details: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[SystemLog]:
        """
        Log API operation to database
        
        Args:
            session: Database session
            operation: Operation name
            level: Log level (INFO, ERROR, etc.)
            message: Log message
            execution_time: Operation execution time in seconds
            error_details: Error details if any
            extra_data: Additional data to log
            
        Returns:
            SystemLog database model instance
        """
        try:
            # Convert log level
            log_level_mapping = {
                'DEBUG': LogLevel.DEBUG,
                'INFO': LogLevel.INFO,
                'WARNING': LogLevel.WARNING,
                'ERROR': LogLevel.ERROR,
                'CRITICAL': LogLevel.CRITICAL
            }
            
            log_level = log_level_mapping.get(level.upper(), LogLevel.INFO)
            
            # Create log entry
            log_entry = SystemLog(
                log_level=log_level,
                module_name="KISCollector",
                function_name=operation,
                message=message,
                error_details=error_details,
                execution_time=execution_time,
                extra_data=extra_data
            )
            
            session.add(log_entry)
            session.commit()
            
            return log_entry
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to save system log: {e}")
            return None
        except Exception as e:
            session.rollback()
            self.logger.error(f"Unexpected error saving system log: {e}")
            return None
    
    # Performance metrics
    async def save_performance_metrics(
        self,
        session: Session,
        metrics: PerformanceMetrics,
        collector_id: str = "kis_collector"
    ) -> bool:
        """
        Save performance metrics to database as system log
        
        Args:
            session: Database session
            metrics: PerformanceMetrics instance
            collector_id: Identifier for the collector instance
            
        Returns:
            True if successful
        """
        try:
            metrics_data = metrics.to_dict()
            metrics_data['collector_id'] = collector_id
            
            await self.log_api_operation(
                session=session,
                operation="performance_metrics",
                level="INFO",
                message=f"KIS Collector performance metrics: {metrics.success_rate:.1f}% success rate",
                execution_time=metrics.average_response_time,
                extra_data=metrics_data
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save performance metrics: {e}")
            return False
    
    # Utility methods
    async def _get_or_create_stock(self, session: Session, symbol: str) -> Stock:
        """Get existing stock or create a minimal record"""
        stock = session.query(Stock).filter(Stock.symbol == symbol).first()
        
        if not stock:
            # Create minimal stock record
            stock = Stock(
                symbol=symbol,
                name=f"종목{symbol}",  # Placeholder name
                market=DBMarket.KOSPI,  # Default market
                sector="기타",
                is_active=True
            )
            session.add(stock)
            session.flush()  # Get the ID without committing
        
        return stock
    
    async def cleanup_old_data(
        self,
        session: Session,
        days_to_keep: int = 30
    ) -> Dict[str, int]:
        """
        Clean up old data from database
        
        Args:
            session: Database session
            days_to_keep: Number of days of data to keep
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleanup_results = {}
            
            # Clean up old market data
            old_market_data = session.query(MarketData).filter(
                MarketData.datetime < cutoff_date
            ).count()
            
            if old_market_data > 0:
                session.query(MarketData).filter(
                    MarketData.datetime < cutoff_date
                ).delete()
                cleanup_results['market_data'] = old_market_data
            
            # Clean up old system logs
            old_logs = session.query(SystemLog).filter(
                SystemLog.created_at < cutoff_date
            ).count()
            
            if old_logs > 0:
                session.query(SystemLog).filter(
                    SystemLog.created_at < cutoff_date
                ).delete()
                cleanup_results['system_logs'] = old_logs
            
            # Clean up old filtered stocks
            old_filtered = session.query(FilteredStock).filter(
                FilteredStock.filtered_date < cutoff_date
            ).count()
            
            if old_filtered > 0:
                session.query(FilteredStock).filter(
                    FilteredStock.filtered_date < cutoff_date
                ).delete()
                cleanup_results['filtered_stocks'] = old_filtered
            
            session.commit()
            
            self.logger.info(f"Database cleanup completed: {cleanup_results}")
            return cleanup_results
            
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database cleanup failed: {e}")
            raise KISAPIError(f"Database cleanup failed: {e}")
    
    # Query helpers
    async def get_latest_stock_prices(
        self,
        session: Session,
        symbols: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get latest stock prices from database
        
        Args:
            session: Database session
            symbols: List of symbols to query (None for all)
            limit: Maximum number of results
            
        Returns:
            List of stock price dictionaries
        """
        try:
            query = session.query(Stock).filter(Stock.is_active == True)
            
            if symbols:
                query = query.filter(Stock.symbol.in_(symbols))
            
            stocks = query.order_by(Stock.updated_at.desc()).limit(limit).all()
            
            return [
                {
                    'symbol': stock.symbol,
                    'name': stock.name,
                    'current_price': stock.current_price,
                    'market': stock.market.value,
                    'updated_at': stock.updated_at.isoformat() if stock.updated_at else None
                }
                for stock in stocks
            ]
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get stock prices: {e}")
            return []
    
    async def get_trading_performance(
        self,
        session: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get trading performance statistics
        
        Args:
            session: Database session
            days: Number of days to analyze
            
        Returns:
            Performance statistics dictionary
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get trade statistics
            trades = session.query(Trade).filter(
                Trade.order_time >= cutoff_date
            ).all()
            
            if not trades:
                return {'message': 'No trades found in the specified period'}
            
            total_trades = len(trades)
            buy_trades = len([t for t in trades if t.trade_type == DBTradeType.BUY])
            sell_trades = len([t for t in trades if t.trade_type == DBTradeType.SELL])
            filled_trades = len([t for t in trades if t.order_status == DBOrderStatus.FILLED])
            
            # Calculate success rate
            success_rate = (filled_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Get portfolio performance
            portfolios = session.query(Portfolio).all()
            total_pnl = sum(p.unrealized_pnl or 0 for p in portfolios)
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'filled_trades': filled_trades,
                'success_rate': success_rate,
                'active_positions': len(portfolios),
                'total_unrealized_pnl': total_pnl
            }
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get trading performance: {e}")
            return {'error': str(e)}


# Factory function for easy integration
def create_database_integrator(logger: Optional[logging.Logger] = None) -> KISDatabaseIntegrator:
    """
    Create and return a KIS database integrator instance
    
    Args:
        logger: Optional logger instance
        
    Returns:
        KISDatabaseIntegrator instance
    """
    return KISDatabaseIntegrator(logger=logger)


# Async context manager for database operations
class DatabaseOperationContext:
    """
    Async context manager for database operations with the KIS collector
    
    Usage:
        async with DatabaseOperationContext(session, logger) as db_ops:
            await db_ops.save_stock_data(stock_data)
    """
    
    def __init__(self, session: Session, logger: Optional[logging.Logger] = None):
        self.session = session
        self.integrator = KISDatabaseIntegrator(logger)
        self.start_time = None
    
    async def __aenter__(self) -> KISDatabaseIntegrator:
        self.start_time = datetime.now()
        return self.integrator
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Log error if operation failed
            duration = datetime.now() - self.start_time if self.start_time else None
            await self.integrator.log_api_operation(
                session=self.session,
                operation="database_operation",
                level="ERROR",
                message=f"Database operation failed: {exc_val}",
                execution_time=duration.total_seconds() if duration else None,
                error_details=str(exc_val) if exc_val else None
            )
        
        # Don't suppress exceptions
        return False