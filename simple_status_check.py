#!/usr/bin/env python3
# -*- coding: utf-8 -*-"""
간단한 매매 상태 확인 (Unicode 이슈 해결)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from config import Config
from trading.executor import TradingExecutor
from trading.db_auto_trader import DatabaseAutoTrader
from data_collectors.kis_collector import KISCollector

async def simple_status_check():
    """현재 매매 상태 간단 확인"""
    config = Config()
    db_manager = DatabaseManager(config)
    kis_collector = KISCollector(config, db_manager)
    executor = TradingExecutor(config, kis_collector, db_manager)
    db_auto_trader = DatabaseAutoTrader(config, kis_collector, executor, db_manager=db_manager)
    
    try:
        print("=" * 80)
        print(f"{''현재 매매 상태 확인'':^80}")
        print("=" * 80)
        
        status_info = await db_auto_trader.get_monitoring_status()
        
        monitoring_stocks = status_info['monitoring_stocks']
        trading_enabled = status_info['trading_enabled']
        
        print(f"\n{''[ 모니터링 중인 종목 ]'':<80}")
        print("-" * 80)
        
        if not monitoring_stocks:
            print(f"{''모니터링 중인 종목이 없습니다.'':^80}")
        else:
            # 헤더 출력
            header = f"{''종목명'':<15} {''전략'':<10} {''현재가'':>10} {''매수가'':>10} {''수익률'':>8} {''목표가'':>10} {''손절가'':>10} {''등록일'':<15}"
            print(header)
            print("-" * 80)

            for symbol, stock_data in monitoring_stocks.items():
                name = stock_data.get('name', symbol)
                strategy = stock_data.get('strategy', 'N/A')
                current_price = f"{stock_data.get('current_price', 0):,}" if stock_data.get('current_price') is not None else 'N/A'
                buy_price = f"{stock_data.get('buy_price', 0):,}" if stock_data.get('buy_price') is not None else 'N/A'
                profit_rate = f"{stock_data.get('profit_rate', 0):.2f}%" if stock_data.get('profit_rate') is not None else 'N/A'
                target_price = f"{stock_data.get('target_price', 0):,}" if stock_data.get('target_price') is not None else 'N/A'
                stop_loss_price = f"{stock_data.get('stop_loss_price', 0):,}" if stock_data.get('stop_loss_price') is not None else 'N/A'
                added_time = stock_data.get('added_time', 'N/A')

                print(f"{name:<15} {strategy:<10} {current_price:>10} {buy_price:>10} {profit_rate:>8} {target_price:>10} {stop_loss_price:>10} {added_time:<15}")
        
        print("-" * 80)
        print(f"{''매매 활성화 상태:'':<20} {'활성화' if trading_enabled else '비활성화':<60}")
        
        print("\n" + "=" * 80)
        print(f"{''목표 달성 상황'':^80}")
        print("=" * 80)
        
        trading_count = status_info['active_count']
        
        print(f"{''  매매 모니터링:'':<20} {trading_count}개 (목표: {db_auto_trader.max_positions}개 이상)")
        
        held_stocks_count = sum(1 for stock_data in monitoring_stocks.values() if stock_data.get('buy_price') is not None and stock_data.get('buy_price') > 0)
        print(f"{''  보유 종목:'':<20} {held_stocks_count}개 (목표: {db_auto_trader.max_positions}개 이하)")

        if trading_count >= db_auto_trader.max_positions:
            print(f"{''  모니터링 목표 달성!'':^80}")
        else:
            print(f"{f''  모니터링 {db_auto_trader.max_positions - trading_count}개 추가 필요'':^80}")
            
        if held_stocks_count <= db_auto_trader.max_positions:
            print(f"{''  보유 종목 목표 달성!'':^80}")
        else:
            print(f"{f''  보유 종목 {held_stocks_count - db_auto_trader.max_positions}개 정리 필요'':^80}")
        
    except Exception as e:
        print(f"상태 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()
        await kis_collector.close()

if __name__ == "__main__":
    asyncio.run(simple_status_check())