#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보유종목을 DB에 등록하는 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def register_holdings_to_db():
    """보유종목들을 DB 모니터링 테이블에 등록"""
    print("=" * 60)
    print("보유종목 DB 등록 스크립트")
    print("=" * 60)
    
    # 보유종목 정보
    holdings_to_register = [
        {'symbol': '187660'}, {'name': '아바이오메드'}, {'strategy': 'SCALPING_3M'},
        {'symbol': '013310', 'name': '아진산업', 'strategy': 'SMART_MONEY'},
        {'symbol': '018500', 'name': '동원금속', 'strategy': 'SMART_MONEY'},
        {'symbol': '044180', 'name': 'KD', 'strategy': 'SMART_MONEY'},
        {'symbol': '201490', 'name': '미투온', 'strategy': 'SMART_MONEY'},
        {'symbol': '321370', 'name': '센서뷰', 'strategy': 'SMART_MONEY'},  # HTS명 사용
        {'symbol': '363260', 'name': '모비데이즈', 'strategy': 'SMART_MONEY'}  # HTS명 사용
    ]
    
    try:
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus, MonitoringType
        from config import Config
        from datetime import datetime
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        print(f"1. {len(holdings_to_register)}개 보유종목을 DB에 등록합니다...")
        print("-" * 40)
        
        with db_manager.get_session() as session:
            registered_count = 0
            
            for stock_info in holdings_to_register:
                symbol = stock_info['symbol']
                name = stock_info['name']
                strategy = stock_info['strategy']
                
                # 이미 등록된 종목인지 확인
                existing = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).first()
                
                if existing:
                    print(f"   [이미등록] {symbol}: {name} - {existing.strategy_name}")
                    # 전략명 업데이트 (필요시)
                    if existing.strategy_name != strategy:
                        existing.strategy_name = strategy
                        print(f"   [전략수정] {symbol}: {existing.strategy_name} → {strategy}")
                else:
                    # 새로 등록
                    new_stock = MonitoringStock(
                        symbol=symbol,
                        name=name,
                        strategy_name=strategy,
                        status=MonitoringStatus.ACTIVE.value,
                        monitoring_type=MonitoringType.TRADING,
                        monitoring_active=True,
                        recommendation_time=datetime.now()
                    )
                    session.add(new_stock)
                    registered_count += 1
                    print(f"   [신규등록] {symbol}: {name} - {strategy}")
            
            session.commit()
            
            print("-" * 40)
            print(f"✅ 등록 완료: 신규 {registered_count}개")
            print("이제 모니터링 화면에서 올바른 전략명이 표시됩니다!")
            
    except Exception as e:
        print(f"[ERROR] 등록 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    register_holdings_to_db()