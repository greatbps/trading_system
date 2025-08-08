#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데이터베이스 제약 조건 수정 스크립트"""

import asyncio
import sys
sys.path.append('.')

from database.database_manager import DatabaseManager
from config import Config
from sqlalchemy import text

async def fix_constraints():
    """점수 제약 조건을 0-100 범위로 수정"""
    print("데이터베이스 제약 조건 수정 시작...")
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        # 데이터베이스 연결
        async with db_manager.get_async_session() as session:
            
            # 기존 제약 조건 삭제
            constraints_to_drop = [
                "check_technical_score_range",
                "check_supply_demand_score_range"
            ]
            
            for constraint in constraints_to_drop:
                try:
                    await session.execute(
                        text(f"ALTER TABLE analysis_results DROP CONSTRAINT IF EXISTS {constraint}")
                    )
                    print(f"[OK] 기존 제약 조건 삭제: {constraint}")
                except Exception as e:
                    print(f"[WARN] 제약 조건 삭제 실패 (무시): {constraint} - {e}")
            
            # 새로운 제약 조건 추가
            new_constraints = [
                ("check_technical_score_range", "technical_score >= 0 AND technical_score <= 100"),
                ("check_supply_demand_score_range", "supply_demand_score >= 0 AND supply_demand_score <= 100")
            ]
            
            for constraint_name, constraint_condition in new_constraints:
                try:
                    await session.execute(
                        text(f"ALTER TABLE analysis_results ADD CONSTRAINT {constraint_name} CHECK ({constraint_condition})")
                    )
                    print(f"[OK] 새 제약 조건 추가: {constraint_name}")
                except Exception as e:
                    print(f"[ERROR] 제약 조건 추가 실패: {constraint_name} - {e}")
            
            await session.commit()
            print("\n[SUCCESS] 데이터베이스 제약 조건 수정 완료!")
            return True
            
    except Exception as e:
        print(f"[ERROR] 제약 조건 수정 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(fix_constraints())
    if result:
        print("\n[SUCCESS] 제약 조건이 성공적으로 수정되었습니다.")
    else:
        print("\n[FAILED] 제약 조건 수정에 실패했습니다.")