#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트 스크립트: 수정사항 검증
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_imports():
    """모든 임포트 테스트"""
    print("임포트 테스트 시작...")
    
    try:
        # 설정 임포트
        from config import Config
        print("Config 임포트 성공")
        
        # 데이터베이스 모델 임포트
        from database.models import TradeExecution, Trade, Stock
        print("TradeExecution 모델 임포트 성공")
        
        # 분석 엔진 임포트
        from analyzers.analysis_engine import AnalysisEngine
        print("AnalysisEngine 임포트 성공")
        
        # 전략 임포트
        from strategies.vwap_strategy import VwapStrategy
        print("VwapStrategy 임포트 성공")
        
        from strategies import VwapStrategy as VwapStrategyFromInit
        print("VwapStrategy from __init__ 임포트 성공")
        
        # 데이터 수집기 임포트
        from data_collectors.kis_collector import KISCollector
        print("KISCollector 임포트 성공")
        
        return True
        
    except Exception as e:
        print(f"임포트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_initialization():
    """초기화 테스트"""
    print("\n초기화 테스트 시작...")
    
    try:
        # 설정 초기화
        from config import Config
        config = Config()
        print("Config 초기화 성공")
        
        # 데이터 수집기 초기화
        from data_collectors.kis_collector import KISCollector
        collector = KISCollector(config)
        print("KISCollector 초기화 성공")
        
        # 분석 엔진 초기화 (data_collector와 함께)
        from analyzers.analysis_engine import AnalysisEngine
        engine = AnalysisEngine(config, collector)
        print("AnalysisEngine 초기화 성공 (data_collector 포함)")
        
        # 전략 초기화
        from strategies.vwap_strategy import VwapStrategy
        strategy = VwapStrategy(config)
        print("VwapStrategy 초기화 성공")
        
        return True
        
    except Exception as e:
        print(f"초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트 함수"""
    print("수정사항 검증 테스트")
    print("=" * 50)
    
    # 임포트 테스트
    import_success = await test_imports()
    
    # 초기화 테스트
    init_success = await test_initialization()
    
    print("\n" + "=" * 50)
    print("테스트 결과:")
    print(f"  • 임포트 테스트: {'성공' if import_success else '실패'}")
    print(f"  • 초기화 테스트: {'성공' if init_success else '실패'}")
    
    if import_success and init_success:
        print("\n모든 수정사항이 정상적으로 적용되었습니다!")
        return True
    else:
        print("\n일부 문제가 남아있습니다.")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)