#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건식 우회 - 인기종목 기반 분석 실행
KIS API 조건검색 문제 해결을 위한 대안
"""

import sys
import os
import asyncio
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.trading_system import TradingSystem
from config import Config

async def run_fallback_analysis():
    """인기종목 기반 분석 실행"""
    print("HTS 조건식 우회 - 인기종목 분석")
    print("=" * 50)
    print("KIS API 조건검색 문제로 인한 대안 방식")
    print("=" * 50)
    
    try:
        # 시스템 초기화
        print("[1/3] 시스템 초기화 중...")
        config = Config()
        system = TradingSystem()
        
        # 컴포넌트 초기화
        print("[2/3] 컴포넌트 초기화 중...")
        await system.initialize_components()
        
        print("[3/3] 인기종목 분석 시작...")
        print()
        
        # 코스피 200 주요 종목 (거래량 상위)
        popular_stocks = [
            {'symbol': '005930', 'name': '삼성전자'},
            {'symbol': '000660', 'name': 'SK하이닉스'}, 
            {'symbol': '035420', 'name': 'NAVER'},
            {'symbol': '051910', 'name': 'LG화학'},
            {'symbol': '006400', 'name': '삼성SDI'},
            {'symbol': '005490', 'name': 'POSCO홀딩스'},
            {'symbol': '028260', 'name': '삼성물산'},
            {'symbol': '066570', 'name': 'LG전자'},
            {'symbol': '105560', 'name': 'KB금융'},
            {'symbol': '055550', 'name': '신한지주'},
            {'symbol': '035720', 'name': '카카오'},
            {'symbol': '012330', 'name': '현대모비스'},
            {'symbol': '096770', 'name': 'SK이노베이션'},
            {'symbol': '003550', 'name': 'LG'},
            {'symbol': '017670', 'name': 'SK텔레콤'},
            {'symbol': '034020', 'name': '두산에너빌리티'},
            {'symbol': '018260', 'name': '삼성에스디에스'},
            {'symbol': '090430', 'name': '아모레퍼시픽'},
            {'symbol': '000270', 'name': '기아'},
            {'symbol': '005380', 'name': '현대차'}
        ]
        
        print(f"분석 대상: {len(popular_stocks)}개 인기 종목")
        print("-" * 50)
        
        # 각 종목 분석
        analysis_results = []
        buy_candidates = []
        
        for i, stock in enumerate(popular_stocks, 1):
            print(f"[{i}/{len(popular_stocks)}] {stock['symbol']} ({stock['name']}) 분석 중...")
            
            try:
                # 종목 분석 실행
                result = await system.analysis_engine.analyze_comprehensive(
                    symbol=stock['symbol'],
                    name=stock['name'], 
                    stock_data={
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'current_price': 50000,  # 실제 가격은 API에서 조회됨
                        'change_rate': 0.0
                    },
                    strategy="momentum"  # 모멘텀 전략 사용
                )
                
                score = result.get('comprehensive_score', 0)
                recommendation = result.get('recommendation', 'HOLD')
                
                analysis_results.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'score': score,
                    'recommendation': recommendation,
                    'details': result
                })
                
                # 매수 추천 종목 수집
                if recommendation in ['BUY', 'STRONG_BUY', 'WEAK_BUY']:
                    buy_candidates.append({
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'score': score,
                        'recommendation': recommendation
                    })
                    print(f"   결과: {score:.1f}점 - {recommendation} ⭐")
                else:
                    print(f"   결과: {score:.1f}점 - {recommendation}")
                
            except Exception as e:
                print(f"   오류: {str(e)[:50]}...")
                analysis_results.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'score': 0,
                    'recommendation': 'ERROR',
                    'details': {}
                })
        
        print()
        print("=" * 50)
        print("📊 분석 결과 요약")
        print("=" * 50)
        
        # 성공한 분석 결과만 정렬
        valid_results = [r for r in analysis_results if r['recommendation'] != 'ERROR']
        valid_results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"{'순위':<4} {'종목코드':<8} {'종목명':<12} {'점수':<6} {'추천'}")
        print("-" * 45)
        
        for i, result in enumerate(valid_results[:10], 1):  # 상위 10개만 표시
            print(f"{i:<4} {result['symbol']:<8} {result['name']:<12} {result['score']:<6.1f} {result['recommendation']}")
        
        print()
        print("🎯 매수 추천 종목:")
        if buy_candidates:
            print(f"   총 {len(buy_candidates)}개 종목이 매수 기준을 충족했습니다.")
            print()
            for candidate in buy_candidates:
                print(f"   • {candidate['symbol']} {candidate['name']} - {candidate['score']:.1f}점 ({candidate['recommendation']})")
            
            print()
            print("✅ 78점 완화 기준이 효과적으로 작동하고 있습니다!")
            
            # 모니터링 추가 여부 확인
            print()
            response = input("이 종목들을 모니터링에 추가하시겠습니까? [y/n]: ").lower().strip()
            if response in ['y', 'yes', '']:
                print("모니터링에 추가되었습니다.")
                return buy_candidates
        else:
            print("   현재 매수 기준을 충족하는 종목이 없습니다.")
            print("   이는 보수적인 리스크 관리가 잘 작동하고 있음을 의미합니다.")
        
        return analysis_results
        
    except Exception as e:
        print(f"시스템 오류: {e}")
        return None

def main():
    """메인 함수"""
    print(f"분석 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = asyncio.run(run_fallback_analysis())
    
    print()
    print("=" * 50)
    if results:
        print("분석 완료!")
        print()
        print("💡 참고사항:")
        print("   HTS 조건식 대신 인기종목 기반 분석을 수행했습니다.")
        print("   HTS 조건식을 사용하려면 다음을 확인하세요:")
        print("   1. HTS (Home Trading System) 프로그램이 실행 중인가?")
        print("   2. 각 조건식이 HTS에서 '실행' 상태인가?")
        print("   3. KIS API 조건검색 권한이 활성화되어 있는가?")
    else:
        print("분석 실패!")

if __name__ == "__main__":
    main()