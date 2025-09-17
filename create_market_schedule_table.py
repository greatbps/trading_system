#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def create_market_schedule_table():
    """MarketScheduleCache 테이블 생성"""
    try:
        print("=== MarketScheduleCache 테이블 생성 ===")
        
        from database.models import MarketScheduleCache, Base
        from sqlalchemy import create_engine
        from config import Config
        
        config = Config()
        print(f"데이터베이스 URL: {config.database.DB_URL}")
        
        # 엔진 생성
        engine = create_engine(config.database.DB_URL)
        
        # MarketScheduleCache 테이블만 생성
        MarketScheduleCache.__table__.create(engine, checkfirst=True)
        
        print("OK MarketScheduleCache 테이블 생성 완료")
        return True
        
    except Exception as e:
        print(f"ERROR 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_market_schedule_table()
    if success:
        print("\n테이블 생성 완료!")
    else:
        print("\n테이블 생성 실패!")