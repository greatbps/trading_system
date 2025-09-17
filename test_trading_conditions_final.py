#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_trading_conditions_final():
    """매매조건 감시 최종 테스트"""
    try:
        print("=== 매매조건 감시 최종 테스트 ===")
        print(f"테스트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        print("Trading System 초기화 중...")
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return False
        
        print("Trading System 초기화 완료")
        
        # DB Auto Trader 확인
        db_auto_trader = trading_system.db_auto_trader
        if not db_auto_trader:
            print("DB Auto Trader가 없습니다")
            return False
        
        print(f"DB Auto Trader: {type(db_auto_trader).__name__}")
        print(f"market_manager: {type(db_auto_trader.market_manager).__name__}")
        
        # 시장 시간 체크를 우회하기 위해 임시로 메서드 교체
        original_method = db_auto_trader.market_manager.is_monitoring_allowed_now
        
        def always_allow():
            return True
            
        db_auto_trader.market_manager.is_monitoring_allowed_now = always_allow
        print("시장 시간 체크 우회 설정 완료 (점심시간 무시)")
        
        # 실제 모니터링 사이클 실행
        print("매매조건 감시 실행 중...")
        await db_auto_trader._monitoring_cycle()
        print("매매조건 감시 실행 완료")
        
        # 원본 메서드 복원
        db_auto_trader.market_manager.is_monitoring_allowed_now = original_method
        
        # 결과 확인 - 상세 분석
        from database.models import MonitoringStock
        from sqlalchemy import create_engine, desc
        from sqlalchemy.orm import sessionmaker
        from config import Config
        
        config = Config()
        engine = create_engine(config.database.DB_URL)
        Session = sessionmaker(bind=engine)
        
        print("\n=== 매매조건 감시 결과 분석 ===")
        
        with Session() as session:
            # 최근 체크된 종목들
            now = datetime.now()
            recent_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.last_check_time.isnot(None)
            ).order_by(desc(MonitoringStock.last_check_time)).limit(10).all()
            
            if recent_stocks:
                print(f"SUCCESS: {len(recent_stocks)}개 종목이 감시되었습니다!")
                print("\n최근 체크된 종목들:")
                print("종목코드 | 종목명    | 체크시간    | 현재가")
                print("-" * 45)
                
                for stock in recent_stocks:
                    check_time = stock.last_check_time.strftime('%H:%M:%S') if stock.last_check_time else '미체크'
                    current_price = f"{stock.current_price:,}" if stock.current_price else "0"
                    print(f"{stock.symbol} | {stock.name[:8]:8} | {check_time:8} | {current_price:>8}")
                
                # 최근 5분 내 체크된 종목 수
                from datetime import timedelta
                recent_5min = now - timedelta(minutes=5)
                recent_count = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE',
                    MonitoringStock.last_check_time >= recent_5min
                ).count()
                
                print(f"\n최근 5분 내 체크: {recent_count}개 종목")
                
                if recent_count > 0:
                    print("\n✅ 매매조건 감시 시스템이 정상 동작하고 있습니다!")
                    print("📊 각 종목별로 다음 매매조건들이 실시간 체크됩니다:")
                    print("   매수조건: 종합신호, 골든크로스, RSI 과매도반등, 거래량급증, 캔들패턴, MACD")
                    print("   매도조건: 손절가도달, 종합신호매도, 데드크로스, RSI 과매수, 목표가달성")
                    return True
                else:
                    print("WARNING: 최근에 체크된 종목이 없습니다.")
                    return False
            else:
                print("WARNING: 아직 체크된 종목이 없습니다.")
                return False
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_trading_conditions_final())
    if success:
        print("\n🎯 매매조건 감시 시스템 최종 테스트 성공!")
        print("🔄 시스템이 활성 종목들을 지속적으로 감시하며 매매조건을 체크합니다.")
    else:
        print("\n❌ 매매조건 감시 시스템 테스트 실패!")