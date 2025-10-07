#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS API 원본 응답 디버깅
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector
import json

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    # HTS 조건식 목록 API 원본 응답 확인
    user_id = getattr(config.kis_account, 'KIS_HTS_USER_ID', config.kis_account.KIS_USER_ID)
    
    print("\n" + "="*80)
    print("HTS 조건식 목록 API 원본 응답")
    print("="*80 + "\n")
    
    result = await collector._make_api_request(
        method="GET",
        endpoint="/uapi/domestic-stock/v1/quotations/psearch-title",
        params={"user_id": user_id},
        tr_id="HHKST03900300",
        custtype="P"
    )
    
    print("전체 응답:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "="*80)
    print("output2 상세:")
    print("="*80 + "\n")
    
    output2 = result.get('output2', [])
    for i, item in enumerate(output2):
        print(f"\n조건식 {i}:")
        print(json.dumps(item, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
