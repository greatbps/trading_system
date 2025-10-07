#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATR 기반 목표가/손절가 계산 로직 테스트
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from analyzers.technical_analyzer import TechnicalAnalyzer
import pandas as pd

def create_sample_price_data():
    """테스트용 가격 데이터 생성 (변동성 다른 3가지 패턴)"""

    # 패턴 1: 안정적인 대형주 (변동성 낮음)
    stable_stock = []
    base_price = 60000
    for i in range(30):
        stable_stock.append({
            'date': f'2025-01-{i+1:02d}',
            'open': base_price + (i % 3 - 1) * 100,
            'high': base_price + (i % 3) * 150,
            'low': base_price - (i % 3) * 150,
            'close': base_price + (i % 3 - 1) * 100,
            'volume': 1000000 + i * 10000
        })

    # 패턴 2: 변동성 큰 바이오주
    volatile_stock = []
    base_price = 15000
    for i in range(30):
        volatile_stock.append({
            'date': f'2025-01-{i+1:02d}',
            'open': base_price + (i % 5 - 2) * 800,
            'high': base_price + (i % 5) * 1200,
            'low': base_price - (i % 5) * 1200,
            'close': base_price + (i % 5 - 2) * 800,
            'volume': 500000 + i * 5000
        })

    # 패턴 3: 중간 변동성 종목
    normal_stock = []
    base_price = 30000
    for i in range(30):
        normal_stock.append({
            'date': f'2025-01-{i+1:02d}',
            'open': base_price + (i % 4 - 2) * 400,
            'high': base_price + (i % 4) * 600,
            'low': base_price - (i % 4) * 600,
            'close': base_price + (i % 4 - 2) * 400,
            'volume': 800000 + i * 8000
        })

    return {
        'stable': stable_stock,
        'volatile': volatile_stock,
        'normal': normal_stock
    }

