#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from data_collectors.kis_collector import KISCollector
from config import Config

async def update_stock_names():
    try:
        print("KIS API 종목명 업데이트 시작")
        print("=" * 60)
        
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        
        await kis_collector.initialize()
        print("KIS API 초기화 완료")
        
        with db_manager.get_session() as session:
            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).all()
            
            print(f"업데이트 대상: {len(monitoring_stocks)}개 종목")
            print("-" * 60)
            
            updated_count = 0
            failed_count = 0
            
            for stock in monitoring_stocks:
                try:
                    print(f"{stock.symbol} 종목명 조회 중...", end=" ")
                    
                    stock_info = await kis_collector.get_stock_info(stock.symbol)
                    
                    if stock_info and stock_info.name:
                        old_name = stock.name or "N/A"
                        new_name = stock_info.name
                        
                        stock.name = new_name
                        stock.updated_at = datetime.now()
                        
                        updated_count += 1
                        
                        if old_name != new_name:
                            print(f"업데이트: {old_name} -> {new_name}")
                        else:
                            print(f"확인: {new_name} (변경없음)")
                        
                        await asyncio.sleep(0.1)
                        
                    else:
                        print(f"종목명 조회 실패")
                        failed_count += 1
                        
                except Exception as e:
                    print(f"오류: {e}")
                    failed_count += 1
                    continue
            
            session.commit()
            
            print("-" * 60)
            print("업데이트 결과:")
            print(f"  성공: {updated_count}개")
            print(f"  실패: {failed_count}개")
            if updated_count + failed_count > 0:
                print(f"  성공률: {updated_count/(updated_count+failed_count)*100:.1f}%")
            
            return updated_count > 0
            
    except Exception as e:
        print(f"전체 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await update_stock_names()
    
    if success:
        print("\n종목명 업데이트 완료!")
        print("python test_monitoring_display.py 로 결과를 확인하세요.")
    else:
        print("\n종목명 업데이트 실패!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
