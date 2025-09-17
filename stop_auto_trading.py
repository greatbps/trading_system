#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/stop_auto_trading.py

자동매매 수동 중지 스크립트
"""

import asyncio
import sys
from datetime import datetime
from core.trading_system import TradingSystem
import config

async def stop_auto_trading():
    """자동매매 수동 중지"""
    print(f"[{datetime.now()}] Manual Auto Trading Stop")
    print("=" * 50)
    
    try:
        # 시스템 초기화
        config_instance = config.Config()
        system = TradingSystem()
        await system.initialize_components()
        
        handler = system.auto_trading_handler
        
        # 현재 상태 확인
        monitoring_status = "RUNNING" if handler.auto_trader.is_monitoring else "STOPPED"
        trading_status = "ENABLED" if handler.executor.is_trading_enabled() else "DISABLED"
        
        print(f"Current Status:")
        print(f"  Monitoring: {monitoring_status}")
        print(f"  Trading: {trading_status}")
        print()
        
        # 사용자 확인
        if monitoring_status == "STOPPED" and trading_status == "DISABLED":
            print("Auto trading is already stopped.")
            return
            
        print("Do you want to stop auto trading? (y/N): ", end="")
        choice = input().strip().lower()
        
        if choice in ['y', 'yes']:
            print(f"\n[{datetime.now()}] Stopping auto trading...")
            
            # 모니터링 중지
            if handler.auto_trader.is_monitoring:
                print("→ Stopping monitoring...")
                await handler._stop_monitoring()
                
            # 트레이딩 비활성화
            if handler.executor.is_trading_enabled():
                print("→ Disabling trading...")
                handler.executor.disable_trading()
                
            print(f"[{datetime.now()}] [OK] Auto trading stopped successfully!")
            print("→ Monitoring: STOPPED")
            print("→ Trading: DISABLED")
            
        else:
            print("Operation cancelled.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("=== MANUAL AUTO TRADING STOP ===")
    asyncio.run(stop_auto_trading())