#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/kis_collector.py

Production-Ready KIS (Korea Investment & Securities) API Collector
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

# Third-party imports - PyKis API 통합
PYKIS_AVAILABLE = False
Api = None

try:
    # PyKis 모듈 동적 임포트 시도
    import importlib
    pykis_module = importlib.import_module('pykis')
    
    # 다양한 API 클래스명 시도
    possible_classes = ['Api', 'KisApi', 'PyKis', 'Client']
    for class_name in possible_classes:
        if hasattr(pykis_module, class_name):
            Api = getattr(pykis_module, class_name)
            PYKIS_AVAILABLE = True
            print(f"SUCCESS: PyKis {class_name} imported successfully")
            break
    
    if not PYKIS_AVAILABLE:
        print("WARNING: PyKis module found but no compatible API class detected")
        # 사용 가능한 속성 목록 출력
        available_attrs = [attr for attr in dir(pykis_module) if not attr.startswith('_')]
        print(f"Available PyKis attributes: {available_attrs}")
        
except ImportError as e:
    print(f"INFO: PyKis module not available: {e}")
    print("INFO: Fallback mode activated - using HTTP client for KIS API")
except Exception as e:
    print(f"ERROR: Unexpected error loading PyKis: {e}")
    
# Local imports
from utils.logger import get_logger
from utils.http_client import HTTPSessionManager, KISHTTPConfig, RetryableHTTPError, NonRetryableHTTPError

# Enums for type safety
class Market(Enum):
    """Market classification"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KONEX = "KONEX"

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

def validate_symbol_format(symbol: str) -> bool:
    """
    종목 코드 형식 검증 공통 함수

    Args:
        symbol: 6자리 종목 코드

    Returns:
        bool: 유효한 형식이면 True

    Raises:
        KISDataValidationError: 잘못된 형식
    """
    if not symbol or len(symbol) != 6:
        raise KISDataValidationError(f"Invalid symbol format: {symbol}")

    # Check if it's a valid Korean stock symbol (6 digits) or handle special cases
    if not symbol.isdigit():
        # For symbols like "0023A0", check if it might be a legitimate special security type
        # Special securities can have letters (e.g., rights, warrants, ETNs)
        # Pattern: NNNNXX where N=digit, X=digit or letter
        if not (len(symbol) == 6 and symbol[:4].isdigit()):
            raise KISDataValidationError(f"Invalid symbol format: {symbol}")

        # Additional validation for 5th and 6th characters - can be digit or letter
        pos_5_6 = symbol[4:6]
        if not all(c.isalnum() for c in pos_5_6):
            raise KISDataValidationError(f"Invalid symbol format: {symbol}")

        import logging
        logger = logging.getLogger("KISCollector")
        logger.info(f"✅ Special security symbol validated: {symbol}")

    return True

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
        # Validate symbol format - allow special securities like 0023A0
        if not self.symbol or len(self.symbol) != 6:
            raise ValueError(f"Invalid symbol format: {self.symbol}")

        # Check if it's a valid Korean stock symbol (6 digits) or handle special cases
        if not self.symbol.isdigit():
            # For symbols like "0023A0", check if it might be a legitimate special security type
            # Special securities can have letters (e.g., rights, warrants, ETNs)
            # Pattern: NNNNXX where N=digit, X=digit or letter
            if not (len(self.symbol) == 6 and self.symbol[:4].isdigit()):
                raise ValueError(f"Invalid symbol format: {self.symbol}")

            # Additional validation for 5th and 6th characters - can be digit or letter
            pos_5_6 = self.symbol[4:6]
            if not all(c.isalnum() for c in pos_5_6):
                raise ValueError(f"Invalid symbol format: {self.symbol}")

            import logging
            logger = logging.getLogger("KISCollector")
            logger.info(f"✅ Special security symbol validated: {self.symbol}")
        if self.current_price <= 0:
            raise ValueError(f"Invalid price: {self.current_price}")
        if self.volume < 0:
            raise ValueError(f"Invalid volume: {self.volume}")

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
    
    # Compatibility properties for AnalysisEngine
    @property
    def date(self) -> datetime:
        """Date property for backward compatibility"""
        return self.datetime
    
    @property
    def open(self) -> int:
        """Open price property for backward compatibility"""
        return self.open_price
    
    @property  
    def high(self) -> int:
        """High price property for backward compatibility"""
        return self.high_price
    
    @property
    def low(self) -> int:
        """Low price property for backward compatibility"""
        return self.low_price
    
    @property
    def close(self) -> int:
        """Close price property for backward compatibility"""
        return self.close_price

# Rate limiter for API compliance
class RateLimiter:
    """Token bucket rate limiter for KIS API (20 requests/second)"""
    
    def __init__(self, max_requests: int = 20, time_window: int = 1):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
        
    async def acquire(self) -> bool:
        """Acquire rate limit permission with timeout protection"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use timeout with asyncio.wait_for to protect the entire lock operation
                async def lock_operation():
                    async with self._lock:
                        now = time.time()
                        
                        # Remove old requests outside time window
                        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
                        
                        if len(self.requests) < self.max_requests:
                            self.requests.append(now)
                            return True
                        
                        # Calculate wait time (limit to prevent infinite waiting)
                        oldest_request = min(self.requests)
                        wait_time = min(self.time_window - (now - oldest_request), 2.0)  # Max 2 seconds
                        
                        if wait_time > 0:
                            # Wait outside the lock to prevent blocking other requests
                            pass
                        else:
                            # Force acquire if wait time is 0 or negative
                            self.requests.append(now)
                            return True
                
                result = await asyncio.wait_for(lock_operation(), timeout=5.0)
                if result:
                    return True
                
                # Wait outside the lock if needed
                if 'wait_time' in locals() and wait_time > 0:
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                else:
                    return True
                    
            except (asyncio.TimeoutError, asyncio.CancelledError):
                retry_count += 1
                if retry_count >= max_retries:
                    # Force return True to prevent blocking the system
                    return True
                await asyncio.sleep(0.1)  # Brief pause before retry
        
        return True  # Fallback: allow the request

