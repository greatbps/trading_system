#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
강제 토큰 갱신 테스트
"""

import asyncio
import aiohttp
import json
import os
from data_collectors.kis_collector import KISCollector
from config import Config

async def test_force_token_refresh():
    """강제 토큰 갱신 테스트"""
    print("=== 강제 토큰 갱신 테스트 ===")

    config = Config()
    collector = KISCollector(config)

    # 기존 토큰 캐시 삭제
    cache_file = "data/kis_token_cache.json"
    if os.path.exists(cache_file):
        print(f"기존 토큰 캐시 삭제: {cache_file}")
        os.remove(cache_file)

    # 강제 초기화 (새 토큰 요청)
    print("새 토큰 요청 중...")
    await collector.initialize()

    print(f"새 액세스 토큰: {collector.token_manager.access_token[:20] if collector.token_manager.access_token else 'None'}...")
    print(f"토큰 만료: {collector.token_manager.token_expired}")

    # API 테스트
    try:
        print("\nAPI 테스트 중...")
        result = await collector._make_api_request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/chk-holiday",
            params={
                "BASS_DT": "20250916",
                "CTX_AREA_NK": "",
                "CTX_AREA_FK": ""
            },
            tr_id="CTCA0903R"
        )
        print("API 호출 성공!")
        print(f"결과: {result}")

        # 시장 일정 파싱
        if result.get('rt_cd') == '0' and 'output' in result:
            output = result['output']
            print(f"\n=== 시장 일정 정보 ===")
            print(f"날짜: {output.get('bass_dt', 'N/A')}")
            print(f"개장 여부: {output.get('opnd_yn', 'N/A')}")
            print(f"영업일 여부: {output.get('bzdy_yn', 'N/A')}")
            print(f"거래일 여부: {output.get('tr_day_yn', 'N/A')}")
            print(f"결제일 여부: {output.get('sttl_day_yn', 'N/A')}")
            print(f"요일 코드: {output.get('wday_dvsn_cd', 'N/A')}")

    except Exception as e:
        print(f"API 호출 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_force_token_refresh())