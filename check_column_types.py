#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 컬럼 타입 확인 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import create_database_engine
from config import DatabaseConfig
from sqlalchemy import text

def check_column_types():
    """데이터베이스 컬럼 타입 확인"""
    try:
        engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)

        print("=== 데이터베이스 컬럼 타입 확인 ===")

        with engine.connect() as conn:
            # monitoring_stocks 테이블의 status 컬럼 타입 확인
            result = conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'monitoring_stocks'
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """))

            print("\n[TABLE] monitoring_stocks 컬럼 정보:")
            for row in result:
                print(f"  {row[0]}: {row[1]} ({row[2]})")

            # 특히 status와 monitoring_type 컬럼 확인
            result = conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'monitoring_stocks'
                AND column_name IN ('status', 'monitoring_type')
            """))

            print("\n[ENUM 컬럼들] status, monitoring_type:")
            for row in result:
                print(f"  {row[0]}: {row[1]} ({row[2]})")

            # ENUM 타입들 확인
            result = conn.execute(text("""
                SELECT typname, enumlabel
                FROM pg_type
                JOIN pg_enum ON pg_type.oid = pg_enum.enumtypid
                WHERE typname IN ('monitoringstatus', 'monitoringtype')
                ORDER BY typname, enumsortorder
            """))

            print("\n[ENUM 타입 값들]:")
            current_type = None
            for row in result:
                if row[0] != current_type:
                    current_type = row[0]
                    print(f"  {current_type}:")
                print(f"    - {row[1]}")

    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_column_types()