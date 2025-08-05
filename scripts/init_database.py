#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/init_database.py

데이터베이스 초기화 스크립트
PostgreSQL 데이터베이스 생성 및 초기 데이터 설정
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import (
    create_database_engine, create_all_tables, get_session_factory, get_session,
    insert_initial_data, Stock, AccountInfo
)
from config import Config
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """데이터베이스 초기화"""
    try:
        # 환경 설정 로드
        config = Config()
        
        logger.info("데이터베이스 연결 중...")
        # 데이터베이스 엔진 생성
        engine = create_database_engine(config.DATABASE_URL, echo=True)
        
        logger.info("테이블 생성 중...")
        # 모든 테이블 생성
        create_all_tables(engine)
        
        # 세션 생성
        session_factory = get_session_factory(engine)
        session = get_session(session_factory)
        
        try:
            logger.info("초기 데이터 삽입 중...")
            # 초기 데이터 삽입
            insert_initial_data(session)
            
            logger.info("✅ 데이터베이스 초기화 완료!")
            return True
            
        except Exception as e:
            logger.error(f"초기 데이터 삽입 실패: {e}")
            session.rollback()
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        return False

def drop_all_tables():
    """모든 테이블 삭제 (주의!)"""
    try:
        config = Config()
        engine = create_database_engine(config.DATABASE_URL)
        
        logger.warning("⚠️  모든 테이블을 삭제합니다!")
        from database.models import Base
        Base.metadata.drop_all(engine)
        
        logger.info("✅ 모든 테이블이 삭제되었습니다.")
        return True
        
    except Exception as e:
        logger.error(f"테이블 삭제 실패: {e}")
        return False

def reset_database():
    """데이터베이스 리셋 (삭제 후 재생성)"""
    logger.info("데이터베이스 리셋 시작...")
    
    if drop_all_tables():
        logger.info("테이블 삭제 완료, 재생성 중...")
        return init_database()
    else:
        logger.error("데이터베이스 리셋 실패")
        return False

def check_database_connection():
    """데이터베이스 연결 확인"""
    try:
        config = Config()
        engine = create_database_engine(config.DATABASE_URL)
        
        # 연결 테스트
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ 데이터베이스 연결 성공!")
            return True
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        return False

def show_table_info():
    """테이블 정보 출력"""
    try:
        config = Config()
        engine = create_database_engine(config.DATABASE_URL)
        session_factory = get_session_factory(engine)
        session = get_session(session_factory)
        
        try:
            # 각 테이블의 레코드 수 확인
            from database.models import (
                Stock, FilteredStock, AnalysisResult, Trade, 
                Portfolio, AccountInfo, MarketData, SystemLog, TradingSession
            )
            
            models = [
                ('stocks', Stock),
                ('filtered_stocks', FilteredStock),
                ('analysis_results', AnalysisResult),
                ('trades', Trade),
                ('portfolio', Portfolio),
                ('account_info', AccountInfo),
                ('market_data', MarketData),
                ('system_logs', SystemLog),
                ('trading_sessions', TradingSession)
            ]
            
            logger.info("\n📊 데이터베이스 현황:")
            logger.info("-" * 50)
            
            for table_name, model_class in models:
                try:
                    count = session.query(model_class).count()
                    logger.info(f"{table_name:20} : {count:>8} 건")
                except Exception as e:
                    logger.warning(f"{table_name:20} : 테이블 없음")
            
            logger.info("-" * 50)
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"테이블 정보 조회 실패: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "init":
            logger.info("🚀 데이터베이스 초기화 시작...")
            success = init_database()
            if success:
                show_table_info()
            
        elif command == "reset":
            logger.info("🔄 데이터베이스 리셋 시작...")
            success = reset_database()
            if success:
                show_table_info()
                
        elif command == "drop":
            logger.info("🗑️  테이블 삭제 시작...")
            drop_all_tables()
            
        elif command == "check":
            logger.info("🔍 데이터베이스 연결 확인...")
            check_database_connection()
            
        elif command == "info":
            logger.info("📋 테이블 정보 조회...")
            show_table_info()
            
        else:
            print("사용법:")
            print("  python scripts/init_database.py init    # 데이터베이스 초기화")
            print("  python scripts/init_database.py reset   # 데이터베이스 리셋")
            print("  python scripts/init_database.py drop    # 모든 테이블 삭제")
            print("  python scripts/init_database.py check   # 연결 확인")
            print("  python scripts/init_database.py info    # 테이블 정보")
    else:
        # 기본 동작: 초기화
        logger.info("🚀 데이터베이스 초기화 시작...")
        success = init_database()
        if success:
            show_table_info()