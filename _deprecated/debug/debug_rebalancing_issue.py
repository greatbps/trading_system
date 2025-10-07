#!/usr/bin/env python3
"""
자동 리밸런싱 차단 원인 분석 스크립트
- 8월 27일 이후 리밸런싱이 중단된 이유 조사
"""

import asyncio
import sys
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

async def debug_rebalancing_issue():
    """자동 리밸런싱 차단 원인 분석"""
    print("=== 자동 리밸런싱 차단 원인 분석 ===")
    print(f"분석 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        from config import Config
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus, MonitoringType
        from data_collectors.kis_collector import KISCollector
        
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        print("[OK] 시스템 초기화 완료")
        
        # 1. 현재 모니터링 종목 현황
        print(f"\n[1] 현재 모니터링 종목 현황:")
        
        with db_manager.get_session() as session:
            active_monitoring_data = session.query(
                MonitoringStock.symbol,
                MonitoringStock.name,
                MonitoringStock.monitoring_type,
                MonitoringStock.strategy_name,
                MonitoringStock.recommendation_time
            ).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).all()
            
            trading_count = len([s for s in active_monitoring_data if s.monitoring_type == MonitoringType.TRADING])
            portfolio_count = len([s for s in active_monitoring_data if s.monitoring_type == MonitoringType.PORTFOLIO])
            
            print(f"  전체 활성 모니터링: {len(active_monitoring_data)}개")
            print(f"  - TRADING 타입: {trading_count}개")
            print(f"  - PORTFOLIO 타입: {portfolio_count}개")
            
            print(f"\n  활성 모니터링 종목 목록:")
            for stock in active_monitoring_data[:10]:  # 상위 10개만
                print(f"    {stock.symbol}({stock.name}) - {stock.monitoring_type.name} - {stock.strategy_name}")
            if len(active_monitoring_data) > 10:
                print(f"    ... 및 {len(active_monitoring_data)-10}개 더")
        
        # 2. 실제 보유종목 현황
        print(f"\n[2] 실제 보유종목 현황:")
        
        async with kis_collector:
            try:
                holdings_dict = await kis_collector.get_holdings()
                if holdings_dict:
                    portfolio_holdings = list(holdings_dict.values())
                    actual_holding_symbols = set([h.get('symbol') for h in portfolio_holdings if h.get('symbol')])
                    print(f"  실제 보유종목: {len(actual_holding_symbols)}개")
                    
                    holding_list = list(actual_holding_symbols)[:10]
                    print(f"  보유종목 목록: {holding_list}")
                    if len(actual_holding_symbols) > 10:
                        print(f"    ... 및 {len(actual_holding_symbols)-10}개 더")
                else:
                    actual_holding_symbols = set()
                    print(f"  [ERROR] 실제 보유종목 조회 실패")
                    
            except Exception as e:
                print(f"  [ERROR] KIS API 조회 오류: {e}")
                actual_holding_symbols = set()
        
        # 3. 모니터링과 실제 보유의 교집합 분석
        print(f"\n[3] 모니터링 vs 실제 보유 교집합 분석:")
        
        if active_monitoring_data:
            monitoring_symbols = set([stock.symbol for stock in active_monitoring_data])
            intersection = monitoring_symbols.intersection(actual_holding_symbols)
            only_monitoring = monitoring_symbols - actual_holding_symbols
            only_holding = actual_holding_symbols - monitoring_symbols
            
            print(f"  모니터링 중인 종목: {len(monitoring_symbols)}개")
            print(f"  실제 보유종목: {len(actual_holding_symbols)}개")
            print(f"  교집합 (둘 다): {len(intersection)}개 - {list(intersection)[:5]}{'...' if len(intersection) > 5 else ''}")
            print(f"  모니터링만: {len(only_monitoring)}개 - {list(only_monitoring)[:5]}{'...' if len(only_monitoring) > 5 else ''}")
            print(f"  실제보유만: {len(only_holding)}개 - {list(only_holding)[:5]}{'...' if len(only_holding) > 5 else ''}")
            
            # 4. 필터링 효과 분석
            print(f"\n[4] DatabaseAutoTrader 필터링 효과 분석:")
            
            trading_stocks = [s for s in active_monitoring_data if s.monitoring_type == MonitoringType.TRADING]
            trading_symbols = set([s.symbol for s in trading_stocks])
            
            # 현재 필터링 로직 시뮬레이션
            filtered_trading = [s for s in trading_stocks if s.symbol in actual_holding_symbols]
            
            print(f"  TRADING 타입 모니터링: {len(trading_stocks)}개")
            print(f"  실제 보유 필터링 후: {len(filtered_trading)}개")
            print(f"  필터링으로 제외된 종목: {len(trading_stocks) - len(filtered_trading)}개")
            
            if len(filtered_trading) == 0:
                print(f"  [CRITICAL] 필터링 후 분석 대상이 0개 → 리밸런싱 불가!")
                print(f"  [원인] TRADING 타입 모니터링 종목 중 실제 보유종목이 없음")
                
            # 제외된 종목들 상세 분석
            excluded_stocks = [s for s in trading_stocks if s.symbol not in actual_holding_symbols]
            if excluded_stocks:
                print(f"\n  [제외된 종목 상세]:")
                for stock in excluded_stocks[:5]:
                    print(f"    {stock.symbol}({stock.name}) - {stock.strategy_name} - 등록일: {stock.recommendation_time.strftime('%m-%d %H:%M')}")
        
        # 5. 8월 27일 이후 모니터링 추가 이력
        print(f"\n[5] 8월 27일 이후 모니터링 추가 이력:")
        
        cutoff_date = datetime(2024, 8, 27)
        
        with db_manager.get_session() as session:
            recent_additions = session.query(
                MonitoringStock.symbol,
                MonitoringStock.name,
                MonitoringStock.monitoring_type,
                MonitoringStock.recommendation_time
            ).filter(
                MonitoringStock.recommendation_time >= cutoff_date
            ).order_by(MonitoringStock.recommendation_time.desc()).all()
            
            print(f"  8월 27일 이후 추가된 모니터링: {len(recent_additions)}개")
            
            if recent_additions:
                print(f"  최근 추가 이력:")
                for stock in recent_additions[:10]:
                    print(f"    {stock.recommendation_time.strftime('%m-%d %H:%M')} - {stock.symbol}({stock.name}) - {stock.monitoring_type.name}")
            else:
                print(f"  [INFO] 8월 27일 이후 새로운 모니터링 추가 없음")
        
        # 6. 결론 및 해결책
        print(f"\n[6] 결론 및 해결책:")
        
        if len(actual_holding_symbols) == 0:
            print(f"  [결론] 실제 보유종목이 0개 → KIS API 연결 문제")
            print(f"  [해결책] KIS API 설정 및 연결 상태 확인 필요")
            
        elif len([s for s in active_monitoring_data if s.monitoring_type == MonitoringType.TRADING and s.symbol in actual_holding_symbols]) == 0:
            print(f"  [결론] TRADING 타입 모니터링 중 실제 보유종목 없음")
            print(f"  [원인] 모니터링 종목들이 실제로 매수되지 않았거나 이미 매도됨")
            print(f"  [해결책1] 필터링 로직 수정 - TRADING 타입은 실제 보유 여부와 무관하게 분석")
            print(f"  [해결책2] 모니터링 종목을 실제로 매수하여 보유종목으로 만들기")
            
        else:
            print(f"  [결론] 필터링 로직은 정상 작동 중")
            print(f"  [참고] 다른 원인 조사 필요")
            
        return True
    
    except Exception as e:
        print(f"[ERROR] 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_rebalancing_issue())
    if success:
        print(f"\n[RESULT] 분석 완료")
    else:
        print(f"\n[RESULT] 분석 실패")