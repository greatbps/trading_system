#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/test_performance_optimization.py

매매 분석 성능 최적화 테스트 스크립트
"""

import asyncio
import time
from typing import Dict, Any

class PerformanceTester:
    """성능 테스트 클래스"""

    def __init__(self, db_auto_trader):
        self.trader = db_auto_trader

    async def run_performance_test(self) -> Dict[str, Any]:
        """성능 테스트 실행"""
        print("🔥 매매 분석 성능 최적화 테스트 시작")
        print("=" * 60)

        # 1. 현재 성능 측정
        print("\n📊 1단계: 현재 성능 측정")
        initial_metrics = await self.measure_current_performance()
        self.print_performance_metrics(initial_metrics, "현재 성능")

        # 2. 최적 설정 분석
        print("\n🎯 2단계: 최적 설정 분석")
        optimal_settings = self.trader.get_optimal_monitoring_count()
        self.print_optimal_settings(optimal_settings)

        # 3. 성능 최적화 적용
        print("\n⚡ 3단계: 성능 최적화 적용")
        optimization_result = await self.trader.optimize_monitoring_performance()
        self.print_optimization_result(optimization_result)

        # 4. 종합 리포트 생성
        print("\n📋 4단계: 종합 성능 리포트")
        performance_report = self.trader.get_performance_report()
        self.print_performance_report(performance_report)

        # 5. 권장사항 요약
        print("\n💡 5단계: 최종 권장사항")
        self.print_recommendations(performance_report)

        return {
            'initial_metrics': initial_metrics,
            'optimal_settings': optimal_settings,
            'optimization_result': optimization_result,
            'performance_report': performance_report
        }

    async def measure_current_performance(self) -> Dict[str, Any]:
        """현재 성능 측정"""
        start_time = time.time()

        # DB에서 활성 모니터링 종목 수 조회
        with self.trader.db_manager.get_session() as session:
            from database.models import MonitoringStock, MonitoringStatus
            active_count = session.query(MonitoringStock).filter(
                MonitoringStock.status == MonitoringStatus.ACTIVE.value
            ).count()

        # 기본 성능 메트릭
        metrics = self.trader.calculate_performance_metrics()

        elapsed_time = time.time() - start_time

        return {
            'active_stocks': active_count,
            'measurement_time': elapsed_time,
            'metrics': metrics
        }

    def print_performance_metrics(self, metrics: Dict, title: str):
        """성능 메트릭 출력"""
        print(f"\n📈 {title}:")
        if 'metrics' in metrics:
            m = metrics['metrics']
            print(f"   • 활성 종목 수: {metrics['active_stocks']}개")
            print(f"   • 평균 분석 시간: {m.get('avg_analysis_time', 0):.2f}초")
            print(f"   • 전체 분석 시간: {m.get('total_analysis_time', 0):.2f}초")
            print(f"   • 현재 갱신 주기: {m.get('current_interval', 30)}초")
            print(f"   • 병렬 처리: {'활성화' if m.get('parallel_enabled', False) else '비활성화'}")
            print(f"   • 병렬 처리 권장: {'Yes' if m.get('parallel_recommended', False) else 'No'}")
        else:
            print("   성능 데이터 부족")

    def print_optimal_settings(self, settings: Dict):
        """최적 설정 출력"""
        print(f"   • 현재 종목 수: {settings.get('current_count', 0)}개")
        print(f"   • 권장 종목 수: {settings.get('recommended_count', 20)}개")
        print(f"   • 최대 안전 종목 수: {settings.get('max_safe_count', 24)}개")
        print(f"   • 성능 상태: {settings.get('performance_status', '알 수 없음')}")

        if 'optimization_suggestions' in settings and settings['optimization_suggestions']:
            print("   📝 최적화 제안:")
            for suggestion in settings['optimization_suggestions']:
                print(f"      - {suggestion}")

    def print_optimization_result(self, result: Dict):
        """최적화 결과 출력"""
        if result.get('success'):
            applied = result.get('optimizations_applied', [])
            if applied:
                print("   ✅ 적용된 최적화:")
                for optimization in applied:
                    print(f"      - {optimization}")
            else:
                print("   ✅ 이미 최적화된 상태입니다")
        else:
            print(f"   ❌ 최적화 실패: {result.get('error', '알 수 없는 오류')}")

    def print_performance_report(self, report: Dict):
        """성능 리포트 출력"""
        if 'error' not in report:
            print(f"   🏆 성능 등급: {report.get('performance_grade', 'N/A')}")

            system_health = report.get('system_health', {})
            print(f"   • 병렬 처리: {'활성화' if system_health.get('parallel_processing', False) else '비활성화'}")
            print(f"   • 동시 분석 수: {system_health.get('max_concurrent', 8)}개")
            print(f"   • 갱신 주기: {system_health.get('monitoring_interval', 30)}초")

            memory = report.get('memory_usage', {})
            print(f"   • 메모리 사용량: {memory.get('estimated_memory_kb', 0):.2f}KB")
        else:
            print(f"   ❌ 리포트 생성 실패: {report.get('error', '알 수 없는 오류')}")

    def print_recommendations(self, report: Dict):
        """권장사항 출력"""
        recommendations = report.get('recommendations', [])
        if recommendations:
            print("   📌 권장사항:")
            for i, rec in enumerate(recommendations, 1):
                print(f"      {i}. {rec}")
        else:
            print("   ✅ 추가 최적화 권장사항이 없습니다")

        # 종목 수에 따른 일반적인 가이드라인
        print("\n📋 일반적인 가이드라인:")
        print("   • 10개 이하: 순차 처리 권장")
        print("   • 11-20개: 병렬 처리 고려")
        print("   • 21개 이상: 병렬 처리 필수")
        print("   • 30개 이상: 감시 종목 수 조정 검토")


async def main():
    """메인 함수"""
    print("⚠️  이 스크립트는 실제 매매 시스템과 연결된 상태에서 실행되어야 합니다.")
    print("실제 사용시에는 다음과 같이 호출하세요:")
    print()
    print("```python")
    print("from test_performance_optimization import PerformanceTester")
    print()
    print("# db_auto_trader가 초기화된 후")
    print("tester = PerformanceTester(db_auto_trader)")
    print("result = await tester.run_performance_test()")
    print("```")


if __name__ == "__main__":
    asyncio.run(main())