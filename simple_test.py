#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 테스트 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    print("Import test starting...")
    
    try:
        # Test core imports
        from config import Config
        print("Config import: OK")
        
        from database.models import TradeExecution
        print("TradeExecution import: OK")
        
        from analyzers.analysis_engine import AnalysisEngine
        print("AnalysisEngine import: OK")
        
        from strategies.vwap_strategy import VwapStrategy
        print("VwapStrategy import: OK")
        
        from strategies import VwapStrategy as VwapFromInit
        print("VwapStrategy from __init__ import: OK")
        
        from strategies.eod_strategy import EodStrategy
        print("EodStrategy import: OK")
        
        return True
        
    except Exception as e:
        print(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_init():
    print("\nBasic initialization test...")
    
    try:
        from config import Config
        config = Config()
        print("Config initialization: OK")
        
        from data_collectors.kis_collector import KISCollector
        collector = KISCollector(config)
        print("KISCollector initialization: OK")
        
        from analyzers.analysis_engine import AnalysisEngine
        engine = AnalysisEngine(config, collector)
        print("AnalysisEngine with data_collector: OK")
        
        return True
        
    except Exception as e:
        print(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing system fixes...")
    print("=" * 40)
    
    import_ok = test_imports()
    init_ok = test_basic_init()
    
    print("\n" + "=" * 40)
    print("Results:")
    print(f"Imports: {'PASS' if import_ok else 'FAIL'}")
    print(f"Initialization: {'PASS' if init_ok else 'FAIL'}")
    
    if import_ok and init_ok:
        print("\nAll fixes working correctly!")
    else:
        print("\nSome issues remain.")