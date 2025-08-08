#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자동 매수 기능 테스트"""

import sys
import asyncio
sys.path.append('.')

async def test_auto_buy_functionality():
    """자동 매수 기능 테스트"""
    print('자동 매수 기능 테스트 시작...')
    
    try:
        from core.trading_system import TradingSystem
        from config import Config
        
        # 시스템 초기화 (매매 모드 비활성화로 시뮬레이션 테스트)
        config = Config()
        trading_system = TradingSystem(trading_enabled=False, backtest_mode=False)
        
        print('시스템 초기화 중...')
        if not await trading_system.initialize_components():
            print('[ERROR] 시스템 초기화 실패')
            return False
        
        print('[PASS] 시스템 초기화 완료')
        
        # 모의 분석 결과 생성 (실제 분석 대신 테스트용)
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
            }
        ]
        
        print(f'모의 분석 결과: {len(mock_results)}개 종목')
        
        # 자동 매수 기능 테스트
        print('\n자동 매수 기능 테스트 실행...')
        result = await trading_system.execute_auto_buy(
            results=mock_results,
            top_n=2,  # 상위 2개 종목
            budget_per_stock=1000000  # 종목당 100만원
        )
        
        print('\n테스트 결과:')
        print(f'성공: {result.get("success", False)}')
        if result.get('success'):
            print(f'총 주문: {result.get("total_orders", 0)}건')
            print(f'성공: {result.get("successful_orders", 0)}건')
            print(f'실패: {result.get("failed_orders", 0)}건')
        else:
            print(f'실패 사유: {result.get("reason", "알 수 없음")}')
        
        await trading_system.cleanup()
        return result.get('success', False)
        
    except Exception as e:
        print(f'[ERROR] 테스트 실패: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_auto_buy_functionality())
    if result:
        print('\n[SUCCESS] 자동 매수 기능 테스트 성공!')
    else:
        print('\n[FAILED] 자동 매수 기능 테스트 실패!')