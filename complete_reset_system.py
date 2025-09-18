#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 시스템 완전 초기화 및 재구축
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus, MonitoringType
from config import Config

def complete_system_reset():
    """전체 시스템 완전 초기화 및 재구축"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("전체 시스템 완전 초기화 시작")
        print("=" * 60)
        
        # 완전한 종목명 매핑
        stock_name_mapping = {
            # 대형주
            '005930': '삼성전자',
            '000660': 'SK하이닉스', 
            '035420': 'NAVER',
            '068270': '셀트리온',
            '207940': '삼성바이오로직스',
            '373220': 'LG에너지솔루션',
            '006400': '삼성SDI',
            '051910': 'LG화학',
            '028260': '삼성물산',
            '105560': 'KB금융',
            '055550': '신한지주',
            '086790': '하나금융지주',
            '011070': 'LG이노텍',
            # 중소형주
            '187660': '아바이오메드',
            '005360': '모나미',
            '290550': '디케이티', 
            '023160': '현대위아',
            '226950': '올릭스',
            '059090': 'KCC',
            '223250': '영창케미칼',
            '090460': '비에이치',
            '414780': '펄어비스',
            '108380': '대봉LS',
            '413630': '대한과선'
        }
        
        # 전략별 종목 재분배 (실제 시장 특성 고려)
        strategy_stocks = {
            'MOMENTUM': ['005930', '000660', '035420'],  # 대형 테크주
            'BREAKOUT': ['068270', '207940', '373220'],  # 바이오/배터리
            'RSI_STRATEGY': ['006400', '051910', '028260'],  # 화학/소재
            'SUPERTREND_EMA': ['105560', '055550', '086790'],  # 금융주
            'VWAP_STRATEGY': ['011070', '023160', '226950'],  # 중형 제조업
            'SCALPING_3M': ['187660', '005360', '290550'],  # 소형 변동주
            'SMART_MONEY': ['059090', '223250', '090460'],  # 중소 산업재
            'AI_ANALYSIS': ['414780', '108380', '413630']   # IT/게임/통신
        }
        
        with db_manager.get_session() as session:
            # 1. 모든 기존 데이터 완전 삭제
            print("1단계: 기존 데이터 완전 삭제")
            deleted_count = session.query(MonitoringStock).delete()
            session.commit()
            print(f"   - 삭제된 레코드: {deleted_count}개")
            
            # 2. 새로운 감시종목 생성
            print("\n2단계: 새로운 감시종목 생성")
            total_added = 0
            
            for strategy_name, symbols in strategy_stocks.items():
                print(f"   전략 '{strategy_name}':")
                
                for symbol in symbols:
                    stock_name = stock_name_mapping.get(symbol, f'종목{symbol}')
                    
                    new_stock = MonitoringStock(
                        symbol=symbol,
                        name=stock_name,  # 실제 종목명 저장
                        strategy_name=strategy_name,  # 실제 전략명 저장
                        monitoring_type=MonitoringType.TRADING,
                        status=MonitoringStatus.ACTIVE.value,
                        monitoring_active=True,
                        recommendation_time=datetime.now(),
                        add_reason=f"{strategy_name} 전략 기반 추천"
                    )
                    
                    session.add(new_stock)
                    total_added += 1
                    print(f"     - {symbol}: {stock_name}")
            
            # 3. 변경사항 저장
            session.commit()
            print(f"\n   총 {total_added}개 감시종목 생성 완료")
            
            # 4. 결과 검증
            print("\n3단계: 생성 결과 검증")
            print("-" * 80)
            print(f"{'종목코드':<10} {'종목명':<15} {'전략명':<15} {'상태':<10}")
            print("-" * 80)
            
            verification_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).order_by(MonitoringStock.strategy_name, MonitoringStock.symbol).all()
            
            for stock in verification_stocks:
                print(f"{stock.symbol:<10} {stock.name:<15} {stock.strategy_name:<15} {stock.status.value:<10}")
            
            # 5. 전략별 통계
            print(f"\n4단계: 전략별 통계")
            print("-" * 40)
            
            from sqlalchemy import func
            strategy_stats = session.query(
                MonitoringStock.strategy_name,
                func.count(MonitoringStock.id).label('count')
            ).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE
            ).group_by(MonitoringStock.strategy_name).all()
            
            for strategy, count in strategy_stats:
                print(f"{strategy:<20} {count:>3}개")
            
            print(f"\n전체 시스템 재구축 완료!")
            print(f"총 {len(verification_stocks)}개 종목이 8개 전략으로 분류되었습니다.")
            print("\n이제 모니터링 화면에서 실제 종목명과 전략명이 정확히 표시됩니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    complete_system_reset()