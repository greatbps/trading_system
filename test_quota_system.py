#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Quota System Test
=====================

새로운 쿼터 관리 시스템 테스트
"""

import asyncio
import json
from config import Config
from analyzers.api_quota_manager import APIQuotaManager, get_quota_manager
from analyzers.gpt_analyzer import GPTAnalyzer
from analyzers.gemini_analyzer import GeminiAnalyzer
from utils.logger import get_logger

async def test_quota_manager():
    """쿼터 매니저 테스트"""
    logger = get_logger("QuotaTest")

    # 설정 로드
    config = Config()

    # 쿼터 매니저 테스트
    logger.info("🧪 API 쿼터 매니저 테스트 시작...")

    quota_manager = get_quota_manager(config)

    # 1. OpenAI 쿼터 상태 확인
    logger.info("1️⃣ OpenAI 쿼터 상태 확인...")
    quota_info = await quota_manager.check_quota_status(force_check=True)

    logger.info(f"📊 쿼터 상태: {quota_info.status.value}")
    if quota_info.error_message:
        logger.error(f"❌ 에러 메시지: {quota_info.error_message}")

    # 2. 백업 사용 여부 확인
    logger.info("2️⃣ 백업 분석기 사용 여부 확인...")
    should_fallback = await quota_manager.should_use_fallback("openai")
    logger.info(f"🔄 백업 사용 권장: {should_fallback}")

    # 3. 쿼터 요약 정보
    logger.info("3️⃣ 쿼터 요약 정보...")
    summary = quota_manager.get_quota_summary()
    logger.info(f"📈 쿼터 요약:\n{json.dumps(summary, indent=2, ensure_ascii=False)}")

    return quota_info, should_fallback

async def test_analyzer_fallback():
    """분석기 백업 시스템 테스트"""
    logger = get_logger("AnalyzerTest")

    config = Config()

    logger.info("🔬 분석기 백업 시스템 테스트...")

    # GPT Analyzer 테스트
    logger.info("1️⃣ GPT Analyzer 테스트...")
    gpt_analyzer = GPTAnalyzer(config)

    try:
        # 간단한 테스트 분석 시도
        test_result = await gpt_analyzer.analyze_comprehensive(
            symbol="005930",
            name="삼성전자",
            stock_data={"current_price": 70000, "volume": 1000000, "market_cap": 400000000000000},
            strategy="test"
        )
        logger.info("✅ GPT 분석 성공")
        logger.debug(f"결과 미리보기: {test_result[:200]}...")

    except Exception as e:
        logger.warning(f"⚠️ GPT 분석 실패: {e}")

        # Gemini 백업으로 전환
        logger.info("🔄 Gemini 백업 분석기로 전환...")
        gemini_analyzer = GeminiAnalyzer(config)

        try:
            backup_result = await gemini_analyzer.analyze_comprehensive(
                symbol="005930",
                name="삼성전자",
                stock_data={"current_price": 70000, "volume": 1000000, "market_cap": 400000000000000},
                strategy="test"
            )
            logger.info("✅ Gemini 백업 분석 성공")
            logger.debug(f"결과 미리보기: {backup_result[:200]}...")

        except Exception as backup_e:
            logger.error(f"❌ Gemini 백업도 실패: {backup_e}")

async def main():
    """메인 테스트 함수"""
    logger = get_logger("MainTest")

    logger.info("🚀 API 쿼터 관리 시스템 전체 테스트 시작")

    try:
        # 1. 쿼터 매니저 테스트
        quota_info, should_fallback = await test_quota_manager()

        # 2. 분석기 백업 시스템 테스트
        await test_analyzer_fallback()

        logger.info("✅ 모든 테스트 완료")

        # 3. 권장사항 출력
        logger.info("\n📋 권장사항:")
        if should_fallback:
            logger.warning("⚠️ OpenAI API 사용 불가 - Gemini 백업 사용 권장")
            logger.info("💡 .env 파일에서 PRIMARY_ANALYZER=gemini로 설정 확인")
        else:
            logger.info("✅ OpenAI API 사용 가능 - 정상 운영 가능")

    except Exception as e:
        logger.error(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())