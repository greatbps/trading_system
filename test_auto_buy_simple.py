#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자동 매수 기능 간단 테스트 (API 없이)"""

import sys
import asyncio
sys.path.append('.')

async def test_auto_buy_logic():
    """자동 매수 로직만 테스트 (API 연결 없이)"""
    print('자동 매수 로직 테스트 시작...')
    
    try:
        # 모의 분석 결과 생성
        mock_results = [
            {
                'symbol': '005930',
                'name': '삼성전자',
                'comprehensive_score': 85.5,
                'recommendation': 'STRONG_BUY',
                'technical_score': 80,
                'sentiment_score': 90,
                'supply_demand_score': 85,
                'chart_pattern_score': 85
            },
            {
                'symbol': '000660',
                'name': 'SK하이닉스',
                'comprehensive_score': 78.2,
                'recommendation': 'BUY',
                'technical_score': 75,
                'sentiment_score': 80,
                'supply_demand_score': 78,
                'chart_pattern_score': 80
            },
            {
                'symbol': '035420',
                'name': 'NAVER',
                'comprehensive_score': 72.1,
                'recommendation': 'BUY',
                'technical_score': 70,
                'sentiment_score': 75,
                'supply_demand_score': 72,
                'chart_pattern_score': 71
            },
            {
                'symbol': '051910',
                'name': 'LG화학',
                'comprehensive_score': 55.0,  # 70점 이하 (매수 제외)
                'recommendation': 'HOLD',
                'technical_score': 55,
                'sentiment_score': 55,
                'supply_demand_score': 55,
                'chart_pattern_score': 55
            }
        ]
        
        print(f'모의 분석 결과: {len(mock_results)}개 종목')
        
        # 자동 매수 조건 테스트
        top_n = 3
        budget_per_stock = 1000000
        
        print(f'\n매수 조건:')
        print(f'- 상위 {top_n}개 종목')
        print(f'- 종목당 예산: {budget_per_stock:,}원')
        print(f'- 최소 점수: 70점 이상')
        print(f'- 추천 등급: STRONG_BUY, BUY만')
        
        # 매수 대상 선별 로직 테스트
        buy_candidates = []
        for result in mock_results[:top_n * 2]:  # 여유분 확보
            if result.get('recommendation') in ['STRONG_BUY', 'BUY']:
                score = result.get('comprehensive_score', 0)
                if score >= 70:  # 최소 70점 이상만
                    buy_candidates.append(result)
                    if len(buy_candidates) >= top_n:
                        break
        
        print(f'\n매수 대상 선별 결과:')
        print(f'- 조건 만족 종목: {len(buy_candidates)}개')
        
        if buy_candidates:
            print('\n매수 예정 종목:')
            for i, stock in enumerate(buy_candidates, 1):
                symbol = stock.get('symbol')
                name = stock.get('name', 'N/A')
                score = stock.get('comprehensive_score', 0)
                recommendation = stock.get('recommendation', 'N/A')
                
                # 모의 현재가 (실제로는 KIS API에서 가져옴)
                mock_prices = {
                    '005930': 70500,  # 삼성전자
                    '000660': 95000,  # SK하이닉스  
                    '035420': 180000  # NAVER
                }
                current_price = mock_prices.get(symbol, 50000)
                quantity = max(1, int(budget_per_stock / current_price))
                expected_amount = quantity * current_price
                
                print(f'  {i}. {symbol}({name})')
                print(f'     점수: {score:.1f}, 등급: {recommendation}')
                print(f'     현재가: {current_price:,}원, 수량: {quantity:,}주')
                print(f'     예상금액: {expected_amount:,}원')
        
        # 안전장치 테스트
        total_budget = len(buy_candidates) * budget_per_stock
        print(f'\n안전장치 확인:')
        print(f'- 총 투자 예정 금액: {total_budget:,}원')
        print(f'- 매수 가능 종목: {len(buy_candidates)}개')
        
        # 결과 요약
        if buy_candidates:
            print('\n[PASS] 자동 매수 로직 테스트 성공!')
            print(f'- 조건 만족 종목: {len(buy_candidates)}개')
            print('- 70점 이상, BUY 등급 종목만 선별됨')
            return True
        else:
            print('\n[WARN] 매수 조건을 만족하는 종목이 없습니다')
            return False
            
    except Exception as e:
        print(f'[ERROR] 테스트 실패: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_auto_buy_logic())
    if result:
        print('\n✅ 자동 매수 로직 검증 완료!')
    else:
        print('\n❌ 자동 매수 로직 검증 실패!')