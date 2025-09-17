#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL ENUM 타입 생성 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import create_database_engine
from config import DatabaseConfig
from sqlalchemy import text

def fix_enum_types():
    """PostgreSQL ENUM 타입들을 재생성"""
    try:
        # 데이터베이스 엔진 생성
        engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)

        print("=== PostgreSQL ENUM 타입 수정 ===")
        print(f"Database URL: {DatabaseConfig.DB_URL}")

        if "postgresql" not in str(engine.url):
            print("PostgreSQL 데이터베이스가 아닙니다.")
            return

        with engine.connect() as conn:
            # ENUM 타입들을 명시적으로 생성 (존재하지 않는 경우만)
            enum_types = [
                ("tradetype", ["BUY", "SELL"]),
                ("orderstatus", ["PENDING", "FILLED", "PARTIAL", "CANCELLED", "FAILED"]),
                ("ordertype", ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]),
                ("portfoliostatus", ["OPEN", "CLOSED", "CLOSING"]),
                ("analysisgrade", ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]),
                ("risklevel", ["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                ("loglevel", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
                ("market", ["KOSPI", "KOSDAQ", "KONEX"]),
                ("sessionstatus", ["ACTIVE", "COMPLETED", "STOPPED", "PAUSED"]),
                ("monitoringstatus", ["ACTIVE", "INACTIVE", "PAUSED", "COMPLETED", "REMOVED"]),
                ("monitoringtype", ["TRADING", "REMOVAL_WATCH", "PORTFOLIO"]),
                ("newsperiodtype", ["SHORT_TERM", "MID_TERM", "LONG_TERM", "NEUTRAL"]),
                ("analysissessiontype", ["COMPREHENSIVE", "NEWS_ONLY", "SUPPLY_DEMAND", "TECHNICAL", "FUNDAMENTAL"]),
                ("winlossstatus", ["WIN", "LOSS", "DRAW"])
            ]

            print(f"\n총 {len(enum_types)}개의 ENUM 타입을 확인합니다...")

            for enum_name, values in enum_types:
                try:
                    # ENUM 타입이 존재하는지 확인
                    result = conn.execute(text(f"SELECT 1 FROM pg_type WHERE typname = '{enum_name}'"))
                    if not result.fetchone():
                        # ENUM 타입 생성
                        values_str = "', '".join(values)
                        create_enum_sql = f"CREATE TYPE {enum_name} AS ENUM ('{values_str}')"
                        conn.execute(text(create_enum_sql))
                        print(f"[OK] Created ENUM type: {enum_name}")
                    else:
                        print(f"[INFO] ENUM type already exists: {enum_name}")
                except Exception as e:
                    print(f"[ERROR] Error with ENUM type {enum_name}: {e}")

            conn.commit()
            print("\n=== ENUM 타입 수정 완료 ===")

    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_enum_types()