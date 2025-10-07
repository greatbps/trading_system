#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_monitoring_status():
    """현재 모니터링 상태만 확인"""
    try:
        print("=== 최소 모니터링 상태 확인 ===")
        
        # 데이터베이스 직접 접근
        from database.models import MonitoringStock
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from config import Config
        
        config = Config()
        print(f"데이터베이스 URL: {config.database.DB_URL}")
        
        engine = create_engine(config.database.DB_URL)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # 전체 모니터링 종목 수
            total_count = session.query(MonitoringStock).count()
            print(f"전체 모니터링 종목: {total_count}개")
            
            # 활성 모니터링 종목 수
            active_count = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE'
            ).count()
            print(f"활성 모니터링 종목: {active_count}개")
            
            # 최근 체크된 종목 (지난 1시간 내)
            from datetime import datetime, timedelta
            recent_time = datetime.now() - timedelta(hours=1)
            
            recent_count = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.last_check_time > recent_time
            ).count()
            print(f"최근 1시간 내 체크된 종목: {recent_count}개")
            
            # 활성 종목 목록
            active_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE'
            ).limit(5).all()
            
            print("\n활성 종목 예시 (최대 5개):")
            for stock in active_stocks:
                last_check = stock.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if stock.last_check_time else '미체크'
                print(f"  - {stock.symbol}({stock.name}) | 마지막 체크: {last_check}")
            
            # 매매 신호가 있는 종목
            signal_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.trading_signal.isnot(None)
            ).count()
            print(f"\n매매 신호가 있는 종목: {signal_stocks}개")
            
            return True
            
    except Exception as e:
        print(f"상태 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_monitoring_status()
    if success:
        print("\n모니터링 상태 확인 완료!")
    else:
        print("\n모니터링 상태 확인 실패!")