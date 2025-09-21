#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
200개 종목 실시간 모니터링 시스템 통합 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from database.database_manager import DatabaseManager
from data_collectors.kis_collector import KISCollector
from data_collectors.bulk_realtime_collector import CollectionMode
from monitoring.realtime_monitoring_handler import RealtimeMonitoringHandler
from utils.realtime_display import RealtimeDisplay, DisplayMode, UpdateFrequency
from utils.logger import get_logger


async def test_realtime_monitoring_system():
    """실시간 모니터링 시스템 통합 테스트"""
    logger = get_logger("RealtimeTest")

    print("=" * 80)
    print("🚀 200개 종목 실시간 모니터링 시스템 테스트")
    print("=" * 80)
    print()

    try:
        # 1. 시스템 초기화
        print("1️⃣ 시스템 초기화 중...")

        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)

        # KIS Collector 초기화
        await kis_collector.initialize()
        print("   ✅ KIS Collector 초기화 완료")

        # 2. 실시간 모니터링 핸들러 초기화
        print("2️⃣ 실시간 모니터링 핸들러 초기화 중...")

        monitoring_handler = RealtimeMonitoringHandler(
            config=config,
            kis_collector=kis_collector,
            db_manager=db_manager
        )

        print("   ✅ 모니터링 핸들러 초기화 완료")

        # 3. 디스플레이 시스템 초기화
        print("3️⃣ 디스플레이 시스템 초기화 중...")

        display = RealtimeDisplay(monitoring_handler)

        # 모니터링 종목 로드
        await display.load_monitoring_stocks()

        print("   ✅ 디스플레이 시스템 초기화 완료")

        # 4. 성능 테스트 시작
        print("4️⃣ 성능 테스트 시작...")
        print(f"   시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 실시간 모니터링 시작
        print("🔄 실시간 모니터링 시작...")

        # 하이브리드 모드로 시작 (우선순위 기반)
        if await monitoring_handler.start_monitoring(CollectionMode.HYBRID):
            print("   ✅ 실시간 모니터링 시작 완료")

            # 초기 상태 확인
            await asyncio.sleep(5)  # 5초 대기

            status = await monitoring_handler.get_monitoring_status()
            print(f"   📊 모니터링 상태:")
            print(f"      - 총 종목: {status.get('total_symbols', 0)}개")
            print(f"      - 수집기 상태: {'실행 중' if status.get('collector_status', {}).get('is_running') else '중지됨'}")
            print(f"      - 메모리 사용량: {status.get('storage_stats', {}).get('memory_usage_mb', 0):.1f}MB")
            print()

            # 5. 디스플레이 시작 (대시보드 모드)
            print("5️⃣ 실시간 디스플레이 시작...")
            print("   📺 대시보드 모드로 시작 (Ctrl+C로 종료)")
            print()

            try:
                # 실시간 디스플레이 실행
                await display.start_display(
                    mode=DisplayMode.DASHBOARD,
                    frequency=UpdateFrequency.NORMAL
                )

            except KeyboardInterrupt:
                print("\n사용자에 의한 종료 요청...")

            # 6. 시스템 종료
            print("6️⃣ 시스템 종료 중...")

            # 디스플레이 중지
            await display.stop_display()
            print("   ✅ 디스플레이 중지 완료")

            # 모니터링 중지
            await monitoring_handler.stop_monitoring()
            print("   ✅ 모니터링 중지 완료")

        else:
            print("   ❌ 실시간 모니터링 시작 실패")
            return False

        print()
        print("=" * 80)
        print("✅ 200개 종목 실시간 모니터링 시스템 테스트 완료")
        print("=" * 80)

        return True

    except Exception as e:
        logger.error(f"❌ 시스템 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def quick_performance_test():
    """빠른 성능 테스트"""
    logger = get_logger("PerformanceTest")

    print("⚡ 빠른 성능 테스트 시작...")

    try:
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)

        await kis_collector.initialize()

        # 모니터링 핸들러 생성
        monitoring_handler = RealtimeMonitoringHandler(
            config=config,
            kis_collector=kis_collector,
            db_manager=db_manager
        )

        # 30초간 성능 테스트
        print("📊 30초간 데이터 수집 성능 테스트...")

        start_time = datetime.now()

        # 실시간 모니터링 시작
        if await monitoring_handler.start_monitoring(CollectionMode.HYBRID):

            # 30초 대기
            await asyncio.sleep(30)

            # 성능 통계 출력
            status = await monitoring_handler.get_monitoring_status()
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()

            print(f"⏱️ 테스트 결과 ({duration:.1f}초):")

            collector_status = status.get('collector_status', {})
            storage_stats = status.get('storage_stats', {})
            perf_stats = status.get('performance_stats', {})

            print(f"   - 총 종목: {collector_status.get('total_stocks', 0)}개")
            print(f"   - 활성 종목: {collector_status.get('active_stocks', 0)}개")
            print(f"   - 수집 성공률: {collector_status.get('success_rate', 0):.1%}")
            print(f"   - 평균 응답시간: {collector_status.get('avg_response_time', 0):.3f}초")
            print(f"   - 총 데이터 포인트: {perf_stats.get('total_data_points', 0):,}개")
            print(f"   - 메모리 사용량: {storage_stats.get('memory_usage_mb', 0):.1f}MB")
            print(f"   - 캐시 적중률: {storage_stats.get('cache_hit_rate', 0):.1%}")

            # 초당 처리량 계산
            data_per_second = perf_stats.get('total_data_points', 0) / duration
            print(f"   - 초당 처리량: {data_per_second:.1f} 데이터포인트/초")

            await monitoring_handler.stop_monitoring()

            print("✅ 성능 테스트 완료")

        else:
            print("❌ 성능 테스트 실패")

    except Exception as e:
        logger.error(f"❌ 성능 테스트 오류: {e}")


async def memory_stress_test():
    """메모리 스트레스 테스트"""
    logger = get_logger("MemoryStressTest")

    print("🧠 메모리 스트레스 테스트 시작...")

    try:
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)

        await kis_collector.initialize()

        # 모니터링 핸들러 생성
        monitoring_handler = RealtimeMonitoringHandler(
            config=config,
            kis_collector=kis_collector,
            db_manager=db_manager
        )

        # 10분간 메모리 사용량 모니터링
        print("📊 10분간 메모리 사용량 모니터링...")

        if await monitoring_handler.start_monitoring(CollectionMode.REALTIME):

            for minute in range(10):
                await asyncio.sleep(60)  # 1분 대기

                status = await monitoring_handler.get_monitoring_status()
                storage_stats = status.get('storage_stats', {})

                memory_mb = storage_stats.get('memory_usage_mb', 0)
                data_points = storage_stats.get('total_data_points', 0)

                print(f"   {minute+1}분: 메모리 {memory_mb:.1f}MB, 데이터 {data_points:,}개")

                # 메모리 사용량이 200MB를 초과하면 경고
                if memory_mb > 200:
                    print(f"   ⚠️ 메모리 사용량 경고: {memory_mb:.1f}MB")

            await monitoring_handler.stop_monitoring()
            print("✅ 메모리 스트레스 테스트 완료")

        else:
            print("❌ 메모리 스트레스 테스트 실패")

    except Exception as e:
        logger.error(f"❌ 메모리 스트레스 테스트 오류: {e}")


def main():
    """메인 실행 함수"""
    print("200개 종목 실시간 모니터링 시스템 테스트")
    print()
    print("테스트 옵션:")
    print("1. 전체 시스템 테스트 (디스플레이 포함)")
    print("2. 빠른 성능 테스트 (30초)")
    print("3. 메모리 스트레스 테스트 (10분)")
    print()

    choice = input("선택하세요 (1-3): ").strip()

    if choice == "1":
        asyncio.run(test_realtime_monitoring_system())
    elif choice == "2":
        asyncio.run(quick_performance_test())
    elif choice == "3":
        asyncio.run(memory_stress_test())
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    main()