#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/bulk_realtime_collector.py

200개 종목 실시간 모니터링을 위한 대용량 데이터 수집기
- 배치 처리 최적화
- 병렬 데이터 수집
- 메모리 효율성 극대화
- API 호출 최적화
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any, Coroutine
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
import logging
import random
from enum import Enum

from utils.logger import get_logger
from data_collectors.kis_collector import KISCollector, StockData
from database.database_manager import DatabaseManager
from database.monitoring_models import MonitoringStock, MonitoringStatus


class CollectionMode(Enum):
    """데이터 수집 모드"""
    REAL_TIME = "real_time"  # 실시간 모니터링
    BATCH = "batch"          # 배치 처리
    HYBRID = "hybrid"        # 하이브리드 (우선순위 기반)


@dataclass
class StockPriority:
    """종목 우선순위 정보"""
    symbol: str
    priority: int  # 1(최고) ~ 5(최저)
    last_update: datetime
    update_interval: int  # 초 단위
    consecutive_errors: int = 0
    is_active: bool = True


@dataclass
class BatchCollectionResult:
    """배치 수집 결과"""
    successful: Dict[str, StockData] = field(default_factory=dict)
    failed: Dict[str, str] = field(default_factory=dict)
    collection_time: float = 0.0
    total_symbols: int = 0
    success_rate: float = 0.0