async def test_atr_calculation():
    """ATR 계산 테스트"""
    print("\n" + "="*80)
    print("ATR 계산 로직 테스트")
    print("="*80 + "\n")

    config = Config()
    analyzer = TechnicalAnalyzer(config)

    test_data = create_sample_price_data()

    for stock_type, price_data in test_data.items():
        print(f"\n{'─'*80}")
        print(f"📊 {stock_type.upper()} 종목 테스트")
        print(f"{'─'*80}")

        # DataFrame 변환
        df = pd.DataFrame(price_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        current_price = df['close'].iloc[-1]
        print(f"현재가: {current_price:,}원")

        # ATR 계산
        atr = analyzer._calc_atr(df, period=14)
        print(f"ATR(14일): {atr:.2f}원")
        print(f"ATR 비율: {(atr/current_price)*100:.2f}%")

        # 손절가/목표가 계산 (ATR 기반)
        atr_sl_mult = 1.5
        atr_tp_mult = 2.5

        stop_loss_atr = int(current_price - atr * atr_sl_mult)
        target_price_atr = int(current_price + atr * atr_tp_mult)

        # 고정 비율 방식과 비교
        stop_loss_fixed = int(current_price * 0.95)  # -5%
        target_price_fixed = int(current_price * 1.10)  # +10%

        print(f"\n📉 손절가 비교:")
        print(f"  ATR 기반 (현재가 - ATR×{atr_sl_mult}): {stop_loss_atr:,}원 ({((stop_loss_atr-current_price)/current_price)*100:.2f}%)")
        print(f"  고정 비율 (-5%): {stop_loss_fixed:,}원")
        print(f"  차이: {abs(stop_loss_atr - stop_loss_fixed):,}원")

        print(f"\n📈 목표가 비교:")
        print(f"  ATR 기반 (현재가 + ATR×{atr_tp_mult}): {target_price_atr:,}원 ({((target_price_atr-current_price)/current_price)*100:.2f}%)")
        print(f"  고정 비율 (+10%): {target_price_fixed:,}원")
        print(f"  차이: {abs(target_price_atr - target_price_fixed):,}원")

        # Risk/Reward 비율
        risk_atr = current_price - stop_loss_atr
        reward_atr = target_price_atr - current_price
        rr_ratio_atr = reward_atr / risk_atr if risk_atr > 0 else 0

        risk_fixed = current_price - stop_loss_fixed
        reward_fixed = target_price_fixed - current_price
        rr_ratio_fixed = reward_fixed / risk_fixed if risk_fixed > 0 else 0

        print(f"\n⚖️ Risk/Reward 비율:")
        print(f"  ATR 기반: {rr_ratio_atr:.2f} (리스크 {risk_atr:,}원, 리워드 {reward_atr:,}원)")
        print(f"  고정 비율: {rr_ratio_fixed:.2f} (리스크 {risk_fixed:,}원, 리워드 {reward_fixed:,}원)")

        # 평가
        print(f"\n💡 평가:")
        if stock_type == 'volatile':
            if abs(stop_loss_atr - current_price) > abs(stop_loss_fixed - current_price):
                print("  ✅ 변동성 큰 종목에 더 넓은 손절가 적용됨 (정상)")
            else:
                print("  ❌ 변동성 큰 종목인데 손절가가 좁음 (문제)")
        elif stock_type == 'stable':
            if abs(stop_loss_atr - current_price) < abs(stop_loss_fixed - current_price):
                print("  ✅ 안정적인 종목에 더 좁은 손절가 적용됨 (정상)")
            else:
                print("  ⚠️ 안정적인 종목인데 손절가가 넓음 (과도한 리스크)")

async def test_db_auto_trader_atr():
    """DB Auto Trader의 ATR 기반 계산 테스트"""
    print("\n" + "="*80)
    print("DB Auto Trader ATR 통합 테스트")
    print("="*80 + "\n")

    from trading.db_auto_trader import DatabaseAutoTrader
    from data_collectors.kis_collector import KISCollector
    from trading.executor import TradingExecutor
    from utils.market_manager import MarketManager

    config = Config()

    # Mock 객체 생성 (실제 API 호출 없이 테스트)
    class MockKISCollector:
        def __init__(self):
            self.config = config

    class MockExecutor:
        def __init__(self):
            self.config = config

    class MockMarketManager:
        def is_monitoring_allowed_now(self):
            return True

    class MockDBManager:
        def get_session(self):
            from contextlib import contextmanager
            @contextmanager
            def session():
                yield None
            return session()

    trader = DatabaseAutoTrader(
        config=config,
        kis_collector=MockKISCollector(),
        executor=MockExecutor(),
        market_manager=MockMarketManager(),
        db_manager=MockDBManager()
    )

    # 테스트 데이터
    test_cases = [
        {
            'symbol': '005930',
            'current_price': 70000,
            'atr': 1500,  # 약 2.1% 변동성
            'expected_sl_range': (67750, 68500),  # 현재가 - 1500*1.5
            'expected_tp_range': (73750, 74500)   # 현재가 + 1500*2.5
        },
        {
            'symbol': '000660',
            'current_price': 120000,
            'atr': 4000,  # 약 3.3% 변동성 (높음)
            'expected_sl_range': (114000, 115000),
            'expected_tp_range': (130000, 131000)
        }
    ]

    for case in test_cases:
        print(f"\n{'─'*80}")
        print(f"📊 {case['symbol']} 테스트")
        print(f"{'─'*80}")
        print(f"현재가: {case['current_price']:,}원, ATR: {case['atr']:.2f}원")

        # 가격 데이터 생성 (ATR을 기반으로)
        price_data = []
        for i in range(20):
            price_data.append({
                'date': f'2025-01-{i+1:02d}',
                'open': case['current_price'] + (i % 3 - 1) * (case['atr'] * 0.5),
                'high': case['current_price'] + (i % 3) * (case['atr'] * 0.7),
                'low': case['current_price'] - (i % 3) * (case['atr'] * 0.7),
                'close': case['current_price'] + (i % 3 - 1) * (case['atr'] * 0.5),
                'volume': 1000000
            })

        # ATR 기반 계산
        sl, tp, calc_atr = await trader._calculate_atr_based_prices(
            symbol=case['symbol'],
            price_data=price_data,
            current_price=case['current_price']
        )

        print(f"\n계산 결과:")
        print(f"  계산된 ATR: {calc_atr:.2f}원" if calc_atr else "  ATR 계산 실패 (폴백 사용)")
        print(f"  손절가: {sl:,}원 ({((sl-case['current_price'])/case['current_price'])*100:.2f}%)")
        print(f"  목표가: {tp:,}원 ({((tp-case['current_price'])/case['current_price'])*100:.2f}%)")

        # 검증
        if case['expected_sl_range'][0] <= sl <= case['expected_sl_range'][1]:
            print(f"  ✅ 손절가 정상 범위")
        else:
            print(f"  ❌ 손절가 비정상 (예상: {case['expected_sl_range']})")

        if case['expected_tp_range'][0] <= tp <= case['expected_tp_range'][1]:
            print(f"  ✅ 목표가 정상 범위")
        else:
            print(f"  ❌ 목표가 비정상 (예상: {case['expected_tp_range']})")

async def main():
    """메인 테스트 실행"""
    try:
        await test_atr_calculation()
        await test_db_auto_trader_atr()

        print("\n" + "="*80)
        print("✅ ATR 계산 로직 테스트 완료")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
