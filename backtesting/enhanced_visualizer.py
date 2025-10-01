#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enhanced_visualizer.py

향상된 백테스팅 시각화 도구 - 직관적이고 인터랙티브한 성과 확인
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import numpy as np
import json

# 시각화 라이브러리
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import seaborn as sns
    from matplotlib.widgets import Slider, Button
    from matplotlib.animation import FuncAnimation
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    VISUALIZATION_AVAILABLE = True
    PLOTLY_AVAILABLE = True
except ImportError as e:
    VISUALIZATION_AVAILABLE = False
    PLOTLY_AVAILABLE = False
    print(f"❌ 시각화 라이브러리가 설치되지 않았습니다: {e}")

# Rich 라이브러리
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
    from rich.layout import Layout
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("❌ Rich 라이브러리가 필요합니다. pip install rich")

from .backtesting_engine import BacktestResult, PerformanceMetrics
from .strategy_validator import StrategyComparison, ValidationResult

logger = logging.getLogger(__name__)
console = Console() if RICH_AVAILABLE else None

@dataclass
class VisualizationConfig:
    """시각화 설정"""
    # 차트 기본 설정
    figsize: Tuple[int, int] = (15, 10)
    dpi: int = 300
    style: str = 'seaborn-v0_8'

    # 색상 테마
    primary_color: str = '#2E86AB'
    secondary_color: str = '#A23B72'
    success_color: str = '#F18F01'
    danger_color: str = '#C73E1D'
    warning_color: str = '#F18F01'
    background_color: str = '#F8F9FA'

    # 인터랙티브 설정
    enable_interactive: bool = True
    enable_animations: bool = True
    auto_refresh_interval: int = 5  # 초

    # 출력 설정
    save_html: bool = True
    save_png: bool = True
    show_plots: bool = False

@dataclass
class MetricCard:
    """메트릭 카드 데이터"""
    title: str
    value: float
    format: str = "{:.2f}"
    unit: str = ""
    status: str = "neutral"  # positive, negative, neutral
    description: str = ""
    trend: Optional[float] = None

