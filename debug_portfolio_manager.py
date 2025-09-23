#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 매니저 디버깅 스크립트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.logger import get_logger
from data_collectors.kis_collector import KISCollector

async def debug_portfolio_manager():
    logger = get_logger("PortfolioDebug")

    try:
        # Config 설정
        class ConfigWrapper:
            def __init__(self):
                self.api = config.APIConfig()

        wrapped_config = ConfigWrapper()

        # KIS Collector 초기화
        kis_collector = KISCollector(wrapped_config)

        print("=" * 80)
        print("Portfolio Manager Debug")
        print("=" * 80)

        # 1. KIS Collector로 직접 조회
        print("\n1. KIS Collector 직접 조회:")
        holdings_direct = await kis_collector.get_holdings()
        print(f"   결과 타입: {type(holdings_direct)}")
        print(f"   결과 길이: {len(holdings_direct) if holdings_direct else 0}")
        if holdings_direct:
            if isinstance(holdings_direct, dict):
                print(f"   첫 번째 종목: {list(holdings_direct.keys())[0]}")
                print(f"   데이터 샘플: {list(holdings_direct.values())[0]}")
            else:
                print(f"   데이터 샘플: {holdings_direct[0] if holdings_direct else 'Empty'}")

        # 2. 직접 get_balance 로직 테스트
        print("\n2. get_balance 로직 직접 테스트:")
        if holdings_direct is None:
            print("   Holdings가 None - KIS API 연결 실패")
        elif isinstance(holdings_direct, dict):
            # KIS API get_holdings()는 {symbol: holding_data} 형태로 반환
            holdings_data = list(holdings_direct.values()) if holdings_direct else []
            print(f"   dict 형태 -> list 변환: {len(holdings_data)}개")
            if holdings_data:
                print(f"   변환된 첫 번째 데이터: {holdings_data[0]}")
        else:
            # holdings가 리스트인 경우
            holdings_data = holdings_direct if isinstance(holdings_direct, list) else []
            print(f"   list 형태 유지: {len(holdings_data)}개")

        print("=" * 80)

    except Exception as e:
        logger.error(f"디버깅 실패: {e}")
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_portfolio_manager())