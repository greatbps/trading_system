#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/auto_trading_daemon.py

백그라운드 자동매매 데몬 - 50만원 계좌 안전 매매
"""

import asyncio
import sys
import signal
import os
from datetime import datetime, time
from core.trading_system import TradingSystem
import config

class AutoTradingDaemon:
    """백그라운드 자동매매 데몬"""
    
    def __init__(self):
        self.config = config.Config()
        self.system = None
        self.handler = None
        self.running = False
        
    async def initialize(self):
        """시스템 초기화 및 자동 활성화"""
        print(f"[{datetime.now()}] Auto Trading Daemon Starting...")
        print("Initializing system components...")
        
        self.system = TradingSystem()
        await self.system.initialize_components()
        self.handler = self.system.auto_trading_handler
        
        print(f"[{datetime.now()}] System Initialized")
        
        # 실시간 잔고 기반 동적 한도 표시
        try:
            limits = await self.handler.executor.update_dynamic_limits()
            print(f"[{datetime.now()}] Dynamic Limits Updated:")
            print(f"  Current Balance: {limits['current_balance']:,}원")
            print(f"  Max Position per Stock: {limits['max_position_size']:,}원 ({self.config.trading.MAX_POSITION_SIZE_PCT*100:.0f}%)")
            print(f"  Daily Loss Limit: {limits['max_daily_loss']:,}원 ({self.config.trading.MAX_DAILY_LOSS_PCT*100:.0f}%)")
        except Exception as e:
            print(f"[{datetime.now()}] Failed to get dynamic limits: {e}")
        
        # 장시간이면 즉시 자동매매 시작
        if self.is_market_open():
            print(f"[{datetime.now()}] Market is OPEN - Auto-starting trading...")
            await self.start_trading()
        else:
            print(f"[{datetime.now()}] Market is CLOSED - Waiting for market open...")
        
    def is_market_open(self):
        """장 시간 확인 (09:00-15:30)"""
        now = datetime.now().time()
        market_open = time(9, 0)
        market_close = time(15, 30)
        
        # 주말 확인 (0=월요일, 6=일요일)
        weekday = datetime.now().weekday()
        if weekday >= 5:  # 토요일(5), 일요일(6)
            return False
            
        return market_open <= now <= market_close
    
    async def start_trading(self):
        """자동매매 시작 - 모니터링과 트레이딩 모두 자동 활성화"""
        print(f"[{datetime.now()}] Starting Auto Trading System...")
        
        # 1. 모니터링 시작
        if not self.handler.auto_trader.is_monitoring:
            print(f"[{datetime.now()}] → Starting Monitoring...")
            await self.handler._start_monitoring()
        else:
            print(f"[{datetime.now()}] → Monitoring already running")
            
        # 2. 트레이딩 모드 활성화
        if not self.handler.executor.is_trading_enabled():
            print(f"[{datetime.now()}] → Enabling Trading Mode...")
            self.handler.executor.enable_trading()
        else:
            print(f"[{datetime.now()}] → Trading Mode already enabled")
            
        print(f"[{datetime.now()}] [OK] AUTO TRADING FULLY ACTIVE")
        print(f"[{datetime.now()}] → Monitoring: RUNNING")
        print(f"[{datetime.now()}] → Trading: ENABLED") 
        print(f"[{datetime.now()}] → Stocks: 8 monitored")
        
        # 실시간 한도 표시
        try:
            limits = await self.handler.executor.update_dynamic_limits()
            print(f"[{datetime.now()}] → Max per stock: {limits['max_position_size']:,}원")
            print(f"[{datetime.now()}] → Daily loss limit: {limits['max_daily_loss']:,}원")
        except Exception as e:
            print(f"[{datetime.now()}] → Using default limits (API error: {e})")
        
    async def stop_trading(self):
        """자동매매 중지"""
        if self.handler.auto_trader.is_monitoring:
            print(f"[{datetime.now()}] Stopping Auto Trading...")
            await self.handler._stop_monitoring()
            
        print(f"[{datetime.now()}] Auto Trading Stopped")
        
    async def run_daemon(self):
        """데몬 메인 루프"""
        await self.initialize()
        self.running = True
        
        print(f"[{datetime.now()}] Daemon Started - Auto Trading Active")
        
        while self.running:
            try:
                if self.is_market_open():
                    # 장 시간 - 자동매매가 꺼져있으면 다시 켜기
                    if not self.handler.auto_trader.is_monitoring or not self.handler.executor.is_trading_enabled():
                        print(f"[{datetime.now()}] Restarting auto trading...")
                        await self.start_trading()
                    
                    # 5분마다 상태 체크 및 유지
                    await asyncio.sleep(300)
                    
                else:
                    # 장 마감 - 자동매매 중지 (수동으로만 중지 가능)
                    if self.handler.auto_trader.is_monitoring:
                        await self.stop_trading()
                        
                    # 1분마다 장 시간 체크
                    await asyncio.sleep(60)
                    
            except Exception as e:
                print(f"[{datetime.now()}] Error: {e}")
                # 오류 발생해도 계속 실행
                await asyncio.sleep(60)
                
        print(f"[{datetime.now()}] Daemon Stopped")
        
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"\n[{datetime.now()}] Received signal {signum}, stopping daemon...")
        self.running = False

async def main():
    """메인 함수"""
    daemon = AutoTradingDaemon()
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, daemon.signal_handler)
    signal.signal(signal.SIGTERM, daemon.signal_handler)
    
    try:
        await daemon.run_daemon()
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Keyboard interrupt received")
    finally:
        if daemon.handler and daemon.handler.auto_trader.is_monitoring:
            await daemon.stop_trading()

if __name__ == "__main__":
    print("=== AUTO TRADING DAEMON ===")
    print("50만원 계좌 안전 자동매매 시스템")
    print("Ctrl+C로 중지 가능")
    print("=" * 30)
    
    asyncio.run(main())