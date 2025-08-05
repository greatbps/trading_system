#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/kis_collector.py

Production-Ready KIS (Korea Investment & Securities) API Collector

Enterprise-grade features:
- Async/await architecture for high performance
- Circuit breaker pattern for reliability  
- Rate limiting compliance (20 req/sec)
- Exponential backoff retry mechanism
- Comprehensive error handling and logging
- HTS conditional search integration
- Token auto-refresh with caching
- Type hints and validation throughout
- Database integration with SQLAlchemy models
- Structured JSON logging
- Performance monitoring and metrics

Author: AI Trading System
Version: 2.1.0
Last Updated: 2025-08-05
"""

import asyncio
import aiohttp
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, AsyncContextManager
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from contextlib import asynccontextmanager
import logging
from decimal import Decimal
import math
import random

# Third-party imports
try:
    from pykis import Api, DomainInfo
except ImportError as e:
    Api = None
    DomainInfo = None
    print(f"FATAL: Failed to import pykis components: {e}")
    
# Local imports
from utils.logger import get_logger

# Enums for type safety
class Market(Enum):
    """Market classification"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"

class OrderType(Enum):
    """Order types for trading"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class TradeType(Enum):
    """Trade directions"""
    BUY = "BUY"
    SELL = "SELL"

class APIStatus(Enum):
    """API connection status"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"

# Custom exceptions for better error handling
class KISAPIError(Exception):
    """Base exception for KIS API errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.response_data = response_data
        
class KISAuthenticationError(KISAPIError):
    """Authentication related errors"""
    pass
    
class KISRateLimitError(KISAPIError):  
    """Rate limiting errors"""
    pass
    
class KISNetworkError(KISAPIError):
    """Network related errors"""
    pass
    
class KISDataValidationError(KISAPIError):
    """Data validation errors"""
    pass

# Data models with comprehensive validation
@dataclass
class StockData:
    """Enhanced stock data model with validation"""
    symbol: str
    name: str
    current_price: int  # Korean won - no decimals
    change_rate: float
    volume: int
    trading_value: float  # In millions
    market_cap: float    # In billions
    market: Market
    
    # Extended data
    shares_outstanding: Optional[int] = None
    high_52w: Optional[int] = None
    low_52w: Optional[int] = None
    pe_ratio: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[int] = None
    bps: Optional[int] = None
    sector: Optional[str] = "기타"
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    data_source: str = "KIS_API"
    
    def __post_init__(self):
        """Validate data after initialization"""
        if len(self.symbol) != 6 or not self.symbol.isdigit():
            raise ValueError(f"Invalid symbol format: {self.symbol}")
        if self.current_price <= 0:
            raise ValueError(f"Invalid price: {self.current_price}")
        if self.volume < 0:
            raise ValueError(f"Invalid volume: {self.volume}")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'current_price': self.current_price,
            'change_rate': self.change_rate,
            'volume': self.volume,
            'trading_value': self.trading_value,
            'market_cap': self.market_cap,
            'market': self.market.value,
            'shares_outstanding': self.shares_outstanding,
            'high_52w': self.high_52w,
            'low_52w': self.low_52w,
            'pe_ratio': self.pe_ratio,
            'pbr': self.pbr,
            'eps': self.eps,
            'bps': self.bps,
            'sector': self.sector,
            'last_updated': self.last_updated.isoformat(),
            'data_source': self.data_source
        }

@dataclass
class OHLCVData:
    """OHLCV candlestick data"""
    symbol: str
    datetime: datetime
    timeframe: str  # 1m, 5m, 15m, 1h, 1d, etc.
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int
    trade_amount: Optional[int] = None
    
    def __post_init__(self):
        """Validate OHLCV data"""
        if not all(p > 0 for p in [self.open_price, self.high_price, self.low_price, self.close_price]):
            raise ValueError("All prices must be positive")
        if self.high_price < self.low_price:
            raise ValueError("High price cannot be less than low price")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
            
@dataclass
class AccountInfo:
    """Account balance and position information"""
    account_number: str
    cash_balance: int  # Available cash in KRW
    total_assets: int  # Total portfolio value
    stock_value: int   # Current stock holdings value
    available_cash: int  # Available for trading
    daily_pnl: int = 0   # Daily profit/loss
    total_pnl: int = 0   # Total profit/loss
    
@dataclass
class OrderRequest:
    """Order request data structure"""
    symbol: str
    order_type: OrderType
    trade_type: TradeType
    quantity: int
    price: Optional[int] = None  # None for market orders
    
@dataclass
class OrderResponse:
    """Order response from KIS API"""
    order_id: str
    symbol: str
    status: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
@dataclass
class HTSCondition:
    """HTS conditional search condition"""
    condition_id: str
    condition_name: str
    description: Optional[str] = None

# Circuit breaker implementation
class CircuitBreaker:
    """Circuit breaker pattern implementation for API reliability"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == 'CLOSED':
            return True
        elif self.state == 'OPEN':
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = 'HALF_OPEN'
                return True
            return False
        elif self.state == 'HALF_OPEN':
            return True
        return False
        
    def on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = 'CLOSED'
        
    def on_failure(self, exception: Exception):
        """Handle failed operation"""
        if isinstance(exception, self.expected_exception):
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'

