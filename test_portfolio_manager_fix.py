#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_portfolio_manager_fix.py

포트폴리오 매니저 수정사항 테스트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.portfolio_manager import PortfolioManager
from core.trading_system import TradingSystem
from config import Config

async def test_portfolio_manager():
    """포트폴리오 매니저 테스트"""
    print("=== 포트폴리오 매니저 수정사항 테스트 ===")

    try:
        # 설정 로드
        config = Config()

        # 시스템 초기화
        system = TradingSystem(config)
        await system.initialize_components()

        print(f"시스템 초기화 완료")
        print(f"auto_trading_handler 존재: {hasattr(system, 'auto_trading_handler') and system.auto_trading_handler is not None}")
        print(f"db_auto_trading_handler 존재: {hasattr(system, 'db_auto_trading_handler') and system.db_auto_trading_handler is not None}")

        # 포트폴리오 매니저 초기화 (수정된 방식)
        portfolio_manager = PortfolioManager(
            trading_handler=getattr(system, 'auto_trading_handler', None),
            config=config
        )

        print(f"포트폴리오 매니저 trading_handler: {portfolio_manager.trading_handler is not None}")

        # 포트폴리오 상태 확인
        print("\n[INFO] 포트폴리오 상태 확인...")
        status = await portfolio_manager.get_portfolio_status()
        print(f"상태: {status}")

        # 정리 분석 시도
        print("\n[INFO] 포트폴리오 정리 분석...")
        analysis = await portfolio_manager.analyze_and_cleanup_portfolio()
        print(f"분석 결과: {analysis}")

        print("\n[OK] 테스트 완료 - 이제 더 나은 메시지가 표시됩니다!")

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_portfolio_manager())