class EnhancedVisualizer:
    """향상된 시각화 도구"""

    def __init__(self, config=None, output_dir: str = "reports"):
        """향상된 시각화 도구 초기화"""
        self.trading_config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 출력 디렉토리 구조
        self.charts_dir = self.output_dir / "charts"
        self.interactive_dir = self.output_dir / "interactive"
        self.data_dir = self.output_dir / "data"

        for dir_path in [self.charts_dir, self.interactive_dir, self.data_dir]:
            dir_path.mkdir(exist_ok=True)

        self.config = VisualizationConfig()
        self.logger = logging.getLogger(__name__)

        # 스타일 설정
        if VISUALIZATION_AVAILABLE:
            plt.style.use('default')
            sns.set_palette("husl")

    async def create_interactive_dashboard(
        self,
        backtest_results: List[BacktestResult],
        comparison_results: Optional[Dict[str, StrategyComparison]] = None,
        live_mode: bool = False
    ) -> str:
        """
        인터랙티브 대시보드 생성

        Args:
            backtest_results: 백테스팅 결과 리스트
            comparison_results: 전략 비교 결과
            live_mode: 라이브 모드 (실시간 업데이트)

        Returns:
            생성된 대시보드 파일 경로
        """
        try:
            if not PLOTLY_AVAILABLE:
                self.logger.warning("⚠️ Plotly가 설치되지 않아 기본 시각화를 사용합니다")
                return await self._create_basic_dashboard(backtest_results)

            console.print("[cyan]🚀 인터랙티브 대시보드 생성 중...[/cyan]")

            # 대시보드 생성
            dashboard_html = await self._create_plotly_dashboard(
                backtest_results, comparison_results, live_mode
            )

            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dashboard_file = self.interactive_dir / f"dashboard_{timestamp}.html"

            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)

            console.print(f"[green]✅ 대시보드 생성 완료: {dashboard_file}[/green]")

            return str(dashboard_file)

        except Exception as e:
            self.logger.error(f"❌ 대시보드 생성 실패: {e}")
            return await self._create_basic_dashboard(backtest_results)

    async def _create_plotly_dashboard(
        self,
        backtest_results: List[BacktestResult],
        comparison_results: Optional[Dict[str, StrategyComparison]],
        live_mode: bool
    ) -> str:
        """Plotly 기반 인터랙티브 대시보드"""

        # 메인 대시보드 레이아웃
        fig = make_subplots(
            rows=3, cols=3,
            subplot_titles=[
                "포트폴리오 성과 추이", "수익률 분포", "드로우다운 분석",
                "월별 수익률", "전략 비교", "리스크-수익 산점도",
                "거래 분석", "AI 성과", "종합 지표"
            ],
            specs=[
                [{"secondary_y": True}, {"type": "histogram"}, {"type": "scatter"}],
                [{"type": "bar"}, {"type": "bar"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "scatter"}, {"type": "indicator"}]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.08
        )

        # 각 결과에 대해 차트 생성
        for i, result in enumerate(backtest_results):
            color = px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]

            # 1. 포트폴리오 성과 추이
            if result.equity_curve:
                dates = [point['date'] for point in result.equity_curve]
                values = [point['portfolio_value'] for point in result.equity_curve]

                fig.add_trace(
                    go.Scatter(
                        x=dates, y=values,
                        name=result.strategy_name,
                        line=dict(color=color, width=2),
                        hovertemplate='<b>%{text}</b><br>날짜: %{x}<br>가치: ₩%{y:,.0f}<extra></extra>',
                        text=[result.strategy_name] * len(dates)
                    ),
                    row=1, col=1
                )

            # 2. 수익률 분포
            if result.trades:
                pnl_values = []
                for trade in result.trades:
                    if trade['action'] == 'SELL' and 'net_amount' in trade:
                        pnl = trade['net_amount'] - abs(trade['quantity']) * trade['price']
                        pnl_values.append(pnl)

                if pnl_values:
                    fig.add_trace(
                        go.Histogram(
                            x=pnl_values,
                            name=f"{result.strategy_name} 손익분포",
                            opacity=0.7,
                            marker_color=color
                        ),
                        row=1, col=2
                    )

            # 3. 드로우다운
            if result.equity_curve:
                dates = [point['date'] for point in result.equity_curve]
                values = [point['portfolio_value'] for point in result.equity_curve]

                # 드로우다운 계산
                peak = values[0]
                drawdowns = []
                for value in values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak * 100
                    drawdowns.append(-drawdown)

                fig.add_trace(
                    go.Scatter(
                        x=dates, y=drawdowns,
                        name=f"{result.strategy_name} DD",
                        fill='tonexty' if i == 0 else None,
                        line=dict(color=color),
                        hovertemplate='<b>%{text}</b><br>날짜: %{x}<br>드로우다운: %{y:.2f}%<extra></extra>',
                        text=[result.strategy_name] * len(dates)
                    ),
                    row=1, col=3
                )

        # 4. 월별 수익률 (첫 번째 결과만)
        if backtest_results and backtest_results[0].equity_curve:
            result = backtest_results[0]
            monthly_returns = self._calculate_monthly_returns(result)

            if monthly_returns:
                months = list(monthly_returns.keys())
                returns = list(monthly_returns.values())
                colors = ['green' if r >= 0 else 'red' for r in returns]

                fig.add_trace(
                    go.Bar(
                        x=[m.strftime('%Y-%m') for m in months],
                        y=returns,
                        name="월별 수익률",
                        marker_color=colors,
                        hovertemplate='월: %{x}<br>수익률: %{y:.2f}%<extra></extra>'
                    ),
                    row=2, col=1
                )

        # 5. 전략 비교
        if comparison_results:
            strategies = list(comparison_results.keys())
            ai_returns = [comp.with_ai_result.metrics.annual_return for comp in comparison_results.values()]
            traditional_returns = [comp.without_ai_result.metrics.annual_return for comp in comparison_results.values()]

            fig.add_trace(
                go.Bar(x=strategies, y=ai_returns, name="AI 강화", marker_color=self.config.primary_color),
                row=2, col=2
            )
            fig.add_trace(
                go.Bar(x=strategies, y=traditional_returns, name="전통적", marker_color=self.config.secondary_color),
                row=2, col=2
            )

        # 6. 리스크-수익 산점도
        for i, result in enumerate(backtest_results):
            fig.add_trace(
                go.Scatter(
                    x=[result.metrics.volatility],
                    y=[result.metrics.annual_return],
                    mode='markers+text',
                    name=result.strategy_name,
                    text=[result.strategy_name],
                    textposition="top center",
                    marker=dict(
                        size=15,
                        color=px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
                    ),
                    hovertemplate='<b>%{text}</b><br>변동성: %{x:.2f}%<br>연수익률: %{y:.2f}%<extra></extra>'
                ),
                row=2, col=3
            )

        # 레이아웃 설정
        fig.update_layout(
            title={
                'text': '🤖 AI Trading System - 백테스팅 대시보드',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 24}
            },
            height=1200,
            showlegend=True,
            template='plotly_white',
            font=dict(family="Arial, sans-serif", size=12)
        )

        # 축 라벨 설정
        fig.update_xaxes(title_text="날짜", row=1, col=1)
        fig.update_yaxes(title_text="포트폴리오 가치 (원)", row=1, col=1)

        fig.update_xaxes(title_text="손익 (원)", row=1, col=2)
        fig.update_yaxes(title_text="빈도", row=1, col=2)

        fig.update_xaxes(title_text="날짜", row=1, col=3)
        fig.update_yaxes(title_text="드로우다운 (%)", row=1, col=3)

        fig.update_xaxes(title_text="월", row=2, col=1)
        fig.update_yaxes(title_text="수익률 (%)", row=2, col=1)

        fig.update_xaxes(title_text="전략", row=2, col=2)
        fig.update_yaxes(title_text="연간 수익률 (%)", row=2, col=2)

        fig.update_xaxes(title_text="변동성 (%)", row=2, col=3)
        fig.update_yaxes(title_text="연간 수익률 (%)", row=2, col=3)

        # HTML 생성
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'backtest_dashboard',
                'height': 1200,
                'width': 1600,
                'scale': 1
            }
        }

        html_string = fig.to_html(
            config=config,
            include_plotlyjs='cdn',
            div_id="dashboard"
        )

        # 추가 기능을 위한 JavaScript 코드 삽입
        additional_js = """
        <script>
        // 실시간 업데이트 기능
        function refreshDashboard() {
            console.log('대시보드 새로고침...');
            // TODO: 백엔드에서 새 데이터 가져와서 업데이트
        }

        // 자동 새로고침 (5분마다)
        if (""" + str(live_mode).lower() + """) {
            setInterval(refreshDashboard, 300000);
        }

        // 추가 인터랙션
        document.addEventListener('DOMContentLoaded', function() {
            console.log('대시보드 로드 완료');
        });
        </script>

        <style>
        .plotly-graph-div {
            margin: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
        }

        body {
            font-family: 'Arial', sans-serif;
            background-color: #f8f9fa;
            margin: 0;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        </style>
        """

        # 헤더 추가
        header_html = f"""
        <div class="header">
            <h1>🤖 AI Trading System Dashboard</h1>
            <p>생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>분석된 전략: {len(backtest_results)}개</p>
        </div>
        """

        # 최종 HTML 조합
        final_html = html_string.replace(
            '<head>',
            '<head><meta charset="utf-8"><title>AI Trading Dashboard</title>'
        ).replace(
            '<body>',
            f'<body>{header_html}'
        ).replace(
            '</body>',
            f'{additional_js}</body>'
        )

        return final_html

    async def _create_basic_dashboard(self, backtest_results: List[BacktestResult]) -> str:
        """기본 대시보드 (Matplotlib 기반)"""
        try:
            if not VISUALIZATION_AVAILABLE:
                return "시각화 라이브러리가 설치되지 않았습니다."

            # 기본 차트 생성
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            axes = axes.flatten()

            # 각 결과에 대해 기본 차트 생성
            for i, result in enumerate(backtest_results):
                if i >= len(axes):
                    break

                # 수익률 곡선
                if result.equity_curve:
                    dates = [point['date'] for point in result.equity_curve]
                    values = [point['portfolio_value'] for point in result.equity_curve]

                    axes[i].plot(dates, values, linewidth=2, label=result.strategy_name)
                    axes[i].set_title(f"{result.strategy_name} 성과")
                    axes[i].set_ylabel("포트폴리오 가치")
                    axes[i].grid(True, alpha=0.3)
                    axes[i].legend()

            plt.tight_layout()

            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.charts_dir / f"basic_dashboard_{timestamp}.png"
            plt.savefig(filename, dpi=self.config.dpi, bbox_inches='tight')
            plt.close()

            return str(filename)

        except Exception as e:
            self.logger.error(f"❌ 기본 대시보드 생성 실패: {e}")
            return "대시보드 생성 실패"

    def _calculate_monthly_returns(self, result: BacktestResult) -> Dict:
        """월별 수익률 계산"""
        try:
            if not result.equity_curve:
                return {}

            monthly_data = {}
            current_month = None
            month_start_value = None

            for point in result.equity_curve:
                date = point['date']
                value = point['portfolio_value']

                month_key = date.replace(day=1)

                if current_month != month_key:
                    if current_month and month_start_value:
                        monthly_return = (value - month_start_value) / month_start_value * 100
                        monthly_data[current_month] = monthly_return

                    current_month = month_key
                    month_start_value = value

            return monthly_data

        except Exception as e:
            self.logger.error(f"❌ 월별 수익률 계산 실패: {e}")
            return {}

    async def create_real_time_monitor(
        self,
        trading_handler=None,
        refresh_interval: int = 5
    ) -> str:
        """
        실시간 모니터링 대시보드

        Args:
            trading_handler: 거래 핸들러
            refresh_interval: 새로고침 간격(초)

        Returns:
            모니터링 대시보드 파일 경로
        """
        try:
            if not RICH_AVAILABLE:
                self.logger.warning("⚠️ Rich 라이브러리가 없어 간단한 모니터링을 제공합니다")
                return await self._create_simple_monitor()

            console.print("[cyan]📊 실시간 모니터링 시작...[/cyan]")

            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main", ratio=1),
                Layout(name="footer", size=3)
            )

            layout["main"].split_row(
                Layout(name="left"),
                Layout(name="right")
            )

            layout["left"].split_column(
                Layout(name="portfolio"),
                Layout(name="positions")
            )

            layout["right"].split_column(
                Layout(name="performance"),
                Layout(name="orders")
            )

            # 실시간 데이터 수집 및 표시
            async def update_data():
                while True:
                    try:
                        # 헤더 업데이트
                        layout["header"].update(
                            Panel(
                                f"🤖 AI Trading System - 실시간 모니터링\n"
                                f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                style="bold blue"
                            )
                        )

                        # 포트폴리오 정보 (예시)
                        portfolio_table = Table(title="포트폴리오 현황")
                        portfolio_table.add_column("항목", style="cyan")
                        portfolio_table.add_column("값", style="magenta")

                        # TODO: 실제 데이터로 교체
                        portfolio_table.add_row("총 자산", "₩10,000,000")
                        portfolio_table.add_row("현금", "₩3,000,000")
                        portfolio_table.add_row("주식", "₩7,000,000")
                        portfolio_table.add_row("일일 수익", "+2.5%")

                        layout["portfolio"].update(portfolio_table)

                        # 보유 포지션 (예시)
                        positions_table = Table(title="보유 포지션")
                        positions_table.add_column("종목", style="cyan")
                        positions_table.add_column("수량", style="magenta")
                        positions_table.add_column("수익률", style="green")

                        # TODO: 실제 데이터로 교체
                        positions_table.add_row("삼성전자", "100주", "+3.2%")
                        positions_table.add_row("SK하이닉스", "50주", "-1.1%")

                        layout["positions"].update(positions_table)

                        # 성과 지표 (예시)
                        performance_table = Table(title="성과 지표")
                        performance_table.add_column("지표", style="cyan")
                        performance_table.add_column("값", style="magenta")

                        performance_table.add_row("총 수익률", "+15.3%")
                        performance_table.add_row("승률", "68.5%")
                        performance_table.add_row("샤프비율", "1.42")
                        performance_table.add_row("최대낙폭", "-5.2%")

                        layout["performance"].update(performance_table)

                        # 최근 주문 (예시)
                        orders_table = Table(title="최근 주문")
                        orders_table.add_column("시간", style="cyan")
                        orders_table.add_column("종목", style="magenta")
                        orders_table.add_column("구분", style="green")

                        orders_table.add_row("14:30", "NAVER", "매수")
                        orders_table.add_row("14:25", "카카오", "매도")

                        layout["orders"].update(orders_table)

                        # 푸터
                        layout["footer"].update(
                            Panel(
                                "💡 Ctrl+C로 종료 | 자동 새로고침 5초",
                                style="dim"
                            )
                        )

                        await asyncio.sleep(refresh_interval)

                    except Exception as e:
                        self.logger.error(f"❌ 모니터링 업데이트 실패: {e}")
                        await asyncio.sleep(refresh_interval)

            # 실시간 모니터링 시작
            with Live(layout, refresh_per_second=1) as live:
                await update_data()

            return "실시간 모니터링 완료"

        except Exception as e:
            self.logger.error(f"❌ 실시간 모니터링 실패: {e}")
            return "실시간 모니터링 실패"

    async def _create_simple_monitor(self) -> str:
        """간단한 모니터링"""
        try:
            monitor_data = {
                "timestamp": datetime.now().isoformat(),
                "portfolio": {
                    "total_value": 10000000,
                    "cash": 3000000,
                    "stocks": 7000000,
                    "daily_pnl": 2.5
                },
                "positions": [
                    {"symbol": "005930", "quantity": 100, "pnl_pct": 3.2},
                    {"symbol": "000660", "quantity": 50, "pnl_pct": -1.1}
                ]
            }

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            monitor_file = self.data_dir / f"monitor_{timestamp}.json"

            with open(monitor_file, 'w', encoding='utf-8') as f:
                json.dump(monitor_data, f, ensure_ascii=False, indent=2)

            return str(monitor_file)

        except Exception as e:
            self.logger.error(f"❌ 간단한 모니터링 실패: {e}")
            return "모니터링 실패"

    async def create_strategy_comparison_heatmap(
        self,
        comparison_results: Dict[str, StrategyComparison]
    ) -> Optional[str]:
        """전략 비교 히트맵 생성"""
        try:
            if not PLOTLY_AVAILABLE:
                return None

            # 데이터 준비
            strategies = list(comparison_results.keys())
            metrics = ['수익률', '샤프비율', '최대낙폭', '승률', 'AI효과']

            data_matrix = []
            for strategy in strategies:
                comp = comparison_results[strategy]
                row = [
                    comp.with_ai_result.metrics.annual_return,
                    comp.with_ai_result.metrics.sharpe_ratio,
                    -comp.with_ai_result.metrics.max_drawdown,  # 음수를 양수로
                    comp.with_ai_result.metrics.win_rate,
                    comp.return_improvement
                ]
                data_matrix.append(row)

            # 정규화 (0-100 스케일)
            data_matrix = np.array(data_matrix)
            for i in range(data_matrix.shape[1]):
                col = data_matrix[:, i]
                col_min, col_max = col.min(), col.max()
                if col_max > col_min:
                    data_matrix[:, i] = (col - col_min) / (col_max - col_min) * 100

            # 히트맵 생성
            fig = go.Figure(data=go.Heatmap(
                z=data_matrix,
                x=metrics,
                y=strategies,
                colorscale='RdYlGn',
                hoverongaps=False,
                hovertemplate='전략: %{y}<br>지표: %{x}<br>점수: %{z:.1f}<extra></extra>'
            ))

            fig.update_layout(
                title='전략 성과 히트맵',
                xaxis_title='성과 지표',
                yaxis_title='전략',
                height=400 + len(strategies) * 30
            )

            # 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.interactive_dir / f"heatmap_{timestamp}.html"
            fig.write_html(str(filename))

            return str(filename)

        except Exception as e:
            self.logger.error(f"❌ 히트맵 생성 실패: {e}")
            return None

# 사용 예시
async def main():
    """테스트 함수"""
    visualizer = EnhancedVisualizer()

    # 예시 백테스팅 결과 (실제로는 백테스팅 엔진에서 받아옴)
    # results = [...]

    # 대시보드 생성
    # dashboard_path = await visualizer.create_interactive_dashboard(results)
    # print(f"대시보드 생성됨: {dashboard_path}")

    # 실시간 모니터링
    # await visualizer.create_real_time_monitor()

if __name__ == "__main__":
    asyncio.run(main())