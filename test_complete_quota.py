#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Quota Management System Test
====================================

전체 쿼터 관리 시스템 테스트
"""

import asyncio
import sys
from config import Config
from analyzers.api_quota_manager import get_quota_manager
from analyzers.quota_monitoring import get_quota_monitor
from utils.logger import get_logger

async def test_complete_system():
    """전체 시스템 테스트"""
    logger = get_logger("CompleteTest")

    print("=" * 60)
    print("Complete Quota Management System Test")
    print("=" * 60)

    # 설정 로드
    config = Config()

    # 1. 쿼터 매니저 테스트
    print("\n1. API Quota Manager Test...")
    quota_manager = get_quota_manager(config)

    if quota_manager:
        quota_info = await quota_manager.check_quota_status(force_check=True)
        print(f"   Status: {quota_info.status.value}")
        print(f"   Should use fallback: {await quota_manager.should_use_fallback()}")

        if quota_info.error_message:
            print(f"   Error: {quota_info.error_message[:100]}...")
    else:
        print("   ERROR: Quota manager not initialized")

    # 2. 쿼터 모니터 테스트
    print("\n2. Quota Monitor Test...")
    quota_monitor = get_quota_monitor(config)

    if quota_monitor:
        # 건강 상태 체크
        health = await quota_monitor.health_check()
        print(f"   Overall Status: {health['overall_status']}")
        print(f"   APIs: {list(health['apis'].keys())}")
        print(f"   Active Alerts: {health['alerts']['active_count']}")

        # 사용량 요약
        usage = quota_monitor.get_usage_summary(days=1)
        print(f"   Total Checks (24h): {usage['total_checks']}")

        # 예측
        prediction = await quota_monitor.predict_quota_exhaustion("openai")
        if prediction:
            print(f"   Exhaustion Prediction: {prediction.strftime('%Y-%m-%d %H:%M')}")
        else:
            print("   Exhaustion Prediction: Not available")

    else:
        print("   ERROR: Quota monitor not initialized")

    # 3. GPT 분석기 테스트
    print("\n3. GPT Analyzer with Quota Check...")
    try:
        from analyzers.gpt_analyzer import GPTAnalyzer

        gpt_analyzer = GPTAnalyzer(config)
        print(f"   API Available: {gpt_analyzer.api_available}")

        if gpt_analyzer.api_available:
            try:
                result = await gpt_analyzer.analyze_comprehensive(
                    symbol="TEST",
                    name="테스트",
                    stock_data={"current_price": 1000, "volume": 100, "market_cap": 1000000},
                    strategy="test"
                )
                print("   GPT Analysis: SUCCESS")
                print(f"   Result length: {len(result)} characters")

            except Exception as e:
                print(f"   GPT Analysis: FAILED - {str(e)[:100]}...")
                print("   This is expected if quota is exceeded")
        else:
            print("   GPT API not available")

    except Exception as e:
        print(f"   ERROR: {e}")

    # 4. 백업 시스템 테스트
    print("\n4. Fallback System Test...")
    try:
        from analyzers.gemini_analyzer import GeminiAnalyzer

        gemini_analyzer = GeminiAnalyzer(config)
        print(f"   Gemini Available: {gemini_analyzer.api_available}")

        if gemini_analyzer.api_available:
            try:
                result = await gemini_analyzer.analyze_comprehensive(
                    symbol="TEST",
                    name="테스트",
                    stock_data={"current_price": 1000, "volume": 100, "market_cap": 1000000},
                    strategy="test"
                )
                print("   Gemini Analysis: SUCCESS")
                print(f"   Result length: {len(result)} characters")

            except Exception as e:
                print(f"   Gemini Analysis: FAILED - {str(e)[:100]}...")
        else:
            print("   Gemini API not available")

    except Exception as e:
        print(f"   ERROR: {e}")

    # 5. 권장사항
    print("\n5. Recommendations...")

    if quota_manager:
        should_fallback = await quota_manager.should_use_fallback("openai")

        if should_fallback:
            print("   - OpenAI quota exceeded - Use Gemini as primary")
            print("   - Check OpenAI billing at: https://platform.openai.com/account/billing")
            print("   - Consider upgrading plan or adding credits")
            print("   - PRIMARY_ANALYZER=gemini in .env file")
        else:
            print("   - OpenAI API available for use")
            print("   - Monitor usage to prevent quota exhaustion")
            print("   - Set up alerts for usage thresholds")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

async def simple_quota_check():
    """간단한 쿼터 상태 확인"""
    config = Config()
    quota_manager = get_quota_manager(config)

    print("Quick Quota Status Check:")
    print("-" * 30)

    if quota_manager:
        quota_info = await quota_manager.check_quota_status(force_check=True)
        print(f"OpenAI Status: {quota_info.status.value}")

        should_fallback = await quota_manager.should_use_fallback("openai")
        print(f"Use Fallback: {should_fallback}")

        if quota_info.error_message:
            print(f"Error: {quota_info.error_message[:200]}...")
    else:
        print("ERROR: Quota manager not available")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(simple_quota_check())
    else:
        asyncio.run(test_complete_system())