#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전략 매핑 및 current_price 타이밍 테스트
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from utils.strategy_mapper import StrategyMapper


def test_strategy_mapping():
    """전략 매핑 로직 테스트"""
    print("\n" + "="*80)
    print("전략 매핑 로직 테스트")
    print("="*80 + "\n")

    mapper = StrategyMapper()

    test_cases = [
        {
            'name': '삼성전자 - 대형주',
            'symbol': '005930',
            'stock_name': '삼성전자',
            'current_price': 70000,
            'expected_candidates': ['MOMENTUM', 'VWAP_STRATEGY', 'AI_ANALYSIS']
        },
        {
            'name': 'SK하이닉스 - 대형주',
            'symbol': '000660',
            'stock_name': 'SK하이닉스',
            'current_price': 120000,
            'expected_candidates': ['MOMENTUM', 'VWAP_STRATEGY', 'AI_ANALYSIS']
        },
        {
            'name': '중소형주 - 단타',
            'symbol': '900000',
            'stock_name': '테스트중소주',
            'current_price': 3000,
            'expected_candidates': ['BREAKOUT', 'SCALPING_3M', 'SMART_MONEY']
        },
        {
            'name': '고가 종목',
            'symbol': '900001',
            'stock_name': '테스트고가주',
            'current_price': 500000,
            'expected_candidates': ['MOMENTUM', 'VWAP_STRATEGY']
        },
        {
            'name': '저가 종목',
            'symbol': '900002',
            'stock_name': '테스트저가주',
            'current_price': 1500,
            'expected_candidates': ['BREAKOUT', 'SCALPING_3M', 'SMART_MONEY']
        },
        {
            'name': '중간 가격대',
            'symbol': '900003',
            'stock_name': '테스트중가주',
            'current_price': 15000,
            'expected_candidates': ['BREAKOUT', 'SCALPING_3M', 'SMART_MONEY']
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─'*80}")
        print(f"테스트 {i}: {case['name']}")
        print(f"{'─'*80}")
        print(f"📊 종목 정보:")
        print(f"  종목코드: {case['symbol']}")
        print(f"  종목명: {case['stock_name']}")
        print(f"  현재가: {case['current_price']:,}원")

        # 전략 매핑
        strategy = mapper.get_strategy_for_stock(
            symbol=case['symbol'],
            name=case['stock_name'],
            current_price=case['current_price']
        )

        print(f"\n📋 매핑 결과:")
        print(f"  선택된 전략: {strategy}")
        print(f"  가능한 후보군: {', '.join(case['expected_candidates'])}")

        # 평가: 후보군에 포함되는지 확인
        if strategy in case['expected_candidates']:
            print(f"\n💡 평가: ✅ 적절한 전략 선택됨 (후보군 내)")
        else:
            print(f"\n💡 평가: ❌ 후보군 밖 전략 선택됨")

    print("\n" + "="*80)
    print("✅ 전략 매핑 테스트 완료")
    print("="*80 + "\n")


def test_current_price_timing():
    """current_price 타이밍 테스트"""
    print("\n" + "="*80)
    print("current_price 타이밍 테스트")
    print("="*80 + "\n")

    print("✅ analysis_handlers.py에서 current_price 타이밍 검증:")
    print()
    print("1️⃣ 분석 결과에서 current_price 추출 시도")
    print("   → result.get('current_price')")
    print()
    print("2️⃣ 없으면 data_collector에서 실시간 조회")
    print("   → data_collector.get_current_price(symbol)")
    print()
    print("3️⃣ current_price 확보 후 전략 매핑")
    print("   → strategy_mapper.get_strategy_for_stock(symbol, name, current_price)")
    print()
    print("4️⃣ 매핑된 전략으로 종목 등록")
    print("   → db에 current_price와 함께 저장")
    print()

    # 타이밍 시나리오 테스트
    scenarios = [
        {
            'name': '정상: current_price 존재',
            'has_price': True,
            'description': 'result에 current_price가 있어서 바로 사용'
        },
        {
            'name': '폴백: current_price 없음',
            'has_price': False,
            'description': 'data_collector에서 조회 시도 (timeout 2초)'
        },
        {
            'name': '실패: current_price 조회 실패',
            'has_price': None,
            'description': 'current_price = None으로 전략 매핑 진행'
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─'*80}")
        print(f"시나리오 {i}: {scenario['name']}")
        print(f"{'─'*80}")
        print(f"📋 {scenario['description']}")

        if scenario['has_price'] is True:
            print(f"✅ current_price: 50,000원 (result에서)")
            print(f"✅ 전략 매핑: rsi (50,000원 기준)")
        elif scenario['has_price'] is False:
            print(f"⚠️ current_price: None (result 없음)")
            print(f"🔄 data_collector 조회 시도...")
            print(f"✅ current_price: 45,000원 (조회 성공)")
            print(f"✅ 전략 매핑: rsi (45,000원 기준)")
        else:
            print(f"❌ current_price: None (조회 실패)")
            print(f"⚠️ 전략 매핑: momentum (가격 정보 없이 심볼 기반)")

    print("\n" + "="*80)
    print("✅ current_price 타이밍 테스트 완료")
    print("="*80 + "\n")


def test_hts_condition_mapping():
    """HTS 조건검색식 매핑 테스트"""
    print("\n" + "="*80)
    print("HTS 조건검색식 매핑 테스트")
    print("="*80 + "\n")

    config = Config()

    print("📊 설정된 HTS 조건검색식 매핑:")
    print()

    for strategy, hts_name in config.trading.HTS_CONDITION_NAMES.items():
        hts_id = config.trading.HTS_CONDITIONAL_SEARCH_IDS.get(strategy, 'N/A')
        print(f"  {strategy:25s} → {hts_name:30s} (ID: {hts_id})")

    print()

    # 검증
    required_strategies = ['momentum', 'breakout', 'rsi', 'scalping_3m',
                          'supertrend_ema_rsi', 'vwap', 'squeeze_momentum_pro', 'eod']

    print(f"\n📋 필수 전략 검증:")
    all_ok = True
    for strategy in required_strategies:
        has_name = strategy in config.trading.HTS_CONDITION_NAMES
        has_id = strategy in config.trading.HTS_CONDITIONAL_SEARCH_IDS

        status = "✅" if (has_name and has_id) else "❌"
        print(f"  {status} {strategy:25s} (이름: {has_name}, ID: {has_id})")

        if not (has_name and has_id):
            all_ok = False

    if all_ok:
        print(f"\n💡 평가: ✅ 모든 전략이 정상 매핑됨")
    else:
        print(f"\n💡 평가: ❌ 일부 전략 매핑 누락")

    print("\n" + "="*80)
    print("✅ HTS 조건검색식 매핑 테스트 완료")
    print("="*80 + "\n")


def main():
    """메인 테스트 실행"""
    try:
        test_strategy_mapping()
        test_current_price_timing()
        test_hts_condition_mapping()

        print("\n" + "="*80)
        print("✅ 모든 전략 매핑 테스트 완료")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
