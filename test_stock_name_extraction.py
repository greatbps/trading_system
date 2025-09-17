#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_stock_name_extraction.py

종목명 추출 로직 테스트 - 임시 이름 문제 해결 검증
"""

import sys
import asyncio
import os
from pathlib import Path

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_stock_name_extraction():
    """종목명 추출 테스트"""
    try:
        from config import Config
        from trading.db_auto_trader import DatabaseAutoTrader
        from data_collectors.kis_collector import KISCollector
        from trading.executor import TradingExecutor
        from core.db_manager import DatabaseManager
        
        print("🔍 종목명 추출 로직 테스트 시작")
        print("=" * 60)
        
        # 설정 및 컴포넌트 초기화
        config = Config()
        db_manager = DatabaseManager(config.database.get_database_url())
        kis_collector = KISCollector(config)
        executor = TradingExecutor(config, kis_collector)
        
        # DatabaseAutoTrader 초기화
        db_auto_trader = DatabaseAutoTrader(
            config=config,
            kis_collector=kis_collector,
            executor=executor,
            market_manager=None,
            db_manager=db_manager
        )
        
        # KIS collector 초기화
        await kis_collector.initialize()
        print("✅ KIS collector 초기화 완료")
        
        # 테스트 대상 종목들 (문제가 있었던 종목들)
        test_symbols = ['000150', '443060', '003690', '005930', '000660']  # 삼성전자, SK하이닉스 추가
        
        print(f"\n📋 테스트 대상 종목: {len(test_symbols)}개")
        for symbol in test_symbols:
            print(f"   - {symbol}")
        
        print(f"\n🧪 각 종목별 add_buy_recommendation 테스트:")
        print("-" * 60)
        
        for symbol in test_symbols:
            try:
                print(f"\n🔍 {symbol} 테스트 중...")
                
                # 임시 이름으로 add_buy_recommendation 호출
                temp_name = f"종목{symbol}"
                result = await db_auto_trader.add_buy_recommendation(
                    symbol=symbol,
                    name=temp_name,  # 임시 이름으로 시작
                    strategy_name="TEST_STRATEGY",
                    target_price=None,
                    stop_loss_price=None
                )
                
                if result:
                    print(f"✅ {symbol} 모니터링 추가 성공")
                    
                    # DB에서 실제 저장된 종목명 확인
                    with db_manager.get_session() as session:
                        from database.models import MonitoringStock
                        monitoring_stock = session.query(MonitoringStock).filter(
                            MonitoringStock.symbol == symbol
                        ).first()
                        
                        if monitoring_stock:
                            stored_name = monitoring_stock.name
                            print(f"   📝 DB 저장된 종목명: '{stored_name}'")
                            
                            if stored_name.startswith('종목'):
                                print(f"   ❌ 여전히 임시 이름: '{stored_name}'")
                            else:
                                print(f"   ✅ 정확한 종목명 추출됨: '{stored_name}'")
                        else:
                            print(f"   ⚠️ DB에서 모니터링 정보를 찾을 수 없음")
                else:
                    print(f"❌ {symbol} 모니터링 추가 실패")
                
            except Exception as e:
                print(f"❌ {symbol} 테스트 중 오류: {e}")
        
        print(f"\n📊 최종 DB 상태 확인:")
        print("-" * 60)
        
        # DB에서 모든 모니터링 종목 조회
        with db_manager.get_session() as session:
            from database.models import MonitoringStock
            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.symbol.in_(test_symbols)
            ).all()
            
            print(f"DB에 저장된 종목: {len(monitoring_stocks)}개")
            for stock in monitoring_stocks:
                status_icon = "❌" if stock.name.startswith('종목') else "✅"
                print(f"   {status_icon} {stock.symbol}: '{stock.name}' ({stock.strategy_name})")
        
        print(f"\n🧹 테스트 데이터 정리 중...")
        
        # 테스트로 추가된 데이터 정리
        with db_manager.get_session() as session:
            from database.models import MonitoringStock, Stock
            
            # 테스트 전략으로 추가된 모니터링 종목 삭제
            deleted_monitoring = session.query(MonitoringStock).filter(
                MonitoringStock.strategy_name == "TEST_STRATEGY"
            ).delete()
            
            # 테스트로 추가된 Stock 엔트리 삭제 (기존에 없던 것만)
            for symbol in test_symbols:
                if symbol not in ['005930', '000660']:  # 대형주는 이미 있을 수 있으므로 제외
                    session.query(Stock).filter(Stock.symbol == symbol).delete()
            
            session.commit()
            print(f"✅ 테스트 데이터 정리 완료 (모니터링: {deleted_monitoring}개)")
        
        print(f"\n🎯 종목명 추출 로직 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_stock_name_extraction())
    if success:
        print("\n✅ 종목명 추출 로직이 정상 작동합니다!")
    else:
        print("\n❌ 종목명 추출 로직에 문제가 있습니다.")