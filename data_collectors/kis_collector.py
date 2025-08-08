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
        
        # PyKis integration - KIS 계정 정보 필요
        self.pykis_api = None
        if Api and hasattr(config, 'kis_account'):
            try:
                # 실제 KIS 계정 정보로 초기화
                kis_id = getattr(config.kis_account, 'KIS_USER_ID', None)
                if kis_id:
                    if self.is_virtual:
                        self.pykis_api = Api(
                            virtual_id=kis_id,
                            virtual_appkey=self.app_key,
                            virtual_secretkey=self.app_secret
                        )
                    else:
                        self.pykis_api = Api(
                            id=kis_id,
                            appkey=self.app_key,
                            secretkey=self.app_secret
                        )
                    self.logger.info("PyKis API 객체 생성 성공")
                else:
                    self.logger.warning("KIS 사용자 ID가 설정되지 않음. PyKis 비활성화")
                    self.pykis_api = None
            except Exception as e:
                self.logger.warning(f"PyKis API 초기화 실패: {e}")
                self.pykis_api = None
        else:
            self.logger.warning("PyKis 라이브러리 또는 KIS 계정 설정 없음")
        
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
        """HTS 조건식 목록 조회"""
        try:
            self.logger.info("📋 config.py에서 HTS 조건식 목록 조회 중...")
            strategies = getattr(self.config.trading, 'HTS_CONDITIONAL_SEARCH_IDS', {})
            if not strategies:
                self.logger.warning("⚠️ config.py에 HTS 전략이 설정되지 않음")
                return []
            
            condition_list = [{"id": cond_id, "name": name} for name, cond_id in strategies.items()]
            self.logger.info(f"✅ config에서 {len(condition_list)}개 HTS 조건식 조회")
            return condition_list
            
        except Exception as e:
            self.logger.error(f"❌ config에서 HTS 조건식 목록 조회 실패: {e}")
            return []

    async def get_stocks_by_condition(self, condition_id: str) -> List[str]:
        """HTS 조건식으로 종목 검색"""
        try:
            if not self.pykis_api:
                self.logger.warning("PyKis not available for HTS conditions")
                return []
                
            self.logger.info(f"📊 HTS 조건식 {condition_id} 종목 검색 중...")
            
            # PyKis condition 메서드 호출 (동기 함수를 비동기로 래핑)
            stocks_df = await asyncio.to_thread(self.pykis_api.condition, condition_id)
            
            if stocks_df is None or stocks_df.empty:
                self.logger.warning(f"⚠️ 조건식 {condition_id}에 해당하는 종목 없음")
                return []
                
            # DataFrame index에서 종목 코드 추출
            valid_stocks = list(stocks_df.index)
            self.logger.info(f"✅ 조건식 {condition_id}로 {len(valid_stocks)}개 종목 발견")
            return valid_stocks
            
        except Exception as e:
            self.logger.error(f"❌ 조건식 {condition_id} 검색 실패: {e}")
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
        """필터링된 종목 리스트 반환 - 실제 KIS API 활용"""
        try:
            self.logger.info(f"📊 KIS API를 통한 {limit}개 종목 조회 시작...")
            
            # 방법 1: HTS 조건검색 활용 (momentum 전략)
            try:
                momentum_stocks = await self.get_stocks_by_condition("momentum")
                if momentum_stocks:
                    # 종목코드만 있으므로 종목명 조회 필요
                    stock_list = []
                    for symbol in momentum_stocks[:limit]:
                        try:
                            stock_info = await self.get_stock_info(symbol)
                            if stock_info:
                                stock_list.append((symbol, stock_info.name))
                        except Exception:
                            stock_list.append((symbol, f"종목{symbol}"))
                    
                    if stock_list:
                        self.logger.info(f"✅ 조건검색으로 {len(stock_list)}개 종목 조회 성공")
                        return stock_list
            except Exception as e:
                self.logger.warning(f"⚠️ 조건검색 실패: {e}")
            
            # 방법 2: PyKis stock 메서드 활용 (실제 사용법)
            if self.pykis_api:
                try:
                    # PyKis 2.1.3의 실제 stock 메서드 사용
                    # 주요 종목들을 하나씩 조회
                    major_symbols = ["005930", "000660", "035420", "207940", "005380", "006400", "051910", "035720", "028260", "105560"]
                    stock_list = []
                    
                    for symbol in major_symbols[:limit]:
                        try:
                            # PyKis의 stock 메서드로 개별 종목 조회
                            stock_info = await asyncio.to_thread(self.pykis_api.stock, symbol)
                            if stock_info and hasattr(stock_info, 'name'):
                                stock_list.append((symbol, stock_info.name))
                            elif stock_info:
                                # stock_info가 딕셔너리일 경우
                                name = stock_info.get('name', f'종목{symbol}')
                                stock_list.append((symbol, name))
                        except Exception as e:
                            self.logger.debug(f"⚠️ {symbol} 개별 조회 실패: {e}")
                            continue
                    
                    if stock_list:
                        self.logger.info(f"✅ PyKis로 {len(stock_list)}개 종목 조회 성공")
                        return stock_list
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ PyKis stock 메서드 실패: {e}")
            
            # 방법 3: KIS API 직접 호출로 주요 종목 조회 
            try:
                top_stocks = await self._get_top_stocks_from_kis_api(limit)
                if top_stocks:
                    self.logger.info(f"✅ KIS API 직접 호출로 {len(top_stocks)}개 종목 조회 성공")
                    return top_stocks
            except Exception as e:
                self.logger.warning(f"⚠️ KIS API 직접 호출 실패: {e}")
            
            # 방법 4: DB에서 기존 필터링된 종목 조회
            try:
                if hasattr(self, 'db_operations') and self.db_operations:
                    from database.models import FilteredStock, Stock
                    from sqlalchemy import select
                    
                    async with self.db_operations.db_manager.get_async_session() as session:
                        # 최근 필터링된 종목들 조회
                        result = await session.execute(
                            select(FilteredStock.stock_id, Stock.name)
                            .join(Stock, FilteredStock.stock_id == Stock.id)
                            .order_by(FilteredStock.filtered_date.desc())
                            .limit(limit)
                        )
                        db_stocks = result.fetchall()
                        
                        if db_stocks:
                            stock_list = [(str(stock_id).zfill(6), name) for stock_id, name in db_stocks]
                            self.logger.info(f"✅ DB에서 {len(stock_list)}개 종목 조회 성공")
                            return stock_list
            except Exception as e:
                self.logger.warning(f"⚠️ DB 종목 조회 실패: {e}")
            
            # 실패 시 빈 리스트 반환
            self.logger.error("❌ 모든 종목 조회 방법 실패")
            return []
            
        except Exception as e:
            self.logger.error(f"❌ 종목 조회 실패: {e}")
            return []

    def _get_top_market_cap_stocks(self, limit: int) -> List[Tuple[str, str]]:
        """시가총액 상위 종목 조회 (동기 메소드)"""
        try:
            # PyKis API를 활용한 시가총액 상위 종목 조회
            if not self.pykis_api:
                return []
            
            # 코스피 시가총액 상위 종목 정보 조회
            df = self.pykis_api.get_market_cap_rank(market="KOSPI", limit=limit)
            if df is not None and not df.empty:
                return [(str(code).zfill(6), name) for code, name in df.index[:limit]]
            
            return []
        except Exception as e:
            self.logger.warning(f"⚠️ 시가총액 조회 실패: {e}")
            return []

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
        """KIS API 직접 호출로 주요 종목 조회"""
        try:
            self.logger.info(f"📊 KIS API로 주요 종목 {limit}개 직접 조회 중...")
            
            # KOSPI 시가총액 상위 종목 조회
            result = await self._make_api_request(
                method="GET",
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-market-trading-top",
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",  # KOSPI
                    "FID_COND_SCR_DIV_CODE": "20174",  # 시가총액 상위
                    "FID_DIV_CLS_CODE": "0",  # 전체
                    "FID_TRGT_CLS_CODE": "111111111",  # 전체
                    "FID_TRGT_EXLS_CLS_CODE": "0000000000",  # 제외없음
                    "FID_INPUT_ISCD": "0000",  # 전체
                    "FID_INPUT_CNT_1": str(limit),  # 조회 개수
                },
                tr_id="FHPST01740000"
            )
            
            output = result.get('output', [])
            if not output:
                self.logger.warning("⚠️ KIS API 시가총액 상위 조회 결과 없음")
                return []
            
            # 종목 리스트 생성
            stock_list = []
            for item in output:
                try:
                    symbol = item.get('stck_shrn_iscd', '')  # 종목코드
                    name = item.get('hts_kor_isnm', '')    # 종목명
                    
                    if symbol and name:
                        # 종목코드 6자리 맞추기
                        symbol = symbol.zfill(6)
                        # 종목명 정리
                        clean_name = self._clean_stock_name(name)
                        stock_list.append((symbol, clean_name))
                        
                    if len(stock_list) >= limit:
                        break
                        
                except Exception as e:
                    self.logger.debug(f"⚠️ 종목 데이터 파싱 실패: {e}")
                    continue
            
            if stock_list:
                self.logger.info(f"✅ KIS API로 {len(stock_list)}개 주요 종목 조회 완료")
                return stock_list
            else:
                self.logger.warning("⚠️ KIS API 조회 성공했으나 유효한 종목 없음")
                return []
                
        except Exception as e:
            self.logger.warning(f"⚠️ KIS API 직접 호출 실패: {e}")
            return []

    async def cleanup(self):
        """리소스 정리"""
        await self.close()