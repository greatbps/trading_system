#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/http_client.py

안정적인 HTTP 클라이언트 세션 관리
- aiohttp 세션 풀링 및 재사용
- 자동 재시도 및 에러 처리
- 연결 타임아웃 및 백오프 정책
- 네트워크 에러 복구
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, Callable
from datetime import datetime, timedelta
import json
import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError, ClientResponseError
from contextlib import asynccontextmanager
import weakref
import time

class HTTPClientConfig:
    """HTTP 클라이언트 설정"""
    
    # 기본 타임아웃 설정 (초)
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 30
    TOTAL_TIMEOUT = 60
    
    # 재시도 설정
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 1.0  # 지수 백오프 계수
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}  # 재시도할 HTTP 상태 코드
    
    # 연결 풀 설정
    CONNECTION_POOL_SIZE = 100
    CONNECTION_LIMIT_PER_HOST = 30
    CONNECTION_TTL = 300  # 연결 유지 시간 (초)
    
    # 세션 설정
    SESSION_TIMEOUT = 1800  # 30분 후 세션 재생성
    
    # User-Agent
    USER_AGENT = "TradingSystem/1.0 (Python aiohttp)"


class RetryableHTTPError(Exception):
    """재시도 가능한 HTTP 에러"""
    pass


class NonRetryableHTTPError(Exception):
    """재시도 불가능한 HTTP 에러"""
    pass


