#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENUM 타입 수정 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from config import Config
from sqlalchemy import select

async def test_enum_fix():
    """ENUM 타입 수정이 제대로 되었는지 테스트"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)

        print("=== ENUM 타입 수정 테스트 ===")
        print()

        # 비동기 세션으로 테스트 (원래 오류 상황과 동일)
        async with db_manager.get_async_session() as session:
            print("[TEST] Async 세션으로 ENUM 타입 쿼리 테스트...")

            # 원래 오류가 발생했던 쿼리와 동일한 형태로 테스트
            query = select(MonitoringStock).where(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value
            ).order_by(MonitoringStock.recommendation_time.desc())

            result = await session.execute(query)
            monitoring_stocks = result.scalars().all()

            print(f"[SUCCESS] 활성 모니터링 종목 조회 성공: {len(monitoring_stocks)}개")

            if monitoring_stocks:
                for i, stock in enumerate(monitoring_stocks, 1):
                    print(f"  {i}. {stock.symbol}({stock.name}) - {stock.status}")
            else:
                print("  현재 활성 모니터링 종목이 없습니다.")

        # 동기 세션으로도 테스트
        with db_manager.get_session() as session:
            print("\n[TEST] 동기 세션으로 ENUM 타입 쿼리 테스트...")

            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value
            ).all()

            print(f"[SUCCESS] 동기 쿼리도 성공: {len(monitoring_stocks)}개")

        print("\n=== 테스트 결과 ===")
        print("[OK] ENUM 타입 수정이 성공적으로 완료되었습니다!")
        print("[OK] PostgreSQL ENUM 타입 오류가 해결되었습니다!")

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enum_fix())