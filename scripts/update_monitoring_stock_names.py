#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitoring_stocks 테이블의 종목명 업데이트 스크립트
=====================================================

monitoring_stocks 테이블의 기존 종목 코드들에 대해 실제 종목명을 조회하여 
name 필드를 업데이트하는 스크립트입니다.

사용법:
    python scripts/update_monitoring_stock_names.py

기능:
- monitoring_stocks 테이블의 모든 레코드를 조회
- 각 종목 코드에 대해 KISCollector를 통해 실제 종목명 조회
- 종목명이 없거나 잘못된 경우 업데이트 실행
- 처리 결과 및 통계 출력

주의사항:
- KIS API 호출 제한을 고려하여 적절한 딜레이 추가
- 실패한 종목들에 대한 로그 기록
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 필요한 모듈들 임포트
from database.database_manager import DatabaseManager
from database.monitoring_models import MonitoringStock
from data_collectors.kis_collector import KISCollector
from config import Config
from sqlalchemy.orm import sessionmaker
from utils.logger import get_logger


class MonitoringStockNameUpdater:
    """monitoring_stocks 테이블의 종목명 업데이트 클래스"""
    
    def __init__(self):
        self.console = Console()
        self.logger = get_logger("StockNameUpdater")
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.kis_collector = KISCollector(self.config, self.db_manager)
        
        # 세션 생성
        Session = sessionmaker(bind=self.db_manager.sync_engine)
        self.session = Session()
        
        # 통계
        self.stats = {
            'total_stocks': 0,
            'updated_stocks': 0,
            'already_correct': 0,
            'failed_updates': 0,
            'errors': []
        }
    
    async def run_update(self) -> None:
        """메인 업데이트 실행"""
        try:
            # 헤더 출력
            self._print_header()
            
            # KISCollector 초기화
            await self.kis_collector.initialize()
            
            # 모니터링 종목들 조회
            stocks = await self._get_monitoring_stocks()
            if not stocks:
                self.console.print("[yellow]⚠️ 업데이트할 모니터링 종목이 없습니다.[/yellow]")
                return
            
            self.stats['total_stocks'] = len(stocks)
            self.console.print(f"📊 총 {len(stocks)}개 종목을 처리합니다.\n")
            
            # 프로그레스 바와 함께 업데이트 실행
            await self._update_stock_names_with_progress(stocks)
            
            # 결과 출력
            self._print_results()
            
        except Exception as e:
            self.logger.error(f"업데이트 실행 중 오류 발생: {e}")
            self.console.print(f"[red]❌ 업데이트 실행 중 오류 발생: {e}[/red]")
        finally:
            # 세션 정리
            self.session.close()
            await self.kis_collector.close()
    
    def _print_header(self) -> None:
        """헤더 출력"""
        title_text = "📈 monitoring_stocks 테이블 종목명 업데이트"
        header_panel = Panel(title_text, style="bold blue", border_style="blue")
        self.console.print(header_panel)
        
        self.console.print("🔍 [bold]작업 내용:[/bold]")
        self.console.print("   • monitoring_stocks 테이블의 모든 종목 조회")
        self.console.print("   • KIS API를 통한 실제 종목명 조회")
        self.console.print("   • 종목명이 없거나 잘못된 경우 업데이트")
        self.console.print("   • 처리 결과 및 통계 출력\n")
    
    async def _get_monitoring_stocks(self) -> List[MonitoringStock]:
        """모니터링 종목들 조회"""
        try:
            # 모든 monitoring_stocks 조회 (status와 상관없이)
            stocks = self.session.query(MonitoringStock).all()
            
            self.logger.info(f"모니터링 테이블에서 {len(stocks)}개 종목 조회")
            return stocks
            
        except Exception as e:
            self.logger.error(f"모니터링 종목 조회 실패: {e}")
            raise
    
    async def _update_stock_names_with_progress(self, stocks: List[MonitoringStock]) -> None:
        """프로그레스 바와 함께 종목명 업데이트"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            
            update_task = progress.add_task("종목명 업데이트 중...", total=len(stocks))
            
            for i, stock in enumerate(stocks):
                try:
                    # 현재 처리 중인 종목 표시
                    progress.update(update_task, description=f"[bold blue]처리중: {stock.symbol}[/bold blue]")
                    
                    # 종목명 업데이트 시도
                    await self._update_single_stock_name(stock)
                    
                    # 프로그레스 업데이트
                    progress.advance(update_task)
                    
                    # API 호출 제한 고려 (100ms 딜레이)
                    if i < len(stocks) - 1:  # 마지막 종목이 아닌 경우
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    self.logger.error(f"종목 {stock.symbol} 처리 중 오류: {e}")
                    self.stats['failed_updates'] += 1
                    self.stats['errors'].append(f"{stock.symbol}: {str(e)}")
                    progress.advance(update_task)
    
    async def _update_single_stock_name(self, stock: MonitoringStock) -> None:
        """단일 종목의 이름 업데이트"""
        
        try:
            # 현재 종목명 확인
            current_name = stock.name
            symbol = stock.symbol
            
            # KIS API를 통해 실제 종목 정보 조회
            stock_info = await self.kis_collector.get_stock_info(symbol)
            
            if not stock_info:
                self.logger.warning(f"종목 {symbol} 정보를 조회할 수 없습니다")
                self.stats['failed_updates'] += 1
                self.stats['errors'].append(f"{symbol}: 종목 정보 조회 불가")
                return
            
            # 실제 종목명
            actual_name = stock_info.name
            
            # 종목명 비교 및 업데이트 필요성 판단
            if self._needs_update(current_name, actual_name):
                # 종목명 업데이트
                stock.name = actual_name
                self.session.commit()
                
                self.logger.info(f"종목 {symbol} 이름 업데이트: '{current_name}' → '{actual_name}'")
                self.stats['updated_stocks'] += 1
                
            else:
                # 이미 올바른 종목명
                self.stats['already_correct'] += 1
                self.logger.debug(f"종목 {symbol}({current_name}): 이미 올바른 종목명")
                
        except Exception as e:
            self.logger.error(f"종목 {stock.symbol} 업데이트 실패: {e}")
            self.session.rollback()
            raise
    
    def _needs_update(self, current_name: Optional[str], actual_name: str) -> bool:
        """업데이트가 필요한지 판단"""
        
        # 현재 이름이 없는 경우
        if not current_name:
            return True
        
        # 현재 이름이 종목 코드인 경우 (6자리 숫자)
        if current_name.isdigit() and len(current_name) == 6:
            return True
        
        # 현재 이름과 실제 이름이 다른 경우
        if current_name.strip() != actual_name.strip():
            return True
        
        return False
    
    def _print_results(self) -> None:
        """결과 출력"""
        
        # 결과 통계 테이블
        results_table = Table(title="📊 처리 결과", show_header=True, header_style="bold magenta")
        results_table.add_column("항목", style="cyan", min_width=15)
        results_table.add_column("수량", justify="right", style="yellow", min_width=8)
        results_table.add_column("비율", justify="right", style="green", min_width=10)
        
        total = self.stats['total_stocks']
        
        results_table.add_row("전체 종목", str(total), "100.0%")
        results_table.add_row("업데이트됨", str(self.stats['updated_stocks']), 
                            f"{(self.stats['updated_stocks']/total*100):.1f}%" if total > 0 else "0.0%")
        results_table.add_row("이미 정확함", str(self.stats['already_correct']), 
                            f"{(self.stats['already_correct']/total*100):.1f}%" if total > 0 else "0.0%")
        results_table.add_row("실패", str(self.stats['failed_updates']), 
                            f"{(self.stats['failed_updates']/total*100):.1f}%" if total > 0 else "0.0%")
        
        # 결과 패널로 감싸기
        results_panel = Panel(results_table, border_style="green", expand=True)
        self.console.print(results_panel)
        
        # 성공 메시지
        if self.stats['failed_updates'] == 0:
            success_text = f"✅ 모든 종목 처리 완료! ({self.stats['updated_stocks']}개 업데이트됨)"
            success_panel = Panel(success_text, style="bold green", border_style="green")
            self.console.print(success_panel)
        else:
            # 실패한 종목들 출력
            warning_text = f"⚠️ {self.stats['failed_updates']}개 종목 처리 실패\n"
            if self.stats['errors']:
                warning_text += "\n실패 목록:\n"
                for error in self.stats['errors'][:5]:  # 최대 5개만 표시
                    warning_text += f"  • {error}\n"
                if len(self.stats['errors']) > 5:
                    warning_text += f"  ... 및 {len(self.stats['errors']) - 5}개 더"
            
            warning_panel = Panel(warning_text, style="bold yellow", border_style="yellow")
            self.console.print(warning_panel)
        
        # 로그 파일 안내
        self.console.print(f"\n💡 자세한 로그는 logs/ 디렉토리에서 확인하실 수 있습니다.")


async def main():
    """메인 실행 함수"""
    updater = MonitoringStockNameUpdater()
    await updater.run_update()


if __name__ == "__main__":
    import sys
    import io
    
    # 윈도우 콘솔 인코딩 문제 해결
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    console = Console()
    console.print("[bold blue]🚀 monitoring_stocks 테이블 종목명 업데이트 스크립트 시작...[/bold blue]")
    console.print("=" * 80)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[bold red]🛑 사용자에 의해 중단되었습니다.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]❌ 스크립트 실행 중 오류 발생: {e}[/bold red]")
        import traceback
        traceback.print_exc()
    
    console.print("\n" + "=" * 80)
    console.print("[bold green]📝 스크립트 실행 완료[/bold green]")