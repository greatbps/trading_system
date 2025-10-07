#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건식 API 디버그 도구
"""
import sys
import os
import asyncio
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from data_collectors.kis_collector import KISCollector
from config import Config

async def debug_hts_conditions():
    """HTS 조건식 상세 디버그"""
    print("HTS 조건식 API 디버그")
    print("=" * 60)
    
    try:
        config = Config()
        collector = KISCollector(config)
        await collector.initialize()
        
        # 1. 조건식 목록 조회
        print("1. HTS 조건식 목록 조회...")
        conditions = await collector.get_hts_condition_list()
        print(f"   발견된 조건식 수: {len(conditions)}")
        
        # 조건식 구조 확인
        if conditions:
            print(f"   첫 번째 조건식 구조: {list(conditions[0].keys())}")
        
        for condition in conditions[:3]:  # 처음 3개만 테스트
            # 키 이름 확인 후 올바른 키 사용
            condition_id = condition.get('condition_id') or condition.get('seq') or condition.get('id')
            condition_name = condition.get('condition_name') or condition.get('name') or condition.get('condition_nm')
            
            print(f"\n2. 조건식 {condition_id} ('{condition_name}') 테스트...")
            
            # 직접 API 파라미터 확인
            print(f"   - User ID: {config.kis_account.KIS_USER_ID}")
            print(f"   - Condition ID: {condition_id}")
            print(f"   - API Endpoint: /uapi/domestic-stock/v1/quotations/psearch-result")
            
            try:
                # API 직접 호출하여 정확한 응답 확인
                result = await collector._make_api_request_with_pagination(
                    method="GET",
                    endpoint="/uapi/domestic-stock/v1/quotations/psearch-result",
                    params={
                        "user_id": config.kis_account.KIS_USER_ID,
                        "seq": str(condition_id)
                    },
                    tr_id="HHKST03900400",
                    custtype="P"
                )
                
                print("   ✅ API 호출 성공")
                print(f"   - rt_cd: {result.get('rt_cd')}")
                print(f"   - msg1: {result.get('msg1')}")
                print(f"   - msg_cd: {result.get('msg_cd')}")
                
                output2 = result.get('output2', [])
                print(f"   - 발견된 종목 수: {len(output2)}")
                
                if output2:
                    print("   - 첫 번째 종목 샘플:")
                    first_stock = output2[0]
                    print(f"     * 코드: {first_stock.get('code', 'N/A')}")
                    print(f"     * 이름: {first_stock.get('name', 'N/A')}")
                    print(f"     * 가격: {first_stock.get('price', 'N/A')}")
                else:
                    print("   - 조건에 맞는 종목 없음 (정상)")
                
            except Exception as api_error:
                print(f"   ❌ API 오류: {api_error}")
                print(f"   - 오류 타입: {type(api_error).__name__}")
                
                # 상세 오류 정보
                if hasattr(api_error, 'response_data'):
                    error_data = api_error.response_data
                    print(f"   - API 응답 코드: {error_data.get('rt_cd')}")
                    print(f"   - API 오류 메시지: {error_data.get('msg1')}")
                    print(f"   - API 오류 코드: {error_data.get('msg_cd')}")
        
        return True
        
    except Exception as e:
        print(f"디버그 오류: {e}")
        return False

def main():
    """메인 함수"""
    print(f"디버그 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = asyncio.run(debug_hts_conditions())
    
    print()
    print("=" * 60)
    if success:
        print("디버그 완료!")
    else:
        print("디버그 실패!")

if __name__ == "__main__":
    main()