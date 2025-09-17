#!/usr/bin/env python3
"""
매수 신호 생성 상태 진단 스크립트
- 왜 모니터링 종목들이 매수되지 않았는지 분석
"""

import asyncio
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

async def debug_buy_signals():
    """매수 신호 생성 상태 진단"""
    print("=== 매수 신호 생성 상태 진단 ===")
    print(f"진단 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        from config import Config
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus, MonitoringType
        from data_collectors.kis_collector import KISCollector
        from analyzers.technical_indicators import RealTechnicalIndicators
        
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        tech_indicators = RealTechnicalIndicators()
        
        print("[OK] 시스템 초기화 완료")
        
        # 1. 모니터링 종목 중 일부 샘플링 (5개)
        print(f"\n[1] 모니터링 종목 샘플 분석:")
        
        with db_manager.get_session() as session:
            sample_stocks = session.query(
                MonitoringStock.symbol,
                MonitoringStock.name,
                MonitoringStock.strategy_name
            ).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE,
                MonitoringStock.monitoring_type == MonitoringType.TRADING
            ).limit(5).all()
        
        if not sample_stocks:
            print("  [ERROR] 분석할 모니터링 종목이 없습니다")
            return False
        
        print(f"  샘플 종목: {len(sample_stocks)}개")
        for stock in sample_stocks:
            print(f"    {stock.symbol}({stock.name}) - {stock.strategy_name}")
        
        # 2. 각 종목별 매수 조건 분석
        async with kis_collector:
            print(f"\n[2] 매수 조건 분석:")
            
            for i, stock in enumerate(sample_stocks, 1):
                symbol = stock.symbol
                name = stock.name
                
                print(f"\n  == {i}. {symbol}({name}) ==")
                
                try:
                    # 현재가 조회
                    current_price = await kis_collector.get_current_price(symbol)
                    if not current_price:
                        print(f"    [SKIP] 현재가 조회 실패")
                        continue
                    
                    print(f"    현재가: {current_price:,}원")
                    
                    # 차트 데이터 조회 (간단한 더미 데이터로 대체)
                    from analyzers.technical_indicators import PriceData
                    
                    # 실제로는 kis_collector에서 차트 데이터를 가져와야 하지만, 
                    # 간단한 테스트를 위해 현재가 기준으로 더미 데이터 생성
                    dummy_chart_data = []
                    for i in range(20):  # 20일치 데이터
                        price_variation = current_price * (0.95 + i * 0.005)  # 약간의 변동
                        dummy_chart_data.append(PriceData(
                            timestamp=datetime.now(),
                            open=int(price_variation * 0.99),
                            high=int(price_variation * 1.02),
                            low=int(price_variation * 0.98),
                            close=int(price_variation),
                            volume=1000000
                        ))
                    
                    # 기술적 분석 수행
                    technical_data = await asyncio.to_thread(
                        tech_indicators.calculate_all_indicators, symbol, dummy_chart_data
                    )
                    if not technical_data:
                        print(f"    [SKIP] 기술적 분석 실패")
                        continue
                    
                    # 매수 조건 시뮬레이션
                    signals = technical_data.get('signals', {})
                    composite_signal = signals.get('composite_signal', 'hold')
                    composite_confidence = signals.get('composite_confidence', 0.0)
                    
                    rsi = technical_data.get('rsi', 50)
                    ema_5 = technical_data.get('ema_5', current_price)
                    ema_20 = technical_data.get('ema_20', current_price)
                    volume = technical_data.get('volume', 0)
                    volume_avg = technical_data.get('volume_avg', 0)
                    
                    # MACD 분석
                    macd_composite_signal = signals.get('macd_signal', 'hold')
                    macd_histogram_val = technical_data.get('macd_histogram', 0)
                    
                    # 매수 조건 체크
                    buy_conditions = []
                    
                    # 1. 종합 신호
                    if composite_signal == 'buy' and composite_confidence >= 0.6:
                        buy_conditions.append("종합신호_매수")
                    
                    # 2. 골든크로스
                    if ema_5 > ema_20 * 1.01:
                        buy_conditions.append("골든크로스")
                    
                    # 3. RSI 과매도 반등
                    if 25 <= rsi <= 35:
                        buy_conditions.append("RSI_과매도반등")
                    
                    # 4. 거래량 급증
                    if volume_avg > 0 and volume > volume_avg * 1.5:
                        buy_conditions.append("거래량_급증")
                    
                    # 5. MACD 골든크로스
                    if macd_composite_signal == 'buy' and macd_histogram_val > 0:
                        buy_conditions.append("MACD_골든크로스")
                    
                    # 결과 출력
                    print(f"    매수조건 개수: {len(buy_conditions)}개 (필요: 2개 이상)")
                    print(f"    충족된 조건: {buy_conditions}")
                    
                    # 상세 지표 출력
                    print(f"    기술적 지표:")
                    print(f"      - 종합신호: {composite_signal} ({composite_confidence:.2f})")
                    print(f"      - RSI: {rsi:.1f}")
                    print(f"      - EMA5/EMA20: {ema_5:,} / {ema_20:,}")
                    print(f"      - 거래량: {volume:,} (평균: {volume_avg:,})")
                    print(f"      - MACD신호: {macd_composite_signal} (히스토그램: {macd_histogram_val:.4f})")
                    
                    if len(buy_conditions) >= 2:
                        confidence = min(0.9, len(buy_conditions) * 0.3 + composite_confidence)
                        print(f"    [결과] BUY 신호 생성 가능! (신뢰도: {confidence:.2f})")
                    else:
                        print(f"    [결과] BUY 신호 생성 불가 (조건 부족)")
                        print(f"    [개선방안] 조건 완화 또는 다른 전략 고려 필요")
                    
                except Exception as e:
                    print(f"    [ERROR] {symbol} 분석 실패: {e}")
        
        # 3. 매수 조건 완화 제안
        print(f"\n[3] 매수 조건 완화 제안:")
        print(f"  현재 조건: 2개 이상 매수조건 충족")
        print(f"  제안1: 1개 조건 + 높은 신뢰도 (0.7 이상)")
        print(f"  제안2: 전략별 맞춤 조건 (MOMENTUM, VWAP 등)")
        print(f"  제안3: 수동 매수 후 자동 매도 방식")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] 진단 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_buy_signals())
    if success:
        print(f"\n[RESULT] 매수 신호 진단 완료")
    else:
        print(f"\n[RESULT] 진단 실패")