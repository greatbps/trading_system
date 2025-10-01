#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_stoploss_breached_stocks.py

손절가 하회 종목 탐지 스크립트 - 긴급 청산 대상 찾기
"""

import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

# Rich for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
    from rich.prompt import Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from utils.logger import get_logger
from config.trading_config import TradingConfig

@dataclass
class StopLossAlert:
    """손절 알림 정보"""
    stock_code: str
    stock_name: str
    current_price: float
    purchase_price: float
    stop_loss_price: float
    quantity: int
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    breach_amount: float  # 손절가 하회 금액
    breach_pct: float     # 손절가 하회 비율
    risk_level: str       # 위험도 (HIGH, CRITICAL)
    recommendation: str   # 권장 조치

class StopLossDetector:
    """손절가 하회 탐지기"""

    def __init__(self, config_path: str = None):
        """탐지기 초기화"""
        self.logger = get_logger("StopLossDetector")
        self.console = Console() if RICH_AVAILABLE else None

        # 설정 로드
        try:
            self.config = TradingConfig(config_path) if config_path else TradingConfig()
        except Exception as e:
            self.logger.error(f"❌ 설정 로드 실패: {e}")
            self.config = None

        # 데이터베이스 매니저
        self.db_manager = DatabaseManager()

        # 거래 핸들러 (실제 구현시 임포트 필요)
        self.trading_handler = None
        self._init_trading_handler()

    def _init_trading_handler(self):
        """거래 핸들러 초기화"""
        try:
            # 실제 환경에서는 적절한 핸들러 임포트
            # from core.db_auto_trading_handler import DbAutoTradingHandler
            # self.trading_handler = DbAutoTradingHandler(self.config)
            pass
        except Exception as e:
            self.logger.warning(f"⚠️ 거래 핸들러 초기화 실패: {e}")

    async def find_stoploss_breached_stocks(self) -> List[StopLossAlert]:
        """
        손절가 하회 종목 탐지

        Returns:
            손절 알림 목록
        """
        try:
            if self.console:
                self.console.print(Panel.fit(
                    "🚨 손절가 하회 종목 탐지 시작\n"
                    "현재 보유 종목의 손절 상태를 점검합니다.",
                    style="bold red"
                ))

            # 1. 현재 보유 종목 조회
            holdings = await self._get_current_holdings()
            if not holdings:
                if self.console:
                    self.console.print("[yellow]⚠️ 현재 보유 중인 종목이 없습니다.[/yellow]")
                return []

            # 2. 각 종목의 손절 상태 확인
            alerts = []

            with Progress(console=self.console) as progress:
                task = progress.add_task("손절 상태 확인 중...", total=len(holdings))

                for holding in holdings:
                    try:
                        alert = await self._check_stock_stoploss(holding)
                        if alert:
                            alerts.append(alert)
                        progress.advance(task)
                    except Exception as e:
                        self.logger.error(f"❌ {holding.get('stock_code', 'Unknown')} 확인 실패: {e}")
                        progress.advance(task)

            # 3. 위험도별 정렬 (CRITICAL > HIGH)
            alerts.sort(key=lambda x: (
                0 if x.risk_level == 'CRITICAL' else 1,
                x.breach_pct
            ), reverse=True)

            return alerts

        except Exception as e:
            self.logger.error(f"❌ 손절가 하회 종목 탐지 실패: {e}")
            return []

    async def _get_current_holdings(self) -> List[Dict[str, Any]]:
        """현재 보유 종목 조회"""
        try:
            # 실제 구현에서는 거래 핸들러를 통해 조회
            if self.trading_handler:
                response = await self.trading_handler.get_balance()
                return response.get('holdings', [])

            # 데모용 데이터
            demo_holdings = [
                {
                    'stock_code': '005930',
                    'stock_name': '삼성전자',
                    'quantity': 100,
                    'avg_price': 75000,
                    'current_price': 72000,
                    'current_value': 7200000,
                    'unrealized_pnl': -300000,
                    'unrealized_pnl_pct': -4.0
                },
                {
                    'stock_code': '000660',
                    'stock_name': 'SK하이닉스',
                    'quantity': 50,
                    'avg_price': 120000,
                    'current_price': 115000,
                    'current_value': 5750000,
                    'unrealized_pnl': -250000,
                    'unrealized_pnl_pct': -4.17
                }
            ]

            self.logger.info(f"📊 보유 종목 조회 완료: {len(demo_holdings)}개")
            return demo_holdings

        except Exception as e:
            self.logger.error(f"❌ 보유 종목 조회 실패: {e}")
            return []

    async def _check_stock_stoploss(self, holding: Dict[str, Any]) -> Optional[StopLossAlert]:
        """개별 종목 손절 상태 확인"""
        try:
            stock_code = holding['stock_code']
            stock_name = holding['stock_name']
            current_price = holding['current_price']
            avg_price = holding['avg_price']
            quantity = holding['quantity']

            # 데이터베이스에서 손절가 조회
            stop_loss_price = await self._get_stop_loss_price(stock_code)

            if not stop_loss_price:
                # 손절가가 설정되지 않은 경우 기본값 사용 (평균 매수가의 95%)
                stop_loss_price = avg_price * 0.95
                self.logger.warning(f"⚠️ {stock_name}({stock_code}) 손절가 미설정, 기본값 사용: {stop_loss_price:,.0f}원")

            # 손절가 하회 여부 확인
            if current_price > stop_loss_price:
                return None  # 손절가 하회하지 않음

            # 손절 알림 정보 생성
            breach_amount = stop_loss_price - current_price
            breach_pct = (breach_amount / stop_loss_price) * 100

            current_value = current_price * quantity
            unrealized_pnl = (current_price - avg_price) * quantity
            unrealized_pnl_pct = (current_price - avg_price) / avg_price * 100

            # 위험도 판정
            risk_level = self._assess_risk_level(breach_pct, unrealized_pnl_pct)
            recommendation = self._get_recommendation(risk_level, breach_pct)

            alert = StopLossAlert(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                purchase_price=avg_price,
                stop_loss_price=stop_loss_price,
                quantity=quantity,
                current_value=current_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                breach_amount=breach_amount,
                breach_pct=breach_pct,
                risk_level=risk_level,
                recommendation=recommendation
            )

            return alert

        except Exception as e:
            self.logger.error(f"❌ {holding.get('stock_code', 'Unknown')} 손절 확인 실패: {e}")
            return None

    async def _get_stop_loss_price(self, stock_code: str) -> Optional[float]:
        """데이터베이스에서 손절가 조회"""
        try:
            # 실제 구현에서는 데이터베이스 쿼리
            # query = "SELECT stop_loss_price FROM portfolio WHERE stock_code = ?"
            # result = await self.db_manager.execute_query(query, (stock_code,))

            # 데모용 손절가 (평균 매수가의 95%)
            demo_stop_loss = {
                '005930': 71250,  # 삼성전자 손절가
                '000660': 114000  # SK하이닉스 손절가
            }

            return demo_stop_loss.get(stock_code)

        except Exception as e:
            self.logger.error(f"❌ {stock_code} 손절가 조회 실패: {e}")
            return None

    def _assess_risk_level(self, breach_pct: float, unrealized_pnl_pct: float) -> str:
        """위험도 평가"""
        if breach_pct > 3.0 or unrealized_pnl_pct < -8.0:
            return "CRITICAL"
        elif breach_pct > 1.0 or unrealized_pnl_pct < -5.0:
            return "HIGH"
        else:
            return "MEDIUM"

    def _get_recommendation(self, risk_level: str, breach_pct: float) -> str:
        """권장 조치 제안"""
        if risk_level == "CRITICAL":
            return "🚨 즉시 청산 권장"
        elif risk_level == "HIGH":
            return "⚠️ 긴급 청산 검토"
        else:
            return "⚡ 면밀 관찰 필요"

    async def display_alerts(self, alerts: List[StopLossAlert]):
        """손절 알림 표시"""
        try:
            if not alerts:
                if self.console:
                    self.console.print(Panel.fit(
                        "✅ 손절가 하회 종목이 없습니다.\n"
                        "모든 보유 종목이 안전한 상태입니다.",
                        style="bold green"
                    ))
                else:
                    print("✅ 손절가 하회 종목이 없습니다.")
                return

            # 위험도별 분류
            critical_alerts = [a for a in alerts if a.risk_level == "CRITICAL"]
            high_alerts = [a for a in alerts if a.risk_level == "HIGH"]

            if self.console:
                # 요약 패널
                self.console.print(Panel.fit(
                    f"🚨 손절가 하회 종목 발견!\n"
                    f"총 {len(alerts)}개 종목 (위험: {len(critical_alerts)}개, 높음: {len(high_alerts)}개)",
                    style="bold red"
                ))

                # 상세 테이블
                table = Table(title="손절가 하회 종목 상세")
                table.add_column("종목", style="cyan", width=12)
                table.add_column("현재가", style="magenta", justify="right")
                table.add_column("손절가", style="red", justify="right")
                table.add_column("하회금액", style="red", justify="right")
                table.add_column("하회율", style="red", justify="right")
                table.add_column("평가손익", style="yellow", justify="right")
                table.add_column("손익률", style="yellow", justify="right")
                table.add_column("위험도", style="bold")
                table.add_column("권장조치", style="bold")

                for alert in alerts:
                    pnl_style = "green" if alert.unrealized_pnl >= 0 else "red"
                    risk_style = "red" if alert.risk_level == "CRITICAL" else "yellow"

                    table.add_row(
                        f"{alert.stock_name}\n({alert.stock_code})",
                        f"₩{alert.current_price:,.0f}",
                        f"₩{alert.stop_loss_price:,.0f}",
                        f"₩{alert.breach_amount:,.0f}",
                        f"{alert.breach_pct:.2f}%",
                        f"[{pnl_style}]₩{alert.unrealized_pnl:,.0f}[/{pnl_style}]",
                        f"[{pnl_style}]{alert.unrealized_pnl_pct:.2f}%[/{pnl_style}]",
                        f"[{risk_style}]{alert.risk_level}[/{risk_style}]",
                        alert.recommendation
                    )

                self.console.print(table)

                # 총 손실 요약
                total_unrealized_loss = sum(alert.unrealized_pnl for alert in alerts if alert.unrealized_pnl < 0)
                total_current_value = sum(alert.current_value for alert in alerts)

                summary_table = Table(title="손실 요약")
                summary_table.add_column("항목", style="cyan")
                summary_table.add_column("금액", style="magenta", justify="right")

                summary_table.add_row("총 평가금액", f"₩{total_current_value:,.0f}")
                summary_table.add_row("총 평가손실", f"₩{total_unrealized_loss:,.0f}")

                self.console.print(summary_table)

            else:
                # 텍스트 출력
                print("\n🚨 손절가 하회 종목 발견!")
                print(f"총 {len(alerts)}개 종목")
                print("\n" + "="*80)

                for alert in alerts:
                    print(f"\n종목: {alert.stock_name}({alert.stock_code})")
                    print(f"현재가: ₩{alert.current_price:,.0f}")
                    print(f"손절가: ₩{alert.stop_loss_price:,.0f}")
                    print(f"하회금액: ₩{alert.breach_amount:,.0f} ({alert.breach_pct:.2f}%)")
                    print(f"평가손익: ₩{alert.unrealized_pnl:,.0f} ({alert.unrealized_pnl_pct:.2f}%)")
                    print(f"위험도: {alert.risk_level}")
                    print(f"권장조치: {alert.recommendation}")
                    print("-" * 40)

        except Exception as e:
            self.logger.error(f"❌ 알림 표시 실패: {e}")

    async def save_alert_report(self, alerts: List[StopLossAlert], output_dir: str = "reports") -> str:
        """알림 보고서 저장"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = output_path / f"stoploss_alert_{timestamp}.json"

            # 보고서 데이터 생성
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "total_alerts": len(alerts),
                "critical_count": len([a for a in alerts if a.risk_level == "CRITICAL"]),
                "high_count": len([a for a in alerts if a.risk_level == "HIGH"]),
                "alerts": []
            }

            for alert in alerts:
                alert_data = {
                    "stock_code": alert.stock_code,
                    "stock_name": alert.stock_name,
                    "current_price": alert.current_price,
                    "stop_loss_price": alert.stop_loss_price,
                    "breach_amount": alert.breach_amount,
                    "breach_pct": alert.breach_pct,
                    "unrealized_pnl": alert.unrealized_pnl,
                    "unrealized_pnl_pct": alert.unrealized_pnl_pct,
                    "risk_level": alert.risk_level,
                    "recommendation": alert.recommendation
                }
                report_data["alerts"].append(alert_data)

            # 파일 저장
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"📄 알림 보고서 저장: {report_file}")
            return str(report_file)

        except Exception as e:
            self.logger.error(f"❌ 보고서 저장 실패: {e}")
            return ""

async def main():
    """메인 함수"""
    try:
        # 손절가 탐지기 초기화
        detector = StopLossDetector()

        # 손절가 하회 종목 탐지
        alerts = await detector.find_stoploss_breached_stocks()

        # 결과 표시
        await detector.display_alerts(alerts)

        # 보고서 저장
        if alerts:
            report_file = await detector.save_alert_report(alerts)
            if detector.console:
                detector.console.print(f"[green]📄 상세 보고서: {report_file}[/green]")

        # 다음 단계 안내
        if alerts and detector.console:
            detector.console.print(Panel.fit(
                "⚠️ 다음 단계 안내\n\n"
                "1. 위 종목들의 손절 필요성을 신중히 검토하세요\n"
                "2. 청산이 필요하다면 'execute_liquidation.py' 스크립트를 실행하세요\n"
                "3. 시장 상황과 개인 투자 전략을 종합적으로 고려하세요",
                style="bold yellow"
            ))

    except KeyboardInterrupt:
        print("\n👋 사용자가 중단했습니다.")
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 스크립트 실행
    asyncio.run(main())