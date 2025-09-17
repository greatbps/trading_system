#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENUM 타입에 누락된 값들을 추가하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import create_database_engine
from config import DatabaseConfig
from sqlalchemy import text

def fix_enum_values():
    """ENUM 타입에 누락된 값들을 추가"""
    try:
        engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)

        print("=== ENUM 타입 값 추가 ===")

        with engine.connect() as conn:
            # monitoringstatus에 PAUSED 추가 (만약 없다면)
            try:
                conn.execute(text("ALTER TYPE monitoringstatus ADD VALUE IF NOT EXISTS 'PAUSED'"))
                print("[OK] monitoringstatus에 PAUSED 추가")
            except Exception as e:
                print(f"[INFO] monitoringstatus PAUSED 추가 실패 (이미 존재할 수 있음): {e}")

            # monitoringtype에 PORTFOLIO 추가 (만약 없다면)
            try:
                conn.execute(text("ALTER TYPE monitoringtype ADD VALUE IF NOT EXISTS 'PORTFOLIO'"))
                print("[OK] monitoringtype에 PORTFOLIO 추가")
            except Exception as e:
                print(f"[INFO] monitoringtype PORTFOLIO 추가 실패 (이미 존재할 수 있음): {e}")

            conn.commit()

            # 이제 monitoring_type 컬럼 변경 재시도
            print("\n[2] monitoring_stocks.monitoring_type 컬럼을 monitoringtype ENUM으로 재시도...")
            try:
                conn.execute(text("""
                    ALTER TABLE monitoring_stocks
                    ALTER COLUMN monitoring_type TYPE monitoringtype
                    USING monitoring_type::monitoringtype
                """))
                print("    [OK] monitoring_type 컬럼 변경 완료")
                conn.commit()
            except Exception as e:
                print(f"    [ERROR] monitoring_type 컬럼 변경 여전히 실패: {e}")

            # 변경 결과 확인
            result = conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'monitoring_stocks'
                AND column_name IN ('status', 'monitoring_type')
            """))

            print("\n[확인] 최종 컬럼 타입:")
            for row in result:
                print(f"  {row[0]}: {row[1]} ({row[2]})")

    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_enum_values()