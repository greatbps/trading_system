#!/usr/bin/env python3
"""
Test if token needs activation delay and try a simpler endpoint
"""

import asyncio
import aiohttp
from data_collectors.kis_collector import KISTokenManager
from utils.logger import setup_logger
from config.config import Config
import time

async def test_token_with_delay():
    """토큰 활성화 지연 및 다른 엔드포인트 테스트"""
    logger = setup_logger("test_delay")

    logger.info("=== 토큰 활성화 지연 테스트 ===")

    config = Config()

    token_manager = KISTokenManager(
        app_key=config.kis.APP_KEY,
        app_secret=config.kis.APP_SECRET,
        base_url=config.kis.URL_BASE,
        logger=logger
    )

    async with aiohttp.ClientSession() as session:
        try:
            # 새 토큰 요청
            logger.info("새 토큰 요청...")
            success = await token_manager.request_new_token(session)

            if success:
                logger.info("✅ 토큰 획득 완료")

                # 3초 대기 (토큰 활성화 대기)
                logger.info("토큰 활성화를 위해 3초 대기...")
                await asyncio.sleep(3)

                headers = token_manager.get_headers()

                # 더 간단한 엔드포인트 테스트 - 현재시간 조회
                logger.info("=== 현재시간 조회 API 테스트 ===")
                time_url = f"{config.kis.URL_BASE}/uapi/domestic-stock/v1/quotations/inquire-time"

                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(time_url, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()
                    logger.info(f"시간 조회 응답 상태: {response.status}")
                    logger.info(f"시간 조회 응답: {response_text[:300]}")

                # 잔고 조회 API 테스트 (원래 실패했던 것)
                logger.info("=== 잔고 조회 API 테스트 ===")
                balance_url = f"{config.kis.URL_BASE}/uapi/domestic-stock/v1/trading/inquire-balance"

                # 계좌번호 파싱
                account_number = config.api.KIS_ACCOUNT_NUMBER
                if '-' in account_number:
                    cano, acnt_prdt_cd = account_number.split('-', 1)
                else:
                    logger.error("계좌번호 형식 오류")
                    return

                params = {
                    'CANO': cano,
                    'ACNT_PRDT_CD': acnt_prdt_cd,
                    'AFHR_FLPR_YN': 'N',
                    'OFL_YN': '',
                    'INQR_DVSN': '02',
                    'UNPR_DVSN': '01',
                    'FUND_STTL_ICLD_YN': 'N',
                    'FNCG_AMT_AUTO_RDPT_YN': 'N',
                    'PRCS_DVSN': '01',
                    'CTX_AREA_FK100': '',
                    'CTX_AREA_NK100': ''
                }

                headers['tr_id'] = 'TTTC8434R'
                headers['custtype'] = 'P'

                async with session.get(balance_url, params=params, headers=headers, timeout=timeout) as response:
                    response_text = await response.text()
                    logger.info(f"잔고 조회 응답 상태: {response.status}")
                    logger.info(f"잔고 조회 응답: {response_text[:300]}")

                    if response.status == 200:
                        logger.info("✅ 토큰 활성화 지연 후 성공!")
                        return True
                    else:
                        logger.error("❌ 여전히 실패")
                        return False

        except Exception as e:
            logger.error(f"❌ 테스트 중 오류: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_token_with_delay())