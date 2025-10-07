#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATR 계산 로직 간단 테스트 (독립 실행)
"""

import pandas as pd

def calc_atr(df, period=14):
    """ATR 계산"""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return float(atr.iloc[-1]) if not atr.empty and not pd.isna(atr.iloc[-1]) else 0.0

def create_test_data(stock_type, base_price, volatility_pct):
    """테스트 데이터 생성"""
    data = []
    for i in range(30):
        variation = base_price * volatility_pct * (i % 5 - 2) / 100
        data.append({
            'date': f'2025-01-{i+1:02d}',
            'open': base_price + variation,
            'high': base_price + abs(variation) * 1.5,
            'low': base_price - abs(variation) * 1.5,
            'close': base_price + variation,
            'volume': 1000000
        })
    return data

def test_atr_scenarios():
    """다양한 시나리오 테스트"""

    scenarios = [
        {'name': '안정 대형주 (삼성전자)', 'base': 70000, 'volatility': 2},
        {'name': '변동성 큰 바이오주', 'base': 15000, 'volatility': 8},
        {'name': '중간 변동성 종목', 'base': 30000, 'volatility': 4}
    ]

    print("\n" + "="*80)
    print("ATR 기반 손절/목표가 계산 테스트")
    print("="*80)

    for scenario in scenarios:
        print(f"\n{'─'*80}")
        print(f"📊 {scenario['name']}")
        print(f"{'─'*80}")

        # 데이터 생성
        price_data = create_test_data(scenario['name'], scenario['base'], scenario['volatility'])
        df = pd.DataFrame(price_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        current_price = df['close'].iloc[-1]
        atr = calc_atr(df, period=14)

        print(f"현재가: {current_price:,.0f}원")
        print(f"ATR(14): {atr:,.0f}원 ({(atr/current_price)*100:.2f}%)")

        # ATR 기반 계산
        atr_sl_mult = 1.5
        atr_tp_mult = 2.5

        sl_atr = int(current_price - atr * atr_sl_mult)
        tp_atr = int(current_price + atr * atr_tp_mult)

        # 고정 비율
        sl_fixed = int(current_price * 0.95)
        tp_fixed = int(current_price * 1.10)

        print(f"\n손절가:")
        print(f"  ATR 기반: {sl_atr:,}원 ({((sl_atr-current_price)/current_price)*100:.2f}%)")
        print(f"  고정 비율: {sl_fixed:,}원 (-5.00%)")
        print(f"  차이: {abs(sl_atr - sl_fixed):,}원")

        print(f"\n목표가:")
        print(f"  ATR 기반: {tp_atr:,}원 ({((tp_atr-current_price)/current_price)*100:.2f}%)")
        print(f"  고정 비율: {tp_fixed:,}원 (+10.00%)")
        print(f"  차이: {abs(tp_atr - tp_fixed):,}원")

        # R:R 비율
        risk_atr = current_price - sl_atr
        reward_atr = tp_atr - current_price
        rr_atr = reward_atr / risk_atr if risk_atr > 0 else 0

        risk_fixed = current_price - sl_fixed
        reward_fixed = tp_fixed - current_price
        rr_fixed = reward_fixed / risk_fixed if risk_fixed > 0 else 0

        print(f"\nR:R 비율:")
        print(f"  ATR 기반: 1:{rr_atr:.2f}")
        print(f"  고정 비율: 1:{rr_fixed:.2f}")

        # 평가
        print(f"\n💡 평가:")
        if scenario['volatility'] > 5:
            if abs((sl_atr - current_price)/current_price) > 0.05:
                print(f"  ✅ 변동성 큰 종목 → 넓은 손절가 ({abs((sl_atr-current_price)/current_price)*100:.2f}% > 5%)")
            else:
                print(f"  ❌ 변동성 큰데 손절가 너무 좁음")
        else:
            if abs((sl_atr - current_price)/current_price) < 0.05:
                print(f"  ✅ 안정적인 종목 → 좁은 손절가 ({abs((sl_atr-current_price)/current_price)*100:.2f}% < 5%)")
            else:
                print(f"  ⚠️ 안정적인데 손절가 너무 넓음 (과도한 리스크)")

    print("\n" + "="*80)
    print("✅ 테스트 완료")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_atr_scenarios()
