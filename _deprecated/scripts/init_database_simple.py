#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 초기화 스크립트
모든 테이블을 생성합니다.
"""

import sys
from sqlalchemy import create_engine
from database.models import Base
from config import Config
from utils.logger import get_logger

logger = get_logger("InitDatabase")

def init_database():
    """데이터베이스 테이블 초기화"""
    try:
        # 설정 로드
        config = Config()
        db_url = config.database.DB_URL

        logger.info(f"🔗 데이터베이스 연결 중: {db_url.split('@')[-1]}")

        # 엔진 생성
        engine = create_engine(db_url, echo=False)

        # 모든 테이블 생성
        logger.info("📊 데이터베이스 테이블 생성 중...")
        Base.metadata.create_all(engine)

        logger.info("✅ 데이터베이스 초기화 완료!")
        logger.info(f"✅ 생성된 테이블 수: {len(Base.metadata.tables)}")

        # 생성된 테이블 목록 출력
        logger.info("📋 생성된 테이블:")
        for table_name in sorted(Base.metadata.tables.keys()):
            logger.info(f"  - {table_name}")

        return True

    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
