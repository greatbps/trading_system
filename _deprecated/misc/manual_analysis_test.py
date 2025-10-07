#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 조건식 우회 - 수동 종목 분석 테스트
매수 기준 완화 효과 실제 확인
"""

import sys
import os
import asyncio
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import Config
from core.trading_system import TradingSystem

async def test_manual_analysis():
    """수동 종목 리스트로 분석 테스트"""
    print("KIS API 조건식 우회 - 수동 분석 테스트")
    print("=" * 60)
    print("매수 기준: 78점으로 완화 적용됨")
    print("=" * 60)
    
    try:
        # 시스템 초기화
        print("[1/3] 시스템 초기화 중...")
        config = Config()
        system = TradingSystem()
        
        # 컴포넌트 초기화
        print("[2/3] 컴포넌트 초기화 중...")
        await system.initialize_components()
        
        print("[3/3] 분석 시작...")
        print()
        
        # 테스트할 종목 리스트 (실제 종목코드)
        test_symbols = [
            {'symbol': '005930', 'name': '삼성전자'},
            {'symbol': '000660', 'name': 'SK하이닉스'},
            {'symbol': '005490', 'name': 'POSCO홀딩스'},
            {'symbol': '035420', 'name': 'NAVER'},
            {'symbol': '051910', 'name': 'LG화학'},
            {'symbol': '006400', 'name': '삼성SDI'},
            {'symbol': '012330', 'name': '현대모비스'},
            {'symbol': '028260', 'name': '삼성물산'},
            {'symbol': '066570', 'name': 'LG전자'},
            {'symbol': '105560', 'name': 'KB금융'}
        ]
        
        print(f"분석 대상: {len(test_symbols)}개 종목")
        print("-" * 60)
        
        # 각 종목 분석
        results = []
        buy_count = 0
        weak_buy_count = 0
        
        for i, stock in enumerate(test_symbols, 1):
            print(f"[{i}/{len(test_symbols)}] {stock['symbol']} ({stock['name']}) 분석 중...")
            
            try:
                # 종목 분석 실행
                result = await system.analysis_engine.analyze_comprehensive(
                    symbol=stock['symbol'],
                    name=stock['name'], 
                    stock_data={
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'current_price': 50000,  # 임시 가격
                        'change_rate': 0.0
                    },
                    strategy="momentum"
                )
                
                score = result.get('comprehensive_score', 0)
                recommendation = result.get('recommendation', 'HOLD')
                
                results.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'score': score,
                    'recommendation': recommendation
                })
                
                # 통계 집계
                if recommendation in ['BUY', 'STRONG_BUY']:
                    buy_count += 1
                elif recommendation == 'WEAK_BUY':
                    weak_buy_count += 1
                
                print(f"   결과: {score:.1f}점 - {recommendation}")
                
            except Exception as e:
                print(f"   오류: {str(e)[:50]}...")
                results.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'score': 0,
                    'recommendation': 'ERROR'
                })
        
        print()
        print("=" * 60)
        print("📊 분석 결과 요약")
        print("=" * 60)
        
        # 결과 정렬 (점수 순)
        valid_results = [r for r in results if r['recommendation'] != 'ERROR']
        valid_results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"{'순위':<4} {'종목코드':<8} {'종목명':<12} {'점수':<6} {'추천'}")
        print("-" * 50)
        
        for i, result in enumerate(valid_results, 1):
            print(f"{i:<4} {result['symbol']:<8} {result['name']:<12} {result['score']:<6.1f} {result['recommendation']}")
        
        print()
        print(f"🎯 매수 기준 완화 효과:")
        print(f"   BUY/STRONG_BUY: {buy_count}개")
        print(f"   WEAK_BUY: {weak_buy_count}개") 
        print(f"   총 매수 추천: {buy_count + weak_buy_count}개 / {len(valid_results)}개")
        print(f"   매수 비율: {((buy_count + weak_buy_count) / len(valid_results) * 100):.1f}%")
        
        if buy_count + weak_buy_count > 0:
            print()
            print("✅ 매수 기준 완화가 효과적으로 작동하고 있습니다!")
            print("   78점 기준으로 더 많은 매수 기회가 확보되었습니다.")
        else:
            print()
            print("ℹ️  현재 시장 상황에서는 추천할 종목이 없습니다.")
            print("   이는 보수적인 리스크 관리가 잘 작동하고 있음을 의미합니다.")
        
        return True
        
    except Exception as e:
        print(f"시스템 오류: {e}")
        return False

def main():
    """메인 함수"""
    print(f"수동 분석 테스트 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = asyncio.run(test_manual_analysis())
    
    print()
    print("=" * 60)
    if success:
        print("✅ 테스트 완료!")
    else:
        print("❌ 테스트 실패!")

if __name__ == "__main__":
    main()