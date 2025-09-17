#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 컬럼 타입을 ENUM으로 변경하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import create_database_engine
from config import DatabaseConfig
from sqlalchemy import text

def fix_column_types():
    """컬럼 타입을 ENUM으로 변경"""
    try:
        engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)

        print("=== 컬럼 타입을 ENUM으로 변경 ===")

        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()

            try:
                # monitoring_stocks 테이블의 status 컬럼을 monitoringstatus ENUM으로 변경
                print("[1] monitoring_stocks.status 컬럼을 monitoringstatus ENUM으로 변경...")
                conn.execute(text("""
                    ALTER TABLE monitoring_stocks
                    ALTER COLUMN status TYPE monitoringstatus
                    USING status::monitoringstatus
                """))
                print("    [OK] status 컬럼 변경 완료")

                # monitoring_stocks 테이블의 monitoring_type 컬럼을 monitoringtype ENUM으로 변경
                print("[2] monitoring_stocks.monitoring_type 컬럼을 monitoringtype ENUM으로 변경...")
                conn.execute(text("""
                    ALTER TABLE monitoring_stocks
                    ALTER COLUMN monitoring_type TYPE monitoringtype
                    USING monitoring_type::monitoringtype
                """))
                print("    [OK] monitoring_type 컬럼 변경 완료")

                # 변경 사항 커밋
                trans.commit()
                print("\n[SUCCESS] 모든 컬럼 타입 변경이 완료되었습니다!")

                # 변경 결과 확인
                result = conn.execute(text("""
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_name = 'monitoring_stocks'
                    AND column_name IN ('status', 'monitoring_type')
                """))

                print("\n[확인] 변경된 컬럼 타입:")
                for row in result:
                    print(f"  {row[0]}: {row[1]} ({row[2]})")

            except Exception as e:
                trans.rollback()
                print(f"[ERROR] 컬럼 타입 변경 실패: {e}")
                print("트랜잭션을 롤백했습니다.")
                raise

    except Exception as e:
        print(f"[ERROR] 전체 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_column_types()