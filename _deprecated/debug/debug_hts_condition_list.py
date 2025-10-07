#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS에 등록된 조건식 목록 전체 확인
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

async def main():
    config = Config()
    collector = KISCollector(config)
    await collector.initialize()
    
    print("\n" + "="*80)
    print("HTS 등록된 조건식 목록 확인")
    print("="*80 + "\n")
    
    conditions = await collector.get_hts_condition_list()
    
    if conditions:
        print(f"총 {len(conditions)}개 조건식 등록됨:\n")
        for cond in conditions:
            cond_id = cond.get('condition_id', 'N/A')
            cond_name = cond.get('condition_name', 'N/A')
            print(f"  ID: {cond_id:>3} | 이름: {cond_name}")
    else:
        print("조건식이 없거나 조회 실패")
    
    print("\n" + "="*80)
    print("config.py 설정과 비교")
    print("="*80 + "\n")
    
    print("config.py HTS_CONDITIONAL_SEARCH_IDS:")
    for strategy, seq_id in config.trading.HTS_CONDITIONAL_SEARCH_IDS.items():
        cond_name = config.trading.HTS_CONDITION_NAMES.get(strategy, 'N/A')
        print(f"  전략: {strategy:25} | ID: {seq_id} | 이름: {cond_name}")

if __name__ == "__main__":
    asyncio.run(main())
