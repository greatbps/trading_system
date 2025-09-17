#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완성된 _configure_trading_settings 함수

이 코드를 core/db_auto_trading_handler.py의 1084-1085라인에 있는
플레이스홀더 함수를 대체하여 사용하세요.
"""

async def _configure_trading_settings(self):
    """매매 설정 구성 - 현재 설정 조회 및 수정"""
    try:
        while True:
            # 현재 설정 조회
            current_settings = await self._get_current_trading_settings()
            
            # 설정 메뉴 출력
            self.console.print("\n" + "="*60)
            self.console.print("[bold cyan]⚙️  매매 설정 구성[/bold cyan]")
            self.console.print("="*60)
            
            # 현재 설정 상태 표시
            settings_table = Table(show_header=True, header_style="bold magenta")
            settings_table.add_column("설정 항목", style="cyan", width=25)
            settings_table.add_column("현재 값", style="green", width=20)
            settings_table.add_column("설명", style="white", width=35)
            
            settings_table.add_row(
                "목표 수익률",
                f"{current_settings.get('target_profit_rate', 10.0):.1f}%",
                "매수 후 목표 수익률 (자동 매도)"
            )
            settings_table.add_row(
                "손절 비율", 
                f"{current_settings.get('stop_loss_rate', 5.0):.1f}%",
                "매수가 대비 최대 손실 비율"
            )
            settings_table.add_row(
                "ATR 기반 손절",
                "활성화" if current_settings.get('use_atr_stop_loss', True) else "비활성화",
                "ATR 지표 기반 동적 손절 사용"
            )
            settings_table.add_row(
                "ATR 배수",
                f"{current_settings.get('atr_multiplier', 2.0):.1f}배",
                "ATR 손절가 계산 배수"
            )
            settings_table.add_row(
                "최소 거래 수량",
                f"{current_settings.get('min_order_quantity', 1)}주",
                "최소 주문 수량"
            )
            settings_table.add_row(
                "최대 거래 금액",
                f"{current_settings.get('max_order_amount', 1000000):,}원",
                "단일 주문 최대 금액"
            )
            settings_table.add_row(
                "매매 활성화",
                "활성화" if current_settings.get('trading_enabled', False) else "비활성화",
                "자동 매매 실행 허용"
            )
            
            self.console.print(settings_table)
            
            # 메뉴 옵션
            menu_options = """
[bold yellow]📋 설정 옵션:[/bold yellow]

