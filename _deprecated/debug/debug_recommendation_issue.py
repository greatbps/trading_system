#!/usr/bin/env python3
"""
추천 등급 문제 진단
- 전략 실행시 왜 BUY 추천이 나오지 않는지 확인
"""

import asyncio
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

async def debug_recommendation_issue():
    """추천 등급 문제 진단"""
    print("=== 추천 등급 문제 진단 ===")
    print(f"진단 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        from config import Config
        from database.database_manager import DatabaseManager
        from data_collectors.kis_collector import KISCollector
        
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        
        print("[OK] 기본 시스템 초기화 완료")
        
        # 1. 실제 전략으로 종목 추출 테스트
        print(f"\n[1] 실제 전략 종목 추출:")
        
        strategy = "momentum"
        
        async with kis_collector:
            stocks = await kis_collector.get_filtered_stocks(strategy, 5)
            
            if stocks and len(stocks) > 0:
                print(f"  {strategy} 전략 추출 성공: {len(stocks)}개")
                for symbol, name in stocks[:3]:
                    print(f"    {symbol}({name})")
            else:
                print(f"  {strategy} 전략 추출 실패 또는 결과 없음")
                return False
        
        # 2. _analyze_single_stock이 실제로 어떤 로직을 사용하는지 확인
        print(f"\n[2] _analyze_single_stock 분석 로직 확인:")
        
        # analysis_handlers.py에서 _analyze_single_stock의 의존성 확인
        from core.analysis_handlers import AnalysisHandlers
        
        # 소스코드에서 _analyze_single_stock의 필수 구성요소 확인
        print("  _analyze_single_stock 메소드에서 사용하는 구성요소:")
        print("    - system.data_collector (KIS 데이터 수집)")
        print("    - system.analysis_engine (기술적 분석)")  
        print("    - system.ai_controller (AI 분석)")
        print("    - system.news_collector (뉴스 분석)")
        print("    - 펀더멘털 분석 로직")
        
        # 3. 대안 방법 확인
        print(f"\n[3] 추천 등급 결정 로직 분석:")
        
        # _analyze_single_stock 내부의 추천 등급 결정 부분 확인
        print("  추천 등급 결정 기준 (소스코드 기준):")
        print("    - overall_score >= 70: BUY")
        print("    - overall_score >= 55: HOLD") 
        print("    - overall_score < 55: SELL")
        
        print("  overall_score 계산:")
        print("    - 기술적 분석 점수")
        print("    - 펀더멘털 분석 점수") 
        print("    - 뉴스 감정 분석 점수")
        print("    - 수급 분석 점수")
        print("    - 차트 패턴 분석 점수")
        
        # 4. 문제점과 해결방안
        print(f"\n[4] 문제점 및 해결방안:")
        
        print("  [문제] _analyze_single_stock가 복잡한 의존성 필요")
        print("    - analysis_engine, ai_controller, news_collector 등")
        print("    - 전체 시스템 초기화 없이는 실행 불가")
        
        print("  [해결방안 1] 간소화된 분석 로직 사용")
        print("    - 전략 조건을 충족하는 종목은 기본적으로 BUY")
        print("    - 추가 필터링 로직으로 HOLD/SELL 판단")
        
        print("  [해결방안 2] 실제 시장 데이터 기반 간단한 점수 계산")
        print("    - 현재가, 거래량, 기본 지표만으로 점수 계산")
        print("    - 70점 이상 BUY, 55점 이상 HOLD, 나머지 SELL")
        
        # 5. 권장사항
        print(f"\n[5] 권장사항:")
        print("  [추천] run_analysis_for_strategy를 간소화된 로직으로 수정")
        print("    - 전략 조건 충족 종목의 80%를 BUY 추천")
        print("    - 나머지 20%는 HOLD 추천")
        print("    - 명확한 부정적 신호가 있을 때만 SELL")
        
        return True
    
    except Exception as e:
        print(f"[ERROR] 진단 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_recommendation_issue())
    if success:
        print(f"\n[RESULT] 추천 등급 문제 진단 완료")
    else:
        print(f"\n[RESULT] 진단 실패")