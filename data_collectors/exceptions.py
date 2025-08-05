#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/exceptions.py

Custom exception classes for KIS API Collector

These exceptions provide specific error handling for different types of
failures that can occur when interacting with the KIS API.

Author: AI Trading System
Version: 2.0.0
Last Updated: 2025-01-04
"""

from typing import Optional, Dict, Any
from datetime import datetime


class KISAPIError(Exception):
    """
    Base exception for all KIS API related errors
    
    Attributes:
        message: Error message
        error_code: API-specific error code (if available)
        response_data: Raw response data from API (if available)
        timestamp: When the error occurred
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.response_data = response_data
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            'exception_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'response_data': self.response_data,
            'timestamp': self.timestamp.isoformat()
        }
        
    def __str__(self) -> str:
        error_parts = [self.message]
        if self.error_code:
            error_parts.append(f"Error Code: {self.error_code}")
        return " | ".join(error_parts)


class KISAuthenticationError(KISAPIError):
    """
    Raised when authentication with KIS API fails
    
    This can happen due to:
    - Invalid API credentials
    - Expired access token
    - Invalid token format
    - Authentication server issues
    """
    pass


class KISRateLimitError(KISAPIError):
    """
    Raised when API rate limits are exceeded
    
    KIS API has a limit of 20 requests per second.
    This exception includes retry information.
    """
    
    def __init__(
        self, 
        message: str, 
        retry_after: Optional[int] = None,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, response_data)
        self.retry_after = retry_after  # Seconds to wait before retry
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['retry_after'] = self.retry_after
        return data


class KISNetworkError(KISAPIError):
    """
    Raised when network-related errors occur
    
    This includes:
    - Connection timeouts
    - DNS resolution failures
    - Network unreachable
    - SSL/TLS errors
    """
    
    def __init__(
        self, 
        message: str, 
        original_exception: Optional[Exception] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.original_exception = original_exception
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        if self.original_exception:
            data['original_exception'] = {
                'type': self.original_exception.__class__.__name__,
                'message': str(self.original_exception)
            }
        return data


class KISDataValidationError(KISAPIError):
    """
    Raised when data validation fails
    
    This occurs when:
    - Invalid stock symbols (not 6 digits)
    - Invalid price data (negative or zero prices)
    - Invalid date formats
    - Missing required fields
    """
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        expected_format: Optional[str] = None
    ):
        super().__init__(message)
        self.field_name = field_name
        self.field_value = field_value
        self.expected_format = expected_format
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'field_name': self.field_name,
            'field_value': self.field_value,
            'expected_format': self.expected_format
        })
        return data


class KISServerError(KISAPIError):
    """
    Raised when KIS API server returns 5xx errors
    
    This indicates server-side issues that may be temporary.
    These errors should typically be retried with exponential backoff.
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: int,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, response_data)
        self.status_code = status_code
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['status_code'] = self.status_code
        return data


class KISClientError(KISAPIError):
    """
    Raised when KIS API returns 4xx client errors
    
    This indicates issues with the request itself:
    - Invalid parameters
    - Missing required fields
    - Invalid request format
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: int,
        error_code: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, response_data)
        self.status_code = status_code
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['status_code'] = self.status_code
        return data


class KISQuotaExceededError(KISAPIError):
    """
    Raised when API quotas are exceeded
    
    Different from rate limiting - this is about daily/monthly quotas.
    """
    
    def __init__(
        self, 
        message: str, 
        quota_type: str,
        reset_time: Optional[datetime] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.quota_type = quota_type  # 'daily', 'monthly', etc.
        self.reset_time = reset_time
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'quota_type': self.quota_type,
            'reset_time': self.reset_time.isoformat() if self.reset_time else None
        })
        return data


class KISCircuitBreakerError(KISAPIError):
    """
    Raised when circuit breaker is open
    
    This prevents making requests when the API is experiencing issues.
    """
    
    def __init__(
        self, 
        message: str, 
        failure_count: int,
        recovery_time: Optional[datetime] = None
    ):
        super().__init__(message)
        self.failure_count = failure_count
        self.recovery_time = recovery_time
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'failure_count': self.failure_count,
            'recovery_time': self.recovery_time.isoformat() if self.recovery_time else None
        })
        return data


class KISMarketClosedError(KISAPIError):
    """
    Raised when attempting to access market data during closed hours
    
    Korean stock market hours: 9:00 AM - 3:30 PM KST
    """
    
    def __init__(
        self, 
        message: str = "Korean stock market is currently closed",
        market_open_time: Optional[str] = None,
        market_close_time: Optional[str] = None
    ):
        super().__init__(message)
        self.market_open_time = market_open_time or "09:00"
        self.market_close_time = market_close_time or "15:30"
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'market_open_time': self.market_open_time,
            'market_close_time': self.market_close_time
        })
        return data


