#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/test_db.py

데이터베이스 연결 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import Config
    from utils.logger import get_logger
    from database.database_manager import DatabaseManager
    
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("현재 디렉토리:", Path.cwd())
    print("프로젝트 루트:", PROJECT_ROOT)
    print("\n💡 해결 방법:")
    print("1. trading_system 디렉토리에서 실행하세요:")
    print("   cd trading_system")
    print("   python database/test_db.py")
    sys.exit(1)

logger = get_logger("TestDB")

async def test_database():
    """데이터베이스 연결 테스트"""
    try:
        logger.info("🧪 데이터베이스 연결 테스트 시작...")
        
        # 설정 확인
        logger.info(f"데이터베이스 URL: {Config.database.DB_URL}")
        
        db_manager = DatabaseManager(Config)
        logger.info("✅ 데이터베이스 매니저 생성 성공")
        
        # 1. 종목 저장 테스트
        logger.info("1. 종목 저장 테스트...")
        test_stock = {
            "symbol": "TEST001",
            "name": "테스트종목",
            "market": "KOSPI",
            "sector": "테스트",
            "current_price": 10000,
            "market_cap": 1000000,
            "pe_ratio": 10.0,
            "pbr": 1.0
        }
        
        stock_id = await db_manager.save_stock(test_stock)
        if stock_id:
            logger.info(f"✅ 종목 저장 성공: ID {stock_id}")
        else:
            logger.error("❌ 종목 저장 실패")
            return False
        
        # 2. 종목 조회 테스트
        logger.info("2. 종목 조회 테스트...")
        stock = await db_manager.get_stock_by_symbol("TEST001")
        if stock:
            logger.info(f"✅ 종목 조회 성공: {stock['name']} (ID: {stock['id']})")
        else:
            logger.error("❌ 종목 조회 실패")
            return False
        
        # 3. 분석 결과 저장 테스트
        logger.info("3. 분석 결과 저장 테스트...")
        analysis_data = {
            "stock_id": stock_id,
            "analysis_date": datetime.now(),
            "strategy": "momentum",
            "comprehensive_score": 75.5,
            "recommendation": "BUY",
            "confidence": 0.8,
            "technical_score": 80.0,
            "fundamental_score": 70.0,
            "sentiment_score": 75.0,
            "signal_strength": 78.0,
            "signal_type": "BUY",
            "action": "BUY",
            "risk_level": "MEDIUM",
            "price_at_analysis": 10000,
            "technical_details": {"rsi": 65, "macd": "bullish"},
            "fundamental_details": {"pe": 10.0, "pbr": 1.0},
            "sentiment_details": {"news_sentiment": "positive"}
        }
        
        analysis_id = await db_manager.save_analysis_result(analysis_data)
        if analysis_id:
            logger.info(f"✅ 분석 결과 저장 성공: ID {analysis_id}")
        else:
            logger.error("❌ 분석 결과 저장 실패")
            return False
        
        # 4. 활성 종목 리스트 조회 테스트
        logger.info("4. 활성 종목 리스트 조회 테스트...")
        active_stocks = await db_manager.get_active_stocks(limit=10)
        logger.info(f"✅ 활성 종목 {len(active_stocks)}개 조회 성공")
        
        for stock in active_stocks[:3]:
            logger.info(f"  - {stock['symbol']} {stock['name']}")
        
        # 5. 최신 분석 결과 조회 테스트
        logger.info("5. 최신 분석 결과 조회 테스트...")
        latest_analysis = await db_manager.get_latest_analysis("TEST001", "momentum")
        if latest_analysis:
            logger.info(f"✅ 최신 분석 결과 조회 성공: 점수 {latest_analysis['comprehensive_score']}")
        else:
            logger.warning("⚠️ 최신 분석 결과 없음")
        
        # 6. 포트폴리오 요약 테스트
        logger.info("6. 포트폴리오 요약 테스트...")
        portfolio_summary = await db_manager.get_portfolio_summary()
        logger.info(f"✅ 포트폴리오 요약 조회 성공: 포지션 {portfolio_summary['total_positions']}개")
        
        logger.info("🎉 모든 데이터베이스 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 테스트 실패: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

async def test_connection_only():
    """기본 연결만 테스트"""
    try:
        logger.info("🔌 데이터베이스 기본 연결 테스트...")
        
        db_manager = DatabaseManager(Config)
        
        # 간단한 쿼리 실행
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            
            if test_value == 1:
                logger.info("✅ 데이터베이스 연결 성공!")
                return True
            else:
                logger.error("❌ 연결 테스트 실패")
                return False
                
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="데이터베이스 테스트")
    parser.add_argument("--connection-only", action="store_true", help="연결 테스트만 실행")
    args = parser.parse_args()
    
    if args.connection_only:
        success = asyncio.run(test_connection_only())
    else:
        success = asyncio.run(test_database())
    
    sys.exit(0 if success else 1)