class KISTokenManager:
    """Enhanced token manager with file-based caching and auto-refresh"""
    
    def __init__(self, app_key: str, app_secret: str, base_url: str, logger: logging.Logger):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.logger = logger
        
        # Token state
        self.access_token: Optional[str] = None
        self.token_expired: Optional[datetime] = None
        self.refresh_threshold = timedelta(hours=1)  # Refresh 1 hour before expiry
        
        # File-based token cache
        import os
        self.token_cache_file = os.path.join("data", "kis_token_cache.json")
        os.makedirs("data", exist_ok=True)
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Load cached token on initialization
        self._load_cached_token()
    
    async def request_new_token(self, session: aiohttp.ClientSession) -> bool:
        """Request new access token with comprehensive error handling"""
        async with self._lock:
            try:
                self.logger.info("🔑 새 액세스 토큰 요청 중...")
                
                endpoint = "/oauth2/tokenP"
                url = f"{self.base_url}{endpoint}"

                payload = {
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret
                }
                
                headers = {
                    'content-type': 'application/json'
                }

                # Make request with timeout
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()

                    self.logger.debug(f"KIS API 응답 상태: {response.status}")
                    self.logger.debug(f"KIS API 응답 헤더: {dict(response.headers)}")
                    self.logger.debug(f"KIS API 응답 내용 (처음 500자): {response_text[:500]}")

                    # HTML 에러 페이지 감지
                    if response_text.strip().startswith('<'):
                        error_msg = f"KIS API가 HTML 에러 페이지를 반환했습니다. URL: {url}, Status: {response.status}"
                        self.logger.error(error_msg)
                        self.logger.error(f"HTML 내용: {response_text[:1000]}")
                        raise KISAPIError(error_msg)

                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            
                            # KIS API /oauth2/tokenP에서 access_token을 직접 반환
                            if 'access_token' in result:
                                access_token = result['access_token']
                                expires_in = result.get('expires_in', 86400)  # 기본 24시간
                                self.logger.info(f"✅ JWT Access token 획득: {access_token[:20]}...")

                                # KIS API access_token 설정
                                self.access_token = access_token
                                # expires_in 초 후 만료 (약간의 여유시간 제거)
                                self.token_expired = datetime.now() + timedelta(seconds=expires_in - 300)  # 5분 여유

                                # 토큰을 파일에 캐시
                                self._save_token_to_cache()

                                self.logger.info(f"✅ 새 JWT 액세스 토큰 획득 완료 (만료: {self.token_expired})")
                                return True
                            else:
                                self.logger.error(f"응답에서 access_token을 찾을 수 없습니다: {list(result.keys())}")
                                raise KISAuthenticationError("Access token not found in response")
                            
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON 파싱 실패: {str(e)}")
                            self.logger.error(f"서버 응답: {response_text[:1000]}")
                            raise KISAuthenticationError(f"Invalid JSON response. Server sent: {response_text[:1000]}")

                    elif response.status == 401:
                        self.logger.error(f"인증 실패 (401): {response_text}")
                        raise KISAuthenticationError(f"Authentication failed: {response_text}")
                    elif response.status == 429:
                        self.logger.error(f"API 호출 한도 초과 (429): {response_text}")
                        raise KISRateLimitError(f"Rate limit exceeded: {response_text}")
                    elif response.status >= 400:
                        self.logger.error(f"HTTP 에러 ({response.status}): {response_text}")
                        raise KISAPIError(f"HTTP {response.status} error: {response_text}")
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

    async def _get_access_token_with_approval_key(self, session: aiohttp.ClientSession, approval_key: str) -> Optional[str]:
        """Approval key를 사용하여 실제 access token 요청"""
        try:
            self.logger.info("🔑 Approval key로 access token 요청 중...")

            endpoint = "/oauth2/token"
            url = f"{self.base_url}{endpoint}"

            payload = {
                "grant_type": "authorization_code",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "approval_key": approval_key
            }

            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'User-Agent': 'TradingSystem/2.0',
                'Accept': 'application/json'
            }

            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                response_text = await response.text()

                self.logger.debug(f"Access token 응답 상태: {response.status}")
                self.logger.debug(f"Access token 응답: {response_text[:500]}")

                if response.status == 200:
                    try:
                        result = json.loads(response_text)

                        if 'access_token' in result:
                            self.logger.info("✅ Access token 획득 성공!")
                            return result['access_token']
                        else:
                            self.logger.error(f"Access token이 응답에 없습니다: {list(result.keys())}")
                            return None

                    except json.JSONDecodeError as e:
                        self.logger.error(f"Access token 응답 JSON 파싱 실패: {str(e)}")
                        return None
                else:
                    self.logger.error(f"Access token 요청 실패: HTTP {response.status}")
                    self.logger.error(f"에러 응답: {response_text}")
                    return None

        except Exception as e:
            self.logger.error(f"Access token 요청 중 예외: {e}")
            return None

    def is_token_valid(self) -> bool:
        """Check if current token is valid and not near expiry"""
        if not self.access_token or self.token_expired is None:
            return False
        return datetime.now() < self.token_expired - self.refresh_threshold
    
    def get_headers(self, tr_id: Optional[str] = None, custtype: str = "P") -> Dict[str, str]:
        """Get API headers with optional transaction ID - KIS API 표준 준수"""
        if not self.access_token:
            raise KISAuthenticationError("No valid access token available")

        headers = {
            # KIS API: approval_key를 authorization 헤더에 전달
            'authorization': f'Bearer {self.access_token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'Content-Type': 'application/json; charset=utf-8'
        }

        if tr_id:
            headers['tr_id'] = tr_id
        if custtype:
            headers['custtype'] = custtype

        return headers
        
    async def ensure_valid_token(self, session: aiohttp.ClientSession, force_refresh: bool = False) -> bool:
        """Ensure we have a valid token, refresh if necessary"""
        if force_refresh:
            self.logger.info("🔄 토큰 강제 갱신 요청...")
            return await self.request_new_token(session)

        if self.is_token_valid():
            return True

        self.logger.info("토큰 만료 임박, 새로운 토큰 요청...")
        return await self.request_new_token(session)
    
    def _load_cached_token(self):
        """Load cached token from file"""
        try:
            import os
            if os.path.exists(self.token_cache_file):
                with open(self.token_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.access_token = cache_data.get('access_token')
                    if cache_data.get('token_expired'):
                        self.token_expired = datetime.fromisoformat(cache_data['token_expired'])
                    self.logger.info("캐시된 토큰 로드 완료")
        except Exception as e:
            self.logger.warning(f"토큰 캐시 로드 실패: {e}")
            self.access_token = None
            self.token_expired = None
    
    def _save_token_to_cache(self):
        """Save token to cache file"""
        try:
            import os
            cache_data = {
                'access_token': self.access_token,
                'token_expired': self.token_expired.isoformat() if self.token_expired else None
            }
            with open(self.token_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            self.logger.debug("토큰 캐시 저장 완료")
        except Exception as e:
            self.logger.warning(f"토큰 캐시 저장 실패: {e}")

class KISCollector:
    """Production-ready KIS API Collector with enterprise features"""
    
    def __init__(self, config, pykis_api: Any = None, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or get_logger("KISCollector")
        
        # API Configuration
        self.base_url = config.api.KIS_BASE_URL
        self.app_key = config.api.KIS_APP_KEY
        self.app_secret = config.api.KIS_APP_SECRET
        # 실거래 전용
        # PyKis API 설정 - 파라미터로 전달되거나 글로벌 Api 클래스 사용
        self.pykis_api = pykis_api if pykis_api is not None else Api
        self.use_pykis = PYKIS_AVAILABLE and (pykis_api is not None or Api is not None)
        self.api = self.pykis_api if self.use_pykis else None
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS API credentials not configured")
        
        # Core components
        self.token_manager = None
        self.http_session: Optional[HTTPSessionManager] = None
        self.rate_limiter = RateLimiter(max_requests=20, time_window=1)
        
        # Performance metrics
        self.metrics = {
            'requests_made': 0,
            'requests_failed': 0,
            'average_response_time': 0.0,
            'last_request_time': None
        }
        
        # Status
        self.status = APIStatus.DISCONNECTED
        self.last_error = None
        self.is_initialized = False
        
        # 중복 주문 방지용 (스레드 세이프)
        self.recent_orders = {}
        self._orders_lock = asyncio.Lock()
        
        # DB 연동을 위한 매니저 (AutoTrader에서 설정)
        self.db_manager = None
        
        self.logger.info("KISCollector 초기화 완료 (실거래 모드)")
    
    async def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """인증 헤더 생성"""
        try:
            if not self.token_manager:
                self.logger.error("토큰 매니저가 초기화되지 않았습니다.")
                return None
            
            session = await self.http_session.get_session()
            if not await self.token_manager.ensure_valid_token(session):
                self.logger.error("유효한 토큰을 가져올 수 없습니다.")
                return None
            
            return {
                'Authorization': f'Bearer {self.token_manager.access_token}',
                'appkey': self.app_key,
                'appsecret': self.app_secret,
                'Content-Type': 'application/json',
                'User-Agent': 'TradingSystem/2.0'
            }
        except Exception as e:
            self.logger.error(f"인증 헤더 생성 실패: {e}")
            return None
    
    async def __aenter__(self) -> 'KISCollector':
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self) -> bool:
        """Initialize the collector with all components"""
        try:
            self.logger.info("🚀 KIS API collector 초기화 중...")
            
            self.token_manager = KISTokenManager(
                self.app_key, self.app_secret, self.base_url, self.logger
            )
            
            # 개선된 HTTP 세션 관리자 초기화
            kis_config = KISHTTPConfig()
            self.http_session = HTTPSessionManager.get_instance("kis_api", kis_config)
            
            # 토큰 확인/획득 (캐시된 토큰이 유효하면 재사용)
            session = await self.http_session.get_session()
            await self.token_manager.ensure_valid_token(session)
            
            self.status = APIStatus.CONNECTED
            self.is_initialized = True
            self.logger.info("✅ KIS API collector 초기화 성공")
            return True
            
        except Exception as e:
            self.status = APIStatus.ERROR
            self.last_error = str(e)
            self.logger.error(f"❌ KIS collector 초기화 실패: {e}")
            raise KISAPIError(f"Initialization failed: {e}")
    
    async def close(self):
        """Clean up resources"""
        try:
            self.logger.info("KIS API collector 종료 중...")
            if self.http_session:
                await self.http_session.close()
            self.http_session = None
            self.is_initialized = False
            self.status = APIStatus.DISCONNECTED
            self.logger.info("✅ KIS API collector 종료 완료")
        except Exception as e:
            self.logger.warning(f"⚠️ 종료 중 오류: {e}")

    async def is_session_ready(self) -> bool:
        """Check if session is ready for API calls"""
        return (self.http_session is not None and
                self.is_initialized and
                self.status == APIStatus.CONNECTED)

    async def ensure_session_ready(self) -> bool:
        """Ensure session is ready, reinitialize if needed"""
        if not await self.is_session_ready():
            self.logger.warning("⚠️ KIS API 세션이 준비되지 않음 - 재초기화 시도...")
            try:
                return await self.initialize()
            except Exception as e:
                self.logger.error(f"❌ KIS API 세션 재초기화 실패: {e}")
                return False
        return True

    async def ensure_valid_token(self) -> bool:
        """토큰 유효성 확인 및 갱신"""
        if not self.token_manager:
            raise KISAPIError("Token manager not initialized")
        if not self.http_session:
            raise KISAPIError("HTTP session not initialized")
            
        session = await self.http_session.get_session()
        return await self.token_manager.ensure_valid_token(session)
    
    async def _make_api_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None,
        data: Optional[Dict] = None, tr_id: Optional[str] = None,
        custtype: str = "P", retry_count: int = 3, timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Make API request with proper error handling"""
        if not self.http_session:
            self.logger.error("❌ HTTP 세션이 초기화되지 않음 - initialize() 메서드 호출 필요")
            raise KISAPIError("HTTP session not initialized - call initialize() first")
        
        await self.rate_limiter.acquire()
        
        # URL 조합 시 중복 슬래시 방지
        if self.base_url.endswith('/') and endpoint.startswith('/'):
            url = f"{self.base_url[:-1]}{endpoint}"
        elif not self.base_url.endswith('/') and not endpoint.startswith('/'):
            url = f"{self.base_url}/{endpoint}"
        else:
            url = f"{self.base_url}{endpoint}"
        
        request_start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                session = await self.http_session.get_session()
                await self.token_manager.ensure_valid_token(session)
                headers = self.token_manager.get_headers(tr_id=tr_id, custtype=custtype)

                # Hashkey generation for ordering
                ORDERING_TR_IDS = ["VTTC0802U", "VTTC0801U", "TTTC0802U", "TTTC0801U", "VTTC0012U", "VTTC0011U"]
                if tr_id in ORDERING_TR_IDS and data:
                    headers['hashkey'] = await self._generate_hashkey(session, data)

                # 디버깅 로그 추가
                self.logger.debug(f"---> API Request [Attempt {attempt+1}/{retry_count}] ---")
                self.logger.debug(f"URL: {method} {url}")
                self.logger.debug(f"Headers: {headers}")
                self.logger.debug(f"Params: {params}")
                self.logger.debug(f"Data: {data}")
                self.logger.debug("--------------------------------------")
                
                request_kwargs = {
                    'params': params,
                    'json': data,
                    'headers': headers
                }

                # 타임아웃 설정 (개별 지정 시 우선 적용)
                request_kwargs = {
                    'params': params,
                    'json': data,
                    'headers': headers
                }
                
                if timeout_seconds is not None:
                    from aiohttp import ClientTimeout
                    request_kwargs['timeout'] = ClientTimeout(total=timeout_seconds)
                
                response = await self.http_session.request(method, url, **request_kwargs)
                
                self.metrics['requests_made'] += 1
                response_time = time.time() - request_start_time
                self._update_response_time(response_time)

                # API Response 로그 추가
                self.logger.debug(f"<--- API Response [Status: {response.status}] ---")
                self.logger.debug("--------------------------------------")
                
                if response.status == 200:
                    try:
                        result = await response.json()
                        await response.release()
                        
                        # rt_cd가 0이 아닌 경우, KIS API 레벨의 오류로 간주
                        if result.get('rt_cd') != '0':
                            error_msg = result.get('msg1', '')
                            error_code = result.get('msg_cd', '')
                            rt_cd = result.get('rt_cd', '')
                            full_error = f"rt_cd: {rt_cd}, msg_cd: {error_code}, msg1: {error_msg}"

                            # EGW00121 토큰 오류인 경우 토큰 갱신 시도
                            if error_code == 'EGW00121' or "token" in error_msg.lower():
                                if attempt < retry_count - 1:
                                    self.logger.warning(f"⚠️ 토큰 오류 감지, 강제 갱신 후 재시도 {attempt + 1}/{retry_count}: {error_msg}")
                                    session = await self.http_session.get_session()
                                    await self.token_manager.ensure_valid_token(session, force_refresh=True)
                                    continue
                                else:
                                    self.logger.error(f"❌ 토큰 갱신 재시도 한도 초과: {full_error}")
                                    raise KISAPIError(f"Token refresh failed after retries: {full_error}", response_data=result)

                            self.logger.warning(f"KIS API Error: {full_error}")
                            self.logger.debug(f"Full API response: {result}")
                            # 실패로 간주하고 재시도 로직을 탈 수 있도록 예외 발생
                            raise KISAPIError(f"KIS API returned error: {full_error}", response_data=result)

                        self.logger.debug(f"✅ API 요청 성공: {method} {endpoint}")
                        return result
                    except json.JSONDecodeError as e:
                        await response.release()
                        raise KISAPIError(f"Invalid JSON response: {e}")
                
                elif response.status == 401:
                    await response.release()
                    self.logger.info("토큰 만료, 새로고침 중...")
                    session = await self.http_session.get_session()
                    await self.token_manager.request_new_token(session)
                    continue
                
                elif response.status == 429:
                    await response.release()
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Rate limited, {wait_time}초 대기...")
                    await asyncio.sleep(wait_time)
                    continue
                
                elif response.status >= 500:
                    response_text = await response.text()
                    await response.release()
                    # Check if the 500 error is a disguised rate limit error
                    if "EGW00201" in response_text or "초당 거래건수를 초과하였습니다" in response_text:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited (disguised as 500), {wait_time}초 대기...")
                        await asyncio.sleep(wait_time)
                        continue
                    # Check if the 500 error is due to expired token
                    elif "기간이 만료된 token 입니다" in response_text or "EGW00123" in response_text:
                        self.logger.info("토큰 만료 감지 (HTTP 500), 새로고침 중...")
                        session = await self.http_session.get_session()
                        await self.token_manager.request_new_token(session)
                        continue

                    self.logger.error(f"KIS API 서버 오류 {response.status}: {response_text[:500]}")
                    self.logger.error(f"요청 URL: {method} {endpoint}")
                    self.logger.error(f"요청 파라미터: {params}")
                    self.logger.error(f"TR_ID: {tr_id}")
                    if attempt < retry_count - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(f"서버 오류 {response.status}, {wait_time:.1f}초 후 재시도...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise KISAPIError(f"Server error {response.status}: {response_text}")
                
                else:
                    response_text = await response.text()
                    await response.release()
                    raise KISAPIError(f"API request failed with status {response.status}: {response_text}")
                    
            except (RetryableHTTPError, NonRetryableHTTPError) as e:
                # HTTP session manager에서 이미 재시도를 처리했으므로 바로 예외 발생
                if isinstance(e, NonRetryableHTTPError):
                    raise KISAPIError(f"Non-retryable HTTP error: {e}")
                else:
                    raise KISNetworkError(f"HTTP error after retries: {e}")
            
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"예상치 못한 오류, {wait_time}초 후 재시도: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError(f"Unexpected error: {e}")
        
        self.metrics['requests_failed'] += 1
        raise KISAPIError("Max retry attempts exceeded")
    
    async def _make_api_request_with_pagination(
        self, method: str, endpoint: str, params: Optional[Dict] = None,
        data: Optional[Dict] = None, tr_id: Optional[str] = None,
        custtype: str = "P", retry_count: int = 3
    ) -> Dict[str, Any]:
        """Make API request with pagination support for condition search"""
        if not self.http_session:
            raise KISAPIError("HTTP session not initialized")
        
        await self.rate_limiter.acquire()
        
        # URL 조합 시 중복 슬래시 방지
        if self.base_url.endswith('/') and endpoint.startswith('/'):
            url = f"{self.base_url[:-1]}{endpoint}"
        elif not self.base_url.endswith('/') and not endpoint.startswith('/'):
            url = f"{self.base_url}/{endpoint}"
        else:
            url = f"{self.base_url}{endpoint}"
        
        request_start_time = time.time()
        
        for attempt in range(retry_count):
            try:
                session = await self.http_session.get_session()
                await self.token_manager.ensure_valid_token(session)
                headers = self.token_manager.get_headers(tr_id=tr_id, custtype=custtype)

                # Hashkey generation for ordering
                ORDERING_TR_IDS = ["VTTC0802U", "VTTC0801U", "TTTC0802U", "TTTC0801U", "VTTC0012U", "VTTC0011U"]
                if tr_id in ORDERING_TR_IDS and data:
                    headers['hashkey'] = await self._generate_hashkey(session, data)

                request_kwargs = {
                    'params': params,
                    'json': data,
                    'headers': headers
                }

                timeout_val = 10.0 # Pagination requests can be longer
                async with asyncio.timeout(timeout_val):
                    response = await self.http_session.request(method, url, **request_kwargs)
                
                self.metrics['requests_made'] += 1
                response_time = time.time() - request_start_time
                self._update_response_time(response_time)
                
                if response.status == 200:
                    try:
                        result = await response.json()
                        await response.release()
                        
                        # 페이지네이션 및 '결과 없음' 케이스 특별 처리
                        if result.get('rt_cd') != '0':
                            msg1 = result.get('msg1', '')
                            msg_cd = result.get('msg_cd', '')
                            
                            # "조회가 계속" (페이지네이션) 또는 "결과 없음" (MCA05918, 종목코드 오류)은 정상 응답으로 처리
                            if "조회가 계속" in msg1 or msg_cd == 'MCA05918' or "종목코드 오류입니다" in msg1:
                                self.logger.debug(f"ℹ️ KIS API 정보 메시지: {msg1}")
                                return result
                            else:
                                # 그 외의 다른 오류는 예외로 처리
                                self.logger.warning(f"KIS API Error: {msg1}")
                                raise KISAPIError(f"KIS API returned error: {msg1}", response_data=result)

                        self.logger.debug(f"✅ API 요청 성공: {method} {endpoint}")
                        return result
                    except json.JSONDecodeError as e:
                        await response.release()
                        raise KISAPIError(f"Invalid JSON response: {e}")
                
                elif response.status == 401:
                    await response.release()
                    self.logger.info("토큰 만료, 새로고침 중...")
                    session = await self.http_session.get_session()
                    await self.token_manager.request_new_token(session)
                    continue
                
                elif response.status == 429:
                    await response.release()
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Rate limited, {wait_time}초 대기...")
                    await asyncio.sleep(wait_time)
                    continue
                
                elif response.status >= 500:
                    response_text = await response.text()
                    await response.release()
                    # Check if the 500 error is a disguised rate limit error
                    if "EGW00201" in response_text or "초당 거래건수를 초과하였습니다" in response_text:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited (disguised as 500), {wait_time}초 대기...")
                        await asyncio.sleep(wait_time)
                        continue
                    # Check if the 500 error is due to expired token
                    elif "기간이 만료된 token 입니다" in response_text or "EGW00123" in response_text:
                        self.logger.info("토큰 만료 감지 (HTTP 500), 새로고침 중...")
                        session = await self.http_session.get_session()
                        await self.token_manager.request_new_token(session)
                        continue

                    self.logger.error(f"KIS API 서버 오류 {response.status}: {response_text[:500]}")
                    self.logger.error(f"요청 URL: {method} {endpoint}")
                    self.logger.error(f"요청 파라미터: {params}")
                    self.logger.error(f"TR_ID: {tr_id}")
                    if attempt < retry_count - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(f"서버 오류 {response.status}, {wait_time:.1f}초 후 재시도...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise KISAPIError(f"Server error {response.status}: {response_text}")
                
                else:
                    response_text = await response.text()
                    await response.release()
                    raise KISAPIError(f"API request failed with status {response.status}: {response_text}")
                    
            except (RetryableHTTPError, NonRetryableHTTPError) as e:
                # HTTP session manager에서 이미 재시도를 처리했으므로 바로 예외 발생
                if isinstance(e, NonRetryableHTTPError):
                    raise KISAPIError(f"Non-retryable HTTP error: {e}")
                else:
                    raise KISNetworkError(f"HTTP error after retries: {e}")
            
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"예상치 못한 오류, {wait_time}초 후 재시도: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError(f"Unexpected error: {e}")
        
        self.metrics['requests_failed'] += 1
        raise KISAPIError("Max retry attempts exceeded")
    
    def _update_response_time(self, response_time: float):
        """Update average response time metric"""
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            self.metrics['average_response_time'] = (0.9 * self.metrics['average_response_time'] + 0.1 * response_time)
        self.metrics['last_request_time'] = datetime.now()

    async def get_current_price(self, symbol: str) -> Optional[int]:
        """현재가만 간단히 조회"""
        try:
            # HTTP session 상태 체크 및 복구
            if not self.is_initialized or not hasattr(self, 'http_session') or not self.http_session:
                self.logger.info("🔄 KIS collector 재초기화 중...")
                await self.initialize()
            
            # 세션 오류 발생시 자동 복구
            try:
                stock_info = await self.get_stock_info(symbol)
                if stock_info:
                    return stock_info.current_price
            except Exception as session_error:
                if "HTTP session not initialized" in str(session_error):
                    self.logger.warning(f"🔄 {symbol} 세션 복구 중...")
                    await self.initialize()
                    # 재시도
                    stock_info = await self.get_stock_info(symbol)
                    if stock_info:
                        return stock_info.current_price
                else:
                    raise session_error
                    
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 현재가 조회 실패: {e}")
            return None

    async def get_stock_info(self, symbol: str) -> Optional[StockData]:
        """주식 정보 조회"""
        try:
            validate_symbol_format(symbol)
            
            # Ensure KIS collector is initialized before making API calls
            if not self.is_initialized:
                self.logger.info("🔄 KIS collector 초기화 중...")
                await self.initialize()
            
            self.logger.debug(f"📊 {symbol} 주식 정보 조회 중...")
            
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
                tr_id="FHKST01010100"
            )
            
            output = result.get('output', {})
            if not output:
                self.logger.warning(f"⚠️ {symbol} 데이터 없음")
                return None
            
            current_price = self._safe_int_parse(output.get('stck_prpr', '0'))
            if current_price <= 0:
                return None
            
            # 주식기본조회 API로 정확한 종목명 조회
            try:
                basic_info_result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/quotations/search-stock-info",
                    params={
                        "PDNO": symbol,
                        "PRDT_TYPE_CD": "300"  # 주식
                    },
                    tr_id="CTPF1002R"
                )
                
                # 기본조회 API 응답을 현재가 API 응답에 병합
                if basic_info_result and basic_info_result.get('rt_cd') == '0':
                    basic_output = basic_info_result.get('output', {})
                    if basic_output:
                        # 기본조회 API의 종목명 필드를 현재가 API 출력에 추가
                        output.update({
                            'prdt_abrv_name': basic_output.get('prdt_abrv_name', ''),
                            'prdt_name': basic_output.get('prdt_name', ''),
                        })
                        self.logger.debug(f"📝 {symbol} 기본조회 API에서 종목명 추가: {basic_output.get('prdt_abrv_name', 'N/A')}")
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} 주식기본조회 API 호출 실패, 현재가 API만 사용: {e}")
            
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
            
            self.logger.debug(f"✅ {symbol} 주식 정보 조회 성공")
            return stock_data
            
        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"❌ {symbol} 주식 정보 조회 실패: {e}")  
            raise KISAPIError(f"Failed to fetch stock info: {e}")

    def _extract_stock_name(self, output: Dict, symbol: str) -> str:
        """주식명 추출 - 개선된 버전"""
        # KIS API에서 종목명을 가져올 수 있는 필드들 (우선순위 순)
        name_candidates = [
            output.get('prdt_abrv_name', '').strip(),    # 주식기본조회 API 상품약어명 (최우선)
            output.get('prdt_name', '').strip(),         # 주식기본조회 API 상품명
            output.get('hts_kor_isnm', '').strip(),      # 한국어 종목명 (현재가 API)
            output.get('bstp_kor_isnm', '').strip(),     # 기본 한국어 종목명 (현재가 API)
            output.get('rprs_mrkt_kor_name', '').strip(), # 대표 시장 한국어명
            output.get('itms_nm', '').strip(),           # 종목명
            output.get('prdt_nm', '').strip(),           # 상품명 (현재가 API)
            output.get('hts_prdt_nm', '').strip(),       # HTS 상품명
            output.get('hts_kor_isnm_1', '').strip(),    # 한국어 종목명 대체1
            output.get('stck_shrn_iscd', '').strip()     # 종목 단축 코드
        ]
        
        # 유효한 종목명 찾기
        for candidate in name_candidates:
            if (candidate and 
                not candidate.startswith('종목') and 
                not candidate.isdigit() and  # 숫자만으로 구성되지 않음
                len(candidate) >= 2 and      # 최소 2글자 이상
                not candidate in ['+', '-', '0', '1', '2', '3', '4', '5']):  # 기호나 숫자가 아님
                cleaned_name = self._clean_stock_name(candidate)
                if cleaned_name and len(cleaned_name) >= 2:
                    self.logger.debug(f"📝 {symbol} 종목명 추출: '{cleaned_name}' (원본: '{candidate}')")
                    return cleaned_name
        
        # 모든 후보가 실패한 경우 - 더 상세한 로그와 함께
        self.logger.warning(f"⚠️ {symbol} 종목명 추출 실패. API 응답 데이터: {list(output.keys())[:10]}")
        self.logger.debug(f"📋 {symbol} 후보들: {name_candidates}")
        
        # API 응답 중 종목명 관련 필드들의 실제 값 출력
        name_related_fields = {}
        for key, value in output.items():
            if any(keyword in key.lower() for keyword in ['name', 'nm', 'isnm', 'kor']):
                name_related_fields[key] = value
        
        if name_related_fields:
            self.logger.debug(f"🔍 {symbol} 종목명 관련 필드들: {name_related_fields}")
        
        # API 응답에서 모든 필드를 더 포괄적으로 분석
        # 종목명일 가능성이 있는 모든 필드를 검사
        potential_name_fields = []
        for key, value in output.items():
            if value and isinstance(value, str):
                value_cleaned = str(value).strip()
                
                # 종목명 패턴 확인 (더 포괄적)
                is_korean = any(ord(char) >= 44032 and ord(char) <= 55203 for char in value_cleaned)  # 한글 포함
                is_english = any(char.isalpha() for char in value_cleaned)  # 영문 포함
                is_numeric_only = value_cleaned.replace('.', '').replace('-', '').replace('+', '').replace(',', '').isdigit()
                is_boolean = value_cleaned.lower() in ['y', 'n', 'true', 'false', '0', '1']
                is_code = value_cleaned.isdigit() and len(value_cleaned) == 6  # 종목코드 패턴
                
                if (value_cleaned and 
                    len(value_cleaned) >= 2 and len(value_cleaned) <= 50 and
                    (is_korean or is_english) and  # 한글 또는 영문 포함
                    not is_numeric_only and  # 숫자만이 아님
                    not is_boolean and  # 불린값이 아님
                    not is_code):  # 6자리 종목코드가 아님
                    
                    # 종목명일 가능성 점수 계산
                    score = 0
                    
                    # 한글이 포함되면 높은 점수
                    if is_korean:
                        score += 10
                    
                    # 'name', 'nm', 'isnm' 등이 키에 포함되면 높은 점수
                    if any(keyword in key.lower() for keyword in ['name', 'nm', 'isnm', 'kor']):
                        score += 20
                    
                    # 적절한 길이면 점수 추가
                    if 2 <= len(value_cleaned) <= 20:
                        score += 5
                    
                    # 불필요한 단어가 포함되면 점수 차감
                    if any(word in value_cleaned.lower() for word in ['krx', 'kospi', 'kosdaq', 'code']):
                        score -= 5
                    
                    # 일반적인 회사명 패턴이면 점수 추가
                    if any(pattern in value_cleaned for pattern in ['주식회사', '㈜', 'Co.', 'Corp', 'Inc']):
                        score += 3
                    
                    # ETF, REIT 등 특수 종목은 점수 추가 (유효한 종목명)
                    if any(suffix in value_cleaned for suffix in ['ETF', 'REIT', 'SPAC']):
                        score += 15
                    
                    potential_name_fields.append((key, value_cleaned, score))
        
        # 찾은 후보들을 점수와 함께 로그에 출력
        if potential_name_fields:
            # 점수 순으로 정렬
            potential_name_fields.sort(key=lambda x: x[2], reverse=True)
            
            self.logger.info(f"🔍 {symbol} 종목명 후보 필드들 (점수순):")
            for field_name, field_value, score in potential_name_fields:
                self.logger.info(f"   {field_name}: '{field_value}' (점수: {score})")
            
            # 가장 점수가 높은 후보 선택
            if potential_name_fields:
                field_name, stock_name, score = potential_name_fields[0]
                cleaned_name = self._clean_stock_name(stock_name)
                if cleaned_name and len(cleaned_name) >= 2:
                    self.logger.info(f"✅ {symbol} 종목명 발견: '{cleaned_name}' (필드: {field_name}, 점수: {score})")
                    return cleaned_name
        
        # 최종적으로 실패한 경우 None 반환
        self.logger.error(f"❌ {symbol} 종목명을 찾을 수 없습니다")
        return None

    def _clean_stock_name(self, name: str) -> str:
        """주식명 정리 - 개선된 버전"""
        if not name: return ""
        
        clean_name = name.strip()
        
        # 제거할 접미사들 (우선주, 특수 구분 등)
        suffixes_to_remove = [
            "우", "우B", "우C", "1우", "2우", "3우", "4우", "5우",
            "스팩", "SPAC", "리츠", "REIT", "ETF", "ETN",
            "주식회사", "(주)", "㈜", "코퍼레이션", "Corp", "Co.",
            "그룹", "홀딩스", "Holdings"
        ]
        
        # 접미사 제거
        for suffix in suffixes_to_remove:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()
        
        # 앞의 불필요한 접두사 제거
        prefixes_to_remove = ["(주)", "㈜"]
        for prefix in prefixes_to_remove:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):].strip()
        
        # 괄호 안의 내용 제거 (예: "삼성전자(주)" -> "삼성전자")
        import re
        clean_name = re.sub(r'\([^)]*\)', '', clean_name).strip()
        clean_name = re.sub(r'\[[^]]*\]', '', clean_name).strip()
        
        # 연속된 공백 제거
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        return clean_name

    def _safe_int_parse(self, value: Any, default: int = 0) -> int:
        """안전한 int 변환"""
        try:
            if isinstance(value, int): return value
            if isinstance(value, float): return default if math.isnan(value) or math.isinf(value) else int(value)
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']: return default
            return int(float(value_str)) if '.' in value_str else int(value_str)
        except (ValueError, TypeError): return default

    def _safe_float_parse(self, value: Any, default: float = 0.0) -> float:
        """안전한 float 변환"""
        try:
            if isinstance(value, (int, float)): return default if math.isnan(value) or math.isinf(value) else float(value)
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']: return default
            float_val = float(value_str)
            return default if math.isnan(float_val) or math.isinf(float_val) else float_val
        except (ValueError, TypeError): return default

    async def get_ohlcv_data(self, symbol: str, period: str = "D", count: int = 100) -> List[OHLCVData]:
        """OHLCV 데이터 조회 (페이지네이션 지원)"""
        try:
            validate_symbol_format(symbol)

            # 세션 상태 확인 및 재초기화
            if not await self.ensure_session_ready():
                raise KISAPIError(f"KIS API session not ready for {symbol}")

            self.logger.debug(f"📈 {symbol} OHLCV 데이터 조회 중 (요청: {count}개)...")
            
            all_ohlcv_data = []
            end_date = datetime.now().strftime('%Y%m%d')
            
            while len(all_ohlcv_data) < count:
                # KIS API는 한 번에 최대 100개의 데이터 포인트를 반환합니다.
                result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                    params={
                        "FID_COND_MRKT_DIV_CODE": "J",
                        "FID_INPUT_ISCD": symbol,
                        "FID_INPUT_DATE_1": "19900101", # 충분히 과거 날짜로 설정
                        "FID_INPUT_DATE_2": end_date,
                        "FID_PERIOD_DIV_CODE": period,
                        "FID_ORG_ADJ_PRC": "0"
                    },
                    tr_id="FHKST03010100"
                )
                
                output = result.get('output2', [])
                if not output:
                    self.logger.info(f"ℹ️ {symbol} 더 이상 조회할 OHLCV 데이터가 없습니다. (총 {len(all_ohlcv_data)}개 수집)")
                    break
                
                page_data = []
                for item in output:
                    try:
                        date_str = item.get('stck_bsop_date', '')
                        if not date_str or len(date_str) != 8:
                            continue
                        
                        chart_date = datetime.strptime(date_str, '%Y%m%d')
                        open_price = self._safe_int_parse(item.get('stck_oprc', '0'))
                        high_price = self._safe_int_parse(item.get('stck_hgpr', '0'))
                        low_price = self._safe_int_parse(item.get('stck_lwpr', '0'))
                        close_price = self._safe_int_parse(item.get('stck_clpr', '0'))
                        volume = self._safe_int_parse(item.get('acml_vol', '0'))
                        trade_amount = self._safe_int_parse(item.get('acml_tr_pbmn', '0'))
                        
                        if all(p > 0 for p in [open_price, high_price, low_price, close_price]):
                            page_data.append(OHLCVData(
                                symbol=symbol, datetime=chart_date, timeframe=period.lower(),
                                open_price=open_price, high_price=high_price, low_price=low_price,
                                close_price=close_price, volume=volume, trade_amount=trade_amount
                            ))
                    except Exception as item_error:
                        self.logger.debug(f"OHLCV 아이템 파싱 실패 {symbol}: {item_error}")
                        continue
                
                # 중복 제거 후 추가
                existing_dates = {d.datetime for d in all_ohlcv_data}
                new_data = [d for d in page_data if d.datetime not in existing_dates]
                
                if not new_data:
                    break # 새로운 데이터가 없으면 종료

                all_ohlcv_data.extend(new_data)
                
                # 다음 페이지 조회를 위해 end_date 업데이트
                oldest_date = min(d.datetime for d in new_data)
                end_date = (oldest_date - timedelta(days=1)).strftime('%Y%m%d')
                
                self.logger.debug(f"📄 {symbol} OHLCV 페이지 수집: {len(new_data)}개, 총: {len(all_ohlcv_data)}개")
                await asyncio.sleep(0.25) # Rate limit 준수

            # 날짜순 정렬 (최신순)
            all_ohlcv_data.sort(key=lambda x: x.datetime, reverse=True)
            
            final_data = all_ohlcv_data[:count]
            self.logger.debug(f"✅ {symbol} OHLCV {len(final_data)}개 조회 성공")
            return final_data
            
        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"❌ {symbol} OHLCV 데이터 조회 실패: {e}")
            raise KISAPIError(f"Failed to fetch OHLCV data: {e}")

    async def get_chart_data(self, symbol: str, period: str = "D", 
                           start_date: str = "", end_date: str = "",
                           adjust_price: bool = True) -> List[Dict]:
        """
        차트 데이터 조회 (ChartDataCollector와 호환)
        
        Args:
            symbol: 종목코드 (6자리)
            period: 차트 주기 ('D'=일봉, '1'=1분, '5'=5분, '15'=15분, '30'=30분, '60'=60분)
            start_date: 시작일 (YYYYMMDD, 공백시 최근 데이터)
            end_date: 종료일 (YYYYMMDD, 공백시 최근 데이터)
            adjust_price: 수정주가 여부 (True=수정주가, False=원주가)
            
        Returns:
            원시 차트 데이터 딕셔너리 리스트
        """
        try:
            validate_symbol_format(symbol)
            
            self.logger.debug(f"📊 {symbol} 차트 데이터 조회 ({period}, {start_date}-{end_date})")
            
            # 분봉과 일봉은 다른 API 엔드포인트 사용
            if period == "D":
                # 일봉 데이터
                result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                    params={
                        "FID_COND_MRKT_DIV_CODE": "J",
                        "FID_INPUT_ISCD": symbol,
                        "FID_INPUT_DATE_1": start_date,
                        "FID_INPUT_DATE_2": end_date,
                        "FID_PERIOD_DIV_CODE": "D",
                        "FID_ORG_ADJ_PRC": "0" if adjust_price else "1"
                    },
                    tr_id="FHKST03010100"
                )
                output_key = 'output2'
            else:
                # 분봉 데이터 (1, 5, 15, 30, 60분)
                result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                    params={
                        "FID_COND_MRKT_DIV_CODE": "J",
                        "FID_INPUT_ISCD": symbol,
                        "FID_INPUT_HOUR_1": period,  # 분봉 간격
                        "FID_PW_DATA_INCU_YN": "Y"
                    },
                    tr_id="FHKST03020200"
                )
                output_key = 'output2'
            
            output = result.get(output_key, [])
            if not output:
                self.logger.warning(f"⚠️ {symbol} 차트 데이터 없음")
                return []
            
            # KIS API 응답을 ChartDataCollector 호환 형식으로 변환
            chart_data = []
            for item in output:
                try:
                    if period == "D":
                        # 일봉 데이터 변환
                        date_str = item.get('stck_bsop_date', '')
                        if len(date_str) != 8:
                            continue
                        
                        data_point = {
                            'date': date_str,
                            'time': '',  # 일봉은 시간 정보 없음
                            'open': self._safe_int_parse(item.get('stck_oprc', '0')),
                            'high': self._safe_int_parse(item.get('stck_hgpr', '0')),
                            'low': self._safe_int_parse(item.get('stck_lwpr', '0')),
                            'close': self._safe_int_parse(item.get('stck_clpr', '0')),
                            'volume': self._safe_int_parse(item.get('acml_vol', '0'))
                        }
                    else:
                        # 분봉 데이터 변환
                        date_str = item.get('stck_cntg_hour', '')  # 체결시간 (HHMMSS)
                        if len(date_str) != 6:
                            continue
                        
                        # 오늘 날짜로 설정
                        today = datetime.now().strftime('%Y%m%d')
                        
                        data_point = {
                            'date': today,
                            'time': date_str,
                            'open': self._safe_int_parse(item.get('stck_oprc', '0')),
                            'high': self._safe_int_parse(item.get('stck_hgpr', '0')),
                            'low': self._safe_int_parse(item.get('stck_lwpr', '0')),
                            'close': self._safe_int_parse(item.get('stck_prpr', '0')),  # 현재가
                            'volume': self._safe_int_parse(item.get('cntg_vol', '0'))  # 체결량
                        }
                    
                    # 데이터 유효성 검증
                    if all(data_point[k] > 0 for k in ['open', 'high', 'low', 'close']):
                        chart_data.append(data_point)
                        
                except Exception as item_error:
                    self.logger.debug(f"차트 데이터 아이템 파싱 실패 {symbol}: {item_error}")
                    continue
            
            # 시간순 정렬 (과거 -> 현재)
            if period == "D":
                chart_data.sort(key=lambda x: x['date'])
            else:
                chart_data.sort(key=lambda x: (x['date'], x['time']))
            
            # 백그라운드 로그만 기록
            pass  # 차트 데이터 조회 성공 메시지 제거
            return chart_data
            
        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"❌ {symbol} 차트 데이터 조회 실패: {e}")
            raise KISAPIError(f"Failed to fetch chart data: {e}")

    async def load_hts_conditions(self) -> bool:
        """HTS 조건식 로드"""
        try:
            if not self.pykis_api:
                self.logger.warning("PyKis not available for HTS conditions")
                return False
                
            # PyKis 2.x 버전에서는 자동으로 조건식이 로드됨
            self.logger.info("✅ HTS 조건식 로드 완료 (PyKis 2.x auto-load)")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ HTS 조건식 로드 실패: {e}")
            return False

    async def get_hts_condition_list(self) -> List[Dict[str, str]]:
        """HTS에 저장된 조건식 목록을 API를 통해 직접 조회 (공식 API 스펙 준수)"""
        try:
            self.logger.info("📡 KIS API를 통해 HTS 조건식 목록 조회 중...")
            
            # HTS ID를 우선적으로 사용하고, 없으면 일반 ID 사용 (하위 호환성)
            user_id = getattr(self.config.kis_account, 'KIS_HTS_USER_ID', self.config.kis_account.KIS_USER_ID)

            # 공식 API 스펙에 따른 요청
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/psearch-title",
                params={"user_id": user_id},
                tr_id="HHKST03900300",
                custtype="P"  # 개인 고객 타입
            )

            # 공식 스펙: output2 필드에 결과 포함
            output2 = result.get('output2', [])
            if not output2:
                self.logger.warning("⚠️ HTS에 저장된 조건식이 없거나 API 조회에 실패했습니다.")
                self.logger.debug(f"API 응답: {result}")
                return []

            # 공식 스펙에 따른 형식 변환: {'id': 'seq', 'name': 'condition_nm'}
            condition_list = []
            for item in output2:
                if 'seq' in item and 'condition_nm' in item:
                    condition_list.append({
                        "id": item['seq'],
                        "name": item['condition_nm'],
                        "grp_nm": item.get('grp_nm', ''),
                        "user_id": item.get('user_id', '')
                    })
            
            self.logger.info(f"✅ API를 통해 {len(condition_list)}개의 HTS 조건식 목록 조회 성공")
            for condition in condition_list:
                self.logger.debug(f"  - [{condition['id']}] {condition['name']}")
            
            return condition_list

        except Exception as e:
            self.logger.error(f"❌ HTS 조건식 목록 조회 실패: {e}")
            return []

    async def get_stocks_by_condition(self, condition_id: str, condition_name: str = "") -> List[Dict]:
        """HTS 조건식으로 종목 검색 - KIS API 직접 호출 (공식 API 스펙 준수)"""
        try:
            self.logger.info(f"📊 HTS 조건식 {condition_id} ({condition_name}) 종목 검색 중...")

            # HTS ID를 우선적으로 사용하고, 없으면 일반 ID 사용 (하위 호환성)
            user_id = getattr(self.config.kis_account, 'KIS_HTS_USER_ID', self.config.kis_account.KIS_USER_ID)

            # 필수 파라미터 확인
            if not user_id:
                self.logger.error("❌ KIS_USER_ID 또는 KIS_HTS_USER_ID가 설정되지 않았습니다. 환경변수를 확인하세요.")
                return []
            
            # 조건ID 유효성 검사
            if not condition_id or not condition_id.isdigit():
                self.logger.error(f"❌ 잘못된 조건ID: {condition_id}. 숫자여야 합니다.")
                return []

            all_stocks_data = []
            page_count = 0
            max_pages = 3  # 최대 3페이지까지만 조회
            
            while page_count < max_pages:
                try:
                    # 공식 API 스펙에 따른 종목 조회
                    result = await self._make_api_request_with_pagination(
                        method="GET",
                        endpoint="/uapi/domestic-stock/v1/quotations/psearch-result",
                        params={
                            "user_id": self.config.kis_account.KIS_USER_ID,
                            "seq": str(condition_id)  # seq는 문자열로 전달
                        },
                        tr_id="HHKST03900400",
                        custtype="P"  # 개인 고객 타입
                    )

                    # 공식 스펙: output2 필드에 종목 정보 포함
                    output2 = result.get('output2', [])
                    if not output2:
                        if page_count == 0:
                            self.logger.warning(f"⚠️ 조건식 {condition_id} ({condition_name})에 해당하는 종목 없음")
                            # MCA05918 에러는 검색 결과가 0개인 경우
                            if result.get('msg_cd') == 'MCA05918':
                                self.logger.debug(f"검색 결과 0개: {result.get('msg1')}")
                        break

                    # 공식 스펙에 따른 종목 정보 변환
                    page_stocks = []
                    for item in output2:
                        if 'code' in item and 'name' in item:
                            stock_info = {
                                'code': item['code'],
                                'name': item['name'],
                                'price': float(item.get('price', '0').replace(',', '')),
                                'change': float(item.get('change', '0').replace(',', '')),
                                'chgrate': float(item.get('chgrate', '0').replace(',', '')),
                                'volume': int(float(item.get('acml_vol', '0').replace(',', ''))),
                                'market_cap': float(item.get('stotprice', '0').replace(',', ''))
                            }
                            page_stocks.append(stock_info)
                    
                    all_stocks_data.extend(page_stocks)
                    page_count += 1
                    
                    self.logger.debug(f"📖 페이지 {page_count}: {len(page_stocks)}개 종목 추가")
                    
                    # 페이지가 더 있는지 확인 (msg1에 "조회가 계속" 메시지가 없으면 마지막 페이지)
                    if "조회가 계속" not in result.get('msg1', ''):
                        break
                        
                    # 다음 페이지 조회를 위한 대기 (API 호출 제한 고려)
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    if "조회가 계속" in str(e):
                        self.logger.debug(f"📄 페이지네이션 감지: 페이지 {page_count + 1} 존재")
                        page_count += 1
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        raise e
            
            if all_stocks_data:
                self.logger.info(f"✅ 조건식 {condition_id} ({condition_name})로 {len(all_stocks_data)}개 종목 발견 ({page_count}페이지)")
                
                # 상위 종목들 로그 출력
                for i, stock in enumerate(all_stocks_data[:5]):
                    self.logger.debug(f"  {i+1}. {stock['code']} {stock['name']} - {stock['price']:,.0f}원 ({stock['chgrate']:+.2f}%)")
            else:
                self.logger.warning(f"⚠️ 조건식 {condition_id} ({condition_name}) 결과 없음")
            
            return all_stocks_data

        except Exception as e:
            error_msg = str(e)
            if "종목코드 오류" in error_msg:
                self.logger.error(f"❌ 조건식 {condition_id} ({condition_name}) 검색 실패: 잘못된 조건ID 또는 사용자ID")
                self.logger.error(f"   확인사항:")
                self.logger.error(f"   1. HTS에서 조건식 ID {condition_id}가 등록되어 있는지 확인")
                
                # HTS ID를 우선적으로 확인하도록 로그 수정
                hts_user_id = getattr(self.config.kis_account, 'KIS_HTS_USER_ID', None)
                if hts_user_id:
                    self.logger.error(f"   2. KIS_HTS_USER_ID (HTS 접속용 ID)가 올바른지 확인: {hts_user_id[:4]}****")
                else:
                    user_id_val = getattr(self.config.kis_account, 'KIS_USER_ID', '설정되지 않음')
                    user_id_to_log = user_id_val[:4] + '****' if user_id_val != '설정되지 않음' else '설정되지 않음'
                    self.logger.error(f"   2. KIS_HTS_USER_ID가 없어 KIS_USER_ID를 사용 중입니다. HTS 접속용 ID를 KIS_HTS_USER_ID로 설정했는지 확인하세요: {user_id_to_log}")

                self.logger.error(f"   3. 조건식이 활성화되어 있는지 HTS에서 확인")
            else:
                self.logger.error(f"❌ 조건식 {condition_id} ({condition_name}) 검색 실패: {e}")
            return None  # API 오류 시 None 반환

    async def get_news_data(self, symbol: str, name: str, days: int = 14) -> List[Dict]:
        """뉴스 데이터 수집 - 실제 NewsCollector 사용"""
        try:
            self.logger.debug(f"📰 {symbol}({name}) 뉴스 데이터 수집 시작...")
            
            # NewsCollector를 사용해 실제 뉴스 수집
            try:
                from data_collectors.news_collector import NewsCollector
                news_collector = NewsCollector(self.config)
                
                # 네이버 뉴스 검색으로 실제 뉴스 수집
                news_items = news_collector.search_stock_news_naver(name, symbol)
                
                if news_items and len(news_items) > 0:
                    self.logger.debug(f"✅ {symbol} 뉴스 {len(news_items)}건 수집 완료")
                    return news_items  # 전체 뉴스 반환 (10개 제한 제거)
                else:
                    self.logger.debug(f"📰 {symbol} 관련 뉴스 없음")
                    return []
                
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} 뉴스 수집 실패: {e}")
                return []
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 뉴스 데이터 수집 실패: {e}")
            return []

    async def get_filtered_stocks(self, strategy: str, limit: int = 20) -> Optional[List[Tuple[str, str]]]:
        """
        전략별 HTS 조건검색을 통해 필터링된 종목 리스트를 반환합니다.
        - HTS 조건검색 실패 시 None 반환
        """
        self.logger.info(f"📊 '{strategy}' 전략으로 {limit}개 필터링 종목 조회 시작...")
        
        # HTS 조건검색 시도
        hts_result = await self._try_hts_condition_search(strategy, limit)
        if hts_result is not None:
            return hts_result
        
        # HTS 조건검색 실패 시 None 반환
        self.logger.error(f"❌ HTS 조건검색 실패: '{strategy}' 전략으로 종목을 조회할 수 없습니다.")
        return None
    
    async def _try_hts_condition_search(self, strategy: str, limit: int) -> Optional[List[Tuple[str, str]]]:
        """HTS 조건검색 시도"""
        stock_list = []

        if not (hasattr(self.config, 'kis_account') and self.config.kis_account.KIS_USER_ID):
            self.logger.warning("⚠️ KIS_USER_ID가 설정되지 않아 HTS 조건검색을 사용할 수 없습니다.")
            return None

        try:
            target_condition_name = self.config.trading.HTS_CONDITION_NAMES.get(strategy)
            if not target_condition_name:
                self.logger.warning(f"⚠️ 설정 정보 없음: '{strategy}' 전략에 해당하는 HTS_CONDITION_NAMES가 config.py에 없습니다.")
                return None

            self.logger.info(f"🔍 HTS 조건검색 시도 (전략: {strategy}, 조건식명: {target_condition_name})...")
            
            # 직접 조건ID로 시도 (config에서 설정된 ID 사용)
            condition_id = self.config.trading.HTS_CONDITIONAL_SEARCH_IDS.get(strategy)
            if condition_id:
                try:
                    stocks_data = await self.get_stocks_by_condition(condition_id, target_condition_name)
                    
                    # stocks_data가 None이면 API 오류 발생
                    if stocks_data is None:
                        self.logger.error(f"❌ HTS 조건검색 API 오류 (조건식 ID {condition_id})")
                        return None
                    
                    for stock_data in stocks_data:
                        symbol = stock_data.get('code')
                        name = stock_data.get('name')
                        if symbol and name:
                            stock_list.append((symbol, name))
                    
                    if stock_list:
                        self.logger.info(f"✅ HTS 조건검색 성공: {len(stock_list)}개 종목 조회 완료")
                        return stock_list[:limit]
                    else:
                        self.logger.info(f"🔍 HTS 조건검색 성공했지만 조건에 맞는 종목 없음")
                        return []
                        
                except Exception as condition_error:
                    if "종목코드 오류" in str(condition_error):
                        self.logger.error(f"❌ HTS 조건식 ID {condition_id} 오류: 조건식이 등록되지 않았거나 비활성화됨")
                        self.logger.error(f"   확인사항:")
                        self.logger.error(f"   1. HTS에서 조건식 ID {condition_id}가 등록되어 있는지 확인")
                        self.logger.error(f"   2. 조건식이 활성화되어 있는지 확인")
                        self.logger.error(f"   3. KIS_USER_ID 환경변수 확인")
                    else:
                        self.logger.error(f"❌ HTS 조건검색 오류: {condition_error}")
                    return None
            
            # 조건ID가 없는 경우 조건목록에서 검색
            conditions = await self.get_hts_condition_list()
            
            if not conditions:
                self.logger.warning("⚠️ HTS에 저장된 조건식이 하나도 없습니다.")
                return None

            target_condition = next((c for c in conditions if c.get('name') == target_condition_name), None)

            if not target_condition:
                self.logger.warning(f"⚠️ HTS에서 '{target_condition_name}' 조건식을 찾을 수 없습니다.")
                return None

            condition_id = target_condition['id']
            self.logger.info(f"✅ 조건식 '{target_condition_name}' 발견 (ID: {condition_id})")
            
            stocks_data = await self.get_stocks_by_condition(condition_id, target_condition_name)
            
            for stock_data in stocks_data:
                symbol = stock_data.get('code')
                name = stock_data.get('name')
                if symbol and name:
                    stock_list.append((symbol, name))
            
            self.logger.info(f"✅ HTS 조건검색으로 {len(stock_list)}개 종목 조회 완료")
            return stock_list[:limit]

        except Exception as e:
            self.logger.warning(f"⚠️ HTS 조건검색 중 예외 발생: {e}")
            return None
    

    async def get_financial_ratios(self, symbol: str) -> Optional[Dict]:
        """
        국내주식 재무비율 조회 (EPS, BPS, ROE 등)
        TR_ID: FHKST66430300
        """
        try:
            self.logger.debug(f"📊 {symbol} 재무비율 조회 중...")

            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/finance/financial-ratio",
                params={
                    "FID_DIV_CLS_CODE": "0",  # 0: 년, 1: 분기 (년 단위 데이터 요청)
                    "fid_cond_mrkt_div_code": "J", # J: 전체 시장
                    "fid_input_iscd": symbol
                },
                tr_id="FHKST66430300"
            )

            output = result.get('output', [])
            if not output:
                self.logger.debug(f"ℹ️ {symbol} 재무비율 데이터 없음 (신규상장/스팩/특수업종 등)")
                return None

            # 가장 최근 데이터 (보통 첫 번째 항목)
            latest_data = output[0]
            self.logger.debug(f"Raw latest financial data for {symbol}: {latest_data}")

            financial_data = {
                'eps': self._safe_float_parse(latest_data.get('eps', '0')),
                'bps': self._safe_float_parse(latest_data.get('bps', '0')),
                'roe_val': self._safe_float_parse(latest_data.get('roe_val', '0')),
                'grs': self._safe_float_parse(latest_data.get('grs', '0')), # 매출액 증가율
                'bsop_prfi_inrt': self._safe_float_parse(latest_data.get('bsop_prfi_inrt', '0')), # 영업이익 증가율
                'ntin_inrt': self._safe_float_parse(latest_data.get('ntin_inrt', '0')), # 순이익 증가율
                'rsrv_rate': self._safe_float_parse(latest_data.get('rsrv_rate', '0')), # 유보율
                'lblt_rate': self._safe_float_parse(latest_data.get('lblt_rate', '0')), # 부채비율
            }
            self.logger.debug(f"✅ {symbol} 재무비율 조회 성공: {financial_data}")
            return financial_data

        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"❌ {symbol} 재무비율 조회 실패: {e}")
            return None

    async def get_investor_trading_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """특정 종목의 투자자별 매매 동향 조회"""
        try:
            validate_symbol_format(symbol)
            
            self.logger.debug(f"⚠️ {symbol} 투자자별 매매 동향 API는 현재 KIS API의 응답 문제로 일시 비활성화되었습니다.")
            return self._get_default_investor_data()
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 투자자별 매매 동향 조회 중 예상치 못한 오류: {e}")
            return self._get_default_investor_data()

    def _get_default_investor_data(self) -> Dict[str, Any]:
        """투자자별 매매 동향 기본값 반환"""
        return {
            'foreign': {'net_buying': 0, 'buy_volume': 0, 'sell_volume': 0},
            'institution': {'net_buying': 0, 'buy_volume': 0, 'sell_volume': 0},
            'individual': {'net_buying': 0, 'buy_volume': 0, 'sell_volume': 0}
        }

    async def place_order(self, symbol: str, quantity: int, price: Optional[int], 
                         order_type: str, side: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """주식 주문 (현금) - KIS API"""
        try:
            # 0. 주문 중복 방지 (5초 내 같은 주문 방지) - 스레드 세이프
            order_key = f"{symbol}_{side}_{quantity}_{price}"
            current_time = time.time()
            
            async with self._orders_lock:
                if order_key in self.recent_orders:
                    if current_time - self.recent_orders[order_key] < 5:
                        return {'success': False, 'error': '중복 주문 방지: 5초 이내 동일 주문이 있습니다.'}
                
                self.recent_orders[order_key] = current_time
            
            # 0-1. 일일 손실 한도 체크 (매수 주문일 때)
            if side.upper() == 'BUY':
                daily_loss_check = await self._check_daily_loss_limit()
                if not daily_loss_check['allowed']:
                    return {'success': False, 'error': f'일일 손실 한도 초과: {daily_loss_check["reason"]}'}
            
            # 1. 계좌번호 처리
            account_number = getattr(self.config.api, 'KIS_ACCOUNT_NUMBER', '')
            if not account_number:
                raise KISAPIError("KIS 계좌번호가 설정되지 않았습니다.")
            
            if '-' in account_number:
                cano, acnt_prdt_cd = account_number.split('-', 1)
            else:
                raise KISAPIError("계좌번호 형식이 올바르지 않습니다.")

            # 2. 호가단위 검증 (지정가 주문인 경우)
            if order_type.upper() == 'LIMIT' and price:
                validated_price = self._validate_korean_price_unit(price)
                if validated_price != price:
                    self.logger.warning(f"호가단위 조정: {price} → {validated_price}")
                    price = validated_price

            # 3. TR_ID 설정
            if side.upper() == 'BUY':
                tr_id = "TTTC0802U"  # 실거래 매수
            else: # SELL
                tr_id = "TTTC0801U"  # 실거래 매도
            
            # 4. 주문구분 코드 매핑
            order_type_map = {'MARKET': '01', 'LIMIT': '00'}
            ord_dvsn = order_type_map.get(order_type.upper(), '00')
            
            # 5. Request Body 구성
            request_body = {
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_prdt_cd,
                "PDNO": symbol,
                "ORD_DVSN": ord_dvsn,
                "ORD_QTY": str(quantity),
                "ORD_UNPR": "0" if ord_dvsn == '01' else str(price)
            }
            
            self.logger.info(f"📤 KIS 주문 요청: {side} {symbol} {quantity}주 @ {price if ord_dvsn == '00' else 'Market'}")
            
            # 6. API 호출 제한 체크
            await self.rate_limiter.acquire()
            
            # 7. 중앙 API 요청 메소드 사용
            result = await self._make_api_request(
                method="POST",
                endpoint="/uapi/domestic-stock/v1/trading/order-cash",
                data=request_body,
                tr_id=tr_id,
                timeout_seconds=timeout
            )

            # 8. 결과 처리
            if result.get('rt_cd') == '0':
                order_id = result.get('output', {}).get('ODNO', '')
                self.logger.info(f"✅ KIS 주문 성공: {order_id}")
                
                # 주문 성공 시 최근 주문 목록에서 제거 (중복 방지용) - 스레드 세이프
                async with self._orders_lock:
                    if order_key in self.recent_orders:
                        del self.recent_orders[order_key]
                    
                return {'success': True, 'order_id': order_id, 'message': result.get('msg1', ''), 'kis_response': result}
            else:
                error_msg = result.get('msg1', '주문 실패')
                self.logger.error(f"❌ KIS 주문 실패: {error_msg}")
                return {'success': False, 'error': error_msg, 'kis_response': result}
                        
        except Exception as e:
            self.logger.error(f"❌ KIS 주문 중 예외 발생: {e}")
            return {'success': False, 'error': f'주문 실행 중 오류: {str(e)}'}

    def _validate_korean_price_unit(self, price: int) -> int:
        """한국 주식 호가단위 검증 및 조정"""
        if price < 1000:
            return ((price + 0) // 1) * 1  # 1원 단위
        elif price < 5000:
            return ((price + 2) // 5) * 5  # 5원 단위
        elif price < 10000:
            return ((price + 4) // 10) * 10  # 10원 단위
        elif price < 50000:
            return ((price + 24) // 50) * 50  # 50원 단위
        elif price < 100000:
            return ((price + 49) // 100) * 100  # 100원 단위
        elif price < 500000:
            return ((price + 249) // 500) * 500  # 500원 단위
        else:
            return ((price + 499) // 1000) * 1000  # 1000원 단위

    async def _check_daily_loss_limit(self) -> Dict[str, Any]:
        """일일 손실 한도 체크 - 실제 DB 연동"""
        try:
            from datetime import datetime
            from sqlalchemy import func
            
            # DB가 연결되지 않은 경우 기본 허용 (개발환경)
            if not hasattr(self, 'db_manager') or not self.db_manager:
                self.logger.info("DB 매니저가 없어서 일일 손실 한도 체크를 건너뜁니다. (개발 모드)")
                return {'allowed': True, 'reason': 'DB 연결 없음 - 개발 모드'}
            
            max_daily_loss = getattr(self.config.risk, 'HARD_MAX_DAILY_LOSS', 100000)
            today = datetime.now().date()
            
            # DB에서 오늘 거래 내역 조회 (손실만)
            session = self.db_manager.get_session()
            try:
                # TradingHistory 테이블에서 오늘 매도 거래 중 손실 계산
                # 매도가격이 매수평균가보다 낮은 경우만 손실로 계산
                query = """
                    SELECT COALESCE(SUM((buy_average_price - sell_price) * sell_quantity), 0) as today_loss
                    FROM trading_history 
                    WHERE DATE(sell_date) = :today 
                    AND sell_price < buy_average_price
                    AND side = 'SELL'
                """
                result = session.execute(query, {'today': today}).fetchone()
                today_loss = float(result[0] if result and result[0] else 0)
                
                if today_loss >= max_daily_loss:
                    return {
                        'allowed': False, 
                        'reason': f'일일 손실 한도 {max_daily_loss:,}원 초과 (현재: {today_loss:,}원)'
                    }
                
                return {'allowed': True, 'remaining': max_daily_loss - today_loss}
                
            finally:
                session.close()
            
        except Exception as e:
            self.logger.warning(f"일일 손실 한도 체크 실패: {e}")
            # 오류 발생 시 보수적으로 허용 (시스템 중단 방지)
            return {'allowed': True, 'reason': f'손실 한도 체크 실패: {str(e)}'}

    async def _generate_hashkey(self, session: aiohttp.ClientSession, request_body: Dict) -> str:
        """해시키 생성"""
        try:
            hashkey_url = f"{self.base_url}/uapi/hashkey"
            headers = {
                'content-type': 'application/json; charset=utf-8',
                'appkey': self.app_key,
                'appsecret': self.app_secret
            }
            
            async with session.post(hashkey_url, headers=headers, json=request_body) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('HASH', '')
                else:
                    self.logger.warning(f"⚠️ 해시키 생성 실패: {response.status}")
                    return ''
                    
        except Exception as e:
            self.logger.warning(f"⚠️ 해시키 생성 중 오류: {e}")
            return ''

    async def get_orderable_cash(self, symbol: Optional[str] = None, order_price: Optional[int] = None, order_division: str = "01", use_margin: bool = False) -> Optional[int]:
        """매수가능금액 조회 (토큰 재발급 재시도 포함)"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 첫 번째 시도가 실패하면 토큰 강제 갱신
                if attempt > 0:
                    self.logger.info("🔄 토큰 강제 갱신 시도...")
                    session = await self.http_session.get_session()
                    await self.token_manager.request_new_token(session)

                await self.ensure_valid_token()

                account_number = getattr(self.config.api, 'KIS_ACCOUNT_NUMBER', '')
                if not account_number:
                    raise KISAPIError("KIS 계좌번호가 설정되지 않았습니다. .env 파일에 KIS_ACCOUNT_NUMBER를 추가하세요.")

                cano, acnt_prdt_cd = account_number.split('-', 1)

                params = {
                    'CANO': cano,
                    'ACNT_PRDT_CD': acnt_prdt_cd,
                    'PDNO': symbol if symbol else '',  # 종목번호 (공란시 매수수량 없이 금액만 조회)
                    'ORD_UNPR': str(order_price) if order_price else '0',  # 주문단가 (시장가 조회시 공란)
                    'ORD_DVSN': order_division,  # 주문구분 (01: 시장가, 00: 지정가 등)
                    'CMA_EVLU_AMT_ICLD_YN': 'N',  # CMA 평가금액 포함 여부
                    'OVRS_ICLD_YN': 'N'  # 해외 포함 여부
                }

                tr_id = "TTTC8908R"  # 실거래 매수가능금액 조회

                self.logger.debug(f"💰 매수가능금액 조회 요청 중 (TR_ID: {tr_id})...")

                result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/trading/inquire-psbl-order",
                    params=params,
                    tr_id=tr_id
                )

                if result.get('rt_cd') == '0':
                    output = result.get('output', {})
                    if use_margin:
                        available_amount = self._safe_int_parse(output.get('max_buy_amt', '0'))
                    else:
                        available_amount = self._safe_int_parse(output.get('nrcvb_buy_amt', '0'))

                    # 백그라운드 로그만 기록
                    pass  # 매수가능금액 조회 성공 메시지 제거
                    return available_amount
                else:
                    error_msg = result.get('msg1', '알 수 없는 오류')

                    # 토큰 관련 오류인지 확인
                    if "token" in error_msg.lower() or "EGW00121" in result.get('msg_cd', ''):
                        if attempt < max_retries - 1:
                            self.logger.warning(f"⚠️ 토큰 오류 감지, 재시도 {attempt + 1}/{max_retries}: {error_msg}")
                            continue

                    self.logger.error(f"❌ 매수가능금액 조회 실패: {error_msg}")
                    return None

            except Exception as e:
                if attempt < max_retries - 1 and ("token" in str(e).lower() or "EGW00121" in str(e)):
                    self.logger.warning(f"⚠️ 매수가능금액 조회 재시도 {attempt + 1}/{max_retries}: {e}")
                    continue

                self.logger.error(f"❌ 매수가능금액 조회 중 예외 발생: {e}")
                return None


    async def get_orderable_quantity(self, symbol: str, order_price: Optional[int] = None, order_division: str = "01", use_margin: bool = False) -> Optional[int]:
        """매수가능수량 조회"""
        try:
            await self.ensure_valid_token()

            account_number = getattr(self.config.api, 'KIS_ACCOUNT_NUMBER', '')
            if not account_number:
                raise KISAPIError("KIS 계좌번호가 설정되지 않았습니다. .env 파일에 KIS_ACCOUNT_NUMBER를 추가하세요.")

            cano, acnt_prdt_cd = account_number.split('-', 1)

            params = {
                'CANO': cano,
                'ACNT_PRDT_CD': acnt_prdt_cd,
                'PDNO': symbol,  # 종목번호 필수
                'ORD_UNPR': '0' if order_division == "01" else str(order_price or 0),  # 시장가는 0
                'ORD_DVSN': order_division,  # 주문구분 (01: 시장가 권장)
                'CMA_EVLU_AMT_ICLD_YN': 'N',  # CMA 평가금액 포함 여부
                'OVRS_ICLD_YN': 'N'  # 해외 포함 여부
            }

            tr_id = "TTTC8908R"  # 실거래 매수가능금액 조회

            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/trading/inquire-psbl-order",
                params=params,
                tr_id=tr_id
            )

            if result.get('rt_cd') == '0':
                output = result.get('output', {})
                if use_margin:
                    available_qty = self._safe_int_parse(output.get('max_buy_qty', '0'))
                else:
                    available_qty = self._safe_int_parse(output.get('nrcvb_buy_qty', '0'))

                return available_qty
            else:
                return None

        except Exception as e:
            return None

    async def get_account_balance(self) -> Dict[str, Any]:
        """계좌 잔고 조회 (토큰 재발급 재시도 포함)"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 첫 번째 시도가 실패하면 토큰 강제 갱신
                if attempt > 0:
                    self.logger.info("🔄 토큰 강제 갱신 시도...")
                    session = await self.http_session.get_session()
                    await self.token_manager.request_new_token(session)

                await self.ensure_valid_token()

                account_number = getattr(self.config.api, 'KIS_ACCOUNT_NUMBER', '')
                if not account_number:
                    raise KISAPIError("KIS 계좌번호가 설정되지 않았습니다. .env 파일에 KIS_ACCOUNT_NUMBER를 추가하세요.")

                # 계좌번호 파싱: "12345678-01" -> CANO="12345678", ACNT_PRDT_CD="01"
                if '-' in account_number:
                    cano, acnt_prdt_cd = account_number.split('-', 1)
                else:
                    raise KISAPIError(f"계좌번호 형식이 올바르지 않습니다. 형식: 12345678-01, 입력값: {account_number}")

                params = {
                    'CANO': cano,
                    'ACNT_PRDT_CD': acnt_prdt_cd,
                    'AFHR_FLPR_YN': 'N',
                    'OFL_YN': '',
                    'INQR_DVSN': '02',
                    'UNPR_DVSN': '01',
                    'FUND_STTL_ICLD_YN': 'N',
                    'FNCG_AMT_AUTO_RDPT_YN': 'N',
                    'PRCS_DVSN': '01',
                    'CTX_AREA_FK100': '',
                    'CTX_AREA_NK100': ''
                }

                result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/trading/inquire-balance",
                    params=params,
                    tr_id="TTTC8434R"
                )

                if result.get('rt_cd') == '0':
                    # 예수금 정보 추출
                    output2 = result.get('output2', [{}])[0]
                    # dnca_tot_amt: 예수금총금액 (실제 사용 가능한 금액)
                    available_cash = int(output2.get('dnca_tot_amt', '0'))

                    self.logger.info(f"✅ 계좌 잔고 조회 성공: {available_cash:,}원")
                    return {
                        'available_cash': available_cash,
                        'total_evaluation': int(output2.get('TOT_EVLU_AMT', '0')),
                        'data': result
                    }

                error_msg = result.get('msg1', '알 수 없는 오류')

                # 토큰 관련 오류인지 확인
                if "token" in error_msg.lower() or "EGW00121" in result.get('msg_cd', ''):
                    if attempt < max_retries - 1:
                        self.logger.warning(f"⚠️ 토큰 오류 감지, 재시도 {attempt + 1}/{max_retries}: {error_msg}")
                        continue

                self.logger.error(f"❌ 계좌 잔고 조회 실패: {error_msg}")
                raise KISAPIError(f"계좌 잔고 조회 실패: {error_msg}")

            except Exception as e:
                if attempt < max_retries - 1 and ("token" in str(e).lower() or "EGW00121" in str(e)):
                    self.logger.warning(f"⚠️ 계좌 잔고 조회 재시도 {attempt + 1}/{max_retries}: {e}")
                    continue

                self.logger.error(f"❌ 계좌 잔고 조회 실패: {e}")
                raise KISAPIError(f"계좌 잔고 조회 실패: {e}")

    async def get_holdings(self) -> Dict[str, Any]:
        """보유 종목 조회 (연속조회 지원, 보유수량 0 포함)"""
        try:
            # Ensure KIS collector is initialized before making API calls
            if not self.is_initialized:
                self.logger.info("🔄 KIS collector 초기화 중...")
                await self.initialize()

            await self.ensure_valid_token()

            account_number = getattr(self.config.api, 'KIS_ACCOUNT_NUMBER', '')
            if not account_number:
                raise KISAPIError("KIS 계좌번호가 설정되지 않았습니다. .env 파일에 KIS_ACCOUNT_NUMBER를 추가하세요.")

            # 계좌번호 파싱: "12345678-01" -> CANO="12345678", ACNT_PRDT_CD="01"
            if '-' in account_number:
                cano, acnt_prdt_cd = account_number.split('-', 1)
            else:
                raise KISAPIError(f"계좌번호 형식이 올바르지 않습니다. 형식: 12345678-01, 입력값: {account_number}")

            holdings = {}
            ctx_area_fk100 = ''
            ctx_area_nk100 = ''
            page_count = 0
            max_pages = 5  # 최대 5페이지까지 조회

            while page_count < max_pages:
                params = {
                    'CANO': cano,
                    'ACNT_PRDT_CD': acnt_prdt_cd,
                    'AFHR_FLPR_YN': 'N',
                    'OFL_YN': '',
                    'INQR_DVSN': '02',  # 01: 대출일별, 02: 종목별 (더 많은 데이터)
                    'UNPR_DVSN': '01',
                    'FUND_STTL_ICLD_YN': 'N',
                    'FNCG_AMT_AUTO_RDPT_YN': 'N',
                    'PRCS_DVSN': '00',  # 00: 전일매매포함, 01: 전일매매미포함 (더 포괄적)
                    'CTX_AREA_FK100': ctx_area_fk100,
                    'CTX_AREA_NK100': ctx_area_nk100
                }

                result = await self._make_api_request(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/trading/inquire-balance",
                    params=params,
                    tr_id="TTTC8434R"
                )

                if result.get('rt_cd') != '0':
                    break

                # 현재 페이지 데이터 처리
                page_items = 0
                for item in result.get('output1', []):
                    symbol = item.get('pdno', '')
                    quantity = int(item.get('hldg_qty', '0'))

                    # 보유수량이 0인 종목도 포함 (당일 매도, D-2일까지 보이는 종목)
                    if symbol:
                        avg_price = float(item.get('pchs_avg_pric', '0'))
                        current_price = int(item.get('prpr', '0'))
                        evaluation = int(item.get('evlu_amt', '0'))

                        # 의미있는 데이터가 있는 종목만 포함
                        if quantity > 0 or avg_price > 0 or evaluation > 0:
                            holdings[symbol] = {
                                'name': item.get('prdt_name', ''),
                                'quantity': quantity,
                                'avg_price': avg_price,
                                'current_price': current_price,
                                'evaluation': evaluation,
                                'profit_loss': int(item.get('evlu_pfls_amt', '0')),
                                'profit_rate': float(item.get('evlu_pfls_rt', '0')),
                                'trade_type': item.get('trad_dvsn_name', ''),  # 매매구분
                                'today_buy_qty': int(item.get('thdt_buyqty', '0')),  # 당일매수수량
                                'today_sell_qty': int(item.get('thdt_sll_qty', '0'))  # 당일매도수량
                            }
                            page_items += 1

                self.logger.info(f"📊 보유종목 조회 페이지 {page_count + 1}: {page_items}개 종목")

                # 연속조회 확인
                tr_cont = result.get('tr_cont', '')
                if tr_cont in ['F', 'M']:  # 다음 데이터 있음
                    ctx_area_fk100 = result.get('ctx_area_fk100', '')
                    ctx_area_nk100 = result.get('ctx_area_nk100', '')
                    page_count += 1
                else:
                    break  # 마지막 데이터

            self.logger.info(f"✅ 총 보유종목 조회 완료: {len(holdings)}개 종목 ({page_count + 1}페이지)")
            return holdings

        except Exception as e:
            self.logger.error(f"❌ 보유 종목 조회 실패: {e}")
            return {}

    async def get_market_index_data(self, market_type: str = "KOSPI") -> Optional[Dict[str, Any]]:
        """시장 지수 데이터 조회 - 국내업종 현재 지수 API 사용 (MD 파일 기준)
        
        Args:
            market_type: KOSPI, KOSDAQ, KOSPI200 등
            
        Returns:
            시장 지수 정보 딕셔너리
        """
        try:
            if not self.is_initialized:
                await self.initialize()
            
            self.logger.debug(f"📊 {market_type} 시장 지수 조회 중...")
            
            # 시장 지수 코드 매핑 (국내업종 현재 지수 API 기준)
            index_codes = {
                "KOSPI": "0001",    # 코스피
                "KOSDAQ": "1001",   # 코스닥
                "KOSPI200": "2001"  # 코스피200
            }
            
            fid_input_iscd = index_codes.get(market_type.upper(), "0001")
            
            # 국내업종 현재 지수 API 호출 (MD 파일 기준 TR_ID 및 엔드포인트)
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-index-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": "U",  # U: 업종 (MD 파일 기준)
                    "FID_INPUT_ISCD": fid_input_iscd
                },
                tr_id="FHPUP02100000"  # 국내업종 현재 지수 올바른 TR_ID
            )
            
            if not result or result.get('rt_cd') != '0':
                self.logger.warning(f"⚠️ {market_type} 시장 지수 API 응답 오류: {result}")
                return None
            
            output = result.get('output', {})
            if not output:
                self.logger.warning(f"⚠️ {market_type} 시장 지수 데이터 없음")
                return None
            
            # MD 파일 기준 응답 필드 사용 (소문자)
            current_value = self._safe_float_parse(output.get('bstp_nmix_prpr', '0'))        # 현재가
            change_value = self._safe_float_parse(output.get('bstp_nmix_prdy_vrss', '0'))   # 전일대비
            change_rate = self._safe_float_parse(output.get('prdy_ctrt', '0'))              # 전일대비율
            
            return {
                'market_type': market_type.upper(),
                'index_code': fid_input_iscd,
                'current_value': current_value,
                'change_value': change_value,
                'change_rate': change_rate,
                'volume': self._safe_int_parse(output.get('acml_vol', '0')),
                'trading_value': self._safe_float_parse(output.get('acml_tr_pbmn', '0')),
                'timestamp': datetime.now().isoformat(),
                'market_status': output.get('mrkt_stat_tp_cd', 'UNKNOWN')
            }
                    
        except Exception as e:
            self.logger.error(f"❌ {market_type} 시장 지수 조회 실패: {e}")
            return None

    async def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """종목 상세 데이터 조회
        
        Args:
            symbol: 종목 코드 (6자리)
            
        Returns:
            종목 상세 정보 딕셔너리
        """
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # 6자리 종목 코드 확인
            if len(symbol) != 6 or not symbol.isdigit():
                self.logger.error(f"❌ 잘못된 종목 코드 형식: {symbol}")
                return None
            
            # KIS API 종목 상세 정보 조회
            if self.use_pykis and self.api:
                try:
                    # PyKis를 사용한 종목 정보 조회 (현재가 시세)
                    response = await self._make_api_request(
                        method="GET",
                        endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                        params={
                            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
                            "FID_INPUT_ISCD": symbol
                        },
                        tr_id="FHKST01010100"  # 주식현재가 시세 TR_ID
                    )
                    
                    if response and response.get('rt_cd') == '0':
                        output = response.get('output', {})
                        
                        # 추가 정보를 위한 종목 기본 정보 조회
                        basic_info_response = await self._make_api_request(
                            method="GET",
                            endpoint="/uapi/domestic-stock/v1/quotations/search-stock-info",
                            params={
                                "PDNO": symbol,
                                "PRDT_TYPE_CD": "300"  # 주식
                            },
                            tr_id="CTPF1002R"  # 상품기본조회 TR_ID
                        )
                        
                        basic_info = {}
                        if basic_info_response and basic_info_response.get('rt_cd') == '0':
                            basic_output = basic_info_response.get('output', [])
                            if basic_output:
                                basic_info = basic_output[0]
                        
                        return {
                            'symbol': symbol,
                            'name': basic_info.get('PRDT_ABRV_NAME', output.get('PRDT_ABRV_NAME', 'Unknown')),
                            'current_price': int(output.get('STCK_PRPR', '0')),
                            'change_price': int(output.get('PRDY_VRSS', '0')),
                            'change_rate': float(output.get('PRDY_CTRT', '0')),
                            'volume': int(output.get('ACML_VOL', '0')),
                            'trade_amount': int(output.get('ACML_TR_PBMN', '0')),
                            'open_price': int(output.get('STCK_OPRC', '0')),
                            'high_price': int(output.get('STCK_HGPR', '0')),
                            'low_price': int(output.get('STCK_LWPR', '0')),
                            'prev_close': int(output.get('STCK_SDPR', '0')),
                            'market_cap': int(output.get('HTSM_MAMT', '0')),
                            'listed_shares': int(output.get('LSTN_STCN', '0')),
                            'per': float(output.get('PER', '0')),
                            'pbr': float(output.get('PBR', '0')),
                            'eps': float(output.get('EPS', '0')),
                            'bps': float(output.get('BPS', '0')),
                            'high_52w': int(output.get('W52_HGPR', '0')),
                            'low_52w': int(output.get('W52_LWPR', '0')),
                            'timestamp': datetime.now(),
                            'market_status': output.get('MRKT_STAT_TP_CD', 'UNKNOWN')
                        }
                    else:
                        self.logger.warning(f"⚠️ 종목 데이터 조회 실패: {response}")
                
                except Exception as e:
                    self.logger.warning(f"⚠️ PyKis 종목 데이터 조회 실패: {e}")
            
            # HTTP 클라이언트로 조회  
            data = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol
                },
                tr_id="FHKST01010100"
            )
            
            if data.get('rt_cd') == '0':
                output = data.get('output', {})
                
                # 기본 정보 추가 조회
                try:
                    basic_data = await self._make_api_request(
                        method="GET",
                        endpoint="/uapi/domestic-stock/v1/quotations/search-stock-info",
                        params={
                            "PDNO": symbol,
                            "PRDT_TYPE_CD": "300"
                        },
                        tr_id="CTPF1002R"
                    )
                    
                    basic_info = {}
                    if basic_data.get('rt_cd') == '0' and basic_data.get('output'):
                        basic_info = basic_data.get('output', [{}])[0]
                except:
                    basic_info = {}
                
                return {
                    'symbol': symbol,
                    'name': basic_info.get('PRDT_ABRV_NAME', output.get('PRDT_ABRV_NAME', 'Unknown')),
                    'current_price': int(output.get('STCK_PRPR', '0')),
                    'change_price': int(output.get('PRDY_VRSS', '0')),
                    'change_rate': float(output.get('PRDY_CTRT', '0')),
                    'volume': int(output.get('ACML_VOL', '0')),
                    'trade_amount': int(output.get('ACML_TR_PBMN', '0')),
                    'open_price': int(output.get('STCK_OPRC', '0')),
                    'high_price': int(output.get('STCK_HGPR', '0')),
                    'low_price': int(output.get('STCK_LWPR', '0')),
                    'prev_close': int(output.get('STCK_SDPR', '0')),
                    'market_cap': int(output.get('HTSM_MAMT', '0')),
                    'listed_shares': int(output.get('LSTN_STCN', '0')),
                    'per': float(output.get('PER', '0')),
                    'pbr': float(output.get('PBR', '0')),
                    'eps': float(output.get('EPS', '0')),
                    'bps': float(output.get('BPS', '0')),
                    'high_52w': int(output.get('W52_HGPR', '0')),
                    'low_52w': int(output.get('W52_LWPR', '0')),
                    'timestamp': datetime.now(),
                    'market_status': output.get('MRKT_STAT_TP_CD', 'UNKNOWN')
                }
            else:
                self.logger.error(f"❌ 종목 데이터 조회 API 오류: {data}")
                return None
                    
        except Exception as e:
            self.logger.error(f"❌ 종목 데이터 조회 실패: {e}")
            return None

    async def get_active_stocks(self, market_type="ALL", limit=20):
        """거래량 기반 활성 종목 조회"""
        try:
            # KOSPI 200 구성종목 조회
            kospi_stocks = await self._get_kospi200_stocks()
            if not kospi_stocks:
                # 기본 대형주 목록 (시가총액 기준)
                return ["005930", "000660", "035420", "051910", "068270", 
                       "207940", "005935", "035720", "006400", "003670"]
            
            # 최대 limit 개수만 반환
            return kospi_stocks[:limit]
            
        except Exception as e:
            self.logger.error(f"활성 종목 조회 실패: {e}")
            # 안전 장치: 기본 종목 반환
            return ["005930", "000660", "035420", "051910", "068270"]

    async def get_market_leaders(self, limit=10):
        """시가총액 상위 종목 조회"""
        try:
            # KOSPI 200 대형주 조회
            kospi_stocks = await self._get_kospi200_stocks()
            if kospi_stocks:
                return kospi_stocks[:limit]
            
            # 기본 대형주 목록
            leaders = ["005930", "000660", "035420", "051910", "068270", 
                      "207940", "005935", "035720", "006400", "003670"]
            return leaders[:limit]
            
        except Exception as e:
            self.logger.error(f"시장 대표 종목 조회 실패: {e}")
            return ["005930", "000660", "035420"]

    async def _get_kospi200_stocks(self):
        """KOSPI 200 구성종목 조회"""
        try:
            headers = await self._get_auth_headers()
            if not headers:
                return None
                
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-stock-price"
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "0001"  # KOSPI 200 지수
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('rt_cd') == '0':
                            stocks = []
                            for item in data.get('output', [])[:50]:  # 상위 50개
                                stock_code = item.get('mksc_shrn_iscd', '').strip()
                                if stock_code and len(stock_code) == 6:
                                    stocks.append(stock_code)
                            return stocks
                    return None
                    
        except Exception as e:
            self.logger.error(f"KOSPI 200 종목 조회 실패: {e}")
            return None

    async def cleanup(self):
        """리소스 정리"""
        await self.close()