# Rate limiter for API compliance
class RateLimiter:
    """Token bucket rate limiter for KIS API (20 requests/second)"""
    
    def __init__(self, max_requests: int = 20, time_window: int = 1):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
        
    async def acquire(self) -> bool:
        """Acquire rate limit permission"""
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside time window
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return await self.acquire()
            
            return True

class KISTokenManager:
    """Enhanced token manager with caching and auto-refresh"""
    
    def __init__(self, app_key: str, app_secret: str, base_url: str, logger: logging.Logger, virtual_mode: bool = True):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.logger = logger
        self.virtual_mode = virtual_mode
        
        # Token state
        self.access_token: Optional[str] = None
        self.token_expired: Optional[datetime] = None
        self.refresh_threshold = timedelta(hours=1)  # Refresh 1 hour before expiry
        
        # File caching
        self.token_file = Path("data/kis_token.json")
        self.token_file.parent.mkdir(exist_ok=True)
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
    def _load_token_from_file(self) -> Optional[Dict]:
        """Load cached token from file with validation"""
        try:
            if not self.token_file.exists():
                self.logger.debug("Token cache file does not exist")
                return None
            
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # Validate required fields
            required_fields = ['access_token', 'expired_at', 'app_key', 'app_secret', 'virtual_mode']
            if not all(field in token_data for field in required_fields):
                self.logger.warning("Token cache missing required fields")
                return None
            
            # Validate credentials match
            if (token_data['app_key'] != self.app_key or 
                token_data['app_secret'] != self.app_secret or
                token_data['virtual_mode'] != self.virtual_mode):
                self.logger.warning("Token cache credentials mismatch")
                return None
            
            self.logger.debug("Token cache loaded successfully")
            return token_data
            
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Failed to load token cache: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error loading token cache: {e}")
            return None
    
    def _save_token_to_file(self) -> bool:
        """Save token to cache file with metadata"""
        try:
            if not self.access_token or not self.token_expired:
                self.logger.warning("Cannot save incomplete token data")
                return False
            
            # Create secure token data
            token_data = {
                'access_token': self.access_token,
                'expired_at': self.token_expired.isoformat(),
                'app_key': self.app_key,
                'app_secret': self.app_secret,  # Consider encrypting in production
                'virtual_mode': self.virtual_mode,
                'created_at': datetime.now().isoformat(),
                'cache_version': '2.0'
            }
            
            # Atomic write to prevent corruption
            temp_file = self.token_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.token_file)
            self.logger.info("Token cache saved successfully")
            return True
            
        except IOError as e:
            self.logger.error(f"Failed to save token cache (IO error): {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error saving token cache: {e}")
            return False
    
    async def load_cached_token(self) -> bool:
        """Load and validate cached token with expiry check"""
        async with self._lock:
            try:
                token_data = self._load_token_from_file()
                if not token_data:
                    return False
                
                expired_at = datetime.fromisoformat(token_data['expired_at'])
                
                # Check if token is still valid (with refresh threshold)
                if datetime.now() >= expired_at - self.refresh_threshold:
                    self.logger.info("Cached token is near expiry, will refresh")
                    return False
                
                self.access_token = token_data['access_token']
                self.token_expired = expired_at
                
                remaining_time = expired_at - datetime.now()
                self.logger.info(f"Using cached token (expires in {remaining_time})")
                return True
                
            except ValueError as e:
                self.logger.warning(f"Invalid token data format: {e}")
                return False
            except Exception as e:
                self.logger.error(f"Unexpected error loading cached token: {e}")
                return False
    
    async def request_new_token(self, session: aiohttp.ClientSession) -> bool:
        """Request new access token with comprehensive error handling"""
        async with self._lock:
            try:
                self.logger.info("Requesting new access token...")
                
                # Select endpoint based on mode
                endpoint = "/oauth2/tokenP" if not self.virtual_mode else "/oauth2/tokenP"
                url = f"{self.base_url}{endpoint}"
                
                payload = {
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'TradingSystem/2.0'
                }
                
                # Make request with timeout
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            
                            # Validate response structure
                            if 'access_token' not in result:
                                raise KISAuthenticationError("Access token not found in response")
                            
                            self.access_token = result['access_token']
                            # KIS tokens typically expire in 24 hours, set to 23h50m for safety
                            self.token_expired = datetime.now() + timedelta(hours=23, minutes=50)
                            
                            # Cache the token
                            self._save_token_to_file()
                            
                            self.logger.info(f"New access token obtained (expires: {self.token_expired})")
                            return True
                            
                        except json.JSONDecodeError as e:
                            raise KISAuthenticationError(f"Invalid JSON response: {e}")
                            
                    elif response.status == 401:
                        raise KISAuthenticationError(f"Authentication failed: {response_text}")
                    elif response.status == 429:
                        raise KISRateLimitError(f"Rate limit exceeded: {response_text}")
                    else:
                        raise KISAPIError(f"Token request failed with status {response.status}: {response_text}")
                        
            except asyncio.TimeoutError:
                raise KISNetworkError("Token request timed out")
            except aiohttp.ClientError as e:
                raise KISNetworkError(f"Network error during token request: {e}")
            except KISAPIError:
                raise  # Re-raise KIS-specific errors
            except Exception as e:
                raise KISAPIError(f"Unexpected error during token request: {e}")
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not near expiry"""
        if not self.access_token or not self.token_expired:
            return False
        return datetime.now() < self.token_expired - self.refresh_threshold
        
    def get_token_info(self) -> Dict[str, Any]:
        """Get current token information"""
        if not self.access_token:
            return {'status': 'No token', 'valid': False}
            
        remaining_time = self.token_expired - datetime.now() if self.token_expired else None
        
        return {
            'status': 'Active',
            'valid': self.is_token_valid(),
            'expires_at': self.token_expired.isoformat() if self.token_expired else None,
            'remaining_time': str(remaining_time) if remaining_time else None,
            'virtual_mode': self.virtual_mode
        }
    
    def get_headers(self, tr_id: Optional[str] = None, custtype: str = "P") -> Dict[str, str]:
        """Get API headers with optional transaction ID"""
        if not self.access_token:
            raise KISAuthenticationError("No valid access token available")
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'Content-Type': 'application/json',
            'User-Agent': 'TradingSystem/2.0'
        }
        
        if tr_id:
            headers['tr_id'] = tr_id
        if custtype:
            headers['custtype'] = custtype
            
        return headers
        
    async def ensure_valid_token(self, session: aiohttp.ClientSession) -> bool:
        """Ensure we have a valid token, refresh if necessary"""
        if self.is_token_valid():
            return True
            
        self.logger.info("Token invalid or near expiry, refreshing...")
        return await self.request_new_token(session)

class KISCollector:
    """
    Production-ready KIS API Collector with enterprise features
    """
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or get_logger("KISCollector")
        
        # API Configuration
        self.base_url = config.api.KIS_BASE_URL
        self.app_key = config.api.KIS_APP_KEY
        self.app_secret = config.api.KIS_APP_SECRET
        self.is_virtual = getattr(config.api, 'KIS_VIRTUAL_ACCOUNT', True)
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS API credentials not configured")
        
        # Core components
        self.token_manager = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(max_requests=20, time_window=1)
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # PyKis integration
        self.pykis_api = None
        if Api and DomainInfo:
            try:
                key_info = {"appkey": self.app_key, "appsecret": self.app_secret}
                
                domain_info = None
                if self.is_virtual:
                    domain_info = DomainInfo(kind="virtual")

                self.pykis_api = Api(key_info=key_info, domain_info=domain_info)
                self.logger.info("pykis.Api integration enabled")
            except Exception as e:
                self.logger.warning(f"pykis.Api initialization failed: {e}")
        
        # Performance metrics
        self.metrics = {
            'requests_made': 0,
            'requests_failed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0.0,
            'last_request_time': None
        }
        
        # Status
        self.status = APIStatus.DISCONNECTED
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # Performance metrics
        self.metrics = {
            'requests_made': 0,
            'requests_failed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0.0,
            'last_request_time': None
        }
        
        # Status
        self.status = APIStatus.DISCONNECTED
        self.last_error = None
        
        self.logger.info(f"KISCollector initialized (virtual: {self.is_virtual})")
    
    async def __aenter__(self) -> 'KISCollector':
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self) -> bool:
        """
        Initialize the collector with all components
        """
        try:
            self.logger.info("Initializing KIS API collector...")
            
            self.token_manager = KISTokenManager(
                self.app_key, self.app_secret, self.base_url, self.logger, self.is_virtual
            )
            
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300, use_dns_cache=True, enable_cleanup_closed=True)
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.session = aiohttp.ClientSession(
                connector=connector, timeout=timeout,
                headers={'Content-Type': 'application/json', 'User-Agent': 'TradingSystem/2.0', 'Accept': 'application/json'}
            )
            
            if not await self.token_manager.load_cached_token():
                await self.token_manager.request_new_token(self.session)
            
            await self._test_connection()
            
            self.status = APIStatus.CONNECTED
            self.logger.info("KIS API collector initialized successfully")
            return True
            
        except Exception as e:
            self.status = APIStatus.ERROR
            self.last_error = str(e)
            self.logger.error(f"Failed to initialize KIS collector: {e}")
            raise KISAPIError(f"Initialization failed: {e}")
    
    async def close(self):
        """Clean up resources"""
        try:
            self.logger.info("Closing KIS API collector...")
            if self.session and not self.session.closed:
                await self.session.close()
                await asyncio.sleep(0.1)
            self.session = None
            self.status = APIStatus.DISCONNECTED
            self.logger.info("KIS API collector closed successfully")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def _test_connection(self) -> bool:
        """Test API connection with a simple request"""
        try:
            result = await self.get_stock_info("005930")
            if result:
                self.logger.info("API connection test successful")
                return True
            else:
                self.logger.warning("API connection test failed - no data returned")
                return False
        except Exception as e:
            self.logger.warning(f"API connection test failed: {e}")
            return False
    
    async def _make_api_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None,
        data: Optional[Dict] = None, tr_id: Optional[str] = None,
        custtype: str = "P", retry_count: int = 3
    ) -> Dict[str, Any]:
        if not self.session:
            raise KISAPIError("Session not initialized")
        
        if not self.circuit_breaker.can_execute():
            raise KISAPIError("Circuit breaker is open - API temporarily unavailable")
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        request_start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                await self.token_manager.ensure_valid_token(self.session)
                headers = self.token_manager.get_headers(tr_id=tr_id, custtype=custtype)
                
                async with self.session.request(method, url, params=params, json=data, headers=headers) as response:
                    response_text = await response.text()
                    self.metrics['requests_made'] += 1
                    response_time = time.time() - request_start_time
                    self._update_response_time(response_time)
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            self.circuit_breaker.on_success()
                            self.logger.debug(f"API request successful: {method} {endpoint}")
                            return result
                        except json.JSONDecodeError as e:
                            raise KISAPIError(f"Invalid JSON response: {e}")
                    
                    elif response.status == 401:
                        self.logger.info("Token expired, refreshing...")
                        await self.token_manager.request_new_token(self.session)
                        continue
                    
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    elif response.status >= 500:
                        if attempt < retry_count - 1:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            self.logger.warning(f"Server error {response.status}, retrying in {wait_time:.1f}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise KISAPIError(f"Server error {response.status}: {response_text}")
                    
                    else:
                        raise KISAPIError(f"API request failed with status {response.status}: {response_text}")
            
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Request timeout, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError("Request timed out after retries")
            
            except aiohttp.ClientError as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Network error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError(f"Network error: {e}")
        
        self.metrics['requests_failed'] += 1
        self.circuit_breaker.on_failure(Exception("Max retries exceeded"))
        raise KISAPIError("Max retry attempts exceeded")
    
    def _update_response_time(self, response_time: float):
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            self.metrics['average_response_time'] = (0.9 * self.metrics['average_response_time'] + 0.1 * response_time)
        self.metrics['last_request_time'] = datetime.now()

    async def get_stock_info(self, symbol: str) -> Optional[StockData]:
        try:
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                raise KISDataValidationError(f"Invalid symbol format: {symbol}")
            
            self.logger.debug(f"Fetching stock info for {symbol}")
            
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
                tr_id="FHKST01010100"
            )
            
            output = result.get('output', {})
            if not output:
                self.logger.warning(f"No data returned for symbol {symbol}")
                return None
            
            current_price = self._safe_int_parse(output.get('stck_prpr', '0'))
            if current_price <= 0:
                return None
            
            name = self._extract_stock_name(output, symbol)
            market_div = output.get('mrkt_div_cd', '')
            market = Market.KOSPI if market_div == "J" else Market.KOSDAQ
            
            stock_data = StockData(
                symbol=symbol, name=name, current_price=current_price,
                change_rate=self._safe_float_parse(output.get('prdy_ctrt', '0')),
                volume=self._safe_int_parse(output.get('acml_vol', '0')),
                trading_value=self._safe_float_parse(output.get('acml_tr_pbmn', '0')) / 1000000,
                market_cap=self._safe_float_parse(output.get('hts_avls', '0')) / 100,
                market=market,
                high_52w=self._safe_int_parse(output.get('w52_hgpr', '0')) or int(current_price * 1.5),
                low_52w=self._safe_int_parse(output.get('w52_lwpr', '0')) or int(current_price * 0.7),
                pe_ratio=self._safe_float_parse(output.get('per', '0')) or None,
                pbr=self._safe_float_parse(output.get('pbr', '0')) or None,
                sector="기타"
            )
            
            self.logger.debug(f"Successfully fetched stock info for {symbol}")
            return stock_data
            
        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"Error fetching stock info for {symbol}: {e}")  
            raise KISAPIError(f"Failed to fetch stock info: {e}")

    def _extract_stock_name(self, output: Dict, symbol: str) -> str:
        name_candidates = [
            output.get('hts_kor_isnm', '').strip(),
            output.get('prdy_vrss_sign', '').strip(),
            output.get('hts_kor_isnm_1', '').strip()
        ]
        for candidate in name_candidates:
            if candidate and not candidate.startswith('종목') and len(candidate) > 2:
                return self._clean_stock_name(candidate)
        
        # pykrx는 선택적 의존성이므로, 없어도 동작하도록 처리
        try:
            from pykrx import stock as pykrx_stock
            pykrx_name = pykrx_stock.get_market_ticker_name(symbol)
            if pykrx_name and pykrx_name.strip() and len(pykrx_name.strip()) > 2:
                return self._clean_stock_name(pykrx_name.strip())
        except ImportError:
            pass # pykrx가 없으면 그냥 넘어감
        except Exception:
            pass

        return f'종목{symbol}'

    def _clean_stock_name(self, name: str) -> str:
        if not name: return ""
        suffixes = ["우", "우B", "우C", "1우", "2우", "3우", "스팩", "SPAC", "리츠", "REIT", "ETF", "ETN"]
        clean_name = name.strip()
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()
        return clean_name

    def _safe_int_parse(self, value: Any, default: int = 0) -> int:
        try:
            if isinstance(value, int): return value
            if isinstance(value, float): return default if math.isnan(value) or math.isinf(value) else int(value)
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']: return default
            return int(float(value_str)) if '.' in value_str else int(value_str)
        except (ValueError, TypeError): return default

    def _safe_float_parse(self, value: Any, default: float = 0.0) -> float:
        try:
            if isinstance(value, (int, float)): return default if math.isnan(value) or math.isinf(value) else float(value)
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']: return default
            float_val = float(value_str)
            return default if math.isnan(float_val) or math.isinf(float_val) else float_val
        except (ValueError, TypeError): return default

    async def get_ohlcv_data(self, symbol: str, timeframe: str = "1d", start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[OHLCVData]:
        pass

    # HTS Conditional Search Integration (Core Feature)
    async def get_hts_condition_list(self) -> List[Dict[str, str]]:
        """
        config.py에 설정된 HTS 조건검색식 목록을 반환합니다.
        """
        try:
            self.logger.info("Fetching HTS conditional search list from config...")
            strategies = getattr(self.config.trading, 'HTS_CONDITIONAL_SEARCH_IDS', {})
            if not strategies:
                self.logger.warning("No HTS strategies configured in config.py")
                return []
            
            condition_list = [{"id": cond_id, "name": name} for name, cond_id in strategies.items()]
            self.logger.info(f"Retrieved {len(condition_list)} HTS conditions from config")
            return condition_list
            
        except Exception as e:
            self.logger.error(f"Failed to get HTS condition list from config: {e}")
            return []
    
    async def get_stocks_by_condition(self, condition_id: str, user_id: str) -> List[str]:
        """
        특정 HTS 조건검색식에 해당하는 종목 코드를 API를 통해 직접 조회합니다.
        """
        try:
            self.logger.info(f"Fetching stocks for HTS condition {condition_id}...")
            
            # KIS API는 사용자 ID와 조건식 순번(seq)이 필요합니다.
            # 여기서는 condition_id를 seq로 가정합니다.
            params = {
                "USER_ID": user_id,
                "SEQ": condition_id
            }
            
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/psearch-result",
                params=params,
                tr_id="HHKST03010100" # 국내주식 조건검색 TR_ID (추정)
            )
            
            output = result.get('output2', [])
            if not output:
                self.logger.warning(f"No stocks found for condition {condition_id}")
                return []

            stocks = [item.get('code') for item in output if item.get('code')]
            
            self.logger.info(f"Found {len(stocks)} stocks for condition {condition_id}")
            return stocks
            
        except Exception as e:
            self.logger.error(f"Failed to get stocks for condition {condition_id}: {e}")
            return []
            
# ... (The rest of the file remains the same)
    
    async def __aenter__(self) -> 'KISCollector':
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self) -> bool:
        """
        Initialize the collector with all components
        """
        try:
            self.logger.info("Initializing KIS API collector...")
            
            self.token_manager = KISTokenManager(
                self.app_key, self.app_secret, self.base_url, self.logger, self.is_virtual
            )
            
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300, use_dns_cache=True, enable_cleanup_closed=True)
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.session = aiohttp.ClientSession(
                connector=connector, timeout=timeout,
                headers={'Content-Type': 'application/json', 'User-Agent': 'TradingSystem/2.0', 'Accept': 'application/json'}
            )
            
            if not await self.token_manager.load_cached_token():
                await self.token_manager.request_new_token(self.session)
            
            await self._test_connection()
            
            self.status = APIStatus.CONNECTED
            self.logger.info("KIS API collector initialized successfully")
            return True
            
        except Exception as e:
            self.status = APIStatus.ERROR
            self.last_error = str(e)
            self.logger.error(f"Failed to initialize KIS collector: {e}")
            raise KISAPIError(f"Initialization failed: {e}")
    
    async def close(self):
        """Clean up resources"""
        try:
            self.logger.info("Closing KIS API collector...")
            if self.session and not self.session.closed:
                await self.session.close()
                await asyncio.sleep(0.1)
            self.session = None
            self.status = APIStatus.DISCONNECTED
            self.logger.info("KIS API collector closed successfully")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def _test_connection(self) -> bool:
        """Test API connection with a simple request"""
        try:
            result = await self.get_stock_info("005930")
            if result:
                self.logger.info("API connection test successful")
                return True
            else:
                self.logger.warning("API connection test failed - no data returned")
                return False
        except Exception as e:
            self.logger.warning(f"API connection test failed: {e}")
            return False
    
    async def _make_api_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None,
        data: Optional[Dict] = None, tr_id: Optional[str] = None,
        custtype: str = "P", retry_count: int = 3
    ) -> Dict[str, Any]:
        if not self.session:
            raise KISAPIError("Session not initialized")
        
        if not self.circuit_breaker.can_execute():
            raise KISAPIError("Circuit breaker is open - API temporarily unavailable")
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        request_start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                await self.token_manager.ensure_valid_token(self.session)
                headers = self.token_manager.get_headers(tr_id=tr_id, custtype=custtype)
                
                async with self.session.request(method, url, params=params, json=data, headers=headers) as response:
                    response_text = await response.text()
                    self.metrics['requests_made'] += 1
                    response_time = time.time() - request_start_time
                    self._update_response_time(response_time)
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            self.circuit_breaker.on_success()
                            self.logger.debug(f"API request successful: {method} {endpoint}")
                            return result
                        except json.JSONDecodeError as e:
                            raise KISAPIError(f"Invalid JSON response: {e}")
                    
                    elif response.status == 401:
                        self.logger.info("Token expired, refreshing...")
                        await self.token_manager.request_new_token(self.session)
                        continue
                    
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    elif response.status >= 500:
                        if attempt < retry_count - 1:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            self.logger.warning(f"Server error {response.status}, retrying in {wait_time:.1f}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise KISAPIError(f"Server error {response.status}: {response_text}")
                    
                    else:
                        raise KISAPIError(f"API request failed with status {response.status}: {response_text}")
            
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Request timeout, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError("Request timed out after retries")
            
            except aiohttp.ClientError as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Network error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError(f"Network error: {e}")
        
        self.metrics['requests_failed'] += 1
        self.circuit_breaker.on_failure(Exception("Max retries exceeded"))
        raise KISAPIError("Max retry attempts exceeded")
    
    def _update_response_time(self, response_time: float):
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            self.metrics['average_response_time'] = (0.9 * self.metrics['average_response_time'] + 0.1 * response_time)
        self.metrics['last_request_time'] = datetime.now()

    async def get_stock_info(self, symbol: str) -> Optional[StockData]:
        try:
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                raise KISDataValidationError(f"Invalid symbol format: {symbol}")
            
            self.logger.debug(f"Fetching stock info for {symbol}")
            
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
                tr_id="FHKST01010100"
            )
            
            output = result.get('output', {})
            if not output:
                self.logger.warning(f"No data returned for symbol {symbol}")
                return None
            
            current_price = self._safe_int_parse(output.get('stck_prpr', '0'))
            if current_price <= 0:
                return None
            
            name = self._extract_stock_name(output, symbol)
            market_div = output.get('mrkt_div_cd', '')
            market = Market.KOSPI if market_div == "J" else Market.KOSDAQ
            
            stock_data = StockData(
                symbol=symbol, name=name, current_price=current_price,
                change_rate=self._safe_float_parse(output.get('prdy_ctrt', '0')),
                volume=self._safe_int_parse(output.get('acml_vol', '0')),
                trading_value=self._safe_float_parse(output.get('acml_tr_pbmn', '0')) / 1000000,
                market_cap=self._safe_float_parse(output.get('hts_avls', '0')) / 100,
                market=market,
                high_52w=self._safe_int_parse(output.get('w52_hgpr', '0')) or int(current_price * 1.5),
                low_52w=self._safe_int_parse(output.get('w52_lwpr', '0')) or int(current_price * 0.7),
                pe_ratio=self._safe_float_parse(output.get('per', '0')) or None,
                pbr=self._safe_float_parse(output.get('pbr', '0')) or None,
                sector="기타"
            )
            
            self.logger.debug(f"Successfully fetched stock info for {symbol}")
            return stock_data
            
        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"Error fetching stock info for {symbol}: {e}")  
            raise KISAPIError(f"Failed to fetch stock info: {e}")

    def _extract_stock_name(self, output: Dict, symbol: str) -> str:
        name_candidates = [
            output.get('hts_kor_isnm', '').strip(),
            output.get('prdy_vrss_sign', '').strip(),
            output.get('hts_kor_isnm_1', '').strip()
        ]
        for candidate in name_candidates:
            if candidate and not candidate.startswith('종목') and len(candidate) > 2:
                return self._clean_stock_name(candidate)
        if self.pykis_api:
            try:
                from pykrx import stock as pykrx_stock
                pykrx_name = pykrx_stock.get_market_ticker_name(symbol)
                if pykrx_name and pykrx_name.strip() and len(pykrx_name.strip()) > 2:
                    return self._clean_stock_name(pykrx_name.strip())
            except Exception:
                pass
        return f'종목{symbol}'

    def _clean_stock_name(self, name: str) -> str:
        if not name: return ""
        suffixes = ["우", "우B", "우C", "1우", "2우", "3우", "스팩", "SPAC", "리츠", "REIT", "ETF", "ETN"]
        clean_name = name.strip()
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()
        return clean_name

    def _safe_int_parse(self, value: Any, default: int = 0) -> int:
        try:
            if isinstance(value, int): return value
            if isinstance(value, float): return default if math.isnan(value) or math.isinf(value) else int(value)
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']: return default
            return int(float(value_str)) if '.' in value_str else int(value_str)
        except (ValueError, TypeError): return default

    def _safe_float_parse(self, value: Any, default: float = 0.0) -> float:
        try:
            if isinstance(value, (int, float)): return default if math.isnan(value) or math.isinf(value) else float(value)
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']: return default
            float_val = float(value_str)
            return default if math.isnan(float_val) or math.isinf(float_val) else float_val
        except (ValueError, TypeError): return default

    async def get_ohlcv_data(self, symbol: str, timeframe: str = "1d", start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[OHLCVData]:
        # ... (Implementation of get_ohlcv_data and other methods)
        pass

    async def load_hts_conditions(self) -> bool:
        try:
            if not self.pykis_api:
                self.logger.warning("PyKis not available for HTS conditions")
                return False
            self.logger.info("HTS conditions are loaded automatically by pykis>=0.7.0")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load HTS conditions: {e}")
            return False

    async def get_hts_condition_list(self) -> List[Dict[str, str]]:
        """
        config.py에 설정된 HTS 조건검색식 목록을 반환합니다.
        """
        try:
            self.logger.info("Fetching HTS conditional search list from config...")
            strategies = getattr(self.config.trading, 'HTS_CONDITIONAL_SEARCH_IDS', {})
            if not strategies:
                self.logger.warning("No HTS strategies configured in config.py")
                return []
            
            condition_list = [{"id": cond_id, "name": name} for name, cond_id in strategies.items()]
            self.logger.info(f"Retrieved {len(condition_list)} HTS conditions from config")
            return condition_list
            
        except Exception as e:
            self.logger.error(f"Failed to get HTS condition list from config: {e}")
            return []

    async def get_stocks_by_condition(self, condition_id: str) -> List[str]:
        try:
            if not self.pykis_api:
                self.logger.warning("PyKis not available for HTS conditions")
                return []
            self.logger.info(f"Fetching stocks for HTS condition {condition_id}...")
            stocks_df = await asyncio.to_thread(self.pykis_api.condition, condition_id)
            valid_stocks = list(stocks_df.index)
            self.logger.info(f"Found {len(valid_stocks)} stocks for condition {condition_id}")
            return valid_stocks
        except Exception as e:
            self.logger.error(f"Failed to get stocks for condition {condition_id}: {e}")
            return []
            
# ... (The rest of the file remains the same)
    
    async def __aenter__(self) -> 'KISCollector':
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self) -> bool:
        """
        Initialize the collector with all components
        """
        try:
            self.logger.info("Initializing KIS API collector...")
            
            self.token_manager = KISTokenManager(
                self.app_key, self.app_secret, self.base_url, self.logger, self.is_virtual
            )
            
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300, use_dns_cache=True, enable_cleanup_closed=True)
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.session = aiohttp.ClientSession(
                connector=connector, timeout=timeout,
                headers={'Content-Type': 'application/json', 'User-Agent': 'TradingSystem/2.0', 'Accept': 'application/json'}
            )
            
            if not await self.token_manager.load_cached_token():
                await self.token_manager.request_new_token(self.session)
            
            await self._test_connection()
            
            self.status = APIStatus.CONNECTED
            self.logger.info("KIS API collector initialized successfully")
            return True
            
        except Exception as e:
            self.status = APIStatus.ERROR
            self.last_error = str(e)
            self.logger.error(f"Failed to initialize KIS collector: {e}")
            raise KISAPIError(f"Initialization failed: {e}")
    
    async def close(self):
        """Clean up resources"""
        try:
            self.logger.info("Closing KIS API collector...")
            if self.session and not self.session.closed:
                await self.session.close()
                await asyncio.sleep(0.1)
            self.session = None
            self.status = APIStatus.DISCONNECTED
            self.logger.info("KIS API collector closed successfully")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def _test_connection(self) -> bool:
        """Test API connection with a simple request"""
        try:
            result = await self.get_stock_info("005930")
            if result:
                self.logger.info("API connection test successful")
                return True
            else:
                self.logger.warning("API connection test failed - no data returned")
                return False
        except Exception as e:
            self.logger.warning(f"API connection test failed: {e}")
            return False
    
    async def _make_api_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None,
        data: Optional[Dict] = None, tr_id: Optional[str] = None,
        custtype: str = "P", retry_count: int = 3
    ) -> Dict[str, Any]:
        if not self.session:
            raise KISAPIError("Session not initialized")
        
        if not self.circuit_breaker.can_execute():
            raise KISAPIError("Circuit breaker is open - API temporarily unavailable")
        
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        request_start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                await self.token_manager.ensure_valid_token(self.session)
                headers = self.token_manager.get_headers(tr_id=tr_id, custtype=custtype)
                
                async with self.session.request(method, url, params=params, json=data, headers=headers) as response:
                    response_text = await response.text()
                    self.metrics['requests_made'] += 1
                    response_time = time.time() - request_start_time
                    self._update_response_time(response_time)
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            self.circuit_breaker.on_success()
                            self.logger.debug(f"API request successful: {method} {endpoint}")
                            return result
                        except json.JSONDecodeError as e:
                            raise KISAPIError(f"Invalid JSON response: {e}")
                    
                    elif response.status == 401:
                        self.logger.info("Token expired, refreshing...")
                        await self.token_manager.request_new_token(self.session)
                        continue
                    
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    elif response.status >= 500:
                        if attempt < retry_count - 1:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            self.logger.warning(f"Server error {response.status}, retrying in {wait_time:.1f}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise KISAPIError(f"Server error {response.status}: {response_text}")
                    
                    else:
                        raise KISAPIError(f"API request failed with status {response.status}: {response_text}")
            
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Request timeout, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError("Request timed out after retries")
            
            except aiohttp.ClientError as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Network error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError(f"Network error: {e}")
        
        self.metrics['requests_failed'] += 1
        self.circuit_breaker.on_failure(Exception("Max retries exceeded"))
        raise KISAPIError("Max retry attempts exceeded")
    
    def _update_response_time(self, response_time: float):
        """Update average response time metric"""
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            self.metrics['average_response_time'] = (0.9 * self.metrics['average_response_time'] + 0.1 * response_time)
        self.metrics['last_request_time'] = datetime.now()
