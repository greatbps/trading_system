#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/memory_optimized_storage.py

200개 종목 실시간 데이터를 위한 메모리 최적화 저장 시스템
- 순환 버퍼를 통한 메모리 효율성
- 압축 저장
- 빠른 검색 및 집계
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, NamedTuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import pickle
import zlib
from concurrent.futures import ThreadPoolExecutor
import weakref
import gc

from utils.logger import get_logger


class DataPriority(Enum):
    """데이터 우선순위"""
    CRITICAL = 1    # 매매 중인 종목
    HIGH = 2        # 감시 리스트 상위
    MEDIUM = 3      # 일반 감시
    LOW = 4         # 백그라운드 모니터링


class StorageMode(Enum):
    """저장 모드"""
    MEMORY_ONLY = "memory_only"      # 메모리만 사용
    COMPRESSED = "compressed"        # 압축 저장
    HYBRID = "hybrid"               # 혼합 모드


@dataclass
class CompactStockData:
    """메모리 최적화 종목 데이터"""
    price: float           # 현재가
    change: float          # 변동률
    volume: int           # 거래량
    timestamp: int        # Unix timestamp (4바이트)

    @classmethod
    def from_stock_data(cls, stock_data):
        """일반 StockData에서 변환"""
        return cls(
            price=float(stock_data.current_price),
            change=float(stock_data.change_rate),
            volume=int(stock_data.volume or 0),
            timestamp=int(time.time())
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'price': self.price,
            'change': self.change,
            'volume': self.volume,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp)
        }


