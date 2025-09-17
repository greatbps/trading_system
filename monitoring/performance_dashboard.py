#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/monitoring/performance_dashboard.py

실시간 성능 대시보드 - Phase 7 System Optimization
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from utils.logger import get_logger
from monitoring.performance_monitor import PerformanceMonitor


class PerformanceDashboard:
    """실시간 성능 대시보드"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
        self.console = Console()
        self.logger = get_logger("PerformanceDashboard")
        self.is_running = False
        
    async def start_dashboard(self, refresh_interval: float = 2.0):
        """대시보드 시작"""
        self.is_running = True
        self.logger.info("🖥️ 성능 대시보드 시작")
        
        try:
            with Live(self._create_layout(), refresh_per_second=1/refresh_interval, screen=True) as live:
                while self.is_running:
                    live.update(self._create_layout())
                    await asyncio.sleep(refresh_interval)
        except KeyboardInterrupt:
            self.is_running = False
            self.logger.info("⏹️ 대시보드 중지 (Ctrl+C)")
    
    def stop_dashboard(self):
        """대시보드 중지"""
        self.is_running = False
    
    def _create_layout(self) -> Layout:
        """대시보드 레이아웃 생성"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        layout["left"].split_column(
            Layout(name="system", ratio=1),
            Layout(name="alerts", ratio=1)
        )
        
        layout["right"].split_column(
            Layout(name="components", ratio=1),
            Layout(name="history", ratio=1)
        )
        
        # 각 섹션 업데이트
        layout["header"].update(self._create_header())
        layout["system"].update(self._create_system_metrics())
        layout["components"].update(self._create_component_table())
        layout["alerts"].update(self._create_alerts_panel())
        layout["history"].update(self._create_history_chart())
        layout["footer"].update(self._create_footer())
        
        return layout
    
    def _create_header(self) -> Panel:
        """헤더 생성"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"🚀 AI Trading System - Performance Dashboard | {current_time}"
        
        return Panel(
            Text(title, style="bold cyan", justify="center"),
            style="blue"
        )
    
    def _create_system_metrics(self) -> Panel:
        """시스템 메트릭 패널"""
        current_metrics = self.monitor.get_current_metrics()
        
        if not current_metrics:
            return Panel("📊 메트릭 수집 중...", title="System Metrics")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Status", style="white")
        
        # CPU
        cpu_color = self._get_status_color(current_metrics.cpu_percent, [70, 85, 95])
        table.add_row("🖥️  CPU Usage", f"{current_metrics.cpu_percent:.1f}%", 
                     f"[{cpu_color}]●[/]")
        
        # Memory
        mem_color = self._get_status_color(current_metrics.memory_percent, [75, 90, 95])
        table.add_row("💾 Memory Usage", f"{current_metrics.memory_percent:.1f}%",
                     f"[{mem_color}]●[/]")
        
        # Response Time
        resp_color = self._get_status_color(current_metrics.response_time_ms, [1000, 3000, 5000])
        table.add_row("⚡ Avg Response", f"{current_metrics.response_time_ms:.1f}ms",
                     f"[{resp_color}]●[/]")
        
        # Throughput
        table.add_row("📈 Throughput", f"{current_metrics.throughput_ops_per_sec:.1f} ops/s", 
                     "[green]●[/]")
        
        # Error Rate
        error_color = self._get_status_color(current_metrics.error_rate_percent, [1, 5, 10])
        table.add_row("❌ Error Rate", f"{current_metrics.error_rate_percent:.2f}%",
                     f"[{error_color}]●[/]")
        
        # Threads
        table.add_row("🧵 Active Threads", str(current_metrics.active_threads), "[blue]●[/]")
        
        return Panel(table, title="📊 System Metrics", border_style="green")
    
    def _create_component_table(self) -> Panel:
        """컴포넌트 성능 테이블"""
        component_metrics = self.monitor.get_component_performance()
        
        if not component_metrics:
            return Panel("📈 컴포넌트 분석 중...", title="Component Performance")
        
        table = Table(show_header=True, box=None)
        table.add_column("Component", style="cyan")
        table.add_column("Avg Time", style="white")
        table.add_column("Calls", style="green")
        table.add_column("Errors", style="red")
        table.add_column("Memory", style="yellow")
        
        # 평균 실행 시간 순으로 정렬
        sorted_components = sorted(
            component_metrics.values(),
            key=lambda x: x.avg_execution_time_ms,
            reverse=True
        )
        
        for comp in sorted_components[:8]:  # 상위 8개만 표시
            table.add_row(
                comp.component_name[:15],  # 이름 길이 제한
                f"{comp.avg_execution_time_ms:.1f}ms",
                str(comp.total_calls),
                str(comp.error_count) if comp.error_count > 0 else "-",
                f"{comp.memory_usage_mb:.1f}MB" if comp.memory_usage_mb > 0 else "-"
            )
        
        return Panel(table, title="🧩 Component Performance", border_style="blue")
    
    def _create_alerts_panel(self) -> Panel:
        """알림 패널"""
        active_alerts = self.monitor.get_active_alerts()
        
        if not active_alerts:
            return Panel("✅ No Active Alerts", title="🚨 Alerts", border_style="green")
        
        alert_text = ""
        for alert in active_alerts:
            severity_emoji = {
                'MEDIUM': '⚠️ ',
                'HIGH': '🚨',
                'CRITICAL': '🔥'
            }
            
            emoji = severity_emoji.get(alert.severity, '⚠️')
            alert_text += f"{emoji} {alert.alert_type}: {alert.current_value:.1f}\n"
            alert_text += f"   Threshold: {alert.threshold_value:.1f}\n"
            alert_text += f"   Action: {alert.recommended_action}\n\n"
        
        return Panel(alert_text.strip(), title="🚨 Active Alerts", border_style="red")
    
    def _create_history_chart(self) -> Panel:
        """간단한 이력 차트"""
        metrics_history = self.monitor.get_metrics_history(minutes=10)  # 최근 10분
        
        if len(metrics_history) < 5:
            return Panel("📈 데이터 수집 중...", title="Performance History")
        
        # 간단한 ASCII 차트
        chart_text = "CPU & Memory Trends (Last 10min)\n\n"
        
        # 최근 20개 데이터포인트로 차트 생성
        recent_data = metrics_history[-20:]
        
        cpu_values = [m.cpu_percent for m in recent_data]
        mem_values = [m.memory_percent for m in recent_data]
        
        # 스케일링
        max_val = max(max(cpu_values), max(mem_values))
        scale = 30 / max_val if max_val > 0 else 1  # 30자로 스케일링
        
        chart_text += "CPU:  "
        for cpu in cpu_values[-15:]:  # 최근 15개
            bar_len = int(cpu * scale)
            chart_text += "█" * max(1, bar_len // 2)
        chart_text += f" ({cpu_values[-1]:.1f}%)\n\n"
        
        chart_text += "MEM:  "
        for mem in mem_values[-15:]:  # 최근 15개
            bar_len = int(mem * scale)
            chart_text += "█" * max(1, bar_len // 2)
        chart_text += f" ({mem_values[-1]:.1f}%)\n"
        
        return Panel(chart_text, title="📈 Performance History", border_style="yellow")
    
    def _create_footer(self) -> Panel:
        """푸터 생성"""
        summary = self.monitor.get_performance_summary()
        
        footer_text = f"Monitoring: {summary.get('monitoring_duration_minutes', 0):.1f}min | "
        footer_text += f"Total Ops: {summary.get('total_operations', 0)} | "
        footer_text += f"Alerts: {summary.get('active_alerts_count', 0)} | "
        footer_text += "Press Ctrl+C to exit"
        
        return Panel(
            Text(footer_text, justify="center"),
            style="dim"
        )
    
    def _get_status_color(self, value: float, thresholds: List[float]) -> str:
        """상태 색상 반환"""
        if value >= thresholds[2]:  # Critical
            return "red"
        elif value >= thresholds[1]:  # High
            return "yellow"
        elif value >= thresholds[0]:  # Medium
            return "orange"
        else:
            return "green"
    
    def show_performance_summary(self):
        """성능 요약 표시"""
        summary = self.monitor.get_performance_summary()
        
        self.console.print("\n" + "="*60)
        self.console.print("📊 PERFORMANCE SUMMARY", style="bold cyan")
        self.console.print("="*60)
        
        if not summary:
            self.console.print("❌ 성능 데이터 없음")
            return
        
        # 시스템 정보
        sys_info = summary.get('system_info', {})
        self.console.print(f"\n🖥️  System Info:")
        self.console.print(f"   CPU: {sys_info.get('cpu_count', 'N/A')} cores @ {sys_info.get('cpu_freq_mhz', 'N/A')} MHz")
        self.console.print(f"   Memory: {sys_info.get('total_memory_gb', 'N/A'):.1f} GB")
        self.console.print(f"   Python: {sys_info.get('python_version', 'N/A')}")
        
        # 현재 메트릭
        current = summary.get('current_metrics')
        if current:
            self.console.print(f"\n📊 Current Metrics:")
            self.console.print(f"   CPU Usage: [cyan]{current['cpu_percent']:.1f}%[/]")
            self.console.print(f"   Memory Usage: [cyan]{current['memory_percent']:.1f}%[/]")
            self.console.print(f"   Response Time: [cyan]{current['response_time_ms']:.1f}ms[/]")
            self.console.print(f"   Throughput: [cyan]{current['throughput_ops_per_sec']:.1f} ops/sec[/]")
        
        # 평균값
        self.console.print(f"\n📈 Averages (Recent):")
        self.console.print(f"   Avg CPU: [green]{summary.get('avg_cpu_percent', 0):.1f}%[/]")
        self.console.print(f"   Avg Memory: [green]{summary.get('avg_memory_percent', 0):.1f}%[/]")
        self.console.print(f"   Avg Response: [green]{summary.get('avg_response_time_ms', 0):.1f}ms[/]")
        
        # 느린 컴포넌트
        slow_components = summary.get('top_slow_components', [])
        if slow_components:
            self.console.print(f"\n🐌 Slowest Components:")
            for comp in slow_components:
                self.console.print(f"   {comp['name']}: [red]{comp['avg_time_ms']:.1f}ms[/] "
                                f"({comp['total_calls']} calls, {comp['error_count']} errors)")
        
        # 통계
        self.console.print(f"\n📊 Statistics:")
        self.console.print(f"   Total Operations: [cyan]{summary.get('total_operations', 0)}[/]")
        self.console.print(f"   Active Alerts: [red]{summary.get('active_alerts_count', 0)}[/]")
        self.console.print(f"   Monitoring Duration: [green]{summary.get('monitoring_duration_minutes', 0):.1f} minutes[/]")
        
        self.console.print("\n" + "="*60)
    
    def show_component_details(self):
        """컴포넌트 상세 정보 표시"""
        component_metrics = self.monitor.get_component_performance()
        
        if not component_metrics:
            self.console.print("❌ 컴포넌트 데이터 없음")
            return
        
        table = Table(title="🧩 Component Performance Details")
        table.add_column("Component", style="cyan")
        table.add_column("Avg Time (ms)", style="white")
        table.add_column("Max Time (ms)", style="yellow") 
        table.add_column("Min Time (ms)", style="green")
        table.add_column("Total Calls", style="blue")
        table.add_column("Error Count", style="red")
        table.add_column("Error Rate", style="red")
        table.add_column("Memory (MB)", style="magenta")
        
        # 평균 시간순 정렬
        sorted_components = sorted(
            component_metrics.values(),
            key=lambda x: x.avg_execution_time_ms,
            reverse=True
        )
        
        for comp in sorted_components:
            error_rate = (comp.error_count / comp.total_calls * 100) if comp.total_calls > 0 else 0
            
            table.add_row(
                comp.component_name,
                f"{comp.avg_execution_time_ms:.2f}",
                f"{comp.max_execution_time_ms:.2f}",
                f"{comp.min_execution_time_ms:.2f}",
                str(comp.total_calls),
                str(comp.error_count),
                f"{error_rate:.1f}%",
                f"{comp.memory_usage_mb:.1f}" if comp.memory_usage_mb > 0 else "-"
            )
        
        self.console.print(table)
    
    def show_alerts_history(self):
        """알림 이력 표시"""
        alert_history = list(self.monitor.alert_history)
        
        if not alert_history:
            self.console.print("✅ 알림 이력 없음")
            return
        
        table = Table(title="🚨 Alert History")
        table.add_column("Time", style="white")
        table.add_column("Type", style="cyan")
        table.add_column("Severity", style="white")
        table.add_column("Value", style="yellow")
        table.add_column("Threshold", style="red")
        table.add_column("Action", style="green")
        
        # 최근 순서로 정렬
        sorted_alerts = sorted(alert_history, key=lambda x: x.timestamp, reverse=True)
        
        for alert in sorted_alerts[:20]:  # 최근 20개만
            severity_color = {
                'MEDIUM': 'yellow',
                'HIGH': 'red',
                'CRITICAL': 'bright_red'
            }.get(alert.severity, 'white')
            
            table.add_row(
                alert.timestamp.strftime("%H:%M:%S"),
                alert.alert_type,
                f"[{severity_color}]{alert.severity}[/]",
                f"{alert.current_value:.1f}",
                f"{alert.threshold_value:.1f}",
                alert.recommended_action[:30] + "..." if len(alert.recommended_action) > 30 else alert.recommended_action
            )
        
        self.console.print(table)


async def run_performance_dashboard(performance_monitor: PerformanceMonitor):
    """성능 대시보드 실행"""
    dashboard = PerformanceDashboard(performance_monitor)
    await dashboard.start_dashboard()


def show_performance_menu(performance_monitor: PerformanceMonitor):
    """성능 모니터링 메뉴"""
    console = Console()
    dashboard = PerformanceDashboard(performance_monitor)
    
    while True:
        console.clear()
        console.print("\n" + "="*50)
        console.print("📊 PERFORMANCE MONITORING", style="bold cyan")
        console.print("="*50)
        
        console.print("\n1. 📈 실시간 대시보드")
        console.print("2. 📊 성능 요약")
        console.print("3. 🧩 컴포넌트 상세")
        console.print("4. 🚨 알림 이력")
        console.print("5. 🧹 가비지 컬렉션 강제 실행")
        console.print("6. 🔄 메트릭 초기화")
        console.print("0. 🔙 메인 메뉴로")
        
        try:
            choice = console.input("\n선택하세요: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                console.print("\n🖥️  실시간 대시보드 시작 (Ctrl+C로 종료)")
                console.input("Press Enter to continue...")
                asyncio.run(dashboard.start_dashboard())
            elif choice == "2":
                dashboard.show_performance_summary()
                console.input("\nPress Enter to continue...")
            elif choice == "3":
                dashboard.show_component_details()
                console.input("\nPress Enter to continue...")
            elif choice == "4":
                dashboard.show_alerts_history()
                console.input("\nPress Enter to continue...")
            elif choice == "5":
                collected = performance_monitor.force_garbage_collection()
                console.print(f"🧹 가비지 컬렉션 완료: {collected}개 객체 정리")
                console.input("\nPress Enter to continue...")
            elif choice == "6":
                performance_monitor.reset_metrics()
                console.print("🔄 메트릭 초기화 완료")
                console.input("\nPress Enter to continue...")
            else:
                console.print("❌ 잘못된 선택입니다")
                console.input("Press Enter to continue...")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"❌ 오류: {e}")
            console.input("Press Enter to continue...")