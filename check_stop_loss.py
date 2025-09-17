#!/usr/bin/env python3
"""
손절가 직접 확인 스크립트
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus, MonitoringType

async def check_stop_loss():
    """손절가 직접 확인"""
    try:
        print("손절가 확인 시작...")
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE,
                MonitoringStock.monitoring_active == True,
                MonitoringStock.monitoring_type == MonitoringType.TRADING
            ).all()
            
            print(f"활성 모니터링 종목: {len(stocks)}개")
            print("-" * 80)
            
            for stock in stocks:
                stop_loss_str = f"{stock.stop_loss_price:,}원" if stock.stop_loss_price else "없음"
                current_price_str = f"{stock.current_price:,}원" if stock.current_price else "없음"
                
                print(f"종목: {stock.symbol}({stock.name})")
                print(f"  전략: {stock.strategy_name}")
                print(f"  현재가: {current_price_str}")
                print(f"  손절가: {stop_loss_str}")
                print(f"  목표가: {stock.target_price:,}원" if stock.target_price else "  목표가: 없음")
                print("-" * 40)
        
        print("손절가 확인 완료")
        
    except Exception as e:
        print(f"손절가 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_stop_loss())