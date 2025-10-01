#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/performance_visualizer.py

성능 시각화 도구 - 백테스팅 결과 시각화 및 보고서 생성
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import numpy as np

# 시각화 라이브러리
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("❌ 시각화 라이브러리가 설치되지 않았습니다. pip install matplotlib seaborn")

# Rich 라이브러리
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
except ImportError:
    print("❌ Rich 라이브러리가 필요합니다. pip install rich")

from .backtesting_engine import BacktestResult, PerformanceMetrics
from .strategy_validator import StrategyComparison, ValidationResult

logger = logging.getLogger(__name__)
console = Console()

@dataclass
class ChartConfig:
    """차트 설정"""
    figsize: Tuple[int, int] = (12, 8)
    dpi: int = 300
    style: str = 'seaborn'
    color_palette: str = 'husl'
    font_size: int = 10
    title_size: int = 14
    
    # 색상 설정
    primary_color: str = '#1f77b4'
    secondary_color: str = '#ff7f0e'
    success_color: str = '#2ca02c'
    danger_color: str = '#d62728'
    warning_color: str = '#ff9800'

@dataclass
class ReportSection:
    """보고서 섹션"""
    title: str
    content: str
    charts: List[str] = field(default_factory=list)
    tables: List[Dict] = field(default_factory=list)

