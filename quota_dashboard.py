#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Quota Status Dashboard
==========================

실시간 API 쿼터 상태 모니터링 대시보드
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import time

from config import Config
from analyzers.quota_monitoring import QuotaMonitor, get_quota_monitor
from utils.logger import get_logger


class QuotaDashboard:
    """실시간 쿼터 상태 대시보드"""

    def __init__(self, config):
        self.config = config
        self.logger = get_logger("QuotaDashboard")
        self.monitor = get_quota_monitor(config)
        self.refresh_interval = 30  # 30초마다 갱신

    def _clear_screen(self):
        """화면 클리어"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _format_status_indicator(self, status: str) -> str:
        """상태 표시기 포맷"""
        indicators = {
            "available": "🟢 정상",
            "warning": "🟡 경고",
            "exceeded": "🔴 초과",
            "unknown": "⚪ 불명",
            "healthy": "💚 양호",
            "degraded": "🟠 저하",
            "error": "❌ 오류"
        }
        return indicators.get(status.lower(), f"❓ {status}")

    def _format_percentage(self, percentage: float) -> str:
        """퍼센트 포맷 (컬러 포함)"""
        if percentage is None:
            return "N/A"

        if percentage >= 90:
            return f"🔴 {percentage:.1f}%"
        elif percentage >= 75:
            return f"🟡 {percentage:.1f}%"
        else:
            return f"🟢 {percentage:.1f}%"

    def _format_time_ago(self, timestamp: datetime) -> str:
        """시간 경과 포맷"""
        if not timestamp:
            return "N/A"

        now = datetime.now()
        diff = now - timestamp

        if diff.total_seconds() < 60:
            return f"{int(diff.total_seconds())}초 전"
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() / 60)}분 전"
        elif diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() / 3600)}시간 전"
        else:
            return f"{int(diff.total_seconds() / 86400)}일 전"

    async def _get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 수집"""
        try:
            # 시스템 상태 체크
            health_status = await self.monitor.health_check()

            # 사용량 요약
            usage_summary = self.monitor.get_usage_summary(days=7)

            # 최근 알림
            recent_alerts = [
                a for a in self.monitor.alerts
                if a.timestamp > datetime.now() - timedelta(hours=24)
            ]

            # 쿼터 소진 예측
            exhaustion_prediction = await self.monitor.predict_quota_exhaustion("openai")

            return {
                "health": health_status,
                "usage": usage_summary,
                "alerts": recent_alerts,
                "exhaustion_prediction": exhaustion_prediction,
                "last_updated": datetime.now()
            }

        except Exception as e:
            self.logger.error(f"❌ 대시보드 데이터 수집 실패: {e}")
            return {
                "error": str(e),
                "last_updated": datetime.now()
            }

    def _render_dashboard(self, data: Dict[str, Any]):
        """대시보드 렌더링"""
        self._clear_screen()

        print("=" * 80)
        print("API QUOTA STATUS DASHBOARD")
        print("=" * 80)
        print(f"📅 업데이트: {data['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if "error" in data:
            print(f"❌ 오류: {data['error']}")
            return

        health = data["health"]
        usage = data["usage"]
        alerts = data["alerts"]
        exhaustion = data["exhaustion_prediction"]

        # 전체 상태
        print("🏥 시스템 상태")
        print("-" * 40)
        print(f"전체 상태: {self._format_status_indicator(health['overall_status'])}")
        print()

        # API 상태
        print("🔌 API 상태")
        print("-" * 40)
        for api_name, api_data in health["apis"].items():
            status_text = self._format_status_indicator(api_data["status"])
            print(f"{api_name.upper():12}: {status_text}")
            if api_data.get("error_message"):
                print(f"{'':12}  └─ {api_data['error_message'][:60]}...")
        print()

        # 사용량 통계 (7일)
        print("📊 사용량 통계 (7일)")
        print("-" * 40)
        print(f"총 체크 수:     {usage['total_checks']:,}회")

        for api_name, api_stats in usage["apis"].items():
            print(f"\n{api_name.upper()} API:")
            print(f"  가용성:       {api_stats['availability_rate']:.1f}%")
            print(f"  체크 수:      {api_stats['total_checks']:,}회")
            print(f"  초과 횟수:    {api_stats['exceeded_count']:,}회")
            print(f"  현재 상태:    {self._format_status_indicator(api_stats['last_status'])}")

        print()

        # 활성 알림
        print(f"🔔 활성 알림 (24시간)")
        print("-" * 40)
        if alerts:
            for alert in alerts[-5:]:  # 최근 5개만 표시
                emoji = {"warning": "⚠️", "critical": "🚨", "exceeded": "❌"}
                time_ago = self._format_time_ago(alert.timestamp)
                print(f"{emoji.get(alert.alert_type, '🔔')} {alert.message}")
                print(f"{'':3}└─ {time_ago}")
                if alert.recommendation:
                    print(f"{'':3}💡 {alert.recommendation}")
                print()
        else:
            print("✅ 활성 알림 없음")

        print()

        # 쿼터 소진 예측
        print("🔮 쿼터 소진 예측")
        print("-" * 40)
        if exhaustion:
            time_until = exhaustion - datetime.now()
            if time_until.total_seconds() > 0:
                if time_until.days > 0:
                    print(f"OpenAI API: 약 {time_until.days}일 후 소진 예상")
                elif time_until.seconds > 3600:
                    hours = time_until.seconds // 3600
                    print(f"OpenAI API: 약 {hours}시간 후 소진 예상")
                else:
                    minutes = time_until.seconds // 60
                    print(f"OpenAI API: 약 {minutes}분 후 소진 예상")
                print(f"예상 시간: {exhaustion.strftime('%Y-%m-%d %H:%M')}")
            else:
                print("OpenAI API: 이미 소진됨")
        else:
            print("OpenAI API: 예측 불가 (데이터 부족)")

        print()

        # 권장사항
        if health.get("recommendations"):
            print("💡 권장사항")
            print("-" * 40)
            for i, rec in enumerate(health["recommendations"], 1):
                print(f"{i}. {rec}")

        print()
        print("=" * 80)
        print(f"🔄 다음 갱신: {self.refresh_interval}초 후 | 'Ctrl+C'로 종료")

    async def run_dashboard(self, auto_refresh: bool = True):
        """대시보드 실행"""
        self.logger.info("🎛️ 쿼터 상태 대시보드 시작")

        try:
            while True:
                # 데이터 수집 및 렌더링
                data = await self._get_dashboard_data()
                self._render_dashboard(data)

                if not auto_refresh:
                    break

                # 일정 시간 대기
                await asyncio.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            print("\n\n👋 대시보드를 종료합니다.")
            self.logger.info("🛑 사용자에 의해 대시보드 종료")

        except Exception as e:
            self.logger.error(f"❌ 대시보드 실행 중 오류: {e}")

    async def show_detailed_report(self):
        """상세 리포트 표시"""
        print("\n" + "=" * 80)
        print("📋 상세 쿼터 리포트")
        print("=" * 80)

        # 7일 요약
        usage_7d = self.monitor.get_usage_summary(days=7)
        print("\n📅 7일 요약:")
        print(f"총 체크 수: {usage_7d['total_checks']:,}회")
        print(f"경고 알림: {usage_7d['alerts']['warning']:,}개")
        print(f"위험 알림: {usage_7d['alerts']['critical']:,}개")
        print(f"초과 알림: {usage_7d['alerts']['exceeded']:,}개")

        # 30일 요약
        usage_30d = self.monitor.get_usage_summary(days=30)
        print("\n📅 30일 요약:")
        print(f"총 체크 수: {usage_30d['total_checks']:,}회")
        print(f"경고 알림: {usage_30d['alerts']['warning']:,}개")
        print(f"위험 알림: {usage_30d['alerts']['critical']:,}개")
        print(f"초과 알림: {usage_30d['alerts']['exceeded']:,}개")

        # 최근 이력
        print("\n📚 최근 이력 (10개):")
        recent_history = sorted(self.monitor.history, key=lambda x: x.timestamp, reverse=True)[:10]

        for entry in recent_history:
            time_str = entry.timestamp.strftime("%m-%d %H:%M")
            status_str = self._format_status_indicator(entry.status.value)
            print(f"{time_str} | {entry.api_name:8} | {status_str}")


async def main():
    """메인 실행 함수"""
    print("API 쿼터 대시보드를 시작합니다...")

    # 설정 로드
    config = Config()

    # 대시보드 생성
    dashboard = QuotaDashboard(config)

    # 옵션 메뉴
    print("\n선택하세요:")
    print("1. 실시간 대시보드 (자동 갱신)")
    print("2. 일회성 상태 확인")
    print("3. 상세 리포트")

    try:
        choice = input("\n선택 (1-3): ").strip()

        if choice == "1":
            await dashboard.run_dashboard(auto_refresh=True)
        elif choice == "2":
            await dashboard.run_dashboard(auto_refresh=False)
        elif choice == "3":
            await dashboard.show_detailed_report()
        else:
            print("잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")


if __name__ == "__main__":
    asyncio.run(main())