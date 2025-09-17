#!/usr/bin/env python3
"""
간단한 잔고 조회 테스트 - 원래 HTTP 500 에러가 해결되었는지 확인
"""

import asyncio
from data_collectors.kis_collector import KISCollector
from utils.logger import setup_logger
from config.config import Config

async def test_balance_check():
    """잔고 조회 테스트로 HTTP 500 에러 해결 확인"""
    logger = setup_logger("test_balance")

    logger.info("=== KIS 잔고 조회 테스트 시작 ===")

    try:
        # 설정 로드
        config = Config()

        # KIS Collector 초기화
        collector = KISCollector(config, logger=logger)
        await collector.initialize()

        logger.info("KIS Collector 초기화 완료")

        # 잔고 조회 시도 (원래 HTTP 500 에러가 발생했던 부분)
        logger.info("계좌 잔고 조회 중...")
        balance = await collector.get_account_balance()

        if balance:
            logger.info("✅ 잔고 조회 성공!")
            logger.info(f"계좌 정보: {list(balance.keys())}")
            return True
        else:
            logger.warning("잔고 조회 결과가 없습니다")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False
    finally:
        try:
            if 'collector' in locals():
                await collector.cleanup()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_balance_check())
    if success:
        print("\nHTTP 500 token error has been resolved!")
    else:
        print("\nThere may still be issues.")