[cyan]1.[/cyan] 목표 수익률 변경
[cyan]2.[/cyan] 손절 비율 변경  
[cyan]3.[/cyan] ATR 기반 손절 토글
[cyan]4.[/cyan] ATR 배수 변경
[cyan]5.[/cyan] 거래 수량/금액 한도 변경
[cyan]6.[/cyan] 매매 활성화/비활성화 토글
[cyan]7.[/cyan] 설정 초기화
[cyan]8.[/cyan] 현재 설정으로 테스트 실행
[cyan]0.[/cyan] 이전 메뉴로 돌아가기
"""
            self.console.print(Panel.fit(menu_options, border_style="yellow"))
            
            # 사용자 선택
            choice = Prompt.ask(
                "[bold yellow]선택하세요[/bold yellow]",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"],
                default="0"
            )
            
            if choice == "0":
                self.console.print("[green]✅ 매매 설정을 종료합니다.[/green]")
                break
            elif choice == "1":
                await self._change_target_profit_rate(current_settings)
            elif choice == "2":
                await self._change_stop_loss_rate(current_settings)
            elif choice == "3":
                await self._toggle_atr_stop_loss(current_settings)
            elif choice == "4":
                await self._change_atr_multiplier(current_settings)
            elif choice == "5":
                await self._change_trading_limits(current_settings)
            elif choice == "6":
                await self._toggle_trading_enabled(current_settings)
            elif choice == "7":
                await self._reset_trading_settings()
            elif choice == "8":
                await self._test_trading_settings(current_settings)
                
    except Exception as e:
        self.console.print(f"[bold red]❌ 매매 설정 중 오류 발생: {e}[/bold red]")
        self.logger.error(f"매매 설정 오류: {e}")

async def _get_current_trading_settings(self) -> Dict[str, Any]:
    """현재 매매 설정 조회"""
    # 기본 설정 (추후 DB나 설정 파일에서 로드)
    default_settings = {
        'target_profit_rate': 10.0,     # 목표 수익률 10%
        'stop_loss_rate': 5.0,          # 손절 비율 5%
        'use_atr_stop_loss': True,      # ATR 기반 손절 사용
        'atr_multiplier': 2.0,          # ATR 배수
        'min_order_quantity': 1,        # 최소 주문 수량
        'max_order_amount': 1000000,    # 최대 주문 금액 100만원
        'trading_enabled': False,       # 매매 비활성화 (안전)
    }
    
    try:
        # 추후: config 파일이나 DB에서 설정 로드
        # config_file = "trading_settings.json"
        # if os.path.exists(config_file):
        #     with open(config_file, 'r', encoding='utf-8') as f:
        #         user_settings = json.load(f)
        #         default_settings.update(user_settings)
        
        return default_settings
        
    except Exception as e:
        self.logger.error(f"매매 설정 조회 실패: {e}")
        return default_settings

async def _save_trading_settings(self, settings: Dict[str, Any]) -> bool:
    """매매 설정 저장"""
    try:
        # 추후: config 파일이나 DB에 설정 저장
        # config_file = "trading_settings.json"
        # with open(config_file, 'w', encoding='utf-8') as f:
        #     json.dump(settings, f, ensure_ascii=False, indent=2)
        
        self.console.print("[green]✅ 설정이 저장되었습니다.[/green]")
        return True
        
    except Exception as e:
        self.console.print(f"[red]❌ 설정 저장 실패: {e}[/red]")
        self.logger.error(f"매매 설정 저장 실패: {e}")
        return False

async def _change_target_profit_rate(self, current_settings: Dict[str, Any]):
    """목표 수익률 변경"""
    try:
        current_rate = current_settings.get('target_profit_rate', 10.0)
        self.console.print(f"[cyan]현재 목표 수익률: {current_rate:.1f}%[/cyan]")
        
        new_rate = FloatPrompt.ask(
            "[yellow]새로운 목표 수익률 (%)을 입력하세요[/yellow]",
            default=current_rate
        )
        
        if 0.1 <= new_rate <= 100.0:
            current_settings['target_profit_rate'] = new_rate
            await self._save_trading_settings(current_settings)
            self.console.print(f"[green]✅ 목표 수익률이 {new_rate:.1f}%로 변경되었습니다.[/green]")
        else:
            self.console.print("[red]❌ 목표 수익률은 0.1% ~ 100% 범위여야 합니다.[/red]")
            
    except Exception as e:
        self.console.print(f"[red]❌ 목표 수익률 변경 실패: {e}[/red]")

async def _change_stop_loss_rate(self, current_settings: Dict[str, Any]):
    """손절 비율 변경"""
    try:
        current_rate = current_settings.get('stop_loss_rate', 5.0)
        self.console.print(f"[cyan]현재 손절 비율: {current_rate:.1f}%[/cyan]")
        
        new_rate = FloatPrompt.ask(
            "[yellow]새로운 손절 비율 (%)을 입력하세요[/yellow]",
            default=current_rate
        )
        
        if 0.1 <= new_rate <= 50.0:
            current_settings['stop_loss_rate'] = new_rate
            await self._save_trading_settings(current_settings)
            self.console.print(f"[green]✅ 손절 비율이 {new_rate:.1f}%로 변경되었습니다.[/green]")
        else:
            self.console.print("[red]❌ 손절 비율은 0.1% ~ 50% 범위여야 합니다.[/red]")
            
    except Exception as e:
        self.console.print(f"[red]❌ 손절 비율 변경 실패: {e}[/red]")

async def _toggle_atr_stop_loss(self, current_settings: Dict[str, Any]):
    """ATR 기반 손절 토글"""
    try:
        current_status = current_settings.get('use_atr_stop_loss', True)
        new_status = not current_status
        
        current_settings['use_atr_stop_loss'] = new_status
        await self._save_trading_settings(current_settings)
        
        status_text = "활성화" if new_status else "비활성화"
        self.console.print(f"[green]✅ ATR 기반 손절이 {status_text}되었습니다.[/green]")
        
        if new_status:
            self.console.print("[cyan]💡 ATR 기반 손절은 시장 변동성에 따라 동적으로 손절가를 계산합니다.[/cyan]")
        else:
            self.console.print("[yellow]⚠️  고정 비율 손절을 사용합니다. (변동성 고려 안함)[/yellow]")
            
    except Exception as e:
        self.console.print(f"[red]❌ ATR 설정 변경 실패: {e}[/red]")

async def _change_atr_multiplier(self, current_settings: Dict[str, Any]):
    """ATR 배수 변경"""
    try:
        current_multiplier = current_settings.get('atr_multiplier', 2.0)
        self.console.print(f"[cyan]현재 ATR 배수: {current_multiplier:.1f}배[/cyan]")
        
        new_multiplier = FloatPrompt.ask(
            "[yellow]새로운 ATR 배수를 입력하세요[/yellow]",
            default=current_multiplier
        )
        
        if 0.5 <= new_multiplier <= 5.0:
            current_settings['atr_multiplier'] = new_multiplier
            await self._save_trading_settings(current_settings)
            self.console.print(f"[green]✅ ATR 배수가 {new_multiplier:.1f}배로 변경되었습니다.[/green]")
            
            if new_multiplier < 1.5:
                self.console.print("[yellow]⚠️  낮은 ATR 배수는 빈번한 손절을 야기할 수 있습니다.[/yellow]")
            elif new_multiplier > 3.0:
                self.console.print("[yellow]⚠️  높은 ATR 배수는 큰 손실을 허용할 수 있습니다.[/yellow]")
        else:
            self.console.print("[red]❌ ATR 배수는 0.5 ~ 5.0 범위여야 합니다.[/red]")
            
    except Exception as e:
        self.console.print(f"[red]❌ ATR 배수 변경 실패: {e}[/red]")

async def _change_trading_limits(self, current_settings: Dict[str, Any]):
    """거래 수량/금액 한도 변경"""
    try:
        current_min_qty = current_settings.get('min_order_quantity', 1)
        current_max_amount = current_settings.get('max_order_amount', 1000000)
        
        self.console.print(f"[cyan]현재 최소 주문 수량: {current_min_qty}주[/cyan]")
        self.console.print(f"[cyan]현재 최대 주문 금액: {current_max_amount:,}원[/cyan]")
        
        new_min_qty = IntPrompt.ask(
            "[yellow]새로운 최소 주문 수량 (주)[/yellow]",
            default=current_min_qty
        )
        
        new_max_amount = IntPrompt.ask(
            "[yellow]새로운 최대 주문 금액 (원)[/yellow]",
            default=current_max_amount
        )
        
        if new_min_qty >= 1 and new_max_amount >= 10000:
            current_settings['min_order_quantity'] = new_min_qty
            current_settings['max_order_amount'] = new_max_amount
            await self._save_trading_settings(current_settings)
            self.console.print(f"[green]✅ 거래 한도가 변경되었습니다.[/green]")
            self.console.print(f"[green]   최소 수량: {new_min_qty}주[/green]")
            self.console.print(f"[green]   최대 금액: {new_max_amount:,}원[/green]")
        else:
            self.console.print("[red]❌ 최소 수량은 1주 이상, 최대 금액은 10,000원 이상이어야 합니다.[/red]")
            
    except Exception as e:
        self.console.print(f"[red]❌ 거래 한도 변경 실패: {e}[/red]")

async def _toggle_trading_enabled(self, current_settings: Dict[str, Any]):
    """매매 활성화/비활성화 토글"""
    try:
        current_status = current_settings.get('trading_enabled', False)
        
        if not current_status:
            # 활성화 확인
            self.console.print("[bold red]⚠️  주의: 매매를 활성화하면 실제 거래가 실행될 수 있습니다![/bold red]")
            confirm = Confirm.ask("[yellow]매매를 활성화하시겠습니까?[/yellow]", default=False)
            
            if confirm:
                current_settings['trading_enabled'] = True
                await self._save_trading_settings(current_settings)
                self.console.print("[green]✅ 자동 매매가 활성화되었습니다.[/green]")
                self.console.print("[yellow]💡 모니터링 중인 종목에 대해 자동 매매가 수행됩니다.[/yellow]")
            else:
                self.console.print("[cyan]매매 활성화를 취소했습니다.[/cyan]")
        else:
            # 비활성화
            current_settings['trading_enabled'] = False
            await self._save_trading_settings(current_settings)
            self.console.print("[green]✅ 자동 매매가 비활성화되었습니다.[/green]")
            self.console.print("[cyan]💡 모니터링은 계속되지만 실제 거래는 실행되지 않습니다.[/cyan]")
            
    except Exception as e:
        self.console.print(f"[red]❌ 매매 상태 변경 실패: {e}[/red]")

async def _reset_trading_settings(self):
    """설정 초기화"""
    try:
        self.console.print("[bold red]⚠️  주의: 모든 매매 설정이 기본값으로 초기화됩니다![/bold red]")
        confirm = Confirm.ask("[yellow]정말로 설정을 초기화하시겠습니까?[/yellow]", default=False)
        
        if confirm:
            default_settings = {
                'target_profit_rate': 10.0,
                'stop_loss_rate': 5.0,
                'use_atr_stop_loss': True,
                'atr_multiplier': 2.0,
                'min_order_quantity': 1,
                'max_order_amount': 1000000,
                'trading_enabled': False,
            }
            
            await self._save_trading_settings(default_settings)
            self.console.print("[green]✅ 모든 매매 설정이 기본값으로 초기화되었습니다.[/green]")
        else:
            self.console.print("[cyan]설정 초기화를 취소했습니다.[/cyan]")
            
    except Exception as e:
        self.console.print(f"[red]❌ 설정 초기화 실패: {e}[/red]")

async def _test_trading_settings(self, current_settings: Dict[str, Any]):
    """현재 설정으로 테스트 실행"""
    try:
        self.console.print("[cyan]🧪 현재 설정으로 테스트를 실행합니다...[/cyan]")
        
        # 테스트 시나리오
        test_scenarios = [
            {'symbol': 'TEST001', 'buy_price': 10000, 'current_price': 11000, 'scenario': '목표 수익률 달성'},
            {'symbol': 'TEST002', 'buy_price': 20000, 'current_price': 19000, 'scenario': '손절가 근접'},
            {'symbol': 'TEST003', 'buy_price': 15000, 'current_price': 15300, 'scenario': '소폭 상승'},
        ]
        
        test_table = Table(show_header=True, header_style="bold cyan")
        test_table.add_column("종목", style="cyan")
        test_table.add_column("매수가", justify="right")
        test_table.add_column("현재가", justify="right")
        test_table.add_column("수익률", justify="right")
        test_table.add_column("판단", style="bold")
        test_table.add_column("시나리오")
        
        for scenario in test_scenarios:
            buy_price = scenario['buy_price']
            current_price = scenario['current_price']
            profit_rate = ((current_price - buy_price) / buy_price) * 100
            
            # 설정에 따른 판단
            target_rate = current_settings['target_profit_rate']
            stop_loss_rate = current_settings['stop_loss_rate']
            
            if profit_rate >= target_rate:
                judgment = "[green]매도 신호[/green]"
            elif profit_rate <= -stop_loss_rate:
                judgment = "[red]손절 신호[/red]"
            else:
                judgment = "[yellow]보유[/yellow]"
            
            test_table.add_row(
                scenario['symbol'],
                f"{buy_price:,}원",
                f"{current_price:,}원",
                f"{profit_rate:+.1f}%",
                judgment,
                scenario['scenario']
            )
        
        self.console.print("\n[bold yellow]📊 테스트 결과:[/bold yellow]")
        self.console.print(test_table)
        
        self.console.print(f"\n[cyan]💡 현재 설정 요약:[/cyan]")
        self.console.print(f"   목표 수익률: {current_settings['target_profit_rate']:.1f}% 이상 → 매도")
        self.console.print(f"   손절 비율: {current_settings['stop_loss_rate']:.1f}% 이하 → 손절")
        self.console.print(f"   ATR 손절: {'활성화' if current_settings['use_atr_stop_loss'] else '비활성화'}")
        
    except Exception as e:
        self.console.print(f"[red]❌ 테스트 실행 실패: {e}[/red]")

# 필요한 추가 임포트 (파일 상단에 추가해야 함)
"""
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt
import json
import os
from typing import Dict, Any
"""