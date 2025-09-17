#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매수 기준 완화 효과 간단 테스트
"""

def simulate_old_criteria(score, high_scores):
    """기존 매수 기준 (85점)"""
    if score >= 92: return "STRONG_BUY"
    elif score >= 85 and high_scores >= 3: return "BUY"
    elif score >= 75 and high_scores >= 2: return "WEAK_BUY"
    else: return "HOLD"

def simulate_new_criteria(score, high_scores):
    """새로운 매수 기준 (78점)"""
    if score >= 92: return "STRONG_BUY"
    elif score >= 78 and high_scores >= 2: return "BUY"
    elif score >= 68 and high_scores >= 1: return "WEAK_BUY"
    else: return "HOLD"

def main():
    print("매수 기준 완화 효과 테스트")
    print("=" * 50)
    
    # 실제 분석 결과 데이터 + 테스트 시나리오
    test_stocks = [
        {"name": "TestStock-A", "score": 82.5, "high_scores": 2},  # BUY 가능성
        {"name": "TestStock-B", "score": 79.3, "high_scores": 2},  # 새 기준으로 BUY
        {"name": "TestStock-C", "score": 76.8, "high_scores": 1},  # WEAK_BUY로 개선
        {"name": "TestStock-D", "score": 69.2, "high_scores": 1},  # WEAK_BUY로 개선  
        {"name": "SK Ocean", "score": 62.6, "high_scores": 1},
        {"name": "Mejion", "score": 55.99, "high_scores": 1},
    ]
    
    print("\n매수 기준 비교:")
    print(f"{'종목명':<12} {'점수':<6} {'기존기준':<10} {'새기준':<10} {'변화'}")
    print("-" * 55)
    
    old_buy_total = 0
    new_buy_total = 0
    
    for stock in test_stocks:
        old_rec = simulate_old_criteria(stock["score"], stock["high_scores"])
        new_rec = simulate_new_criteria(stock["score"], stock["high_scores"])
        
        if old_rec in ["BUY", "WEAK_BUY", "STRONG_BUY"]: old_buy_total += 1
        if new_rec in ["BUY", "WEAK_BUY", "STRONG_BUY"]: new_buy_total += 1
        
        change = "개선!" if new_rec != old_rec and new_rec in ["BUY", "WEAK_BUY", "STRONG_BUY"] else ""
        
        print(f"{stock['name']:<12} {stock['score']:<6.1f} {old_rec:<10} {new_rec:<10} {change}")
    
    print(f"\n결과 요약:")
    print(f"기존 기준: {old_buy_total}개 매수 추천")
    print(f"새 기준: {new_buy_total}개 매수 추천")
    print(f"매수 기회 증가: +{new_buy_total - old_buy_total}개")
    
    print("\n=" * 50)
    print("테스트 완료: 매수 기준 78점 완화가 적용되었습니다!")

if __name__ == "__main__":
    main()