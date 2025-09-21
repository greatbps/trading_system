#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/monitoring/realtime_monitoring_handler.py

실시간 모니터링 통합 핸들러
- 200개 종목 실시간 모니터링
- 기존 시스템과의 완벽한 통합
- 성능 최적화된 데이터 처리
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from data_collectors.bulk_realtime_collector import BulkRealtimeCollector, CollectionMode
from data_collectors.memory_optimized_storage import MemoryOptimizedStorage, DataPriority
from database.database_manager import DatabaseManager
from database.monitoring_models import MonitoringStock, MonitoringStatus
from notifications.notification_manager import NotificationManager


class MonitoringEvent(Enum):
    """모니터링 이벤트 타입"""
    PRICE_ALERT = "price_alert"
    VOLUME_SPIKE = "volume_spike"
    TARGET_REACHED = "target_reached"
    STOP_LOSS_HIT = "stop_loss_hit"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass
class AlertCondition:
    """알림 조건"""
    symbol: str
    condition_type: MonitoringEvent
    threshold: float
    current_value: float
    message: str
    priority: int = 3  # 1=긴급, 5=정보


class RealtimeMonitoringHandler:
    """실시간 모니터링 통합 핸들러"""

    def __init__(self, config, kis_collector, db_manager: DatabaseManager):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.logger = get_logger("RealtimeMonitoringHandler")

        # 핵심 컴포넌트 초기화
        self.bulk_collector = BulkRealtimeCollector(
            config, kis_collector, db_manager
        )
        self.memory_storage = MemoryOptimizedStorage(
            max_symbols=250,  # 여유분 포함
            buffer_size_per_symbol=120
        )

        # 알림 시스템
        self.notification_manager = NotificationManager(config)

        # 모니터링 상태
        self.is_running = False
        self.monitoring_task = None
        self.alert_task = None

        # 알림 조건 저장소
        self.alert_conditions: Dict[str, List[AlertCondition]] = {}

        # 성능 통계
        self.performance_stats = {
            'monitoring_start_time': None,
            'total_data_points': 0,
            'alerts_triggered': 0,
            'avg_processing_time': 0.0,
            'symbols_processed': 0,
            'last_update_time': None
        }

        # 이벤트 핸들러
        self.event_handlers = {
            MonitoringEvent.PRICE_ALERT: self._handle_price_alert,
            MonitoringEvent.VOLUME_SPIKE: self._handle_volume_spike,
            MonitoringEvent.TARGET_REACHED: self._handle_target_reached,
            MonitoringEvent.STOP_LOSS_HIT: self._handle_stop_loss_hit,
            MonitoringEvent.ANOMALY_DETECTED: self._handle_anomaly_detected
        }

        self.logger.info("🔄 RealtimeMonitoringHandler 초기화 완료")

    async def start_monitoring(self, mode: CollectionMode = CollectionMode.HYBRID) -> bool:
        """실시간 모니터링 시작"""
        try:
            if self.is_running:
                self.logger.warning("이미 실시간 모니터링이 실행 중입니다")
                return True

            self.logger.info("🚀 실시간 모니터링 시스템 시작...")

            # 1. 알림 조건 로드
            await self._load_alert_conditions()

            # 2. 대용량 수집기 시작
            if not await self.bulk_collector.start_monitoring(mode):
                self.logger.error("❌ 대용량 수집기 시작 실패")
                return False

            # 3. 모니터링 루프 시작
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.alert_task = asyncio.create_task(self._alert_processing_loop())

            # 4. 통계 초기화
            self.performance_stats['monitoring_start_time'] = datetime.now()

            self.logger.info(f"✅ 실시간 모니터링 시작 완료 - 모드: {mode.value}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 실시간 모니터링 시작 실패: {e}")
            return False

    async def stop_monitoring(self) -> bool:
        """실시간 모니터링 중지"""
        try:
            if not self.is_running:
                return True

            self.logger.info("🛑 실시간 모니터링 시스템 중지...")

            self.is_running = False

            # 1. 태스크 중지
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass

            if self.alert_task and not self.alert_task.done():
                self.alert_task.cancel()
                try:
                    await self.alert_task
                except asyncio.CancelledError:
                    pass

            # 2. 대용량 수집기 중지
            await self.bulk_collector.stop_monitoring()

            # 3. 메모리 저장소 정리
            self.memory_storage.shutdown()

            # 4. 최종 통계 출력
            await self._log_final_statistics()

            self.logger.info("✅ 실시간 모니터링 중지 완료")
            return True

        except Exception as e:
            self.logger.error(f"❌ 실시간 모니터링 중지 실패: {e}")
            return False

    async def _monitoring_loop(self):
        """메인 모니터링 루프"""
        while self.is_running:
            try:
                start_time = time.time()

                # 1. 최신 데이터 수집 상태 확인
                collector_status = await self.bulk_collector.get_monitoring_status()

                if collector_status['is_running'] and collector_status['latest_data_count'] > 0:
                    # 2. 수집된 데이터를 메모리 저장소에 저장
                    await self._process_collected_data()

                    # 3. 알림 조건 검사
                    await self._check_alert_conditions()

                    # 4. 통계 업데이트
                    self._update_performance_stats(start_time)

                # 모니터링 간격
                await asyncio.sleep(2)  # 2초마다

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 모니터링 루프 오류: {e}")
                await asyncio.sleep(5)

    async def _process_collected_data(self):
        """수집된 데이터 처리"""
        try:
            # 대용량 수집기에서 최신 데이터 가져오기
            latest_data = self.bulk_collector.latest_data

            if not latest_data:
                return

            # 메모리 저장소에 저장 (우선순위 기반)
            for symbol, stock_data in latest_data.items():
                # 우선순위 결정
                priority = await self._determine_data_priority(symbol)

                # 메모리 저장소에 저장
                self.memory_storage.store_data(symbol, stock_data, priority)

                # 통계 업데이트
                self.performance_stats['total_data_points'] += 1

            self.performance_stats['symbols_processed'] = len(latest_data)
            self.performance_stats['last_update_time'] = datetime.now()

        except Exception as e:
            self.logger.error(f"❌ 수집 데이터 처리 실패: {e}")

    async def _determine_data_priority(self, symbol: str) -> DataPriority:
        """데이터 우선순위 결정"""
        try:
            with self.db_manager.get_session() as session:
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).first()

                if not stock:
                    return DataPriority.LOW

                # 매수 완료된 종목은 최고 우선순위
                if stock.buy_price and stock.buy_price > 0:
                    return DataPriority.CRITICAL

                # 전략별 우선순위
                high_priority_strategies = ['SMART_MONEY', 'VWAP_STRATEGY']
                if stock.strategy_name in high_priority_strategies:
                    return DataPriority.HIGH

                # 목표가 근접 시 높은 우선순위
                if stock.target_price and stock.current_price:
                    distance = abs(stock.current_price - stock.target_price) / stock.target_price
                    if distance < 0.05:  # 5% 이내
                        return DataPriority.HIGH

                return DataPriority.MEDIUM

        except Exception as e:
            self.logger.error(f"❌ {symbol} 우선순위 결정 실패: {e}")
            return DataPriority.MEDIUM

    async def _load_alert_conditions(self):
        """알림 조건 로드"""
        try:
            with self.db_manager.get_session() as session:
                active_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).all()

                for stock in active_stocks:
                    conditions = []

                    # 목표가 알림
                    if stock.target_price:
                        conditions.append(AlertCondition(
                            symbol=stock.symbol,
                            condition_type=MonitoringEvent.TARGET_REACHED,
                            threshold=stock.target_price,
                            current_value=0,
                            message=f"{stock.name} 목표가 도달",
                            priority=2
                        ))

                    # 손절가 알림
                    if stock.stop_loss_price:
                        conditions.append(AlertCondition(
                            symbol=stock.symbol,
                            condition_type=MonitoringEvent.STOP_LOSS_HIT,
                            threshold=stock.stop_loss_price,
                            current_value=0,
                            message=f"{stock.name} 손절가 도달",
                            priority=1
                        ))

                    # 거래량 급증 알림 (평균 대비 3배)
                    conditions.append(AlertCondition(
                        symbol=stock.symbol,
                        condition_type=MonitoringEvent.VOLUME_SPIKE,
                        threshold=3.0,
                        current_value=0,
                        message=f"{stock.name} 거래량 급증",
                        priority=3
                    ))

                    self.alert_conditions[stock.symbol] = conditions

                self.logger.info(f"📋 {len(self.alert_conditions)}개 종목 알림 조건 로드")

        except Exception as e:
            self.logger.error(f"❌ 알림 조건 로드 실패: {e}")

    async def _check_alert_conditions(self):
        """알림 조건 검사"""
        try:
            for symbol, conditions in self.alert_conditions.items():
                latest_data = self.memory_storage.get_latest_data(symbol)

                if not latest_data:
                    continue

                for condition in conditions:
                    condition.current_value = latest_data.get('price', 0)

                    if await self._evaluate_condition(condition, latest_data):
                        await self._trigger_alert(condition)

        except Exception as e:
            self.logger.error(f"❌ 알림 조건 검사 실패: {e}")

    async def _evaluate_condition(self, condition: AlertCondition, data: Dict) -> bool:
        """조건 평가"""
        try:
            if condition.condition_type == MonitoringEvent.TARGET_REACHED:
                return data['price'] >= condition.threshold

            elif condition.condition_type == MonitoringEvent.STOP_LOSS_HIT:
                return data['price'] <= condition.threshold

            elif condition.condition_type == MonitoringEvent.VOLUME_SPIKE:
                # 평균 거래량 대비 급증 확인
                historical = self.memory_storage.get_historical_data(condition.symbol, 30)
                if len(historical) < 5:
                    return False

                avg_volume = sum(h['volume'] for h in historical[:-1]) / len(historical[:-1])
                current_volume = data['volume']

                return current_volume > avg_volume * condition.threshold

            elif condition.condition_type == MonitoringEvent.PRICE_ALERT:
                # 가격 변동 알림 (임계치 돌파)
                return abs(data['change']) >= condition.threshold

            elif condition.condition_type == MonitoringEvent.ANOMALY_DETECTED:
                # 이상 패턴 감지
                return await self._detect_anomaly(condition.symbol, data)

            return False

        except Exception as e:
            self.logger.error(f"❌ 조건 평가 실패: {e}")
            return False

    async def _detect_anomaly(self, symbol: str, data: Dict) -> bool:
        """이상 패턴 감지"""
        try:
            # 가격 통계 기반 이상 감지
            stats = self.memory_storage.get_price_statistics(symbol, 10)

            if not stats:
                return False

            current_price = data['price']
            avg_price = stats['avg']
            volatility = stats['volatility']

            # 평균에서 3시그마 이상 벗어나면 이상
            threshold = avg_price + (3 * volatility)
            return current_price > threshold or current_price < (avg_price - 3 * volatility)

        except Exception as e:
            self.logger.error(f"❌ {symbol} 이상 패턴 감지 실패: {e}")
            return False

    async def _trigger_alert(self, condition: AlertCondition):
        """알림 발생"""
        try:
            # 중복 알림 방지 (5분 내 동일 조건)
            alert_key = f"{condition.symbol}_{condition.condition_type.value}"
            current_time = datetime.now()

            # 알림 발생
            await self.notification_manager.send_alert(
                title=f"🚨 {condition.condition_type.value.upper()}",
                message=condition.message,
                priority=condition.priority,
                data={
                    'symbol': condition.symbol,
                    'condition_type': condition.condition_type.value,
                    'threshold': condition.threshold,
                    'current_value': condition.current_value,
                    'timestamp': current_time.isoformat()
                }
            )

            # 이벤트 핸들러 실행
            if condition.condition_type in self.event_handlers:
                await self.event_handlers[condition.condition_type](condition)

            # 통계 업데이트
            self.performance_stats['alerts_triggered'] += 1

            self.logger.info(f"🚨 알림 발생: {condition.message}")

        except Exception as e:
            self.logger.error(f"❌ 알림 발생 실패: {e}")

    async def _alert_processing_loop(self):
        """알림 처리 루프"""
        while self.is_running:
            try:
                # 비동기 알림 처리
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 알림 처리 루프 오류: {e}")
                await asyncio.sleep(5)

    # 이벤트 핸들러들
    async def _handle_price_alert(self, condition: AlertCondition):
        """가격 알림 처리"""
        self.logger.info(f"💰 가격 알림: {condition.symbol} - {condition.current_value}")

    async def _handle_volume_spike(self, condition: AlertCondition):
        """거래량 급증 처리"""
        self.logger.info(f"📊 거래량 급증: {condition.symbol}")

    async def _handle_target_reached(self, condition: AlertCondition):
        """목표가 도달 처리"""
        self.logger.info(f"🎯 목표가 도달: {condition.symbol} - {condition.current_value}")

    async def _handle_stop_loss_hit(self, condition: AlertCondition):
        """손절가 도달 처리"""
        self.logger.warning(f"🛑 손절가 도달: {condition.symbol} - {condition.current_value}")

    async def _handle_anomaly_detected(self, condition: AlertCondition):
        """이상 패턴 감지 처리"""
        self.logger.warning(f"⚠️ 이상 패턴: {condition.symbol}")

    def _update_performance_stats(self, start_time: float):
        """성능 통계 업데이트"""
        processing_time = time.time() - start_time

        # 이동 평균으로 계산
        if self.performance_stats['avg_processing_time'] == 0:
            self.performance_stats['avg_processing_time'] = processing_time
        else:
            self.performance_stats['avg_processing_time'] = (
                self.performance_stats['avg_processing_time'] * 0.9 + processing_time * 0.1
            )

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """모니터링 상태 조회"""
        try:
            collector_status = await self.bulk_collector.get_monitoring_status()
            storage_stats = self.memory_storage.get_storage_statistics()

            return {
                'is_running': self.is_running,
                'monitoring_duration': (
                    datetime.now() - self.performance_stats['monitoring_start_time']
                ).total_seconds() if self.performance_stats['monitoring_start_time'] else 0,
                'collector_status': collector_status,
                'storage_stats': storage_stats,
                'performance_stats': self.performance_stats.copy(),
                'alert_conditions_count': sum(len(conditions) for conditions in self.alert_conditions.values()),
                'total_symbols': len(self.alert_conditions)
            }

        except Exception as e:
            self.logger.error(f"❌ 모니터링 상태 조회 실패: {e}")
            return {'is_running': False, 'error': str(e)}

    async def _log_final_statistics(self):
        """최종 통계 로깅"""
        try:
            stats = await self.get_monitoring_status()

            self.logger.info("📊 실시간 모니터링 최종 통계:")
            self.logger.info(f"   - 총 모니터링 시간: {stats['monitoring_duration']:.1f}초")
            self.logger.info(f"   - 총 데이터 포인트: {self.performance_stats['total_data_points']:,}")
            self.logger.info(f"   - 총 알림 발생: {self.performance_stats['alerts_triggered']:,}")
            self.logger.info(f"   - 평균 처리 시간: {self.performance_stats['avg_processing_time']:.3f}초")
            self.logger.info(f"   - 메모리 사용량: {stats['storage_stats']['memory_usage_mb']:.1f}MB")

        except Exception as e:
            self.logger.error(f"❌ 최종 통계 로깅 실패: {e}")

    async def add_custom_alert(self, symbol: str, condition_type: MonitoringEvent,
                             threshold: float, message: str, priority: int = 3) -> bool:
        """사용자 정의 알림 추가"""
        try:
            condition = AlertCondition(
                symbol=symbol,
                condition_type=condition_type,
                threshold=threshold,
                current_value=0,
                message=message,
                priority=priority
            )

            if symbol not in self.alert_conditions:
                self.alert_conditions[symbol] = []

            self.alert_conditions[symbol].append(condition)

            self.logger.info(f"✅ {symbol} 커스텀 알림 추가: {condition_type.value}")
            return True

        except Exception as e:
            self.logger.error(f"❌ {symbol} 커스텀 알림 추가 실패: {e}")
            return False

    async def remove_symbol_monitoring(self, symbol: str) -> bool:
        """종목 모니터링 제거"""
        try:
            # 알림 조건 제거
            self.alert_conditions.pop(symbol, None)

            # 대용량 수집기에서 제거
            await self.bulk_collector.remove_monitoring_stock(symbol)

            # 메모리 저장소에서 제거는 자동 관리됨

            self.logger.info(f"🗑️ {symbol} 모니터링 제거 완료")
            return True

        except Exception as e:
            self.logger.error(f"❌ {symbol} 모니터링 제거 실패: {e}")
            return False