#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
휴장일 조회 API 발견 및 테스트
"""

import asyncio
import aiohttp
from data_collectors.kis_collector import KISCollector
from config import Config

async def test_different_holiday_apis():
    """다양한 휴장일 조회 API 시도"""
    print("=== 휴장일 조회 API 발견 테스트 ===")

    config = Config()
    collector = KISCollector(config)

    # 초기화
    await collector.initialize()

    # 다양한 TR ID 시도
    tr_ids_to_try = [
        "CTCA0903R",  # 현재 사용하는 것
        "CTPF1702R",  # 가능한 휴장일 조회 TR ID
        "CTSC0018R",  # 다른 가능한 TR ID
        "CTPF1702A",  # 또 다른 가능성
        "FHKST01010100",  # 일반적인 한국투자증권 패턴
    ]

    # 다양한 엔드포인트 시도
    endpoints_to_try = [
        "/uapi/domestic-stock/v1/quotations/chk-holiday",  # 현재 사용
        "/uapi/domestic-stock/v1/quotations/holiday-check",
        "/uapi/domestic-stock/v1/quotations/holiday",
        "/uapi/domestic-stock/v1/quotations/market-holiday",
        "/uapi/domestic-stock/v1/trading/holiday-check",
        "/uapi/domestic-stock/v1/trading/market-schedule",
    ]

    for tr_id in tr_ids_to_try:
        for endpoint in endpoints_to_try:
            print(f"\n🔍 테스트: TR_ID={tr_id}, ENDPOINT={endpoint}")

            try:
                result = await collector._make_api_request(
                    method="GET",
                    endpoint=endpoint,
                    params={
                        "BASS_DT": "20250916",
                        "CTX_AREA_NK": "",
                        "CTX_AREA_FK": ""
                    },
                    tr_id=tr_id
                )

                print(f"✅ 성공! TR_ID={tr_id}, ENDPOINT={endpoint}")
                print(f"응답: {result}")

                # 성공하면 더 이상 시도하지 않음
                return tr_id, endpoint, result

            except Exception as e:
                error_msg = str(e)
                if "유효하지 않은 token" in error_msg:
                    print(f"❌ 토큰 오류: {tr_id}")
                elif "not found" in error_msg.lower() or "404" in error_msg:
                    print(f"❌ 엔드포인트 없음: {endpoint}")
                elif "invalid tr_id" in error_msg.lower():
                    print(f"❌ 잘못된 TR_ID: {tr_id}")
                else:
                    print(f"❌ 기타 오류: {error_msg}")

    print("\n❌ 모든 조합 실패")
    return None, None, None

async def test_simple_market_api():
    """더 간단한 시장 API 시도"""
    print("\n=== 간단한 시장 API 테스트 ===")

    config = Config()
    collector = KISCollector(config)
    await collector.initialize()

    # 시장 현재가 조회 (이건 확실히 작동해야 함)
    simple_apis = [
        {
            "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-price",
            "tr_id": "FHKST01010100",
            "params": {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": "005930"  # 삼성전자
            }
        }
    ]

    for api_test in simple_apis:
        try:
            print(f"🔍 간단 API 테스트: {api_test['tr_id']}")

            result = await collector._make_api_request(
                method="GET",
                endpoint=api_test["endpoint"],
                params=api_test["params"],
                tr_id=api_test["tr_id"]
            )

            print(f"✅ 간단 API 성공!")
            print(f"응답 일부: {str(result)[:200]}...")

            # 토큰이 정상이면 휴장일 API 문제임
            print("🎯 토큰은 정상입니다. 휴장일 API 엔드포인트/TR_ID 문제입니다.")
            return True

        except Exception as e:
            print(f"❌ 간단 API도 실패: {e}")

    return False

if __name__ == "__main__":
    async def main():
        # 1단계: 휴장일 API 발견 시도
        tr_id, endpoint, result = await test_different_holiday_apis()

        if tr_id and endpoint:
            print(f"\n🎉 성공한 조합 발견!")
            print(f"TR_ID: {tr_id}")
            print(f"ENDPOINT: {endpoint}")
            return

        # 2단계: 간단한 API로 토큰 검증
        token_ok = await test_simple_market_api()

        if token_ok:
            print("\n💡 토큰은 정상이므로 휴장일 API 스펙을 다시 확인해야 합니다.")
        else:
            print("\n⚠️ 토큰 자체에 문제가 있을 수 있습니다.")

    asyncio.run(main())