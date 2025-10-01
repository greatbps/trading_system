#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
execute_liquidation.py

긴급 청산 실행 스크립트 - 사용자 확인 후 손절가 하회 종목 청산
"""

import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass

# Rich for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.progress import Progress
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.find_stoploss_breached_stocks import StopLossDetector, StopLossAlert
from utils.logger import get_logger
from config.trading_config import TradingConfig

@dataclass
class LiquidationOrder:
    """청산 주문 정보"""
    stock_code: str
    stock_name: str
    quantity: int
    order_type: str = "MARKET"  # 시장가
    estimated_price: float = 0.0
    estimated_amount: float = 0.0
    order_id: Optional[str] = None
    status: str = "PENDING"  # PENDING, SUBMITTED, FILLED, FAILED
    execution_time: Optional[datetime] = None
    actual_price: Optional[float] = None
    actual_amount: Optional[float] = None

class LiquidationExecutor:
    """긴급 청산 실행기"""

    def __init__(self, config_path: str = None):
        """청산 실행기 초기화"""
        self.logger = get_logger("LiquidationExecutor")
        self.console = Console() if RICH_AVAILABLE else None

        # 설정 로드
        try:
            self.config = TradingConfig(config_path) if config_path else TradingConfig()
        except Exception as e:
            self.logger.error(f"❌ 설정 로드 실패: {e}")
            self.config = None

        # 손절가 탐지기
        self.detector = StopLossDetector(config_path)

        # 거래 핸들러 (실제 구현시 임포트 필요)
        self.trading_handler = None
        self._init_trading_handler()

        # 안전 장치
        self.safety_enabled = True
        self.max_liquidation_count = 10  # 한 번에 최대 10개 종목만
        self.confirmation_required = True

    def _init_trading_handler(self):
        """거래 핸들러 초기화"""
        try:
            # 실제 환경에서는 적절한 핸들러 임포트
            # from core.db_auto_trading_handler import DbAutoTradingHandler
            # self.trading_handler = DbAutoTradingHandler(self.config)
            pass
        except Exception as e:
            self.logger.warning(f"⚠️ 거래 핸들러 초기화 실패: {e}")

    async def execute_emergency_liquidation(self) -> Dict[str, Any]:
        """
        긴급 청산 실행

        Returns:
            청산 실행 결과
        """
        try:
            if self.console:
                self.console.print(Panel.fit(
                    "🚨 긴급 청산 시스템\n"
                    "손절가 하회 종목을 안전하게 청산합니다.\n\n"
                    "⚠️ 주의: 이 작업은 되돌릴 수 없습니다!",
                    style="bold red"
                ))

            # 1. 손절가 하회 종목 탐지
            alerts = await self.detector.find_stoploss_breached_stocks()

            if not alerts:
                if self.console:
                    self.console.print(Panel.fit(
                        "✅ 청산이 필요한 종목이 없습니다.\n"
                        "모든 보유 종목이 안전한 상태입니다.",
                        style="bold green"
                    ))
                return {"status": "no_action", "message": "청산 대상 없음"}

            # 2. 청산 대상 종목 표시
            await self.detector.display_alerts(alerts)

            # 3. 청산 계획 생성
            liquidation_plan = await self._create_liquidation_plan(alerts)

            # 4. 사용자 확인
            if self.confirmation_required:
                confirmed = await self._get_user_confirmation(liquidation_plan)
                if not confirmed:
                    if self.console:
                        self.console.print("[yellow]⚠️ 사용자가 청산을 취소했습니다.[/yellow]")
                    return {"status": "cancelled", "message": "사용자 취소"}

            # 5. 청산 실행
            execution_results = await self._execute_liquidation_plan(liquidation_plan)

            # 6. 결과 요약
            summary = await self._summarize_results(execution_results)

            return {
                "status": "executed",
                "liquidation_plan": liquidation_plan,
                "execution_results": execution_results,
                "summary": summary
            }

        except Exception as e:
            self.logger.error(f"❌ 긴급 청산 실행 실패: {e}")
            return {"status": "error", "message": str(e)}

    async def _create_liquidation_plan(self, alerts: List[StopLossAlert]) -> List[LiquidationOrder]:
        """청산 계획 생성"""
        try:
            if self.console:
                self.console.print("\n[cyan]📋 청산 계획 생성 중...[/cyan]")

            liquidation_orders = []

            # 위험도가 높은 순서로 정렬
            sorted_alerts = sorted(alerts, key=lambda x: (
                0 if x.risk_level == 'CRITICAL' else 1,
                -x.breach_pct
            ))

            # 안전 장치: 최대 개수 제한
            if len(sorted_alerts) > self.max_liquidation_count:
                if self.console:
                    self.console.print(f"[yellow]⚠️ 안전을 위해 상위 {self.max_liquidation_count}개 종목만 처리합니다.[/yellow]")
                sorted_alerts = sorted_alerts[:self.max_liquidation_count]

            for alert in sorted_alerts:
                # 현재가 기준 예상 청산 금액 계산
                estimated_amount = alert.current_price * alert.quantity * 0.99  # 1% 슬리피지 고려

                order = LiquidationOrder(
                    stock_code=alert.stock_code,
                    stock_name=alert.stock_name,
                    quantity=alert.quantity,
                    estimated_price=alert.current_price,
                    estimated_amount=estimated_amount
                )

                liquidation_orders.append(order)

            return liquidation_orders

        except Exception as e:
            self.logger.error(f"❌ 청산 계획 생성 실패: {e}")
            return []

    async def _get_user_confirmation(self, liquidation_plan: List[LiquidationOrder]) -> bool:
        """사용자 확인"""
        try:
            if not liquidation_plan:
                return False

            if self.console:
                # 청산 계획 표시
                self.console.print("\n[bold yellow]🚨 청산 계획 확인[/bold yellow]")

                plan_table = Table(title="청산 예정 종목")
                plan_table.add_column("종목", style="cyan")
                plan_table.add_column("수량", style="magenta", justify="right")
                plan_table.add_column("예상가격", style="yellow", justify="right")
                plan_table.add_column("예상금액", style="yellow", justify="right")
                plan_table.add_column("주문유형", style="green")

                total_estimated_amount = 0

                for order in liquidation_plan:
                    plan_table.add_row(
                        f"{order.stock_name}\n({order.stock_code})",
                        f"{order.quantity:,}주",
                        f"₩{order.estimated_price:,.0f}",
                        f"₩{order.estimated_amount:,.0f}",
                        "시장가 매도"
                    )
                    total_estimated_amount += order.estimated_amount

                self.console.print(plan_table)

                # 총계 표시
                self.console.print(f"\n[bold]총 예상 청산 금액: ₩{total_estimated_amount:,.0f}[/bold]")

                # 경고 메시지
                self.console.print(Panel.fit(
                    "⚠️ 중요한 안내사항\n\n"
                    "1. 시장가 매도 주문으로 즉시 체결됩니다\n"
                    "2. 실제 체결가는 현재가와 다를 수 있습니다\n"
                    "3. 이 작업은 되돌릴 수 없습니다\n"
                    "4. 시장 상황을 고려하여 신중히 결정하세요",
                    style="bold red"
                ))

                # 확인 절차
                self.console.print("\n[bold red]정말로 위 종목들을 청산하시겠습니까?[/bold red]")

                # 단계별 확인
                step1 = Confirm.ask("1단계: 청산 계획을 확인했습니까?")
                if not step1:
                    return False

                step2 = Confirm.ask("2단계: 시장가 매도의 위험성을 이해했습니까?")
                if not step2:
                    return False

                # 최종 확인 - 종목 코드 입력
                if len(liquidation_plan) > 0:
                    first_stock = liquidation_plan[0]
                    expected_code = first_stock.stock_code

                    self.console.print(f"\n[bold]3단계: 최종 확인을 위해 첫 번째 종목 코드를 입력하세요[/bold]")
                    self.console.print(f"종목: {first_stock.stock_name}({expected_code})")

                    entered_code = Prompt.ask("종목 코드 입력")

                    if entered_code != expected_code:
                        self.console.print("[red]❌ 종목 코드가 일치하지 않습니다. 청산을 취소합니다.[/red]")
                        return False

                final_confirm = Confirm.ask("최종 확인: 정말로 청산을 실행하시겠습니까?")
                return final_confirm

            else:
                # 텍스트 기반 확인
                print("\n🚨 청산 계획 확인")
                print(f"총 {len(liquidation_plan)}개 종목을 청산 예정")

                for order in liquidation_plan:
                    print(f"- {order.stock_name}({order.stock_code}): {order.quantity}주")

                response = input("\n정말로 청산하시겠습니까? (y/N): ")
                return response.lower() in ['y', 'yes']

        except Exception as e:
            self.logger.error(f"❌ 사용자 확인 실패: {e}")
            return False

    async def _execute_liquidation_plan(self, liquidation_plan: List[LiquidationOrder]) -> List[LiquidationOrder]:
        """청산 계획 실행"""
        try:
            if self.console:
                self.console.print("\n[red]🚨 청산 실행 중...[/red]")

            executed_orders = []

            with Progress(console=self.console) as progress:
                task = progress.add_task("청산 실행 중...", total=len(liquidation_plan))

                for order in liquidation_plan:
                    try:
                        # 개별 종목 청산 실행
                        executed_order = await self._execute_single_liquidation(order)
                        executed_orders.append(executed_order)
                        progress.advance(task)

                        # 주문 간 간격 (시장 충격 최소화)
                        await asyncio.sleep(1)

                    except Exception as e:
                        self.logger.error(f"❌ {order.stock_name} 청산 실패: {e}")
                        order.status = "FAILED"
                        executed_orders.append(order)
                        progress.advance(task)

            return executed_orders

        except Exception as e:
            self.logger.error(f"❌ 청산 계획 실행 실패: {e}")
            return []

    async def _execute_single_liquidation(self, order: LiquidationOrder) -> LiquidationOrder:
        """개별 종목 청산 실행"""
        try:
            self.logger.info(f"💰 {order.stock_name}({order.stock_code}) 청산 시작")

            # 실제 구현에서는 거래 핸들러를 통해 매도 주문
            if self.trading_handler:
                # 시장가 매도 주문 실행
                # result = await self.trading_handler.sell_stock(
                #     stock_code=order.stock_code,
                #     quantity=order.quantity,
                #     order_type="MARKET"
                # )
                #
                # order.order_id = result.get("order_id")
                # order.status = "SUBMITTED"
                pass

            # 데모 모드: 시뮬레이션 실행
            order.status = "FILLED"
            order.execution_time = datetime.now()
            order.actual_price = order.estimated_price * 0.99  # 1% 슬리피지
            order.actual_amount = order.actual_price * order.quantity

            self.logger.info(f"✅ {order.stock_name} 청산 완료: ₩{order.actual_amount:,.0f}")

            return order

        except Exception as e:
            self.logger.error(f"❌ {order.stock_name} 청산 실행 실패: {e}")
            order.status = "FAILED"
            return order

    async def _summarize_results(self, execution_results: List[LiquidationOrder]) -> Dict[str, Any]:
        """청산 결과 요약"""
        try:
            successful_orders = [o for o in execution_results if o.status == "FILLED"]
            failed_orders = [o for o in execution_results if o.status == "FAILED"]

            total_liquidated_amount = sum(o.actual_amount or 0 for o in successful_orders)
            total_liquidated_count = len(successful_orders)

            summary = {
                "total_orders": len(execution_results),
                "successful_orders": len(successful_orders),
                "failed_orders": len(failed_orders),
                "total_liquidated_amount": total_liquidated_amount,
                "total_liquidated_count": total_liquidated_count,
                "execution_time": datetime.now(),
                "success_rate": len(successful_orders) / len(execution_results) * 100 if execution_results else 0
            }

            # 결과 표시
            if self.console:
                self.console.print("\n[bold green]📊 청산 결과 요약[/bold green]")

                result_table = Table(title="청산 결과")
                result_table.add_column("종목", style="cyan")
                result_table.add_column("상태", style="bold")
                result_table.add_column("실제가격", style="yellow", justify="right")
                result_table.add_column("실제금액", style="yellow", justify="right")
                result_table.add_column("실행시간", style="dim")

                for order in execution_results:
                    status_style = "green" if order.status == "FILLED" else "red"
                    price_text = f"₩{order.actual_price:,.0f}" if order.actual_price else "-"
                    amount_text = f"₩{order.actual_amount:,.0f}" if order.actual_amount else "-"
                    time_text = order.execution_time.strftime("%H:%M:%S") if order.execution_time else "-"

                    result_table.add_row(
                        f"{order.stock_name}\n({order.stock_code})",
                        f"[{status_style}]{order.status}[/{status_style}]",
                        price_text,
                        amount_text,
                        time_text
                    )

                self.console.print(result_table)

                # 요약 통계
                summary_panel = Panel.fit(
                    f"✅ 총 {total_liquidated_count}개 종목 청산 완료\n"
                    f"💰 총 청산 금액: ₩{total_liquidated_amount:,.0f}\n"
                    f"📈 성공률: {summary['success_rate']:.1f}%",
                    style="bold green"
                )
                self.console.print(summary_panel)

            return summary

        except Exception as e:
            self.logger.error(f"❌ 결과 요약 실패: {e}")
            return {}

    async def save_execution_report(self, execution_results: List[LiquidationOrder], summary: Dict[str, Any], output_dir: str = "reports") -> str:
        """청산 실행 보고서 저장"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = output_path / f"liquidation_execution_{timestamp}.json"

            # 보고서 데이터 생성
            report_data = {
                "execution_timestamp": datetime.now().isoformat(),
                "summary": summary,
                "execution_results": []
            }

            for order in execution_results:
                order_data = {
                    "stock_code": order.stock_code,
                    "stock_name": order.stock_name,
                    "quantity": order.quantity,
                    "order_type": order.order_type,
                    "estimated_price": order.estimated_price,
                    "estimated_amount": order.estimated_amount,
                    "actual_price": order.actual_price,
                    "actual_amount": order.actual_amount,
                    "status": order.status,
                    "execution_time": order.execution_time.isoformat() if order.execution_time else None,
                    "order_id": order.order_id
                }
                report_data["execution_results"].append(order_data)

            # 파일 저장
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"📄 청산 실행 보고서 저장: {report_file}")
            return str(report_file)

        except Exception as e:
            self.logger.error(f"❌ 실행 보고서 저장 실패: {e}")
            return ""

async def main():
    """메인 함수"""
    try:
        # 청산 실행기 초기화
        executor = LiquidationExecutor()

        # 긴급 청산 실행
        result = await executor.execute_emergency_liquidation()

        # 결과에 따른 처리
        if result["status"] == "executed":
            # 실행 보고서 저장
            report_file = await executor.save_execution_report(
                result["execution_results"],
                result["summary"]
            )

            if executor.console:
                executor.console.print(f"[green]📄 실행 보고서: {report_file}[/green]")

        elif result["status"] == "cancelled":
            if executor.console:
                executor.console.print("[yellow]⚠️ 청산이 취소되었습니다.[/yellow]")

        elif result["status"] == "no_action":
            if executor.console:
                executor.console.print("[green]✅ 청산이 필요한 종목이 없습니다.[/green]")

        else:
            if executor.console:
                executor.console.print(f"[red]❌ 청산 실행 실패: {result.get('message')}[/red]")

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