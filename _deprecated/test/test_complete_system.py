#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_complete_system.py

전체 시스템 통합 테스트 및 검증
"""

import asyncio
import unittest
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import tempfile
import shutil

# 테스트 대상 모듈들
from core.dynamic_settings_manager import DynamicSettingsManager, TradingSettings, BalanceHistory
from backtesting.enhanced_visualizer import EnhancedVisualizer
from backtesting.backtesting_engine import BacktestResult, PerformanceMetrics
from integration_demo import TradingSystemIntegration

class TestDynamicSettingsManager(unittest.TestCase):
    """동적 설정 관리자 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DynamicSettingsManager(data_dir=self.temp_dir)

    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)

    def test_initial_settings(self):
        """초기 설정 테스트"""
        settings = asyncio.run(self.manager.get_current_settings())

        self.assertIsInstance(settings, TradingSettings)
        self.assertGreater(settings.position_size_ratio, 0)
        self.assertGreater(settings.max_positions, 0)
        self.assertGreater(settings.stop_loss_pct, 0)
        self.assertGreater(settings.take_profit_pct, 0)

    def test_balance_based_adjustment(self):
        """잔고 기반 설정 조정 테스트"""
        # 낮은 잔고 테스트
        low_balance_settings = self.manager._get_settings_by_balance(3_000_000)
        self.assertEqual(low_balance_settings.risk_level, "low")
        self.assertLessEqual(low_balance_settings.position_size_ratio, 0.1)

        # 높은 잔고 테스트
        high_balance_settings = self.manager._get_settings_by_balance(30_000_000)
        self.assertEqual(high_balance_settings.risk_level, "high")
        self.assertGreater(high_balance_settings.position_size_ratio, 0.1)

class TestEnhancedVisualizer(unittest.TestCase):
    """향상된 시각화 도구 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.visualizer = EnhancedVisualizer(output_dir=self.temp_dir)

    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)

    def test_monthly_returns_calculation(self):
        """월별 수익률 계산 테스트"""
        # 테스트용 백테스트 결과 생성
        result = self._create_test_backtest_result()
        monthly_returns = self.visualizer._calculate_monthly_returns(result)

        self.assertIsInstance(monthly_returns, dict)

    def _create_test_backtest_result(self) -> BacktestResult:
        """테스트용 백테스트 결과 생성"""
        # 30일간의 데이터
        equity_curve = []
        initial_value = 10_000_000

        for i in range(30):
            date = datetime.now() - timedelta(days=30-i)
            value = initial_value * (1 + i * 0.01)  # 1%씩 증가

            equity_curve.append({
                "date": date,
                "portfolio_value": value
            })

        metrics = PerformanceMetrics(
            total_return=30.0,
            annual_return=365.0,
            volatility=15.0,
            sharpe_ratio=2.0,
            max_drawdown=5.0,
            win_rate=70.0,
            profit_factor=1.5,
            total_trades=10
        )

        return BacktestResult(
            strategy_name="테스트 전략",
            initial_capital=initial_value,
            final_capital=initial_value * 1.3,
            total_return_pct=30.0,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=[]
        )

async def run_performance_benchmark():
    """성능 벤치마크 실행"""
    print("🚀 성능 벤치마크 시작...")

    import time
    start_time = time.time()

    # 통합 시스템 테스트
    integration = TradingSystemIntegration()

    # 여러 시나리오 실행
    scenarios = [
        {"balance": 5_000_000, "cash": 1_500_000, "stocks": 3_500_000},
        {"balance": 10_000_000, "cash": 3_000_000, "stocks": 7_000_000},
        {"balance": 20_000_000, "cash": 6_000_000, "stocks": 14_000_000},
    ]

    for scenario in scenarios:
        await integration.settings_manager.update_balance_and_adjust_settings(
            current_balance=scenario["balance"],
            cash_balance=scenario["cash"],
            stock_value=scenario["stocks"]
        )

    # 시각화 테스트
    results = []
    for i in range(5):
        result = await integration._create_demo_backtest_result(f"전략 {i+1}")
        results.append(result)

    # 결과 출력
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"⏱️  총 실행 시간: {execution_time:.2f}초")
    print(f"📊 처리된 시나리오: {len(scenarios)}개")
    print(f"📈 생성된 백테스트 결과: {len(results)}개")

    if execution_time < 10.0:
        print("✅ 실행 시간 기준 통과")
    else:
        print("⚠️ 실행 시간이 기준을 초과했습니다")

def run_all_tests():
    """모든 테스트 실행"""
    print("🧪 전체 시스템 테스트 시작...\n")

    test_classes = [
        TestDynamicSettingsManager,
        TestEnhancedVisualizer,
    ]

    total_tests = 0
    total_failures = 0

    for test_class in test_classes:
        print(f"📋 {test_class.__name__} 테스트 실행 중...")

        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        result = unittest.TextTestRunner(verbosity=1).run(suite)

        total_tests += result.testsRun
        total_failures += len(result.failures) + len(result.errors)

        if result.wasSuccessful():
            print(f"✅ {test_class.__name__} 모든 테스트 통과\n")
        else:
            print(f"❌ {test_class.__name__} 일부 테스트 실패\n")

    print(f"📊 테스트 결과 요약:")
    print(f"   총 테스트: {total_tests}개")
    print(f"   실패: {total_failures}개")

    if total_tests > 0:
        success_rate = ((total_tests - total_failures) / total_tests * 100)
        print(f"   성공률: {success_rate:.1f}%")

        if total_failures == 0:
            print("🎉 모든 테스트가 성공적으로 통과했습니다!")
        else:
            print("⚠️ 일부 테스트가 실패했습니다.")

async def main():
    """메인 함수"""
    print("🔍 AI Trading System - 전체 시스템 검증\n")

    try:
        # 1. 단위 테스트 실행
        run_all_tests()

        print("\n" + "="*50 + "\n")

        # 2. 성능 벤치마크 실행
        await run_performance_benchmark()

        print("\n" + "="*50 + "\n")
        print("🏁 전체 시스템 검증 완료!")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 테스트 실행
    asyncio.run(main())