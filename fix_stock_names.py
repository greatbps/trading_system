import asyncio
import json
from datetime import datetime
from pathlib import Path
from config import Config
from database.database_manager import DatabaseManager
from database.models import MonitoringStock
from data_collectors.kis_collector import KISCollector
from sqlalchemy.orm import Session
from sqlalchemy import or_

async def fix_stock_names_in_db():
    """DB의 monitoring_stocks 테이블에 있는 잘못된 종목명을 수정합니다."""
    print("잘못된 종목명 수정을 시작합니다...")
    
    config = Config()
    db_manager = DatabaseManager(config)
    kis_collector = KISCollector(config)
    
    updated_count = 0
    failed_count = 0
    
    with Session(db_manager.engine) as session:
        # '종목'으로 시작하거나 이름이 비어있는 종목 조회
        stocks_to_fix = session.query(MonitoringStock).filter(
            or_(
                MonitoringStock.name.like('종목%'),
                MonitoringStock.name == None,
                MonitoringStock.name == ''
            )
        ).all()
        
        if not stocks_to_fix:
            print("수정할 종목이 없습니다. 모든 종목명이 올바릅니다.")
            return

        print(f"총 {len(stocks_to_fix)}개의 종목을 수정해야 합니다.")
        
        for stock in stocks_to_fix:
            try:
                # KIS API를 통해 실제 종목명 조회
                stock_info = await kis_collector.get_stock_info(stock.symbol)
                
                if stock_info and hasattr(stock_info, 'name') and stock_info.name:
                    correct_name = stock_info.name
                    if stock.name != correct_name:
                        print(f"  - {stock.symbol}: '{stock.name}' -> '{correct_name}' (으)로 수정 중...")
                        stock.name = correct_name
                        updated_count += 1
                    else:
                         # 이름은 같지만 업데이트 대상에 포함된 경우
                        print(f"  - {stock.symbol}: '{stock.name}' (이)는 이미 올바른 이름입니다.")
                else:
                    print(f"  - {stock.symbol}: KIS에서 종목 정보를 찾을 수 없습니다.")
                    failed_count += 1
            except Exception as e:
                print(f"  - {stock.symbol}: 종목명 조회/수정 중 오류 발생: {e}")
                failed_count += 1
        
        if updated_count > 0:
            session.commit()
            print(f"\n총 {updated_count}개 종목의 이름이 성공적으로 수정되었습니다.")
        else:
            print("\n실제로 수정된 종목은 없습니다.")

        if failed_count > 0:
            print(f"{failed_count}개 종목은 수정에 실패했습니다.")

def check_kis_token():
    """KIS API 토큰 상태 확인"""
    token_file = Path("data/kis_token.json")

    if not token_file.exists():
        print("ERROR: 토큰 파일(data/kis_token.json)이 존재하지 않습니다.")
        return False
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        expired_at = datetime.fromisoformat(token_data['expired_at'])
        if expired_at < datetime.now():
            return False
        return True
    except Exception as e:
        print(f"ERROR: 토큰 파일 읽기 실패: {e}")
        return False

if __name__ == "__main__":
    if not check_kis_token():
        print("KIS 토큰이 유효하지 않습니다. `reissue_kis_token.py`를 먼저 실행해주세요.")
    else:
        asyncio.run(fix_stock_names_in_db())
