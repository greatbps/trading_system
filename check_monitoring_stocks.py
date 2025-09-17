#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 종목 상태 확인
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus, MonitoringType
from sqlalchemy.orm import Session

async def check_monitoring_stocks():
    """모니터링 종목 상태 확인"""
    print("=== 모니터링 종목 상태 확인 ===")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        with Session(db_manager.engine) as session:
            # DB에서 모니터링 종목 조회
            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.monitoring_type == MonitoringType.TRADING
            ).all()
            
            print(f"[DB] 전체 모니터링 종목: {len(monitoring_stocks)}개")
            
            # 상태별 분류
            active_stocks = [s for s in monitoring_stocks if s.status == MonitoringStatus.ACTIVE]
            inactive_stocks = [s for s in monitoring_stocks if s.status != MonitoringStatus.ACTIVE]
            
            print(f"[상태] 활성 종목: {len(active_stocks)}개")
            print(f"[상태] 비활성 종목: {len(inactive_stocks)}개")
            
            print("\n--- 활성 모니터링 종목 목록 ---")
            for stock in active_stocks[:10]:  # 최대 10개만 표시                   
                print(f"  - {stock.symbol}({stock.name}) [{stock.strategy_name}]")
                print(f"    등록일: {stock.created_at.strftime('%m/%d %H:%M')}")
                print(f"    상태: {stock.status.value}, 활성: {stock.monitoring_active}")
                print(f"    현재가: {stock.current_price}, 손절가: {stock.stop_loss_price}")
                
            print("\n--- 손절가 이하 종목 확인 ---")
            for stock in active_stocks:
                if hasattr(stock, 'current_price') and hasattr(stock, 'stop_loss_price'):
                    if stock.current_price and stock.stop_loss_price:
                        if stock.current_price <= stock.stop_loss_price:
                            print(f"  [위험] {stock.stock.symbol}: 현재가 {stock.current_price} <= 손절가 {stock.stop_loss_price}")
    
    except Exception as e:
        print(f"[ERROR] 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_monitoring_stocks())
