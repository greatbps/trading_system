#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitoring_stocks 테이블 enum 값 불일치 수정
"""

import sys
import io
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from database.database_manager import DatabaseManager
from config import Config
from rich.console import Console
from rich.panel import Panel
from sqlalchemy import text

def fix_enum_values():
    """enum 값 불일치 수정"""
    console = Console()
    
    try:
        # 설정 및 DB 매니저 초기화
        config = Config()
        db_manager = DatabaseManager(config)
        
        console.print(Panel("[bold blue]🔧 monitoring_stocks enum 값 불일치 수정[/bold blue]", border_style="blue"))
        
        with db_manager.get_session() as session:
            # 1. 먼저 실제 DB 데이터 확인
            console.print("\n[yellow]1. 현재 DB 상태 확인[/yellow]")
            
            # Raw SQL로 데이터 확인
            result = session.execute(text("SELECT status, monitoring_type, COUNT(*) as count FROM monitoring_stocks GROUP BY status, monitoring_type"))
            rows = result.fetchall()
            
            if not rows:
                console.print("[red]❌ monitoring_stocks 테이블에 데이터가 없습니다.[/red]")
                return
            
            console.print("현재 DB의 enum 값 분포:")
            for row in rows:
                console.print(f"  Status: {row[0]}, Type: {row[1]}, Count: {row[2]}")
            
            # 2. 잘못된 enum 값들 수정
            console.print("\n[yellow]2. enum 값 수정 시작[/yellow]")
            
            # status 값 수정 (소문자 -> 대문자)
            status_updates = [
                ("active", "ACTIVE"),
                ("inactive", "INACTIVE"), 
                ("paused", "PAUSED"),
                ("completed", "COMPLETED"),
                ("removed", "REMOVED")
            ]
            
            status_update_count = 0
            for old_val, new_val in status_updates:
                result = session.execute(
                    text("UPDATE monitoring_stocks SET status = :new_val WHERE status = :old_val"),
                    {"old_val": old_val, "new_val": new_val}
                )
                if result.rowcount > 0:
                    console.print(f"  ✅ status '{old_val}' -> '{new_val}': {result.rowcount}개 수정")
                    status_update_count += result.rowcount
            
            # monitoring_type 값 수정
            type_updates = [
                ("trading", "TRADING"),
                ("removal_watch", "REMOVAL_WATCH"),
                ("portfolio", "PORTFOLIO")
            ]
            
            type_update_count = 0
            for old_val, new_val in type_updates:
                result = session.execute(
                    text("UPDATE monitoring_stocks SET monitoring_type = :new_val WHERE monitoring_type = :old_val"),
                    {"old_val": old_val, "new_val": new_val}
                )
                if result.rowcount > 0:
                    console.print(f"  ✅ monitoring_type '{old_val}' -> '{new_val}': {result.rowcount}개 수정")
                    type_update_count += result.rowcount
            
            # 3. 변경사항 커밋
            session.commit()
            
            # 4. 수정 후 상태 확인
            console.print("\n[yellow]3. 수정 후 상태 확인[/yellow]")
            result = session.execute(text("SELECT status, monitoring_type, COUNT(*) as count FROM monitoring_stocks GROUP BY status, monitoring_type"))
            rows = result.fetchall()
            
            console.print("수정 후 enum 값 분포:")
            for row in rows:
                console.print(f"  Status: {row[0]}, Type: {row[1]}, Count: {row[2]}")
            
            # 5. 결과 요약
            total_updates = status_update_count + type_update_count
            if total_updates > 0:
                console.print(f"\n[bold green]✅ 수정 완료: 총 {total_updates}개 레코드 수정됨[/bold green]")
                console.print(f"  - status 필드: {status_update_count}개 수정")
                console.print(f"  - monitoring_type 필드: {type_update_count}개 수정")
            else:
                console.print(f"\n[green]ℹ️ 수정이 필요한 enum 값이 없습니다.[/green]")
    
    except Exception as e:
        console.print(f"[red]❌ enum 값 수정 실패: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_enum_values()