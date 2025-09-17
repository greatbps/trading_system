#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
알려진 종목 코드로 종목명 수동 업데이트
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
from sqlalchemy import text

def manual_update_stock_names():
    """알려진 종목 코드로 종목명 수동 업데이트"""
    console = Console()
    
    # 한국 주요 종목 코드 매핑
    stock_mapping = {
        '000660': 'SK하이닉스',
        '010130': '고려아연', 
        '302440': '코리아써키트',
        '073240': '금호타이어',
        '083650': '비에이치아이',
        '010120': 'LS ELECTRIC',
        '028260': '삼성물산',
        '013310': '아진산업',
        '072770': '율호',
        '201490': '미투온',
        '321370': '넷마블랩',
        '363260': '유비쿼스'
    }
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        console.print(Panel("[bold blue]📝 종목명 수동 업데이트[/bold blue]", border_style="blue"))
        
        with db_manager.get_session() as session:
            updated_count = 0
            
            for symbol, name in stock_mapping.items():
                try:
                    # 해당 종목이 모니터링 테이블에 있는지 확인
                    stock = session.query(MonitoringStock).filter(
                        MonitoringStock.symbol == symbol,
                        MonitoringStock.name.like('종목%')
                    ).first()
                    
                    if stock:
                        old_name = stock.name
                        stock.name = name
                        session.commit()
                        console.print(f"  ✅ {symbol}: '{old_name}' → '{name}'")
                        updated_count += 1
                    else:
                        console.print(f"  ⚠️ {symbol}: 대상 종목 없음")
                        
                except Exception as e:
                    console.print(f"  ❌ {symbol}: 업데이트 실패 - {e}")
                    continue
            
            console.print(f"\n[bold green]📊 수동 업데이트 완료: {updated_count}개 종목[/bold green]")
    
    except Exception as e:
        console.print(f"[red]❌ 수동 업데이트 실패: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    manual_update_stock_names()