#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동매매 시스템 상태 확인 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_auto_trading_status():
    """자동매매 시스템 상태 확인"""
    print("=" * 60)
    print("자동매매 시스템 상태 진단")
    print("=" * 60)
    
    print("현재 손실 종목들:")
    print("-" * 40)
    
    loss_stocks = [
        {'name': '미투온', 'rate': -9.83, 'loss': -1180, 'should_cut': True},
        {'name': '대한광통신', 'rate': -6.76, 'loss': -175, 'should_cut': True},
        {'name': '동원금속', 'rate': -4.05, 'loss': -10048, 'should_cut': False},
        {'name': '센서뷰', 'rate': -1.75, 'loss': -984, 'should_cut': False},
        {'name': '아진산업', 'rate': -0.97, 'loss': -510, 'should_cut': False},
        {'name': 'KD', 'rate': -0.66, 'loss': -317, 'should_cut': False}
    ]
    
    total_loss = 0
    should_cut_count = 0
    
    for stock in loss_stocks:
        status = "[손절필요]" if stock['should_cut'] else "[정상범위]"
        print(f"{status} {stock['name']}: {stock['rate']:+.2f}% ({stock['loss']:+,}원)")
        total_loss += stock['loss']
        if stock['should_cut']:
            should_cut_count += 1
    
    print("-" * 40)
    print(f"총 손실 금액: {total_loss:,}원")
    print(f"손절 필요 종목: {should_cut_count}개")
    
    print("\n" + "=" * 40)
    print("자동매매 시스템 점검사항")
    print("=" * 40)
    
    issues = [
        "1. [CRITICAL] 손절 시스템 미작동",
        "   - 미투온 -9.83% (손절선 -5% 돌파)",
        "   - 대한광통신 -6.76% (손절선 -5% 돌파)",
        "",
        "2. [HIGH] 매수 신호 정확도 문제", 
        "   - 7개 중 6개 손실 (승률 14%)",
        "   - 전략별 성과 검토 필요",
        "",
        "3. [MEDIUM] 리스크 관리 부족",
        "   - 포지션 사이징 검토 필요",
        "   - 분산투자 효과 미흡",
        "",
        "4. 점검 필요 사항:",
        "   □ 자동매매 모니터링 실행 여부",
        "   □ 손절 알고리즘 작동 여부", 
        "   □ 매매 모드 활성화 여부",
        "   □ 전략별 신호 품질",
        "   □ 시장 상황 vs 전략 적합성"
    ]
    
    for issue in issues:
        print(issue)
    
    print("\n" + "=" * 40)
    print("즉시 조치 필요:")
    print("=" * 40)
    print("1. 수동 손절: 미투온, 대한광통신")
    print("2. 자동매매 시스템 점검")
    print("3. 전략 재검토 및 조정")

if __name__ == "__main__":
    check_auto_trading_status()