#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import os
from pathlib import Path

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def check_real_monitoring_data():
    """실제 모니터링 데이터 확인"""
    try:
        print("=" * 80)
        print("                      실제 모니터링 데이터 확인")
        print("=" * 80)

        from config import Config
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus
        from analyzers.technical_analyzer import TechnicalAnalyzer
        from data_collectors.kis_collector import KISCollector
        import pandas as pd

        # 초기화
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        await kis_collector.initialize()

        technical_analyzer = TechnicalAnalyzer(config)

        # 실제 모니터링 데이터 조회
        with db_manager.get_session() as session:
            # 활성 모니터링 종목들
            active_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                MonitoringStock.buy_price.is_(None)  # 아직 매수되지 않은 종목들
            ).limit(10).all()

            print(f"분석 대상 종목: {len(active_stocks)}개")
            print()

            if not active_stocks:
                print("활성 모니터링 종목이 없습니다.")
                return False

            # 각 종목별 점수 계산
            stock_scores = []

            for i, stock in enumerate(active_stocks, 1):
                print(f"{i}. {stock.symbol} ({stock.name}) 분석 중...")

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

                    # 점수 정보
                    signal_strength = analysis_result['technical_score']

                    # RSI 상태 확인
                    current_rsi = indicators.get('rsi', 50)

                    # 신호 텍스트 생성 (show_sorted_stocks와 동일한 함수 사용)
                    def _generate_signal_text(indicators: dict) -> str:
                        """지표를 바탕으로 신호 텍스트 생성"""
                        ma_signal = indicators.get('ma_signal', 'HOLD')
                        macd_trend = indicators.get('macd_trend', 'NEUTRAL')
                        supertrend_signal = indicators.get('supertrend_signal', 'HOLD')

                        if ma_signal == 'BUY' and macd_trend == 'BULLISH':
                            return "골든크로스"
                        elif ma_signal == 'SELL' and macd_trend == 'BEARISH':
                            return "데드크로스"
                        elif supertrend_signal == 'BUY':
                            return "상승돌파"
                        elif supertrend_signal == 'SELL':
                            return "하락돌파"
                        elif macd_trend == 'BULLISH':
                            return "상승신호"
                        elif macd_trend == 'BEARISH':
                            return "하락신호"
                        else:
                            return "중립"

                    def _generate_volume_text(indicators: dict) -> str:
                        """거래량 지표를 바탕으로 텍스트 생성"""
                        volume_signal = indicators.get('volume_signal', 'NORMAL')

                        if volume_signal == 'VERY_HIGH':
                            return "급등량"
                        elif volume_signal == 'HIGH':
                            return "고량"
                        elif volume_signal == 'ABOVE_AVERAGE':
                            return "평균상"
                        elif volume_signal == 'NORMAL':
                            return "평균"
                        else:
                            return "저조량"

                    def _generate_momentum_text(indicators: dict) -> str:
                        """모멘텀 지표를 바탕으로 텍스트 생성"""
                        supertrend_trend = indicators.get('supertrend_trend', 'NEUTRAL')
                        macd_trend = indicators.get('macd_trend', 'NEUTRAL')

                        if supertrend_trend == 'BULLISH' and macd_trend == 'BULLISH':
                            return "강세"
                        elif supertrend_trend == 'BULLISH' or macd_trend == 'BULLISH':
                            return "상승"
                        elif supertrend_trend == 'BEARISH' and macd_trend == 'BEARISH':
                            return "약세"
                        elif supertrend_trend == 'BEARISH' or macd_trend == 'BEARISH':
                            return "하락"
                        else:
                            return "중립"

                    # 신호 텍스트 생성
                    signal_type = _generate_signal_text(indicators)
                    volume_status = _generate_volume_text(indicators)
                    momentum_status = _generate_momentum_text(indicators)

                    # 등급 계산 (70점 이상 A, 50-69 B, 50 미만 C)
                    if signal_strength >= 70:
                        grade = "A"
                    elif signal_strength >= 50:
                        grade = "B"
                    else:
                        grade = "C"

                    stock_scores.append({
                        'symbol': stock.symbol,
                        'name': stock.name,
                        'rsi': round(current_rsi, 1),
                        'signal': signal_type,
                        'volume': volume_status,
                        'momentum': momentum_status,
                        'score': int(signal_strength),
                        'grade': grade,
                        'strategy': stock.strategy_name
                    })

                    print(f"   점수: {signal_strength}점, 등급: {grade}")

                except Exception as e:
                    print(f"   분석 실패: {e}")
                    continue

            # 점수 순으로 정렬 (높은 점수부터)
            sorted_stocks = sorted(stock_scores, key=lambda x: x['score'], reverse=True)

            print()
            print("=" * 80)
            print("실제 종목 현황 (점수 순 정렬)")
            print("=" * 80)
            print("종목      RSI   신호        거래량    모멘텀   점수   등급    전략")
            print("-" * 80)

            for stock in sorted_stocks:
                buy_signal = " <<<매수 추천!!!" if stock['grade'] == 'A' else ""
                grade_display = f"[{stock['grade']}]"

                print(f"{stock['symbol']:<8} {stock['rsi']:<5.1f} {stock['signal']:<10} {stock['volume']:<8} "
                     f"{stock['momentum']:<6} {stock['score']:<3}점  {grade_display:<3} {stock['strategy']:<15}{buy_signal}")

            print()
            print("=" * 80)

            # A등급 종목들 (70점 이상)
            a_grade_stocks = [s for s in sorted_stocks if s['grade'] == 'A']
            if a_grade_stocks:
                print(">> 70점 이상 A등급 매수 추천 종목:")
                for stock in a_grade_stocks:
                    print(f"   -> {stock['symbol']} ({stock['name']}) - {stock['score']}점")
            else:
                print(">> 현재 70점 이상 A등급 종목 없음")

            print()
            print(">> 등급 기준:")
            print("   A등급 (70점 이상): 강력 매수 추천")
            print("   B등급 (50-69점): 매수 검토")
            print("   C등급 (50점 미만): 관망")

        return True

    except Exception as e:
        print(f"실제 데이터 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_real_monitoring_data())
    if success:
        print("\n>> 실제 모니터링 데이터 확인 완료!")
    else:
        print("\n>> 실제 모니터링 데이터 확인 실패!")