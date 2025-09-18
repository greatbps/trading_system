#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from config import Config

# 새로운 24개 종목 데이터
stocks_data = [
    # MOMENTUM 전략 (3개)
    {'symbol': '005930', 'name': '삼성전자', 'strategy': 'MOMENTUM'},
    {'symbol': '000660', 'name': 'SK하이닉스', 'strategy': 'MOMENTUM'},  
    {'symbol': '035420', 'name': 'NAVER', 'strategy': 'MOMENTUM'},
    
    # BREAKOUT 전략 (3개)  
    {'symbol': '068270', 'name': '셀트리온', 'strategy': 'BREAKOUT'},
    {'symbol': '207940', 'name': '삼성바이오로직스', 'strategy': 'BREAKOUT'},
    {'symbol': '373220', 'name': 'LG에너지솔루션', 'strategy': 'BREAKOUT'},
    
    # RSI_STRATEGY (3개)
    {'symbol': '006400', 'name': '삼성SDI', 'strategy': 'RSI_STRATEGY'},
    {'symbol': '051910', 'name': 'LG화학', 'strategy': 'RSI_STRATEGY'},
    {'symbol': '028260', 'name': '삼성물산', 'strategy': 'RSI_STRATEGY'},
    
    # SUPERTREND_EMA (3개)
    {'symbol': '105560', 'name': 'KB금융', 'strategy': 'SUPERTREND_EMA'},
    {'symbol': '055550', 'name': '신한지주', 'strategy': 'SUPERTREND_EMA'},
    {'symbol': '086790', 'name': '하나금융지주', 'strategy': 'SUPERTREND_EMA'},
    
    # VWAP_STRATEGY (3개)
    {'symbol': '011070', 'name': 'LG이노텍', 'strategy': 'VWAP_STRATEGY'},
    {'symbol': '023160', 'name': '태광산업', 'strategy': 'VWAP_STRATEGY'},
    {'symbol': '226950', 'name': '올릭스', 'strategy': 'VWAP_STRATEGY'},
    
    # SCALPING_3M (3개)
    {'symbol': '187660', 'name': '아바신제약', 'strategy': 'SCALPING_3M'},
    {'symbol': '005360', 'name': '모나미', 'strategy': 'SCALPING_3M'},
    {'symbol': '290550', 'name': '디케이티', 'strategy': 'SCALPING_3M'},
    
    # SMART_MONEY (3개)  
    {'symbol': '059090', 'name': 'KCC', 'strategy': 'SMART_MONEY'},
    {'symbol': '223250', 'name': '엘원메디칼', 'strategy': 'SMART_MONEY'},
    {'symbol': '090460', 'name': '네오위즈', 'strategy': 'SMART_MONEY'},
    
    # AI_ANALYSIS (3개)
    {'symbol': '414780', 'name': '제넥신', 'strategy': 'AI_ANALYSIS'}, 
    {'symbol': '108380', 'name': '대림LS', 'strategy': 'AI_ANALYSIS'},
    {'symbol': '413630', 'name': '유한양행', 'strategy': 'AI_ANALYSIS'}
]

def clear_and_create():
    config = Config()
    db_manager = DatabaseManager(config)
    
    print("모든 데이터 완전 삭제 및 새로 생성")
    print("=" * 50)
    
    with db_manager.get_session() as session:
        # 기존 데이터 모두 삭제
        session.execute("DELETE FROM monitoring_stocks")
        session.commit()
        print("기존 데이터 모두 삭제 완료")
        
        # 새 데이터 생성
        created_count = 0
        for stock_data in stocks_data:
            new_stock = MonitoringStock(
                symbol=stock_data['symbol'],
                name=stock_data['name'], 
                strategy_name=stock_data['strategy'],
                status=MonitoringStatus.ACTIVE.value,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(new_stock)
            created_count += 1
        
        session.commit()
        print(f"새로운 감시 종목 {created_count}개 생성 완료")
        
        # 확인
        stocks = session.query(MonitoringStock).all()
        print(f"총 감시 종목: {len(stocks)}개")
        
        for stock in stocks[:5]:  # 처음 5개만 출력
            print(f"  {stock.symbol}: {stock.name} ({stock.strategy_name})")
        
        if len(stocks) > 5:
            print(f"  ... 외 {len(stocks)-5}개")
            
        print("완료!")

if __name__ == "__main__":
    clear_and_create()
