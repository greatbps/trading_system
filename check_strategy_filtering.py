#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
# Set UTF-8 encoding for console output
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
"""
HTS 조건검색 전략별 필터링 결과 확인
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def check_strategy_filtering():
    """전략별 HTS 조건검색 필터링 결과 확인"""
    print("=" * 80)
    print("HTS 조건검색 전략별 필터링 결과 분석")
    print("=" * 80)
    
    try:
        from config import Config
        from data_collectors.kis_collector import KISCollector
        from strategies.strategy_definitions import STRATEGY_INFO_MAP, StrategyType
        
        config = Config()
        
        print(f"[INFO] 8가지 전략별 HTS 조건검색 결과 확인...")
        print("-" * 80)
        
        # 전략별 조건검색 실행
        total_filtered = 0
        strategy_results = {}
        
        # KISCollector를 async context manager로 사용
        async with KISCollector(config) as kis_collector:
            for strategy_type in StrategyType:
                strategy_info = STRATEGY_INFO_MAP[strategy_type]
                strategy_name = strategy_info.name
                strategy_id = strategy_info.strategy_id
                
                print(f"\n[STRATEGY] [{strategy_id}번] {strategy_name} 전략 조건검색 중...")
                print(f"   설명: {strategy_info.description}")
                print(f"   시간프레임: {strategy_info.timeframe}")
                print(f"   리스크: {strategy_info.risk_level}")
                print(f"   예상 승률: {strategy_info.expected_win_rate*100:.1f}%")
                
                try:
                    # HTS 조건검색 실행 (조건번호는 전략 ID 사용)
                    condition_results = await kis_collector.get_stocks_by_condition(
                        condition_id=str(strategy_id),  # 1-8번 사용
                        condition_name=strategy_name
                    )
                
                    if condition_results:
                        filtered_count = len(condition_results)
                        total_filtered += filtered_count
                        strategy_results[strategy_name] = {
                            'count': filtered_count,
                            'stocks': condition_results[:5],  # 상위 5개만 저장
                            'strategy_info': strategy_info
                        }
                        
                        print(f"   [SUCCESS] 필터링 결과: {filtered_count}개 종목 발견")
                        
                        if filtered_count > 0:
                            print(f"   상위 5개 종목:")
                            for i, stock in enumerate(condition_results[:5], 1):
                                symbol = stock.get('code', 'N/A')
                                name = stock.get('name', 'N/A')
                                print(f"      {i}. {symbol}: {name}")
                        else:
                            print(f"   [WARNING] 해당 조건에 맞는 종목이 없습니다")
                            
                    else:
                        print(f"   [ERROR] 조건검색 실패 또는 결과 없음")
                        strategy_results[strategy_name] = {
                            'count': 0,
                            'stocks': [],
                            'strategy_info': strategy_info
                        }
                    
                except Exception as e:
                    print(f"   [ERROR] 오류 발생: {e}")
                    strategy_results[strategy_name] = {
                        'count': 0,
                        'stocks': [],
                        'error': str(e),
                        'strategy_info': strategy_info
                    }
                
                # Rate limiting을 위한 대기
                await asyncio.sleep(1.0)
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("[SUMMARY] 전략별 필터링 결과 요약")
        print("=" * 80)
        
        print(f"{'전략명':<20} {'필터링 종목수':<12} {'승률':<8} {'리스크':<10} {'시간프레임':<10}")
        print("-" * 80)
        
        for strategy_name, result in strategy_results.items():
            count = result['count']
            strategy_info = result['strategy_info']
            win_rate = f"{strategy_info.expected_win_rate*100:.1f}%"
            risk_level = strategy_info.risk_level
            timeframe = strategy_info.timeframe
            
            print(f"{strategy_name:<20} {count:<12} {win_rate:<8} {risk_level:<10} {timeframe:<10}")
        
        print("-" * 80)
        print(f"[TOTAL] 총 필터링된 종목 수: {total_filtered}개")
        print(f"[AVERAGE] 평균 전략별 종목 수: {total_filtered/8:.1f}개")
        
        # 가장 많은 종목이 나온 전략
        if strategy_results:
            max_strategy = max(strategy_results.items(), key=lambda x: x[1]['count'])
            min_strategy = min(strategy_results.items(), key=lambda x: x[1]['count'])
            
            print(f"\n[MAX] 가장 많은 종목 필터링: {max_strategy[0]} ({max_strategy[1]['count']}개)")
            print(f"[MIN] 가장 적은 종목 필터링: {min_strategy[0]} ({min_strategy[1]['count']}개)")
        
        # 문제 진단
        print("\n" + "=" * 80)
        print("[DIAGNOSIS] 시스템 진단")
        print("=" * 80)
        
        zero_count = sum(1 for r in strategy_results.values() if r['count'] == 0)
        if zero_count > 0:
            print(f"[WARNING] 종목이 0개인 전략: {zero_count}개")
            print("   -> HTS 조건식이 제대로 설정되었는지 확인 필요")
        
        if total_filtered < 50:
            print("[WARNING] 전체 필터링된 종목 수가 적습니다.")
            print("   -> 조건식 완화 또는 다양한 조건 추가 검토 필요")
        
        if total_filtered > 500:
            print("[WARNING] 전체 필터링된 종목 수가 너무 많습니다.")
            print("   -> 조건식 강화 또는 추가 필터링 로직 필요")
        
        print(f"\n[COMPLETE] 분석 완료!")
        
    except Exception as e:
        print(f"[ERROR] 전체 분석 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_strategy_filtering())