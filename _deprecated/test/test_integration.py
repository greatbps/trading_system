"""
종합 통합 테스트 시스템
Trading System Integration Tests

모든 구현된 시스템의 통합 동작을 검증합니다:
- 동적 설정 관리자
- 향상된 시각화
- 알림 시스템
- 웹 대시보드 API
- 성능 최적화
"""

import asyncio
import unittest
import tempfile
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# 테스트를 위한 임포트
try:
    from core.dynamic_settings_manager import DynamicSettingsManager, TradingSettings
    DYNAMIC_SETTINGS_AVAILABLE = True
except ImportError:
    DYNAMIC_SETTINGS_AVAILABLE = False
    print("WARNING: Dynamic Settings Manager not available")

try:
    from backtesting.enhanced_visualizer import EnhancedVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False
    print("WARNING: Enhanced Visualizer not available")

try:
    from monitoring.notification_system import NotificationSystem, NotificationLevel
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False
    print("WARNING: Notification System not available")

try:
    from api.web_dashboard_api import TradingSystemAPI
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("WARNING: Web Dashboard API not available")

try:
    from utils.performance_optimizer import PerformanceProfiler, MemoryOptimizer
    PERFORMANCE_AVAILABLE = True
except ImportError:
    PERFORMANCE_AVAILABLE = False
    print("WARNING: Performance Optimizer not available")


