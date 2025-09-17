#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종목명 확인 스크립트
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def verify_stock_names():
    """종목코드별 종목명 확인"""
    print("=" * 60)
    print("종목코드별 종목명 확인")
    print("=" * 60)
    
    try:
        from data_collectors.kis_collector import KISCollector
        from config import Config
        
        config = Config()
        kis_collector = KISCollector(config)
        
        await kis_collector.initialize()
        
        # 확인할 종목코드들
        target_codes = ['363260', '321370']
        
        print("사용자 제공 종목코드 확인:")
        print("-" * 40)
        
        for code in target_codes:
            try:
                # 개별 종목 정보 조회
                stock_info = await kis_collector.get_stock_info(code)
                if stock_info:
                    print(f"종목코드: {code}")
                    print(f"종목명: {stock_info.name}")
                    print(f"현재가: {stock_info.current_price:,}원")
                    print()
                else:
                    print(f"종목코드: {code} - 조회 실패")
                    print()
                    
            except Exception as e:
                print(f"종목코드: {code} - 오류: {e}")
                print()
        
        print("=" * 40)
        print("KIS API 보유종목 재확인:")
        print("-" * 40)
        
        holdings = await kis_collector.get_holdings()
        for symbol, data in holdings.items():
            if symbol in target_codes:
                print(f"[보유중] {symbol}: {data['name']} - {data['quantity']}주")
            else:
                print(f"[보유중] {symbol}: {data['name']} - {data['quantity']}주")
        
        print("\n" + "=" * 40)
        print("확인사항:")
        print("1. 363260이 '생서뷰'와 같은 종목인지 확인")
        print("2. 321370이 '모비데이즈'와 같은 종목인지 확인")
        print("3. HTS에서 표시되는 종목명과 비교")
        
        await kis_collector.cleanup()
        
    except Exception as e:
        print(f"[ERROR] 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_stock_names())