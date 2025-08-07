#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/notifications/telegram_notifier.py

텔레그램 알림기 - Phase 5 Notification & Monitoring System
AI 기능이 포함된 아름다운 메시지 포맷팅과 전문적인 알림 시스템
"""

import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer


class AlertLevel(Enum):
    """알림 레벨"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NotificationType(Enum):
    """알림 타입"""
    TRADE = "TRADE"
    SIGNAL = "SIGNAL"
    ERROR = "ERROR"
    SYSTEM = "SYSTEM"
    AI_INSIGHT = "AI_INSIGHT"


@dataclass
class TelegramMessage:
    """텔레그램 메시지"""
    text: str
    parse_mode: str = "Markdown"
    disable_notification: bool = False
    reply_markup: Optional[Dict] = None


class TelegramNotifier:
    """텔레그램 알림기 - 아름다운 포맷팅과 AI 인사이트"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("TelegramNotifier")
        
        # 텔레그램 설정
        self.bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', None) or getattr(config.api, 'TELEGRAM_BOT_TOKEN', None)
        self.chat_id = getattr(config, 'TELEGRAM_CHAT_ID', None) or getattr(config.api, 'TELEGRAM_CHAT_ID', None)
        
        # AI 분석기 (옵셀널)
        try:
            self.gemini_analyzer = GeminiAnalyzer(config) if hasattr(config, 'api') else None
        except:
            self.gemini_analyzer = None
        
        # 메시지 포맷팅 설정
        self.emoji_map = {
            AlertLevel.CRITICAL: "🚨",
            AlertLevel.HIGH: "⚠️",
            AlertLevel.MEDIUM: "ℹ️",
            AlertLevel.LOW: "💡"
        }
        
        self.type_emoji_map = {
            NotificationType.TRADE: "💼",
            NotificationType.SIGNAL: "📡",
            NotificationType.ERROR: "❌",
            NotificationType.SYSTEM: "🔧",
            NotificationType.AI_INSIGHT: "🧠"
        }
        
        # 전송 통계
        self.stats = {
            'sent_count': 0,
            'failed_count': 0,
            'last_sent': None,
            'rate_limit_count': 0
        }
        
        # 속도 제한 설정
        self.rate_limit_delay = 1  # 초
        self.last_sent_time = datetime.min
        
        self.logger.info("✅ 텔레그램 알림기 초기화 완료")
    
    async def send_notification(
        self,
        message: str,
        alert_level: AlertLevel = AlertLevel.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM,
        disable_preview: bool = True,
        add_ai_context: bool = False
    ) -> bool:
        """알림 전송"""
        try:
            # 텔레그램 설정 확인
            if not self._is_telegram_configured():
                self.logger.warning("⚠️ 텔레그램 설정이 없습니다")
                return False
            
            # 속도 제한 확인
            await self._apply_rate_limit()
            
            # 메시지 포맷팅
            formatted_message = await self._format_message(
                message, alert_level, notification_type, add_ai_context
            )
            
            # 텔레그램 메시지 객체 생성
            telegram_message = TelegramMessage(
                text=formatted_message,
                parse_mode="Markdown",
                disable_notification=(alert_level == AlertLevel.LOW)
            )
            
            # 전송
            success = await self._send_to_telegram(telegram_message, disable_preview)
            
            # 통계 업데이트
            self._update_stats(success)
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 알림 전송 오류: {e}")
            self.stats['failed_count'] += 1
            return False
    
    def _is_telegram_configured(self) -> bool:
        """텔레그램 설정 확인"""
        return bool(self.bot_token and self.chat_id)
    
    async def _apply_rate_limit(self):
        """속도 제한 적용"""
        now = datetime.now()
        time_diff = (now - self.last_sent_time).total_seconds()
        
        if time_diff < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - time_diff
            await asyncio.sleep(wait_time)
            self.stats['rate_limit_count'] += 1
        
        self.last_sent_time = datetime.now()
    
    async def _format_message(
        self,
        message: str,
        alert_level: AlertLevel,
        notification_type: NotificationType,
        add_ai_context: bool = False
    ) -> str:
        """메시지 포맷팅"""
        try:
            # 헤더 생성
            level_emoji = self.emoji_map.get(alert_level, "ℹ️")
            type_emoji = self.type_emoji_map.get(notification_type, "📊")
            
            header = f"{level_emoji} {type_emoji} **{alert_level.value}**"
            
            # 시간 정보
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # AI 컨텍스트 추가 (옵셀널)
            ai_context = ""
            if add_ai_context and self.gemini_analyzer:
                ai_context = await self._generate_ai_context(message, alert_level)
            
            # 메시지 조립
            formatted_parts = [
                header,
                f"⏰ {timestamp}",
                "",  # 빈 줄
                message
            ]
            
            if ai_context:
                formatted_parts.extend(["", "🧠 **AI 인사이트:**", ai_context])
            
            # 푸터 추가
            footer = self._generate_footer(alert_level, notification_type)
            if footer:
                formatted_parts.extend(["", footer])
            
            return "\n".join(formatted_parts)
            
        except Exception as e:
            self.logger.error(f"❌ 메시지 포맷팅 오류: {e}")
            return f"{level_emoji} {message}\n⏰ {timestamp}"
    
    async def _generate_ai_context(self, message: str, alert_level: AlertLevel) -> str:
        """AI 컨텍스트 생성"""
        try:
            if not self.gemini_analyzer:
                return ""
            
            # AI 분석 요청
            context_prompt = f"""
            다음 트레이딩 알림에 대해 간단한 컨텍스트나 설명을 제공해주세요:
            
            알림: {message}
            중요도: {alert_level.value}
            
            요구사항:
            - 50자 이내로 간단하게
            - 투자자에게 도움이 되는 인사이트
            - 한국어로 작성
            """
            
            # 분석 실행 (타임아웃 5초)
            analysis = await asyncio.wait_for(
                self.gemini_analyzer.analyze_text(context_prompt),
                timeout=5.0
            )
            
            if analysis and 'summary' in analysis:
                return analysis['summary'][:100]  # 최대 100자
            
            return ""
            
        except asyncio.TimeoutError:
            self.logger.debug("⏱️ AI 컨텍스트 생성 타임아웃")
            return ""
        except Exception as e:
            self.logger.debug(f"⚠️ AI 컨텍스트 생성 실패: {e}")
            return ""
    
    def _generate_footer(self, alert_level: AlertLevel, notification_type: NotificationType) -> str:
        """푸터 생성"""
        footers = {
            AlertLevel.CRITICAL: "🚨 즉시 확인 필요",
            AlertLevel.HIGH: "⚡ 빠른 대응 권장",
            AlertLevel.MEDIUM: "",
            AlertLevel.LOW: ""
        }
        
        return footers.get(alert_level, "")
    
    async def _send_to_telegram(self, telegram_message: TelegramMessage, disable_preview: bool) -> bool:
        """텔레그램 API 전송"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': telegram_message.text,
                'parse_mode': telegram_message.parse_mode,
                'disable_notification': telegram_message.disable_notification,
                'disable_web_page_preview': disable_preview
            }
            
            if telegram_message.reply_markup:
                data['reply_markup'] = json.dumps(telegram_message.reply_markup)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as response:
                    if response.status == 200:
                        self.logger.debug("✅ 텔레그램 메시지 전송 성공")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ 텔레그램 API 오류 {response.status}: {error_text}")
                        return False
                        
        except asyncio.TimeoutError:
            self.logger.error("❌ 텔레그램 전송 타임아웃")
            return False
        except Exception as e:
            self.logger.error(f"❌ 텔레그램 전송 실패: {e}")
            return False
    
    def _update_stats(self, success: bool):
        """통계 업데이트"""
        if success:
            self.stats['sent_count'] += 1
            self.stats['last_sent'] = datetime.now()
        else:
            self.stats['failed_count'] += 1
    
    # 고급 메시지 타입별 전송 메서드
    async def send_trade_alert(self, trade_data: Dict[str, Any]) -> bool:
        """거래 알림 전송"""
        symbol = trade_data.get('symbol', '')
        action = trade_data.get('action', '')
        price = trade_data.get('price', 0)
        quantity = trade_data.get('quantity', 0)
        confidence = trade_data.get('confidence', 0)
        
        message = f"""📈 **거래 체결**
        
**종목:** {symbol}
**액션:** {action}
**가격:** {price:,}원
**수량:** {quantity:,}주
**신뢰도:** {confidence:.1%}"""
        
        alert_level = AlertLevel.HIGH if abs(trade_data.get('amount', 0)) > 1000000 else AlertLevel.MEDIUM
        
        return await self.send_notification(
            message=message,
            alert_level=alert_level,
            notification_type=NotificationType.TRADE,
            add_ai_context=True
        )
    
    async def send_signal_alert(self, signal_data: Dict[str, Any]) -> bool:
        """신호 알림 전송"""
        symbol = signal_data.get('symbol', '')
        signal_type = signal_data.get('signal_type', '')
        confidence = signal_data.get('confidence', 0)
        reason = signal_data.get('reason', '')
        
        message = f"""🎯 **매매 신호**
        
**종목:** {symbol}
**신호:** {signal_type}
**신뢰도:** {confidence:.1%}
**근거:** {reason[:100]}"""
        
        alert_level = AlertLevel.HIGH if confidence > 0.8 else AlertLevel.MEDIUM
        
        return await self.send_notification(
            message=message,
            alert_level=alert_level,
            notification_type=NotificationType.SIGNAL,
            add_ai_context=True
        )
    
    async def send_error_alert(self, error_data: Dict[str, Any]) -> bool:
        """에러 알림 전송"""
        module = error_data.get('module', '시스템')
        error_msg = error_data.get('error', '알 수 없는 오류')
        severity = error_data.get('severity', 'MEDIUM')
        
        message = f"""❌ **시스템 오류**
        
**모듈:** {module}
**오류:** {error_msg}
**심각도:** {severity}"""
        
        if error_data.get('action_taken'):
            message += f"\n**조치:** {error_data['action_taken']}"
        
        alert_level = {
            'CRITICAL': AlertLevel.CRITICAL,
            'HIGH': AlertLevel.HIGH,
            'MEDIUM': AlertLevel.MEDIUM,
            'LOW': AlertLevel.LOW
        }.get(severity, AlertLevel.MEDIUM)
        
        return await self.send_notification(
            message=message,
            alert_level=alert_level,
            notification_type=NotificationType.ERROR
        )
    
    async def send_portfolio_update(self, portfolio_data: Dict[str, Any]) -> bool:
        """포트폴리오 업데이트 알림"""
        total_value = portfolio_data.get('total_value', 0)
        total_pnl = portfolio_data.get('total_pnl', 0)
        return_rate = portfolio_data.get('return_rate', 0)
        position_count = portfolio_data.get('position_count', 0)
        
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        
        message = f"""📊 **포트폴리오 업데이트**
        
**총 자산:** {total_value:,}원
**총 손익:** {pnl_emoji} {total_pnl:,}원
**수익률:** {return_rate:.2%}
**포지션:** {position_count}개"""
        
        # 손익에 따른 알림 레벨
        if abs(return_rate) > 0.1:  # ±10% 이상
            alert_level = AlertLevel.HIGH
        elif abs(return_rate) > 0.05:  # ±5% 이상
            alert_level = AlertLevel.MEDIUM
        else:
            alert_level = AlertLevel.LOW
        
        return await self.send_notification(
            message=message,
            alert_level=alert_level,
            notification_type=NotificationType.SYSTEM,
            add_ai_context=True
        )
    
    async def send_ai_insight(self, ai_data: Dict[str, Any]) -> bool:
        """AI 인사이트 알림"""
        analysis_type = ai_data.get('analysis_type', 'AI 분석')
        prediction = ai_data.get('prediction', '')
        confidence = ai_data.get('confidence', 0)
        key_points = ai_data.get('key_points', [])
        
        message = f"""🧠 **AI 인사이트**
        
**분석:** {analysis_type}
**예측:** {prediction}
**신뢰도:** {confidence:.1%}"""
        
        if key_points:
            message += "\n\n**주요 포인트:**\n"
            for point in key_points[:3]:
                message += f"• {point}\n"
        
        return await self.send_notification(
            message=message,
            alert_level=AlertLevel.MEDIUM,
            notification_type=NotificationType.AI_INSIGHT
        )
    
    async def send_system_status(self, status_data: Dict[str, Any]) -> bool:
        """시스템 상태 알림"""
        status = status_data.get('status', 'UNKNOWN')
        uptime = status_data.get('uptime', 0)
        active_strategies = status_data.get('active_strategies', 0)
        
        status_emoji = {
            'RUNNING': '🟢',
            'STOPPED': '🔴',
            'WARNING': '🟡',
            'ERROR': '🔴'
        }.get(status, '⚪')
        
        message = f"""🔧 **시스템 상태**
        
**상태:** {status_emoji} {status}
**가동시간:** {uptime}시간
**활성 전략:** {active_strategies}개"""
        
        alert_level = {
            'RUNNING': AlertLevel.LOW,
            'WARNING': AlertLevel.MEDIUM,
            'ERROR': AlertLevel.HIGH,
            'STOPPED': AlertLevel.CRITICAL
        }.get(status, AlertLevel.MEDIUM)
        
        return await self.send_notification(
            message=message,
            alert_level=alert_level,
            notification_type=NotificationType.SYSTEM
        )
    
    async def test_connection(self) -> bool:
        """연결 테스트"""
        if not self._is_telegram_configured():
            self.logger.error("❌ 텔레그램 설정이 없습니다")
            return False
        
        test_message = "🧪 **알림 테스트**\n\n✅ 텔레그램 알림 시스템이 정상 작동합니다!"
        
        success = await self.send_notification(
            message=test_message,
            alert_level=AlertLevel.LOW,
            notification_type=NotificationType.SYSTEM
        )
        
        if success:
            self.logger.info("✅ 텔레그램 연결 테스트 성공")
        else:
            self.logger.error("❌ 텔레그램 연결 테스트 실패")
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['sent_count'] / 
                (self.stats['sent_count'] + self.stats['failed_count'])
                if (self.stats['sent_count'] + self.stats['failed_count']) > 0 else 0
            ),
            'configured': self._is_telegram_configured()
        }
    
    def reset_stats(self):
        """통계 리셋"""
        self.stats = {
            'sent_count': 0,
            'failed_count': 0,
            'last_sent': None,
            'rate_limit_count': 0
        }
        self.logger.info("📊 텔레그램 통계 리셋")
    
    async def cleanup(self):
        """리소스 정리 - 현재는 aiohttp 세션이 context manager로 관리되므로 별도 정리 불필요"""
        try:
            # 현재 aiohttp.ClientSession이 context manager로 사용되므로 자동 정리됨
            # 필요시 추가 정리 작업을 여기에 추가
            self.logger.info("✅ TelegramNotifier 정리 완료")
        except Exception as e:
            self.logger.error(f"❌ TelegramNotifier 정리 중 오류: {e}")