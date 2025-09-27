#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Quota Management System
===========================

OpenAI API 쿼터 관리 및 백업 시스템
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from utils.logger import get_logger


class QuotaStatus(Enum):
    """API 쿼터 상태"""
    AVAILABLE = "available"
    WARNING = "warning"
    EXCEEDED = "exceeded"
    UNKNOWN = "unknown"


@dataclass
class QuotaInfo:
    """API 쿼터 정보"""
    status: QuotaStatus
    remaining_requests: Optional[int] = None
    reset_time: Optional[datetime] = None
    current_usage: Optional[float] = None
    limit: Optional[float] = None
    error_message: Optional[str] = None


class APIQuotaManager:
    """
    API 쿼터 관리자

    OpenAI API 사용량 모니터링 및 백업 시스템 관리
    """

    def __init__(self, config):
        self.config = config
        self.logger = get_logger("APIQuotaManager")
        self.quota_cache = {}
        self.last_check = None
        self.check_interval = 300  # 5분

        # OpenAI 클라이언트 초기화
        self.client = None
        self.api_available = False

        if not OPENAI_AVAILABLE:
            self.logger.warning("⚠️ OpenAI 모듈이 설치되지 않음")
            return

        from dotenv import load_dotenv
        load_dotenv(override=True)

        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('CHATGPT_API_KEY')
        if api_key and api_key.startswith('sk-'):
            try:
                self.client = openai.AsyncOpenAI(api_key=api_key)
                self.api_available = True
            except Exception as e:
                self.logger.error(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
                self.api_available = False
        else:
            self.logger.warning("⚠️ OpenAI API 키가 설정되지 않음")
            self.api_available = False

    async def check_quota_status(self, force_check: bool = False) -> QuotaInfo:
        """API 쿼터 상태 확인"""

        # 캐시된 결과 사용 (강제 체크가 아닌 경우)
        if not force_check and self.last_check:
            if datetime.now() - self.last_check < timedelta(seconds=self.check_interval):
                return self.quota_cache.get('openai', QuotaInfo(QuotaStatus.UNKNOWN))

        if not self.api_available:
            return QuotaInfo(
                status=QuotaStatus.UNKNOWN,
                error_message="OpenAI API 클라이언트를 사용할 수 없음"
            )

        try:
            # OpenAI API로 간단한 요청을 보내서 쿼터 상태 확인
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )

            quota_info = QuotaInfo(status=QuotaStatus.AVAILABLE)

            # 응답 헤더에서 쿼터 정보 추출 (가능한 경우)
            # OpenAI는 현재 사용량을 직접적으로 제공하지 않으므로
            # 성공적인 응답을 받으면 사용 가능한 것으로 간주

            self.quota_cache['openai'] = quota_info
            self.last_check = datetime.now()

            self.logger.info("✅ OpenAI API 쿼터 상태 정상")
            return quota_info

        except Exception as rate_limit_e:
            # OpenAI RateLimitError 체크 (openai 모듈이 있는 경우에만)
            if OPENAI_AVAILABLE and hasattr(openai, 'RateLimitError') and isinstance(rate_limit_e, openai.RateLimitError):
                quota_info = QuotaInfo(
                    status=QuotaStatus.EXCEEDED,
                    error_message=str(rate_limit_e)
                )
                self.quota_cache['openai'] = quota_info
                self.last_check = datetime.now()

                self.logger.error(f"❌ OpenAI API 쿼터 초과: {rate_limit_e}")
                return quota_info

            # 일반적인 예외로 처리
            quota_info = QuotaInfo(
                status=QuotaStatus.UNKNOWN,
                error_message=str(rate_limit_e)
            )
            self.quota_cache['openai'] = quota_info
            self.last_check = datetime.now()

            self.logger.error(f"❌ OpenAI API 호출 실패: {rate_limit_e}")
            return quota_info

    async def should_use_fallback(self, api_name: str = "openai") -> bool:
        """백업 분석기 사용 여부 결정"""
        quota_info = await self.check_quota_status()

        if quota_info.status in [QuotaStatus.EXCEEDED, QuotaStatus.UNKNOWN]:
            self.logger.warning(f"⚠️ {api_name} API 사용 불가, 백업 분석기로 전환")
            return True

        return False

    def get_quota_summary(self) -> Dict[str, Any]:
        """쿼터 상태 요약"""
        summary = {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "quotas": {}
        }

        for api_name, quota_info in self.quota_cache.items():
            summary["quotas"][api_name] = {
                "status": quota_info.status.value,
                "remaining_requests": quota_info.remaining_requests,
                "current_usage": quota_info.current_usage,
                "limit": quota_info.limit,
                "error_message": quota_info.error_message
            }

        return summary

    async def handle_quota_exceeded(self, api_name: str) -> Dict[str, Any]:
        """쿼터 초과 시 대응 방안"""
        self.logger.warning(f"🚨 {api_name} API 쿼터 초과 감지")

        response = {
            "action": "fallback_activated",
            "api_name": api_name,
            "timestamp": datetime.now().isoformat(),
            "recommendations": []
        }

        if api_name.lower() == "openai":
            response["recommendations"].extend([
                "Gemini 백업 분석기로 자동 전환",
                "OpenAI 플랫폼에서 사용량 확인 필요",
                "플랜 업그레이드 또는 크레딧 추가 고려",
                f"다음 확인 시간: {(datetime.now() + timedelta(seconds=self.check_interval)).strftime('%H:%M:%S')}"
            ])

        return response


# 글로벌 쿼터 매니저 인스턴스
quota_manager = None

def get_quota_manager(config=None):
    """글로벌 쿼터 매니저 인스턴스 반환"""
    global quota_manager
    if quota_manager is None and config:
        quota_manager = APIQuotaManager(config)
    return quota_manager