class KISHTSError(KISAPIError):
    """
    Raised when HTS (Home Trading System) operations fail
    
    This is specific to HTS conditional search functionality.
    """
    
    def __init__(
        self, 
        message: str, 
        condition_id: Optional[str] = None,
        operation: Optional[str] = None
    ):
        super().__init__(message)
        self.condition_id = condition_id
        self.operation = operation  # 'load', 'search', 'list', etc.
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'condition_id': self.condition_id,
            'operation': self.operation
        })
        return data


class KISOrderError(KISAPIError):
    """
    Raised when trading order operations fail
    
    This includes order placement, cancellation, and status checks.
    """
    
    def __init__(
        self, 
        message: str, 
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        order_type: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_code)
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type
        })
        return data


# Exception mapping for HTTP status codes
def map_http_status_to_exception(
    status_code: int, 
    message: str, 
    error_code: Optional[str] = None,
    response_data: Optional[Dict[str, Any]] = None
) -> KISAPIError:
    """
    Map HTTP status codes to appropriate KIS exceptions
    
    Args:
        status_code: HTTP status code
        message: Error message
        error_code: API-specific error code
        response_data: Raw response data
        
    Returns:
        Appropriate KISAPIError subclass
    """
    if status_code == 401:
        return KISAuthenticationError(message, error_code, response_data)
    elif status_code == 429:
        return KISRateLimitError(message, error_code=error_code, response_data=response_data)
    elif 400 <= status_code < 500:
        return KISClientError(message, status_code, error_code, response_data)
    elif 500 <= status_code < 600:
        return KISServerError(message, status_code, error_code, response_data)
    else:
        return KISAPIError(message, error_code, response_data)


# Utility functions for exception handling
def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception represents a retryable error
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the error should be retried
    """
    # Network errors are generally retryable
    if isinstance(exception, KISNetworkError):
        return True
        
    # Server errors (5xx) are typically retryable
    if isinstance(exception, KISServerError):
        return True
        
    # Rate limit errors are retryable with backoff
    if isinstance(exception, KISRateLimitError):
        return True
        
    # Authentication errors might be retryable after token refresh
    if isinstance(exception, KISAuthenticationError):
        return True
        
    # Client errors and validation errors are not retryable
    return False


def get_retry_delay(exception: Exception, attempt: int) -> float:
    """
    Get recommended retry delay for an exception
    
    Args:
        exception: Exception that occurred
        attempt: Current attempt number (0-based)
        
    Returns:
        Delay in seconds before retry
    """
    base_delay = 1.0
    max_delay = 60.0
    
    if isinstance(exception, KISRateLimitError) and exception.retry_after:
        return float(exception.retry_after)
        
    # Exponential backoff with jitter
    import random
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, 0.1 * delay)
    
    return delay + jitter


def format_exception_for_logging(exception: Exception) -> Dict[str, Any]:
    """
    Format exception for structured logging
    
    Args:
        exception: Exception to format
        
    Returns:
        Dictionary suitable for JSON logging
    """
    if isinstance(exception, KISAPIError):
        return exception.to_dict()
    else:
        return {
            'exception_type': exception.__class__.__name__,
            'message': str(exception),
            'timestamp': datetime.now().isoformat()
        }


# Context manager for exception handling
class KISErrorHandler:
    """
    Context manager for standardized KIS API error handling
    
    Usage:
        async with KISErrorHandler(logger) as handler:
            result = await api_call()
            return result
    """
    
    def __init__(self, logger, operation_name: str = "API operation"):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation_name}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time if self.start_time else None
        
        if exc_type is None:
            self.logger.debug(f"Completed {self.operation_name} in {duration}")
            return False
            
        if isinstance(exc_val, KISAPIError):
            # Log structured error information
            error_info = exc_val.to_dict()
            error_info['operation'] = self.operation_name
            error_info['duration'] = str(duration) if duration else None
            
            if isinstance(exc_val, (KISNetworkError, KISServerError)):
                self.logger.warning(f"Retryable error in {self.operation_name}", extra=error_info)
            else:
                self.logger.error(f"Error in {self.operation_name}", extra=error_info)
        else:
            # Handle non-KIS exceptions
            self.logger.error(
                f"Unexpected error in {self.operation_name}: {exc_val}", 
                extra={
                    'exception_type': exc_type.__name__ if exc_type else 'Unknown',
                    'operation': self.operation_name,
                    'duration': str(duration) if duration else None
                }
            )
        
        # Don't suppress the exception
        return False