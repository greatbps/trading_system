#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_oracle_db.py

Oracle 프리티어 데이터베이스 초기화 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 기본 설정 클래스
class OracleConfig:
    """Oracle 프리티어용 기본 설정"""

    def __init__(self):
        # 데이터베이스 설정 (Oracle 프리티어용)
        self.database = {
            'type': 'sqlite',  # Oracle 설치 전까지 SQLite 사용
            'url': 'sqlite:///./trading_system.db',
            'echo': False,
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600
        }

        # Oracle 연결 정보 (실제 Oracle 설치 후 사용)
        self.oracle = {
            'host': 'localhost',  # Oracle 프리티어 인스턴스 IP
            'port': 1521,
            'service_name': 'XEPDB1',  # Oracle XE 기본 서비스명
            'username': 'trading_user',
            'password': 'trading_password',
            'thick_mode': False  # Thin 모드 사용 (Oracle Instant Client 불필요)
        }

        # 로깅 설정
        self.logging = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'logs/trading_system.log'
        }

    def get_oracle_url(self):
        """Oracle 연결 URL 생성"""
        oracle = self.oracle
        return f"oracle+oracledb://{oracle['username']}:{oracle['password']}@{oracle['host']}:{oracle['port']}/{oracle['service_name']}"

async def initialize_database_with_config():
    """설정이 포함된 데이터베이스 초기화"""
    try:
        print("🚀 Oracle 프리티어 데이터베이스 초기화 시작...")

        # 설정 생성
        config = OracleConfig()

        # 데이터베이스 매니저 초기화
        from database.database_manager import DatabaseManager

        db_manager = DatabaseManager(config)

        print("📊 데이터베이스 초기화 중...")
        await db_manager.initialize_database()

        print("✅ 데이터베이스 초기화 완료!")

        # 기본 데이터 생성
        print("📝 기본 데이터 생성 중...")
        await create_sample_data(db_manager)

        print("🎉 Oracle 프리티어 설정 완료!")

        # 연결 테스트
        await test_database_connection(db_manager)

    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        import traceback
        traceback.print_exc()

async def create_sample_data(db_manager):
    """샘플 데이터 생성"""
    try:
        from database.models import Stock

        # 주요 종목 데이터
        sample_stocks = [
            {"code": "005930", "name": "삼성전자", "market": "KOSPI"},
            {"code": "000660", "name": "SK하이닉스", "market": "KOSPI"},
            {"code": "035420", "name": "NAVER", "market": "KOSPI"},
            {"code": "051910", "name": "LG화학", "market": "KOSPI"},
            {"code": "006400", "name": "삼성SDI", "market": "KOSPI"},
            {"code": "207940", "name": "삼성바이오로직스", "market": "KOSPI"},
            {"code": "068270", "name": "셀트리온", "market": "KOSPI"},
            {"code": "035720", "name": "카카오", "market": "KOSPI"},
            {"code": "028260", "name": "삼성물산", "market": "KOSPI"},
            {"code": "066570", "name": "LG전자", "market": "KOSPI"}
        ]

        # 주식 데이터 저장
        for stock_data in sample_stocks:
            try:
                await db_manager.upsert_stock(
                    code=stock_data["code"],
                    name=stock_data["name"],
                    market=stock_data["market"]
                )
                print(f"   📈 {stock_data['name']} ({stock_data['code']}) 추가")
            except Exception as e:
                print(f"   ⚠️ {stock_data['name']} 추가 실패: {e}")

        print("✅ 샘플 데이터 생성 완료")

    except Exception as e:
        print(f"❌ 샘플 데이터 생성 실패: {e}")

async def test_database_connection(db_manager):
    """데이터베이스 연결 테스트"""
    try:
        print("🔗 데이터베이스 연결 테스트 중...")

        # 주식 목록 조회 테스트
        stocks = await db_manager.get_all_stocks()
        print(f"   📊 등록된 주식 수: {len(stocks)}개")

        # 첫 번째 주식 정보 출력
        if stocks:
            first_stock = stocks[0]
            print(f"   📈 첫 번째 주식: {first_stock.name} ({first_stock.code})")

        print("✅ 데이터베이스 연결 테스트 통과")

    except Exception as e:
        print(f"❌ 데이터베이스 연결 테스트 실패: {e}")

def setup_oracle_connection():
    """Oracle 연결 설정 가이드"""
    print("""
📋 Oracle 프리티어 연결 설정 가이드:

1. Oracle Database 21c XE 설치 (무료)
   - https://www.oracle.com/database/technologies/xe-downloads.html

2. 사용자 및 테이블스페이스 생성:
   ```sql
   -- SYS 사용자로 접속 후 실행
   CREATE TABLESPACE trading_tbs
   DATAFILE '/opt/oracle/oradata/XE/trading_tbs.dbf'
   SIZE 100M AUTOEXTEND ON;

   CREATE USER trading_user IDENTIFIED BY trading_password
   DEFAULT TABLESPACE trading_tbs;

   GRANT CONNECT, RESOURCE, CREATE VIEW TO trading_user;
   GRANT UNLIMITED TABLESPACE TO trading_user;
   ```

3. Python Oracle 드라이버 설치:
   ```bash
   pip install oracledb
   ```

4. 설정 파일 수정:
   - setup_oracle_db.py의 oracle 설정에서 실제 연결 정보 입력

5. Oracle 모드로 전환:
   - database 설정의 'type'을 'oracle'로 변경
   - 'url'을 Oracle 연결 URL로 변경

현재는 SQLite로 실행되며, Oracle 설치 완료 후 위 설정을 적용하세요.
    """)

def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Oracle 프리티어 데이터베이스 설정')
    parser.add_argument('--guide', action='store_true', help='Oracle 연결 설정 가이드 표시')
    parser.add_argument('--init', action='store_true', help='데이터베이스 초기화 실행')

    args = parser.parse_args()

    if args.guide:
        setup_oracle_connection()
        return

    if args.init or len(sys.argv) == 1:
        # 로그 디렉토리 생성
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 비동기 초기화 실행
        asyncio.run(initialize_database_with_config())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()