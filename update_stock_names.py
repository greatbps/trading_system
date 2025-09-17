#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 모니터링 종목들의 종목명 업데이트
"""

import sys
import io
import asyncio
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from database.models import MonitoringStock, MonitoringStatus, MonitoringType
from database.database_manager import DatabaseManager
from data_collectors.kis_collector import KISCollector
from config import Config
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

async def update_stock_names():
    """종목명이 '종목XXXXXX' 형태인 모니터링 종목들의 실제 종목명 업데이트"""
    console = Console()
    
    try:
        # 설정 및 컴포넌트 초기화
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        
        console.print(Panel("[bold blue]📝 모니터링 종목명 업데이트[/bold blue]", border_style="blue"))
        
        with db_manager.get_session() as session:
            # '종목XXXXXX' 형태의 종목들 조회
            stocks_to_update = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE,
                MonitoringStock.name.like('종목%')
            ).all()
            
            if not stocks_to_update:
                console.print("[green]✅ 업데이트가 필요한 종목이 없습니다.[/green]")
                return
            
            console.print(f"\n[yellow]📋 업데이트 대상: {len(stocks_to_update)}개 종목[/yellow]")
            
            updated_count = 0
            failed_count = 0
            
            # 각 종목의 실제 이름 조회 및 업데이트
            for stock in track(stocks_to_update, description="종목명 업데이트 중..."):
                try:
                    # KIS API를 통해 실제 종목명 조회
                    stock_info = await kis_collector.get_stock_info(stock.symbol)
                    
                    if stock_info and hasattr(stock_info, 'name') and stock_info.name:
                        real_name = stock_info.name
                        old_name = stock.name
                        
                        # 종목명 업데이트
                        stock.name = real_name
                        session.commit()
                        
                        console.print(f"  ✅ {stock.symbol}: '{old_name}' → '{real_name}'")
                        updated_count += 1
                        
                        # API 호출 간격 조절 (과도한 호출 방지)
                        await asyncio.sleep(0.1)
                        
                    else:
                        console.print(f"  ⚠️ {stock.symbol}: 종목 정보 조회 실패")
                        failed_count += 1
                        
                except Exception as e:
                    console.print(f"  ❌ {stock.symbol}: 업데이트 실패 - {e}")
                    failed_count += 1
                    continue
            
            # 결과 요약
            console.print(f"\n[bold green]📊 업데이트 완료[/bold green]")
            console.print(f"  ✅ 성공: {updated_count}개")
            console.print(f"  ❌ 실패: {failed_count}개")
            console.print(f"  📋 전체: {len(stocks_to_update)}개")
    
    except Exception as e:
        console.print(f"[red]❌ 종목명 업데이트 실패: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(update_stock_names())