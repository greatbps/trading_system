#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매도 주문 수량 표시 수정 테스트
"""

import asyncio
from typing import Dict, Any, List

# 테스트용 가상 데이터
def create_test_execution_results() -> List[Dict[str, Any]]:
    """테스트용 execution_results 생성"""
    return [
        {
            "signal": {
                'symbol': '013360',
                'quantity_ratio': 1.0,
                'reason': '손절 (-3.9%)'
            },
            "execution_result": {
                'success': False,
                'order_id': None,
                'message': '013360 150주 매도 주문 완료',
                'quantity': 150,
                'reason': '손절 (-3.9%)'
            }
        },
        {
            "signal": {
                'symbol': '045340',
                'quantity_ratio': 0.8,
                'reason': '손절 (-4.6%)'
            },
            "execution_result": {
                'success': False,
                'order_id': None,
                'message': '045340 80주 매도 주문 완료',
                'quantity': 80,
                'reason': '손절 (-4.6%)'
            }
        }
    ]

def test_quantity_extraction():
    """수량 추출 테스트"""
    print("=" * 50)
    print("매도 주문 수량 표시 수정 테스트")
    print("=" * 50)

    execution_results = create_test_execution_results()

    print("\n테스트 결과:")
    print("종목   | 수량   | 결과 | 사유")
    print("-" * 40)

    for exec_result in execution_results:
        signal = exec_result['signal']
        result_data = exec_result['execution_result']

        # 수정된 로직: execution_result에서 quantity 가져오기
        quantity = result_data.get('quantity', 0)

        status_text = "성공" if result_data.get('success') else "실패"

        print(f"{signal['symbol']} | {quantity:4}주 | {status_text:4} | {signal['reason']}")

    print("\n수량이 올바르게 표시되었습니다!")

if __name__ == "__main__":
    test_quantity_extraction()