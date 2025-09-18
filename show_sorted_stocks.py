#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import os
from pathlib import Path
from datetime import datetime

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def show_sorted_stocks(auto_add_a_grade=True):
    """점수 순으로 정렬된 종목 현황 표시"""
    try:
        print("=" * 80)
        print("                           종목 현황 (점수 순)")
        print("=" * 80)
        print()

        from config import Config
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus, MonitoringType

        # 데이터베이스 연결
        config = Config()
        db_manager = DatabaseManager(config)

        with db_manager.get_session() as session:
            # 활성 모니터링 종목 조회 (점수가 있는 것만)
            stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value
            ).all()

            # 실제 DB에서 활성 모니터링 종목 조회
            print(">> DB에서 모니터링 종목 조회 중...")
            active_stocks = [stock for stock in stocks if hasattr(stock, 'symbol')]


            print(f">> 총 {len(active_stocks)}개 종목 발견")

            # API 데이터 수집 및 기술적 분석
            from data_collectors.kis_collector import KISCollector
            from analyzers.technical_analyzer import TechnicalAnalyzer

            kis_collector = KISCollector(config)
            await kis_collector.initialize()

            technical_analyzer = TechnicalAnalyzer(config)

            stock_data = []
            for i, stock in enumerate(active_stocks):
                try:
                    symbol = stock.symbol if hasattr(stock, 'symbol') else stock["symbol"]
                    print(f">> [{i+1}/{len(active_stocks)}] {symbol} 분석 중...")

                    # 1. 종목 정보 조회
                    stock_info = await kis_collector.get_stock_info(symbol)
                    if not stock_info:
                        print(f">> {symbol} 정보 조회 실패")
                        continue

                    # 2. 일봉 데이터 조회 (최근 50일)
                    daily_data = await kis_collector.get_ohlcv_data(symbol, period="D", count=50)
                    if not daily_data or len(daily_data) < 15:
                        print(f">> {symbol} 일봉 데이터 부족 ({len(daily_data) if daily_data else 0}개)")
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
                    analysis_result = await technical_analyzer.analyze_stock(symbol, formatted_data)
                    indicators = analysis_result['indicators']

                    # 4. 신호 및 등급 계산
                    score = analysis_result['technical_score']
                    if score >= 70:
                        grade = "A"
                    elif score >= 50:
                        grade = "B"
                    else:
                        grade = "C"

                    # 5. 신호 텍스트 생성
                    signal_text = _generate_signal_text(indicators)
                    volume_text = _generate_volume_text(indicators)
                    momentum_text = _generate_momentum_text(indicators)

                    stock_data.append({
                        "symbol": symbol,
                        "name": stock_info.name if hasattr(stock_info, 'name') else f"종목{symbol}",
                        "rsi": round(indicators.get('rsi', 50), 1),
                        "signal": signal_text,
                        "volume": volume_text,
                        "momentum": momentum_text,
                        "score": round(score, 0),
                        "grade": grade,
                        "current_price": stock_info.current_price if hasattr(stock_info, 'current_price') else 0
                    })

                    print(f">> {symbol} 분석 완료 - 점수: {score:.0f}점 ({grade}등급)")

                except Exception as e:
                    print(f">> {symbol} 분석 실패: {e}")
                    continue

            if not stock_data:
                print(">> 분석 가능한 종목이 없습니다.")
                return False

            print(f">> 총 {len(stock_data)}개 종목 분석 완료")

            # 점수 순으로 정렬 (높은 점수부터)
            sorted_stocks = sorted(stock_data, key=lambda x: x['score'], reverse=True)

            print("종목      RSI   신호        거래량    모멘텀   점수   등급")
            print("-" * 70)

            for stock in sorted_stocks:
                # A 등급은 매수 신호로 표시
                buy_signal = "<<<매수!!!" if stock['grade'] == 'A' else ""

                # 등급별 표시
                if stock['grade'] == 'A':
                    grade_display = f"[{stock['grade']}]"
                elif stock['grade'] == 'B':
                    grade_display = f"[{stock['grade']}]"
                else:
                    grade_display = f"[{stock['grade']}]"

                print(f"{stock['symbol']:<8} {stock['rsi']:<5.1f} {stock['signal']:<10} {stock['volume']:<8} {stock['momentum']:<6} {stock['score']:<3}점  {grade_display}  {buy_signal}")

            print()
            print("=" * 70)
            print(">> A 등급 종목 매수 추천:")

            a_grade_stocks = [s for s in sorted_stocks if s['grade'] == 'A']
            for stock in a_grade_stocks:
                print(f"   -> {stock['symbol']} ({stock['name']}) - {stock['score']}점")

            # A등급 종목 자동 모니터링 추가
            if auto_add_a_grade and a_grade_stocks:
                print()
                print("=" * 70)
                print(">> A등급 종목 자동 모니터링 추가:")

                for stock in a_grade_stocks:
                    try:
                        # 이미 모니터링 중인지 확인
                        existing = session.query(MonitoringStock).filter(
                            MonitoringStock.symbol == stock['symbol'],
                            MonitoringStock.status.in_([MonitoringStatus.ACTIVE.value, MonitoringStatus.PAUSED.value])
                        ).first()

                        if existing:
                            print(f"   - {stock['symbol']} ({stock['name']}): 이미 모니터링 중")
                            continue

                        # 새 모니터링 종목 추가
                        new_monitoring = MonitoringStock(
                            symbol=stock['symbol'],
                            name=stock['name'],
                            status=MonitoringStatus.ACTIVE.value,
                            strategy_name="high_score_auto",
                            monitoring_type=MonitoringType.TRADING,
                            recommendation_time=datetime.now()
                        )
                        session.add(new_monitoring)
                        session.commit()

                        print(f"   + {stock['symbol']} ({stock['name']}): 모니터링 추가 완료 ({stock['score']}점)")

                    except Exception as e:
                        print(f"   ! {stock['symbol']} ({stock['name']}): 추가 실패 - {e}")

            print()
            print(">> 등급 기준:")
            print("   A등급 (70점 이상): 강력 매수 추천")
            print("   B등급 (50-69점): 매수 검토")
            print("   C등급 (50점 미만): 관망")

        return True

    except Exception as e:
        print(f"종목 현황 표시 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

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

if __name__ == "__main__":
    success = asyncio.run(show_sorted_stocks())
    if success:
        print("\n>> 종목 현황 표시 완료!")
    else:
        print("\n>> 종목 현황 표시 실패!")