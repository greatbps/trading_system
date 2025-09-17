#!/usr/bin/env python3

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from config import Config

stock_names = {
    '005930': '삼성전자',
    '000660': 'SK하이닉스', 
    '035420': 'NAVER',
    '068270': '셀트리온',
    '207940': '삼성바이오로직스',
    '373220': 'LG에너지솔루션',
    '006400': '삼성SDI',
    '028260': '삼성물산',
    '051910': 'LG화학',
    '005360': '모나미',
    '187660': '아바신제약',
    '290550': '디케이티',
    '059090': 'KCC',
    '090460': '네오위즈',
    '223250': '엘원메디칼',
    '055550': '신한지주',
    '086790': '하나금융지주',
    '105560': 'KB금융',
    '011070': 'LG이노텍',
    '023160': '태광산업',
    '226950': '올릭스',
    '108380': '대림LS',
    '413630': '유한양행',
    '414780': '제넥신'
}

config = Config()
db_manager = DatabaseManager(config)

print("종목명 복원 중...")

with db_manager.get_session() as session:
    updated_count = 0
    
    for symbol, correct_name in stock_names.items():
        stock = session.query(MonitoringStock).filter(
            MonitoringStock.symbol == symbol,
            MonitoringStock.status == MonitoringStatus.ACTIVE
        ).first()
        
        if stock:
            old_name = stock.name
            stock.name = correct_name
            stock.updated_at = datetime.now()
            updated_count += 1
            print(f"{symbol}: {old_name} -> {correct_name}")
    
    session.commit()
    print(f"복원 완료: {updated_count}개 종목")
