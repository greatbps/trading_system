#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Analysis Engine Test
"""

import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_enhanced_analysis():
    """향상된 분석 엔진 테스트"""
    print("Enhanced Analysis Engine Test")
    print("=" * 40)
    
    try:
        # 필요한 컴포넌트 임포트 및 초기화
        from config import Config
        from data_collectors.kis_collector import KISCollector
        from analyzers.analysis_engine import AnalysisEngine
        
        config = Config()
        collector = KISCollector(config)
        
        # 향상된 분석 엔진 초기화
        engine = AnalysisEngine(config, collector)
        print("Enhanced AnalysisEngine initialized successfully")
        
        # 테스트용 샘플 데이터
        test_symbol = "005930"
        test_name = "삼성전자"
        test_stock_data = {
            'symbol': test_symbol,
            'name': test_name,
            'current_price': 70000,
            'change_rate': 2.5,
            'volume': 1000000,
            'market_cap': 400000000
        }
        
        # 종합 분석 실행
        print(f"\nRunning comprehensive analysis for {test_symbol} ({test_name})...")
        result = await engine.analyze_comprehensive(
            symbol=test_symbol,
            name=test_name,
            stock_data=test_stock_data,
            strategy="momentum"
        )
        
        if result:
            print(f"\nAnalysis Results:")
            print(f"  Symbol: {result.get('symbol')}")
            print(f"  Name: {result.get('name')}")
            print(f"  Comprehensive Score: {result.get('comprehensive_score')}")
            print(f"  Recommendation: {result.get('recommendation')}")
            print(f"  Strategy Used: {result.get('strategy_used')}")
            print(f"  Confidence Level: {result.get('confidence_level')}")
            print(f"  Risk Assessment: {result.get('risk_assessment')}")
            print(f"  Execution Time: {result.get('execution_time_seconds')}s")
            
            # 점수 세부사항 출력
            score_details = result.get('score_details', {})
            if score_details:
                print(f"\nScore Details:")
                print(f"  Base Score: {score_details.get('base_score')}")
                print(f"  Synergy Bonus: {score_details.get('synergy_bonus')}")
                print(f"  Consistency Bonus: {score_details.get('consistency_bonus')}")
                
                individual_scores = score_details.get('individual_scores', {})
                print(f"  Individual Scores:")
                for key, score in individual_scores.items():
                    print(f"    {key}: {score}")
            
            print("\nEnhanced analysis completed successfully!")
            return True
        else:
            print("Analysis failed - no result returned")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_enhanced_analysis())
    print(f"\nTest Result: {'PASS' if result else 'FAIL'}")