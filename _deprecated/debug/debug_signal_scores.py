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
        from analyzers.technical_analyzer import TechnicalAnalyzer

        # 초기화
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        await kis_collector.initialize()

        technical_analyzer = TechnicalAnalyzer(config)

        # A등급 종목들 우선 분석
        a_grade_symbols = ['025890', '071050', '130740', '097800', '069140']

        with db_manager.get_session() as session:
            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                MonitoringStock.symbol.in_(a_grade_symbols)
            ).all()  # A등급 종목 전체

            print(f"A등급 종목 분석 대상: {len(monitoring_stocks)}개")

            for i, stock in enumerate(monitoring_stocks, 1):
                print(f"\n{i}. {stock.symbol}({stock.name}) 분석 중...")

                try:
                    # 1. 종목 정보 조회
                    stock_info = await kis_collector.get_stock_info(stock.symbol)
                    if not stock_info:
                        print(f"   {stock.symbol} 정보 조회 실패")
                        continue

                    # 2. 일봉 데이터 조회 (최근 50일)
                    daily_data = await kis_collector.get_ohlcv_data(stock.symbol, period="D", count=50)
                    if not daily_data or len(daily_data) < 15:
                        print(f"   {stock.symbol} 일봉 데이터 부족 ({len(daily_data) if daily_data else 0}개)")
                        continue

                    # OHLCV 데이터를 기술적 분석기가 이해할 수 있는 형태로 변환
                    formatted_data = []
                    for ohlcv in daily_data:
                        formatted_data.append({
                            'date': ohlcv.date,
                            'open': float(ohlcv.open_price),
                            'high': float(ohlcv.high_price),
                            'low': float(ohlcv.low_price),
                            'close': float(ohlcv.close_price),
                            'volume': int(ohlcv.volume)
                        })

                    # 3. 기술적 분석 수행 (formatted_data 사용)
                    analysis_result = await technical_analyzer.analyze_stock(stock.symbol, formatted_data)
                    indicators = analysis_result['indicators']

                    # 결과 표시
                    signal_strength = analysis_result['technical_score']
                    current_price = stock_info.current_price

                    print(f"   현재가: {current_price:,}원")
                    print(f"   기술적 점수: {signal_strength:.1f}점")
                    print(f"   RSI: {indicators.get('rsi', 50):.1f}")
                    print(f"   MACD 추세: {indicators.get('macd_trend', 'NEUTRAL')}")
                    print(f"   이동평균 신호: {indicators.get('ma_signal', 'HOLD')}")
                    print(f"   슈퍼트렌드: {indicators.get('supertrend_signal', 'HOLD')}")
                    print(f"   거래량 신호: {indicators.get('volume_signal', 'NORMAL')}")

                    if signal_strength >= 70:
                        print(f"   -> A등급 (70점 이상) 매수 추천!")
                    elif signal_strength >= 50:
                        print(f"   -> B등급 (50-69점) 매수 검토")
                    else:
                        print(f"   -> C등급 (50점 미만) 관망")

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