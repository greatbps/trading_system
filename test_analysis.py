#!/usr/bin/env python3
"""
4번 메뉴 종합 분석 기능 테스트 스크립트
"""

import asyncio
import sys
sys.path.append('.')

async def test_comprehensive_analysis():
    """4번 메뉴 종합 분석 기능 테스트"""
    print("=== 4번 메뉴 종합 분석 기능 테스트 ===")
    
    try:
        # 시스템 초기화
        from core.trading_system import TradingSystem
        from core.analysis_handlers import AnalysisHandlers
        
        system = TradingSystem()
        await system.initialize_components()
        print("[PASS] TradingSystem 초기화 완료")
        
        # AnalysisEngine 직접 사용
        analysis_engine = system.analysis_engine
        print("[PASS] AnalysisEngine 초기화 완료")
        
        # 테스트용 종목 데이터 (037270 - YG PLUS)
        test_symbol = "037270"
        test_name = "YG PLUS"
        
        print(f"\n[START] {test_symbol}({test_name}) comprehensive analysis test...")
        
        # 종목 기본 정보 수집
        stock_data = await system.data_collector.get_stock_info(test_symbol)
        if not stock_data:
            stock_data = {
                'symbol': test_symbol,
                'name': test_name,
                'current_price': 10000,  # 임시값
                'change_rate': 0.0,
                'volume': 100000
            }
        
        # 종합 분석 실행
        result = await analysis_engine.analyze_comprehensive(test_symbol, test_name, stock_data)
        
        if result:
            print(f"\n[SUCCESS] {test_symbol} analysis completed!")
            print(f"   - Comprehensive Score: {result.get('comprehensive_score', 'N/A')}")
            print(f"   - Recommendation: {result.get('recommendation', 'N/A')}")
            print(f"   - Technical Score: {result.get('technical_score', 'N/A')}")
            print(f"   - Sentiment Score: {result.get('sentiment_score', 'N/A')}")
            print(f"   - Supply/Demand Score: {result.get('supply_demand_score', 'N/A')}")
            print(f"   - Chart Pattern Score: {result.get('chart_pattern_score', 'N/A')}")
            print(f"   - Confidence Level: {result.get('confidence_level', 'N/A')}")
            print(f"   - Risk Assessment: {result.get('risk_assessment', 'N/A')}")
            print(f"   - Execution Time: {result.get('execution_time_seconds', 'N/A')}s")
        else:
            print(f"[FAILED] {test_symbol} analysis failed")
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 정리
        try:
            await system.cleanup()
            print("\n[PASS] 시스템 정리 완료")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_comprehensive_analysis())