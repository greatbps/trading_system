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

async def test_monitoring_display():
    """모니터링 현황 표시 테스트"""
    try:
        print("모니터링 현황 표시 테스트")
        print("=" * 40)
        
        from database.models import Stock, MonitoringStock, MonitoringStatus
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from config import Config
        
        config = Config()
        engine = create_engine(config.database.DB_URL)
        Session = sessionmaker(bind=engine)
        
        # 실제 모니터링 표시 로직 시뮬레이션
        with Session() as session:
            active_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).order_by(MonitoringStock.recommendation_time.desc()).limit(30).all()
            
            print(f"활성 모니터링 종목: {len(active_stocks)}개")
            print()
            
            for monitoring in active_stocks:
                # 실제 표시 로직과 동일한 방식으로 종목명 조회
                raw_name = "N/A"
                try:
                    stock_info = session.query(Stock).filter(Stock.symbol == monitoring.symbol).first()
                    if stock_info and stock_info.name:
                        raw_name = stock_info.name
                    elif monitoring.name:
                        raw_name = monitoring.name
                except Exception:
                    if monitoring.name:
                        raw_name = monitoring.name
                
                # 결과 표시
                if raw_name.startswith('종목'):
                    status_icon = "[임시]"
                else:
                    status_icon = "[정상]"
                
                print(f"{status_icon} {monitoring.symbol}: \"{raw_name}\" ({monitoring.strategy_name})")
        
        print()
        print("테스트 완료!")
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_monitoring_display())
    if success:
        print("\n모니터링 현황 표시 테스트 성공!")
    else:
        print("\n모니터링 현황 표시 테스트 실패!")