#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 데이터 초기화 및 재생성
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus, MonitoringType
from config import Config

def reset_and_populate_data():
    """모니터링 데이터 초기화 및 재생성"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("모니터링 데이터 초기화 및 재생성 시작")
        print("=" * 50)
        
        # 종목명 매핑 (종목코드 → 종목명)
        stock_name_mapping = {
            '187660': '아바이오메드',
            '005360': '모나미', 
            '290550': '디케이티',
            '023160': '현대위아',
            '226950': '올릭스',
            '059090': 'KCC',
            '011070': 'LG이노텍',
            '223250': '영창케미칼',
            '090460': '비에이치',
            '414780': '펄어비스',
            '108380': '대봉LS',
            '413630': '대한과선',
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '035420': 'NAVER',
            '068270': '셀트리온',
            '207940': '삼성바이오로직스',
            '373220': 'LG에너지솔루션',
            '006400': '삼성SDI',
            '051910': 'LG화학',
            '028260': '삼성물산',
            '105560': 'KB금융',
            '055550': '신한지주',
            '086790': '하나금융지주'
        }
        
        # 전략별 종목 데이터
        strategy_stocks = {
            'MOMENTUM': ['023160', '005930', '000660'],
            'BREAKOUT': ['005360', '035420', '068270'], 
            'RSI_STRATEGY': ['059090', '207940', '373220'],
            'SUPERTREND_EMA': ['011070', '006400', '051910'],
            'VWAP_STRATEGY': ['226950', '028260', '105560'],
            'SCALPING_3M': ['187660', '055550', '086790'],
            'SMART_MONEY': ['223250', '090460', '414780'],
            'AI_ANALYSIS': ['290550', '108380', '413630']
        }
        
        with db_manager.get_session() as session:
            # 1. 기존 모든 모니터링 종목 삭제 (완전 초기화)
            deleted_count = session.query(MonitoringStock).delete()
            session.commit()  # 삭제 즉시 커밋
            
            print(f"기존 모든 모니터링 종목 삭제: {deleted_count}개")
            
            # 2. 새로운 모니터링 종목 생성
            total_added = 0
            
            for strategy_name, symbols in strategy_stocks.items():
                print(f"\n전략 '{strategy_name}' 종목 추가:")
                
                for symbol in symbols:
                    stock_name = stock_name_mapping.get(symbol, f'종목{symbol}')
                    
                    # 새 모니터링 종목 생성
                    new_stock = MonitoringStock(
                        symbol=symbol,
                        name=stock_name,
                        strategy_name=strategy_name,
                        monitoring_type=MonitoringType.TRADING,
                        status=MonitoringStatus.ACTIVE.value,
                        monitoring_active=True,
                        recommendation_time=datetime.now(),
                        add_reason=f"{strategy_name} 전략 추천"
                    )
                    
                    session.add(new_stock)
                    total_added += 1
                    print(f"  - {symbol}: {stock_name}")
            
            # 3. 변경사항 저장
            session.commit()
            
            print(f"\n총 {total_added}개 모니터링 종목 추가 완료")
            
            # 4. 결과 확인
            print("\n추가된 종목 목록 확인:")
            print("-" * 70)
            print(f"{'종목코드':<10} {'종목명':<15} {'전략명':<15} {'상태':<10}")
            print("-" * 70)
            
            final_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).order_by(MonitoringStock.strategy_name, MonitoringStock.symbol).all()
            
            for stock in final_stocks:
                print(f"{stock.symbol:<10} {stock.name:<15} {stock.strategy_name:<15} {stock.status.value:<10}")
            
            print(f"\n모니터링 데이터 재생성 완료! (총 {len(final_stocks)}개 종목)")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_and_populate_data()