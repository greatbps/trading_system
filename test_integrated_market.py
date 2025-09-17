#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 시장 일정 시스템 테스트
"""

import asyncio
from utils.market_schedule_manager import MarketScheduleManager
from config import Config

async def test_integrated_market():
    """통합 시장 일정 시스템 테스트"""
    print("=== 통합 시장 일정 테스트 ===")

    config = Config()

    # KIS Collector 초기화 (실패할 예정)
    from data_collectors.kis_collector import KISCollector
    kis_collector = KISCollector(config)

    manager = MarketScheduleManager(config, kis_collector)

    try:
        print("1. MarketScheduleManager 초기화...")
        await manager.initialize()
        print("   초기화 완료 (KIS API 실패 예상)")
    except Exception as e:
        print(f"   초기화 오류: {e}")

    # KIS API 실패 → Fallback 시스템 동작 테스트
    test_dates = ["20250916", "20250917", "20250919", "20250921"]

    for test_date in test_dates:
        print(f"\n2. {test_date} 시장 일정 조회...")

        schedule = await manager.get_market_schedule(test_date)

        if schedule:
            status = "개장" if schedule.is_market_open else "휴장"
            print(f"   결과: {status}")
            print(f"   영업일: {'O' if schedule.is_business_day else 'X'}")
            print(f"   거래일: {'O' if schedule.is_trading_day else 'X'}")
        else:
            print("   시장 일정 조회 실패")

    # 현재 상태 확인
    print(f"\n3. 현재 시장 상태 확인...")
    try:
        await manager.update_market_status()
        current_status = manager.current_status
        print(f"   현재 상태: {current_status.value}")
    except Exception as e:
        print(f"   상태 확인 오류: {e}")

    # 다음 거래일 확인
    print(f"\n4. 다음 거래일 확인...")
    try:
        next_open = await manager.get_next_market_open_time()
        if next_open:
            print(f"   다음 개장: {next_open.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("   다음 개장 시간 없음")
    except Exception as e:
        print(f"   다음 거래일 확인 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_integrated_market())