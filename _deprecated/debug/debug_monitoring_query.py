#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 상태 조회 디버그
"""

import sys
import io
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from database.models import MonitoringStock, MonitoringStatus, MonitoringType
from database.database_manager import DatabaseManager
from config import Config
from rich.console import Console
from rich.panel import Panel

def debug_monitoring_query():
    """모니터링 조회 쿼리 디버그"""
    console = Console()
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        console.print(Panel("[bold blue]🔍 모니터링 조회 쿼리 디버그[/bold blue]", border_style="blue"))
        
        with db_manager.get_session() as session:
            # 1. 전체 모니터링 종목 조회
            all_stocks = session.query(MonitoringStock).all()
            console.print(f"\n[yellow]전체 모니터링 종목 수: {len(all_stocks)}[/yellow]")
            
            # 2. 활성 상태만 조회
            active_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value
            ).all()
            console.print(f"[yellow]활성 상태 종목 수: {len(active_stocks)}[/yellow]")
            
            # 3. 활성 + monitoring_active = True 조회
            active_monitoring = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                MonitoringStock.monitoring_active == True
            ).all()
            console.print(f"[yellow]활성 모니터링 종목 수: {len(active_monitoring)}[/yellow]")
            
            # 4. TRADING 타입만 조회
            trading_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                MonitoringStock.monitoring_active == True,
                MonitoringStock.monitoring_type == MonitoringType.TRADING
            ).all()
            console.print(f"[yellow]매매용 활성 모니터링 종목 수: {len(trading_stocks)}[/yellow]")
            
            # 5. get_active_monitoring() 메서드 테스트
            method_result = MonitoringStock.get_active_monitoring(session, MonitoringType.TRADING)
            console.print(f"[yellow]get_active_monitoring() 결과: {len(method_result)}[/yellow]")
            
            # 6. 각 종목의 상세 정보
            console.print("\n[blue]각 종목 상세 정보:[/blue]")
            for i, stock in enumerate(all_stocks[:5]):  # 처음 5개만 표시
                console.print(f"  {i+1}. {stock.symbol} ({stock.name})")
                console.print(f"     - status: {stock.status}")
                console.print(f"     - monitoring_active: {stock.monitoring_active}")
                console.print(f"     - monitoring_type: {stock.monitoring_type}")
                console.print()
            
            if len(all_stocks) > 5:
                console.print(f"     ... (총 {len(all_stocks) - 5}개 더 있음)")
    
    except Exception as e:
        console.print(f"[red]❌ 디버그 실패: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_monitoring_query()