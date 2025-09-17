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

async def test_monitoring_addition():
    """모니터링 추가 테스트"""
    try:
        print("모니터링 추가 종목명 처리 테스트 시작")
        print("=" * 50)
        
        from core.trading_system import TradingSystem
        
        # Trading System 초기화
        trading_system = TradingSystem()
        success = await trading_system.initialize_components()
        
        if not success:
            print("Trading System 초기화 실패")
            return False
            
        print("Trading System 초기화 완료")
        
        # DB AutoTrader 확인
        if not hasattr(trading_system, 'db_auto_trader') or not trading_system.db_auto_trader:
            print("DB AutoTrader가 초기화되지 않음")
            return False
            
        print("DB AutoTrader 확인 완료")
        
        # 테스트 데이터 - 임시 종목명으로 시작
        test_data = [
            {
                'symbol': '000150',
                'name': '종목000150',  # 임시 이름
                'recommendation': 'BUY',
                'strategy': 'TEST_ADVANCED_EXTRACTION',
                'current_price': 10000
            },
            {
                'symbol': '443060', 
                'name': '종목443060',  # 임시 이름
                'recommendation': 'BUY',
                'strategy': 'TEST_ADVANCED_EXTRACTION',
                'current_price': 20000
            }
        ]
        
        print(f"\n테스트 데이터: {len(test_data)}개 종목")
        for data in test_data:
            print(f"   - {data['symbol']}: '{data['name']}' → 정확한 종목명으로 변경 예상")
        
        print(f"\nadd_buy_recommendation 테스트:")
        print("-" * 50)
        
        added_symbols = []
        
        for data in test_data:
            try:
                symbol = data['symbol']
                temp_name = data['name']
                
                print(f"\n{symbol} 처리 중...")
                print(f"   입력 이름: '{temp_name}'")
                
                # add_buy_recommendation 호출
                result = await trading_system.db_auto_trader.add_buy_recommendation(
                    symbol=symbol,
                    name=temp_name,
                    strategy_name=data['strategy'],
                    target_price=int(data['current_price'] * 1.15),
                    stop_loss_price=int(data['current_price'] * 0.95)
                )
                
                if result:
                    print(f"   모니터링 추가: 성공")
                    added_symbols.append(symbol)
                    
                    # DB에서 실제 저장된 이름 확인
                    try:
                        # DB 매니저를 통해 직접 확인
                        db_manager = trading_system.db_auto_trader.db_manager
                        with db_manager.get_session() as session:
                            from database.models import MonitoringStock
                            monitoring_stock = session.query(MonitoringStock).filter(
                                MonitoringStock.symbol == symbol,
                                MonitoringStock.strategy_name == data['strategy']
                            ).first()
                            
                            if monitoring_stock:
                                stored_name = monitoring_stock.name
                                print(f"   저장된 이름: '{stored_name}'")
                                
                                if stored_name.startswith('종목'):
                                    print(f"   결과: 임시 이름 유지 (개선 필요)")
                                else:
                                    print(f"   결과: 정확한 종목명 추출 성공!")
                            else:
                                print(f"   DB에서 모니터링 정보를 찾을 수 없음")
                    except Exception as db_error:
                        print(f"   DB 확인 중 오류: {db_error}")
                else:
                    print(f"   모니터링 추가: 실패")
                
            except Exception as e:
                print(f"   오류: {e}")
        
        # 테스트 데이터 정리
        print(f"\n테스트 데이터 정리 중...")
        try:
            if added_symbols:
                db_manager = trading_system.db_auto_trader.db_manager
                with db_manager.get_session() as session:
                    from database.models import MonitoringStock
                    deleted_count = session.query(MonitoringStock).filter(
                        MonitoringStock.strategy_name == 'TEST_ADVANCED_EXTRACTION'
                    ).delete()
                    session.commit()
                    print(f"테스트 데이터 정리 완료: {deleted_count}개 삭제")
        except Exception as cleanup_error:
            print(f"정리 중 오류: {cleanup_error}")
        
        print(f"\n모니터링 추가 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_monitoring_addition())
    if success:
        print("\n모니터링 추가 종목명 처리 테스트 성공!")
    else:
        print("\n모니터링 추가 종목명 처리 테스트 실패!")