#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def analyze_monitoring_status():
    """매매조건 감시 상태 상세 분석"""
    try:
        print("=== 매매조건 감시 상태 상세 분석 ===")
        print(f"분석 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        from database.models import MonitoringStock
        from sqlalchemy import create_engine, desc
        from sqlalchemy.orm import sessionmaker
        from config import Config
        
        config = Config()
        engine = create_engine(config.database.DB_URL)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # 1. 전체 모니터링 종목 현황
            print("\n1. 전체 모니터링 종목 현황")
            total_stocks = session.query(MonitoringStock).count()
            active_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE'
            ).count()
            print(f"전체 종목: {total_stocks}개")
            print(f"활성 종목: {active_stocks}개")
            
            # 2. 최근 체크 현황 분석
            print("\n2. 최근 체크 현황 분석")
            now = datetime.now()
            
            # 오늘 체크된 종목
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_checked = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.last_check_time >= today_start
            ).count()
            
            # 최근 1시간 내 체크된 종목  
            recent_hour = now - timedelta(hours=1)
            hour_checked = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.last_check_time >= recent_hour
            ).count()
            
            # 최근 10분 내 체크된 종목
            recent_10min = now - timedelta(minutes=10)
            min10_checked = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE',
                MonitoringStock.last_check_time >= recent_10min
            ).count()
            
            print(f"오늘 체크된 종목: {today_checked}개 / {active_stocks}개")
            print(f"최근 1시간 체크: {hour_checked}개")
            print(f"최근 10분 체크: {min10_checked}개")
            
            # 3. 활성 종목별 상태 상세 조회
            print("\n3. 활성 종목별 상태 상세")
            stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'ACTIVE'
            ).order_by(desc(MonitoringStock.last_check_time)).all()
            
            print("종목코드 | 종목명 | 마지막체크 | 현재가 | 매매신호")
            print("-" * 60)
            
            for stock in stocks:
                last_check = stock.last_check_time.strftime('%H:%M:%S') if stock.last_check_time else '미체크'
                current_price = f"{stock.current_price:,}" if stock.current_price else "0"
                signal = stock.trading_signal if hasattr(stock, 'trading_signal') and stock.trading_signal else "없음"
                
                print(f"{stock.symbol} | {stock.name[:8]:8} | {last_check:8} | {current_price:>8} | {signal}")
            
            # 4. 매매신호 분석
            print("\n4. 매매신호 분석")
            
            # 신호 타입별 집계 (trading_signal 컬럼이 있다면)
            try:
                buy_signals = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE',
                    MonitoringStock.trading_signal == 'BUY'
                ).count()
                
                sell_signals = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE', 
                    MonitoringStock.trading_signal == 'SELL'
                ).count()
                
                no_signals = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE',
                    MonitoringStock.trading_signal.is_(None)
                ).count()
                
                print(f"매수 신호: {buy_signals}개")
                print(f"매도 신호: {sell_signals}개")
                print(f"신호 없음: {no_signals}개")
                
            except Exception as e:
                print(f"매매신호 컬럼 없음: {e}")
            
            # 5. 모니터링 전략별 분석
            print("\n5. 모니터링 전략별 분석")
            try:
                strategies = session.query(MonitoringStock.strategy).distinct().all()
                for strategy_tuple in strategies:
                    strategy = strategy_tuple[0]
                    count = session.query(MonitoringStock).filter(
                        MonitoringStock.status == 'ACTIVE',
                        MonitoringStock.strategy == strategy
                    ).count()
                    print(f"{strategy}: {count}개")
            except Exception as e:
                print(f"전략 컬럼 정보 없음: {e}")
            
            return True
            
    except Exception as e:
        print(f"분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = analyze_monitoring_status()
    if success:
        print("\n모니터링 상태 분석 완료!")
    else:
        print("\n모니터링 상태 분석 실패!")