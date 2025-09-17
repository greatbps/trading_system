#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
누락된 종목 검색 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def search_stock_patterns():
    """누락된 종목 패턴 검색"""
    print("=" * 60)
    print("누락된 종목 검색 도구")
    print("=" * 60)
    
    # 가능한 종목명 패턴들
    patterns = {
        "생서뷰": ["생서뷰", "생서뷰텍", "생화학서뷰", "서뷰"],
        "모비데이즈": ["모비데이즈", "모비", "데이즈", "Mobidays"]
    }
    
    print("1. 종목명 패턴 검색:")
    for stock, pattern_list in patterns.items():
        print(f"\n[{stock}] 가능한 검색 키워드:")
        for i, pattern in enumerate(pattern_list, 1):
            print(f"   {i}. '{pattern}'")
    
    print("\n" + "=" * 40)
    print("수동 확인 방법:")
    print("1. HTS에서 해당 종목들의 정확한 종목코드 확인")
    print("2. 종목코드 6자리 (예: 123456)")
    print("3. 정확한 종목명도 함께 확인")
    
    print("\n추가 확인사항:")
    print("• 넷마블랩(321370)이 HTS에 정말 없는지 재확인")
    print("• 매도 체결 시간과 KIS API 조회 시간 차이 확인")
    print("• HTS 새로고침 후 다시 확인")
    
    print("\n" + "=" * 40)
    print("해결 방안:")
    print("1. HTS에서 정확한 종목코드를 확인해주세요")
    print("2. 생서뷰: ??????")
    print("3. 모비데이즈: ??????")
    print("4. 확인되면 KIS API로 개별 조회 가능")

def check_common_stock_codes():
    """일반적인 종목코드 패턴 확인"""
    print("\n" + "=" * 60)
    print("일반적인 종목코드 패턴")
    print("=" * 60)
    
    patterns = [
        "생화학 관련: 096770(SK이노베이션), 000850(화성산업) 등",
        "바이오/제약: 207940(삼성바이오로직스), 068270(셀트리온) 등", 
        "IT/모바일: 035720(카카오), 035420(NAVER) 등"
    ]
    
    for pattern in patterns:
        print(f"• {pattern}")

if __name__ == "__main__":
    search_stock_patterns()
    check_common_stock_codes()