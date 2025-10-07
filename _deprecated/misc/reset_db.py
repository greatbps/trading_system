#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/reset_db.py

데이터베이스 리셋 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Any

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import Config
    from utils.logger import get_logger
    from database.database_manager import DatabaseManager
    
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

logger = get_logger("ResetDB")

async def reset_database(force: bool = False):
    """데이터베이스 완전 리셋"""
    try:
        if not force:
            print("⚠️ 이 작업은 모든 데이터베이스 테이블과 데이터를 삭제합니다!")
            response = input("계속하시겠습니까? (yes/no): ").lower()
            if response not in ['yes', 'y']:
                print("작업이 취소되었습니다.")
                return False
        
        logger.info("🗑️ 데이터베이스 리셋 시작...")
        
        # 데이터베이스 매니저 생성
        db_manager = DatabaseManager(Config)
        
        # 기존 테이블 삭제
        await db_manager.drop_tables()
        logger.info("✅ 기존 테이블 삭제 완료")
        
        # 새 테이블 생성
        await db_manager.create_tables()
        logger.info("✅ 새 테이블 생성 완료")
        
        logger.info("🎉 데이터베이스 리셋 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 리셋 실패: {e}")
        return False

async def safe_init_database():
    """안전한 데이터베이스 초기화"""
    try:
        logger.info("🗄️ 안전한 데이터베이스 초기화 시작...")
        
        # 설정 검증
        Config.validate()
        logger.info("✅ 설정 검증 완료")
        
        # 데이터베이스 매니저 생성
        db_manager = DatabaseManager(Config)
        
        # 데이터베이스 파일 확인 (SQLite인 경우)
        db_url = Config.database.DB_URL
        if db_url.startswith('sqlite://'):
            db_file = db_url.replace('sqlite:///', '')
            if os.path.exists(db_file):
                logger.info(f"📁 기존 데이터베이스 파일 발견: {db_file}")
                
                # 백업 생성
                backup_file = f"{db_file}.backup_{int(asyncio.get_event_loop().time())}"
                import shutil
                shutil.copy2(db_file, backup_file)
                logger.info(f"💾 백업 파일 생성: {backup_file}")
        
        # 테이블 생성 (이미 존재하면 스킵)
        await db_manager.create_tables()
        
        # 샘플 데이터 삽입
        await insert_sample_data(db_manager)
        
        logger.info("🎉 안전한 데이터베이스 초기화 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

async def insert_sample_data(db_manager: Any):
    """샘플 데이터 삽입"""
    try:
        logger.info("📝 샘플 데이터 확인 및 삽입 중...")
        
        # 기존 데이터 확인
        existing_stocks = await db_manager.get_active_stocks(limit=10)
        if existing_stocks:
            logger.info(f"📊 기존 종목 데이터 {len(existing_stocks)}개 발견")
            logger.info("새로운 샘플 데이터 삽입을 건너뜁니다.")
            return
        
        # 주요 종목들 샘플 데이터
        sample_stocks = [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI",
                "sector": "반도체",
                "current_price": 50000,
                "market_cap": 300000000,
                "pe_ratio": 12.5,
                "pbr": 1.2
            },
            {
                "symbol": "000660",
                "name": "SK하이닉스",
                "market": "KOSPI", 
                "sector": "반도체",
                "current_price": 80000,
                "market_cap": 60000000,
                "pe_ratio": 8.5,
                "pbr": 1.0
            },
            {
                "symbol": "035720",
                "name": "카카오",
                "market": "KOSPI",
                "sector": "IT서비스",
                "current_price": 45000,
                "market_cap": 20000000,
                "pe_ratio": 15.0,
                "pbr": 2.5
            },
            {
                "symbol": "035420",
                "name": "NAVER",
                "market": "KOSPI",
                "sector": "IT서비스", 
                "current_price": 180000,
                "market_cap": 30000000,
                "pe_ratio": 18.0,
                "pbr": 2.0
            },
            {
                "symbol": "051910",
                "name": "LG화학",
                "market": "KOSPI",
                "sector": "화학",
                "current_price": 400000,
                "market_cap": 28000000,
                "pe_ratio": 11.0,
                "pbr": 1.5
            }
        ]
        
        inserted_count = 0
        for stock_data in sample_stocks:
            stock_id = await db_manager.save_stock(stock_data)
            if stock_id:
                logger.info(f"✅ 샘플 종목 저장: {stock_data['symbol']} {stock_data['name']}")
                inserted_count += 1
        
        logger.info(f"📊 총 {inserted_count}개 샘플 종목 삽입 완료")
        
    except Exception as e:
        logger.warning(f"⚠️ 샘플 데이터 삽입 실패: {e}")

async def check_database_status():
    """데이터베이스 상태 확인"""
    try:
        logger.info("🔍 데이터베이스 상태 확인 중...")
        
        db_manager = DatabaseManager(Config)
        
        # 기본 연결 테스트
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            if result.fetchone()[0] == 1:
                logger.info("✅ 데이터베이스 연결 정상")
            
        # 테이블 존재 확인
        stats = await db_manager.get_database_stats()
        if stats:
            logger.info("📊 데이터베이스 통계:")
            for key, value in stats.items():
                if key.endswith('_count'):
                    table_name = key.replace('_count', '')
                    logger.info(f"  {table_name}: {value}개")
        
        # 종목 데이터 확인
        stocks = await db_manager.get_active_stocks(limit=5)
        logger.info(f"📈 활성 종목 {len(stocks)}개:")
        for stock in stocks[:3]:
            logger.info(f"  - {stock['symbol']} {stock['name']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 상태 확인 실패: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="데이터베이스 관리 도구")
    parser.add_argument("--reset", action="store_true", help="데이터베이스 완전 리셋")
    parser.add_argument("--force", action="store_true", help="확인 없이 강제 실행")
    parser.add_argument("--init", action="store_true", help="안전한 초기화")
    parser.add_argument("--status", action="store_true", help="상태 확인")
    
    args = parser.parse_args()
    
    if args.reset:
        success = asyncio.run(reset_database(force=args.force))
    elif args.init:
        success = asyncio.run(safe_init_database())
    elif args.status:
        success = asyncio.run(check_database_status())
    else:
        # 기본값: 안전한 초기화
        success = asyncio.run(safe_init_database())
    
    sys.exit(0 if success else 1)