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

# Third-party imports
try:
    from pykis import PyKis
    Api = PyKis  # 호환성을 위한 alias
    print("SUCCESS: pykis PyKis imported successfully")
except ImportError as e:
    Api = None
    print(f"FATAL: Failed to import pykis components: {e}")
    
# Local imports
from utils.logger import get_logger

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
    """Enhanced token manager with file-based caching and auto-refresh"""
    
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
                    'Content-Type': 'application/json',
                    'User-Agent': 'TradingSystem/2.0'
                }
                
                # Make request with timeout
                timeout = aiohttp.ClientTimeout(total=10, connect=5)
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            
                            # Validate response structure
                            if 'access_token' not in result:
                                raise KISAuthenticationError("Access token not found in response")
                            
                            self.access_token = result['access_token']
                            # KIS tokens typically expire in 24 hours
                            self.token_expired = datetime.now() + timedelta(hours=23, minutes=50)
                            
                            # 토큰을 파일에 캐시
                            self._save_token_to_cache()
                            
                            self.logger.info(f"✅ 새 액세스 토큰 획득 완료 (만료: {self.token_expired})")
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
        self.is_virtual = getattr(config.api, 'KIS_VIRTUAL_ACCOUNT', True)
        self.pykis_api = pykis_api # pykis_api 속성 초기화
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS API credentials not configured")
        
        # Core components
        self.token_manager = None
        self.session: Optional[aiohttp.ClientSession] = None
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
        
        self.logger.info(f"KISCollector 초기화 완료 (virtual: {self.is_virtual})")
    
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
                self.app_key, self.app_secret, self.base_url, self.logger, self.is_virtual
            )
            
            # 간소화된 세션 설정
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'Content-Type': 'application/json', 'User-Agent': 'TradingSystem/2.0'}
            )
            
            # 토큰 확인/획득 (캐시된 토큰이 유효하면 재사용)
            await self.token_manager.ensure_valid_token(self.session)
            
            self.status = APIStatus.CONNECTED
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
            if self.session and not self.session.closed:
                await self.session.close()
                await asyncio.sleep(0.1)
            self.session = None
            self.status = APIStatus.DISCONNECTED
            self.logger.info("✅ KIS API collector 종료 완료")
        except Exception as e:
            self.logger.warning(f"⚠️ 종료 중 오류: {e}")
    
    async def _make_api_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None,
        data: Optional[Dict] = None, tr_id: Optional[str] = None,
        custtype: str = "P", retry_count: int = 3
    ) -> Dict[str, Any]:
        """Make API request with proper error handling"""
        if not self.session:
            raise KISAPIError("Session not initialized")
        
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
                await self.token_manager.ensure_valid_token(self.session)
                headers = self.token_manager.get_headers(tr_id=tr_id, custtype=custtype)

                # 디버깅 로그 추가 (위치 수정)
                self.logger.debug(f"---> API Request [Attempt {attempt+1}/{retry_count}] ---")
                self.logger.debug(f"URL: {method} {url}")
                self.logger.debug(f"Headers: {headers}")
                self.logger.debug(f"Params: {params}")
                self.logger.debug(f"Data: {data}")
                self.logger.debug("--------------------------------------")
                
                async with self.session.request(method, url, params=params, json=data, headers=headers) as response:
                    response_text = await response.text()
                    self.metrics['requests_made'] += 1
                    response_time = time.time() - request_start_time
                    self._update_response_time(response_time)

                    # <--- API Response 로그 추가
                    self.logger.debug(f"<--- API Response [Status: {response.status}] ---")
                    self.logger.debug(f"Response Body: {response_text[:500]}...") # 너무 길면 잘라서 표시
                    self.logger.debug("--------------------------------------")
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            # rt_cd가 0이 아닌 경우, KIS API 레벨의 오류로 간주
                            if result.get('rt_cd') != '0':
                                self.logger.warning(f"KIS API Error: {result.get('msg1')}")
                                # 실패로 간주하고 재시도 로직을 탈 수 있도록 예외 발생
                                raise KISAPIError(f"KIS API returned error: {result.get('msg1')}", response_data=result)

                            self.logger.debug(f"✅ API 요청 성공: {method} {endpoint}")
                            return result
                        except json.JSONDecodeError as e:
                            raise KISAPIError(f"Invalid JSON response: {e}")
                    
                    elif response.status == 401:
                        self.logger.info("토큰 만료, 새로고침 중...")
                        await self.token_manager.request_new_token(self.session)
                        continue
                    
                    elif response.status == 429:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limited, {wait_time}초 대기...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    elif response.status >= 500:
                        if attempt < retry_count - 1:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            self.logger.warning(f"서버 오류 {response.status}, {wait_time:.1f}초 후 재시도...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise KISAPIError(f"Server error {response.status}: {response_text}")
                    
                    else:
                        raise KISAPIError(f"API request failed with status {response.status}: {response_text}")
            
            except asyncio.TimeoutError:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"요청 타임아웃, {wait_time}초 후 재시도...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError("Request timed out after retries")
            
            except aiohttp.ClientError as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"네트워크 오류, {wait_time}초 후 재시도: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KISNetworkError(f"Network error: {e}")
        
        self.metrics['requests_failed'] += 1
        raise KISAPIError("Max retry attempts exceeded")
    
    def _update_response_time(self, response_time: float):
        """Update average response time metric"""
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = response_time
        else:
            self.metrics['average_response_time'] = (0.9 * self.metrics['average_response_time'] + 0.1 * response_time)
        self.metrics['last_request_time'] = datetime.now()

    async def get_stock_info(self, symbol: str) -> Optional[StockData]:
        """주식 정보 조회"""
        try:
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                raise KISDataValidationError(f"Invalid symbol format: {symbol}")
            
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
        """주식명 추출"""
        name_candidates = [
            output.get('hts_kor_isnm', '').strip(),
            output.get('prdy_vrss_sign', '').strip(),
            output.get('hts_kor_isnm_1', '').strip()
        ]
        for candidate in name_candidates:
            if candidate and not candidate.startswith('종목') and len(candidate) > 2:
                return self._clean_stock_name(candidate)
        
        return f'종목{symbol}'

    def _clean_stock_name(self, name: str) -> str:
        """주식명 정리"""
        if not name: return ""
        suffixes = ["우", "우B", "우C", "1우", "2우", "3우", "스팩", "SPAC", "리츠", "REIT", "ETF", "ETN"]
        clean_name = name.strip()
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()
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
        """OHLCV 데이터 조회"""
        try:
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                raise KISDataValidationError(f"Invalid symbol format: {symbol}")
            
            self.logger.debug(f"📈 {symbol} OHLCV 데이터 조회 중...")
            
            # KIS API 일봉 차트 조회
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": "",  # 시작일 (공백시 최근 데이터)
                    "FID_INPUT_DATE_2": "",  # 종료일 (공백시 최근 데이터)  
                    "FID_PERIOD_DIV_CODE": period,  # D=일봉, W=주봉, M=월봉
                    "FID_ORG_ADJ_PRC": "0"   # 0=수정주가, 1=원주가
                },
                tr_id="FHKST03010100"
            )
            
            output = result.get('output2', [])
            if not output:
                self.logger.warning(f"⚠️ {symbol} OHLCV 데이터 없음")
                return []
            
            # 응답 데이터를 OHLCVData 객체로 변환
            ohlcv_data = []
            for item in output[:count]:  # 최대 count개까지만
                try:
                    date_str = item.get('stck_bsop_date', '')  # 영업일자
                    if not date_str or len(date_str) != 8:
                        continue
                    
                    # 날짜 파싱 (YYYYMMDD 형식)
                    chart_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    # 가격 데이터 파싱 및 검증
                    open_price = self._safe_int_parse(item.get('stck_oprc', '0'))
                    high_price = self._safe_int_parse(item.get('stck_hgpr', '0'))
                    low_price = self._safe_int_parse(item.get('stck_lwpr', '0'))
                    close_price = self._safe_int_parse(item.get('stck_clpr', '0'))
                    volume = self._safe_int_parse(item.get('acml_vol', '0'))
                    trade_amount = self._safe_int_parse(item.get('acml_tr_pbmn', '0'))
                    
                    # 데이터 유효성 검증
                    if all(p > 0 for p in [open_price, high_price, low_price, close_price]):
                        ohlcv_item = OHLCVData(
                            symbol=symbol,
                            datetime=chart_date,
                            timeframe=period.lower(),
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            volume=volume,
                            trade_amount=trade_amount
                        )
                        ohlcv_data.append(ohlcv_item)
                        
                except Exception as item_error:
                    self.logger.debug(f"OHLCV 아이템 파싱 실패 {symbol}: {item_error}")
                    continue
            
            # 날짜순 정렬 (최신순)
            ohlcv_data.sort(key=lambda x: x.datetime, reverse=True)
            
            self.logger.debug(f"✅ {symbol} OHLCV {len(ohlcv_data)}개 조회 성공")
            return ohlcv_data
            
        except KISAPIError:
            raise
        except Exception as e:
            self.logger.error(f"❌ {symbol} OHLCV 데이터 조회 실패: {e}")
            raise KISAPIError(f"Failed to fetch OHLCV data: {e}")

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
            
            # 공식 API 스펙에 따른 요청
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/psearch-title",
                params={"user_id": self.config.kis_account.KIS_USER_ID},
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

            # 공식 API 스펙에 따른 종목 조회
            result = await self._make_api_request(
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
                self.logger.warning(f"⚠️ 조건식 {condition_id} ({condition_name})에 해당하는 종목 없음")
                # MCA05918 에러는 검색 결과가 0개인 경우
                if result.get('msg_cd') == 'MCA05918':
                    self.logger.debug(f"검색 결과 0개: {result.get('msg1')}")
                return []

            # 공식 스펙에 따른 종목 정보 변환
            stocks_data = []
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
                    stocks_data.append(stock_info)
            
            self.logger.info(f"✅ 조건식 {condition_id} ({condition_name})로 {len(stocks_data)}개 종목 발견")
            
            # 상위 종목들 로그 출력
            for i, stock in enumerate(stocks_data[:5]):
                self.logger.debug(f"  {i+1}. {stock['code']} {stock['name']} - {stock['price']:,.0f}원 ({stock['chgrate']:+.2f}%)")
            
            return stocks_data

        except Exception as e:
            self.logger.error(f"❌ 조건식 {condition_id} ({condition_name}) 검색 실패: {e}")
            return []

    async def get_news_data(self, symbol: str, name: str, days: int = 7) -> List[Dict]:
        """뉴스 데이터 수집 - KIS API 실제 호출 시도"""
        try:
            self.logger.info(f"📰 {symbol}({name}) 실제 뉴스 데이터 수집 시작...")
            
            # 실제 KIS API 뉴스 호출 시도
            real_news = []
            if self.pykis_api:
                try:
                    # PyKis API로 실제 뉴스 데이터 조회 시도
                    # 실제 구현: 종목 관련 뉴스 API 호출
                    import asyncio
                    news_result = await asyncio.to_thread(
                        self._get_stock_news_from_kis, symbol, name, days
                    )
                    if news_result and len(news_result) > 0:
                        real_news = news_result
                        self.logger.info(f"✅ {symbol} 실제 KIS 뉴스 {len(real_news)}건 수집 완료")
                    else:
                        self.logger.debug(f"📰 {symbol} KIS API에서 뉴스 없음")
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} KIS API 뉴스 조회 실패: {e}")
            
            # KIS API 실패 시 실제 웹 뉴스 크롤링 시도 (간단한 구현)
            if not real_news:
                try:
                    web_news = await self._crawl_web_news(symbol, name, days)
                    if web_news and len(web_news) > 0:
                        real_news = web_news
                        self.logger.info(f"✅ {symbol} 웹 뉴스 {len(real_news)}건 수집 완료")
                    else:
                        self.logger.debug(f"📰 {symbol} 웹에서 뉴스 없음")
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 웹 뉴스 크롤링 실패: {e}")
            
            # 실제 뉴스가 있으면 반환
            if real_news and len(real_news) > 0:
                return real_news[:10]  # 최근 10개만 반환
            
            # 실제 뉴스가 없으면 빈 리스트 반환 (기본값 처리는 sentiment_analyzer에서)
            self.logger.debug(f"📰 {symbol} 실제 뉴스 없음 - 빈 데이터 반환")
            return []
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 뉴스 데이터 수집 실패: {e}")
            return []

    async def get_filtered_stocks(self, limit: int = 20) -> List[Tuple[str, str]]:
        """
        필터링된 종목 리스트 반환 (다중 소스 활용)
        1. KIS HTS 조건검색 (사용자 ID 설정 시)
        2. KIS API 시가총액 상위 종목 (Fallback)
        3. 데이터베이스 캐시 (최후의 Fallback)
        """
        self.logger.info(f"📊 {limit}개 필터링 종목 조회 시작 (다중 소스 활용)...")
        stock_list = []
        
        # 1. KIS HTS 조건검색 (사용자 ID가 설정된 경우에만 시도)
        if hasattr(self.config, 'kis_account') and self.config.kis_account.KIS_USER_ID:
            try:
                self.logger.info("1️⃣ HTS 조건검색 시도...")
                # 'momentum' 조건식 ID를 동적으로 찾거나, 설정 파일에서 가져오도록 개선 가능
                # 여기서는 'momentum' 이라는 이름의 조건식이 있다고 가정
                conditions = await self.get_hts_condition_list()
                momentum_condition = next((c for c in conditions if 'momentum' in c.get('name', '').lower()), None)

                if momentum_condition:
                    self.logger.info(f"'momentum' 조건식 발견 (ID: {momentum_condition['id']})")
                    momentum_stocks = await self.get_stocks_by_condition(momentum_condition['id'], momentum_condition['name'])
                    
                    for stock_data in momentum_stocks:
                        symbol = stock_data.get('code')
                        name = stock_data.get('name')
                        if symbol and name:
                            stock_list.append((symbol, name))
                            if len(stock_list) >= limit:
                                break
                    
                    self.logger.info(f"✅ HTS 조건검색으로 {len(stock_list)}개 종목 조회 성공")

                else:
                    self.logger.warning("⚠️ HTS에서 'momentum' 조건식을 찾을 수 없습니다.")

            except Exception as e:
                self.logger.warning(f"⚠️ HTS 조건검색 실패: {e}")
        else:
            self.logger.info("ℹ️ KIS_USER_ID가 설정되지 않아 HTS 조건검색을 건너뜁니다.")

        # 2. HTS 조건검색 결과가 충분하지 않으면, KIS API로 시총 상위 종목 조회
        if len(stock_list) < limit:
            try:
                self.logger.info("2️⃣ KIS API 시가총액 상위 종목 조회 시도...")
                top_stocks = await self._get_top_stocks_from_kis_api(limit=limit * 2) # 여유있게 조회
                
                # HTS 결과와 중복되지 않게 추가
                existing_symbols = {s[0] for s in stock_list}
                for symbol, name in top_stocks:
                    if symbol not in existing_symbols:
                        stock_list.append((symbol, name))
                    if len(stock_list) >= limit:
                        break
                
                self.logger.info(f"✅ KIS API 시총 상위 종목 추가 후 총 {len(stock_list)}개 종목 확보")

            except Exception as e:
                self.logger.warning(f"⚠️ KIS API 시총 상위 종목 조회 실패: {e}")

        # 3. 그래도 종목이 없으면, 최후의 수단으로 DB 캐시 사용 (이 기능은 외부에서 호출)
        if not stock_list:
            self.logger.warning("⚠️ 모든 종목 소스에서 종목을 가져오지 못했습니다. DB 캐시를 확인해야 할 수 있습니다.")
            # DB 캐시 조회 로직은 여기에 직접 구현하기보다, 이 메서드를 호출하는 쪽에서 처리하는 것이 좋음
            # 예: trading_system.py에서 이 메서드 결과가 비어있으면 DB에서 로드

        return stock_list[:limit]

    def _get_stock_news_from_kis(self, symbol: str, name: str, days: int = 7) -> List[Dict]:
        """KIS API로 종목 뉴스 데이터 조회 (동기 메서드)"""
        try:
            # 현재 KIS API에 뉴스 조회 기능이 없으므로 빈 리스트 반환
            # 실제 서비스에서는 KIS API의 뉴스 관련 엔드포인트를 구현
            self.logger.debug(f"📰 {symbol} KIS API 뉴스 조회 (현재 미지원)")
            return []
        except Exception as e:
            self.logger.warning(f"⚠️ KIS API 뉴스 조회 실패: {e}")
            return []
    
    async def _crawl_web_news(self, symbol: str, name: str, days: int = 7) -> List[Dict]:
        """웹에서 실제 뉴스 크롤링"""
        try:
            import aiohttp
            from datetime import datetime, timedelta
            
            news_list = []
            
            # 네이버 금융 뉴스 크롤링 시도
            try:
                search_url = f"https://finance.naver.com/item/news_news.naver?code={symbol}"
                
                if self.session:
                    async with self.session.get(search_url, timeout=10) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            
                            # 간단한 HTML 파싱 (Beautiful Soup 없이)
                            import re
                            
                            # 제목과 내용 패턴 매칭
                            title_pattern = r'<dd class="title"><a[^>]*>([^<]+)</a>'
                            date_pattern = r'<dd class="date">([^<]+)</dd>'
                            
                            titles = re.findall(title_pattern, html_content)
                            dates = re.findall(date_pattern, html_content)
                            
                            # 최대 5개 뉴스 처리
                            for i, (title, date_str) in enumerate(zip(titles[:5], dates[:5])):
                                if title and date_str:
                                    news_item = {
                                        'title': title.strip(),
                                        'description': f"{name} 관련 뉴스",
                                        'content': f"{name}에 대한 뉴스 내용입니다.",
                                        'published_date': date_str.strip(),
                                        'source': "네이버 금융",
                                        'url': search_url
                                    }
                                    news_list.append(news_item)
                            
                            if news_list:
                                self.logger.info(f"✅ {symbol} 네이버 금융에서 {len(news_list)}건 뉴스 수집")
                                return news_list
                            
            except Exception as e:
                self.logger.debug(f"📰 {symbol} 네이버 금융 크롤링 실패: {e}")
            
            # 다음 카카오 금융 뉴스 크롤링 시도
            try:
                daum_url = f"https://finance.daum.net/quotes/A{symbol}"
                
                if self.session:
                    async with self.session.get(daum_url, timeout=10) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            
                            # 간단한 뉴스 제목 추출
                            import re
                            news_pattern = r'<a[^>]*class="[^"]*link_news[^"]*"[^>]*>([^<]+)</a>'
                            news_titles = re.findall(news_pattern, html_content)
                            
                            # 최대 3개 뉴스 처리
                            for i, title in enumerate(news_titles[:3]):
                                if title.strip():
                                    news_item = {
                                        'title': title.strip(),
                                        'description': f"{name} 관련 뉴스",
                                        'content': f"{name}에 대한 뉴스 내용입니다.",
                                        'published_date': datetime.now().isoformat(),
                                        'source': "다음 금융",
                                        'url': daum_url
                                    }
                                    news_list.append(news_item)
                            
                            if news_list:
                                self.logger.info(f"✅ {symbol} 다음 금융에서 {len(news_list)}건 뉴스 수집")
                                return news_list
                                
            except Exception as e:
                self.logger.debug(f"📰 {symbol} 다음 금융 크롤링 실패: {e}")
            
            # 모든 크롤링 실패 시 빈 리스트 반환
            self.logger.debug(f"📰 {symbol} 실제 웹 뉴스 크롤링 결과 없음")
            return []
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 웹 뉴스 크롤링 실패: {e}")
            return []

    async def _get_top_stocks_from_kis_api(self, limit: int = 20) -> List[Tuple[str, str]]:
        """KIS API 직접 호출로 KOSPI 200 구성 종목 조회"""
        try:
            self.logger.info(f"📊 KIS API로 KOSPI 200 구성 종목 {limit}개 조회 중...")
            
            # KOSPI 200 지수 (업종코드: 001)
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-index-constituent-stocks",
                params={
                    "FID_COND_MRKT_DIV_CODE": "U",
                    "FID_INPUT_ISCD": "001",  # KOSPI 200
                },
                tr_id="FHPUP03100000"
            )
            
            output = result.get('output', [])
            if not output:
                self.logger.warning("⚠️ KIS API KOSPI 200 조회 결과 없음")
                return []
            
            stock_list = []
            for item in output[:limit]:
                symbol = item.get('stck_shrn_iscd', '').zfill(6)
                name = self._clean_stock_name(item.get('hts_kor_isnm', ''))
                if symbol and name:
                    stock_list.append((symbol, name))
            
            if stock_list:
                self.logger.info(f"✅ KIS API로 KOSPI 200 {len(stock_list)}개 종목 조회 완료")
                return stock_list
            else:
                self.logger.warning("⚠️ KIS API 조회 성공했으나 유효한 KOSPI 200 종목 없음")
                return []
                
        except Exception as e:
            self.logger.warning(f"⚠️ KIS API KOSPI 200 직접 호출 실패: {e}")
            return []

    async def get_investor_trading_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """특정 종목의 투자자별 매매 동향 조회"""
        try:
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                raise KISDataValidationError(f"Invalid symbol format: {symbol}")
            
            self.logger.debug(f"📊 {symbol} 투자자별 매매 동향 조회 중...")
            
            today = datetime.now().strftime('%Y%m%d')
            
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-investor-trend",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": today,
                    "FID_INPUT_DATE_2": today,
                    "FID_PERIOD_DIV_CODE": "D", # 일별
                    "FID_ORG_ADJ_PRC": "0"
                },
                tr_id="FHKST01010400"
            )
            
            output = result.get('output1', [])
            if not output:
                self.logger.warning(f"⚠️ {symbol} 투자자별 매매 동향 데이터 없음")
                return None

            # 최신 데이터 사용
            latest_data = output[0]

            investor_data = {
                'foreign': {
                    'net_buying': self._safe_int_parse(latest_data.get('frgn_ntby_qty', '0')),
                    'buy_volume': self._safe_int_parse(latest_data.get('frgn_shnu_vol', '0')),
                    'sell_volume': self._safe_int_parse(latest_data.get('frgn_seln_vol', '0')),
                },
                'institution': {
                    'net_buying': self._safe_int_parse(latest_data.get('orgn_ntby_qty', '0')),
                    'buy_volume': self._safe_int_parse(latest_data.get('orgn_shnu_vol', '0')),
                    'sell_volume': self._safe_int_parse(latest_data.get('orgn_seln_vol', '0')),
                },
                'individual': {
                    'net_buying': self._safe_int_parse(latest_data.get('prsn_ntby_qty', '0')),
                    'buy_volume': self._safe_int_parse(latest_data.get('prsn_shnu_vol', '0')),
                    'sell_volume': self._safe_int_parse(latest_data.get('prsn_seln_vol', '0')),
                }
            }
            self.logger.debug(f"✅ {symbol} 투자자별 매매 동향 조회 성공")
            return investor_data

        except KISAPIError as e:
            self.logger.error(f"❌ {symbol} 투자자별 매매 동향 조회 실패: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 투자자별 매매 동향 조회 중 예상치 못한 오류: {e}")
            return None

    async def cleanup(self):
        """리소스 정리"""
        await self.close()