class BulkRealtimeCollector:
    """200개 종목 실시간 모니터링을 위한 대용량 데이터 수집기"""

    def __init__(self, config, kis_collector: KISCollector, db_manager: DatabaseManager):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.logger = get_logger("BulkRealtimeCollector")

        # 수집 설정
        self.max_concurrent_requests = 50  # 동시 요청 수
        self.batch_size = 20  # 배치당 종목 수
        self.collection_interval = 5  # 기본 수집 간격 (초)
        self.timeout_per_request = 3  # 요청당 타임아웃

        # 우선순위 기반 수집 간격 설정
        self.priority_intervals = {
            1: 3,   # 최고 우선순위: 3초마다
            2: 5,   # 높음: 5초마다
            3: 10,  # 보통: 10초마다
            4: 30,  # 낮음: 30초마다
            5: 60   # 최저: 60초마다
        }

        # 데이터 저장소
        self.stock_priorities: Dict[str, StockPriority] = {}
        self.latest_data: Dict[str, StockData] = {}
        self.collection_stats: Dict[str, Any] = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'last_batch_time': 0.0
        }

        # 제어 변수
        self.is_running = False
        self.collection_task = None
        self.session_manager = None

        # 성능 추적
        self.response_times = deque(maxlen=100)
        self.error_counts = defaultdict(int)

        self.logger.info("🚀 BulkRealtimeCollector 초기화 완료")

    async def initialize(self) -> bool:
        """시스템 초기화"""
        try:
            # KIS Collector 초기화 확인
            if not self.kis_collector.is_initialized:
                await self.kis_collector.initialize()

            # HTTP 세션 매니저 설정
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_requests,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True
            )

            timeout = aiohttp.ClientTimeout(total=self.timeout_per_request)
            self.session_manager = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )

            # DB에서 모니터링 대상 종목 로드
            await self._load_monitoring_stocks()

            self.logger.info(f"✅ 초기화 완료 - 모니터링 대상: {len(self.stock_priorities)}개 종목")
            return True

        except Exception as e:
            self.logger.error(f"❌ 초기화 실패: {e}")
            return False

    async def _load_monitoring_stocks(self):
        """DB에서 모니터링 대상 종목 로드"""
        try:
            with self.db_manager.get_session() as session:
                active_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).all()

                for stock in active_stocks:
                    # 전략에 따른 우선순위 설정
                    priority = self._calculate_priority(stock)

                    self.stock_priorities[stock.symbol] = StockPriority(
                        symbol=stock.symbol,
                        priority=priority,
                        last_update=datetime.now() - timedelta(hours=1),  # 초기값
                        update_interval=self.priority_intervals[priority]
                    )

                self.logger.info(f"📊 {len(self.stock_priorities)}개 종목 로드 완료")

        except Exception as e:
            self.logger.error(f"❌ 모니터링 종목 로드 실패: {e}")

    def _calculate_priority(self, stock: MonitoringStock) -> int:
        """종목별 우선순위 계산"""
        # 전략에 따른 기본 우선순위
        strategy_priorities = {
            'SMART_MONEY': 1,      # 최고 우선순위
            'VWAP_STRATEGY': 2,    # 높음
            'SUPERTREND_EMA': 2,   # 높음
            'MOMENTUM': 3,         # 보통
            'RSI_STRATEGY': 3,     # 보통
            'BREAKOUT': 4,         # 낮음
            'EOD_STRATEGY': 5      # 최저
        }

        base_priority = strategy_priorities.get(stock.strategy_name, 3)

        # 추가 조건들로 우선순위 조정
        if stock.buy_price and stock.current_price:
            # 이미 매수한 종목은 우선순위 상승
            base_priority = max(1, base_priority - 1)

        if stock.target_price and stock.current_price:
            # 목표가 근접 시 우선순위 상승
            distance_to_target = abs(stock.current_price - stock.target_price) / stock.target_price
            if distance_to_target < 0.05:  # 5% 이내
                base_priority = max(1, base_priority - 1)

        return min(5, max(1, base_priority))

    async def start_monitoring(self, mode: CollectionMode = CollectionMode.HYBRID) -> bool:
        """실시간 모니터링 시작"""
        try:
            if self.is_running:
                self.logger.warning("이미 모니터링이 실행 중입니다")
                return True

            # 초기화 확인
            if not await self.initialize():
                return False

            self.is_running = True

            # 모드에 따른 수집 태스크 시작
            if mode == CollectionMode.REAL_TIME:
                self.collection_task = asyncio.create_task(self._realtime_collection_loop())
            elif mode == CollectionMode.BATCH:
                self.collection_task = asyncio.create_task(self._batch_collection_loop())
            else:  # HYBRID
                self.collection_task = asyncio.create_task(self._hybrid_collection_loop())

            self.logger.info(f"🚀 대용량 실시간 모니터링 시작 - 모드: {mode.value}")
            self.logger.info(f"📊 모니터링 대상: {len(self.stock_priorities)}개 종목")
            return True

        except Exception as e:
            self.logger.error(f"❌ 모니터링 시작 실패: {e}")
            return False

    async def stop_monitoring(self) -> bool:
        """모니터링 중지"""
        try:
            if not self.is_running:
                return True

            self.is_running = False

            # 수집 태스크 중지
            if self.collection_task and not self.collection_task.done():
                self.collection_task.cancel()
                try:
                    await self.collection_task
                except asyncio.CancelledError:
                    pass

            # 세션 정리
            if self.session_manager and not self.session_manager.closed:
                await self.session_manager.close()

            self.logger.info("🛑 대용량 실시간 모니터링 중지")
            return True

        except Exception as e:
            self.logger.error(f"❌ 모니터링 중지 실패: {e}")
            return False

    async def _hybrid_collection_loop(self):
        """하이브리드 수집 루프 (우선순위 기반)"""
        while self.is_running:
            try:
                start_time = time.time()

                # 수집 대상 선별 (우선순위 + 시간 간격 기반)
                targets = self._select_collection_targets()

                if targets:
                    # 우선순위별 그룹화
                    priority_groups = self._group_by_priority(targets)

                    # 높은 우선순위부터 처리
                    for priority in sorted(priority_groups.keys()):
                        symbols = priority_groups[priority]

                        # 배치로 수집
                        result = await self._collect_batch(symbols)

                        # 결과 처리
                        await self._process_collection_result(result)

                        # 우선순위 간 간격
                        if priority < max(priority_groups.keys()):
                            await asyncio.sleep(0.5)

                # 통계 업데이트
                self.collection_stats['last_batch_time'] = time.time() - start_time

                # 다음 수집까지 대기
                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 하이브리드 수집 루프 오류: {e}")
                await asyncio.sleep(5)

    def _select_collection_targets(self) -> List[str]:
        """수집 대상 종목 선별"""
        targets = []
        current_time = datetime.now()

        for symbol, priority_info in self.stock_priorities.items():
            if not priority_info.is_active:
                continue

            # 마지막 업데이트로부터 충분한 시간이 지났는지 확인
            time_since_update = (current_time - priority_info.last_update).total_seconds()

            if time_since_update >= priority_info.update_interval:
                targets.append(symbol)

        return targets

    def _group_by_priority(self, symbols: List[str]) -> Dict[int, List[str]]:
        """우선순위별 그룹화"""
        groups = defaultdict(list)

        for symbol in symbols:
            priority = self.stock_priorities[symbol].priority
            groups[priority].append(symbol)

        return dict(groups)

    async def _collect_batch(self, symbols: List[str]) -> BatchCollectionResult:
        """배치 데이터 수집"""
        start_time = time.time()
        result = BatchCollectionResult(total_symbols=len(symbols))

        # 배치를 더 작은 청크로 분할
        chunks = [symbols[i:i + self.batch_size] for i in range(0, len(symbols), self.batch_size)]

        for chunk in chunks:
            # 병렬 수집
            tasks = [self._collect_single_stock(symbol) for symbol in chunk]

            try:
                # 동시 실행 with timeout
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.timeout_per_request * 2
                )

                # 결과 처리
                for i, res in enumerate(results):
                    symbol = chunk[i]

                    if isinstance(res, Exception):
                        result.failed[symbol] = str(res)
                        self._handle_collection_error(symbol, str(res))
                    elif res:
                        result.successful[symbol] = res
                        self._handle_collection_success(symbol, res)
                    else:
                        result.failed[symbol] = "No data returned"
                        self._handle_collection_error(symbol, "No data returned")

                # 청크 간 간격
                if len(chunks) > 1:
                    await asyncio.sleep(0.2)

            except asyncio.TimeoutError:
                self.logger.warning(f"⏰ 배치 수집 타임아웃: {chunk}")
                for symbol in chunk:
                    result.failed[symbol] = "Timeout"
                    self._handle_collection_error(symbol, "Timeout")

        # 통계 계산
        result.collection_time = time.time() - start_time
        result.success_rate = len(result.successful) / result.total_symbols if result.total_symbols > 0 else 0

        # 성능 통계 업데이트
        self._update_collection_stats(result)

        return result

    async def _collect_single_stock(self, symbol: str) -> Optional[StockData]:
        """단일 종목 데이터 수집"""
        try:
            start_time = time.time()

            # KIS Collector를 통한 데이터 수집
            stock_data = await self.kis_collector.get_stock_data(symbol)

            # 응답 시간 추적
            response_time = time.time() - start_time
            self.response_times.append(response_time)

            return stock_data

        except Exception as e:
            self.error_counts[type(e).__name__] += 1
            raise e

    def _handle_collection_success(self, symbol: str, data: StockData):
        """수집 성공 처리"""
        # 최신 데이터 저장
        self.latest_data[symbol] = data

        # 우선순위 정보 업데이트
        if symbol in self.stock_priorities:
            priority_info = self.stock_priorities[symbol]
            priority_info.last_update = datetime.now()
            priority_info.consecutive_errors = 0

    def _handle_collection_error(self, symbol: str, error: str):
        """수집 실패 처리"""
        if symbol in self.stock_priorities:
            priority_info = self.stock_priorities[symbol]
            priority_info.consecutive_errors += 1

            # 연속 실패 시 우선순위 조정
            if priority_info.consecutive_errors >= 5:
                # 우선순위 낮추기 (간격 증가)
                priority_info.priority = min(5, priority_info.priority + 1)
                priority_info.update_interval = self.priority_intervals[priority_info.priority]

                self.logger.warning(f"⚠️ {symbol} 연속 실패로 우선순위 조정: {priority_info.priority}")

            # 너무 많이 실패하면 일시 비활성화
            if priority_info.consecutive_errors >= 10:
                priority_info.is_active = False
                self.logger.warning(f"🚫 {symbol} 일시 비활성화 (연속 실패 {priority_info.consecutive_errors}회)")

    def _update_collection_stats(self, result: BatchCollectionResult):
        """수집 통계 업데이트"""
        self.collection_stats['total_requests'] += result.total_symbols
        self.collection_stats['successful_requests'] += len(result.successful)
        self.collection_stats['failed_requests'] += len(result.failed)

        # 평균 응답 시간 계산
        if self.response_times:
            self.collection_stats['avg_response_time'] = sum(self.response_times) / len(self.response_times)

    async def _process_collection_result(self, result: BatchCollectionResult):
        """수집 결과 처리"""
        if result.successful:
            # 성공한 데이터를 DB에 업데이트 (배치로)
            await self._update_database_batch(result.successful)

            # 로깅
            self.logger.debug(f"📊 배치 수집 완료: {len(result.successful)}/{result.total_symbols} "
                            f"(성공률: {result.success_rate:.1%}, 소요시간: {result.collection_time:.2f}초)")

    async def _update_database_batch(self, data: Dict[str, StockData]):
        """데이터베이스 배치 업데이트"""
        try:
            with self.db_manager.get_session() as session:
                # 배치로 업데이트
                for symbol, stock_data in data.items():
                    stock = session.query(MonitoringStock).filter(
                        MonitoringStock.symbol == symbol,
                        MonitoringStock.status == MonitoringStatus.ACTIVE.value
                    ).first()

                    if stock:
                        stock.current_price = float(stock_data.current_price)
                        stock.change_rate = float(stock_data.change_rate)
                        stock.volume = int(stock_data.volume) if stock_data.volume else 0
                        stock.last_check_time = datetime.now()

                session.commit()

        except Exception as e:
            self.logger.error(f"❌ DB 배치 업데이트 실패: {e}")

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """모니터링 상태 조회"""
        active_count = sum(1 for p in self.stock_priorities.values() if p.is_active)

        return {
            'is_running': self.is_running,
            'total_stocks': len(self.stock_priorities),
            'active_stocks': active_count,
            'latest_data_count': len(self.latest_data),
            'collection_stats': self.collection_stats.copy(),
            'avg_response_time': self.collection_stats['avg_response_time'],
            'success_rate': (
                self.collection_stats['successful_requests'] /
                max(1, self.collection_stats['total_requests'])
            ),
            'priority_distribution': self._get_priority_distribution()
        }

    def _get_priority_distribution(self) -> Dict[int, int]:
        """우선순위별 분포"""
        distribution = defaultdict(int)
        for priority_info in self.stock_priorities.values():
            if priority_info.is_active:
                distribution[priority_info.priority] += 1
        return dict(distribution)

    async def add_monitoring_stock(self, symbol: str, priority: int = 3) -> bool:
        """모니터링 종목 추가"""
        try:
            if symbol in self.stock_priorities:
                self.logger.warning(f"⚠️ {symbol} 이미 모니터링 중")
                return False

            self.stock_priorities[symbol] = StockPriority(
                symbol=symbol,
                priority=priority,
                last_update=datetime.now() - timedelta(hours=1),
                update_interval=self.priority_intervals[priority]
            )

            self.logger.info(f"✅ {symbol} 모니터링 추가 (우선순위: {priority})")
            return True

        except Exception as e:
            self.logger.error(f"❌ {symbol} 모니터링 추가 실패: {e}")
            return False

    async def remove_monitoring_stock(self, symbol: str) -> bool:
        """모니터링 종목 제거"""
        try:
            if symbol in self.stock_priorities:
                del self.stock_priorities[symbol]

            if symbol in self.latest_data:
                del self.latest_data[symbol]

            self.logger.info(f"🗑️ {symbol} 모니터링 제거")
            return True

        except Exception as e:
            self.logger.error(f"❌ {symbol} 모니터링 제거 실패: {e}")
            return False

    async def _realtime_collection_loop(self):
        """실시간 수집 루프 (단순)"""
        while self.is_running:
            try:
                # 모든 활성 종목 수집
                active_symbols = [
                    symbol for symbol, priority_info in self.stock_priorities.items()
                    if priority_info.is_active
                ]

                if active_symbols:
                    result = await self._collect_batch(active_symbols)
                    await self._process_collection_result(result)

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 실시간 수집 루프 오류: {e}")
                await asyncio.sleep(5)

    async def _batch_collection_loop(self):
        """배치 수집 루프"""
        while self.is_running:
            try:
                # 모든 종목을 배치로 나누어 처리
                all_symbols = list(self.stock_priorities.keys())
                batches = [all_symbols[i:i + self.batch_size * 3]
                          for i in range(0, len(all_symbols), self.batch_size * 3)]

                for batch in batches:
                    if not self.is_running:
                        break

                    result = await self._collect_batch(batch)
                    await self._process_collection_result(result)

                    # 배치 간 간격
                    await asyncio.sleep(1)

                # 전체 배치 완료 후 대기
                await asyncio.sleep(self.collection_interval * 2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 배치 수집 루프 오류: {e}")
                await asyncio.sleep(10)