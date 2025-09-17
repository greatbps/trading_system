#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/init_db.py

데이터베이스 초기화 스크립트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from database.database_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger("InitDB")

async def init_database():
    """데이터베이스 초기화"""
    try:
        logger.info("🗄️ 데이터베이스 초기화 시작...")
        
        # 설정 검증
        Config.validate()
        
        # 데이터베이스 매니저 생성
        db_manager = DatabaseManager(Config)
        
        # 테이블 생성
        await db_manager.create_tables()
        
        logger.info("✅ 데이터베이스 초기화 완료!")
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_database())