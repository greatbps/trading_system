#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB 모니터링 종목 확인 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_db_monitoring():
    """DB 모니터링 종목 확인"""
    print("=" * 60)
    print("DB 모니터링 종목 vs 보유종목 비교")
    print("=" * 60)
    
    # 확인된 보유종목들
    holdings = {
        '010170': '대한광통신',
        '013310': '아진산업', 
        '018500': '동원금속',
        '044180': 'KD',
        '201490': '미투온',
        '321370': '센서뷰(넷마블랩)',
        '363260': '모비데이즈(유비쿼스)'
    }
    
    print("1. 현재 보유종목 (7개):")
    print("-" * 40)
    for symbol, name in holdings.items():
        print(f"   {symbol}: {name}")
    
    print("\n2. DB 모니터링 확인이 필요한 이유:")
    print("-" * 40)
    print("   • 모든 종목이 'PORTFOLIO_HOLD'로 표시됨")
    print("   • DB에서 해당 종목들의 전략명을 찾지 못함")
    print("   • monitoring_symbols가 비어있거나 다른 종목코드들만 있음")
    
    print("\n3. 해결 방법:")
    print("-" * 40)
    print("   A. DB에서 실제 모니터링 종목 확인")
    print("   B. 보유종목들을 올바른 전략으로 DB에 등록")
    print("   C. 또는 보유종목의 전략 매핑 로직 수정")
    
    try:
        from database.models import DatabaseManager, MonitoringStock, MonitoringStatus
        from config import Config
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("\n4. DB 실제 모니터링 종목 조회:")
        print("-" * 40)
        
        with db_manager.get_session() as session:
            monitoring_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).all()
            
            print(f"   DB 모니터링 종목 수: {len(monitoring_stocks)}개")
            
            if monitoring_stocks:
                print("   DB 종목 목록:")
                for stock in monitoring_stocks:
                    print(f"     {stock.symbol}: {stock.name} - {stock.strategy_name}")
                    
                print("\n   보유종목과 DB 매칭:")
                for symbol, name in holdings.items():
                    db_stock = next((s for s in monitoring_stocks if s.symbol == symbol), None)
                    if db_stock:
                        print(f"     [매칭] {symbol}: {db_stock.strategy_name}")
                    else:
                        print(f"     [없음] {symbol}: DB에 없음 → PORTFOLIO_HOLD 표시됨")
            else:
                print("   DB에 모니터링 종목이 없습니다!")
                print("   → 모든 보유종목이 PORTFOLIO_HOLD로 표시됨")
                
    except Exception as e:
        print(f"\n[ERROR] DB 확인 실패: {e}")
        print("실제 DB 연결이 필요합니다.")

if __name__ == "__main__":
    check_db_monitoring()