#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/strategy_optimizer.py

6번, 7번 전략 파라미터 최적화 실행기
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import Config
from data_collectors.kis_collector import KISCollector
from .signal_based_backtester import SignalBasedBacktester, BacktestResult
from utils.encoding_fix import clean_unicode_emojis


class StrategyOptimizer:
    """전략 파라미터 최적화 실행기"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.console = Console()
        self.backtester = SignalBasedBacktester(config)
        self.kis_collector = None
        
        self.logger.info("✅ Strategy Optimizer 초기화 완료")
    
    async def initialize(self):
        """KIS 데이터 수집기 초기화"""
        try:
            self.kis_collector = KISCollector(self.config)
            await self.kis_collector.initialize()
            self.logger.info("✅ KIS 데이터 수집기 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ KIS 초기화 오류: {e}")
            raise
    
    async def optimize_strategies_6_7(
        self,
        symbols: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """6번, 7번 전략 최적화 실행"""
        try:
            self.console.print("\n🎯 6번(3분봉 스캘핑), 7번(RSI) 전략 파라미터 최적화 시작", style="bold blue")
            
            # 기본 종목 설정
            if symbols is None:
                symbols = ['005930', '000660', '035420', '051910', '068270']  # 대형주 5개
            
            # 백테스팅 기간 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            results = {}
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                
                # 6번 전략 (3분봉 스캘핑) 최적화
                task1 = progress.add_task("6번 전략(3분봉 스캘핑) 최적화 중...", total=None)
                strategy_6_results = await self._optimize_strategy(
                    "scalping_3m", symbols, start_date, end_date, progress, task1
                )
                results['scalping_3m'] = strategy_6_results
                progress.update(task1, description="6번 전략 최적화 완료 ✅")
                
                # 7번 전략 (RSI) 최적화
                task2 = progress.add_task("7번 전략(RSI) 최적화 중...", total=None)
                strategy_7_results = await self._optimize_strategy(
                    "rsi", symbols, start_date, end_date, progress, task2
                )
                results['rsi'] = strategy_7_results
                progress.update(task2, description="7번 전략 최적화 완료 ✅")
            
            # 결과 출력
            await self._display_optimization_results(results)
            
            # 최적화 결과 저장
            await self._save_optimization_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 전략 최적화 오류: {e}")
            self.console.print(f"❌ 최적화 실행 오류: {e}", style="bold red")
            raise
    
    async def _optimize_strategy(
        self,
        strategy_name: str,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        progress: Progress,
        task_id: int
    ) -> Dict[str, Any]:
        """개별 전략 최적화"""
        try:
            strategy_results = {
                'strategy_name': strategy_name,
                'optimization_period': f"{start_date.date()} ~ {end_date.date()}",
                'symbols': symbols,
                'symbol_results': {},
                'best_overall': None,
                'optimization_summary': {}
            }
            
            total_profit = 0
            total_trades = 0
            win_count = 0
            
            for symbol in symbols:
                progress.update(task_id, description=f"{strategy_name} - {symbol} 백테스팅 중...")
                
                try:
                    # 차트 데이터 수집
                    chart_data = await self._get_chart_data(symbol, start_date, end_date)
                    
                    if not chart_data:
                        continue
                    
                    # 백테스팅 실행
                    result = await self.backtester.run_strategy_backtest(
                        strategy_name, symbol, start_date, end_date, chart_data, optimize_params=True
                    )
                    
                    strategy_results['symbol_results'][symbol] = {
                        'result': result,
                        'profit_loss_pct': result.profit_loss_pct,
                        'win_rate': result.win_rate,
                        'total_trades': result.total_trades,
                        'sharpe_ratio': result.sharpe_ratio,
                        'max_drawdown': result.max_drawdown
                    }
                    
                    # 전체 통계 누적
                    total_profit += result.profit_loss_pct
                    total_trades += result.total_trades
                    if result.profit_loss_pct > 0:
                        win_count += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ {symbol} 백테스팅 오류: {e}")
                    continue
            
            # 최고 성과 종목 선정
            if strategy_results['symbol_results']:
                best_symbol = max(
                    strategy_results['symbol_results'].keys(),
                    key=lambda s: strategy_results['symbol_results'][s]['profit_loss_pct']
                )
                strategy_results['best_overall'] = {
                    'symbol': best_symbol,
                    'result': strategy_results['symbol_results'][best_symbol]
                }
            
            # 최적화 요약
            strategy_results['optimization_summary'] = {
                'tested_symbols': len(symbols),
                'successful_symbols': len(strategy_results['symbol_results']),
                'avg_profit_pct': total_profit / max(1, len(strategy_results['symbol_results'])),
                'total_trades': total_trades,
                'symbol_win_rate': (win_count / max(1, len(strategy_results['symbol_results']))) * 100
            }
            
            return strategy_results
            
        except Exception as e:
            self.logger.error(f"❌ {strategy_name} 최적화 오류: {e}")
            return {}
    
    async def _get_chart_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """차트 데이터 수집"""
        try:
            # 임시로 가상 데이터 생성 (실제로는 KIS API에서 수집)
            # 실제 구현에서는 KIS API의 차트 데이터 수집 메서드 사용
            days = (end_date - start_date).days
            chart_data = []
            
            base_price = 50000  # 기준 가격
            
            for i in range(days * 288):  # 3분봉 기준 (하루 288개)
                timestamp = start_date + timedelta(minutes=i * 3)
                
                # 가상 데이터 생성 (실제로는 KIS API 데이터 사용)
                price_change = (hash(f"{symbol}_{i}") % 200 - 100) / 1000  # -10% ~ +10%
                open_price = base_price * (1 + price_change)
                
                high_price = open_price * (1 + abs(hash(f"h_{symbol}_{i}") % 50) / 2000)
                low_price = open_price * (1 - abs(hash(f"l_{symbol}_{i}") % 50) / 2000)
                close_price = low_price + (high_price - low_price) * (hash(f"c_{symbol}_{i}") % 100) / 100
                
                volume = 1000000 + (hash(f"v_{symbol}_{i}") % 2000000)
                
                chart_data.append({
                    'timestamp': timestamp,
                    'open': round(open_price, 0),
                    'high': round(high_price, 0),
                    'low': round(low_price, 0),
                    'close': round(close_price, 0),
                    'volume': volume
                })
                
                base_price = close_price  # 다음 봉의 기준가격
            
            return chart_data[-2000:]  # 최근 2000개 봉만 사용
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 차트 데이터 수집 오류: {e}")
            return []
    
    async def _display_optimization_results(self, results: Dict[str, Any]):
        """최적화 결과 출력"""
        try:
            self.console.print("\n📊 전략 최적화 결과 요약", style="bold green")
            
            for strategy_name, strategy_data in results.items():
                if not strategy_data:
                    continue
                
                self.console.print(f"\n🎯 {strategy_name.upper()} 전략", style="bold blue")
                
                # 요약 테이블
                summary_table = Table(title=f"{strategy_name} 최적화 요약")
                summary_table.add_column("항목", style="cyan")
                summary_table.add_column("값", style="magenta")
                
                summary = strategy_data.get('optimization_summary', {})
                summary_table.add_row("테스트 종목 수", str(summary.get('tested_symbols', 0)))
                summary_table.add_row("성공 종목 수", str(summary.get('successful_symbols', 0)))
                summary_table.add_row("평균 수익률", f"{summary.get('avg_profit_pct', 0):.2f}%")
                summary_table.add_row("총 거래 수", str(summary.get('total_trades', 0)))
                summary_table.add_row("종목 승률", f"{summary.get('symbol_win_rate', 0):.1f}%")
                
                self.console.print(summary_table)
                
                # 종목별 상세 결과
                if strategy_data.get('symbol_results'):
                    detail_table = Table(title=f"{strategy_name} 종목별 상세 결과")
                    detail_table.add_column("종목", style="cyan")
                    detail_table.add_column("수익률", style="green")
                    detail_table.add_column("승률", style="blue")
                    detail_table.add_column("거래수", style="yellow")
                    detail_table.add_column("샤프비율", style="magenta")
                    detail_table.add_column("최대손실", style="red")
                    
                    for symbol, data in strategy_data['symbol_results'].items():
                        detail_table.add_row(
                            symbol,
                            f"{data['profit_loss_pct']:.2f}%",
                            f"{data['win_rate']:.1f}%",
                            str(data['total_trades']),
                            f"{data['sharpe_ratio']:.2f}",
                            f"{data['max_drawdown']:.2f}%"
                        )
                    
                    self.console.print(detail_table)
                
                # 최고 성과 종목
                if strategy_data.get('best_overall'):
                    best = strategy_data['best_overall']
                    self.console.print(
                        f"\n🏆 최고 성과: {best['symbol']} "
                        f"(수익률: {best['result']['profit_loss_pct']:.2f}%, "
                        f"승률: {best['result']['win_rate']:.1f}%)",
                        style="bold yellow"
                    )
            
        except Exception as e:
            self.logger.error(f"❌ 결과 출력 오류: {e}")
    
    async def _save_optimization_results(self, results: Dict[str, Any]):
        """최적화 결과 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"D:/trading_system/logs/strategy_optimization_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("6번, 7번 전략 파라미터 최적화 결과\n")
                f.write("=" * 50 + "\n")
                f.write(f"최적화 실행 시간: {datetime.now()}\n\n")
                
                for strategy_name, strategy_data in results.items():
                    if not strategy_data:
                        continue
                    
                    f.write(f"\n[{strategy_name.upper()} 전략]\n")
                    f.write("-" * 30 + "\n")
                    
                    summary = strategy_data.get('optimization_summary', {})
                    f.write(f"테스트 종목 수: {summary.get('tested_symbols', 0)}\n")
                    f.write(f"성공 종목 수: {summary.get('successful_symbols', 0)}\n")
                    f.write(f"평균 수익률: {summary.get('avg_profit_pct', 0):.2f}%\n")
                    f.write(f"총 거래 수: {summary.get('total_trades', 0)}\n")
                    f.write(f"종목 승률: {summary.get('symbol_win_rate', 0):.1f}%\n")
                    
                    if strategy_data.get('best_overall'):
                        best = strategy_data['best_overall']
                        f.write(f"\n최고 성과 종목: {best['symbol']}\n")
                        f.write(f"  수익률: {best['result']['profit_loss_pct']:.2f}%\n")
                        f.write(f"  승률: {best['result']['win_rate']:.1f}%\n")
                        f.write(f"  거래수: {best['result']['total_trades']}\n")
                        f.write(f"  샤프비율: {best['result']['sharpe_ratio']:.2f}\n")
                        f.write(f"  최대손실: {best['result']['max_drawdown']:.2f}%\n")
            
            self.logger.info(f"✅ 최적화 결과 저장 완료: {filename}")
            self.console.print(f"\n💾 결과 저장: {filename}", style="green")
            
        except Exception as e:
            self.logger.error(f"❌ 결과 저장 오류: {e}")
    
    async def run_optimization_demo(self):
        """최적화 데모 실행"""
        try:
            self.console.print("\n🚀 6번, 7번 전략 파라미터 최적화 데모 시작", style="bold cyan")
            
            # 소수 종목으로 빠른 테스트
            demo_symbols = ['005930', '000660']  # 삼성전자, SK하이닉스
            
            results = await self.optimize_strategies_6_7(symbols=demo_symbols, days=30)
            
            self.console.print("\n✅ 최적화 데모 완료!", style="bold green")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 데모 실행 오류: {e}")
            self.console.print(f"❌ 데모 실행 실패: {e}", style="bold red")
            return {}


async def main():
    """메인 실행 함수"""
    try:
        config = Config()
        optimizer = StrategyOptimizer(config)
        await optimizer.initialize()
        
        # 최적화 실행
        results = await optimizer.run_optimization_demo()
        
        print("\n🎉 6번, 7번 전략 파라미터 최적화 완료!")
        return results
        
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        return {}


if __name__ == "__main__":
    asyncio.run(main())