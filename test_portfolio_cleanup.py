#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_portfolio_cleanup.py

포트폴리오 정리 전략 테스트
"""

import asyncio
import json
from datetime import datetime
from strategies.portfolio_cleanup_strategy import PortfolioCleanupStrategy
from core.portfolio_manager import PortfolioManager
from utils.logger import get_logger

async def test_portfolio_cleanup_strategy():
    """포트폴리오 정리 전략 테스트"""
    logger = get_logger("TestPortfolioCleanup")

    print("=" * 60)
    print("포트폴리오 정리 전략 테스트")
    print("=" * 60)

    # 전략 인스턴스 생성
    strategy = PortfolioCleanupStrategy()

    # 테스트 데이터 생성 (실제 KIS API 형식)
    test_holdings = [
        # 하드코딩된 종목 (제외 대상)
        {
            'pdno': '005930',      # 삼성전자
            'prdt_name': '삼성전자',
            'hldg_qty': '100',
            'pchs_avg_pric': '70000',
            'prpr': '72000'        # +2.9% 수익
        },

        # 익절 대상 종목들
        {
            'pdno': '123456',
            'prdt_name': '수익종목A',
            'hldg_qty': '50',
            'pchs_avg_pric': '10000',
            'prpr': '10600'        # +6% 수익 (익절 대상)
        },
        {
            'pdno': '234567',
            'prdt_name': '수익종목B',
            'hldg_qty': '30',
            'pchs_avg_pric': '20000',
            'prpr': '20800'        # +4% 수익 (익절 대상)
        },

        # 손절 대상 종목들
        {
            'pdno': '345678',
            'prdt_name': '손실종목A',
            'hldg_qty': '80',
            'pchs_avg_pric': '15000',
            'prpr': '14400'        # -4% 손실 (손절 대상)
        },
        {
            'pdno': '456789',
            'prdt_name': '손실종목B',
            'hldg_qty': '60',
            'pchs_avg_pric': '25000',
            'prpr': '24000'        # -4% 손실 (손절 대상)
        },

        # 보유 유지 종목
        {
            'pdno': '567890',
            'prdt_name': '보유종목A',
            'hldg_qty': '40',
            'pchs_avg_pric': '30000',
            'prpr': '30300'        # +1% (보유 유지)
        }
    ]

    print(f"테스트 보유 종목: {len(test_holdings)}개")
    print()

    # 1. 포트폴리오 분석
    print("1. 포트폴리오 분석 중...")
    signals = await strategy.analyze_portfolio(test_holdings)

    print(f"생성된 신호: {len(signals)}개")
    print()

    # 2. 신호별 분석
    print("2. 생성된 신호 분석:")
    print("-" * 50)

    for i, signal in enumerate(signals, 1):
        print(f"{i}. {signal.symbol} ({strategy.holdings[signal.symbol].name})")
        print(f"   액션: {signal.action}")
        print(f"   우선순위: {signal.priority}")
        print(f"   매도 비율: {signal.quantity_ratio * 100:.1f}%")
        print(f"   수익률: {signal.profit_rate:.1f}%")
        print(f"   사유: {signal.reason}")
        print()

    # 3. 포트폴리오 요약
    print("3. 포트폴리오 요약:")
    print("-" * 50)

    summary = strategy.get_portfolio_summary()
    print(f"전체 보유 종목: {summary['total_holdings']}개")
    print(f"활성 종목 (하드코딩 제외): {summary['active_holdings']}개")
    print(f"하드코딩 종목: {summary['hardcoded_holdings']}개")
    print(f"익절 후보: {summary['profit_candidates']}개")
    print(f"손절 후보: {summary['loss_candidates']}개")
    print(f"총 손익: {summary['total_profit_loss']:,.0f}원")
    print(f"정리 필요: {'예' if summary['cleanup_needed'] else '아니오'}")
    print()

    if summary['hardcoded_list']:
        print("하드코딩 제외 종목:")
        for stock in summary['hardcoded_list']:
            print(f"  - {stock}")
        print()

    # 4. 정리 계획 생성
    print("4. 정리 계획 생성:")
    print("-" * 50)

    cleanup_plan = await strategy.generate_cleanup_plan(test_holdings)

    # 실행 단계별 정리
    execution_plan = cleanup_plan['execution_plan']

    if execution_plan['step1_profit_taking']:
        print("1단계: 익절 실행")
        for signal in execution_plan['step1_profit_taking']:
            holding = strategy.holdings[signal.symbol]
            print(f"  - {holding.name}: {signal.quantity_ratio*100:.0f}% 매도 (+{signal.profit_rate:.1f}%)")
        print()

    if execution_plan['step2_loss_cutting']:
        print("2단계: 손절 실행")
        for signal in execution_plan['step2_loss_cutting']:
            holding = strategy.holdings[signal.symbol]
            print(f"  - {holding.name}: {signal.quantity_ratio*100:.0f}% 매도 ({signal.profit_rate:.1f}%)")
        print()

    if execution_plan['step3_position_mgmt']:
        print("3단계: 포지션 관리")
        for signal in execution_plan['step3_position_mgmt']:
            holding = strategy.holdings[signal.symbol]
            print(f"  - {holding.name}: {signal.quantity_ratio*100:.0f}% 매도 (포지션 정리)")
        print()

    # 5. JSON 형태로 결과 저장
    result_file = f"data/portfolio_cleanup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(cleanup_plan, f, ensure_ascii=False, indent=2, default=str)
        print(f"테스트 결과 저장: {result_file}")
    except Exception as e:
        logger.error(f"결과 파일 저장 실패: {e}")

    print("=" * 60)
    print("포트폴리오 정리 전략 테스트 완료")
    print("=" * 60)

    return cleanup_plan

async def test_portfolio_manager():
    """포트폴리오 매니저 통합 테스트"""
    print("\n" + "=" * 60)
    print("포트폴리오 매니저 통합 테스트")
    print("=" * 60)

    # 모의 설정 (실거래 비활성화)
    class MockConfig:
        TRADING_ENABLED = False

    config = MockConfig()
    manager = PortfolioManager(config=config)

    # 포트폴리오 상태 조회 (실제 데이터 없이 테스트)
    status = await manager.get_portfolio_status()
    print(f"포트폴리오 상태: {status}")

    print("=" * 60)
    print("포트폴리오 매니저 테스트 완료")
    print("=" * 60)

async def main():
    """메인 테스트 실행"""
    try:
        # 1. 정리 전략 테스트
        await test_portfolio_cleanup_strategy()

        # 2. 포트폴리오 매니저 테스트
        await test_portfolio_manager()

        print("\n✅ 모든 테스트 완료!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())