class PerformanceVisualizer:
    """성능 시각화 도구"""
    
    def __init__(self, config=None, output_dir: str = "reports"):
        """시각화 도구 초기화"""
        self.trading_config = config  # 거래 시스템 설정
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(exist_ok=True)
        
        self.config = ChartConfig()  # 차트 설정
        self.logger = logging.getLogger(__name__)
        
        # 스타일 설정
        if VISUALIZATION_AVAILABLE:
            plt.style.use('default')
            sns.set_palette(self.config.color_palette)
    
    async def create_backtest_visualization(
        self,
        backtest_result: BacktestResult,
        save_charts: bool = True
    ) -> Dict[str, str]:
        """
        백테스팅 결과 시각화 생성
        
        Args:
            backtest_result: 백테스팅 결과
            save_charts: 차트 저장 여부
        
        Returns:
            Dict: 생성된 차트 파일 경로들
        """
        try:
            if not VISUALIZATION_AVAILABLE:
                self.logger.warning("⚠️ 시각화 라이브러리가 없습니다. 텍스트 결과만 제공합니다.")
                return {}
            
            console.print(f"[cyan]📊 {backtest_result.strategy_name} 백테스팅 결과 시각화 생성 중...[/cyan]")
            
            chart_files = {}
            
            with Progress() as progress:
                task = progress.add_task("[green]시각화 생성 중...", total=6)
                
                # 1. 수익 곡선 차트
                progress.update(task, description="수익 곡선 차트 생성 중...")
                equity_chart = await self._create_equity_curve_chart(backtest_result)
                if equity_chart and save_charts:
                    chart_files['equity_curve'] = equity_chart
                progress.advance(task)
                
                # 2. 드로우다운 차트
                progress.update(task, description="드로우다운 차트 생성 중...")
                drawdown_chart = await self._create_drawdown_chart(backtest_result)
                if drawdown_chart and save_charts:
                    chart_files['drawdown'] = drawdown_chart
                progress.advance(task)
                
                # 3. 월별 수익률 차트
                progress.update(task, description="월별 수익률 차트 생성 중...")
                monthly_chart = await self._create_monthly_returns_chart(backtest_result)
                if monthly_chart and save_charts:
                    chart_files['monthly_returns'] = monthly_chart
                progress.advance(task)
                
                # 4. 거래 분석 차트
                progress.update(task, description="거래 분석 차트 생성 중...")
                trades_chart = await self._create_trades_analysis_chart(backtest_result)
                if trades_chart and save_charts:
                    chart_files['trades_analysis'] = trades_chart
                progress.advance(task)
                
                # 5. AI 성과 차트 (AI 사용시에만)
                if backtest_result.ai_predictions:
                    progress.update(task, description="AI 성과 차트 생성 중...")
                    ai_chart = await self._create_ai_performance_chart(backtest_result)
                    if ai_chart and save_charts:
                        chart_files['ai_performance'] = ai_chart
                progress.advance(task)
                
                # 6. 종합 대시보드
                progress.update(task, description="종합 대시보드 생성 중...")
                dashboard = await self._create_performance_dashboard(backtest_result)
                if dashboard and save_charts:
                    chart_files['dashboard'] = dashboard
                progress.advance(task)
            
            console.print(f"[green]✅ 시각화 생성 완료: {len(chart_files)}개 차트[/green]")
            return chart_files
            
        except Exception as e:
            self.logger.error(f"❌ 시각화 생성 오류: {e}")
            return {}
    
    async def create_strategy_comparison_chart(
        self,
        comparison_results: Dict[str, StrategyComparison],
        save_chart: bool = True
    ) -> Optional[str]:
        """전략 비교 차트 생성"""
        try:
            if not VISUALIZATION_AVAILABLE or not comparison_results:
                return None
            
            console.print("[cyan]📈 전략 비교 차트 생성 중...[/cyan]")
            
            # 데이터 준비
            strategies = []
            ai_returns = []
            traditional_returns = []
            improvements = []
            
            for strategy_name, comparison in comparison_results.items():
                strategies.append(strategy_name)
                ai_returns.append(comparison.with_ai_result.metrics.annual_return)
                traditional_returns.append(comparison.without_ai_result.metrics.annual_return)
                improvements.append(comparison.return_improvement)
            
            # 차트 생성
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # 1. 수익률 비교
            x = np.arange(len(strategies))
            width = 0.35
            
            ax1.bar(x - width/2, ai_returns, width, label='AI 강화', 
                   color=self.config.primary_color, alpha=0.8)
            ax1.bar(x + width/2, traditional_returns, width, label='전통적', 
                   color=self.config.secondary_color, alpha=0.8)
            
            ax1.set_xlabel('전략')
            ax1.set_ylabel('연간 수익률 (%)')
            ax1.set_title('AI vs 전통적 전략 수익률 비교')
            ax1.set_xticks(x)
            ax1.set_xticklabels(strategies, rotation=45)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 2. 개선율
            colors = [self.config.success_color if imp > 0 else self.config.danger_color 
                     for imp in improvements]
            
            bars = ax2.bar(strategies, improvements, color=colors, alpha=0.7)
            ax2.set_xlabel('전략')
            ax2.set_ylabel('개선율 (%)')
            ax2.set_title('AI 강화로 인한 성능 개선')
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax2.grid(True, alpha=0.3)
            plt.setp(ax2.get_xticklabels(), rotation=45)
            
            # 개선율 값 표시
            for bar, improvement in zip(bars, improvements):
                height = bar.get_height()
                ax2.annotate(f'{improvement:.1f}%',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3 if height >= 0 else -15),
                           textcoords="offset points",
                           ha='center', va='bottom' if height >= 0 else 'top')
            
            plt.tight_layout()
            
            # 저장
            if save_chart:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = self.charts_dir / f"strategy_comparison_{timestamp}.png"
                plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
                plt.close()
                return str(filename)
            else:
                plt.show()
                return None
            
        except Exception as e:
            self.logger.error(f"❌ 전략 비교 차트 생성 오류: {e}")
            return None
    
    async def _create_equity_curve_chart(self, backtest_result: BacktestResult) -> Optional[str]:
        """수익 곡선 차트 생성"""
        try:
            if not backtest_result.equity_curve:
                return None
            
            # 데이터 준비
            dates = [point['date'] for point in backtest_result.equity_curve]
            values = [point['portfolio_value'] for point in backtest_result.equity_curve]
            
            # 차트 생성
            plt.figure(figsize=self.config.figsize)
            plt.plot(dates, values, linewidth=2, color=self.config.primary_color)
            
            # 기준선 (초기 자본)
            plt.axhline(y=backtest_result.initial_capital, 
                       color=self.config.secondary_color, 
                       linestyle='--', alpha=0.7, label='초기 자본')
            
            plt.title(f'{backtest_result.strategy_name} 전략 - 포트폴리오 가치 추이', 
                     fontsize=self.config.title_size)
            plt.xlabel('날짜')
            plt.ylabel('포트폴리오 가치 (원)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # 날짜 형식 설정
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.xticks(rotation=45)
            
            # 수익률 표시
            total_return_pct = backtest_result.total_return_pct
            color = self.config.success_color if total_return_pct >= 0 else self.config.danger_color
            plt.text(0.02, 0.98, f'총 수익률: {total_return_pct:.2f}%', 
                    transform=plt.gca().transAxes, fontsize=12, 
                    bbox=dict(boxstyle='round', facecolor=color, alpha=0.1),
                    verticalalignment='top')
            
            plt.tight_layout()
            
            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"equity_curve_{backtest_result.strategy_name}_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()
            
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"❌ 수익 곡선 차트 생성 오류: {e}")
            return None
    
    async def _create_drawdown_chart(self, backtest_result: BacktestResult) -> Optional[str]:
        """드로우다운 차트 생성"""
        try:
            if not backtest_result.equity_curve:
                return None
            
            # 드로우다운 계산
            dates = [point['date'] for point in backtest_result.equity_curve]
            values = [point['portfolio_value'] for point in backtest_result.equity_curve]
            
            # 누적 최대값과 드로우다운 계산
            peak = values[0]
            drawdowns = []
            
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak * 100
                drawdowns.append(-drawdown)  # 음수로 표시
            
            # 차트 생성
            plt.figure(figsize=self.config.figsize)
            plt.fill_between(dates, drawdowns, 0, 
                           color=self.config.danger_color, alpha=0.3, label='드로우다운')
            plt.plot(dates, drawdowns, color=self.config.danger_color, linewidth=2)
            
            plt.title(f'{backtest_result.strategy_name} 전략 - 드로우다운 분석', 
                     fontsize=self.config.title_size)
            plt.xlabel('날짜')
            plt.ylabel('드로우다운 (%)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # 최대 드로우다운 표시
            max_dd = backtest_result.metrics.max_drawdown
            plt.text(0.02, 0.02, f'최대 드로우다운: {max_dd:.2f}%', 
                    transform=plt.gca().transAxes, fontsize=12,
                    bbox=dict(boxstyle='round', facecolor=self.config.danger_color, alpha=0.1))
            
            # 날짜 형식 설정
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"drawdown_{backtest_result.strategy_name}_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()
            
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"❌ 드로우다운 차트 생성 오류: {e}")
            return None
    
    async def _create_monthly_returns_chart(self, backtest_result: BacktestResult) -> Optional[str]:
        """월별 수익률 차트 생성"""
        try:
            if not backtest_result.equity_curve:
                return None
            
            # 월별 수익률 계산
            df = pd.DataFrame(backtest_result.equity_curve)
            df['date'] = pd.to_datetime(df['date'])
            df['year_month'] = df['date'].dt.to_period('M')
            
            # 월말 값 추출
            monthly_data = df.groupby('year_month')['portfolio_value'].last()
            
            # 월별 수익률 계산
            monthly_returns = monthly_data.pct_change().dropna() * 100
            
            if monthly_returns.empty:
                return None
            
            # 차트 생성
            plt.figure(figsize=(14, 6))
            
            # 색상 설정 (양수: 초록, 음수: 빨강)
            colors = [self.config.success_color if ret >= 0 else self.config.danger_color 
                     for ret in monthly_returns]
            
            bars = plt.bar(range(len(monthly_returns)), monthly_returns, 
                          color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
            
            plt.title(f'{backtest_result.strategy_name} 전략 - 월별 수익률', 
                     fontsize=self.config.title_size)
            plt.xlabel('월')
            plt.ylabel('수익률 (%)')
            plt.grid(True, alpha=0.3, axis='y')
            
            # x축 라벨 설정
            plt.xticks(range(len(monthly_returns)), 
                      [str(period) for period in monthly_returns.index], 
                      rotation=45)
            
            # 0% 기준선
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # 통계 정보 표시
            avg_return = monthly_returns.mean()
            win_rate = (monthly_returns > 0).sum() / len(monthly_returns) * 100
            
            stats_text = f'평균 월수익률: {avg_return:.2f}%\n월 승률: {win_rate:.1f}%'
            plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            
            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"monthly_returns_{backtest_result.strategy_name}_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()
            
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"❌ 월별 수익률 차트 생성 오류: {e}")
            return None
    
    async def _create_trades_analysis_chart(self, backtest_result: BacktestResult) -> Optional[str]:
        """거래 분석 차트 생성"""
        try:
            if not backtest_result.trades:
                return None
            
            # 거래 데이터 분석
            profits = []
            losses = []
            trade_dates = []
            
            for trade in backtest_result.trades:
                if trade['action'] == 'SELL' and 'net_amount' in trade:
                    pnl = trade['net_amount'] - abs(trade['quantity']) * trade['price']
                    trade_dates.append(trade['date'])
                    
                    if pnl > 0:
                        profits.append(pnl)
                        losses.append(0)
                    else:
                        profits.append(0)
                        losses.append(pnl)
            
            if not profits and not losses:
                return None
            
            # 차트 생성 (2x2 subplot)
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # 1. 손익 분포
            if profits or losses:
                all_pnl = [p + l for p, l in zip(profits, losses)]
                colors = [self.config.success_color if pnl >= 0 else self.config.danger_color 
                         for pnl in all_pnl]
                
                ax1.bar(range(len(all_pnl)), all_pnl, color=colors, alpha=0.7)
                ax1.set_title('거래별 손익')
                ax1.set_xlabel('거래 번호')
                ax1.set_ylabel('손익 (원)')
                ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                ax1.grid(True, alpha=0.3)
            
            # 2. 손익 히스토그램
            if profits or losses:
                all_pnl = [pnl for pnl in all_pnl if pnl != 0]
                if all_pnl:
                    ax2.hist(all_pnl, bins=20, color=self.config.primary_color, alpha=0.7)
                    ax2.set_title('손익 분포')
                    ax2.set_xlabel('손익 (원)')
                    ax2.set_ylabel('빈도')
                    ax2.axvline(x=0, color='black', linestyle='--', alpha=0.5)
                    ax2.grid(True, alpha=0.3)
            
            # 3. 누적 손익
            cumulative_pnl = np.cumsum([p + l for p, l in zip(profits, losses)])
            ax3.plot(cumulative_pnl, linewidth=2, color=self.config.primary_color)
            ax3.set_title('누적 손익')
            ax3.set_xlabel('거래 번호')
            ax3.set_ylabel('누적 손익 (원)')
            ax3.grid(True, alpha=0.3)
            
            # 4. 승률 및 통계
            win_count = len([p for p in profits if p > 0])
            loss_count = len([l for l in losses if l < 0])
            total_trades = win_count + loss_count
            
            if total_trades > 0:
                win_rate = win_count / total_trades * 100
                
                # 파이 차트
                sizes = [win_count, loss_count]
                labels = [f'승리 ({win_count})', f'패배 ({loss_count})']
                colors = [self.config.success_color, self.config.danger_color]
                
                ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax4.set_title(f'승률: {win_rate:.1f}%')
            
            plt.suptitle(f'{backtest_result.strategy_name} 전략 - 거래 분석', 
                        fontsize=self.config.title_size)
            plt.tight_layout()
            
            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"trades_analysis_{backtest_result.strategy_name}_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()
            
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"❌ 거래 분석 차트 생성 오류: {e}")
            return None
    
    async def _create_ai_performance_chart(self, backtest_result: BacktestResult) -> Optional[str]:
        """AI 성과 차트 생성"""
        try:
            if not backtest_result.ai_predictions:
                return None
            
            # AI 예측 정확도 분석
            predictions = backtest_result.ai_predictions
            confidences = [pred.get('confidence', 0) for pred in predictions]
            accuracies = [pred.get('accuracy', 0) for pred in predictions]
            
            # 차트 생성
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # 1. 신뢰도 vs 정확도 산점도
            if confidences and accuracies:
                ax1.scatter(confidences, accuracies, alpha=0.6, 
                           color=self.config.primary_color, s=50)
                ax1.set_xlabel('AI 예측 신뢰도')
                ax1.set_ylabel('실제 정확도')
                ax1.set_title('AI 예측 신뢰도 vs 정확도')
                ax1.grid(True, alpha=0.3)
                
                # 추세선
                if len(confidences) > 1:
                    z = np.polyfit(confidences, accuracies, 1)
                    p = np.poly1d(z)
                    ax1.plot(confidences, p(confidences), 
                            color=self.config.danger_color, linestyle='--', alpha=0.8)
            
            # 2. 시간에 따른 AI 정확도
            dates = [pred.get('date', datetime.now()) for pred in predictions]
            if dates and accuracies:
                ax2.plot(dates, accuracies, linewidth=2, color=self.config.success_color, 
                        marker='o', markersize=4)
                ax2.set_xlabel('날짜')
                ax2.set_ylabel('AI 예측 정확도')
                ax2.set_title('시간에 따른 AI 예측 정확도')
                ax2.grid(True, alpha=0.3)
                
                # 평균 정확도 라인
                avg_accuracy = np.mean(accuracies)
                ax2.axhline(y=avg_accuracy, color=self.config.warning_color, 
                           linestyle='--', alpha=0.7, 
                           label=f'평균 정확도: {avg_accuracy:.1%}')
                ax2.legend()
            
            plt.suptitle(f'{backtest_result.strategy_name} - AI 성과 분석', 
                        fontsize=self.config.title_size)
            plt.tight_layout()
            
            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"ai_performance_{backtest_result.strategy_name}_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()
            
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"❌ AI 성과 차트 생성 오류: {e}")
            return None
    
    async def _create_performance_dashboard(self, backtest_result: BacktestResult) -> Optional[str]:
        """종합 성과 대시보드 생성"""
        try:
            # 대시보드 레이아웃 (2x3 그리드)
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            axes = axes.flatten()
            
            metrics = backtest_result.metrics
            
            # 1. 주요 지표 요약
            ax1 = axes[0]
            ax1.axis('off')
            
            summary_text = f"""
            전략: {backtest_result.strategy_name}
            
            수익률: {backtest_result.total_return_pct:.2f}%
            연간수익률: {metrics.annual_return:.2f}%
            샤프비율: {metrics.sharpe_ratio:.2f}
            최대낙폭: {metrics.max_drawdown:.2f}%
            
            총거래수: {metrics.total_trades}
            승률: {metrics.win_rate:.1f}%
            수익팩터: {metrics.profit_factor:.2f}
            """
            
            ax1.text(0.1, 0.9, summary_text, transform=ax1.transAxes, 
                    fontsize=12, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor=self.config.primary_color, alpha=0.1))
            ax1.set_title('성과 요약', fontsize=14, fontweight='bold')
            
            # 2. 수익률 게이지
            ax2 = axes[1]
            self._create_gauge_chart(ax2, backtest_result.total_return_pct, 
                                   '총 수익률 (%)', -50, 100)
            
            # 3. 리스크-수익 산점도
            ax3 = axes[2]
            ax3.scatter([metrics.volatility], [metrics.annual_return], 
                       s=200, color=self.config.primary_color, alpha=0.7)
            ax3.set_xlabel('변동성 (%)')
            ax3.set_ylabel('연간 수익률 (%)')
            ax3.set_title('리스크-수익 프로필')
            ax3.grid(True, alpha=0.3)
            
            # 4. 월별 수익률 히트맵 (간단화)
            ax4 = axes[3]
            if backtest_result.equity_curve:
                # 월별 수익률 데이터 생성 (간단화)
                monthly_returns = self._calculate_monthly_returns_simple(backtest_result)
                if monthly_returns:
                    months = list(monthly_returns.keys())
                    returns = list(monthly_returns.values())
                    colors = [self.config.success_color if r >= 0 else self.config.danger_color 
                             for r in returns]
                    
                    ax4.bar(range(len(returns)), returns, color=colors, alpha=0.7)
                    ax4.set_title('월별 수익률')
                    ax4.set_ylabel('수익률 (%)')
                    ax4.set_xticks(range(len(months)))
                    ax4.set_xticklabels([m.strftime('%Y-%m') for m in months], rotation=45)
                    ax4.grid(True, alpha=0.3)
            
            # 5. 드로우다운 (미니 차트)
            ax5 = axes[4]
            if backtest_result.equity_curve:
                values = [point['portfolio_value'] for point in backtest_result.equity_curve]
                peak = values[0]
                drawdowns = []
                
                for value in values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak * 100
                    drawdowns.append(-drawdown)
                
                ax5.fill_between(range(len(drawdowns)), drawdowns, 0, 
                               color=self.config.danger_color, alpha=0.3)
                ax5.plot(drawdowns, color=self.config.danger_color, linewidth=1)
                ax5.set_title('드로우다운')
                ax5.set_ylabel('드로우다운 (%)')
                ax5.grid(True, alpha=0.3)
            
            # 6. AI 성과 (있는 경우)
            ax6 = axes[5]
            if backtest_result.ai_predictions and metrics.ai_accuracy > 0:
                # AI 성과 파이 차트
                correct = metrics.ai_accuracy
                incorrect = 100 - correct
                
                ax6.pie([correct, incorrect], 
                       labels=[f'정확 ({correct:.1f}%)', f'부정확 ({incorrect:.1f}%)'],
                       colors=[self.config.success_color, self.config.danger_color],
                       autopct='%1.1f%%', startangle=90)
                ax6.set_title('AI 예측 정확도')
            else:
                ax6.axis('off')
                ax6.text(0.5, 0.5, 'AI 데이터 없음', transform=ax6.transAxes,
                        ha='center', va='center', fontsize=12, alpha=0.5)
            
            plt.suptitle(f'{backtest_result.strategy_name} 전략 - 종합 성과 대시보드', 
                        fontsize=16, fontweight='bold')
            plt.tight_layout()
            
            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"dashboard_{backtest_result.strategy_name}_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()
            
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"❌ 대시보드 생성 오류: {e}")
            return None
    
    def _create_gauge_chart(self, ax, value: float, title: str, min_val: float, max_val: float):
        """게이지 차트 생성"""
        try:
            # 게이지 설정
            theta = np.linspace(0, np.pi, 100)
            r_outer = 1.0
            r_inner = 0.7
            
            # 배경 호
            ax.fill_between(theta, r_inner, r_outer, color='lightgray', alpha=0.3)
            
            # 값에 따른 각도 계산
            normalized_value = (value - min_val) / (max_val - min_val)
            value_theta = normalized_value * np.pi
            
            # 값 호
            value_range = theta[theta <= value_theta]
            if len(value_range) > 0:
                color = (self.config.success_color if value >= 0 
                        else self.config.danger_color)
                ax.fill_between(value_range, r_inner, r_outer, 
                               color=color, alpha=0.8)
            
            # 바늘
            needle_theta = value_theta
            ax.plot([needle_theta, needle_theta], [0, r_outer], 
                   'k-', linewidth=3, alpha=0.8)
            
            # 중심점
            ax.plot(needle_theta, 0, 'ko', markersize=8)
            
            # 값 표시
            ax.text(np.pi/2, 0.3, f'{value:.1f}', 
                   ha='center', va='center', fontsize=16, fontweight='bold')
            
            # 설정
            ax.set_xlim(0, np.pi)
            ax.set_ylim(-0.1, 1.1)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.axis('off')
            
        except Exception as e:
            self.logger.error(f"❌ 게이지 차트 생성 오류: {e}")
    
    def _calculate_monthly_returns_simple(self, backtest_result: BacktestResult) -> Dict:
        """월별 수익률 간단 계산"""
        try:
            if not backtest_result.equity_curve:
                return {}
            
            monthly_data = {}
            current_month = None
            month_start_value = None
            
            for point in backtest_result.equity_curve:
                date = point['date']
                value = point['portfolio_value']
                
                month_key = date.replace(day=1)
                
                if current_month != month_key:
                    # 새로운 월 시작
                    if current_month and month_start_value:
                        # 이전 월 수익률 계산
                        prev_value = backtest_result.equity_curve[
                            backtest_result.equity_curve.index(point) - 1
                        ]['portfolio_value']
                        monthly_return = (prev_value - month_start_value) / month_start_value * 100
                        monthly_data[current_month] = monthly_return
                    
                    current_month = month_key
                    month_start_value = value
            
            return monthly_data
            
        except Exception as e:
            self.logger.error(f"❌ 월별 수익률 계산 오류: {e}")
            return {}

