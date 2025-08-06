#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/utils/display.py

결과 표시 유틸리티 - Rich를 활용한 UI 출력 (완전 새로 작성)
"""

from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

console = Console()

class DisplayUtils:
    """결과 표시 유틸리티 클래스"""
    
    def __init__(self):
        pass
    
    def display_recommendations_summary(self, results: List[Dict]):
        """추천 종목 요약 표시"""
        try:
            if not results:
                console.print("[yellow]📊 추천할 종목이 없습니다.[/yellow]")
                return
            
            # 매수 추천 종목들 필터링
            buy_recommendations = [
                r for r in results 
                if r.get('recommendation') in ['BUY', 'STRONG_BUY', 'ULTRA_STRONG_BUY']
            ]
            
            if not buy_recommendations:
                console.print("[yellow]📊 현재 매수 추천 종목이 없습니다.[/yellow]")
                return
            
            # 점수순 정렬
            buy_recommendations.sort(key=lambda x: x.get('comprehensive_score', 0), reverse=True)
            
            # TOP 5 추천 종목 표시
            console.print("\n")
            console.print(Panel.fit(
                "[bold green]🎯 AI 추천 종목 TOP 5[/bold green]",
                border_style="green"
            ))
            
            recommendation_panels = []
            
            for i, stock in enumerate(buy_recommendations[:5], 1):
                symbol = stock.get('symbol', '')
                name = stock.get('name', '')
                score = stock.get('comprehensive_score', 0)
                recommendation = stock.get('recommendation', '')
                
                # 5개 영역 점수 추출
                tech_score = self._safe_get_score(stock, 'technical_analysis')
                fund_score = self._safe_get_score(stock, 'fundamental_analysis')
                news_score = self._safe_get_score(stock, 'sentiment_analysis')
                supply_score = self._safe_get_score(stock, 'supply_demand_analysis')
                pattern_score = self._safe_get_score(stock, 'chart_pattern_analysis')
                
                # 뉴스 재료 확인
                has_news_material = self._safe_get_news_material(stock)
                news_icon = "📰" if has_news_material else ""
                
                # 추천 등급 아이콘
                rec_icon = self._get_recommendation_icon(recommendation)
                
                # 개별 종목 패널 생성
                stock_content = f"""[bold]{symbol} {name}[/bold] {news_icon}\n[bold green]종합점수: {score:.1f}점[/bold green] {rec_icon}\n\n[blue]📊 5개 영역 분석[/blue]\n• 기술적: {tech_score:.1f}점\n• 펀더멘털: {fund_score:.1f}점\n• 뉴스감정: {news_score:.1f}점\n• 수급정보: {supply_score:.1f}점\n• 차트패턴: {pattern_score:.1f}점\n\n[yellow]추천등급: {recommendation}[/yellow]"""
                
                panel = Panel(
                    stock_content,
                    title=f"#{i}",
                    border_style="green" if i <= 3 else "yellow",
                    width=35
                )
                recommendation_panels.append(panel)
            
            # 2열로 배치
            if len(recommendation_panels) >= 2:
                console.print(Columns(recommendation_panels[:2], equal=True, expand=True))
                if len(recommendation_panels) >= 4:
                    console.print(Columns(recommendation_panels[2:4], equal=True, expand=True))
                if len(recommendation_panels) == 5:
                    console.print(Align.center(recommendation_panels[4]))
            else:
                console.print(Align.center(recommendation_panels[0]))
            
            # 추천 요약 통계
            self._display_recommendation_stats(buy_recommendations, len(results))
            
        except Exception as e:
            console.print(f"[red]❌ 추천 요약 생성 실패: {e}[/red]")
    
    def _get_recommendation_icon(self, recommendation: str) -> str:
        """추천 등급별 아이콘"""
        icons = {
            'ULTRA_STRONG_BUY': '🚀🚀🚀',
            'STRONG_BUY': '🚀🚀',
            'BUY': '🚀',
            'WEAK_BUY': '📈',
            'HOLD': '⏸️',
            'WEAK_SELL': '📉',
            'SELL': '⬇️',
            'STRONG_SELL': '⬇️⬇️'
        }
        return icons.get(recommendation, '❓')
    
    def _display_recommendation_stats(self, recommendations: List[Dict], total_count: int):
        """추천 통계 표시"""
        try:
            ultra_strong = len([r for r in recommendations if r.get('recommendation') == 'ULTRA_STRONG_BUY'])
            strong = len([r for r in recommendations if r.get('recommendation') == 'STRONG_BUY'])
            normal = len([r for r in recommendations if r.get('recommendation') == 'BUY'])
            
            avg_score = sum(r.get('comprehensive_score', 0) for r in recommendations) / len(recommendations)
            high_score_count = len([r for r in recommendations if r.get('comprehensive_score', 0) >= 80])
            news_material_count = len([r for r in recommendations if self._safe_get_news_material(r)])
            
            stats_content = f"""[bold cyan]📈 투자 추천 요약[/bold cyan]\n\n[bold]기본 통계[/bold]\n• 전체 분석 종목: {total_count}개\n• 매수 추천 종목: {len(recommendations)}개 ({len(recommendations)/total_count*100:.1f}%)\n• 평균 추천 점수: {avg_score:.1f}점\n\n[bold green]추천 등급 분포[/bold green]\n• 🚀🚀🚀 초강력매수: {ultra_strong}개\n• 🚀🚀 강력매수: {strong}개  \n• 🚀 매수: {normal}개\n\n[bold blue]품질 지표[/bold blue]\n• 고득점(80+) 종목: {high_score_count}개\n• 뉴스재료 보유: {news_material_count}개\n• 투자 적합도: {'매우높음' if avg_score >= 75 else '높음' if avg_score >= 65 else '보통'}\n\n[bold yellow]💡 투자 가이드[/bold yellow]\n1. 🚀🚀🚀 초강력매수 종목을 최우선 검토\n2. 뉴스재료가 있는 종목은 타이밍 중요\n3. 80점 이상 고득점 종목에 집중 투자\n4. 분산투자로 리스크 관리 필수"""
            
            console.print(Panel(
                stats_content,
                title="🎯 AI 투자 가이드",
                border_style="cyan",
                width=80
            ))
            
        except Exception as e:
            console.print(f"[red]❌ 추천 통계 생성 실패: {e}[/red]")
    
    def display_comprehensive_analysis_results(self, results: List[Dict]):
        """종합 분석 결과 표시"""
        if not results:
            console.print("[yellow]📊 분석 결과가 없습니다.[/yellow]")
            return
        # ⭐ 전략 확인 (안전한 방식)
        strategy = 'default'
        if results and len(results) > 0:
            strategy = results[0].get('strategy', 'default')
        
        # ⭐ Supertrend 전략일 때만 특별 표시  
        if strategy == 'supertrend_ema_rsi':
            self._display_supertrend_results(results)
            return
        
        # 결과 정렬
        sorted_results = sorted(results, key=lambda x: x.get('comprehensive_score', 0), reverse=True)
        
        # 메인 결과 테이블
        table = Table(title="📈 5개 영역 통합 분석 결과", show_header=True, header_style="bold magenta")
        table.add_column("순위", style="cyan", width=4, justify="center")
        table.add_column("종목", style="bold white", width=12)
        table.add_column("종합", style="bold green", width=6, justify="center")
        table.add_column("기술적", style="blue", width=6, justify="center")
        table.add_column("펀더멘털", style="magenta", width=8, justify="center")
        table.add_column("뉴스", style="yellow", width=6, justify="center")
        table.add_column("수급", style="cyan", width=6, justify="center")
        table.add_column("패턴", style="red", width=6, justify="center")
        table.add_column("추천", style="bold", width=10, justify="center")
        table.add_column("재료", style="orange3", width=4, justify="center")
        
        for i, result in enumerate(sorted_results[:20], 1):
            symbol = result.get('symbol', 'N/A')
            name = result.get('name', 'N/A')
            
            # 종목명 줄임
            display_name = f"{symbol}\n{name[:8]}" if len(name) > 8 else f"{symbol}\n{name}"
            
            # 5개 영역 점수
            comprehensive = result.get('comprehensive_score', 0)
            tech_score = self._safe_get_score(result, 'technical_analysis')
            fund_score = self._safe_get_score(result, 'fundamental_analysis')
            news_score = self._safe_get_score(result, 'sentiment_analysis')
            supply_score = self._safe_get_score(result, 'supply_demand_analysis')
            pattern_score = self._safe_get_score(result, 'chart_pattern_analysis')
            
            # 추천 및 재료
            recommendation = result.get('recommendation', 'HOLD')
            has_material = self._safe_get_news_material(result)
            
            # 색상 적용
            rec_display = self._format_recommendation_text(recommendation)
            material_icon = "📰" if has_material else ""
            
            table.add_row(
                str(i),
                display_name,
                self._score_with_color(comprehensive),
                self._score_with_color(tech_score),
                self._score_with_color(fund_score),
                self._score_with_color(news_score),
                self._score_with_color(supply_score),
                self._score_with_color(pattern_score),
                rec_display,
                material_icon
            )
        
        console.print(table)
        
        # 분석 통계
        self._display_analysis_summary(sorted_results)
    
    def _display_analysis_summary(self, results: List[Dict]):
        """분석 요약 통계"""
        total = len(results)
        avg_score = sum(r.get('comprehensive_score', 0) for r in results) / total if total > 0 else 0
        
        # 점수 분포
        excellent = len([r for r in results if r.get('comprehensive_score', 0) >= 85])
        good = len([r for r in results if 70 <= r.get('comprehensive_score', 0) < 85])
        average = len([r for r in results if 50 <= r.get('comprehensive_score', 0) < 70])
        poor = len([r for r in results if r.get('comprehensive_score', 0) < 50])
        
        # 추천 분포
        strong_buy = len([r for r in results if r.get('recommendation') in ['ULTRA_STRONG_BUY', 'STRONG_BUY']])
        buy = len([r for r in results if r.get('recommendation') == 'BUY'])
        hold = len([r for r in results if r.get('recommendation') == 'HOLD'])
        sell = len([r for r in results if r.get('recommendation') in ['SELL', 'STRONG_SELL']])
        
        # 재료 보유 종목
        with_material = len([r for r in results if self._safe_get_news_material(r)])
        
        summary_content = f"""[bold]📊 5개 영역 통합 분석 요약[/bold]\n\n[cyan]기본 통계[/cyan]\n• 총 분석 종목: {total}개\n• 평균 종합 점수: {avg_score:.1f}점\n• 뉴스 재료 보유: {with_material}개 ({with_material/total*100:.1f}%)\n\n[green]점수 분포[/green]\n• 🌟 우수(85+): {excellent}개 ({excellent/total*100:.1f}%)\n• ✅ 양호(70-84): {good}개 ({good/total*100:.1f}%)\n• 📊 보통(50-69): {average}개 ({average/total*100:.1f}%)\n• ⚠️ 부진(50미만): {poor}개 ({poor/total*100:.1f}%)\n\n[yellow]투자 추천 분포[/yellow]\n• 🚀 강력매수: {strong_buy}개\n• 📈 매수: {buy}개\n• ⏸️ 보유: {hold}개\n• 📉 매도: {sell}개\n\n[bold blue]✨ AI 분석 특징[/bold blue]\n✅ 기술적 분석 (30% 가중치)\n✅ 펀더멘털 분석 (25% 가중치)  \n✅ 뉴스 감정 분석 (25% 가중치)\n✅ 수급 정보 분석 (10% 가중치)\n✅ 차트 패턴 분석 (10% 가중치)"""
        
        console.print(Panel(
            summary_content,
            title="📈 종합 분석 요약",
            border_style="blue",
            width=60
        ))
    
    def display_news_analysis_results(self, news_results: List[Dict]):
        """뉴스 분석 결과 표시"""
        if not news_results:
            console.print("[yellow]📰 뉴스 분석 결과가 없습니다.[/yellow]")
            return
        
        # 재료가 있는 종목들만 필터링
        material_stocks = [r for r in news_results if r.get('has_material', False)]
        
        if not material_stocks:
            console.print("[yellow]📰 현재 특별한 뉴스 재료를 가진 종목이 없습니다.[/yellow]")
            return
        
        # 재료 점수순 정렬
        material_stocks.sort(key=lambda x: x.get('material_score', 0), reverse=True)
        
        # 뉴스 재료 테이블
        table = Table(title="📰 뉴스 재료 분석 결과", show_header=True, header_style="bold cyan")
        table.add_column("순위", style="cyan", width=4, justify="center")
        table.add_column("종목", style="bold white", width=15)
        table.add_column("재료유형", style="green", width=10, justify="center")
        table.add_column("재료점수", style="yellow", width=8, justify="center")
        table.add_column("뉴스수", style="blue", width=6, justify="center")
        table.add_column("감정", style="magenta", width=8, justify="center")
        table.add_column("핵심키워드", style="white", width=25)
        
        for i, stock in enumerate(material_stocks[:15], 1):
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            material_type = stock.get('material_type', '')
            material_score = stock.get('material_score', 0)
            news_count = stock.get('news_count', 0)
            sentiment_score = stock.get('sentiment_score', 0)
            keywords = stock.get('keywords', [])
            
            # 포맷팅
            display_name = f"{symbol}\n{name[:10]}" if len(name) > 10 else f"{symbol}\n{name}"
            type_display = self._format_material_type(material_type)
            sentiment_display = self._format_sentiment(sentiment_score)
            keywords_display = ", ".join(keywords[:3]) if keywords else "-"
            
            table.add_row(
                str(i),
                display_name,
                type_display,
                f"{material_score:.1f}",
                str(news_count),
                sentiment_display,
                keywords_display
            )
        
        console.print(table)
        
        # 뉴스 분석 요약
        self._display_news_summary(material_stocks, len(news_results))
    
    def _display_news_summary(self, material_stocks: List[Dict], total_count: int):
        """뉴스 분석 요약"""
        material_count = len(material_stocks)
        avg_score = sum(s.get('material_score', 0) for s in material_stocks) / material_count if material_count > 0 else 0
        
        # 재료 유형별 분포
        long_term = len([s for s in material_stocks if s.get('material_type') == '장기재료'])
        mid_term = len([s for s in material_stocks if s.get('material_type') == '중기재료'])
        short_term = len([s for s in material_stocks if s.get('material_type') == '단기재료'])
        
        # 감정 분포
        positive = len([s for s in material_stocks if s.get('sentiment_score', 0) > 0])
        neutral = len([s for s in material_stocks if s.get('sentiment_score', 0) == 0])
        negative = len([s for s in material_stocks if s.get('sentiment_score', 0) < 0])
        
        summary_content = f"""[bold]📊 뉴스 재료 분석 요약[/bold]\n\n[cyan]기본 현황[/cyan]\n• 전체 분석: {total_count}개 종목\n• 재료 보유: {material_count}개 종목 ({material_count/total_count*100:.1f}%)\n• 평균 재료 점수: {avg_score:.1f}점\n\n[green]재료 유형별 분포[/green]\n• 🔵 장기재료: {long_term}개 (중장기 투자)\n• 🟡 중기재료: {mid_term}개 (단기~중기)\n• 🔴 단기재료: {short_term}개 (단기 트레이딩)\n\n[yellow]시장 감정 분포[/yellow]\n• 긍정적: {positive}개\n• 중립적: {neutral}개\n• 부정적: {negative}개\n\n[bold blue]💡 뉴스 투자 전략[/bold blue]\n1. 장기재료 종목은 중장기 관점에서 접근\n2. 단기재료는 빠른 진입/청산 전략 고려\n3. 감정 점수가 높은 종목일수록 상승 모멘텀 기대\n4. 재료 점수 70점 이상 종목에 집중"""
        
        console.print(Panel(
            summary_content,
            title="📰 뉴스 재료 투자 가이드",
            border_style="cyan",
            width=65
        ))
    
    def display_supply_demand_results(self, supply_results: List[Dict]):
        """수급 분석 결과 표시"""
        if not supply_results:
            console.print("[yellow]💰 수급 분석 결과가 없습니다.[/yellow]")
            return
        
        # 수급 점수순 정렬
        supply_results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # 수급 분석 테이블
        table = Table(title="💰 수급정보 분석 결과", show_header=True, header_style="bold green")
        table.add_column("순위", style="cyan", width=4, justify="center")
        table.add_column("종목", style="bold white", width=12)
        table.add_column("종합", style="bold green", width=6, justify="center")
        table.add_column("외국인", style="blue", width=7, justify="center")
        table.add_column("기관", style="cyan", width=6, justify="center")
        table.add_column("개인", style="yellow", width=6, justify="center")
        table.add_column("거래량", style="magenta", width=7, justify="center")
        table.add_column("스마트머니", style="red", width=9, justify="center")
        table.add_column("거래강도", style="orange3", width=8, justify="center")
        
        for i, result in enumerate(supply_results[:20], 1):
            symbol = result.get('symbol', '')
            name = result.get('name', '')
            overall_score = result.get('overall_score', 0)
            foreign_score = result.get('foreign_score', 0)
            institution_score = result.get('institution_score', 0)
            individual_score = result.get('individual_score', 0)
            volume_score = result.get('volume_score', 0)
            smart_money = result.get('smart_money_dominance', False)
            intensity = result.get('trading_intensity', 'normal')
            
            # 포맷팅
            display_name = f"{symbol}\n{name[:6]}" if len(name) > 6 else f"{symbol}\n{name}"
            smart_display = "[bold green]✓[/bold green]" if smart_money else "[dim]✗[/dim]"
            intensity_display = self._format_trading_intensity(intensity)
            
            table.add_row(
                str(i),
                display_name,
                self._score_with_color(overall_score),
                self._score_with_color(foreign_score),
                self._score_with_color(institution_score),
                self._score_with_color(individual_score),
                self._score_with_color(volume_score),
                smart_display,
                intensity_display
            )
        
        console.print(table)
        
        # 수급 분석 요약
        self._display_supply_summary(supply_results)
    
    def _display_supply_summary(self, supply_results: List[Dict]):
        """수급 분석 요약"""
        total = len(supply_results)
        avg_score = sum(r.get('overall_score', 0) for r in supply_results) / total if total > 0 else 0
        
        # 스마트머니 및 거래강도
        smart_money_count = len([r for r in supply_results if r.get('smart_money_dominance', False)])
        high_intensity = len([r for r in supply_results if r.get('trading_intensity') in ['very_high', 'high']])
        
        # 점수별 분포
        excellent = len([r for r in supply_results if r.get('overall_score', 0) >= 80])
        good = len([r for r in supply_results if 60 <= r.get('overall_score', 0) < 80])
        average = len([r for r in supply_results if 40 <= r.get('overall_score', 0) < 60])
        poor = len([r for r in supply_results if r.get('overall_score', 0) < 40])
        
        # 투자주체별 우수 종목
        foreign_strong = len([r for r in supply_results if r.get('foreign_score', 0) >= 70])
        institution_strong = len([r for r in supply_results if r.get('institution_score', 0) >= 70])
        
        summary_content = f"""[bold]📊 수급정보 분석 요약[/bold]\n\n[cyan]기본 통계[/cyan]\n• 전체 분석: {total}개 종목\n• 평균 수급 점수: {avg_score:.1f}점\n• 스마트머니 우세: {smart_money_count}개 ({smart_money_count/total*100:.1f}%)\n• 고강도 거래: {high_intensity}개 ({high_intensity/total*100:.1f}%)\n\n[green]수급 품질 분포[/green]\n• 🌟 우수(80+): {excellent}개\n• ✅ 양호(60-79): {good}개\n• 📊 보통(40-59): {average}개\n• ⚠️ 부진(40미만): {poor}개\n\n[yellow]투자주체별 현황[/yellow]\n• 외국인 매수 우세: {foreign_strong}개\n• 기관 매수 우세: {institution_strong}개\n• 스마트머니 집중: {smart_money_count}개\n\n[bold blue]💡 수급 투자 전략[/bold blue]\n1. 스마트머니 우세 + 고점수 종목 최우선\n2. 외국인과 기관이 동시 매수하는 종목 주목\n3. 거래강도 높으면서 수급 우수한 종목 발굴\n4. 개인 매도 우세 + 기관 매수 패턴 관찰"""
        
        console.print(Panel(
            summary_content,
            title="💰 수급 분석 투자 가이드",
            border_style="green",
            width=65
        ))
    
    def display_pattern_analysis_results(self, pattern_results: List[Dict]):
        """차트패턴 분석 결과 표시"""
        if not pattern_results:
            console.print("[yellow]📈 차트패턴 분석 결과가 없습니다.[/yellow]")
            return
        
        # 패턴 점수순 정렬
        pattern_results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        # 패턴 분석 테이블
        table = Table(title="📈 차트패턴 분석 결과", show_header=True, header_style="bold magenta")
        table.add_column("순위", style="cyan", width=4, justify="center")
        table.add_column("종목", style="bold white", width=12)
        table.add_column("패턴점수", style="bold green", width=8, justify="center")
        table.add_column("캔들", style="blue", width=6, justify="center")
        table.add_column("기술적", style="cyan", width=6, justify="center")
        table.add_column("추세선", style="yellow", width=6, justify="center")
        table.add_column("지지저항", style="magenta", width=8, justify="center")
        table.add_column("신뢰도", style="red", width=6, justify="center")
        table.add_column("추천", style="bold", width=8, justify="center")
        
        for i, result in enumerate(pattern_results[:20], 1):
            symbol = result.get('symbol', '')
            name = result.get('name', '')
            overall_score = result.get('overall_score', 0)
            candle_score = result.get('candle_pattern_score', 0)
            technical_score = result.get('technical_pattern_score', 0)
            trendline_score = result.get('trendline_score', 0)
            sr_score = result.get('support_resistance_score', 0)
            confidence = result.get('confidence', 0)
            recommendation = result.get('recommendation', 'HOLD')
            
            # 포맷팅
            display_name = f"{symbol}\n{name[:6]}" if len(name) > 6 else f"{symbol}\n{name}"
            confidence_display = self._format_confidence(confidence)
            rec_display = self._format_recommendation_short(recommendation)
            
            table.add_row(
                str(i),
                display_name,
                self._score_with_color(overall_score),
                self._score_with_color(candle_score),
                self._score_with_color(technical_score),
                self._score_with_color(trendline_score),
                self._score_with_color(sr_score),
                confidence_display,
                rec_display
            )
        
        console.print(table)
        
        # 패턴 분석 요약
        self._display_pattern_summary(pattern_results)
    
    def _display_pattern_summary(self, pattern_results: List[Dict]):
        """패턴 분석 요약"""
        total = len(pattern_results)
        avg_score = sum(r.get('overall_score', 0) for r in pattern_results) / total if total > 0 else 0
        avg_confidence = sum(r.get('confidence', 0) for r in pattern_results) / total if total > 0 else 0
        
        # 신뢰도별 분포
        high_confidence = len([r for r in pattern_results if r.get('confidence', 0) > 0.8])
        medium_confidence = len([r for r in pattern_results if 0.6 <= r.get('confidence', 0) <= 0.8])
        low_confidence = len([r for r in pattern_results if r.get('confidence', 0) < 0.6])
        
        # 추천별 분포
        strong_buy_patterns = len([r for r in pattern_results if r.get('recommendation') == 'STRONG_BUY'])
        buy_patterns = len([r for r in pattern_results if r.get('recommendation') == 'BUY'])
        
        # 패턴 품질 분포
        excellent_patterns = len([r for r in pattern_results if r.get('overall_score', 0) >= 80])
        good_patterns = len([r for r in pattern_results if 60 <= r.get('overall_score', 0) < 80])
        
        summary_content = f"""[bold]📊 차트패턴 분석 요약[/bold]\n\n[cyan]기본 통계[/cyan]\n• 전체 분석: {total}개 종목\n• 평균 패턴 점수: {avg_score:.1f}점\n• 평균 신뢰도: {avg_confidence:.3f}\n\n[green]신뢰도 분포[/green]\n• 🌟 고신뢰도(0.8+): {high_confidence}개 ({high_confidence/total*100:.1f}%)\n• ✅ 중신뢰도(0.6-0.8): {medium_confidence}개 ({medium_confidence/total*100:.1f}%)\n• ⚠️ 저신뢰도(0.6미만): {low_confidence}개 ({low_confidence/total*100:.1f}%)\n\n[yellow]패턴 추천 분포[/yellow]\n• 🚀 강력매수 패턴: {strong_buy_patterns}개\n• 📈 매수 패턴: {buy_patterns}개\n• 우수 패턴(80+): {excellent_patterns}개\n• 양호 패턴(60-79): {good_patterns}개\n\n[bold blue]💡 패턴 투자 전략[/bold blue]\n1. 신뢰도 0.8 이상 패턴을 최우선 검토\n2. 여러 패턴이 동시 출현하는 종목 주목\n3. 강력매수 패턴 + 고신뢰도 조합이 최적\n4. 지지저항선 돌파 확인 후 진입"""
        
        console.print(Panel(
            summary_content,
            title="📈 차트패턴 투자 가이드",
            border_style="magenta",
            width=65
        ))
    
    # === 유틸리티 메서드들 ===
    
    def _safe_get_score(self, result: Dict, analysis_type: str) -> float:
        """안전하게 분석 점수 추출"""
        try:
            analysis_data = result.get(analysis_type, {})
            if isinstance(analysis_data, dict):
                return analysis_data.get('overall_score', 0)
            return 0
        except:
            return 0
    
    def _safe_get_news_material(self, stock: Dict) -> bool:
        """안전하게 뉴스 재료 정보 추출"""
        try:
            sentiment_data = stock.get('sentiment_analysis', {})
            if isinstance(sentiment_data, dict):
                return sentiment_data.get('has_material', False)
            return False
        except:
            return False
    
    def _score_with_color(self, score: float) -> str:
        """점수에 따른 색상 적용"""
        if score >= 85:
            return f"[bold green]{score:.1f}[/bold green]"
        elif score >= 70:
            return f"[green]{score:.1f}[/green]"
        elif score >= 55:
            return f"[yellow]{score:.1f}[/yellow]"
        elif score >= 40:
            return f"[orange3]{score:.1f}[/orange3]"
        else:
            return f"[red]{score:.1f}[/red]"
    
    def _format_recommendation_text(self, recommendation: str) -> str:
        """추천 등급 텍스트 포맷팅"""
        if recommendation in ['ULTRA_STRONG_BUY']:
            return f"[bold green]{recommendation}[/bold green]"
        elif recommendation in ['STRONG_BUY']:
            return f"[bold green]{recommendation}[/bold green]"
        elif recommendation == 'BUY':
            return f"[green]{recommendation}[/green]"
        elif recommendation == 'WEAK_BUY':
            return f"[yellow]{recommendation}[/yellow]"
        elif recommendation == 'HOLD':
            return f"[white]{recommendation}[/white]"
        elif recommendation == 'WEAK_SELL':
            return f"[orange3]{recommendation}[/orange3]"
        elif recommendation in ['SELL', 'STRONG_SELL']:
            return f"[red]{recommendation}[/red]"
        else:
            return f"[dim]{recommendation}[/dim]"
    
    def _format_recommendation_short(self, recommendation: str) -> str:
        """추천 등급 단축 표시"""
        short_map = {
            'ULTRA_STRONG_BUY': '초강매',
            'STRONG_BUY': '강매',
            'BUY': '매수',
            'WEAK_BUY': '약매',
            'HOLD': '보유',
            'WEAK_SELL': '약매도',
            'SELL': '매도',
            'STRONG_SELL': '강매도'
        }
        short_text = short_map.get(recommendation, recommendation)
        return self._format_recommendation_text(short_text)
    
    def _format_material_type(self, material_type: str) -> str:
        """재료 타입 포맷팅"""
        if material_type == '장기재료':
            return f"[bold blue]{material_type}[/bold blue]"
        elif material_type == '중기재료':
            return f"[bold yellow]{material_type}[/bold yellow]"
        elif material_type == '단기재료':
            return f"[bold red]{material_type}[/bold red]"
        else:
            return f"[dim]{material_type}[/dim]"
    
    def _format_sentiment(self, sentiment_score: float) -> str:
        """감정 점수 포맷팅"""
        if sentiment_score > 1:
            return f"[bold green]{sentiment_score:+.1f}[/bold green]"
        elif sentiment_score > 0:
            return f"[green]{sentiment_score:+.1f}[/green]"
        elif sentiment_score == 0:
            return f"[white]{sentiment_score:.1f}[/white]"
        elif sentiment_score > -1:
            return f"[orange3]{sentiment_score:+.1f}[/orange3]"
        else:
            return f"[red]{sentiment_score:+.1f}[/red]"
    
    def _format_trading_intensity(self, intensity: str) -> str:
        """거래강도 포맷팅"""
        intensity_map = {
            'very_high': ('[bold red]매우높음[/bold red]', '🔥🔥🔥'),
            'high': ('[red]높음[/red]', '🔥🔥'),
            'above_average': ('[yellow]평균이상[/yellow]', '🔥'),
            'normal': ('[green]보통[/green]', '📊'),
            'below_average': ('[dim]평균이하[/dim]', '📉'),
            'low': ('[dim]낮음[/dim]', '💤')
        }
        
        if intensity in intensity_map:
            text, icon = intensity_map[intensity]
            return f"{text}\n{icon}"
        else:
            return f"[dim]{intensity}[/dim]"
    
    def _format_confidence(self, confidence: float) -> str:
        """신뢰도 포맷팅"""
        if confidence > 0.85:
            return f"[bold green]{confidence:.3f}[/bold green]"
        elif confidence > 0.7:
            return f"[green]{confidence:.3f}[/green]"
        elif confidence > 0.55:
            return f"[yellow]{confidence:.3f}[/yellow]"
        elif confidence > 0.4:
            return f"[orange3]{confidence:.3f}[/orange3]"
        else:
            return f"[red]{confidence:.3f}[/red]"
    
    # === 추가 표시 메서드들 ===
    
    def display_top_picks(self, results: List[Dict], count: int = 3):
        """최고 추천 종목 하이라이트 표시"""
        if not results:
            return
        
        # 최고 점수 종목들
        top_results = sorted(results, key=lambda x: x.get('comprehensive_score', 0), reverse=True)[:count]
        
        console.print("\n")
        console.print(Panel.fit(
            "[bold gold1]🏆 오늘의 TOP 추천 종목[/bold gold1]",
            border_style="gold1"
        ))
        
        for i, stock in enumerate(top_results, 1):
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')
            score = stock.get('comprehensive_score', 0)
            recommendation = stock.get('recommendation', '')
            
            # 특별한 스타일링
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            
            pick_content = f"""{medal} [bold]{symbol} {name}[/bold]\n\n[bold gold1]종합점수: {score:.1f}점[/bold gold1]\n[bold green]추천등급: {recommendation}[/bold green]\n\n🎯 [yellow]투자 포인트[/yellow]\n• 5개 영역 모든 지표 우수\n• AI 신뢰도 최고 수준\n• 즉시 투자 검토 권장"""
            
            console.print(Panel(
                pick_content,
                title=f"TOP {i}",
                border_style="gold1",
                width=50
            ))
    
    def display_market_overview(self, results: List[Dict]):
        """시장 전체 개요 표시"""
        if not results:
            return
        
        total = len(results)
        avg_score = sum(r.get('comprehensive_score', 0) for r in results) / total
        
        # 시장 상태 판단
        if avg_score >= 70:
            market_status = "🟢 매우 긍정적"
            market_color = "green"
        elif avg_score >= 60:
            market_status = "🟡 긍정적"
            market_color = "yellow"
        elif avg_score >= 50:
            market_status = "🟠 중립적"
            market_color = "orange3"
        else:
            market_status = "🔴 부정적"
            market_color = "red"
        
        # 추천 종목 통계
        total_buy = len([r for r in results if r.get('recommendation') in ['BUY', 'STRONG_BUY', 'ULTRA_STRONG_BUY']])
        buy_ratio = total_buy / total * 100 if total > 0 else 0
        
        overview_content = f"""[bold]📊 오늘의 시장 분석 개요[/bold]\n\n[{market_color}]시장 상태: {market_status}[/{market_color}]\n전체 분석 종목: {total}개\n평균 종합 점수: {avg_score:.1f}점\n\n📈 투자 기회\n• 매수 추천 종목: {total_buy}개 ({buy_ratio:.1f}%)\n• 고득점(80+) 종목: {len([r for r in results if r.get('comprehensive_score', 0) >= 80])}개\n• 뉴스 재료 보유: {len([r for r in results if self._safe_get_news_material(r)])}개\n\n💡 [yellow]오늘의 투자 전략[/yellow]\n{"• 적극적 매수 진입 타이밍" if avg_score >= 65 else "• 신중한 종목 선별 필요" if avg_score >= 55 else "• 관망 및 리스크 관리 우선"}"""
        
        console.print(Panel(
            overview_content,
            title="🌟 시장 분석 개요",
            border_style=market_color,
            width=60
        ))
    
    def display_risk_warning(self, high_risk_count: int, total_count: int):
        """리스크 경고 표시"""
        if high_risk_count == 0:
            return
        
        risk_ratio = high_risk_count / total_count * 100
        
        if risk_ratio > 30:  # 30% 이상이 고위험
            warning_content = f"""[bold red]⚠️ 높은 리스크 경고![/bold red]\n\n분석 종목 중 {high_risk_count}개({risk_ratio:.1f}%)가 고위험으로 분류되었습니다.\n\n🚨 [yellow]주의사항[/yellow]\n• 고위험 종목 투자 시 신중한 검토 필요\n• 포지션 크기를 평소의 50% 이하로 제한\n• 손절매 기준을 더욱 엄격하게 설정\n• 분산투자를 통한 리스크 관리 필수\n\n💡 안전한 투자를 위해 리스크 관리를 우선하세요."""
            
            console.print(Panel(
                warning_content,
                title="🚨 리스크 경고",
                border_style="red",
                width=65
            ))
    
    def display_analysis_footer(self):
        """분석 결과 하단 정보"""
        from datetime import datetime
        
        footer_content = f"""[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]\n\n[bold cyan]🤖 AI Trading System v3.0[/bold cyan] | 분석 완료: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n[yellow]⚡ 5개 영역 통합 분석[/yellow]\n• 기술적 분석 (30%) • 펀더멘털 분석 (25%) • 뉴스 감정 분석 (25%) • 수급 정보 (10%) • 차트 패턴 (10%)\n\n[green]💡 투자시 유의사항[/green]\n본 분석은 AI가 제공하는 참고 정보이며, 최종 투자 결정은 본인의 책임입니다.\n시장 상황 변화에 따라 결과가 달라질 수 있으니 실시간 정보를 함께 확인하세요.\n\n[bold blue]📞 Happy Trading! 📊[/bold blue]"""
        
        console.print(footer_content)
