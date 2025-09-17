#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시스템 통합 테스트 - 수정된 KIS Collector 테스트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

async def test_kis_collector():
    """수정된 KIS Collector 테스트"""
    
    logger = get_logger("KISTest")
    config = Config()
    
    logger.info("=== KIS Collector 통합 테스트 ===")
    
    try:
        # KIS Collector 초기화
        collector = KISCollector(config)
        
        logger.info("KIS Collector 초기화 완료")
        
        # 초기화
        await collector.initialize()
        logger.info("KIS Collector 초기화 성공")
        
        # 간단한 API 호출 테스트 - 삼성전자 현재가 조회
        logger.info("삼성전자 현재가 조회 테스트...")
        
        stock_data = await collector.get_stock_data("005930")

        if stock_data:
            logger.info("SUCCESS: 주식 데이터 조회 성공!")
            logger.info(f"데이터 키: {list(stock_data.keys())}")
            # 주요 데이터 출력
            if 'current_price' in stock_data:
                logger.info(f"현재가: {stock_data.get('current_price')}")
            if 'change' in stock_data:
                logger.info(f"전일대비: {stock_data.get('change')}")
            if 'change_rate' in stock_data:
                logger.info(f"등락률: {stock_data.get('change_rate')}%")
            return True
        else:
            logger.error("ERROR: 주식 데이터 조회 실패")
            return False
            
    except Exception as e:
        logger.error(f"ERROR: 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 정리
        if 'collector' in locals():
            await collector.cleanup()

async def main():
    print("=" * 60)
    print("KIS Collector 시스템 통합 테스트")
    print("=" * 60)

    success = await test_kis_collector()

    print("\n" + "=" * 60)
    if success:
        print("SUCCESS: 시스템 통합 테스트 성공!")
    else:
        print("ERROR: 시스템 통합 테스트 실패!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
