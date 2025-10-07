#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
컬럼 값들을 확인하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import create_database_engine
from config import DatabaseConfig
from sqlalchemy import text

def check_column_values():
    """컬럼에 있는 실제 값들을 확인"""
    try:
        engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)

        print("=== 컬럼 값 확인 ===")

        with engine.connect() as conn:
            # monitoring_stocks 테이블의 monitoring_type 값들 확인
            result = conn.execute(text("""
                SELECT DISTINCT monitoring_type, COUNT(*)
                FROM monitoring_stocks
                WHERE monitoring_type IS NOT NULL
                GROUP BY monitoring_type
                ORDER BY monitoring_type
            """))

            print("\n[monitoring_type 값들]:")
            for row in result:
                print(f"  '{row[0]}': {row[1]}개")

            # status 값들도 확인
            result = conn.execute(text("""
                SELECT DISTINCT status, COUNT(*)
                FROM monitoring_stocks
                WHERE status IS NOT NULL
                GROUP BY status
                ORDER BY status
            """))

            print("\n[status 값들]:")
            for row in result:
                print(f"  '{row[0]}': {row[1]}개")

            # ENUM 타입에 정의된 값들 확인
            result = conn.execute(text("""
                SELECT typname, enumlabel
                FROM pg_type
                JOIN pg_enum ON pg_type.oid = pg_enum.enumtypid
                WHERE typname IN ('monitoringstatus', 'monitoringtype')
                ORDER BY typname, enumsortorder
            """))

            print("\n[ENUM 타입에 정의된 값들]:")
            current_type = None
            for row in result:
                if row[0] != current_type:
                    current_type = row[0]
                    print(f"  {current_type}:")
                print(f"    - '{row[1]}'")

    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_column_values()