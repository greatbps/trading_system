#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보유종목 디버깅 스크립트
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def debug_holdings():
    """보유종목 디버깅"""
    print("=" * 60)
    print("보유종목 디버깅 - KIS API vs HTS 비교")
    print("=" * 60)
    
    try:
        from data_collectors.kis_collector import KISCollector
        from config import Config
        
        config = Config()
        kis_collector = KISCollector(config)
        
        print("1. KIS API 초기화 중...")
        await kis_collector.initialize()
        print("[OK] KIS API 초기화 완료")
        
        print("\n2. 보유종목 조회 중...")
        holdings = await kis_collector.get_holdings()
        
        print(f"\n3. KIS API 보유종목 결과: {len(holdings)}개")
        print("=" * 40)
        
        if holdings:
            for symbol, data in holdings.items():
                name = data.get('name', 'N/A')
                quantity = data.get('quantity', 0)
                current_price = data.get('current_price', 0)
                profit_rate = data.get('profit_rate', 0.0)
                
                print(f"종목: {name}({symbol})")
                print(f"  수량: {quantity}주")
                print(f"  현재가: {current_price:,}원")
                print(f"  수익률: {profit_rate:+.2f}%")
                print()
        else:
            print("보유종목이 없습니다.")
        
        print("=" * 40)
        print("HTS와 비교해서 확인하세요:")
        print("- 넷마블랩: KIS API에 있는지 확인")
        print("- 생서뷰, 모비데이즈: KIS API에서 누락되는지 확인")
        print("- 수량이 0인 종목이 있는지 확인")
        
        await kis_collector.cleanup()
        
    except Exception as e:
        print(f"[ERROR] 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_holdings())