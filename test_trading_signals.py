#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매매 신호 분석기 테스트
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

# Windows 콘솔 인코딩 설정
if os.name == 'nt':  # Windows
    try:
        os.system("chcp 65001 > nul 2>&1")  # UTF-8 설정
    except:
        pass

from analyzers.trading_signals import TradingSignalAnalyzer

def create_sample_data():
    """테스트용 샘플 데이터 생성"""
    # 100일간의 일봉 데이터 생성
    dates = pd.date_range('2024-01-01', periods=100, freq='D')

    np.random.seed(42)  # 재현 가능한 데이터

    # 기본 가격 (10,000원 시작)
    price_changes = np.random.randn(100) * 100  # 일일 변동
    prices = 10000 + np.cumsum(price_changes)

    # OHLC 데이터 생성
    close_prices = prices
    open_prices = close_prices + np.random.randn(100) * 50
    high_prices = np.maximum(open_prices, close_prices) + np.random.rand(100) * 100
    low_prices = np.minimum(open_prices, close_prices) - np.random.rand(100) * 100

    # 거래량 (랜덤)
    volumes = np.random.randint(50000, 500000, 100)

    # 특정 날짜에 의도적으로 신호 생성
    # 90일째에 강한 매수 신호 생성
    volumes[-10:] = np.random.randint(200000, 800000, 10)  # 거래량 급증
    close_prices[-5:] = close_prices[-5:] + np.cumsum([50, 60, 40, 30, 20])  # 상승 추세

    df = pd.DataFrame({
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': volumes
    }, index=dates)

    return df

def test_trading_signals():
    """매매 신호 분석 테스트"""
    print("=" * 60)
    print("매매 신호 분석기 테스트")
    print("=" * 60)

    # 샘플 데이터 생성
    print("\n[데이터] 테스트 데이터 생성 중...")
    sample_data = create_sample_data()
    print(f"[완료] {len(sample_data)}일간의 OHLCV 데이터 생성 완료")

    # 매매 신호 분석기 초기화
    analyzer = TradingSignalAnalyzer()

    # 매매 신호 분석
    print("\n[분석] 매매 신호 분석 중...")
    result = analyzer.analyze_stock_signals('TEST001', sample_data)

    if 'error' in result:
        print(f"[오류] 분석 실패: {result['error']}")
        return

    # 결과 출력
    latest = result['latest_signals']

    print(f"\n[결과] 분석 결과 - {result['stock_code']}")
    print(f"매수 신호: {'있음' if latest['has_signal'] else '없음'}")
    print(f"신호 강도: {latest['signal_strength']}%")
    print(f"활성 조건: {latest['signal_count']}/5개")

    print(f"\n[상세] 개별 조건 분석:")
    conditions = {
        'RSI_signal': 'RSI 과매도 탈출',
        'VOL_signal': '거래량 급증',
        'MACD_signal': 'MACD 매수 신호',
        'CANDLE_signal': '강세 캔들 패턴',
        'GOLDEN_signal': '골든 크로스'
    }

    for condition, name in conditions.items():
        status = "활성" if latest['signals'].get(condition, False) else "비활성"
        print(f"  - {name}: {status}")

    # 가격 정보
    price_info = latest['price_info']
    print(f"\n[가격] 가격 정보:")
    print(f"  - 현재가: {price_info['close']:,.0f}원")
    print(f"  - 거래량: {price_info['volume']:,}주")
    print(f"  - RSI: {price_info['rsi']:.1f}")
    print(f"  - 5일선: {price_info['ma5']:,.0f}원")
    print(f"  - 20일선: {price_info['ma20']:,.0f}원")

    # 최근 신호 이력
    if result['recent_history']:
        print(f"\n[이력] 최근 매수 신호 이력:")
        for i, signal in enumerate(result['recent_history'][-3:], 1):  # 최근 3개
            date_str = signal['date'].strftime('%Y-%m-%d') if hasattr(signal['date'], 'strftime') else str(signal['date'])
            print(f"  {i}. {date_str}: 강도 {signal['signal_strength']}% ({', '.join(signal['active_signals'])})")
    else:
        print(f"\n[이력] 최근 7일간 매수 신호 없음")

    # 통계 정보
    stats = result['statistics']
    print(f"\n[통계] 분석 통계:")
    print(f"  - 총 매수 신호 발생: {stats.get('total_signals', 0)}회")
    print(f"  - 평균 신호 강도: {stats.get('avg_signal_strength', 0)}%")

    freq = stats.get('signal_frequency', {})
    print(f"  - 개별 신호 빈도:")
    for condition, name in conditions.items():
        count = freq.get(condition.replace('_signal', '').upper(), 0)
        print(f"    * {name}: {count}회")

    print(f"\n[완료] 테스트 완료!")

    # 실제 데이터프레임의 신호 확인 (상세)
    print(f"\n[상세] 상세 분석 (최근 10일):")
    signals_df = analyzer.check_buy_signals(sample_data.copy())

    # 최근 10일 데이터 표시
    recent_df = signals_df.tail(10)

    print(f"{'날짜':<12} {'종가':<8} {'RSI':<4} {'VOL':<4} {'MACD':<5} {'캔들':<4} {'골든':<4} {'총점':<4} {'신호':<4}")
    print("-" * 60)

    for idx, row in recent_df.iterrows():
        date_str = idx.strftime('%m-%d') if hasattr(idx, 'strftime') else str(idx)[-5:]
        rsi_val = 'O' if row.get('RSI_signal', False) else 'X'
        vol_val = 'O' if row.get('VOL_signal', False) else 'X'
        macd_val = 'O' if row.get('MACD_signal', False) else 'X'
        candle_val = 'O' if row.get('CANDLE_signal', False) else 'X'
        golden_val = 'O' if row.get('GOLDEN_signal', False) else 'X'
        signal_count = row.get('signal_count', 0)
        buy_signal = 'BUY' if row.get('BUY_signal', False) else '---'

        print(f"{date_str:<12} {row['Close']:>7.0f} {rsi_val:>4} {vol_val:>4} {macd_val:>5} {candle_val:>4} {golden_val:>4} {signal_count:>4} {buy_signal:>4}")

    print(f"\n[안내] O: 조건 충족, X: 조건 미충족")
    print(f"[안내] BUY: 매수 신호 (2개 이상 조건 충족), ---: 신호 없음")

if __name__ == "__main__":
    test_trading_signals()