class ReportGenerator:
    """백테스팅 보고서 생성기"""
    
    def __init__(self, output_dir: str = "reports"):
        """보고서 생성기 초기화"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.visualizer = PerformanceVisualizer(output_dir)
        self.logger = logging.getLogger(__name__)

    async def display_market_regime_report(self, regime_analyses: List[Any]):
        """시장 체제 분석 결과를 Rich 테이블로 표시"""
        try:
            if not regime_analyses:
                print("\n--- Market Regime Analysis Report ---")
                print("No market regime analysis results found.")
                print("--- End of Report ---\n")
                return

            print("\n--- Market Regime Analysis Report ---")
            
            for analysis in regime_analyses:
                period_str = f"{analysis.period_start.strftime('%Y-%m-%d')} ~ {analysis.period_end.strftime('%Y-%m-%d')}"
                regime_str = analysis.regime.value
                
                avg_return_str = f"{analysis.avg_return:.2f}"
                volatility_str = f"{analysis.volatility:.2f}"
                max_drawdown_str = f"{analysis.max_drawdown:.2f}"
                ai_accuracy_str = f"{analysis.ai_accuracy:.2f}" if analysis.ai_prediction_count > 0 else "N/A"

                print(f"\n[Period: {period_str}]")
                print(f"  - Regime: {regime_str}")
                print(f"  - Average Return: {avg_return_str}%")
                print(f"  - Volatility: {volatility_str}%")
                print(f"  - Max Drawdown: {max_drawdown_str}%")
                print(f"  - AI Accuracy: {ai_accuracy_str}")

            print("--- End of Report ---\n")
            await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error(f"❌ 시장 체제 보고서 표시 오류: {e}")
            console.print(f"[red]❌ 시장 체제 보고서 표시에 실패했습니다: {e}[/red]")
    
    async def generate_comprehensive_report(
        self,
        backtest_results: List[BacktestResult],
        comparison_results: Optional[Dict[str, StrategyComparison]] = None,
        validation_results: Optional[Dict[str, ValidationResult]] = None
    ) -> str:
        """종합 백테스팅 보고서 생성"""
        try:
            console.print("[cyan]📋 종합 백테스팅 보고서 생성 중...[/cyan]")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.output_dir / f"backtest_report_{timestamp}.html"
            
            # HTML 보고서 생성
            html_content = await self._generate_html_report(
                backtest_results, comparison_results, validation_results
            )
            
            # 파일 저장
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            console.print(f"[green]✅ 종합 보고서 생성 완료: {report_file}[/green]")
            
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"❌ 보고서 생성 오류: {e}")
            raise
    
    async def _generate_html_report(
        self,
        backtest_results: List[BacktestResult],
        comparison_results: Optional[Dict[str, StrategyComparison]],
        validation_results: Optional[Dict[str, ValidationResult]]
    ) -> str:
        """HTML 보고서 생성"""
        try:
            # HTML 템플릿 시작
            html = f"""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AI Trading System - 백테스팅 보고서</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                             color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                    .section {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; 
                              border-left: 4px solid #007bff; }}
                    .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                                   gap: 15px; margin: 20px 0; }}
                    .metric-card {{ background: white; padding: 15px; border-radius: 8px; 
                                  box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                    .chart-container {{ text-align: center; margin: 20px 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .positive {{ color: #28a745; }}
                    .negative {{ color: #dc3545; }}
                    .neutral {{ color: #6c757d; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🤖 AI Trading System - 백테스팅 보고서</h1>
                    <p>생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</p>
                    <p>분석 전략 수: {len(backtest_results)}개</p>
                </div>
            """
            
            # 전체 요약
            html += await self._generate_summary_section(backtest_results)
            
            # 개별 전략 결과
            for result in backtest_results:
                html += await self._generate_strategy_section(result)
            
            # 전략 비교 (있는 경우)
            if comparison_results:
                html += await self._generate_comparison_section(comparison_results)
            
            # 검증 결과 (있는 경우)
            if validation_results:
                html += await self._generate_validation_section(validation_results)
            
            # 결론 및 권고사항
            html += await self._generate_conclusion_section(backtest_results, comparison_results)
            
            # HTML 종료
            html += """
                <div class="section">
                    <h2>📌 면책사항</h2>
                    <p><strong>이 보고서는 과거 데이터를 기반으로 한 백테스팅 결과이며, 
                    실제 투자 성과를 보장하지 않습니다.</strong></p>
                    <ul>
                        <li>과거 성과는 미래 수익을 보장하지 않습니다</li>
                        <li>실제 거래에서는 슬리피지, 수수료 등 추가 비용이 발생할 수 있습니다</li>
                        <li>시장 상황 변화에 따라 전략의 효과가 달라질 수 있습니다</li>
                        <li>투자 결정은 본인의 책임하에 신중하게 하시기 바랍니다</li>
                    </ul>
                </div>
                <div style="text-align: center; margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <p><em>AI Trading System v4.0 - Phase 6: Backtesting & Validation Framework</em></p>
                    <p>Powered by Claude Code SuperClaude Framework</p>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"❌ HTML 보고서 생성 오류: {e}")
            return f"<html><body><h1>보고서 생성 오류</h1><p>{e}</p></body></html>"
    
    async def _generate_summary_section(self, backtest_results: List[BacktestResult]) -> str:
        """요약 섹션 생성"""
        try:
            if not backtest_results:
                return ""
            
            # 전체 통계 계산
            total_strategies = len(backtest_results)
            avg_return = np.mean([result.total_return_pct for result in backtest_results])
            best_strategy = max(backtest_results, key=lambda x: x.total_return_pct)
            worst_strategy = min(backtest_results, key=lambda x: x.total_return_pct)
            
            positive_strategies = len([r for r in backtest_results if r.total_return_pct > 0])
            success_rate = (positive_strategies / total_strategies) * 100
            
            html = f"""
            <div class="section">
                <h2>📊 전체 요약</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div>분석 전략 수</div>
                        <div class="metric-value">{total_strategies}개</div>
                    </div>
                    <div class="metric-card">
                        <div>평균 수익률</div>
                        <div class="metric-value {'positive' if avg_return >= 0 else 'negative'}">
                            {avg_return:.2f}%
                        </div>
                    </div>
                    <div class="metric-card">
                        <div>수익 전략 비율</div>
                        <div class="metric-value positive">{success_rate:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div>최고 성과 전략</div>
                        <div class="metric-value positive">{best_strategy.strategy_name}</div>
                        <div>({best_strategy.total_return_pct:.2f}%)</div>
                    </div>
                </div>
                
                <h3>🏆 성과 랭킹</h3>
                <table>
                    <tr>
                        <th>순위</th><th>전략명</th><th>수익률</th><th>샤프비율</th><th>최대낙폭</th><th>승률</th>
                    </tr>
            """
            
            # 성과순 정렬
            sorted_results = sorted(backtest_results, key=lambda x: x.total_return_pct, reverse=True)
            
            for i, result in enumerate(sorted_results, 1):
                return_class = 'positive' if result.total_return_pct >= 0 else 'negative'
                html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{result.strategy_name}</td>
                        <td class="{return_class}">{result.total_return_pct:.2f}%</td>
                        <td>{result.metrics.sharpe_ratio:.2f}</td>
                        <td class="negative">{result.metrics.max_drawdown:.2f}%</td>
                        <td>{result.metrics.win_rate:.1f}%</td>
                    </tr>
                """
            
            html += """
                </table>
            </div>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"❌ 요약 섹션 생성 오류: {e}")
            return f"<div class='section'><h2>요약 섹션 오류</h2><p>{e}</p></div>"
    
    async def _generate_strategy_section(self, result: BacktestResult) -> str:
        """개별 전략 섹션 생성"""
        try:
            return_class = 'positive' if result.total_return_pct >= 0 else 'negative'
            
            html = f"""
            <div class="section">
                <h2>📈 {result.strategy_name} 전략 분석</h2>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div>총 수익률</div>
                        <div class="metric-value {return_class}">{result.total_return_pct:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div>연간 수익률</div>
                        <div class="metric-value {return_class}">{result.metrics.annual_return:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div>샤프 비율</div>
                        <div class="metric-value">{result.metrics.sharpe_ratio:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div>최대 낙폭</div>
                        <div class="metric-value negative">{result.metrics.max_drawdown:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div>총 거래수</div>
                        <div class="metric-value">{result.metrics.total_trades}</div>
                    </div>
                    <div class="metric-card">
                        <div>승률</div>
                        <div class="metric-value">{result.metrics.win_rate:.1f}%</div>
                    </div>
                </div>
                
                <h3>📊 세부 지표</h3>
                <table>
                    <tr><th>지표</th><th>값</th><th>평가</th></tr>
                    <tr>
                        <td>수익 팩터</td>
                        <td>{result.metrics.profit_factor:.2f}</td>
                        <td class="{'positive' if result.metrics.profit_factor > 1.2 else 'neutral'}">
                            {'우수' if result.metrics.profit_factor > 1.5 else '양호' if result.metrics.profit_factor > 1.2 else '보통'}
                        </td>
                    </tr>
                    <tr>
                        <td>평균 승리</td>
                        <td>{result.metrics.avg_win:,.0f}원</td>
                        <td class="positive">-</td>
                    </tr>
                    <tr>
                        <td>평균 손실</td>
                        <td>{result.metrics.avg_loss:,.0f}원</td>
                        <td class="negative">-</td>
                    </tr>
                    <tr>
                        <td>변동성</td>
                        <td>{result.metrics.volatility:.2f}%</td>
                        <td class="{'neutral' if result.metrics.volatility < 20 else 'negative'}">
                            {'낮음' if result.metrics.volatility < 15 else '보통' if result.metrics.volatility < 25 else '높음'}
                        </td>
                    </tr>
                </table>
            """
            
            # AI 관련 지표 (있는 경우)
            if result.metrics.ai_accuracy > 0:
                html += f"""
                <h3>🤖 AI 성과</h3>
                <table>
                    <tr><th>AI 지표</th><th>값</th><th>평가</th></tr>
                    <tr>
                        <td>AI 예측 정확도</td>
                        <td>{result.metrics.ai_accuracy:.1f}%</td>
                        <td class="{'positive' if result.metrics.ai_accuracy > 60 else 'neutral'}">
                            {'우수' if result.metrics.ai_accuracy > 70 else '양호' if result.metrics.ai_accuracy > 60 else '보통'}
                        </td>
                    </tr>
                    <tr>
                        <td>신뢰도 상관관계</td>
                        <td>{result.metrics.ai_confidence_correlation:.3f}</td>
                        <td class="{'positive' if result.metrics.ai_confidence_correlation > 0.5 else 'neutral'}">
                            {'높음' if result.metrics.ai_confidence_correlation > 0.7 else '보통'}
                        </td>
                    </tr>
                </table>
                """
            
            html += """
            </div>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"❌ 전략 섹션 생성 오류: {e}")
            return f"<div class='section'><h2>{result.strategy_name} 섹션 오류</h2><p>{e}</p></div>"
    
    async def _generate_comparison_section(self, comparison_results: Dict[str, StrategyComparison]) -> str:
        """전략 비교 섹션 생성"""
        try:
            html = """
            <div class="section">
                <h2>🔄 AI vs 전통적 전략 비교</h2>
                <table>
                    <tr>
                        <th>전략</th>
                        <th>AI 수익률</th>
                        <th>전통적 수익률</th>
                        <th>개선률</th>
                        <th>샤프비율 개선</th>
                        <th>통계적 유의성</th>
                        <th>AI 효과성 점수</th>
                    </tr>
            """
            
            for strategy_name, comparison in comparison_results.items():
                ai_return = comparison.with_ai_result.metrics.annual_return
                traditional_return = comparison.without_ai_result.metrics.annual_return
                improvement = comparison.return_improvement
                sharpe_improvement = comparison.sharpe_improvement
                
                improvement_class = 'positive' if improvement > 0 else 'negative'
                significance = '유의함' if comparison.statistical_significance else '유의하지 않음'
                significance_class = 'positive' if comparison.statistical_significance else 'neutral'
                
                html += f"""
                    <tr>
                        <td>{strategy_name}</td>
                        <td class="positive">{ai_return:.2f}%</td>
                        <td class="neutral">{traditional_return:.2f}%</td>
                        <td class="{improvement_class}">{improvement:+.2f}%</td>
                        <td class="{improvement_class}">{sharpe_improvement:+.2f}</td>
                        <td class="{significance_class}">{significance}</td>
                        <td class="metric-value">{comparison.ai_effectiveness_score:.1f}점</td>
                    </tr>
                """
            
            html += """
                </table>
                
                <h3>💡 AI 효과 분석</h3>
                <ul>
            """
            
            # AI 효과 분석
            effective_strategies = [name for name, comp in comparison_results.items() 
                                  if comp.return_improvement > 0]
            significant_strategies = [name for name, comp in comparison_results.items() 
                                    if comp.statistical_significance]
            
            html += f"""
                    <li>AI 효과가 있는 전략: {len(effective_strategies)}개 / {len(comparison_results)}개</li>
                    <li>통계적으로 유의한 개선: {len(significant_strategies)}개</li>
                    <li>평균 AI 효과성 점수: {np.mean([comp.ai_effectiveness_score for comp in comparison_results.values()]):.1f}점</li>
                </ul>
            </div>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"❌ 비교 섹션 생성 오류: {e}")
            return f"<div class='section'><h2>비교 섹션 오류</h2><p>{e}</p></div>"
    
    async def _generate_validation_section(self, validation_results: Dict[str, ValidationResult]) -> str:
        """검증 섹션 생성"""
        try:
            html = """
            <div class="section">
                <h2>✅ 전략 검증 결과</h2>
                <table>
                    <tr>
                        <th>전략</th>
                        <th>검증 상태</th>
                        <th>전체 점수</th>
                        <th>수익률 검증</th>
                        <th>드로우다운 검증</th>
                        <th>샤프비율 검증</th>
                        <th>승률 검증</th>
                    </tr>
            """
            
            for strategy_name, validation in validation_results.items():
                status_class = {
                    'PASSED': 'positive',
                    'WARNING': 'neutral', 
                    'FAILED': 'negative',
                    'INSUFFICIENT_DATA': 'neutral'
                }.get(validation.status.value, 'neutral')
                
                html += f"""
                    <tr>
                        <td>{strategy_name}</td>
                        <td class="{status_class}">{validation.status.value}</td>
                        <td class="metric-value">{validation.overall_score:.1f}점</td>
                        <td class="{'positive' if validation.return_check else 'negative'}">
                            {'✓' if validation.return_check else '✗'}
                        </td>
                        <td class="{'positive' if validation.drawdown_check else 'negative'}">
                            {'✓' if validation.drawdown_check else '✗'}
                        </td>
                        <td class="{'positive' if validation.sharpe_check else 'negative'}">
                            {'✓' if validation.sharpe_check else '✗'}
                        </td>
                        <td class="{'positive' if validation.win_rate_check else 'negative'}">
                            {'✓' if validation.win_rate_check else '✗'}
                        </td>
                    </tr>
                """
            
            # 검증 요약
            passed_count = len([v for v in validation_results.values() if v.status.value == 'PASSED'])
            warning_count = len([v for v in validation_results.values() if v.status.value == 'WARNING'])
            failed_count = len([v for v in validation_results.values() if v.status.value == 'FAILED'])
            
            html += f"""
                </table>
                
                <h3>📋 검증 요약</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div>검증 통과</div>
                        <div class="metric-value positive">{passed_count}개</div>
                    </div>
                    <div class="metric-card">
                        <div>경고</div>
                        <div class="metric-value neutral">{warning_count}개</div>
                    </div>
                    <div class="metric-card">
                        <div>검증 실패</div>
                        <div class="metric-value negative">{failed_count}개</div>
                    </div>
                    <div class="metric-card">
                        <div>전체 통과율</div>
                        <div class="metric-value positive">{(passed_count/len(validation_results)*100):.1f}%</div>
                    </div>
                </div>
            </div>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"❌ 검증 섹션 생성 오류: {e}")
            return f"<div class='section'><h2>검증 섹션 오류</h2><p>{e}</p></div>"
    
    async def display_market_regime_report(self, regime_analyses: List[Any]):
        """시장 체제 분석 결과를 Rich 테이블로 표시"""
        try:
            if not regime_analyses:
                print("\n--- Market Regime Analysis Report ---")
                print("No market regime analysis results found.")
                print("--- End of Report ---\n")
                return

            print("\n--- Market Regime Analysis Report ---")
            
            for analysis in regime_analyses:
                period_str = f"{analysis.period_start.strftime('%Y-%m-%d')} ~ {analysis.period_end.strftime('%Y-%m-%d')}"
                regime_str = analysis.regime.value
                
                avg_return_str = f"{analysis.avg_return:.2f}"
                volatility_str = f"{analysis.volatility:.2f}"
                max_drawdown_str = f"{analysis.max_drawdown:.2f}"
                ai_accuracy_str = f"{analysis.ai_accuracy:.2f}" if analysis.ai_prediction_count > 0 else "N/A"

                print(f"\n[Period: {period_str}]")
                print(f"  - Regime: {regime_str}")
                print(f"  - Average Return: {avg_return_str}%")
                print(f"  - Volatility: {volatility_str}%")
                print(f"  - Max Drawdown: {max_drawdown_str}%")
                print(f"  - AI Accuracy: {ai_accuracy_str}")

            print("--- End of Report ---\n")
            await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error(f"❌ 시장 체제 보고서 표시 오류: {e}")
            console.print(f"[red]❌ 시장 체제 보고서 표시에 실패했습니다: {e}[/red]")

    async def _generate_conclusion_section(
        self,
        backtest_results: List[BacktestResult],
        comparison_results: Optional[Dict[str, StrategyComparison]]
    ) -> str:
        """결론 및 권고사항 섹션 생성"""
        try:
            # 최고 성과 전략
            best_strategy = max(backtest_results, key=lambda x: x.total_return_pct)
            
            # AI 효과가 있는 전략 (비교 결과가 있는 경우)
            ai_effective_strategies = []
            if comparison_results:
                ai_effective_strategies = [
                    name for name, comp in comparison_results.items() 
                    if comp.return_improvement > 2.0  # 2% 이상 개선
                ]
            
            html = f"""
            <div class="section">
                <h2>🎯 결론 및 권고사항</h2>
                
                <h3>📊 주요 발견사항</h3>
                <ul>
                    <li><strong>최고 성과 전략:</strong> {best_strategy.strategy_name} ({best_strategy.total_return_pct:.2f}% 수익률)</li>
                    <li><strong>전체 평균 수익률:</strong> {np.mean([r.total_return_pct for r in backtest_results]):.2f}%</li>
                    <li><strong>수익 전략 비율:</strong> {len([r for r in backtest_results if r.total_return_pct > 0])}개 / {len(backtest_results)}개</li>
            """
            
            if ai_effective_strategies:
                html += f"""
                    <li><strong>AI 효과가 큰 전략:</strong> {', '.join(ai_effective_strategies)}</li>
                """
            
            html += """
                </ul>
                
                <h3>💡 투자 권고사항</h3>
                <ol>
            """
            
            # 권고사항 생성
            if best_strategy.total_return_pct > 10:
                html += f"""
                    <li><strong>우선 고려 전략:</strong> {best_strategy.strategy_name} 전략은 {best_strategy.total_return_pct:.2f}%의 높은 수익률을 보였습니다.</li>
                """
            
            if ai_effective_strategies:
                html += f"""
                    <li><strong>AI 활용:</strong> {', '.join(ai_effective_strategies)} 전략에서 AI 효과가 검증되었으므로 AI 기능을 활용하는 것을 권장합니다.</li>
                """
            
            # 리스크 관리 권고
            high_risk_strategies = [r for r in backtest_results if r.metrics.max_drawdown > 20]
            if high_risk_strategies:
                html += """
                    <li><strong>리스크 관리:</strong> 일부 전략은 높은 드로우다운을 보였으므로 포지션 크기 조절과 손절매 규칙을 엄격히 적용해야 합니다.</li>
                """
            
            # 다양화 권고
            if len(backtest_results) > 1:
                html += """
                    <li><strong>전략 다양화:</strong> 여러 전략을 조합하여 포트폴리오의 위험을 분산하고 안정적인 수익을 추구하시기 바랍니다.</li>
                """
            
            html += """
                    <li><strong>지속적 모니터링:</strong> 시장 환경 변화에 따라 전략의 효과가 달라질 수 있으므로 정기적인 성과 검토가 필요합니다.</li>
                    <li><strong>실전 적용 주의:</strong> 백테스팅 결과와 실전 거래는 차이가 있을 수 있으므로 소액으로 시작하여 점진적으로 확대하시기 바랍니다.</li>
                </ol>
                
                <h3>⚠️ 주의사항</h3>
                <ul>
                    <li>이 결과는 과거 데이터 기반 분석이며 미래 성과를 보장하지 않습니다</li>
                    <li>실제 거래에서는 슬리피지, 수수료, 시장 충격 등이 성과에 영향을 줄 수 있습니다</li>
                    <li>극단적인 시장 상황에서는 전략이 예상과 다르게 작동할 수 있습니다</li>
                    <li>정기적인 전략 검토와 리밸런싱이 필요합니다</li>
                </ul>
            </div>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"❌ 결론 섹션 생성 오류: {e}")
            return f"<div class='section'><h2>결론 섹션 오류</h2><p>{e}</p></div>"