#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/notifications/notification_manager.py

알림 관리자 - Phase 5 Notification & Monitoring System
포트폴리오 알림 및 트레이딩 이벤트 통합 관리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from utils.logger import get_logger
from .telegram_notifier import TelegramNotifier, AlertLevel, NotificationType


@dataclass
class TradingEvent:
    """트레이딩 이벤트"""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    priority: str = "MEDIUM"


class NotificationManager:
    """알림 관리자 - 포트폴리오 및 트레이딩 이벤트 통합 관리"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("NotificationManager")
        
        # 텔레그램 알림 초기화
        self.telegram_notifier = TelegramNotifier(config)
        
        # 이벤트 큐
        self.event_queue = asyncio.Queue()
        self.processing_events = False
        
        # 알림 통계
        self.notification_stats = {
            'sent_today': 0,
            'failed_today': 0,
            'last_reset': datetime.now().date(),
            'types_sent': {}
        }
        
        # 알림 설정
        self.alert_settings = {
            'enabled': True,
            'min_alert_level': AlertLevel.MEDIUM,
            'rate_limit': 5,  # 분당 최대 5개
            'quiet_hours': {'start': '22:00', 'end': '08:00'},
            'enabled_types': [
                NotificationType.TRADE,
                NotificationType.SIGNAL,
                NotificationType.ERROR,
                NotificationType.SYSTEM,
                NotificationType.AI_INSIGHT
            ]
        }
        
        self.logger.info("✅ 알림 관리자 초기화 완료")
    
    async def start_event_processing(self):
        """이벤트 처리 시작"""
        if not self.processing_events:
            self.processing_events = True
            asyncio.create_task(self._process_events())
            self.logger.info("🟢 이벤트 처리 시작")
    
    async def start_processing(self):
        """이벤트 처리 시작 (별칭)"""
        await self.start_event_processing()
    
    async def stop_event_processing(self):
        """이벤트 처리 중단"""
        self.processing_events = False
        self.logger.info("🔴 이벤트 처리 중단")
    
    async def cleanup(self):
        """시스템 정리 - 이벤트 처리 중단 및 리소스 해제"""
        try:
            # 이벤트 처리 중단
            await self.stop_event_processing()
            
            # 텔레그램 알림기 정리
            if hasattr(self.telegram_notifier, 'cleanup'):
                await self.telegram_notifier.cleanup()
            
            self.logger.info("✅ NotificationManager 정리 완료")
        except Exception as e:
            self.logger.error(f"❌ NotificationManager 정리 중 오류: {e}")
    
    async def add_trading_event(self, event_type: str, data: Dict[str, Any], priority: str = "MEDIUM"):
        """트레이딩 이벤트 추가"""
        event = TradingEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            priority=priority
        )
        
        await self.event_queue.put(event)
        self.logger.debug(f"📝 이벤트 추가: {event_type}")
    
    async def _process_events(self):
        """이벤트 처리 루프"""
        while self.processing_events:
            try:
                # 이벤트 가져오기 (1초 타임아웃)
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # 알림 생성 및 전송
                await self._handle_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"❌ 이벤트 처리 오류: {e}")
    
    async def _handle_event(self, event: TradingEvent):
        """개별 이벤트 처리"""
        try:
            # 알림 설정 확인
            if not self._should_send_notification(event):
                return
            
            # 이벤트 타입에 따른 알림 생성
            notification_data = await self._create_notification(event)
            
            if notification_data:
                # 텔레그램 알림 전송
                success = await self.telegram_notifier.send_notification(
                    message=notification_data['message'],
                    alert_level=notification_data['alert_level'],
                    notification_type=notification_data['type']
                )
                
                # 통계 업데이트
                await self._update_stats(event.event_type, success)
                
                if success:
                    self.logger.info(f"✅ 알림 전송 완료: {event.event_type}")
                else:
                    self.logger.warning(f"⚠️ 알림 전송 실패: {event.event_type}")
                    
        except Exception as e:
            self.logger.error(f"❌ 이벤트 처리 실패 {event.event_type}: {e}")
    
    def _should_send_notification(self, event: TradingEvent) -> bool:
        """알림 전송 여부 결정"""
        # 알림 비활성화 확인
        if not self.alert_settings['enabled']:
            return False
        
        # 우선순위 확인
        priority_levels = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
        min_level = priority_levels.get(self.alert_settings['min_alert_level'].name, 2)
        event_level = priority_levels.get(event.priority, 2)
        
        if event_level < min_level:
            return False
        
        # 조용한 시간 확인
        if self._is_quiet_hours():
            return event.priority in ['HIGH', 'CRITICAL']
        
        # 속도 제한 확인
        if self._is_rate_limited():
            return event.priority == 'CRITICAL'
        
        return True
    
    def _is_quiet_hours(self) -> bool:
        """조용한 시간 확인"""
        now = datetime.now().time()
        settings = self.alert_settings['quiet_hours']
        
        start_time = datetime.strptime(settings['start'], '%H:%M').time()
        end_time = datetime.strptime(settings['end'], '%H:%M').time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:  # 밤 시간대 (22:00 - 08:00)
            return now >= start_time or now <= end_time
    
    def _is_rate_limited(self) -> bool:
        """속도 제한 확인"""
        current_minute = datetime.now().strftime('%H:%M')
        recent_count = self.notification_stats.get('recent_minutes', {}).get(current_minute, 0)
        return recent_count >= self.alert_settings['rate_limit']
    
    async def _create_notification(self, event: TradingEvent) -> Optional[Dict[str, Any]]:
        """이벤트에 따른 알림 데이터 생성"""
        try:
            event_handlers = {
                'TRADE_EXECUTED': self._create_trade_notification,
                'SIGNAL_GENERATED': self._create_signal_notification,
                'PORTFOLIO_UPDATE': self._create_portfolio_notification,
                'RISK_ALERT': self._create_risk_notification,
                'SYSTEM_ERROR': self._create_error_notification,
                'AI_ANALYSIS': self._create_ai_notification,
                'MARKET_ALERT': self._create_market_notification
            }
            
            handler = event_handlers.get(event.event_type)
            if handler:
                return await handler(event)
            else:
                # 기본 알림
                return {
                    'message': f"📊 {event.event_type}\n\n{event.data}",
                    'alert_level': AlertLevel.MEDIUM,
                    'type': NotificationType.SYSTEM
                }
                
        except Exception as e:
            self.logger.error(f"❌ 알림 생성 실패: {e}")
            return None
    
    async def _create_trade_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """거래 알림 생성"""
        data = event.data
        action = data.get('action', '거래')
        symbol = data.get('symbol', '')
        quantity = data.get('quantity', 0)
        price = data.get('price', 0)
        confidence = data.get('confidence', 0)
        
        message = f"🔄 **거래 체결**\n\n"
        message += f"📈 종목: {symbol}\n"
        message += f"🎯 액션: {action}\n"
        message += f"📊 수량: {quantity:,}주\n"
        message += f"💰 가격: {price:,}원\n"
        message += f"🎲 신뢰도: {confidence:.1%}\n"
        
        if data.get('pnl'):
            message += f"💸 손익: {data['pnl']:,}원\n"
        
        alert_level = AlertLevel.HIGH if abs(data.get('amount', 0)) > 1000000 else AlertLevel.MEDIUM
        
        return {
            'message': message,
            'alert_level': alert_level,
            'type': NotificationType.TRADE
        }
    
    async def _create_signal_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """신호 알림 생성"""
        data = event.data
        symbol = data.get('symbol', '')
        signal = data.get('signal_type', '')
        confidence = data.get('confidence', 0)
        
        message = f"🎯 **매매 신호**\n\n"
        message += f"📈 종목: {symbol}\n"
        message += f"⚡ 신호: {signal}\n"
        message += f"🎲 신뢰도: {confidence:.1%}\n"
        
        if data.get('reason'):
            message += f"📝 사유: {data['reason']}\n"
        
        alert_level = AlertLevel.HIGH if confidence > 0.8 else AlertLevel.MEDIUM
        
        return {
            'message': message,
            'alert_level': alert_level,
            'type': NotificationType.SIGNAL
        }
    
    async def _create_portfolio_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """포트폴리오 알림 생성"""
        data = event.data
        
        message = f"📊 **포트폴리오 업데이트**\n\n"
        message += f"💰 총 자산: {data.get('total_value', 0):,}원\n"
        message += f"📈 총 손익: {data.get('total_pnl', 0):,}원\n"
        message += f"📊 수익률: {data.get('return_rate', 0):.2%}\n"
        message += f"📍 포지션: {data.get('position_count', 0)}개\n"
        
        return {
            'message': message,
            'alert_level': AlertLevel.MEDIUM,
            'type': NotificationType.SYSTEM
        }
    
    async def _create_risk_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """위험 알림 생성"""
        data = event.data
        risk_level = data.get('risk_level', 'MEDIUM')
        
        message = f"⚠️ **위험 경고**\n\n"
        message += f"🚨 위험도: {risk_level}\n"
        message += f"📉 현재 손익: {data.get('current_pnl', 0):,}원\n"
        
        if data.get('recommendations'):
            message += f"\n💡 권장사항:\n"
            for rec in data['recommendations'][:3]:
                message += f"• {rec}\n"
        
        alert_level = {
            'LOW': AlertLevel.LOW,
            'MEDIUM': AlertLevel.MEDIUM, 
            'HIGH': AlertLevel.HIGH,
            'CRITICAL': AlertLevel.CRITICAL
        }.get(risk_level, AlertLevel.MEDIUM)
        
        return {
            'message': message,
            'alert_level': alert_level,
            'type': NotificationType.ERROR
        }
    
    async def _create_error_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """에러 알림 생성"""
        data = event.data
        
        message = f"❌ **시스템 오류**\n\n"
        message += f"🔧 모듈: {data.get('module', '시스템')}\n"
        message += f"📝 오류: {data.get('error', '알 수 없는 오류')}\n"
        
        if data.get('action_taken'):
            message += f"⚡ 조치: {data['action_taken']}\n"
        
        return {
            'message': message,
            'alert_level': AlertLevel.HIGH,
            'type': NotificationType.ERROR
        }
    
    async def _create_ai_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """AI 분석 알림 생성"""
        data = event.data
        
        message = f"🧠 **AI 인사이트**\n\n"
        message += f"📊 분석: {data.get('analysis_type', 'AI 분석')}\n"
        
        if data.get('prediction'):
            message += f"🔮 예측: {data['prediction']}\n"
        
        if data.get('confidence'):
            message += f"🎲 신뢰도: {data['confidence']:.1%}\n"
        
        if data.get('key_points'):
            message += f"\n💡 주요 포인트:\n"
            for point in data['key_points'][:3]:
                message += f"• {point}\n"
        
        return {
            'message': message,
            'alert_level': AlertLevel.MEDIUM,
            'type': NotificationType.AI_INSIGHT
        }
    
    async def _create_market_notification(self, event: TradingEvent) -> Dict[str, Any]:
        """시장 알림 생성"""
        data = event.data
        
        message = f"🌍 **시장 알림**\n\n"
        message += f"📊 상황: {data.get('market_condition', '시장 변화')}\n"
        
        if data.get('impact'):
            message += f"💥 영향도: {data['impact']}\n"
        
        if data.get('recommendation'):
            message += f"💡 권장: {data['recommendation']}\n"
        
        return {
            'message': message,
            'alert_level': AlertLevel.MEDIUM,
            'type': NotificationType.SYSTEM
        }
    
    async def _update_stats(self, event_type: str, success: bool):
        """알림 통계 업데이트"""
        # 일일 리셋 확인
        today = datetime.now().date()
        if self.notification_stats['last_reset'] != today:
            self._reset_daily_stats()
        
        # 통계 업데이트
        if success:
            self.notification_stats['sent_today'] += 1
            self.notification_stats['types_sent'][event_type] = \
                self.notification_stats['types_sent'].get(event_type, 0) + 1
        else:
            self.notification_stats['failed_today'] += 1
        
        # 분당 통계 (속도 제한용)
        current_minute = datetime.now().strftime('%H:%M')
        if 'recent_minutes' not in self.notification_stats:
            self.notification_stats['recent_minutes'] = {}
        
        self.notification_stats['recent_minutes'][current_minute] = \
            self.notification_stats['recent_minutes'].get(current_minute, 0) + 1
    
    def _reset_daily_stats(self):
        """일일 통계 리셋"""
        self.notification_stats = {
            'sent_today': 0,
            'failed_today': 0,
            'last_reset': datetime.now().date(),
            'types_sent': {}
        }
        self.logger.info("📊 일일 알림 통계 리셋")
    
    # 공개 메서드들
    async def send_trade_notification(self, trade_data: Dict[str, Any]):
        """거래 알림 전송"""
        await self.add_trading_event('TRADE_EXECUTED', trade_data, 'HIGH')
    
    async def send_signal_notification(self, signal_data: Dict[str, Any]):
        """신호 알림 전송"""
        await self.add_trading_event('SIGNAL_GENERATED', signal_data, 'MEDIUM')
    
    async def send_portfolio_notification(self, portfolio_data: Dict[str, Any]):
        """포트폴리오 알림 전송"""
        await self.add_trading_event('PORTFOLIO_UPDATE', portfolio_data, 'MEDIUM')
    
    async def send_risk_notification(self, risk_data: Dict[str, Any]):
        """위험 알림 전송"""
        priority = 'CRITICAL' if risk_data.get('risk_level') == 'CRITICAL' else 'HIGH'
        await self.add_trading_event('RISK_ALERT', risk_data, priority)
    
    async def send_error_notification(self, error_data: Dict[str, Any]):
        """에러 알림 전송"""
        await self.add_trading_event('SYSTEM_ERROR', error_data, 'HIGH')
    
    async def send_ai_notification(self, ai_data: Dict[str, Any]):
        """AI 분석 알림 전송"""
        await self.add_trading_event('AI_ANALYSIS', ai_data, 'MEDIUM')
    
    async def send_market_notification(self, market_data: Dict[str, Any]):
        """시장 알림 전송"""
        await self.add_trading_event('MARKET_ALERT', market_data, 'MEDIUM')
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """알림 통계 조회"""
        return self.notification_stats.copy()
    
    def update_alert_settings(self, settings: Dict[str, Any]):
        """알림 설정 업데이트"""
        self.alert_settings.update(settings)
        self.logger.info("⚙️ 알림 설정 업데이트 완료")
    
    def get_alert_settings(self) -> Dict[str, Any]:
        """알림 설정 조회"""
        return self.alert_settings.copy()
    
    async def test_notification(self):
        """테스트 알림 전송"""
        test_data = {
            'message': '📧 알림 시스템 테스트',
            'timestamp': datetime.now().isoformat()
        }
        
        success = await self.telegram_notifier.send_notification(
            message="🧪 **알림 테스트**\n\n✅ 알림 시스템이 정상 작동합니다!",
            alert_level=AlertLevel.MEDIUM,
            notification_type=NotificationType.SYSTEM
        )
        
        return success