class CircularBuffer:
    """순환 버퍼 - 고정 크기 메모리 사용"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.data = deque(maxlen=max_size)
        self.total_count = 0
        self._lock = threading.RLock()

    def append(self, item: CompactStockData):
        """데이터 추가"""
        with self._lock:
            self.data.append(item)
            self.total_count += 1

    def get_latest(self, count: int = 1) -> List[CompactStockData]:
        """최신 데이터 조회"""
        with self._lock:
            if count == 1:
                return [self.data[-1]] if self.data else []
            else:
                return list(self.data)[-count:]

    def get_range(self, start_time: datetime, end_time: datetime) -> List[CompactStockData]:
        """시간 범위 데이터 조회"""
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        with self._lock:
            return [
                item for item in self.data
                if start_ts <= item.timestamp <= end_ts
            ]

    def calculate_avg_price(self, minutes: int = 5) -> Optional[float]:
        """평균가 계산"""
        cutoff_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp())

        with self._lock:
            recent_data = [
                item.price for item in self.data
                if item.timestamp >= cutoff_time
            ]

            return sum(recent_data) / len(recent_data) if recent_data else None

    def size(self) -> int:
        """현재 저장된 데이터 수"""
        return len(self.data)

    def memory_usage(self) -> int:
        """메모리 사용량 추정 (바이트)"""
        return len(self.data) * 32  # CompactStockData 약 32바이트


class CompressedStorage:
    """압축 저장소"""

    def __init__(self, compression_level: int = 6):
        self.compression_level = compression_level
        self.data: bytes = b''
        self.metadata: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def store(self, data: List[CompactStockData]):
        """데이터 압축 저장"""
        with self._lock:
            try:
                # 직렬화
                serialized = pickle.dumps(data)

                # 압축
                compressed = zlib.compress(serialized, self.compression_level)

                self.data = compressed
                self.metadata = {
                    'count': len(data),
                    'compressed_size': len(compressed),
                    'uncompressed_size': len(serialized),
                    'compression_ratio': len(compressed) / len(serialized),
                    'timestamp': time.time()
                }

            except Exception as e:
                raise RuntimeError(f"압축 저장 실패: {e}")

    def load(self) -> List[CompactStockData]:
        """데이터 압축 해제 및 로드"""
        with self._lock:
            try:
                if not self.data:
                    return []

                # 압축 해제
                decompressed = zlib.decompress(self.data)

                # 역직렬화
                data = pickle.loads(decompressed)

                return data

            except Exception as e:
                raise RuntimeError(f"압축 해제 실패: {e}")

    def get_compression_info(self) -> Dict[str, Any]:
        """압축 정보 조회"""
        return self.metadata.copy()


class MemoryOptimizedStorage:
    """메모리 최적화 실시간 데이터 저장소"""

    def __init__(self, max_symbols: int = 200, buffer_size_per_symbol: int = 100):
        self.max_symbols = max_symbols
        self.buffer_size_per_symbol = buffer_size_per_symbol
        self.logger = get_logger("MemoryOptimizedStorage")

        # 데이터 저장소
        self.buffers: Dict[str, CircularBuffer] = {}
        self.compressed_storage: Dict[str, CompressedStorage] = {}
        self.symbol_metadata: Dict[str, Dict[str, Any]] = {}

        # 우선순위 관리
        self.symbol_priorities: Dict[str, DataPriority] = {}
        self.access_times: Dict[str, float] = {}

        # 성능 통계
        self.stats = {
            'total_writes': 0,
            'total_reads': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_cleanups': 0,
            'compression_saves': 0
        }

        # 스레드 안전성
        self._global_lock = threading.RLock()

        # 메모리 관리 설정
        self.memory_threshold = 100 * 1024 * 1024  # 100MB
        self.cleanup_interval = 300  # 5분마다 정리

        # 백그라운드 태스크
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="MemStorage")

        self.logger.info(f"🧠 MemoryOptimizedStorage 초기화 - 최대 {max_symbols}개 종목")

    def store_data(self, symbol: str, data, priority: DataPriority = DataPriority.MEDIUM):
        """데이터 저장"""
        try:
            # CompactStockData로 변환
            if not isinstance(data, CompactStockData):
                compact_data = CompactStockData.from_stock_data(data)
            else:
                compact_data = data

            with self._global_lock:
                # 버퍼 초기화 (필요시)
                if symbol not in self.buffers:
                    self._initialize_symbol(symbol, priority)

                # 데이터 저장
                self.buffers[symbol].append(compact_data)

                # 메타데이터 업데이트
                self.symbol_metadata[symbol]['last_update'] = time.time()
                self.symbol_metadata[symbol]['total_updates'] += 1

                # 접근 시간 업데이트
                self.access_times[symbol] = time.time()

                # 통계 업데이트
                self.stats['total_writes'] += 1

                # 메모리 관리 (필요시)
                if self.stats['total_writes'] % 100 == 0:
                    self._schedule_memory_check()

        except Exception as e:
            self.logger.error(f"❌ {symbol} 데이터 저장 실패: {e}")

    def get_latest_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """최신 데이터 조회"""
        try:
            with self._global_lock:
                if symbol not in self.buffers:
                    self.stats['cache_misses'] += 1
                    return None

                buffer = self.buffers[symbol]
                latest = buffer.get_latest(1)

                if latest:
                    self.stats['cache_hits'] += 1
                    self.stats['total_reads'] += 1
                    self.access_times[symbol] = time.time()
                    return latest[0].to_dict()
                else:
                    self.stats['cache_misses'] += 1
                    return None

        except Exception as e:
            self.logger.error(f"❌ {symbol} 최신 데이터 조회 실패: {e}")
            return None

    def get_historical_data(self, symbol: str, minutes: int = 30) -> List[Dict[str, Any]]:
        """과거 데이터 조회"""
        try:
            with self._global_lock:
                if symbol not in self.buffers:
                    return []

                end_time = datetime.now()
                start_time = end_time - timedelta(minutes=minutes)

                buffer = self.buffers[symbol]
                historical = buffer.get_range(start_time, end_time)

                self.stats['total_reads'] += 1
                self.access_times[symbol] = time.time()

                return [item.to_dict() for item in historical]

        except Exception as e:
            self.logger.error(f"❌ {symbol} 과거 데이터 조회 실패: {e}")
            return []

    def get_price_statistics(self, symbol: str, minutes: int = 5) -> Optional[Dict[str, float]]:
        """가격 통계 계산"""
        try:
            historical = self.get_historical_data(symbol, minutes)

            if not historical:
                return None

            prices = [item['price'] for item in historical]

            return {
                'current': prices[-1] if prices else 0,
                'high': max(prices),
                'low': min(prices),
                'avg': sum(prices) / len(prices),
                'volatility': self._calculate_volatility(prices),
                'data_points': len(prices)
            }

        except Exception as e:
            self.logger.error(f"❌ {symbol} 가격 통계 계산 실패: {e}")
            return None

    def _calculate_volatility(self, prices: List[float]) -> float:
        """변동성 계산"""
        if len(prices) < 2:
            return 0.0

        avg = sum(prices) / len(prices)
        variance = sum((price - avg) ** 2 for price in prices) / len(prices)
        return variance ** 0.5

    def _initialize_symbol(self, symbol: str, priority: DataPriority):
        """종목 초기화"""
        # 용량 체크
        if len(self.buffers) >= self.max_symbols:
            self._cleanup_least_used()

        # 우선순위에 따른 버퍼 크기 조정
        buffer_size = self._get_buffer_size_by_priority(priority)

        self.buffers[symbol] = CircularBuffer(buffer_size)
        self.symbol_priorities[symbol] = priority
        self.symbol_metadata[symbol] = {
            'created_at': time.time(),
            'last_update': time.time(),
            'total_updates': 0,
            'priority': priority.value
        }

        self.logger.debug(f"📊 {symbol} 초기화 완료 - 우선순위: {priority.name}, 버퍼크기: {buffer_size}")

    def _get_buffer_size_by_priority(self, priority: DataPriority) -> int:
        """우선순위별 버퍼 크기 결정"""
        size_map = {
            DataPriority.CRITICAL: self.buffer_size_per_symbol * 2,  # 200
            DataPriority.HIGH: self.buffer_size_per_symbol,          # 100
            DataPriority.MEDIUM: self.buffer_size_per_symbol // 2,   # 50
            DataPriority.LOW: self.buffer_size_per_symbol // 4       # 25
        }
        return size_map.get(priority, self.buffer_size_per_symbol)

    def _cleanup_least_used(self):
        """사용량이 적은 종목 정리"""
        try:
            with self._global_lock:
                if not self.access_times:
                    return

                # 접근 시간 기준으로 정렬
                sorted_symbols = sorted(
                    self.access_times.items(),
                    key=lambda x: x[1]
                )

                # 하위 10% 제거
                remove_count = max(1, len(sorted_symbols) // 10)

                for symbol, _ in sorted_symbols[:remove_count]:
                    if self.symbol_priorities.get(symbol) != DataPriority.CRITICAL:
                        self._remove_symbol(symbol)
                        if len(self.buffers) < self.max_symbols * 0.9:
                            break

                self.stats['memory_cleanups'] += 1
                self.logger.info(f"🧹 메모리 정리 완료 - {remove_count}개 종목 제거")

        except Exception as e:
            self.logger.error(f"❌ 메모리 정리 실패: {e}")

    def _remove_symbol(self, symbol: str):
        """종목 데이터 제거"""
        try:
            # 압축 저장 (필요시)
            if symbol in self.buffers and self.buffers[symbol].size() > 10:
                self._compress_symbol_data(symbol)

            # 메모리에서 제거
            self.buffers.pop(symbol, None)
            self.symbol_metadata.pop(symbol, None)
            self.symbol_priorities.pop(symbol, None)
            self.access_times.pop(symbol, None)

        except Exception as e:
            self.logger.error(f"❌ {symbol} 제거 실패: {e}")

    def _compress_symbol_data(self, symbol: str):
        """종목 데이터 압축"""
        try:
            if symbol in self.buffers:
                buffer = self.buffers[symbol]
                data = buffer.get_latest(buffer.size())

                if data:
                    if symbol not in self.compressed_storage:
                        self.compressed_storage[symbol] = CompressedStorage()

                    self.compressed_storage[symbol].store(data)
                    self.stats['compression_saves'] += 1

        except Exception as e:
            self.logger.error(f"❌ {symbol} 압축 실패: {e}")

    def _schedule_memory_check(self):
        """메모리 체크 스케줄링"""
        try:
            self.executor.submit(self._perform_memory_check)
        except Exception as e:
            self.logger.error(f"❌ 메모리 체크 스케줄링 실패: {e}")

    def _perform_memory_check(self):
        """메모리 사용량 체크 및 정리"""
        try:
            total_memory = self.get_memory_usage()

            if total_memory > self.memory_threshold:
                self.logger.warning(f"⚠️ 메모리 사용량 임계치 초과: {total_memory / 1024 / 1024:.1f}MB")
                self._cleanup_least_used()

                # 가비지 컬렉션 강제 실행
                gc.collect()

        except Exception as e:
            self.logger.error(f"❌ 메모리 체크 실패: {e}")

    def get_memory_usage(self) -> int:
        """총 메모리 사용량 계산 (바이트)"""
        total = 0

        with self._global_lock:
            # 버퍼 메모리
            for buffer in self.buffers.values():
                total += buffer.memory_usage()

            # 압축 데이터 메모리
            for storage in self.compressed_storage.values():
                if hasattr(storage, 'data'):
                    total += len(storage.data)

            # 메타데이터 메모리 (추정)
            total += len(self.symbol_metadata) * 200

        return total

    def get_storage_statistics(self) -> Dict[str, Any]:
        """저장소 통계"""
        with self._global_lock:
            total_data_points = sum(buffer.size() for buffer in self.buffers.values())

            return {
                'total_symbols': len(self.buffers),
                'total_data_points': total_data_points,
                'memory_usage_mb': self.get_memory_usage() / 1024 / 1024,
                'memory_threshold_mb': self.memory_threshold / 1024 / 1024,
                'compressed_symbols': len(self.compressed_storage),
                'performance_stats': self.stats.copy(),
                'priority_distribution': self._get_priority_distribution(),
                'cache_hit_rate': (
                    self.stats['cache_hits'] /
                    max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
                )
            }

    def _get_priority_distribution(self) -> Dict[str, int]:
        """우선순위별 분포"""
        distribution = defaultdict(int)
        for priority in self.symbol_priorities.values():
            distribution[priority.name] += 1
        return dict(distribution)

    def set_symbol_priority(self, symbol: str, priority: DataPriority):
        """종목 우선순위 변경"""
        try:
            with self._global_lock:
                if symbol in self.symbol_priorities:
                    old_priority = self.symbol_priorities[symbol]
                    self.symbol_priorities[symbol] = priority

                    # 메타데이터 업데이트
                    if symbol in self.symbol_metadata:
                        self.symbol_metadata[symbol]['priority'] = priority.value

                    # 버퍼 크기 조정 (필요시)
                    new_size = self._get_buffer_size_by_priority(priority)
                    current_buffer = self.buffers[symbol]

                    if new_size != current_buffer.max_size:
                        # 새 버퍼 생성
                        new_buffer = CircularBuffer(new_size)

                        # 기존 데이터 이전
                        existing_data = current_buffer.get_latest(current_buffer.size())
                        for data in existing_data[-new_size:]:  # 새 크기만큼만
                            new_buffer.append(data)

                        self.buffers[symbol] = new_buffer

                    self.logger.info(f"📊 {symbol} 우선순위 변경: {old_priority.name} → {priority.name}")

        except Exception as e:
            self.logger.error(f"❌ {symbol} 우선순위 변경 실패: {e}")

    def bulk_update_priorities(self, symbol_priorities: Dict[str, DataPriority]):
        """벌크 우선순위 업데이트"""
        updated_count = 0

        for symbol, priority in symbol_priorities.items():
            try:
                self.set_symbol_priority(symbol, priority)
                updated_count += 1
            except Exception as e:
                self.logger.error(f"❌ {symbol} 우선순위 업데이트 실패: {e}")

        self.logger.info(f"📊 벌크 우선순위 업데이트 완료: {updated_count}/{len(symbol_priorities)}")

    def shutdown(self):
        """저장소 종료"""
        try:
            self.logger.info("🛑 MemoryOptimizedStorage 종료 중...")

            # 백그라운드 작업 종료
            self.executor.shutdown(wait=True)

            # 통계 출력
            stats = self.get_storage_statistics()
            self.logger.info(f"📊 최종 통계: {stats}")

            # 메모리 정리
            with self._global_lock:
                self.buffers.clear()
                self.compressed_storage.clear()
                self.symbol_metadata.clear()
                self.symbol_priorities.clear()
                self.access_times.clear()

            self.logger.info("✅ MemoryOptimizedStorage 종료 완료")

        except Exception as e:
            self.logger.error(f"❌ 저장소 종료 실패: {e}")