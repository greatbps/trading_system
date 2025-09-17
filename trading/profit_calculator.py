#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
손익 계산 및 실시간 업데이트 모듈
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import asyncio

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from data_collectors.kis_collector import KISCollector
from config import Config

class ProfitCalculator:
    """손익 계산기"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, kis_collector: KISCollector):
        self.config = config
        self.db_manager = db_manager
        self.kis_collector = kis_collector
        
    async def update_all_holdings_profit_loss(self) -> Dict[str, Any]:
        """모든 보유종목의 손익 실시간 업데이트"""
        try:
            updated_count = 0
            failed_count = 0
            
            with self.db_manager.get_session() as session:
                # 보유중인 종목들 조회
                holding_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.buy_price.isnot(None),
                    MonitoringStock.holding_quantity > 0
                ).all()
                
                print(f"손익 업데이트 대상: {len(holding_stocks)}개 종목")
                
                for stock in holding_stocks:
                    try:
                        # 현재 가격 조회
                        current_price = await self.kis_collector.get_current_price(stock.symbol)
                        if not current_price:
                            failed_count += 1
                            continue
                        
                        # 손익 계산
                        profit_loss = (current_price - stock.buy_price) * stock.holding_quantity
                        profit_rate = ((current_price - stock.buy_price) / stock.buy_price) * 100
                        
                        # DB 업데이트 (current_price 제외 - 실시간 조회만 사용)
                        stock.profit_loss = profit_loss
                        stock.profit_rate = round(profit_rate, 4)
                        
                        updated_count += 1
                        print(f"Success: {stock.symbol}({stock.name}): {profit_rate:+.2f}% ({profit_loss:+,}원)")
                        
                    except Exception as e:
                        print(f"Error: {stock.symbol} - {e}")
                        failed_count += 1
                
                session.commit()
                
            return {
                'success': True,
                'updated_count': updated_count,
                'failed_count': failed_count,
                'total_count': len(holding_stocks)
            }
            
        except Exception as e:
            print(f"Update error: {e}")
            return {'success': False, 'error': str(e)}

    async def record_buy_transaction(self, symbol: str, buy_price: int, quantity: int, total_amount: int) -> bool:
        """매수 거래 기록"""
        try:
            with self.db_manager.get_session() as session:
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).first()
                
                if not stock:
                    return False
                
                stock.buy_price = buy_price
                stock.buy_quantity = quantity
                stock.buy_amount = total_amount
                stock.avg_price = buy_price
                stock.holding_quantity = quantity
                stock.buy_time = datetime.now()
                stock.profit_loss = 0
                stock.profit_rate = 0.0
                
                session.commit()
                print(f"✅ 매수 기록: {symbol} {quantity:,}주 @ {buy_price:,}원")
                return True
                
        except Exception as e:
            print(f"매수 기록 오류: {e}")
            return False

    async def record_sell_transaction(self, symbol: str, sell_price: int, sell_quantity: int) -> bool:
        """매도 거래 기록"""
        try:
            with self.db_manager.get_session() as session:
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.holding_quantity > 0
                ).first()
                
                if not stock:
                    return False
                
                final_profit_loss = (sell_price - stock.buy_price) * sell_quantity
                final_profit_rate = ((sell_price - stock.buy_price) / stock.buy_price) * 100
                
                # current_price는 DB에 저장하지 않음 - 실시간 조회만 사용
                stock.profit_loss = final_profit_loss
                stock.profit_rate = round(final_profit_rate, 4)
                stock.sell_time = datetime.now()
                stock.holding_quantity = stock.holding_quantity - sell_quantity
                
                if stock.holding_quantity <= 0:
                    stock.status = MonitoringStatus.COMPLETED
                    stock.completed_time = datetime.now()
                
                session.commit()
                print(f"✅ 매도 기록: {symbol} {sell_quantity:,}주 @ {sell_price:,}원")
                return True
                
        except Exception as e:
            print(f"매도 기록 오류: {e}")
            return False
async def main():
    """테스트 함수"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        
        await kis_collector.initialize()
        
        calculator = ProfitCalculator(config, db_manager, kis_collector)
        result = await calculator.update_all_holdings_profit_loss()
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
