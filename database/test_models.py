#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for SQLAlchemy models
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import *
from datetime import datetime
from sqlalchemy import create_engine

def test_models():
    """Test model creation and relationships"""
    
    # Create in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    try:
        # Create all tables
        Base.metadata.create_all(engine)
        print("OK All tables created successfully")
        
        # Create session
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test Stock creation
        stock = Stock(
            symbol='005930',
            name='삼성전자',
            market=Market.KOSPI,
            sector='IT',
            current_price=75000,
            market_cap=4500000000000
        )
        session.add(stock)
        session.commit()
        print("OK Stock model created and saved")
        
        # Test FilteredStock creation
        filtered_stock = FilteredStock(
            stock_id=stock.id,
            strategy_name='momentum',
            filtered_date=datetime.now(),
            current_price=75000,
            volume=1000000
        )
        session.add(filtered_stock)
        session.commit()
        print("OK FilteredStock model created and saved")
        
        # Test AnalysisResult creation
        analysis = AnalysisResult(
            filtered_stock_id=filtered_stock.id,
            stock_id=stock.id,
            total_score=85.5,
            final_grade=AnalysisGrade.BUY,
            news_score=15.0,
            technical_score=35.5,
            supply_demand_score=35.0,
            is_selected=True
        )
        session.add(analysis)
        session.commit()
        print("OK AnalysisResult model created and saved")
        
        # Test Trade creation
        trade = Trade(
            analysis_result_id=analysis.id,
            stock_id=stock.id,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            order_quantity=100,
            order_price=75000,
            executed_price=74900,
            executed_quantity=100,
            order_time=datetime.now(),
            execution_time=datetime.now()
        )
        session.add(trade)
        session.commit()
        print("OK Trade model created and saved")
        
        # Test Portfolio creation
        portfolio = Portfolio(
            stock_id=stock.id,
            quantity=100,
            avg_price=74900,
            total_cost=7490000,
            current_price=75000
        )
        portfolio.update_current_values(75000)
        session.add(portfolio)
        session.commit()
        print("OK Portfolio model created and saved")
        
        # Test MarketData creation
        market_data = MarketData(
            stock_id=stock.id,
            symbol='005930',
            timeframe='1d',
            open_price=74000,
            high_price=76000,
            low_price=73500,
            close_price=75000,
            volume=5000000,
            datetime=datetime.now()
        )
        session.add(market_data)
        session.commit()
        print("OK MarketData model created and saved")
        
        # Test AccountInfo creation
        account = AccountInfo(
            account_number='12345678',
            cash_balance=10000000,
            total_assets=17490000,
            stock_value=7490000,
            available_cash=2500000
        )
        session.add(account)
        session.commit()
        print("OK AccountInfo model created and saved")
        
        # Test SystemLog creation
        log = SystemLog.log_info(
            session=session,
            module='test_models',
            function='test_models',
            message='Test log message',
            extra_data={'test': True}
        )
        print("OK SystemLog model created and saved")
        
        # Test TradingSession creation
        trading_session = TradingSession.create_new_session(
            session=session,
            session_id='TEST_SESSION_001',
            strategy='momentum',
            initial_capital=10000000,
            max_positions=5
        )
        print("OK TradingSession model created and saved")
        
        # Test relationships
        print("\n--- Testing Relationships ---")
        
        # Test Stock -> FilteredStock relationship
        stock_filtered = session.query(Stock).filter(Stock.symbol == '005930').first()
        print(f"Stock filtered_stocks count: {len(stock_filtered.filtered_stocks)}")
        
        # Test FilteredStock -> AnalysisResult relationship
        filtered = session.query(FilteredStock).first()
        print(f"FilteredStock has analysis_result: {filtered.analysis_result is not None}")
        
        # Test Stock -> Trade relationship
        print(f"Stock trades count: {len(stock_filtered.trades)}")
        
        # Test utility methods
        print("\n--- Testing Utility Methods ---")
        
        # Test Stock validation
        try:
            invalid_stock = Stock(symbol='12345', name='Invalid')  # Only 5 digits
            print("ERROR Stock validation failed to catch invalid symbol")
        except ValueError as e:
            print(f"OK Stock validation works: {e}")
        
        # Test Portfolio calculations
        pnl = portfolio.unrealized_pnl
        print(f"Portfolio unrealized P&L: {pnl:,} KRW")
        
        # Test Trade utility methods
        total_amount = trade.get_total_amount()
        is_completed = trade.is_completed()
        print(f"Trade total amount: {total_amount:,} KRW, completed: {is_completed}")
        
        # Test query methods
        print("\n--- Testing Query Methods ---")
        
        # Test class methods
        active_stocks = Stock.get_active_stocks(session)
        print(f"Active stocks count: {len(active_stocks)}")
        
        selected_analyses = AnalysisResult.get_selected_stocks(session)
        print(f"Selected analysis results count: {len(selected_analyses)}")
        
        recent_trades = Trade.get_recent_trades(session)
        print(f"Recent trades count: {len(recent_trades)}")
        
        open_positions = Portfolio.get_open_positions(session)
        print(f"Open positions count: {len(open_positions)}")
        
        session.close()
        print("\nOK All tests passed successfully!")
        
    except Exception as e:
        print(f"ERROR Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_models()