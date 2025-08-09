#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/utils/display.py

Rich 라이브러리를 활용한 터미널 결과 표시 유틸리티
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import List, Dict, Any

console = Console()

class DisplayUtils:
    """결과 표시 유틸리티 클래스"""

    def display_comprehensive_analysis_results(self, results: List[Dict[str, Any]]):
        """종합 분석 결과를 Rich 패널과 테이블로 표시"""
        if not results:
            console.print("[yellow]분석 결과가 없습니다.[/yellow]")
            return

        # 점수 기준으로 내림차순 정렬
        results.sort(key=lambda x: x.get('comprehensive_score', 0), reverse=True)

        console.print(Panel(f"[bold green]종합 분석 결과 ({len(results)}개 종목)[/bold green]", expand=False))

        for i, result in enumerate(results):
            # 기본 정보
            symbol = result.get('symbol', 'N/A')
            name = result.get('name', 'N/A')
            score = result.get('comprehensive_score', 0)
            recommendation = result.get('recommendation', 'HOLD')

            # 추천 등급에 따른 색상
            rec_color = "green" if "BUY" in recommendation else "red" if "SELL" in recommendation else "yellow"

            # 메인 패널 생성
            main_panel_content = Text()
            main_panel_content.append(f"[bold]{name} ({symbol})[/bold]\n")
            main_panel_content.append(f"종합 점수: [bold {rec_color}]{score:.2f}점[/bold {rec_color}] | ")
            main_panel_content.append(f"추천 등급: [bold {rec_color}]{recommendation}[/bold {rec_color}])")

            # 점수 상세 테이블
            score_table = Table.grid(padding=(0, 1))
            score_table.add_column(style="cyan")
            score_table.add_column(style="white")
            scores = {
                "기술": result.get('technical_score', 0),
                "수급": result.get('supply_demand_score', 0),
                "뉴스": result.get('sentiment_score', 0),
                "패턴": result.get('chart_pattern_score', 0)
            }
            score_table.add_row("분석 영역:", " ".join(f"{k}:[bold]{v:.1f}[/bold]" for k, v in scores.items()))
            
            # 뉴스 분석 상세 패널 (장/중/단기)
            sentiment_details = result.get('sentiment_details', {})
            news_panel = self._create_news_panel(sentiment_details)

            # 최종 패널 조합
            console.print(Panel(
                main_panel_content,
                title=f"[bold cyan]분석 {i+1}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            ))
            console.print(score_table)
            console.print(news_panel)
            console.print("-" * 80)

    def _create_news_panel(self, sentiment_details: Dict[str, Any]) -> Panel:
        """장/중/단기 뉴스 분석 결과를 담은 패널 생성"""
        news_table = Table(
            title="[bold]📰 기간별 뉴스 분석[/bold]",
            show_header=True, header_style="bold magenta"
        )
        news_table.add_column("기간", style="cyan", width=15)
        news_table.add_column("점수", style="green", justify="center", width=8)
        news_table.add_column("핵심 요약", style="white")
        news_table.add_column("키워드", style="yellow")

        periods = ['short_term_analysis', 'mid_term_analysis', 'long_term_analysis']
        for period_key in periods:
            period_data = sentiment_details.get(period_key, {})
            if period_data:
                news_table.add_row(
                    period_data.get('period', 'N/A'),
                    f"{period_data.get('score', 50):.1f}",
                    period_data.get('summary', '요약 없음'),
                    ", ".join(period_data.get('keywords', []))
                )
        
        return Panel(news_table, border_style="magenta")

    def display_recommendations_summary(self, results: List[Dict[str, Any]]):
        """추천 등급 요약 표시"""
        if not results:
            return

        buy_count = sum(1 for r in results if "BUY" in r.get('recommendation', ''))
        sell_count = sum(1 for r in results if "SELL" in r.get('recommendation', ''))
        hold_count = len(results) - buy_count - sell_count

        summary_text = (
            f"총 [bold]{len(results)}[/bold]개 종목 분석 완료\n"
            f"  - [green]매수 추천[/green]: {buy_count}개\n"
            f"  - [yellow]보유 추천[/yellow]: {hold_count}개\n"
            f"  - [red]매도 추천[/red]: {sell_count}개"
        )
        console.print(Panel(summary_text, title="[bold blue]분석 요약[/bold blue]", border_style="blue"))