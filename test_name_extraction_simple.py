#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import os
from pathlib import Path

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_kis_name_extraction():
    """KIS API 종목명 추출 테스트"""
    try:
        print("KIS API 종목명 추출 테스트 시작")
        print("=" * 50)
        
        from config import Config
        from data_collectors.kis_collector import KISCollector
        
        # KIS collector 초기화
        config = Config()
        kis_collector = KISCollector(config)
        
        await kis_collector.initialize()
        print("KIS collector 초기화 완료")
        
        # 테스트 대상 종목들
        test_symbols = ['000150', '443060', '003690', '005930']
        
        print(f"\n테스트 대상 종목: {len(test_symbols)}개")
        for symbol in test_symbols:
            print(f"   - {symbol}")
        
        print(f"\n각 종목별 종목명 추출 테스트:")
        print("-" * 50)
        
        for symbol in test_symbols:
            try:
                print(f"\n{symbol} 테스트 중...")
                
                # get_stock_info 호출
                stock_info = await kis_collector.get_stock_info(symbol)
                
                if stock_info:
                    print(f"   get_stock_info 성공: '{stock_info.name}'")
                else:
                    print(f"   get_stock_info 실패, 직접 API 호출 테스트...")
                    
                    # 직접 현재가 API 호출
                    result = await kis_collector._make_api_request(
                        method="GET",
                        endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
                        tr_id="FHKST01010100"
                    )
                    
                    output = result.get('output', {})
                    if output:
                        # 고급 종목명 추출 테스트
                        extracted_name = kis_collector._extract_stock_name(output, symbol)
                        print(f"   고급 추출 결과: '{extracted_name}'")
                        
                        if extracted_name.startswith('종목'):
                            print(f"   결과: 임시 이름 (실패)")
                        else:
                            print(f"   결과: 정확한 종목명 추출 (성공)")
                    else:
                        print(f"   API 응답 데이터 없음")
                
            except Exception as e:
                print(f"   오류: {e}")
        
        print(f"\n종목명 추출 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_kis_name_extraction())
    if success:
        print("\n종목명 추출 로직 테스트 성공!")
    else:
        print("\n종목명 추출 로직 테스트 실패!")