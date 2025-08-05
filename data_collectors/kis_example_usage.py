#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/kis_example_usage.py

Example usage scripts for the KIS API Collector

This file demonstrates how to use the production-ready KIS collector
in various scenarios including basic data retrieval, HTS integration,
database operations, and error handling.

Author: AI Trading System
Version: 2.0.0
Last Updated: 2025-01-04
"""

import asyncio
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import KIS collector and related modules
from data_collectors.kis_collector_v2 import KISCollector
from data_collectors.kis_models import StockData, OrderRequest, OrderType, TradeType
from data_collectors.exceptions import KISAPIError, KISAuthenticationError, KISRateLimitError
from data_collectors.kis_database_integration import KISDatabaseIntegrator, DatabaseOperationContext

# Import database components
from database.models import create_database_engine, get_session_factory, get_session
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)


class KISCollectorExamples:
    """
    Comprehensive examples for using the KIS API Collector
    """
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger("KISExamples")
        
    async def example_basic_usage(self):
        """
        Example 1: Basic usage - Initialize collector and get stock data
        """
        print("\n" + "="*60)
        print("EXAMPLE 1: Basic Usage")
        print("="*60)
        
        try:
            # Initialize collector with async context manager
            async with KISCollector(self.config) as collector:
                
                # Test connection status
                status = collector.get_status()
                print(f"✅ Collector Status: {status['status']}")
                print(f"   Virtual Mode: {status['virtual_mode']}")
                print(f"   Token Valid: {status['token_info'].get('valid', False)}")
                
                # Get basic stock information
                print("\n📊 Getting stock information...")
                symbols = ["005930", "000660", "035420"]  # Samsung, SK Hynix, Naver
                
                for symbol in symbols:
                    stock_data = await collector.get_stock_info(symbol)
                    if stock_data:
                        print(f"   {symbol} ({stock_data.name}): {stock_data.current_price:,}원 "
                              f"({stock_data.change_rate:+.2f}%)")
                    else:
                        print(f"   {symbol}: Data not available")
                
                # Get multiple prices concurrently
                print("\n⚡ Getting multiple prices concurrently...")
                prices = await collector.get_multiple_prices(symbols)
                
                for symbol, price in prices.items():
                    if price:
                        print(f"   {symbol}: {price:,}원")
                    else:
                        print(f"   {symbol}: Price not available")
                
                # Show performance metrics
                metrics = collector.get_metrics()
                print(f"\n📈 Performance Metrics:")
                print(f"   Requests made: {metrics['requests_made']}")
                print(f"   Success rate: {((metrics['requests_made'] - metrics['requests_failed']) / max(metrics['requests_made'], 1) * 100):.1f}%")
                print(f"   Avg response time: {metrics['average_response_time']:.3f}s")
                
        except KISAPIError as e:
            print(f"❌ KIS API Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
    
    async def example_ohlcv_data(self):
        """
        Example 2: Retrieving OHLCV (candlestick) data
        """
        print("\n" + "="*60)
        print("EXAMPLE 2: OHLCV Data Retrieval")
        print("="*60)
        
        try:
            async with KISCollector(self.config) as collector:
                
                symbol = "005930"  # Samsung Electronics
                print(f"📈 Getting OHLCV data for {symbol}...")
                
                # Get daily data for the last 30 days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                ohlcv_data = await collector.get_ohlcv_data(
                    symbol=symbol,
                    timeframe="1d",
                    start_date=start_date,
                    end_date=end_date
                )
                
                if ohlcv_data:
                    print(f"✅ Retrieved {len(ohlcv_data)} OHLCV records")
                    
                    # Show last 5 records
                    print("\n📊 Last 5 trading days:")
                    for record in ohlcv_data[-5:]:
                        trend = "📈" if record.is_bullish else "📉" if record.is_bearish else "➡️"
                        print(f"   {record.datetime.date()} {trend} "
                              f"O:{record.open_price:,} H:{record.high_price:,} "
                              f"L:{record.low_price:,} C:{record.close_price:,} "
                              f"V:{record.volume:,}")
                    
                    # Calculate some basic statistics
                    latest = ohlcv_data[-1]
                    high_20d = max(r.high_price for r in ohlcv_data[-20:])
                    low_20d = min(r.low_price for r in ohlcv_data[-20:])
                    avg_volume = sum(r.volume for r in ohlcv_data[-20:]) / 20
                    
                    print(f"\n📊 20-day Statistics:")
                    print(f"   High: {high_20d:,}원")
                    print(f"   Low: {low_20d:,}원") 
                    print(f"   Current position: {((latest.close_price - low_20d) / (high_20d - low_20d) * 100):.1f}% of range")
                    print(f"   Avg daily volume: {avg_volume:,.0f}")
                    print(f"   Latest volume vs avg: {(latest.volume / avg_volume * 100):.1f}%")
                
                else:
                    print("❌ No OHLCV data available")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def example_hts_integration(self):
        """
        Example 3: HTS Conditional Search Integration
        """
        print("\n" + "="*60)
        print("EXAMPLE 3: HTS Conditional Search")
        print("="*60)
        
        try:
            async with KISCollector(self.config) as collector:
                
                # Check if PyKis is available for HTS operations
                if not collector.pykis:
                    print("⚠️ PyKis not available. HTS features require PyKis installation.")
                    return
                
                print("🔄 Loading HTS conditions...")
                success = await collector.load_hts_conditions()
                
                if not success:
                    print("❌ Failed to load HTS conditions")
                    return
                
                # Get available conditions
                print("📋 Getting HTS condition list...")
                conditions = await collector.get_hts_condition_list()
                
                if conditions:
                    print(f"✅ Found {len(conditions)} HTS conditions:")
                    for condition in conditions[:5]:  # Show first 5
                        print(f"   ID: {condition.condition_id} - {condition.condition_name}")
                    
                    # Use the first condition to get stocks
                    if conditions:
                        condition_id = conditions[0].condition_id
                        print(f"\n🔍 Getting stocks for condition {condition_id}...")
                        
                        stocks = await collector.get_stocks_by_condition(condition_id)
                        
                        if stocks:
                            print(f"✅ Found {len(stocks)} stocks matching condition:")
                            
                            # Get detailed info for first 5 stocks
                            for symbol in stocks[:5]:
                                stock_info = await collector.get_stock_info(symbol)
                                if stock_info:
                                    print(f"   {symbol} ({stock_info.name}): {stock_info.current_price:,}원")
                        else:
                            print("❌ No stocks found for this condition")
                
                # Get all strategy results
                print(f"\n🎯 Getting all strategy results...")
                strategy_results = await collector.get_all_strategy_results()
                
                for strategy_name, stock_list in strategy_results.items():
                    print(f"   Strategy '{strategy_name}': {len(stock_list)} stocks")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def example_database_integration(self):
        """
        Example 4: Database Integration
        """
        print("\n" + "="*60)
        print("EXAMPLE 4: Database Integration")
        print("="*60)
        
        try:
            # Initialize database
            engine = create_database_engine(self.config.database.DB_URL)
            SessionFactory = get_session_factory(engine)
            
            async with KISCollector(self.config) as collector:
                
                with get_session(SessionFactory) as session:
                    db_integrator = KISDatabaseIntegrator()
                    
                    # Get some stock data
                    symbols = ["005930", "000660"]
                    print(f"📊 Getting stock data for database storage...")
                    
                    for symbol in symbols:
                        stock_data = await collector.get_stock_info(symbol)
                        if stock_data:
                            # Save to database
                            db_stock = await db_integrator.save_stock_data(session, stock_data)
                            print(f"✅ Saved {stock_data.name} to database (ID: {db_stock.id})")
                            
                            # Get OHLCV data and save
                            ohlcv_data = await collector.get_ohlcv_data(symbol, timeframe="1d")
                            if ohlcv_data:
                                saved_ohlcv = await db_integrator.save_ohlcv_data(session, ohlcv_data[-5:])  # Last 5 days
                                print(f"✅ Saved {len(saved_ohlcv)} OHLCV records for {symbol}")
                    
                    # Log some metrics
                    metrics = collector.get_metrics()
                    await db_integrator.save_performance_metrics(session, collector.metrics, "example_collector")
                    print("✅ Saved performance metrics to database")
                    
                    # Get latest stock prices from database
                    latest_prices = await db_integrator.get_latest_stock_prices(session, symbols)
                    print(f"\n📈 Latest prices from database:")
                    for price_data in latest_prices:
                        print(f"   {price_data['symbol']} ({price_data['name']}): {price_data['current_price']:,}원")
                        
        except Exception as e:
            print(f"❌ Database Error: {e}")
    
    async def example_error_handling(self):
        """
        Example 5: Comprehensive Error Handling
        """
        print("\n" + "="*60)
        print("EXAMPLE 5: Error Handling Scenarios")
        print("="*60)
        
        try:
            async with KISCollector(self.config) as collector:
                
                print("🧪 Testing various error scenarios...")
                
                # Test with invalid symbol
                print("\n1. Testing invalid symbol...")
                try:
                    invalid_data = await collector.get_stock_info("INVALID")
                    print("   ⚠️ Expected error but got data")
                except KISAPIError as e:
                    print(f"   ✅ Caught expected error: {e}")
                
                # Test rate limiting (make many requests quickly)
                print("\n2. Testing rate limiting protection...")
                symbols = ["005930"] * 25  # More than rate limit
                start_time = datetime.now()
                
                prices = await collector.get_multiple_prices(symbols)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                print(f"   ✅ Completed {len(symbols)} requests in {duration:.2f}s")
                print(f"   ✅ Rate limiting working (should take >1s for 25 requests)")
                
                # Test circuit breaker status
                print("\n3. Testing circuit breaker...")
                cb_state = collector.circuit_breaker.state
                print(f"   Circuit breaker state: {cb_state}")
                
                # Show error handling capabilities
                print("\n4. Error handling features:")
                print("   ✅ Exponential backoff retry")
                print("   ✅ Circuit breaker pattern")
                print("   ✅ Rate limiting compliance")
                print("   ✅ Token auto-refresh")
                print("   ✅ Comprehensive logging")
                
        except KISAuthenticationError as e:
            print(f"❌ Authentication Error: {e}")
        except KISRateLimitError as e:
            print(f"❌ Rate Limit Error: {e}")
        except KISAPIError as e:
            print(f"❌ KIS API Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
    
    async def example_account_operations(self):
        """
        Example 6: Account and Trading Operations (Demo Mode)
        """
        print("\n" + "="*60)
        print("EXAMPLE 6: Account Operations (Demo)")
        print("="*60)
        
        try:
            async with KISCollector(self.config) as collector:
                
                print("💰 Getting account information...")
                
                # Note: This requires proper account configuration
                # In demo mode, this will likely fail gracefully
                try:
                    account_info = await collector.get_account_balance()
                    if account_info:
                        print(f"✅ Account Balance: {account_info.cash_balance:,}원")
                        print(f"   Total Assets: {account_info.total_assets:,}원")
                        print(f"   Available Cash: {account_info.available_cash:,}원")
                        print(f"   Daily P&L: {account_info.daily_pnl:+,}원")
                    else:
                        print("⚠️ Account information not available (demo mode)")
                except Exception as e:
                    print(f"⚠️ Account operations not available: {e}")
                
                # Demo order creation (not executed)
                print("\n📝 Creating demo order request...")
                
                order_request = OrderRequest(
                    symbol="005930",
                    order_type=OrderType.LIMIT,
                    trade_type=TradeType.BUY,
                    quantity=10,
                    price=70000
                )
                
                print(f"✅ Demo Order Created:")
                print(f"   Symbol: {order_request.symbol}")
                print(f"   Type: {order_request.order_type.value}")
                print(f"   Direction: {order_request.trade_type.value}")
                print(f"   Quantity: {order_request.quantity}")
                print(f"   Price: {order_request.price:,}원")
                print(f"   Estimated Value: {order_request.estimated_value:,}원")
                print("   ⚠️ Order not executed (demo mode)")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def example_health_monitoring(self):
        """
        Example 7: Health Check and Monitoring
        """
        print("\n" + "="*60)
        print("EXAMPLE 7: Health Check and Monitoring")
        print("="*60)
        
        try:
            async with KISCollector(self.config) as collector:
                
                print("🏥 Performing comprehensive health check...")
                
                health = await collector.health_check()
                
                print(f"Overall Status: {health['overall_status'].upper()}")
                print(f"Timestamp: {health['timestamp']}")
                
                print("\n📋 Individual Checks:")
                for check_name, check_result in health['checks'].items():
                    status_icon = "✅" if check_result['status'] == 'healthy' else "⚠️" if check_result['status'] == 'warning' else "❌"
                    print(f"   {status_icon} {check_name.replace('_', ' ').title()}: {check_result['details']}")
                
                # Show detailed metrics
                print("\n📊 Detailed Metrics:")
                metrics = collector.get_metrics()
                
                print(f"   Total Requests: {metrics['requests_made']}")
                print(f"   Failed Requests: {metrics['requests_failed']}")
                print(f"   Success Rate: {((metrics['requests_made'] - metrics['requests_failed']) / max(metrics['requests_made'], 1) * 100):.1f}%")
                print(f"   Average Response Time: {metrics['average_response_time']:.3f}s")
                
                if metrics['last_request_time']:
                    print(f"   Last Request: {metrics['last_request_time']}")
                
                # Show status information
                status = collector.get_status()
                print(f"\n🔧 System Status:")
                print(f"   Connection: {status['status']}")
                print(f"   Virtual Mode: {status['virtual_mode']}")
                print(f"   Circuit Breaker: {status['circuit_breaker_state']}")
                
                token_info = status.get('token_info', {})
                if token_info.get('valid'):
                    print(f"   Token: Valid ({token_info.get('remaining_time', 'Unknown')} remaining)")
                else:
                    print(f"   Token: Invalid or expired")
                
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
    
    async def run_all_examples(self):
        """Run all examples in sequence"""
        print("🚀 KIS API Collector - Comprehensive Examples")
        print(f"   Version: 2.0.0")
        print(f"   Start Time: {datetime.now()}")
        
        examples = [
            self.example_basic_usage,
            self.example_ohlcv_data,
            self.example_hts_integration,
            self.example_database_integration,
            self.example_error_handling,
            self.example_account_operations,
            self.example_health_monitoring
        ]
        
        for i, example in enumerate(examples, 1):
            try:
                await example()
            except KeyboardInterrupt:
                print(f"\n⚠️ Example {i} interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Example {i} failed: {e}")
                continue
        
        print(f"\n✅ Examples completed at {datetime.now()}")


# Performance testing
async def performance_test():
    """
    Performance test for the KIS collector
    """
    print("\n" + "="*60)
    print("PERFORMANCE TEST")
    print("="*60)
    
    config = Config()
    
    try:
        async with KISCollector(config) as collector:
            
            # Test concurrent requests
            symbols = ["005930", "000660", "035420", "207940", "006400"]
            
            print(f"🚀 Testing concurrent requests for {len(symbols)} symbols...")
            
            start_time = datetime.now()
            
            # Method 1: Sequential requests
            print("\n1. Sequential requests:")
            seq_start = datetime.now()
            sequential_results = []
            
            for symbol in symbols:
                result = await collector.get_stock_info(symbol)
                if result:
                    sequential_results.append(result)
            
            seq_duration = (datetime.now() - seq_start).total_seconds()
            print(f"   Time: {seq_duration:.2f}s")
            print(f"   Results: {len(sequential_results)}")
            
            # Method 2: Concurrent requests
            print("\n2. Concurrent requests:")
            conc_start = datetime.now()
            
            prices = await collector.get_multiple_prices(symbols)
            
            conc_duration = (datetime.now() - conc_start).total_seconds()
            concurrent_results = len([p for p in prices.values() if p is not None])
            
            print(f"   Time: {conc_duration:.2f}s")
            print(f"   Results: {concurrent_results}")
            
            # Performance comparison
            print(f"\n📊 Performance Comparison:")
            print(f"   Speedup: {seq_duration / conc_duration:.1f}x faster")
            print(f"   Rate: {len(symbols) / conc_duration:.1f} requests/second")
            
            total_duration = (datetime.now() - start_time).total_seconds()
            print(f"   Total test time: {total_duration:.2f}s")
            
            # Show final metrics
            metrics = collector.get_metrics()
            print(f"\n📈 Final Metrics:")
            print(f"   Total Requests: {metrics['requests_made']}")
            print(f"   Success Rate: {((metrics['requests_made'] - metrics['requests_failed']) / max(metrics['requests_made'], 1) * 100):.1f}%")
            print(f"   Average Response Time: {metrics['average_response_time']:.3f}s")
            
    except Exception as e:
        print(f"❌ Performance Test Error: {e}")


# Main execution
async def main():
    """Main example execution"""
    
    print("🎯 KIS API Collector - Example Usage")
    print("=" * 60)
    
    # Check if config is properly set up
    try:
        config = Config()
        if not config.api.KIS_APP_KEY or not config.api.KIS_APP_SECRET:
            print("⚠️ Warning: KIS API credentials not configured")
            print("   Set KIS_APP_KEY and KIS_APP_SECRET in your .env file")
            print("   Some examples may not work without proper credentials")
            print()
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        return
    
    examples = KISCollectorExamples()
    
    # Run examples
    try:
        await examples.run_all_examples()
        
        # Optional performance test
        print("\n" + "="*60)
        run_performance = input("Run performance test? (y/N): ").lower().strip()
        if run_performance == 'y':
            await performance_test()
            
    except KeyboardInterrupt:
        print("\n⚠️ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Examples failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Run examples
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal Error: {e}")
        sys.exit(1)