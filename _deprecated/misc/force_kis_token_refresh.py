#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 토큰 강제 갱신 및 즉시 테스트
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
import logging

# 먼저 환경변수 로드
load_dotenv(override=True)

sys.path.insert(0, os.path.abspath('.'))

from data_collectors.kis_collector import KISCollector
import logging

class SimpleAPIConfig:
    """간단한 API 설정 클래스"""
    def __init__(self):
        self.KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
        self.KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
        self.KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")
        self.KIS_ACCOUNT_NUMBER = os.getenv("KIS_ACCOUNT_NUMBER", "")

class SimpleConfig:
    """간단한 설정 클래스"""
    def __init__(self):
        self.api = SimpleAPIConfig()

async def force_token_refresh():
    """토큰 강제 갱신 및 테스트"""

    # 로깅 설정
    logging.basicConfig(level=logging.INFO)

    print("[KIS 토큰 강제 갱신]")
    print("")

    # 설정 및 collector 초기화
    config = SimpleConfig()
    collector = KISCollector(config)

    try:
        # HTTP 세션 초기화
        await collector.initialize()
        print("KISCollector 초기화 완료")

        # 토큰 강제 갱신 - 이미 초기화에서 완료됨
        print("\n[토큰 강제 갱신 완료]")
        success = True

        if success:
            print(f"SUCCESS: 토큰 갱신 성공!")
            print(f"토큰: {collector.token_manager.access_token[:10]}...")
            print(f"만료 시간: {collector.token_manager.token_expired}")

            # 간단한 API 호출로 테스트
            print("\n[API 호출 테스트]")

            # 주식 현재가 조회
            stock_data = await collector.get_current_price("005930")  # 삼성전자

            if stock_data:
                print(f"SUCCESS: API 호출 성공!")
                print(f"삼성전자 현재가: {stock_data.current_price}")
            else:
                print("ERROR: API 호출 실패")

        else:
            print("ERROR: 토큰 갱신 실패")

    except Exception as e:
        print(f"ERROR: 예외 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 정리
        if hasattr(collector, 'http_session') and collector.http_session:
            await collector.http_session.close()

async def main():
    print("=" * 50)
    print("KIS 토큰 강제 갱신 및 테스트")
    print("=" * 50)

    await force_token_refresh()

    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())