#!/usr/bin/env python3
"""
간단한 백테스팅 테스트
"""

import asyncio
import logging
from datetime import datetime, timedelta
from backtesting.backtesting_engine import BacktestingEngine

# 로깅 설정
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')

async def test_backtest():
    """백테스팅 테스트"""
    print("Backtest test started...")

    # 백테스팅 엔진 생성
    engine = BacktestingEngine()

    # 테스트 파라미터
    strategy_name = 'momentum'
    start_date = datetime(2025, 8, 1)
    end_date = datetime(2025, 9, 1)  # 1개월간
    symbols = ['005930']  # 삼성전자만
    initial_capital = 1000000.0

    try:
        # 백테스팅 실행
        result = await engine.run_backtest(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            initial_capital=initial_capital,
            use_ai=False  # AI 비활성화로 빠른 테스트
        )

        print(f"\nBacktest completed!")
        print(f"Strategy: {result.strategy_name}")
        print(f"Period: {result.start_date.strftime('%Y-%m-%d')} ~ {result.end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {result.initial_capital:,.0f} KRW")
        print(f"Final Capital: {result.final_capital:,.0f} KRW")
        print(f"Total Return: {result.total_return_pct:.2f}%")
        print(f"Total Trades: {result.metrics.total_trades}")
        print(f"Win Rate: {result.metrics.win_rate:.1f}%")

        if result.trades:
            print(f"\nTrade History:")
            for i, trade in enumerate(result.trades[:5]):  # 처음 5개만
                print(f"  {i+1}. {trade['date']} {trade['action']} {trade['symbol']} "
                      f"{trade['quantity']} shares @ {trade['price']:,.0f} KRW")

        return True

    except Exception as e:
        print(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_backtest())
    print(f"\nTest {'SUCCESS' if success else 'FAILED'}!")