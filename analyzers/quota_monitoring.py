#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced API Quota Monitoring System
====================================

고급 API 쿼터 모니터링 및 알림 시스템
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from analyzers.api_quota_manager import APIQuotaManager, QuotaStatus, QuotaInfo
from utils.logger import get_logger


@dataclass
class QuotaHistoryEntry:
    """쿼터 사용 이력 항목"""
    timestamp: datetime
    api_name: str
    status: QuotaStatus
    usage_percentage: Optional[float] = None
    error_message: Optional[str] = None
    requests_count: Optional[int] = None


@dataclass
class QuotaAlert:
    """쿼터 알림 정보"""
    alert_type: str  # warning, critical, exceeded
    api_name: str
    message: str
    timestamp: datetime
    usage_percentage: Optional[float] = None
    recommendation: str = ""


class QuotaMonitor:
    """
    고급 쿼터 모니터링 시스템

    기능:
    - 쿼터 사용량 추적 및 기록
    - 임계값 기반 알림
    - 사용 패턴 분석
    - 예측 기반 경고
    """

    def __init__(self, config):
        self.config = config
        self.logger = get_logger("QuotaMonitor")
        self.quota_manager = APIQuotaManager(config)

        # 설정
        self.history_file = Path("data/quota_history.json")
        self.alerts_file = Path("data/quota_alerts.json")
        self.max_history_days = 30

        # 알림 임계값 (퍼센트)
        self.warning_threshold = 75.0
        self.critical_threshold = 90.0

        # 데이터 디렉토리 생성
        self.history_file.parent.mkdir(exist_ok=True)

        # 이력 및 알림 데이터
        self.history: List[QuotaHistoryEntry] = []
        self.alerts: List[QuotaAlert] = []

        # 데이터 로드
        self._load_history()
        self._load_alerts()

    def _load_history(self):
        """이력 데이터 로드"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for entry_data in data:
                    entry = QuotaHistoryEntry(
                        timestamp=datetime.fromisoformat(entry_data['timestamp']),
                        api_name=entry_data['api_name'],
                        status=QuotaStatus(entry_data['status']),
                        usage_percentage=entry_data.get('usage_percentage'),
                        error_message=entry_data.get('error_message'),
                        requests_count=entry_data.get('requests_count')
                    )
                    self.history.append(entry)

                # 오래된 이력 제거
                cutoff_date = datetime.now() - timedelta(days=self.max_history_days)
                self.history = [h for h in self.history if h.timestamp > cutoff_date]

                self.logger.info(f"📚 쿼터 이력 {len(self.history)}개 로드 완료")

        except Exception as e:
            self.logger.warning(f"⚠️ 쿼터 이력 로드 실패: {e}")
            self.history = []

    def _load_alerts(self):
        """알림 데이터 로드"""
        try:
            if self.alerts_file.exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for alert_data in data:
                    alert = QuotaAlert(
                        alert_type=alert_data['alert_type'],
                        api_name=alert_data['api_name'],
                        message=alert_data['message'],
                        timestamp=datetime.fromisoformat(alert_data['timestamp']),
                        usage_percentage=alert_data.get('usage_percentage'),
                        recommendation=alert_data.get('recommendation', '')
                    )
                    self.alerts.append(alert)

                # 오래된 알림 제거 (7일)
                cutoff_date = datetime.now() - timedelta(days=7)
                self.alerts = [a for a in self.alerts if a.timestamp > cutoff_date]

                self.logger.info(f"🔔 쿼터 알림 {len(self.alerts)}개 로드 완료")

        except Exception as e:
            self.logger.warning(f"⚠️ 쿼터 알림 로드 실패: {e}")
            self.alerts = []

    def _save_history(self):
        """이력 데이터 저장"""
        try:
            data = []
            for entry in self.history:
                entry_dict = asdict(entry)
                entry_dict['timestamp'] = entry.timestamp.isoformat()
                entry_dict['status'] = entry.status.value
                data.append(entry_dict)

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"❌ 쿼터 이력 저장 실패: {e}")

    def _save_alerts(self):
        """알림 데이터 저장"""
        try:
            data = []
            for alert in self.alerts:
                alert_dict = asdict(alert)
                alert_dict['timestamp'] = alert.timestamp.isoformat()
                data.append(alert_dict)

            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"❌ 쿼터 알림 저장 실패: {e}")

    async def check_and_record_quota(self, api_name: str = "openai") -> QuotaInfo:
        """쿼터 확인 및 기록"""
        quota_info = await self.quota_manager.check_quota_status(force_check=True)

        # 이력에 추가
        history_entry = QuotaHistoryEntry(
            timestamp=datetime.now(),
            api_name=api_name,
            status=quota_info.status,
            usage_percentage=quota_info.current_usage,
            error_message=quota_info.error_message,
            requests_count=quota_info.remaining_requests
        )

        self.history.append(history_entry)

        # 알림 체크
        await self._check_alerts(quota_info, api_name)

        # 데이터 저장
        self._save_history()

        return quota_info

    async def _check_alerts(self, quota_info: QuotaInfo, api_name: str):
        """알림 조건 체크"""
        now = datetime.now()

        # 쿼터 초과 알림
        if quota_info.status == QuotaStatus.EXCEEDED:
            alert = QuotaAlert(
                alert_type="exceeded",
                api_name=api_name,
                message=f"{api_name} API 쿼터가 초과되었습니다",
                timestamp=now,
                recommendation="백업 분석기로 전환하거나 플랜을 업그레이드하세요"
            )
            await self._add_alert(alert)

        # 사용량 기반 경고
        elif quota_info.current_usage:
            if quota_info.current_usage >= self.critical_threshold:
                alert = QuotaAlert(
                    alert_type="critical",
                    api_name=api_name,
                    message=f"{api_name} API 사용량이 위험 수준입니다 ({quota_info.current_usage:.1f}%)",
                    timestamp=now,
                    usage_percentage=quota_info.current_usage,
                    recommendation="즉시 사용량을 줄이거나 플랜 업그레이드를 고려하세요"
                )
                await self._add_alert(alert)

            elif quota_info.current_usage >= self.warning_threshold:
                alert = QuotaAlert(
                    alert_type="warning",
                    api_name=api_name,
                    message=f"{api_name} API 사용량이 경고 수준입니다 ({quota_info.current_usage:.1f}%)",
                    timestamp=now,
                    usage_percentage=quota_info.current_usage,
                    recommendation="사용량 모니터링을 강화하고 백업 계획을 준비하세요"
                )
                await self._add_alert(alert)

    async def _add_alert(self, alert: QuotaAlert):
        """알림 추가 (중복 방지)"""
        # 최근 1시간 내 동일 유형 알림이 있는지 확인
        cutoff_time = datetime.now() - timedelta(hours=1)

        recent_similar = any(
            a.alert_type == alert.alert_type and
            a.api_name == alert.api_name and
            a.timestamp > cutoff_time
            for a in self.alerts
        )

        if not recent_similar:
            self.alerts.append(alert)
            self._save_alerts()

            # 로그 출력
            emoji = {"warning": "⚠️", "critical": "🚨", "exceeded": "❌"}
            self.logger.warning(f"{emoji.get(alert.alert_type, '🔔')} {alert.message}")
            if alert.recommendation:
                self.logger.info(f"💡 권장사항: {alert.recommendation}")

    def get_usage_summary(self, days: int = 7) -> Dict[str, Any]:
        """사용량 요약 리포트"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_history = [h for h in self.history if h.timestamp > cutoff_date]

        summary = {
            "period_days": days,
            "total_checks": len(recent_history),
            "apis": {},
            "alerts": {
                "warning": 0,
                "critical": 0,
                "exceeded": 0
            }
        }

        # API별 요약
        api_groups = {}
        for entry in recent_history:
            if entry.api_name not in api_groups:
                api_groups[entry.api_name] = []
            api_groups[entry.api_name].append(entry)

        for api_name, entries in api_groups.items():
            exceeded_count = sum(1 for e in entries if e.status == QuotaStatus.EXCEEDED)
            available_count = sum(1 for e in entries if e.status == QuotaStatus.AVAILABLE)

            summary["apis"][api_name] = {
                "total_checks": len(entries),
                "exceeded_count": exceeded_count,
                "available_count": available_count,
                "availability_rate": (available_count / len(entries) * 100) if entries else 0,
                "last_status": entries[-1].status.value if entries else "unknown"
            }

        # 알림 요약
        recent_alerts = [a for a in self.alerts if a.timestamp > cutoff_date]
        for alert in recent_alerts:
            summary["alerts"][alert.alert_type] += 1

        return summary

    async def predict_quota_exhaustion(self, api_name: str = "openai") -> Optional[datetime]:
        """쿼터 소진 예측"""
        # 최근 24시간 사용 패턴 분석
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_entries = [
            h for h in self.history
            if h.api_name == api_name and h.timestamp > cutoff_time and h.usage_percentage
        ]

        if len(recent_entries) < 2:
            return None

        # 사용량 증가율 계산
        try:
            first_usage = recent_entries[0].usage_percentage
            last_usage = recent_entries[-1].usage_percentage
            time_diff = (recent_entries[-1].timestamp - recent_entries[0].timestamp).total_seconds() / 3600

            if time_diff > 0 and last_usage > first_usage:
                usage_rate = (last_usage - first_usage) / time_diff  # %/hour
                remaining_quota = 100 - last_usage

                if usage_rate > 0:
                    hours_until_exhaustion = remaining_quota / usage_rate
                    exhaustion_time = datetime.now() + timedelta(hours=hours_until_exhaustion)

                    self.logger.info(f"📈 {api_name} 쿼터 소진 예상: {exhaustion_time.strftime('%Y-%m-%d %H:%M')}")
                    return exhaustion_time

        except Exception as e:
            self.logger.warning(f"⚠️ 쿼터 소진 예측 실패: {e}")

        return None

    async def health_check(self) -> Dict[str, Any]:
        """전체 시스템 상태 체크"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "apis": {},
            "alerts": {
                "active_count": len([a for a in self.alerts if a.timestamp > datetime.now() - timedelta(hours=24)]),
                "critical_count": len([a for a in self.alerts if a.alert_type == "critical" and a.timestamp > datetime.now() - timedelta(hours=24)])
            },
            "recommendations": []
        }

        # OpenAI API 체크
        openai_quota = await self.check_and_record_quota("openai")
        health_status["apis"]["openai"] = {
            "status": openai_quota.status.value,
            "available": openai_quota.status == QuotaStatus.AVAILABLE,
            "error_message": openai_quota.error_message
        }

        # 전체 상태 결정
        if openai_quota.status == QuotaStatus.EXCEEDED:
            health_status["overall_status"] = "degraded"
            health_status["recommendations"].append("OpenAI API 쿼터 초과 - Gemini 백업 사용 권장")

        elif health_status["alerts"]["critical_count"] > 0:
            health_status["overall_status"] = "warning"
            health_status["recommendations"].append("활성 중요 알림 확인 필요")

        return health_status


# 글로벌 모니터 인스턴스
quota_monitor = None

def get_quota_monitor(config=None):
    """글로벌 쿼터 모니터 인스턴스 반환"""
    global quota_monitor
    if quota_monitor is None and config:
        quota_monitor = QuotaMonitor(config)
    return quota_monitor