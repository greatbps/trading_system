#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/test_kis_collector.py

Unit tests for KIS API Collector

This file contains comprehensive unit tests for the KIS collector
including mocking external dependencies and testing error conditions.

Author: AI Trading System
Version: 2.0.0
Last Updated: 2025-01-04
"""

import unittest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any
import aiohttp

# Import modules to test
from kis_collector_v2 import KISCollector, KISTokenManager, CircuitBreaker, RateLimiter
from kis_models import StockData, OHLCVData, Market, OrderRequest, OrderType, TradeType
from exceptions import (
    KISAPIError, KISAuthenticationError, KISRateLimitError, 
    KISNetworkError, KISDataValidationError
)


class MockConfig:
    """Mock configuration for testing"""
    
    class API:
        KIS_BASE_URL = "https://test.api.com"
        KIS_APP_KEY = "test_app_key"
        KIS_APP_SECRET = "test_app_secret"
        KIS_VIRTUAL_ACCOUNT = True
    
    class Trading:
        HTS_CONDITIONAL_SEARCH_IDS = {
            'test_strategy': '001'
        }
    
    api = API()
    trading = Trading()


class TestKISTokenManager(unittest.TestCase):
    """Test cases for KIS Token Manager"""
    
    def setUp(self):
        self.logger = Mock()
        self.token_manager = KISTokenManager(
            app_key="test_key",
            app_secret="test_secret", 
            base_url="https://test.api.com",
            logger=self.logger,
            virtual_mode=True
        )
    
    def test_init(self):
        """Test token manager initialization"""
        self.assertEqual(self.token_manager.app_key, "test_key")
        self.assertEqual(self.token_manager.app_secret, "test_secret")
        self.assertEqual(self.token_manager.virtual_mode, True)
        self.assertIsNone(self.token_manager.access_token)
        self.assertIsNone(self.token_manager.token_expired)
    
    def test_is_token_valid_no_token(self):
        """Test token validation with no token"""
        self.assertFalse(self.token_manager.is_token_valid())
    
    def test_is_token_valid_expired(self):
        """Test token validation with expired token"""
        self.token_manager.access_token = "test_token"
        self.token_manager.token_expired = datetime.now() - timedelta(hours=1)
        self.assertFalse(self.token_manager.is_token_valid())
    
    def test_is_token_valid_valid(self):
        """Test token validation with valid token"""
        self.token_manager.access_token = "test_token"
        self.token_manager.token_expired = datetime.now() + timedelta(hours=2)
        self.assertTrue(self.token_manager.is_token_valid())
    
    def test_get_headers_no_token(self):
        """Test getting headers without token"""
        with self.assertRaises(KISAuthenticationError):
            self.token_manager.get_headers()
    
    def test_get_headers_with_token(self):
        """Test getting headers with valid token"""
        self.token_manager.access_token = "test_token"
        
        headers = self.token_manager.get_headers(tr_id="TEST123")
        
        expected_headers = {
            'Authorization': 'Bearer test_token',
            'appkey': 'test_key',
            'appsecret': 'test_secret',
            'Content-Type': 'application/json',
            'User-Agent': 'TradingSystem/2.0',
            'tr_id': 'TEST123',
            'custtype': 'P'
        }
        
        self.assertEqual(headers, expected_headers)
    
    @patch('builtins.open', unittest.mock.mock_open(read_data='{"access_token": "cached_token", "expired_at": "2025-12-31T23:59:59", "app_key": "test_key", "app_secret": "test_secret", "virtual_mode": true}'))
    @patch('pathlib.Path.exists', return_value=True)
    async def test_load_cached_token_valid(self, mock_exists):
        """Test loading valid cached token"""
        # Set future expiry time for valid token
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1)
            mock_datetime.fromisoformat.return_value = datetime(2025, 12, 31, 23, 59, 59)
            
            result = await self.token_manager.load_cached_token()
            
            self.assertTrue(result)
            self.assertEqual(self.token_manager.access_token, "cached_token")


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for Circuit Breaker"""
    
    def setUp(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
    
    def test_init_closed_state(self):
        """Test circuit breaker starts in closed state"""
        self.assertEqual(self.circuit_breaker.state, 'CLOSED')
        self.assertEqual(self.circuit_breaker.failure_count, 0)
        self.assertTrue(self.circuit_breaker.can_execute())
    
    def test_on_success_resets_failures(self):
        """Test success resets failure count"""
        self.circuit_breaker.failure_count = 2
        self.circuit_breaker.on_success()
        
        self.assertEqual(self.circuit_breaker.failure_count, 0)
        self.assertEqual(self.circuit_breaker.state, 'CLOSED')
    
    def test_on_failure_increments_count(self):
        """Test failure increments failure count"""
        self.circuit_breaker.on_failure(Exception("test error"))
        
        self.assertEqual(self.circuit_breaker.failure_count, 1)
        self.assertEqual(self.circuit_breaker.state, 'CLOSED')
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold"""
        for i in range(3):
            self.circuit_breaker.on_failure(Exception(f"error {i}"))
        
        self.assertEqual(self.circuit_breaker.state, 'OPEN')
        self.assertFalse(self.circuit_breaker.can_execute())
    
    @patch('time.time')
    def test_circuit_half_open_after_timeout(self, mock_time):
        """Test circuit goes to half-open after recovery timeout"""
        # Open the circuit
        for i in range(3):
            self.circuit_breaker.on_failure(Exception(f"error {i}"))
        
        # Simulate time passing
        mock_time.side_effect = [100, 100, 200]  # 100 seconds passed
        
        self.assertTrue(self.circuit_breaker.can_execute())
        self.assertEqual(self.circuit_breaker.state, 'HALF_OPEN')


class TestRateLimiter(unittest.TestCase):
    """Test cases for Rate Limiter"""
    
    def setUp(self):
        self.rate_limiter = RateLimiter(max_requests=5, time_window=1)
    
    async def test_acquire_under_limit(self):
        """Test acquiring under rate limit"""
        # Should be able to acquire 5 times quickly
        for i in range(5):
            result = await self.rate_limiter.acquire()
            self.assertTrue(result)
    
    @patch('asyncio.sleep')
    async def test_acquire_over_limit_waits(self, mock_sleep):
        """Test acquiring over limit causes wait"""
        # Fill the bucket
        for i in range(5):
            await self.rate_limiter.acquire()
        
        # Next request should trigger wait
        await self.rate_limiter.acquire()
        
        # Verify sleep was called
        mock_sleep.assert_called()


class TestStockData(unittest.TestCase):
    """Test cases for StockData model"""
    
    def test_valid_stock_data(self):
        """Test creating valid stock data"""
        stock_data = StockData(
            symbol="005930",
            name="삼성전자",
            current_price=70000,
            change_rate=1.5,
            volume=1000000,
            trading_value=500.0,
            market_cap=400.0,
            market=Market.KOSPI
        )
        
        self.assertEqual(stock_data.symbol, "005930")
        self.assertEqual(stock_data.name, "삼성전자")
        self.assertEqual(stock_data.current_price, 70000)
        self.assertTrue(stock_data.is_kospi)
        self.assertFalse(stock_data.is_kosdaq)
    
    def test_invalid_symbol_format(self):
        """Test invalid symbol format raises error"""
        with self.assertRaises(ValueError):
            StockData(
                symbol="12345",  # Wrong length
                name="Test",
                current_price=1000,
                change_rate=0.0,
                volume=100,
                trading_value=1.0,
                market_cap=1.0,
                market=Market.KOSPI
            )
    
    def test_invalid_price(self):
        """Test invalid price raises error"""
        with self.assertRaises(ValueError):
            StockData(
                symbol="123456",
                name="Test",
                current_price=0,  # Invalid price
                change_rate=0.0,
                volume=100,
                trading_value=1.0,
                market_cap=1.0,
                market=Market.KOSPI
            )
    
    def test_to_dict_serialization(self):
        """Test stock data serialization to dict"""
        stock_data = StockData(
            symbol="005930",
            name="삼성전자",
            current_price=70000,
            change_rate=1.5,
            volume=1000000,
            trading_value=500.0,
            market_cap=400.0,
            market=Market.KOSPI
        )
        
        data_dict = stock_data.to_dict()
        
        self.assertEqual(data_dict['symbol'], "005930")
        self.assertEqual(data_dict['market'], "KOSPI")
        self.assertIn('last_updated', data_dict)


class TestOHLCVData(unittest.TestCase):
    """Test cases for OHLCV data model"""
    
    def test_valid_ohlcv_data(self):
        """Test creating valid OHLCV data"""
        ohlcv = OHLCVData(
            symbol="005930",
            datetime=datetime.now(),
            timeframe="1d",
            open_price=70000,
            high_price=72000,
            low_price=69000,
            close_price=71000,
            volume=1000000
        )
        
        self.assertEqual(ohlcv.symbol, "005930")
        self.assertTrue(ohlcv.is_bullish)  # close > open
        self.assertFalse(ohlcv.is_bearish)
        self.assertEqual(ohlcv.price_range, 3000)  # high - low
        self.assertEqual(ohlcv.body_size, 1000)  # |close - open|
    
    def test_invalid_high_low_relationship(self):
        """Test invalid high/low relationship raises error"""
        with self.assertRaises(ValueError):
            OHLCVData(
                symbol="005930",
                datetime=datetime.now(),
                timeframe="1d",
                open_price=70000,
                high_price=69000,  # High < Low - invalid
                low_price=71000,
                close_price=70500,
                volume=1000000
            )
    
    def test_bearish_candle(self):
        """Test bearish candle identification"""
        ohlcv = OHLCVData(
            symbol="005930",
            datetime=datetime.now(),
            timeframe="1d",
            open_price=71000,
            high_price=72000,
            low_price=69000,
            close_price=70000,  # close < open
            volume=1000000
        )
        
        self.assertFalse(ohlcv.is_bullish)
        self.assertTrue(ohlcv.is_bearish)
        self.assertEqual(ohlcv.change_percentage, (70000 - 71000) / 71000 * 100)


class TestKISCollectorIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for KIS Collector"""
    
    def setUp(self):
        self.config = MockConfig()
        self.collector = None
    
    async def asyncSetUp(self):
        """Async setup for each test"""
        self.collector = KISCollector(self.config)
    
    async def asyncTearDown(self):
        """Async cleanup after each test"""
        if self.collector:
            await self.collector.close()
    
    @patch('aiohttp.ClientSession')
    async def test_collector_initialization(self, mock_session_class):
        """Test collector initialization"""
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # Mock successful token request
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {'access_token': 'test_token'}
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        # Mock successful test connection
        mock_get_response = AsyncMock()
        mock_get_response.status = 200
        mock_get_response.json.return_value = {
            'output': {
                'stck_prpr': '70000',
                'hts_kor_isnm': '삼성전자',
                'mrkt_div_cd': 'J'
            }
        }
        mock_session.get.return_value.__aenter__.return_value = mock_get_response
        
        await self.collector.initialize()
        
        self.assertEqual(self.collector.status.value, 'CONNECTED')
        self.assertIsNotNone(self.collector.session)
        self.assertIsNotNone(self.collector.token_manager)
    
    @patch('aiohttp.ClientSession')
    async def test_get_stock_info_success(self, mock_session_class):
        """Test successful stock info retrieval"""
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # Mock token initialization
        token_response = AsyncMock()
        token_response.status = 200
        token_response.json.return_value = {'access_token': 'test_token'}
        
        # Mock stock info response
        stock_response = AsyncMock()
        stock_response.status = 200
        stock_response.json.return_value = {
            'output': {
                'stck_prpr': '70000',
                'hts_kor_isnm': '삼성전자',
                'prdy_ctrt': '1.5',
                'acml_vol': '1000000',
                'acml_tr_pbmn': '70000000000',
                'hts_avls': '40000000000000',
                'mrkt_div_cd': 'J',
                'w52_hgpr': '80000',
                'w52_lwpr': '60000',
                'per': '15.5',
                'pbr': '1.2'
            }
        }
        
        mock_session.post.return_value.__aenter__.return_value = token_response
        mock_session.get.return_value.__aenter__.return_value = stock_response
        
        await self.collector.initialize()
        stock_data = await self.collector.get_stock_info("005930")
        
        self.assertIsInstance(stock_data, StockData)
        self.assertEqual(stock_data.symbol, "005930")
        self.assertEqual(stock_data.name, "삼성전자")
        self.assertEqual(stock_data.current_price, 70000)
        self.assertEqual(stock_data.market, Market.KOSPI)
    
    async def test_get_stock_info_invalid_symbol(self):
        """Test stock info with invalid symbol"""
        with self.assertRaises(KISDataValidationError):
            await self.collector.get_stock_info("INVALID")
    
    @patch('aiohttp.ClientSession')
    async def test_api_error_handling(self, mock_session_class):
        """Test API error handling"""
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # Mock 401 authentication error
        error_response = AsyncMock()
        error_response.status = 401
        error_response.text.return_value = "Unauthorized"
        
        mock_session.post.return_value.__aenter__.return_value = error_response
        
        with self.assertRaises(KISAuthenticationError):
            await self.collector.initialize()
    
    @patch('aiohttp.ClientSession')
    async def test_rate_limiting(self, mock_session_class):
        """Test rate limiting functionality"""
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # Mock responses
        token_response = AsyncMock()
        token_response.status = 200
        token_response.json.return_value = {'access_token': 'test_token'}
        
        stock_response = AsyncMock()
        stock_response.status = 200
        stock_response.json.return_value = {'output': {'stck_prpr': '70000', 'hts_kor_isnm': 'Test'}}
        
        mock_session.post.return_value.__aenter__.return_value = token_response
        mock_session.get.return_value.__aenter__.return_value = stock_response
        
        await self.collector.initialize()
        
        # Test multiple rapid requests
        symbols = ["005930"] * 25  # More than rate limit
        start_time = datetime.now()
        
        prices = await self.collector.get_multiple_prices(symbols)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should take more than 1 second due to rate limiting
        self.assertGreater(duration, 1.0)
        self.assertEqual(len(prices), 25)


class TestExceptionHandling(unittest.TestCase):
    """Test cases for custom exceptions"""
    
    def test_kis_api_error_creation(self):
        """Test KIS API error creation"""
        error = KISAPIError(
            message="Test error",
            error_code="E001",
            response_data={"error": "details"}
        )
        
        self.assertEqual(str(error), "Test error | Error Code: E001")
        self.assertEqual(error.error_code, "E001")
        self.assertEqual(error.response_data, {"error": "details"})
        self.assertIsInstance(error.timestamp, datetime)
    
    def test_exception_to_dict(self):
        """Test exception serialization to dict"""
        error = KISAPIError("Test error", "E001")
        error_dict = error.to_dict()
        
        expected_keys = ['exception_type', 'message', 'error_code', 'response_data', 'timestamp']
        for key in expected_keys:
            self.assertIn(key, error_dict)
        
        self.assertEqual(error_dict['exception_type'], 'KISAPIError')
        self.assertEqual(error_dict['message'], 'Test error')
    
    def test_rate_limit_error_with_retry_after(self):
        """Test rate limit error with retry information"""
        error = KISRateLimitError(
            message="Rate limited",
            retry_after=60
        )
        
        self.assertEqual(error.retry_after, 60)
        
        error_dict = error.to_dict()
        self.assertEqual(error_dict['retry_after'], 60)


# Test runner
def run_tests():
    """Run all tests"""
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestKISTokenManager,
        TestCircuitBreaker,
        TestRateLimiter,
        TestStockData,
        TestOHLCVData,
        TestKISCollectorIntegration,
        TestExceptionHandling
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run tests
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        exit(1)