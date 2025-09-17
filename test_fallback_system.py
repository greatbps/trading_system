#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fallback 시장 일정 시스템 테스트
"""

import asyncio
from utils.fallback_market_schedule import get_fallback_manager
from utils.market_schedule_manager import MarketScheduleManager
from config import Config

async def test_fallback_system():
    """Fallback 시스템 테스트"""
    print("=== Fallback 시스템 테스트 ===")

    fallback_manager = get_fallback_manager()

    # 테스트할 날짜들
    test_dates = [
        "20250916",  # 오늘 (추석)
        "20250917",  # 추석
        "20250918",  # 추석 연휴
        "20250919",  # 목요일 (평일)
        "20250920",  # 금요일 (평일)
        "20250921",  # 토요일 (주말)
        "20250922",  # 일요일 (주말)
        "20250923",  # 월요일 (평일)
        "20251225",  # 크리스마스 (휴장일)
    ]

    for date in test_dates:
        print(f"\n📅 {date} 테스트:")

        result = await fallback_manager.get_market_schedule(date)

        if result:
            print(f"  개장 여부: {'✅ 개장' if result.is_market_open else '❌ 휴장'}")
            print(f"  영업일: {'O' if result.is_business_day else 'X'}")
            print(f"  거래일: {'O' if result.is_trading_day else 'X'}")
            print(f"  요일 코드: {result.weekday_code}")
            print(f"  데이터 소스: {result.source}")
        else:
            print("  결과 없음")

async def test_current_status():
    """현재 시장 상태 테스트"""
    print("\n=== 현재 시장 상태 테스트 ===")

    fallback_manager = get_fallback_manager()
    current_status = fallback_manager.get_current_market_status()

    print(f"현재 시장 상태: {current_status.value}")

    # 다음 거래일 확인
    next_trading = await fallback_manager.get_next_trading_day()
    if next_trading:
        print(f"다음 거래일: {next_trading.strftime('%Y-%m-%d %H:%M')}")
    else:
        print("다음 거래일을 찾을 수 없음")

async def test_integrated_system():
    """통합 시스템 테스트 (기존 MarketScheduleManager 사용)"""
    print("\n=== 통합 시스템 테스트 ===")

    config = Config()
    manager = MarketScheduleManager(config)

    # 초기화 (KIS API 실패 예상)
    print("MarketScheduleManager 초기화 중...")
    try:
        await manager.initialize()
        print("초기화 완료")
    except Exception as e:
        print(f"초기화 실패: {e}")

    # 시장 일정 조회 (Fallback 시스템 동작 예상)
    test_date = "20250917"  # 추석
    print(f"\n{test_date} 시장 일정 조회 (KIS API 실패 → Fallback 예상):")

    schedule = await manager.get_market_schedule(test_date)

    if schedule:
        print(f"  개장 여부: {'✅ 개장' if schedule.is_market_open else '❌ 휴장'}")
        print(f"  영업일: {'O' if schedule.is_business_day else 'X'}")
        print(f"  거래일: {'O' if schedule.is_trading_day else 'X'}")
        print(f"  요일 코드: {schedule.weekday_code}")
    else:
        print("  시장 일정 조회 실패")

async def main():
    """메인 테스트 함수"""
    print("🔄 Fallback 시스템 종합 테스트 시작")

    # 1단계: Fallback 시스템 단독 테스트
    await test_fallback_system()

    # 2단계: 현재 상태 테스트
    await test_current_status()

    # 3단계: 기존 시스템과 통합 테스트
    await test_integrated_system()

    print("\n✅ Fallback 시스템 테스트 완료")

if __name__ == "__main__":
    asyncio.run(main())