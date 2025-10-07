#!/usr/bin/env python3
"""
전략별 종목 추출 문제 진단 스크립트
"""

import asyncio
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

async def debug_strategy_extraction():
    """전략별 종목 추출 문제 진단"""
    print("=== 전략별 종목 추출 문제 진단 ===")
    print(f"진단 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        from config import Config
        from data_collectors.kis_collector import KISCollector
        
        config = Config()
        print("[OK] Config 로드 성공")
        
        # 1. 설정 확인
        print(f"\n[1] HTS 조건검색 설정 확인:")
        
        if hasattr(config.trading, 'HTS_CONDITION_NAMES'):
            hts_names = config.trading.HTS_CONDITION_NAMES
            print(f"  HTS_CONDITION_NAMES: {len(hts_names)}개")
            for strategy, condition in hts_names.items():
                print(f"    {strategy} -> {condition}")
        else:
            print(f"  [ERROR] HTS_CONDITION_NAMES 설정 없음")
            return False
        
        if hasattr(config.trading, 'HTS_CONDITIONAL_SEARCH_IDS'):
            hts_ids = config.trading.HTS_CONDITIONAL_SEARCH_IDS
            print(f"  HTS_CONDITIONAL_SEARCH_IDS: {len(hts_ids)}개")
            for strategy, condition_id in hts_ids.items():
                print(f"    {strategy} -> {condition_id}")
        else:
            print(f"  [WARNING] HTS_CONDITIONAL_SEARCH_IDS 설정 없음")
        
        # 2. KIS API 연결 테스트
        print(f"\n[2] KIS API 연결 테스트:")
        
        kis_collector = KISCollector(config)
        
        async with kis_collector:
            print(f"  [OK] KIS 연결 성공")
            
            # 3. HTS 조건식 목록 조회 테스트
            print(f"\n[3] HTS 조건식 목록 조회:")
            
            try:
                conditions = await kis_collector.get_hts_condition_list()
                if conditions:
                    print(f"  [OK] HTS 조건식 {len(conditions)}개 조회됨:")
                    for i, condition in enumerate(conditions[:5], 1):  # 상위 5개만
                        print(f"    {i}. {condition.get('id')} - {condition.get('name')}")
                    if len(conditions) > 5:
                        print(f"    ... 및 {len(conditions)-5}개 더")
                else:
                    print(f"  [ERROR] HTS 조건식 조회 결과 없음")
                    return False
                    
            except Exception as e:
                print(f"  [ERROR] HTS 조건식 목록 조회 실패: {e}")
                return False
            
            # 4. 각 전략별 종목 추출 테스트
            print(f"\n[4] 전략별 종목 추출 테스트:")
            
            test_strategies = ['momentum', 'breakout', 'vwap']  # 3개 전략만 테스트
            
            for strategy in test_strategies:
                print(f"\n  == {strategy} 전략 테스트 ==")
                
                try:
                    stocks = await kis_collector.get_filtered_stocks(strategy, 5)
                    
                    if stocks is None:
                        print(f"    [ERROR] {strategy}: 설정 오류 (None 반환)")
                        
                        # 설정 매칭 확인
                        target_condition = hts_names.get(strategy)
                        if target_condition:
                            found_condition = next((c for c in conditions if c.get('name') == target_condition), None)
                            if found_condition:
                                print(f"    조건식 매칭: {target_condition} -> ID {found_condition.get('id')} 찾음")
                            else:
                                print(f"    [ISSUE] 조건식 불일치: '{target_condition}'이 HTS에 없음")
                                print(f"    사용 가능한 조건식: {[c.get('name') for c in conditions[:3]]}...")
                        else:
                            print(f"    [ISSUE] config에 {strategy} 설정 없음")
                            
                    elif isinstance(stocks, list):
                        if stocks:
                            print(f"    [OK] {strategy}: {len(stocks)}개 종목 조회 성공")
                            for symbol, name in stocks[:3]:
                                print(f"      {symbol}: {name}")
                        else:
                            print(f"    [INFO] {strategy}: 조건에 맞는 종목 없음 (빈 리스트)")
                    else:
                        print(f"    [ERROR] {strategy}: 예상치 못한 반환값 타입: {type(stocks)}")
                        
                except Exception as e:
                    print(f"    [ERROR] {strategy}: 예외 발생 - {e}")
                    import traceback
                    traceback.print_exc()
            
            # 5. 결론 및 권장사항
            print(f"\n[5] 진단 결과 및 권장사항:")
            
            # config와 HTS 조건식 이름 매칭 확인
            mismatched_strategies = []
            for strategy, target_condition in hts_names.items():
                found = any(c.get('name') == target_condition for c in conditions)
                if not found:
                    mismatched_strategies.append((strategy, target_condition))
            
            if mismatched_strategies:
                print(f"  [CRITICAL] 조건식 이름 불일치 발견:")
                for strategy, condition in mismatched_strategies:
                    print(f"    {strategy}: '{condition}' <- HTS에 없음")
                    
                print(f"\n  [SOLUTION] config.py의 HTS_CONDITION_NAMES 수정 필요:")
                print(f"  실제 HTS 조건식 이름으로 변경:")
                for condition in conditions[:8]:  # 8개 전략에 맞춰
                    print(f"    '{condition.get('name')}'")
                
                return False
            else:
                print(f"  [OK] 모든 조건식 이름이 매칭됨")
                return True
    
    except Exception as e:
        print(f"[ERROR] 진단 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_strategy_extraction())
    if success:
        print(f"\n[RESULT] 진단 완료: 설정 문제 없음")
    else:
        print(f"\n[RESULT] 진단 완료: 설정 수정 필요")