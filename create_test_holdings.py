#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트용 보유종목 생성
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from config import Config

def create_test_holdings():
    """테스트용 보유종목 생성"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("테스트용 보유종목 생성")
        print("=" * 40)
        
        with db_manager.get_session() as session:
            # 일부 종목을 보유종목으로 업데이트
            test_holdings = [
                {
                    'symbol': '005930',  # 삼성전자
                    'buy_price': 75000,
                    'buy_quantity': 10,
                    'current_price': 78000
                },
                {
                    'symbol': '000660',  # SK하이닉스
                    'buy_price': 125000,
                    'buy_quantity': 5,
                    'current_price': 130000
                },
                {
                    'symbol': '187660',  # 아바이오메드
                    'buy_price': 45000,
                    'buy_quantity': 20,
                    'current_price': 42000
                }
            ]
            
            for holding in test_holdings:
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == holding['symbol']
                ).first()
                
                if stock:
                    # 매수 정보 업데이트
                    stock.buy_price = holding['buy_price']
                    stock.buy_quantity = holding['buy_quantity']
                    stock.buy_amount = holding['buy_price'] * holding['buy_quantity']
                    stock.avg_price = holding['buy_price']
                    stock.holding_quantity = holding['buy_quantity']
                    stock.buy_time = datetime.now()
                    
                    # 손익 업데이트 (current_price는 DB에 저장하지 않음)
                    profit_loss = (holding['current_price'] - holding['buy_price']) * holding['buy_quantity']
                    profit_rate = ((holding['current_price'] - holding['buy_price']) / holding['buy_price']) * 100
                    
                    stock.profit_loss = profit_loss
                    stock.profit_rate = profit_rate
                    
                    print(f"OK {stock.symbol}({stock.name}) 보유종목 생성:")
                    print(f"   매수: {stock.buy_quantity}주 @ {stock.buy_price:,}원")
                    print(f"   현재: {stock.current_price:,}원")
                    print(f"   손익: {profit_loss:+,}원 ({profit_rate:+.2f}%)")
                    print(f"   전략: {stock.strategy_name}")
            
            session.commit()
            print(f"\n테스트 보유종목 {len(test_holdings)}개 생성 완료!")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_holdings()