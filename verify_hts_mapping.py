#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTS 조건식 매핑 검증 스크립트
"""

import asyncio
from config import Config
from data_collectors.kis_collector import KISCollector

# HTS 실제 결과 (사용자 제공)
HTS_EXPECTED_COUNTS = {
    'scalping_3m': 0,           # 3분봉 스캘핑 전략 (ID: 0)
    'breakout': 3,              # Breakout (ID: 1)
    'eod': 22,                  # EOD (ID: 2)
    'momentum': 7,              # momentum (ID: 3) - 수정됨
    'rsi': 1,                   # RSI(상대강도지수) 전략 (ID: 4) - 수정됨
    'squeeze_momentum_pro': 4,  # Squeeze Momentum Pro (ID: 5) - 수정됨
    'supertrend_ema_rsi': 54,   # SuperTrend (ID: 6) - 수정됨
    'vwap': 147,                # VWAP (ID: 7) - 수정됨
}

async def verify_all_strategies():
    """모든 전략의 HTS 조건식 매핑 검증"""

    config = Config()
    kis_collector = KISCollector(config)

    # KISCollector 초기화
    await kis_collector.initialize()

    print("\n" + "="*80)
    print("HTS 조건식 매핑 검증 시작")
    print("="*80 + "\n")

    results = []

    for strategy, expected_count in HTS_EXPECTED_COUNTS.items():
        print(f"\n{'─'*80}")
        print(f"전략: {strategy}")
        print(f"{'─'*80}")

        # 조건식 ID 확인
        condition_id = config.trading.HTS_CONDITIONAL_SEARCH_IDS.get(strategy)
        condition_name = config.trading.HTS_CONDITION_NAMES.get(strategy)

        print(f"  조건식 ID: {condition_id}")
        print(f"  조건식 이름: {condition_name}")
        print(f"  예상 종목 수: {expected_count}개")

        # API 호출
        try:
            stocks = await kis_collector.get_filtered_stocks(strategy, limit=999)

            if stocks is None:
                actual_count = "API 실패"
                status = "❌ 실패"
            else:
                actual_count = len(stocks)

                # 결과 비교 (±2개 오차 허용 - 시장 변동성 고려)
                if actual_count == expected_count:
                    status = "✅ 정확"
                elif abs(actual_count - expected_count) <= 2:
                    status = "⚠️  거의 일치"
                else:
                    status = "❌ 불일치"

            print(f"  실제 종목 수: {actual_count}개")
            print(f"  상태: {status}")

            results.append({
                'strategy': strategy,
                'condition_id': condition_id,
                'expected': expected_count,
                'actual': actual_count,
                'status': status
            })

        except Exception as e:
            print(f"  오류: {e}")
            results.append({
                'strategy': strategy,
                'condition_id': condition_id,
                'expected': expected_count,
                'actual': "오류",
                'status': "❌ 오류"
            })

        # API 호출 제한 고려
        await asyncio.sleep(0.5)

    # 결과 요약
    print("\n" + "="*80)
    print("검증 결과 요약")
    print("="*80 + "\n")

    print(f"{'전략':<25} {'ID':<5} {'예상':<8} {'실제':<8} {'상태':<15}")
    print("─"*80)

    for result in results:
        print(f"{result['strategy']:<25} {result['condition_id']:<5} "
              f"{result['expected']:<8} {result['actual']!s:<8} {result['status']:<15}")

    print("\n" + "="*80)

    # 통계
    success_count = sum(1 for r in results if '✅' in r['status'])
    warning_count = sum(1 for r in results if '⚠️' in r['status'])
    fail_count = sum(1 for r in results if '❌' in r['status'])

    print(f"\n통계:")
    print(f"  ✅ 정확: {success_count}개")
    print(f"  ⚠️  거의 일치: {warning_count}개")
    print(f"  ❌ 불일치/실패: {fail_count}개")
    print()

if __name__ == "__main__":
    asyncio.run(verify_all_strategies())