class HTTPSessionManager:
    """
    안정적인 aiohttp 세션 관리자
    
    주요 기능:
    - 세션 풀링 및 재사용
    - 자동 재시도 및 에러 처리
    - 연결 타임아웃 관리
    - 메트릭 수집
    """
    
    _instances: Dict[str, 'HTTPSessionManager'] = {}
    _session_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    
    def __init__(self, name: str = "default", config: HTTPClientConfig = None):
        self.name = name
        self.config = config or HTTPClientConfig()
        self.logger = logging.getLogger(f"HTTPSessionManager.{name}")
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_created_at: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
        # 메트릭
        self.metrics = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'retries_total': 0,
            'session_recreations': 0,
            'last_error': None,
            'last_error_time': None
        }
        
        # 인스턴스 등록
        HTTPSessionManager._instances[name] = self
        HTTPSessionManager._session_refs[name] = self
    
    @classmethod
    def get_instance(cls, name: str = "default", config: HTTPClientConfig = None) -> 'HTTPSessionManager':
        """싱글톤 인스턴스 반환"""
        if name not in cls._instances:
            cls._instances[name] = cls(name, config)
        return cls._instances[name]
    
    async def _create_session(self) -> aiohttp.ClientSession:
        """새로운 aiohttp 세션 생성"""
        self.logger.info(f"Creating new HTTP session: {self.name}")
        
        # 타임아웃 설정
        timeout = ClientTimeout(
            total=self.config.TOTAL_TIMEOUT,
            connect=self.config.CONNECT_TIMEOUT,
            sock_read=self.config.READ_TIMEOUT
        )
        
        # 커넥터 설정
        connector = aiohttp.TCPConnector(
            limit=self.config.CONNECTION_POOL_SIZE,
            limit_per_host=self.config.CONNECTION_LIMIT_PER_HOST,
            ttl_dns_cache=self.config.CONNECTION_TTL,
            use_dns_cache=True,
            enable_cleanup_closed=True
        )
        
        # 헤더 설정
        headers = {
            'User-Agent': self.config.USER_AGENT,
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            raise_for_status=False  # 수동으로 상태 코드 체크
        )
        
        self._session_created_at = datetime.now()
        self.metrics['session_recreations'] += 1
        
        return session
    
    async def get_session(self) -> aiohttp.ClientSession:
        """세션 반환 (필요시 생성/재생성)"""
        async with self._lock:
            # 세션이 없거나 만료된 경우
            if (self._session is None or 
                self._session.closed or 
                (self._session_created_at and 
                 datetime.now() - self._session_created_at > timedelta(seconds=self.config.SESSION_TIMEOUT))):
                
                # 기존 세션이 있으면 정리
                if self._session and not self._session.closed:
                    await self._session.close()
                
                self._session = await self._create_session()
            
            return self._session
    
    async def _should_retry(self, error: Exception, status_code: Optional[int] = None, 
                          retry_count: int = 0) -> bool:
        """재시도 여부 판단"""
        if retry_count >= self.config.MAX_RETRIES:
            return False
        
        # HTTP 상태 코드 기반 재시도
        if status_code and status_code in self.config.RETRY_STATUS_CODES:
            return True
        
        # 네트워크 에러 재시도
        if isinstance(error, (
            ClientConnectorError,
            asyncio.TimeoutError,
            aiohttp.ServerTimeoutError,
            aiohttp.ClientPayloadError,
            ConnectionResetError,
        )):
            return True
        
        return False
    
    async def _calculate_backoff_delay(self, retry_count: int) -> float:
        """백오프 지연 시간 계산"""
        base_delay = self.config.RETRY_BACKOFF_FACTOR
        delay = base_delay * (2 ** retry_count)  # 지수 백오프
        
        # 지터 추가 (±25%)
        import random
        jitter = delay * 0.25 * (2 * random.random() - 1)
        
        return max(0.1, delay + jitter)  # 최소 0.1초
    
    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        HTTP 요청 실행 (재시도 로직 포함)
        
        Args:
            method: HTTP 메서드 (GET, POST, etc.)
            url: 요청 URL
            **kwargs: aiohttp 요청 파라미터
        
        Returns:
            ClientResponse 객체
        
        Raises:
            NonRetryableHTTPError: 재시도 불가능한 에러
            RetryableHTTPError: 재시도 가능한 에러 (최대 재시도 횟수 초과)
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.MAX_RETRIES:
            try:
                self.metrics['requests_total'] += 1
                
                # 세션 획득
                session = await self.get_session()
                
                # 요청 실행
                start_time = time.time()
                response = await session.request(method, url, **kwargs)
                elapsed = time.time() - start_time
                
                self.logger.debug(f"{method} {url} -> {response.status} ({elapsed:.3f}s)")
                
                # 성공적인 응답 처리
                if response.status < 400:
                    self.metrics['requests_successful'] += 1
                    return response
                
                # 4xx 에러는 일반적으로 재시도하지 않음 (429 제외)
                if 400 <= response.status < 500 and response.status not in self.config.RETRY_STATUS_CODES:
                    self.metrics['requests_failed'] += 1
                    error_text = await response.text()
                    await response.release()
                    raise NonRetryableHTTPError(
                        f"HTTP {response.status}: {error_text[:200]}"
                    )
                
                # 재시도 가능한 상태 코드
                if await self._should_retry(None, response.status, retry_count):
                    await response.release()
                    last_error = Exception(f"HTTP {response.status}")
                else:
                    self.metrics['requests_failed'] += 1
                    error_text = await response.text()
                    await response.release()
                    raise RetryableHTTPError(
                        f"HTTP {response.status}: {error_text[:200]} (after {retry_count} retries)"
                    )
            
            except Exception as e:
                # 재시도 불가능한 에러인지 확인
                if isinstance(e, (NonRetryableHTTPError, RetryableHTTPError)):
                    raise
                
                # 재시도 가능한지 확인
                if await self._should_retry(e, None, retry_count):
                    last_error = e
                    self.logger.warning(
                        f"Request failed (attempt {retry_count + 1}): {e}. Retrying..."
                    )
                else:
                    self.metrics['requests_failed'] += 1
                    self.metrics['last_error'] = str(e)
                    self.metrics['last_error_time'] = datetime.now()
                    raise RetryableHTTPError(
                        f"Request failed after {retry_count} retries: {e}"
                    )
            
            # 재시도 전 백오프 지연
            if retry_count < self.config.MAX_RETRIES:
                delay = await self._calculate_backoff_delay(retry_count)
                self.logger.debug(f"Backing off for {delay:.3f}s before retry {retry_count + 1}")
                await asyncio.sleep(delay)
                
                self.metrics['retries_total'] += 1
                retry_count += 1
        
        # 최대 재시도 횟수 초과
        self.metrics['requests_failed'] += 1
        self.metrics['last_error'] = str(last_error)
        self.metrics['last_error_time'] = datetime.now()
        raise RetryableHTTPError(
            f"Request failed after {self.config.MAX_RETRIES} retries: {last_error}"
        )
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET 요청"""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """POST 요청"""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """PUT 요청"""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """DELETE 요청"""
        return await self.request('DELETE', url, **kwargs)
    
    async def json_request(self, method: str, url: str, json_data: Dict = None, 
                          **kwargs) -> Dict[str, Any]:
        """
        JSON 요청/응답 처리
        
        Args:
            method: HTTP 메서드
            url: 요청 URL  
            json_data: JSON 데이터 (POST/PUT 시)
            **kwargs: 기타 요청 파라미터
        
        Returns:
            JSON 응답 데이터
        """
        # JSON 헤더 설정
        headers = kwargs.get('headers', {})
        headers['Content-Type'] = 'application/json'
        kwargs['headers'] = headers
        
        # JSON 데이터 설정
        if json_data:
            kwargs['data'] = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
        
        response = await self.request(method, url, **kwargs)
        
        try:
            response_data = await response.json()
            await response.release()
            return response_data
        except json.JSONDecodeError as e:
            text = await response.text()
            await response.release()
            raise ValueError(f"Invalid JSON response: {e}, content: {text[:200]}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 반환"""
        metrics = self.metrics.copy()
        
        # 성공률 계산
        total_requests = metrics['requests_total']
        if total_requests > 0:
            metrics['success_rate'] = (metrics['requests_successful'] / total_requests) * 100
        else:
            metrics['success_rate'] = 0.0
        
        # 세션 정보
        metrics['session_active'] = self._session is not None and not self._session.closed
        metrics['session_age_seconds'] = 0
        if self._session_created_at:
            metrics['session_age_seconds'] = (datetime.now() - self._session_created_at).total_seconds()
        
        return metrics
    
    async def close(self):
        """세션 정리"""
        async with self._lock:
            if self._session and not self._session.closed:
                self.logger.info(f"Closing HTTP session: {self.name}")
                await self._session.close()
                self._session = None
                self._session_created_at = None
    
    async def __aenter__(self):
        """Context manager 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        await self.close()


# 전역 세션 관리자 팩토리
@asynccontextmanager
async def get_http_session(name: str = "default", config: HTTPClientConfig = None):
    """
    HTTP 세션 컨텍스트 매니저
    
    사용법:
        async with get_http_session("kis_api") as http:
            response = await http.get("https://api.example.com/data")
    """
    session_manager = HTTPSessionManager.get_instance(name, config)
    try:
        yield session_manager
    finally:
        # 세션은 싱글톤으로 관리되므로 여기서 닫지 않음
        pass


# KIS API 전용 설정
class KISHTTPConfig(HTTPClientConfig):
    """KIS API 전용 HTTP 설정"""
    
    CONNECT_TIMEOUT = 15
    READ_TIMEOUT = 45
    TOTAL_TIMEOUT = 60
    
    MAX_RETRIES = 2
    RETRY_BACKOFF_FACTOR = 0.5
    
    CONNECTION_LIMIT_PER_HOST = 20
    
    USER_AGENT = "KISCollector/1.0 (Python aiohttp)"


# 뉴스 API 전용 설정
class NewsHTTPConfig(HTTPClientConfig):
    """뉴스 API 전용 HTTP 설정"""
    
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 30
    TOTAL_TIMEOUT = 45
    
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 1.0
    
    USER_AGENT = "NewsCollector/1.0 (Python aiohttp)"


async def cleanup_all_sessions():
    """모든 HTTP 세션 정리"""
    logger = logging.getLogger("HTTPSessionManager")
    logger.info("Cleaning up all HTTP sessions...")
    
    for name, session_manager in list(HTTPSessionManager._instances.items()):
        try:
            await session_manager.close()
        except Exception as e:
            logger.error(f"Error closing session {name}: {e}")
    
    HTTPSessionManager._instances.clear()
    HTTPSessionManager._session_refs.clear()
    
    logger.info("All HTTP sessions cleaned up")


# 편의 함수들
async def safe_get(url: str, session_name: str = "default", **kwargs) -> aiohttp.ClientResponse:
    """안전한 GET 요청"""
    async with get_http_session(session_name) as http:
        return await http.get(url, **kwargs)


async def safe_post(url: str, session_name: str = "default", **kwargs) -> aiohttp.ClientResponse:
    """안전한 POST 요청"""
    async with get_http_session(session_name) as http:
        return await http.post(url, **kwargs)


async def safe_json_request(method: str, url: str, json_data: Dict = None,
                           session_name: str = "default", **kwargs) -> Dict[str, Any]:
    """안전한 JSON 요청"""
    async with get_http_session(session_name) as http:
        return await http.json_request(method, url, json_data, **kwargs)