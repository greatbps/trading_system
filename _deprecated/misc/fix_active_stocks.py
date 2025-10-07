#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/fix_active_stocks.py

활성 종목 상태 수정 스크립트
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import Config
    from utils.logger import get_logger
    from database.database_manager import DatabaseManager
    
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

logger = get_logger("FixActiveStocks")

async def fix_active_stocks():
    """모든 종목을 활성 상태로 변경"""
    try:
        logger.info("🔧 활성 종목 상태 수정 시작...")
        
        db_manager = DatabaseManager(Config)
        
        # 모든 종목을 활성 상태로 변경
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            
            # 현재 종목 상태 확인
            result = await session.execute(
                text("SELECT symbol, name, is_active FROM stocks")
            )
            stocks = result.fetchall()
            
            logger.info(f"📊 전체 종목 {len(stocks)}개 발견:")
            for stock in stocks:
                active_status = "활성" if stock[2] else "비활성"
                logger.info(f"  - {stock[0]} {stock[1]}: {active_status}")
            
            # 모든 종목을 활성 상태로 변경
            result = await session.execute(
                text("UPDATE stocks SET is_active = true WHERE is_active IS NULL OR is_active = false")
            )
            
            updated_count = result.rowcount
            logger.info(f"✅ {updated_count}개 종목을 활성 상태로 변경")
            
            await session.commit()
            
            # 변경 후 상태 확인
            active_stocks = await db_manager.get_active_stocks(limit=10)
            logger.info(f"📈 활성 종목 {len(active_stocks)}개:")
            for stock in active_stocks:
                logger.info(f"  - {stock['symbol']} {stock['name']}")
        
        logger.info("🎉 활성 종목 상태 수정 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 활성 종목 상태 수정 실패: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(fix_active_stocks())
    sys.exit(0 if success else 1)