#!/usr/bin/env python3
"""
현재 시스템 영향도 분석 - 시간대별 자동 전략 시스템 추가를 위한 사전 분석
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

def analyze_current_system():
    """현재 시스템 구조 및 영향도 분석"""
    print("=== 현재 시스템 영향도 분석 ===")
    
    try:
        from database.database_manager import DatabaseManager
        from database.models import MonitoringStock
        from config import Config
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("[OK] 기본 시스템 분석 시작")
        
        # 1. 현재 모니터링 시스템 분석
        print(f"\n[1] 현재 모니터링 시스템 상태:")
        
        with db_manager.get_session() as session:
            # 전체 모니터링 주식
            total_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.monitoring_active == True
            ).count()
            
            # 전략별 분포
            from sqlalchemy import func
            strategy_stats = session.query(
                MonitoringStock.strategy_name,
                func.count(MonitoringStock.id).label('count'),
                func.min(MonitoringStock.created_at).label('first_added'),
                func.max(MonitoringStock.created_at).label('last_added')
            ).filter(
                MonitoringStock.monitoring_active == True
            ).group_by(MonitoringStock.strategy_name).all()
            
            print(f"  총 모니터링 종목: {total_stocks}개")
            print(f"  활성 전략 수: {len(strategy_stats)}개")
            
            for strategy, count, first_added, last_added in strategy_stats:
                first_str = first_added.strftime('%m-%d %H:%M') if first_added else 'N/A'
                last_str = last_added.strftime('%m-%d %H:%M') if last_added else 'N/A'
                print(f"    {strategy}: {count}개 (최초: {first_str}, 최근: {last_str})")
        
        # 2. 현재 전략 설정 분석
        print(f"\n[2] 전략 설정 분석:")
        
        if hasattr(config.trading, 'HTS_CONDITION_NAMES'):
            strategies = config.trading.HTS_CONDITION_NAMES
            print(f"  설정된 전략: {len(strategies)}개")
            
            strategy_mapping = {}
            for i, (strategy_name, condition) in enumerate(strategies.items(), 1):
                strategy_mapping[i] = {
                    'name': strategy_name,
                    'condition': condition,
                    'current_usage': 'Unknown'
                }
                print(f"    {i}. {strategy_name} -> {condition}")
            
            print(f"\n  전략별 현재 사용률:")
            for strategy, count, _, _ in strategy_stats:
                usage_rate = (count / total_stocks) * 100 if total_stocks > 0 else 0
                print(f"    {strategy}: {usage_rate:.1f}% ({count}/{total_stocks})")
        
        # 3. 시간별 활동 패턴 분석
        print(f"\n[3] 시간별 활동 패턴 분석:")
        
        with db_manager.get_session() as session:
            # 시간대별 종목 추가 패턴 (최근 7일)
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            
            hour_stats = session.query(
                func.extract('hour', MonitoringStock.created_at).label('hour'),
                func.count(MonitoringStock.id).label('count')
            ).filter(
                MonitoringStock.created_at >= week_ago
            ).group_by(func.extract('hour', MonitoringStock.created_at)).all()
            
            print(f"  최근 7일 시간대별 종목 추가 패턴:")
            if hour_stats:
                for hour, count in sorted(hour_stats):
                    if hour is not None:
                        print(f"    {int(hour):02d}시: {count}개")
            else:
                print("    최근 활동 없음")
        
        # 4. 현재 자동화 시스템 분석
        print(f"\n[4] 현재 자동화 시스템 상태:")
        
        # DatabaseAutoTrader 관련 파일 확인
        auto_trader_file = Path("D:/trading_system/trading/db_auto_trader.py")
        if auto_trader_file.exists():
            print(f"  [OK] DatabaseAutoTrader 존재")
            
            # 모니터링 주기 확인
            with open(auto_trader_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'monitoring_interval' in content:
                    print(f"  [OK] 모니터링 주기 설정 확인됨")
                    
                    # 주기 추출 (간단한 패턴 매칭)
                    import re
                    pattern = r'monitoring_interval\s*=\s*(\d+)'
                    match = re.search(pattern, content)
                    if match:
                        interval = match.group(1)
                        print(f"    현재 모니터링 주기: {interval}초")
        
        # 5. 안전한 확장 지점 식별
        print(f"\n[5] 안전한 확장 지점 식별:")
        
        extension_points = [
            {
                'name': '시간대별 스케줄러 추가',
                'location': '새로운 모듈 생성',
                'risk': 'LOW',
                'description': '기존 시스템과 독립적인 스케줄러 모듈'
            },
            {
                'name': '전략 자동 선택 로직',
                'location': '새로운 전략 매니저 클래스',
                'risk': 'LOW', 
                'description': '기존 전략 시스템에 영향 없이 선택 로직만 추가'
            },
            {
                'name': '모니터링 목록 자동 관리',
                'location': 'DatabaseAutoTrader 확장',
                'risk': 'MEDIUM',
                'description': '기존 모니터링 로직에 자동 추가/제거 기능 확장'
            },
            {
                'name': '리밸런싱 자동화',
                'location': 'SmartRebalancer 확장',
                'risk': 'MEDIUM',
                'description': '기존 리밸런싱 로직에 자동 트리거 추가'
            }
        ]
        
        for point in extension_points:
            risk_color = {
                'LOW': '[GREEN]',
                'MEDIUM': '[YELLOW]', 
                'HIGH': '[RED]'
            }.get(point['risk'], '[WHITE]')
            
            print(f"    {risk_color} {point['name']}")
            print(f"      위치: {point['location']}")
            print(f"      위험도: {point['risk']}")
            print(f"      설명: {point['description']}")
            print()
        
        # 6. 권장 개발 순서
        print(f"[6] 권장 개발 순서 (안전성 우선):")
        development_phases = [
            "Phase 1: 시간대별 전략 매핑 테이블 설계 및 구현",
            "Phase 2: 시간대별 스케줄러 모듈 생성 (독립 실행)",
            "Phase 3: 전략 자동 선택 로직 구현 및 테스트",
            "Phase 4: 종목 추출 자동화 모듈 구현",
            "Phase 5: 모니터링 자동 추가 기능 통합",
            "Phase 6: 리밸런싱 자동화 연동",
            "Phase 7: 통합 테스트 및 모니터링"
        ]
        
        for i, phase in enumerate(development_phases, 1):
            print(f"    {i}. {phase}")
        
        print(f"\n[SUCCESS] 현재 시스템 영향도 분석 완료")
        print(f"[RECOMMENDATION] 낮은 위험도부터 단계별 구현 권장")
        
        return {
            'total_monitoring_stocks': total_stocks,
            'active_strategies': len(strategy_stats),
            'strategy_distribution': dict([(s[0], s[1]) for s in strategy_stats]),
            'extension_points': extension_points,
            'development_phases': development_phases
        }
        
    except Exception as e:
        print(f"[ERROR] 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = analyze_current_system()
    if result:
        print(f"\n[SUMMARY] 분석 결과 요약:")
        print(f"  현재 모니터링: {result['total_monitoring_stocks']}개 종목")
        print(f"  활성 전략: {result['active_strategies']}개")
        print(f"  확장 지점: {len(result['extension_points'])}개 식별")
        print(f"  개발 단계: {len(result['development_phases'])}단계 권장")