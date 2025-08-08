#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데이터베이스 Foreign Key 제약 조건 수정 스크립트"""

import asyncio
import sys
sys.path.append('.')

from database.database_manager import DatabaseManager
from config import Config
from sqlalchemy import text

async def fix_foreign_keys():
    """Foreign Key 제약 조건 수정"""
    print("Foreign Key 제약 조건 수정 시작...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # 데이터베이스 연결
        async with db_manager.get_async_session() as session:
            
            # filtered_stock_id를 NULL 허용으로 변경
            try:
                await session.execute(
                    text("ALTER TABLE analysis_results ALTER COLUMN filtered_stock_id DROP NOT NULL")
                )
                print("[OK] filtered_stock_id NULL 허용으로 변경")
            except Exception as e:
                print(f"[WARN] filtered_stock_id 변경 실패: {e}")
            
            # stock_id를 NULL 허용으로 변경
            try:
                await session.execute(
                    text("ALTER TABLE analysis_results ALTER COLUMN stock_id DROP NOT NULL")
                )
                print("[OK] stock_id NULL 허용으로 변경")
            except Exception as e:
                print(f"[WARN] stock_id 변경 실패: {e}")
            
            await session.commit()
            print("\n[SUCCESS] Foreign Key 제약 조건 수정 완료!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Foreign Key 제약 조건 수정 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(fix_foreign_keys())
    if result:
        print("\n[SUCCESS] Foreign Key 제약 조건이 성공적으로 수정되었습니다.")
    else:
        print("\n[FAILED] Foreign Key 제약 조건 수정에 실패했습니다.")