class IntegrationTestSuite:
    """종합 통합 테스트 스위트"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_results = {}
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger("integration_test")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def test_dynamic_settings_integration(self) -> Dict[str, Any]:
        """동적 설정 관리자 통합 테스트"""
        self.logger.info("🔧 Testing Dynamic Settings Manager Integration...")

        if not DYNAMIC_SETTINGS_AVAILABLE:
            return {"status": "skipped", "reason": "Module not available"}

        try:
            # 설정 관리자 초기화
            settings_file = os.path.join(self.temp_dir, "dynamic_settings.json")
            manager = DynamicSettingsManager(settings_file)

            # 시나리오 1: 잔고 증가에 따른 설정 조정
            initial_balance = 1000000  # 100만원
            increased_balance = 2000000  # 200만원

            # 초기 설정
            settings1, changes1 = await manager.update_balance_and_adjust_settings(
                current_balance=initial_balance,
                cash_balance=initial_balance * 0.5,
                stock_value=initial_balance * 0.5
            )

            # 잔고 증가 후 설정
            settings2, changes2 = await manager.update_balance_and_adjust_settings(
                current_balance=increased_balance,
                cash_balance=increased_balance * 0.3,
                stock_value=increased_balance * 0.7
            )

            # 검증
            assert settings1.max_stocks != settings2.max_stocks, "최대 종목수가 조정되지 않음"
            assert len(changes2) > 0, "변경사항이 기록되지 않음"

            # 시나리오 2: 성과 기반 조정
            performance_data = {
                "win_rate": 0.65,
                "avg_return": 0.08,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.15
            }

            settings3 = await manager.adjust_settings_by_performance(performance_data)

            result = {
                "status": "passed",
                "scenarios_tested": 2,
                "settings_adjustments": len(changes1) + len(changes2),
                "performance_adjustment": settings3 is not None
            }

            self.logger.info("✅ Dynamic Settings Integration: PASSED")
            return result

        except Exception as e:
            self.logger.error(f"❌ Dynamic Settings Integration: FAILED - {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def test_notification_system_integration(self) -> Dict[str, Any]:
        """알림 시스템 통합 테스트"""
        self.logger.info("📢 Testing Notification System Integration...")

        if not NOTIFICATION_AVAILABLE:
            return {"status": "skipped", "reason": "Module not available"}

        try:
            # 알림 시스템 초기화
            config_file = os.path.join(self.temp_dir, "notifications.json")
            notification_system = NotificationSystem(config_file)

            # 다양한 알림 레벨 테스트
            test_notifications = [
                ("balance_change", "잔고 변화", "잔고가 200만원으로 증가했습니다", NotificationLevel.INFO),
                ("settings_update", "설정 업데이트", "거래 설정이 자동 조정되었습니다", NotificationLevel.WARNING),
                ("system_error", "시스템 오류", "백테스팅 중 오류가 발생했습니다", NotificationLevel.ERROR),
                ("critical_alert", "긴급 알림", "시스템 리소스가 부족합니다", NotificationLevel.CRITICAL)
            ]

            successful_notifications = 0

            for event_type, title, message, level in test_notifications:
                try:
                    await notification_system.notify(event_type, title, message, level)
                    successful_notifications += 1
                except Exception as e:
                    self.logger.warning(f"알림 전송 실패: {event_type} - {str(e)}")

            # 알림 규칙 테스트
            rule_count = len(notification_system.rules)

            result = {
                "status": "passed",
                "notifications_sent": successful_notifications,
                "total_notifications": len(test_notifications),
                "rules_configured": rule_count
            }

            self.logger.info("✅ Notification System Integration: PASSED")
            return result

        except Exception as e:
            self.logger.error(f"❌ Notification System Integration: FAILED - {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def test_visualization_integration(self) -> Dict[str, Any]:
        """시각화 시스템 통합 테스트"""
        self.logger.info("📊 Testing Visualization System Integration...")

        if not VISUALIZER_AVAILABLE:
            return {"status": "skipped", "reason": "Module not available"}

        try:
            # 시각화 시스템 초기화
            visualizer = EnhancedVisualizer()

            # 테스트 데이터 생성
            mock_backtest_results = self._generate_mock_backtest_data()

            # 대시보드 생성 테스트
            dashboard_html = await visualizer.create_interactive_dashboard(
                mock_backtest_results,
                live_mode=False
            )

            # HTML 생성 검증
            assert isinstance(dashboard_html, str), "대시보드 HTML이 문자열이 아님"
            assert len(dashboard_html) > 1000, "대시보드 HTML이 너무 짧음"
            assert "Plotly" in dashboard_html, "Plotly 스크립트가 포함되지 않음"

            # 실시간 모니터링 테스트
            monitor_result = await visualizer.start_real_time_monitor()

            result = {
                "status": "passed",
                "dashboard_generated": len(dashboard_html) > 0,
                "backtest_results_processed": len(mock_backtest_results),
                "real_time_monitor": monitor_result is not None
            }

            self.logger.info("✅ Visualization Integration: PASSED")
            return result

        except Exception as e:
            self.logger.error(f"❌ Visualization Integration: FAILED - {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def test_api_integration(self) -> Dict[str, Any]:
        """API 시스템 통합 테스트"""
        self.logger.info("🌐 Testing API System Integration...")

        if not API_AVAILABLE:
            return {"status": "skipped", "reason": "Module not available"}

        try:
            # API 시스템 초기화 (실제 서버 시작하지 않고 구조만 테스트)
            api = TradingSystemAPI()

            # FastAPI 앱 구조 검증
            routes = api.app.routes
            route_paths = [route.path for route in routes if hasattr(route, 'path')]

            expected_routes = [
                "/api/balance/update",
                "/api/settings/current",
                "/api/notifications/recent",
                "/api/dashboard/data"
            ]

            routes_found = sum(1 for route in expected_routes if any(route in path for path in route_paths))

            result = {
                "status": "passed",
                "total_routes": len(routes),
                "expected_routes_found": routes_found,
                "api_initialized": api.app is not None
            }

            self.logger.info("✅ API Integration: PASSED")
            return result

        except Exception as e:
            self.logger.error(f"❌ API Integration: FAILED - {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def test_performance_optimization_integration(self) -> Dict[str, Any]:
        """성능 최적화 시스템 통합 테스트"""
        self.logger.info("⚡ Testing Performance Optimization Integration...")

        if not PERFORMANCE_AVAILABLE:
            return {"status": "skipped", "reason": "Module not available"}

        try:
            # 성능 프로파일러 테스트
            profiler = PerformanceProfiler()

            # 메모리 최적화 테스트
            memory_optimizer = MemoryOptimizer()

            # 테스트 작업 실행
            async def test_task():
                return sum(range(10000))

            # 프로파일링된 작업 실행
            with profiler.profile_context("test_task"):
                result = await test_task()

            # 메트릭 수집
            metrics = profiler.get_performance_metrics()
            memory_stats = memory_optimizer.get_memory_stats()

            # 검증
            assert "test_task" in metrics, "성능 메트릭이 수집되지 않음"
            assert memory_stats["total_memory_mb"] > 0, "메모리 통계가 수집되지 않음"

            result = {
                "status": "passed",
                "metrics_collected": len(metrics),
                "memory_tracked": memory_stats["total_memory_mb"] > 0,
                "test_task_result": result == sum(range(10000))
            }

            self.logger.info("✅ Performance Optimization Integration: PASSED")
            return result

        except Exception as e:
            self.logger.error(f"❌ Performance Optimization Integration: FAILED - {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _generate_mock_backtest_data(self):
        """테스트용 백테스팅 데이터 생성"""
        from types import SimpleNamespace

        results = []
        base_date = datetime.now() - timedelta(days=30)

        for i in range(10):
            result = SimpleNamespace()
            result.strategy_name = f"Strategy_{i+1}"
            result.start_date = base_date + timedelta(days=i*3)
            result.end_date = base_date + timedelta(days=(i+1)*3)
            result.total_return = 0.05 + (i * 0.02)
            result.sharpe_ratio = 1.0 + (i * 0.1)
            result.max_drawdown = 0.1 + (i * 0.01)
            result.win_rate = 0.6 + (i * 0.02)
            result.trades = []
            results.append(result)

        return results

    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 통합 테스트 실행"""
        self.logger.info("🚀 Starting Comprehensive Integration Tests...")

        test_methods = [
            ("dynamic_settings", self.test_dynamic_settings_integration),
            ("notification_system", self.test_notification_system_integration),
            ("visualization", self.test_visualization_integration),
            ("api", self.test_api_integration),
            ("performance", self.test_performance_optimization_integration)
        ]

        all_results = {}
        passed_tests = 0
        total_tests = len(test_methods)

        for test_name, test_method in test_methods:
            try:
                result = await test_method()
                all_results[test_name] = result

                if result.get("status") == "passed":
                    passed_tests += 1

            except Exception as e:
                all_results[test_name] = {"status": "error", "error": str(e)}
                self.logger.error(f"테스트 {test_name} 실행 중 오류: {str(e)}")

        # 전체 결과 요약
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "detailed_results": all_results,
            "test_timestamp": datetime.now().isoformat()
        }

        self.logger.info(f"🏁 Integration Tests Completed: {passed_tests}/{total_tests} passed ({summary['success_rate']:.1f}%)")

        return summary

    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """테스트 결과 보고서 생성"""
        report = f"""
# 통합 테스트 결과 보고서
# Integration Test Results Report

## 테스트 개요 (Test Overview)
- **실행 시간**: {results['test_timestamp']}
- **전체 테스트**: {results['total_tests']}개
- **성공**: {results['passed_tests']}개
- **실패**: {results['failed_tests']}개
- **성공률**: {results['success_rate']:.1f}%

## 상세 결과 (Detailed Results)

"""

        for test_name, result in results['detailed_results'].items():
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "error": "💥"
            }.get(result['status'], "❓")

            report += f"### {status_emoji} {test_name.replace('_', ' ').title()}\n"
            report += f"- **상태**: {result['status']}\n"

            if result['status'] == 'passed':
                for key, value in result.items():
                    if key != 'status':
                        report += f"- **{key}**: {value}\n"
            elif result['status'] in ['failed', 'error']:
                if 'error' in result:
                    report += f"- **오류**: {result['error']}\n"
            elif result['status'] == 'skipped':
                if 'reason' in result:
                    report += f"- **사유**: {result['reason']}\n"

            report += "\n"

        report += f"""
## 권장사항 (Recommendations)

{"### ✅ 모든 시스템이 정상적으로 통합되었습니다!" if results['success_rate'] == 100 else "### ⚠️ 일부 시스템에서 문제가 발견되었습니다."}

"""

        if results['success_rate'] < 100:
            report += """
**해결 방안**:
1. 실패한 테스트의 오류 메시지를 확인하세요
2. 필요한 의존성이 설치되어 있는지 확인하세요
3. 설정 파일이 올바르게 구성되어 있는지 확인하세요
4. 로그 파일에서 추가 정보를 찾아보세요

"""

        return report


async def main():
    """메인 통합 테스트 실행"""
    test_suite = IntegrationTestSuite()

    try:
        # 모든 테스트 실행
        results = await test_suite.run_all_tests()

        # 보고서 생성
        report = test_suite.generate_test_report(results)

        # 결과 출력
        print("\n" + "="*80)
        print(report)
        print("="*80)

        # 결과 파일 저장
        with open("integration_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        with open("integration_test_report.md", "w", encoding="utf-8") as f:
            f.write(report)

        return results

    except Exception as e:
        print(f"통합 테스트 실행 중 오류 발생: {str(e)}")
        return None


if __name__ == "__main__":
    asyncio.run(main())