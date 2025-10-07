#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SuperTrend 조건식 페이지네이션 테스트
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector
import json

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    user_id = getattr(config.kis_account, 'KIS_HTS_USER_ID', config.kis_account.KIS_USER_ID)
    
    print("\n" + "="*80)
    print("SuperTrend (ID: 6) 페이지네이션 테스트")
    print("="*80 + "\n")
    
    # 첫 번째 페이지
    result1 = await collector._make_api_request(
        method="GET",
        endpoint="/uapi/domestic-stock/v1/quotations/psearch-result",
        params={"user_id": user_id, "seq": "6"},
        tr_id="HHKST03900400",
        custtype="P"
    )
    
    print(f"첫 페이지 응답:")
    print(f"  rt_cd: {result1.get('rt_cd')}")
    print(f"  msg_cd: {result1.get('msg_cd')}")
    print(f"  msg1: {result1.get('msg1')}")
    print(f"  output2 개수: {len(result1.get('output2', []))}개")
    
    # msg1에 "조회가 계속" 있는지 확인
    if "조회가 계속" in result1.get('msg1', ''):
        print("\n✅ 페이지네이션 필요 감지!")
        print("하지만 KIS API는 seq 파라미터만으로는 다음 페이지 조회 불가")
        print("연속조회 키(ctx_area_fk, ctx_area_nk) 필요")
    else:
        print("\n❌ 페이지네이션 메시지 없음")
        print(f"실제 msg1: '{result1.get('msg1')}'")

if __name__ == "__main__":
    asyncio.run(main())
