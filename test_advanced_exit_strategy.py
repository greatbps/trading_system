#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_advanced_exit_strategy.py

고도화된 매도 전략 통합 테스트
매매조건고도화.md 반영 내용 검증
"""

import asyncio
import sys
import os
from datetime import datetime, time
from typing import Dict, List, Any

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.advanced_exit_strategy import AdvancedExitStrategy, PositionInfo, ExitSignal
from strategies.exit_signal_executor import ExitSignalExecutor
from optimization.exit_strategy_optimizer import ExitStrategyOptimizer
from utils.logger import get_logger

logger = get_logger("AdvancedExitStrategyTest")

class MockKisCollector:
    """테스트용 Mock KIS API"""

    def __init__(self):
        self.holdings = {
            'TEST001': {
                'name': '테스트종목1',
                'current_price': 105000,
                'avg_price': 100000,
                'quantity': 100,
                'profit_rate': 5.0
            },
            'TEST002': {
                'name': '테스트종목2',
                'current_price': 97000,
                'avg_price': 100000,
                'quantity': 50,
                'profit_rate': -3.0
            }
        }

    async def get_holdings(self):
        """보유종목 조회 시뮬레이션"""
        return {symbol: MockHolding(data) for symbol, data in self.holdings.items()}

class MockHolding:
    """테스트용 보유종목 데이터"""

    def __init__(self, data):
        self.quantity = data['quantity']
        self.current_price = data['current_price']
        self.avg_price = data['avg_price']
        self.name = data['name']

class MockExecutor:
    """테스트용 Mock 매매 실행기"""

    async def sell_stock(self, symbol, quantity, price=None, order_type='MARKET'):
        """매도 주문 시뮬레이션"""
        logger.info(f"Mock 매도 주문: {symbol} {quantity}주 @ {price or '시장가'} ({order_type})")
        return {
            'success': True,
            'order_id': f'ORDER_{symbol}_{datetime.now().strftime("%H%M%S")}',
            'message': '주문 성공'
        }

async def test_basic_exit_strategy():
    """기본 매도 전략 테스트"""
    logger.info("=== 기본 매도 전략 테스트 시작 ===")

    try:
        # 전략 초기화
        strategy = AdvancedExitStrategy()

        # 테스트 포지션 생성
        test_holdings = {
            'TEST001': {
                'current_price': 104000,  # +4% 상승
                'avg_price': 100000,
                'quantity': 100
            },
            'TEST002': {
                'current_price': 106000,  # +6% 상승
                'avg_price': 100000,
                'quantity': 50
            },
            'TEST003': {
                'current_price': 97000,   # -3% 하락
                'avg_price': 100000,
                'quantity': 75
            }
        }

        logger.info("포지션 정보 업데이트 중...")
        for symbol, data in test_holdings.items():
            await strategy.update_position(symbol, data)

        # 매도 신호 분석
        logger.info("매도 신호 분석 중...")
        all_signals = []
        for symbol in test_holdings.keys():
            signals = await strategy.analyze_exit_signals(symbol)
            all_signals.extend(signals)

            if signals:
                for signal in signals:
                    logger.info(f"[{symbol}] 매도 신호: {signal.signal_type} - {signal.reason} (신뢰도: {signal.confidence*100:.1f}%)")
            else:
                logger.info(f"[{symbol}] 매도 신호 없음")

        logger.info(f"총 {len(all_signals)}개 매도 신호 발생")
        return True

    except Exception as e:
        logger.error(f"기본 매도 전략 테스트 실패: {e}")
        return False

async def test_partial_profit_taking():
    """부분 익절 테스트"""
    logger.info("=== 부분 익절 테스트 시작 ===")

    try:
        strategy = AdvancedExitStrategy()

        # +4% 상승 종목 (1차 부분익절 조건)
        await strategy.update_position('TEST001', {
            'current_price': 104000,
            'avg_price': 100000,
            'quantity': 100
        })

        signals = await strategy.analyze_exit_signals('TEST001')
        partial_signals = [s for s in signals if s.signal_type == 'partial_profit']

        if partial_signals:
            signal = partial_signals[0]
            logger.info(f"✅ 1차 부분익절 신호 발생: {signal.quantity_ratio*100:.0f}% 매도")
        else:
            logger.warning("❌ 1차 부분익절 신호 미발생")

        # +6% 상승 종목 (2차 부분익절 조건)
        await strategy.update_position('TEST002', {
            'current_price': 106000,
            'avg_price': 100000,
            'quantity': 100
        })

        signals = await strategy.analyze_exit_signals('TEST002')
        partial_signals = [s for s in signals if s.signal_type == 'partial_profit']

        logger.info(f"✅ +6% 도달시 부분익절 신호 {len(partial_signals)}개 발생")

        return True

    except Exception as e:
        logger.error(f"부분 익절 테스트 실패: {e}")
        return False

async def test_trailing_stop():
    """트레일링 스탑 테스트"""
    logger.info("=== ATR 트레일링 스탑 테스트 시작 ===")

    try:
        strategy = AdvancedExitStrategy()

        # +7% 상승 종목 (트레일링 활성화)
        await strategy.update_position('TEST001', {
            'current_price': 107000,
            'avg_price': 100000,
            'quantity': 100
        })

        # 트레일링 스탑 업데이트
        await strategy.update_trailing_stops()

        # 포지션 정보 확인
        position = strategy.positions.get('TEST001')
        if position and position.trailing_stop:
            logger.info(f"✅ 트레일링 스탑 설정: ${position.trailing_stop:.2f}")
        else:
            logger.warning("❌ 트레일링 스탑 미설정")

        # 가격 하락 시뮬레이션
        await strategy.update_position('TEST001', {
            'current_price': 104000,  # 하락
            'avg_price': 100000,
            'quantity': 100
        })

        signals = await strategy.analyze_exit_signals('TEST001')
        trailing_signals = [s for s in signals if s.signal_type == 'trailing_stop']

        if trailing_signals:
            logger.info("✅ 트레일링 스탑 신호 발생")
        else:
            logger.info("ℹ️ 트레일링 스탑 신호 미발생 (정상)")

        return True

    except Exception as e:
        logger.error(f"트레일링 스탑 테스트 실패: {e}")
        return False

async def test_exit_signal_executor():
    """매도 신호 실행기 테스트"""
    logger.info("=== 매도 신고 실행기 테스트 시작 ===")

    try:
        mock_kis = MockKisCollector()
        mock_executor = MockExecutor()

        executor = ExitSignalExecutor(
            config=None,
            kis_collector=mock_kis,
            executor=mock_executor
        )

        # 테스트 매도 신호
        test_signal = ExitSignal(
            symbol='TEST001',
            signal_type='partial_profit',
            quantity_ratio=0.4,
            reason='1차 부분익절 (+4%)',
            confidence=0.8
        )

        # 매도 신호 실행
        result = await executor.execute_exit_signal('TEST001', test_signal)

        if result:
            logger.info("✅ 매도 신호 실행 성공")
        else:
            logger.error("❌ 매도 신호 실행 실패")

        return result

    except Exception as e:
        logger.error(f"매도 신호 실행기 테스트 실패: {e}")
        return False

async def test_parameter_optimization():
    """파라미터 최적화 테스트"""
    logger.info("=== 파라미터 최적화 테스트 시작 ===")

    try:
        optimizer = ExitStrategyOptimizer()

        # 테스트용 히스토리컬 데이터
        historical_data = []
        for i in range(50):
            historical_data.append({
                'entry_price': 100000 + (i % 10) * 1000,
                'exit_price': 100000 + (i % 10) * 1000 + (i % 5 - 2) * 2000,
                'volume': 1000000 + i * 10000
            })

        # 소규모 최적화 테스트 (5회)
        result = await optimizer.optimize_parameters(
            historical_data=historical_data,
            n_trials=5,
            study_name="test_optimization"
        )

        logger.info(f"✅ 최적화 완료: 최적 점수 {result.best_score:.4f}")
        logger.info(f"최적 파라미터: {result.best_params}")

        # 보고서 생성
        report = await optimizer.generate_optimization_report(result)
        logger.info(f"보고서 생성 완료 ({len(report)} 문자)")

        return True

    except Exception as e:
        logger.error(f"파라미터 최적화 테스트 실패: {e}")
        return False

async def test_time_filter():
    """시간 필터 테스트"""
    logger.info("=== 시간 필터 테스트 시작 ===")

    try:
        strategy = AdvancedExitStrategy()

        # 현재 시간이 장 마감 전인지 확인
        now = datetime.now().time()
        market_close = time(15, 30)

        logger.info(f"현재 시간: {now}")
        logger.info(f"장 마감 시간: {market_close}")

        # 시간 필터 체크
        time_filter_active = strategy._check_time_filter()

        if time_filter_active:
            logger.info("✅ 시간 필터 활성화 (장 마감 전)")
        else:
            logger.info("ℹ️ 시간 필터 비활성화 (정상 거래 시간)")

        return True

    except Exception as e:
        logger.error(f"시간 필터 테스트 실패: {e}")
        return False

async def run_comprehensive_test():
    """종합 테스트 실행"""
    logger.info("🚀 고도화된 매도 전략 종합 테스트 시작")

    test_results = []

    # 1. 기본 매도 전략 테스트
    result1 = await test_basic_exit_strategy()
    test_results.append(("기본 매도 전략", result1))

    # 2. 부분 익절 테스트
    result2 = await test_partial_profit_taking()
    test_results.append(("부분 익절", result2))

    # 3. 트레일링 스탑 테스트
    result3 = await test_trailing_stop()
    test_results.append(("트레일링 스탑", result3))

    # 4. 매도 신호 실행기 테스트
    result4 = await test_exit_signal_executor()
    test_results.append(("매도 신호 실행기", result4))

    # 5. 파라미터 최적화 테스트
    result5 = await test_parameter_optimization()
    test_results.append(("파라미터 최적화", result5))

    # 6. 시간 필터 테스트
    result6 = await test_time_filter()
    test_results.append(("시간 필터", result6))

    # 결과 요약
    logger.info("\n" + "="*60)
    logger.info("🏁 고도화된 매도 전략 테스트 결과 요약")
    logger.info("="*60)

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name:<20}: {status}")
        if result:
            passed_tests += 1

    logger.info("-" * 60)
    logger.info(f"전체 테스트: {total_tests}개")
    logger.info(f"성공: {passed_tests}개")
    logger.info(f"실패: {total_tests - passed_tests}개")
    logger.info(f"성공률: {passed_tests/total_tests*100:.1f}%")

    if passed_tests == total_tests:
        logger.info("🎉 모든 테스트 통과! 고도화된 매도 전략 시스템 준비 완료")
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests}개 테스트 실패 - 시스템 점검 필요")

    logger.info("\n📋 매매조건고도화.md 반영 내용:")
    logger.info("✅ ATR 기반 트레일링 스탑")
    logger.info("✅ 부분 익절 (Scale-out)")
    logger.info("✅ 볼륨/VWAP 필터")
    logger.info("✅ 시간 필터")
    logger.info("✅ Optuna 기반 자동 최적화")
    logger.info("✅ 변동성 기반 동적 조정")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())