#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB 스키마를 업데이트하는 스크립트.
- monitoring_stocks 테이블에 buy_trade_id 컬럼을 추가합니다.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DatabaseConfig

def add_buy_trade_id_column():
    """monitoring_stocks 테이블에 buy_trade_id 컬럼을 추가합니다."""
    print("DB 스키마 업데이트를 시작합니다...")
    
    try:
        engine = create_engine(DatabaseConfig.DB_URL)
        
        # SQL 명령 정의
        # IF NOT EXISTS는 PostgreSQL 표준이 아니므로, 별도 체크 로직 사용
        check_column_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='monitoring_stocks' AND column_name='buy_trade_id';
        """
        
        add_column_sql = """
        ALTER TABLE monitoring_stocks ADD COLUMN buy_trade_id INTEGER;
        """
        
        with engine.connect() as connection:
            # 1. 컬럼 존재 여부 확인
            print("1. 'buy_trade_id' 컬럼 존재 여부 확인 중...")
            result = connection.execute(text(check_column_sql))
            column_exists = result.fetchone()
            
            if column_exists:
                print("[OK] 'buy_trade_id' 컬럼이 이미 존재합니다. 스키마 업데이트가 필요 없습니다.")
                return

            # 2. 컬럼 추가
            print("2. 'buy_trade_id' 컬럼을 추가합니다...")
            connection.execute(text(add_column_sql))
            
            # 트랜잭션 커밋
            connection.commit()
            print("[OK] 성공: monitoring_stocks 테이블에 buy_trade_id 컬럼을 추가했습니다.")

    except (OperationalError, ProgrammingError) as e:
        print(f"[ERROR] 데이터베이스 오류가 발생했습니다: {e}")
        print("DB 연결 정보나 테이블 이름을 확인해주세요.")
    except Exception as e:
        print(f"[ERROR] 알 수 없는 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    add_buy_trade_id_column()
