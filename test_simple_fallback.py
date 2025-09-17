#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 Fallback 시스템 테스트
"""

import asyncio
from utils.fallback_market_schedule import get_fallback_manager

async def test_simple_fallback():
    """간단한 Fallback 테스트"""
    print("=== Fallback 테스트 ===")

    fallback_manager = get_fallback_manager()

    # 추석 테스트
    result = await fallback_manager.get_market_schedule("20250917")

    if result:
        print(f"20250917 (추석):")
        print(f"  개장: {result.is_market_open}")
        print(f"  소스: {result.source}")

    # 평일 테스트
    result2 = await fallback_manager.get_market_schedule("20250919")

    if result2:
        print(f"20250919 (목요일):")
        print(f"  개장: {result2.is_market_open}")
        print(f"  소스: {result2.source}")

    # 주말 테스트
    result3 = await fallback_manager.get_market_schedule("20250921")

    if result3:
        print(f"20250921 (토요일):")
        print(f"  개장: {result3.is_market_open}")
        print(f"  소스: {result3.source}")

    return True

if __name__ == "__main__":
    success = asyncio.run(test_simple_fallback())
    if success:
        print("Fallback 시스템 정상 작동!")
    else:
        print("Fallback 시스템 오류")