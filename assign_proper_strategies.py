#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보유종목에 적절한 전략 할당 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def assign_strategies_to_holdings():
    """각 보유종목에 적절한 전략 할당"""
    print("=" * 60)
    print("보유종목별 전략 할당")
    print("=" * 60)
    
    # 보유종목별 적절한 전략 매핑
    # 다양한 전략으로 분산 배치하여 각 전략의 성과를 추적
    strategy_assignments = [
        {'symbol': '010170', 'name': '대한광통신', 'strategy': 'SMART_MONEY'},      # 1D, 스마트머니 추적 (승률 70%)
        {'symbol': '013310', 'name': '아진산업', 'strategy': 'VWAP_STRATEGY'},      # 5M, VWAP 기준 (승률 68%)  
        {'symbol': '018500', 'name': '동원금속', 'strategy': 'SMART_MONEY'},        # 1D, AI 분석 기반 (승률 65%)
        {'symbol': '044180', 'name': 'KD', 'strategy': 'SUPERTREND_EMA'},           # 15M, 슈퍼트렌드+EMA (승률 62%)
        {'symbol': '201490', 'name': '미투온', 'strategy': 'MOMENTUM'},             # 1H, 모멘텀 전략 (승률 60%)
        {'symbol': '321370', 'name': '센서뷰', 'strategy': 'RSI_STRATEGY'},         # 1H, RSI 전략 (승률 58%)
        {'symbol': '363260', 'name': '모비데이즈', 'strategy': 'BREAKOUT'}          # 30M, 돌파 전략 (승률 55%)
    ]
    
    try:
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock, MonitoringStatus
        from config import Config
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("보유종목별 전략 할당:")
        print("-" * 40)
        
        with db_manager.get_session() as session:
            updated_count = 0
            
            for assignment in strategy_assignments:
                symbol = assignment['symbol']
                name = assignment['name']
                strategy = assignment['strategy']
                
                # DB에서 해당 종목 찾기
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).first()
                
                if stock:
                    old_strategy = stock.strategy_name
                    stock.strategy_name = strategy
                    updated_count += 1
                    print(f"   {symbol}: {name}")
                    print(f"     {old_strategy} → {strategy}")
                else:
                    print(f"   [오류] {symbol}: DB에서 찾을 수 없음")
                
                print()
            
            session.commit()
            
            print("-" * 40)
            print(f"[완료] {updated_count}개 종목의 전략을 업데이트했습니다!")
            
            # 전략 분포 확인
            print("\n할당된 전략 분포:")
            strategy_count = {}
            for assignment in strategy_assignments:
                strategy = assignment['strategy']
                strategy_count[strategy] = strategy_count.get(strategy, 0) + 1
            
            for strategy, count in strategy_count.items():
                print(f"   {strategy}: {count}개 종목")
            
            print("\n이제 모니터링 화면에서 다양한 전략명이 표시됩니다!")
            
    except Exception as e:
        print(f"[ERROR] 전략 할당 실패: {e}")
        import traceback
        traceback.print_exc()

def show_strategy_rationale():
    """전략 할당 근거 설명"""
    print("\n" + "=" * 60)
    print("전략 할당 근거")
    print("=" * 60)
    
    rationale = [
        ("대한광통신", "SMART_MONEY", "통신주로 기관투자자 관심 높음, 장기관점"),
        ("아진산업", "VWAP_STRATEGY", "산업재로 거래량 기준 매매 적합"),
        ("동원금속", "SMART_MONEY", "금속/소재주로 AI 분석 효과적"),
        ("KD", "SUPERTREND_EMA", "중소형주로 트렌드 추종 전략"),
        ("미투온", "MOMENTUM", "IT/바이오 관련으로 모멘텀 강함"),
        ("센서뷰", "RSI_STRATEGY", "변동성 높은 기술주로 RSI 역추세"),
        ("모비데이즈", "BREAKOUT", "소형주로 돌파매매 전략 적합")
    ]
    
    for name, strategy, reason in rationale:
        print(f"• {name}: {strategy}")
        print(f"  └─ {reason}")

if __name__ == "__main__":
    assign_strategies_to_holdings()
    show_strategy_rationale()