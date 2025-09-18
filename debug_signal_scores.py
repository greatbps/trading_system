#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import os
from pathlib import Path
import pandas as pd

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def debug_signal_scores():
    """매수 시그널 점수 디버깅"""
    try:
        print("매수 시그널 점수 디버깅")
        print("=" * 50)

        from config import Config
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus
        from data_collectors.kis_collector import KISCollector
        from data_collectors.chart_data_collector import ChartDataCollector
        from analyzers.trading_signals import TradingSignalAnalyzer

        # 초기화
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        await kis_collector.initialize()

        # 모니터링 종목 조회
        with db_manager.get_session() as session:
            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                MonitoringStock.buy_price.is_(None)
            ).limit(5).all()  # 최대 5개만 테스트

            print(f"분석 대상: {len(monitoring_stocks)}개 종목")

            chart_collector = ChartDataCollector(kis_collector)
            signal_analyzer = TradingSignalAnalyzer()

            for i, stock in enumerate(monitoring_stocks, 1):
                print(f"\n{i}. {stock.symbol}({stock.name}) 분석 중...")

                try:
                    # 차트 데이터 수집 (일봉 60일)
                    chart_data_list = await chart_collector.get_daily_chart_data(stock.symbol, days=60)

                    # DataFrame으로 변환
                    if chart_data_list:
                        chart_data = pd.DataFrame([{
                            'Date': item.timestamp,
                            'Open': item.open,
                            'High': item.high,
                            'Low': item.low,
                            'Close': item.close,
                            'Volume': item.volume
                        } for item in chart_data_list])
                        chart_data.set_index('Date', inplace=True)
                    else:
                        chart_data = None

                    if chart_data is None or chart_data.empty or len(chart_data) < 20:
                        print(f"   차트 데이터 부족: {len(chart_data) if chart_data is not None else 0}개")
                        continue

                    # 매수 신호 확인
                    signals_df = signal_analyzer.check_buy_signals(chart_data.copy())
                    latest_signals = signal_analyzer.get_latest_signals(signals_df)

                    # 결과 표시
                    signal_strength = latest_signals.get('signal_strength', 0)
                    signal_count = latest_signals.get('signal_count', 0)
                    signals = latest_signals.get('signals', {})

                    print(f"   신호 강도: {signal_strength}%")
                    print(f"   신호 개수: {signal_count}/5")
                    print(f"   RSI 신호: {signals.get('RSI_signal', False)}")
                    print(f"   볼륨 신호: {signals.get('VOL_signal', False)}")
                    print(f"   MACD 신호: {signals.get('MACD_signal', False)}")
                    print(f"   캔들 신호: {signals.get('CANDLE_signal', False)}")
                    print(f"   골든크로스: {signals.get('GOLDEN_signal', False)}")

                    if signal_strength >= 60 or signal_count >= 3:
                        print(f"   -> 매수 조건 충족! ✅")
                    else:
                        print(f"   -> 매수 조건 미충족 (강도 60% 이상 또는 3개 이상 필요)")

                except Exception as e:
                    print(f"   분석 실패: {e}")
                    continue

        return True

    except Exception as e:
        print(f"디버깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_signal_scores())
    if success:
        print("\n시그널 점수 디버깅 완료!")
    else:
        print("\n시그널 점수 디버깅 실패!")