#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 임포트 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing imports...")

try:
    from monitoring.realtime_monitoring_handler import RealtimeMonitoringHandler
    print("[PASS] RealtimeMonitoringHandler imported successfully")
except Exception as e:
    print(f"[FAIL] RealtimeMonitoringHandler import failed: {e}")

try:
    from utils.realtime_display import RealtimeDisplay, DisplayMode, UpdateFrequency
    print("[PASS] RealtimeDisplay components imported successfully")
except Exception as e:
    print(f"[FAIL] RealtimeDisplay import failed: {e}")

try:
    from data_collectors.bulk_realtime_collector import BulkRealtimeCollector, CollectionMode
    print("[PASS] BulkRealtimeCollector components imported successfully")
except Exception as e:
    print(f"[FAIL] BulkRealtimeCollector import failed: {e}")

try:
    from data_collectors.memory_optimized_storage import MemoryOptimizedStorage
    print("[PASS] MemoryOptimizedStorage imported successfully")
except Exception as e:
    print(f"[FAIL] MemoryOptimizedStorage import failed: {e}")

print("\n[INFO] All core components import test completed!")