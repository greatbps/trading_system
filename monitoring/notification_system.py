#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notification_system.py

실시간 알림 시스템 - 중요한 설정 변경 및 성과 이벤트 알림
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Discord/Slack 알림을 위한 라이브러리
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Windows 알림을 위한 라이브러리
try:
    import plyer
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

from utils.logger import get_logger

class NotificationLevel(Enum):
    """알림 레벨"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    """알림 채널"""
    CONSOLE = "console"
    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    DESKTOP = "desktop"
    LOG = "log"

@dataclass
class NotificationRule:
    """알림 규칙"""
    event_type: str
    level: NotificationLevel
    channels: List[NotificationChannel]
    condition: Optional[Callable] = None
    throttle_minutes: int = 5  # 중복 알림 방지 시간
    enabled: bool = True

@dataclass
class Notification:
    """알림 메시지"""
    title: str
    message: str
    level: NotificationLevel
    event_type: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotificationConfig:
    """알림 설정"""
    # 이메일 설정
    email_enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_user: str = ""
    email_password: str = ""
    recipient_emails: List[str] = field(default_factory=list)

    # Discord 설정
    discord_enabled: bool = False
    discord_webhook_url: str = ""

    # Slack 설정
    slack_enabled: bool = False
    slack_webhook_url: str = ""

    # 데스크톱 알림 설정
    desktop_enabled: bool = True

class NotificationSystem:
    """실시간 알림 시스템"""

    def __init__(self, config: Optional[NotificationConfig] = None):
        """알림 시스템 초기화"""
        self.logger = get_logger("NotificationSystem")
        self.config = config or NotificationConfig()

        # 알림 규칙
        self.rules: List[NotificationRule] = []
        self._initialize_default_rules()

        # 알림 히스토리 (중복 방지용)
        self.notification_history: Dict[str, datetime] = {}

        # 알림 큐 (배치 처리용)
        self.notification_queue: asyncio.Queue = asyncio.Queue()

        # 백그라운드 작업
        self._background_task: Optional[asyncio.Task] = None

    def _initialize_default_rules(self):
        """기본 알림 규칙 초기화"""
        self.rules = [
            # 설정 변경 알림
            NotificationRule(
                event_type="settings_changed",
                level=NotificationLevel.INFO,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.DESKTOP],
                throttle_minutes=10
            ),
            # 큰 손실 알림
            NotificationRule(
                event_type="large_loss",
                level=NotificationLevel.WARNING,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.EMAIL, NotificationChannel.DESKTOP],
                condition=lambda data: data.get("loss_pct", 0) > 5.0,
                throttle_minutes=30
            ),
            # 큰 수익 알림
            NotificationRule(
                event_type="large_profit",
                level=NotificationLevel.INFO,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.DESKTOP],
                condition=lambda data: data.get("profit_pct", 0) > 10.0,
                throttle_minutes=60
            ),
            # 리스크 레벨 변경 알림
            NotificationRule(
                event_type="risk_level_changed",
                level=NotificationLevel.WARNING,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.EMAIL, NotificationChannel.DESKTOP],
                throttle_minutes=30
            ),
            # 시스템 오류 알림
            NotificationRule(
                event_type="system_error",
                level=NotificationLevel.ERROR,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.EMAIL, NotificationChannel.DISCORD],
                throttle_minutes=5
            ),
            # 거래 실행 알림
            NotificationRule(
                event_type="trade_executed",
                level=NotificationLevel.INFO,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG],
                throttle_minutes=1
            ),
            # 백테스팅 완료 알림
            NotificationRule(
                event_type="backtest_completed",
                level=NotificationLevel.INFO,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.DESKTOP],
                throttle_minutes=5
            )
        ]

    async def start(self):
        """알림 시스템 시작"""
        try:
            self.logger.info("🔔 알림 시스템 시작")

            # 백그라운드 알림 처리 작업 시작
            self._background_task = asyncio.create_task(self._process_notifications())

            self.logger.info("✅ 알림 시스템 시작 완료")

        except Exception as e:
            self.logger.error(f"❌ 알림 시스템 시작 실패: {e}")

    async def stop(self):
        """알림 시스템 정지"""
        try:
            self.logger.info("🔔 알림 시스템 정지 중...")

            if self._background_task:
                self._background_task.cancel()
                try:
                    await self._background_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("✅ 알림 시스템 정지 완료")

        except Exception as e:
            self.logger.error(f"❌ 알림 시스템 정지 실패: {e}")

    async def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        알림 발송

        Args:
            event_type: 이벤트 타입
            title: 알림 제목
            message: 알림 메시지
            level: 알림 레벨
            metadata: 추가 메타데이터
        """
        try:
            # 알림 객체 생성
            notification = Notification(
                title=title,
                message=message,
                level=level,
                event_type=event_type,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )

            # 큐에 추가
            await self.notification_queue.put(notification)

        except Exception as e:
            self.logger.error(f"❌ 알림 발송 실패: {e}")

    async def _process_notifications(self):
        """백그라운드 알림 처리"""
        try:
            while True:
                # 큐에서 알림 가져오기
                notification = await self.notification_queue.get()

                # 해당 이벤트 타입의 규칙 찾기
                applicable_rules = [
                    rule for rule in self.rules
                    if rule.event_type == notification.event_type and rule.enabled
                ]

                for rule in applicable_rules:
                    # 조건 확인
                    if rule.condition and not rule.condition(notification.metadata):
                        continue

                    # 중복 알림 방지 확인
                    throttle_key = f"{rule.event_type}_{rule.level.value}"
                    last_sent = self.notification_history.get(throttle_key)

                    if last_sent:
                        time_diff = datetime.now() - last_sent
                        if time_diff.total_seconds() < rule.throttle_minutes * 60:
                            continue

                    # 알림 발송
                    await self._send_notification(notification, rule.channels)

                    # 히스토리 업데이트
                    self.notification_history[throttle_key] = datetime.now()

                # 작업 완료 마킹
                self.notification_queue.task_done()

        except asyncio.CancelledError:
            self.logger.info("알림 처리 작업이 취소되었습니다")
        except Exception as e:
            self.logger.error(f"❌ 알림 처리 오류: {e}")

    async def _send_notification(
        self,
        notification: Notification,
        channels: List[NotificationChannel]
    ):
        """지정된 채널로 알림 발송"""
        for channel in channels:
            try:
                if channel == NotificationChannel.CONSOLE:
                    await self._send_console_notification(notification)
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email_notification(notification)
                elif channel == NotificationChannel.DISCORD:
                    await self._send_discord_notification(notification)
                elif channel == NotificationChannel.SLACK:
                    await self._send_slack_notification(notification)
                elif channel == NotificationChannel.DESKTOP:
                    await self._send_desktop_notification(notification)
                elif channel == NotificationChannel.LOG:
                    await self._send_log_notification(notification)

            except Exception as e:
                self.logger.error(f"❌ {channel.value} 채널 알림 발송 실패: {e}")

    async def _send_console_notification(self, notification: Notification):
        """콘솔 알림"""
        # 레벨에 따른 아이콘
        level_icons = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨"
        }

        icon = level_icons.get(notification.level, "📢")
        timestamp = notification.timestamp.strftime("%H:%M:%S")

        print(f"{icon} [{timestamp}] {notification.title}")
        print(f"   {notification.message}")

        if notification.metadata:
            print(f"   세부사항: {notification.metadata}")

    async def _send_email_notification(self, notification: Notification):
        """이메일 알림"""
        if not self.config.email_enabled or not self.config.recipient_emails:
            return

        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = self.config.email_user
            msg['To'] = ', '.join(self.config.recipient_emails)
            msg['Subject'] = f"[AI Trading] {notification.title}"

            # 본문 생성
            body = f"""
{notification.message}

시간: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
레벨: {notification.level.value.upper()}
이벤트 타입: {notification.event_type}

---
AI Trading System 자동 알림
            """

            if notification.metadata:
                body += f"\n\n세부사항:\n{json.dumps(notification.metadata, indent=2, ensure_ascii=False)}"

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # SMTP 서버 연결 및 발송
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            server.login(self.config.email_user, self.config.email_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"📧 이메일 알림 발송 완료: {notification.title}")

        except Exception as e:
            self.logger.error(f"❌ 이메일 발송 실패: {e}")

    async def _send_discord_notification(self, notification: Notification):
        """Discord 알림"""
        if not self.config.discord_enabled or not self.config.discord_webhook_url or not REQUESTS_AVAILABLE:
            return

        try:
            # Discord 색상 코드
            color_codes = {
                NotificationLevel.INFO: 0x00ff00,      # 초록
                NotificationLevel.WARNING: 0xffff00,   # 노랑
                NotificationLevel.ERROR: 0xff0000,     # 빨강
                NotificationLevel.CRITICAL: 0x800080  # 보라
            }

            embed = {
                "title": notification.title,
                "description": notification.message,
                "color": color_codes.get(notification.level, 0x0099ff),
                "timestamp": notification.timestamp.isoformat(),
                "fields": [
                    {
                        "name": "이벤트 타입",
                        "value": notification.event_type,
                        "inline": True
                    },
                    {
                        "name": "레벨",
                        "value": notification.level.value.upper(),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "AI Trading System"
                }
            }

            # 메타데이터 추가
            if notification.metadata:
                for key, value in notification.metadata.items():
                    embed["fields"].append({
                        "name": key,
                        "value": str(value),
                        "inline": True
                    })

            payload = {"embeds": [embed]}

            response = requests.post(self.config.discord_webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info(f"📱 Discord 알림 발송 완료: {notification.title}")

        except Exception as e:
            self.logger.error(f"❌ Discord 알림 발송 실패: {e}")

    async def _send_slack_notification(self, notification: Notification):
        """Slack 알림"""
        if not self.config.slack_enabled or not self.config.slack_webhook_url or not REQUESTS_AVAILABLE:
            return

        try:
            # Slack 색상
            colors = {
                NotificationLevel.INFO: "good",
                NotificationLevel.WARNING: "warning",
                NotificationLevel.ERROR: "danger",
                NotificationLevel.CRITICAL: "danger"
            }

            attachment = {
                "color": colors.get(notification.level, "good"),
                "title": notification.title,
                "text": notification.message,
                "timestamp": int(notification.timestamp.timestamp()),
                "fields": [
                    {
                        "title": "이벤트 타입",
                        "value": notification.event_type,
                        "short": True
                    },
                    {
                        "title": "레벨",
                        "value": notification.level.value.upper(),
                        "short": True
                    }
                ],
                "footer": "AI Trading System"
            }

            # 메타데이터 추가
            if notification.metadata:
                for key, value in notification.metadata.items():
                    attachment["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })

            payload = {"attachments": [attachment]}

            response = requests.post(self.config.slack_webhook_url, json=payload)
            response.raise_for_status()

            self.logger.info(f"📱 Slack 알림 발송 완료: {notification.title}")

        except Exception as e:
            self.logger.error(f"❌ Slack 알림 발송 실패: {e}")

    async def _send_desktop_notification(self, notification: Notification):
        """데스크톱 알림"""
        if not self.config.desktop_enabled or not PLYER_AVAILABLE:
            return

        try:
            plyer.notification.notify(
                title=f"AI Trading - {notification.title}",
                message=notification.message,
                timeout=10
            )

            self.logger.info(f"🖥️ 데스크톱 알림 발송 완료: {notification.title}")

        except Exception as e:
            self.logger.error(f"❌ 데스크톱 알림 발송 실패: {e}")

    async def _send_log_notification(self, notification: Notification):
        """로그 알림"""
        log_levels = {
            NotificationLevel.INFO: logging.INFO,
            NotificationLevel.WARNING: logging.WARNING,
            NotificationLevel.ERROR: logging.ERROR,
            NotificationLevel.CRITICAL: logging.CRITICAL
        }

        level = log_levels.get(notification.level, logging.INFO)
        self.logger.log(level, f"{notification.title}: {notification.message}")

    def add_rule(self, rule: NotificationRule):
        """알림 규칙 추가"""
        self.rules.append(rule)

    def remove_rule(self, event_type: str):
        """알림 규칙 제거"""
        self.rules = [rule for rule in self.rules if rule.event_type != event_type]

    def update_config(self, config: NotificationConfig):
        """설정 업데이트"""
        self.config = config

    async def test_notifications(self):
        """알림 시스템 테스트"""
        self.logger.info("🧪 알림 시스템 테스트 시작")

        test_cases = [
            ("settings_changed", "설정 변경", "포지션 크기가 10%에서 15%로 변경되었습니다", NotificationLevel.INFO),
            ("large_profit", "큰 수익 발생", "일일 수익률이 12%에 도달했습니다", NotificationLevel.INFO),
            ("large_loss", "큰 손실 발생", "일일 손실률이 7%에 도달했습니다", NotificationLevel.WARNING),
            ("system_error", "시스템 오류", "데이터베이스 연결에 실패했습니다", NotificationLevel.ERROR)
        ]

        for event_type, title, message, level in test_cases:
            await self.notify(event_type, title, message, level)
            await asyncio.sleep(1)  # 테스트 간격

        self.logger.info("✅ 알림 시스템 테스트 완료")

# 글로벌 알림 시스템 인스턴스
_notification_system: Optional[NotificationSystem] = None

def get_notification_system() -> NotificationSystem:
    """글로벌 알림 시스템 인스턴스 반환"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system

async def send_notification(
    event_type: str,
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    metadata: Optional[Dict[str, Any]] = None
):
    """편의 함수: 알림 발송"""
    system = get_notification_system()
    await system.notify(event_type, title, message, level, metadata)

# 사용 예시
async def main():
    """테스트 함수"""
    # 알림 시스템 초기화
    config = NotificationConfig(
        desktop_enabled=True,
        email_enabled=False  # 이메일 설정이 없으므로 비활성화
    )

    system = NotificationSystem(config)
    await system.start()

    # 테스트 알림 발송
    await system.test_notifications()

    # 정리
    await system.stop()

if __name__ == "__main__":
    asyncio.run(main())