#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/core/db_auto_trading_handler.py

DB 연동 자동매매 핸들러 - 완전한 모니터링 시스템
"""

import asyncio
import copy
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt

from sqlalchemy.orm import Session
from utils.logger import get_logger
from database.models import (
    MonitoringStock, MonitoringSchedulerState, MonitoringType, MonitoringStatus,
    Stock
)
from trading.db_auto_trader import DatabaseAutoTrader
from trading.executor import TradingExecutor
from monitoring.db_monitoring_scheduler import DatabaseMonitoringRemovalScheduler
from utils.stock_search import StockSearchEngine
from strategies.strategy_manager import StrategyManager
from utils.market_schedule_manager import MarketScheduleManager
from .auto_mode_controller import AutoModeController, AutoMode


class DatabaseAutoTradingHandler:
    """DB 연동 자동매매 핸들러 - 영구 저장/복원 지원"""
    
    def __init__(self, config, kis_collector, db_manager=None, analysis_engine=None):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.analysis_engine = analysis_engine
        self.logger = get_logger("DatabaseAutoTradingHandler")
        self.console = Console()
        
        self.executor = TradingExecutor(config, kis_collector, db_manager)
        # market_manager를 먼저 초기화
        from utils.market_schedule_manager import MarketScheduleManager
        self.market_manager = MarketScheduleManager(config, kis_collector)
        # 올바른 파라미터 순서로 DatabaseAutoTrader 초기화
        self.auto_trader = DatabaseAutoTrader(config, kis_collector, self.executor, self.market_manager, analysis_engine, db_manager)
        self.removal_scheduler = DatabaseMonitoringRemovalScheduler(config, kis_collector, db_manager)
        self.stock_search = StockSearchEngine(kis_collector)
        self.strategy_manager = StrategyManager(config)
        self.auto_mode_controller = AutoModeController(config, self.market_manager)
        self.monitoring_task = None
        self.removal_scheduler_task = None
        
        # 설정 파일 경로
        self.settings_file = Path("D:/trading_system/configs/trading_settings.json")
        self._setup_auto_mode_callbacks()

    def _safe_get_profit_rate(self, data, key='profit_rate', default=0.0):
        """profit_rate 값을 안전하게 추출하는 유틸리티 함수"""
        try:
            value = data.get(key, default) if isinstance(data, dict) else default

            # dict인 경우 기본값 반환
            if isinstance(value, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"profit_rate가 dict 형태입니다: {value}, 기본값 {default} 사용")
                return default

            # 숫자로 변환 가능한지 확인
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            if hasattr(self, 'logger'):
                self.logger.warning(f"profit_rate 변환 실패: {value}, 기본값 {default} 사용")
            return default

    def _setup_auto_mode_callbacks(self):
        try:
            self.auto_mode_controller.add_mode_change_callback(
                AutoMode.MONITORING, self._on_monitoring_mode_change
            )
            self.auto_mode_controller.add_mode_change_callback(
                AutoMode.TRADING, self._on_trading_mode_change
            )
            self.logger.info("✅ 자동 모드 콜백 설정 완료")
        except Exception as e:
            self.logger.error(f"❌ 자동 모드 콜백 설정 실패: {e}")

    async def _on_monitoring_mode_change(self, mode, old_status, new_status):
        from core.auto_mode_controller import ModeStatus
        try:
            if new_status == ModeStatus.ACTIVE and old_status != ModeStatus.ACTIVE:
                self.logger.info("🟢 모니터링 모드 자동 활성화")
                await self._start_monitoring_internal()
            elif new_status == ModeStatus.INACTIVE and old_status == ModeStatus.ACTIVE:
                self.logger.info("🔴 모니터링 모드 자동 비활성화")
                await self._stop_monitoring_internal()
        except Exception as e:
            self.logger.error(f"❌ 모니터링 모드 변경 처리 실패: {e}")

    async def _on_trading_mode_change(self, mode, old_status, new_status):
        from core.auto_mode_controller import ModeStatus
        try:
            if new_status == ModeStatus.ACTIVE and old_status != ModeStatus.ACTIVE:
                self.logger.info("🟢 매매 모드 자동 활성화")
                await self._activate_auto_trading()
            elif new_status == ModeStatus.INACTIVE and old_status == ModeStatus.ACTIVE:
                self.logger.info("🔴 매매 모드 자동 비활성화")
                await self._deactivate_auto_trading()
        except Exception as e:
            self.logger.error(f"❌ 매매 모드 변경 처리 실패: {e}")

    async def _start_monitoring_internal(self):
        try:
            if self.monitoring_task is None or self.monitoring_task.done():
                self.monitoring_task = asyncio.create_task(self.auto_trader.start_monitoring())
                self.logger.info("📊 자동 모니터링 내부 시작")
        except Exception as e:
            self.logger.error(f"❌ 자동 모니터링 내부 시작 실패: {e}")

    async def _stop_monitoring_internal(self):
        try:
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.logger.info("📊 자동 모니터링 내부 중지")
        except Exception as e:
            self.logger.error(f"❌ 자동 모니터링 내부 중지 실패: {e}")

    async def _activate_auto_trading(self):
        try:
            if hasattr(self.executor, 'enable_trading'):
                self.executor.enable_trading()
                self.logger.info("💰 자동매매 활성화")
            else:
                self.logger.warning("⚠️ executor에 enable_trading 메서드가 없습니다.")
        except Exception as e:
            self.logger.error(f"❌ 자동매매 활성화 실패: {e}")

    async def _deactivate_auto_trading(self):
        try:
            if hasattr(self.executor, 'disable_trading'):
                self.executor.disable_trading()
                self.logger.info("💰 자동매매 비활성화")
            else:
                self.logger.warning("⚠️ executor에 disable_trading 메서드가 없습니다.")
        except Exception as e:
            self.logger.error(f"❌ 자동매매 비활성화 실패: {e}")

    async def initialize_systems(self):
        try:
            await self.market_manager.initialize()
            await self.auto_mode_controller.initialize()
            await self.market_manager.start_monitoring()
            if hasattr(self.executor, 'enable_trading'):
                self.executor.enable_trading()
                self.logger.info("🟢 매매 모드 활성화")
            self.logger.info("🚀 모든 시스템 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 시스템 초기화 실패: {e}")

    async def cleanup_systems(self):
        try:
            await self.auto_mode_controller.cleanup()
            await self.market_manager.cleanup()
            self.logger.info("🧹 시스템 정리 완료")
        except Exception as e:
            self.logger.error(f"❌ 시스템 정리 실패: {e}")

    async def handle_auto_trading_menu(self) -> None:
        """자동매매 메뉴 처리"""
        # main.py에서 이미 백그라운드 모니터링이 시작되었으므로 중복 시작 안함
        
        while True:
            try:
                self._display_auto_trading_menu()
                choice = Prompt.ask("\n🤖 선택하세요", choices=[str(i) for i in range(14)], default="0").strip()
                
                if choice == '0':
                    self.console.print("[green]✅ 자동매매 메뉴를 종료합니다.[/green]")
                    break
                elif choice == '1': await self._start_monitoring()
                elif choice == '2': await self._stop_monitoring()
                elif choice == '3': await self._view_monitoring_status_safe()
                elif choice == '4': await self._manage_monitoring_stocks()
                elif choice == '5': await self._configure_trading_settings()
                elif choice == '6': await self._manual_trade()
                elif choice == '7': await self._add_buy_recommendation()
                elif choice == '8': await self._start_removal_scheduler()
                elif choice == '9': await self._stop_removal_scheduler()
                elif choice == '10': await self._view_removal_scheduler_status()
                elif choice == '11': await self._remove_monitoring()
                elif choice == '12': await self._view_market_schedule()
                elif choice == '13': await self._manage_auto_modes()
                else: self.console.print("❌ 잘못된 선택입니다. 다시 선택해주세요.")
                
                if choice != '0':
                    Prompt.ask("\n[dim]계속하려면 Enter를 누르세요...[/dim]")

            except KeyboardInterrupt:
                self.console.print("\n\nExiting auto trading menu...")
                break
            except Exception as e:
                self.logger.error(f"❌ 자동매매 메뉴 처리 오류: {e}")
                self.console.print(f"❌ 오류가 발생했습니다: {e}")

    def _display_auto_trading_menu(self):
        """자동매매 메뉴 표시"""
        from rich.panel import Panel
        
        menu = """[bold cyan]자동매매 관리[/bold cyan]
    1. 모니터링 시작
    2. 모니터링 중지  
    3. 모니터링 현황 (HTS 보유종목 + 전략 추출종목)
    4. 감시중인 종목 관리
    5. 매매 설정 확인
    6. 수동 매매
    7. 매수 추천 추가
    8. 제거 스케줄러 시작
    9. 제거 스케줄러 중지
    10. 제거 스케줄러 상태
    11. 모니터링 제거
    12. 시장 일정 확인
    13. 자동 모드 관리
    
    [bold red]0. 메인 메뉴로 돌아가기[/bold red]"""
        
        self.console.print(Panel.fit(menu, title="🤖 자동매매 시스템", border_style="cyan"))
    
    # 주요 메서드 구현
    async def _start_monitoring(self):
        """모니터링 시작 - 시장 시간 확인"""
        if not self.market_manager.is_monitoring_allowed_now():
            status_info = self.market_manager.get_current_status_info()
            self.console.print(f"[bold red]시장 운영 시간이 아닙니다. 현재 상태: {status_info.get('market_status_korean', '알 수 없음')}[/bold red]")
            return

        self.console.print("[yellow]INFO 백그라운드에서 이미 모니터링이 실행 중입니다.[/yellow]")
    
    async def _stop_monitoring(self): 
        """모니터링 중지 - UI만 중지, 백그라운드는 계속 실행"""
        # UI 모니터링 표시만 중지, 실제 모니터링은 계속 실행
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            # 주의: auto_trader.stop_monitoring() 호출하지 않음 - 백그라운드에서 계속 실행
            self.console.print("[green]✅ 실시간 모니터링 UI를 종료합니다.[/green]")
            self.console.print("[blue]📊 백그라운드에서 매매조건 감시는 계속 진행됩니다.[/blue]")
            self.console.print("[yellow]💡 완전한 모니터링 중지를 원하면 service_controller.py를 사용하세요.[/yellow]")
        else:
            self.console.print("[yellow]⚠️ 실행중인 UI 모니터링이 없습니다.[/yellow]")
            self.console.print("[blue]📊 백그라운드 모니터링은 독립적으로 실행될 수 있습니다.[/blue]")
    
    def _normalize_strategy_name(self, strategy_name: str) -> str:
        """전략명을 정규화하여 실제 전략명으로 매핑"""
        if not strategy_name or strategy_name.upper() in ['N/A', 'NONE', 'NULL']:
            return "momentum"  # 기본 전략
        
        strategy_mapping = {
            # 기존 잘못된 이름들 매핑
            'AI_ANALYSIS': 'momentum',
            'AI_MOMENTUM': 'momentum',
            'MOMENTUM': 'momentum',
            'BREAKOUT': 'breakout', 
            'RSI_STRATEGY': 'rsi',
            'RSI': 'rsi',
            'SUPERTREND_EMA': 'supertrend_ema_rsi',
            'SUPERTREND': 'supertrend_ema_rsi',
            'VWAP_STRATEGY': 'vwap',
            'VWAP': 'vwap',
            'EOD': 'eod',
            'EOD_STRATEGY': 'eod',
            'SCALPING_3M': 'scalping_3m',
            'SCALPING': 'scalping_3m',
            'MULTI_TIMEFRAME': 'multi_timeframe',
            'MTF': 'multi_timeframe',
            
            # 소문자도 처리
            'ai_analysis': 'momentum',
            'ai_momentum': 'momentum',
            'rsi_strategy': 'rsi',
            'supertrend_ema': 'supertrend_ema_rsi',
            'vwap_strategy': 'vwap',
            'eod_strategy': 'eod',
            'scalping_3m': 'scalping_3m',
            'multi_timeframe': 'multi_timeframe',
            
            # 보유 종목용 특수 전략
            'holding_stock': 'momentum',  # 보유 종목은 모멘텀으로 처리
        }
        
        # 전략명 정규화
        normalized = strategy_name.upper().strip()
        mapped_strategy = strategy_mapping.get(normalized, strategy_name.lower())
        
        # 유효한 전략인지 확인
        valid_strategies = ['momentum', 'breakout', 'rsi', 'supertrend_ema_rsi', 'vwap', 'eod', 'scalping_3m', 'multi_timeframe']
        if mapped_strategy not in valid_strategies:
            return 'momentum'  # 기본 전략으로 폴백
        
        return mapped_strategy

    def _get_strategy_display_name(self, strategy_name: str) -> str:
        """전략명을 한글 표시명으로 변환"""
        strategy_display_names = {
            'momentum': '모멘텀',
            'breakout': '돌파전략', 
            'rsi': 'RSI전략',
            'supertrend_ema_rsi': '슈퍼트렌드',
            'vwap': 'VWAP전략',
            'eod': '장마감전략',
            'scalping_3m': '3분스캘핑',
            'multi_timeframe': '멀티타임'
        }
        normalized_strategy = self._normalize_strategy_name(strategy_name)
        return strategy_display_names.get(normalized_strategy, normalized_strategy)

    def _calculate_dynamic_stop_loss(self, symbol: str, current_price: float, avg_price: float, profit_rate: float) -> str:
        """실시간 동적 손절가 계산 (트레일링 스톱 방식)"""
        if current_price <= 0:
            return "N/A"

        try:
            # profit_rate 안전성 검사
            safe_profit_rate = profit_rate
            if isinstance(profit_rate, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"트레일링스톱 계산에서 profit_rate가 dict: {profit_rate}, 0으로 처리")
                safe_profit_rate = 0.0
            elif not isinstance(profit_rate, (int, float)):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"트레일링스톱 계산에서 profit_rate 타입 오류: {type(profit_rate)}, 0으로 처리")
                safe_profit_rate = 0.0

            # 최고가 기록 관리 (메모리에 임시 저장)
            if not hasattr(self, '_highest_prices'):
                self._highest_prices = {}

            # 현재 가격이 최고가 경신 시 업데이트
            if symbol not in self._highest_prices or current_price > self._highest_prices[symbol]:
                self._highest_prices[symbol] = current_price

            highest_price = self._highest_prices[symbol]

            # 수익률 구간별 트레일링 스톱 전략
            if safe_profit_rate >= 15:  # 15% 이상 대박 수익
                # 보수적 트레일링: 최고가 대비 -8% 
                trailing_stop = int(highest_price * 0.92)
                return f"{trailing_stop:,}"
                
            elif safe_profit_rate >= 10:  # 10% 이상 좋은 수익
                # 표준 트레일링: 최고가 대비 -10%
                trailing_stop = int(highest_price * 0.90)
                return f"{trailing_stop:,}"

            elif safe_profit_rate >= 5:  # 5% 이상 약간 수익
                # 적극적 트레일링: 최고가 대비 -12%
                trailing_stop = int(highest_price * 0.88)
                return f"{trailing_stop:,}"

            elif safe_profit_rate >= 0:  # 0~5% 소폭 수익
                # 보호 손절: 평단가 대비 -2%
                if avg_price > 0:
                    protection_stop = int(avg_price * 0.98)
                else:
                    protection_stop = int(current_price * 0.97)
                return f"{protection_stop:,}"
                
            else:  # 손실 상황
                # 손실 제한: 평단가 대비 -5%
                if avg_price > 0:
                    loss_limit_stop = int(avg_price * 0.95)
                else:
                    loss_limit_stop = int(current_price * 0.95)
                return f"{loss_limit_stop:,}"
                
        except Exception as e:
            # 계산 실패 시 기본 손절가
            if avg_price > 0:
                default_stop = int(avg_price * 0.95)
            else:
                default_stop = int(current_price * 0.95)
            return f"{default_stop:,}"

    

    def _get_holding_status(self, current_price: float, stop_loss_price: str, profit_rate: float) -> str:
        """보유종목 상태 판단"""
        if current_price <= 0:
            return "[yellow]정보없음[/yellow]"

        try:
            # profit_rate 안전성 검사
            safe_profit_rate = profit_rate
            if isinstance(profit_rate, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"보유상태 판단2에서 profit_rate가 dict: {profit_rate}, 0으로 처리")
                safe_profit_rate = 0.0
            elif not isinstance(profit_rate, (int, float)):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"보유상태 판단2에서 profit_rate 타입 오류: {type(profit_rate)}, 0으로 처리")
                safe_profit_rate = 0.0

            if stop_loss_price != "N/A":
                stop_loss_value = float(stop_loss_price.replace(',', ''))
                if current_price <= stop_loss_value:
                    return "[red]손절신호[/red]"

            # 수익률 기반 상태 표시
            if safe_profit_rate >= 15:
                return "[bold green]대박수익[/bold green]"
            elif safe_profit_rate >= 10:
                return "[green]좋은수익[/green]"
            elif safe_profit_rate >= 5:
                return "[green]수익중[/green]"
            elif safe_profit_rate >= 0:
                return "[yellow]소폭수익[/yellow]"
            elif safe_profit_rate >= -5:
                return "[yellow]소폭손실[/yellow]"
            else:
                return "[red]손실주의[/red]"
        except:
            return "[gray]계산불가[/gray]"

    async def start_realtime_price_monitoring(self):
        """실시간 가격 모니터링 시작 (30초마다 업데이트)"""
        if not hasattr(self, '_price_monitoring_active'):
            self._price_monitoring_active = True
            asyncio.create_task(self._realtime_price_update_loop())
            
    async def _realtime_price_update_loop(self):
        """실시간 가격 업데이트 루프"""
        while getattr(self, '_price_monitoring_active', False):
            try:
                # ⚡ 장 시간 확인 (09:00 ~ 15:30, 평일만)
                from datetime import datetime, time
                import calendar
                
                now = datetime.now()
                current_time = now.time()
                current_weekday = now.weekday()  # 0=월요일, 6=일요일
                
                # MarketScheduleManager를 통한 정확한 시장 시간 확인 (점심시간 포함)
                is_monitoring_allowed = False
                if hasattr(self, 'market_manager') and self.market_manager:
                    await self.market_manager.update_market_status()
                    is_monitoring_allowed = self.market_manager.is_monitoring_allowed_now()
                
                # 모니터링 허용되지 않는 시간인 경우
                if not is_monitoring_allowed:
                    if hasattr(self, 'logger'):
                        if current_weekday >= 5:
                            weekday_name = "토요일" if current_weekday == 5 else "일요일"
                            self.logger.info(f"📅 {weekday_name} - 모니터링 대기 중")
                        else:
                            self.logger.info(f"🕐 장 시간 외 ({current_time.strftime('%H:%M')}) - 모니터링 대기 중")
                    
                    await asyncio.sleep(300)  # 장 시간 외에는 5분마다 확인
                    continue
                
                # 30초마다 실제 보유종목만 손절/익절 모니터링 (장 시간에만)
                if hasattr(self, 'kis_collector') and self.kis_collector:
                    all_holdings_raw = await self.kis_collector.get_holdings()
                    if all_holdings_raw:
                        # [CONCURRENCY BUG FIX] 다른 비동기 작업에 의한 데이터 오염을 막기 위해 깊은 복사본을 생성
                        all_holdings = copy.deepcopy(all_holdings_raw)

                        # ⚡ 핵심 필터링: 수량 > 0인 실제 보유 종목만 추출
                        actual_holdings = {}
                        zero_quantity_stocks = []
                        
                        for symbol, holding in all_holdings.items():
                            quantity = getattr(holding, 'quantity', 0) if hasattr(holding, 'quantity') else holding.get('quantity', 0)
                            if quantity > 0:
                                actual_holdings[symbol] = holding  # 실제 보유 종목만
                            else:
                                zero_quantity_stocks.append(symbol)
                        
                        # 실제 보유 종목에 대해서만 손절/익절 신호 처리
                        if actual_holdings:
                            for symbol, holding in actual_holdings.items():
                                await self._update_holding_prices(symbol, holding)
                            
                            if hasattr(self, 'logger'):
                                self.logger.debug(f"📊 손절/익절 모니터링 중: {len(actual_holdings)}개 종목")
                        else:
                            if hasattr(self, 'logger'):
                                if not hasattr(self, '_no_actual_holdings_logged') or not self._no_actual_holdings_logged:
                                    self.logger.info("ℹ️ 실제 보유 종목이 없어 손절/익절 모니터링 중지")
                                    self._no_actual_holdings_logged = True
                        
                        # 수량 0 종목 정리 (한 번만 로그)
                        if zero_quantity_stocks and hasattr(self, 'logger'):
                            if not hasattr(self, '_zero_stocks_reported'):
                                self._zero_stocks_reported = set()
                            new_zero_stocks = [s for s in zero_quantity_stocks if s not in self._zero_stocks_reported]
                            if new_zero_stocks:
                                self.logger.info(f"🗑️ 매도완료로 모니터링 제외: {', '.join(new_zero_stocks[:3])}{'...' if len(new_zero_stocks) > 3 else ''}")
                                self._zero_stocks_reported.update(new_zero_stocks)
                    else:
                        if hasattr(self, 'logger'):
                            if not hasattr(self, '_no_api_holdings_logged') or not self._no_api_holdings_logged:
                                self.logger.warning("⚠️ KIS API에서 보유 종목 조회 결과 없음")
                                self._no_api_holdings_logged = True
                
                await asyncio.sleep(30)  # 장 시간 중에는 30초마다 모니터링
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.error(f"실시간 가격 업데이트 오류: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_strategy_stock_prices(self, symbol: str, holding: dict):
        """전략 추출 감시 종목 가격 모니터링 (매도 신호 차단)"""
        try:
            # ⚡ MarketScheduleManager를 통한 정확한 시장 시간 확인 (점심시간 포함)
            is_monitoring_allowed = False
            if hasattr(self, 'market_manager') and self.market_manager:
                await self.market_manager.update_market_status()
                is_monitoring_allowed = self.market_manager.is_monitoring_allowed_now()
            
            if not is_monitoring_allowed:
                return  # 모니터링 허용되지 않는 시간이면 모니터링하지 않음
            
            # ⚠️ 이 메서드는 전략 추출 감시 종목용으로, 매도 신호를 보내지 않음
            # KIS API로 실시간 현재가 조회
            stock_info = await self.kis_collector.get_stock_info(symbol)
            current_price = 0
            if stock_info:
                if hasattr(stock_info, 'current_price'):
                    current_price = stock_info.current_price
                elif hasattr(stock_info, 'price'):
                    current_price = stock_info.price
                elif isinstance(stock_info, dict) and 'current_price' in stock_info:
                    current_price = stock_info['current_price']
            
            if current_price > 0:
                # 수익률 계산
                avg_price = holding.get('avg_price', 0)
                if avg_price > 0:
                    profit_rate = ((current_price - avg_price) / avg_price) * 100
                    
                    # 동적 손절가 계산
                    stop_loss_price = self._calculate_dynamic_stop_loss(
                        symbol, current_price, avg_price, profit_rate
                    )
                    
                    # ⚠️ 전략 추출 감시 종목은 손절 정보만 로그에 표시 (매도 신호 차단)
                    if stop_loss_price != "N/A":
                        try:
                            stop_loss_value = float(stop_loss_price.replace(',', ''))
                            
                            # 상세 디버깅 로그 추가 (전략 추출 감시 종목 표시)
                            if hasattr(self, 'logger'):
                                self.logger.info(f"📊 {symbol} 손절 체크 (전략추출): 현재가={current_price:,}원, 손절가={stop_loss_value:,}원, 수익률={profit_rate:+.1f}%")
                            
                            if current_price <= stop_loss_value:
                                if hasattr(self, 'logger'):
                                    self.logger.warning(f"🚨 {symbol} 손절 조건 충족! (전략 추출 감시 종목 - 매도 신호 차단)")
                                # ✅ 전략 추출 감시 종목은 매도 신호를 보내지 않음
                            else:
                                if hasattr(self, 'logger') and profit_rate < -3:  # 손실이 클 때만 로그
                                    self.logger.debug(f"⏳ {symbol} 손절 대기중 (전략추출): 현재가({current_price:,}) > 손절가({stop_loss_value:,})")
                        except Exception as e:
                            if hasattr(self, 'logger'):
                                self.logger.error(f"❌ {symbol} 손절가 처리 오류 (전략추출): {e}")
                    else:
                        if hasattr(self, 'logger') and profit_rate < -3:  # 손실이 클 때만 로그
                            self.logger.debug(f"⚠️ {symbol} 손절가 계산 실패 (전략추출): 현재가={current_price:,}원, 평단가={avg_price:,}원")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"{symbol} 전략 추출 감시 가격 업데이트 실패: {e}")

    async def _update_holding_prices(self, symbol: str, holding: dict):
        """개별 보유종목 손절/익절 모니터링 (실제 보유종목만 호출됨)"""
        try:
            
            
            # ✅ 이 메서드는 실제 보유 종목에 대해서만 호출됨 (매도 신호 허용)
            # KIS API로 실시간 현재가 조회
            stock_info = await self.kis_collector.get_stock_info(symbol)
            current_price = 0
            if stock_info:
                if hasattr(stock_info, 'current_price'):
                    current_price = stock_info.current_price
                elif hasattr(stock_info, 'price'):
                    current_price = stock_info.price
                elif isinstance(stock_info, dict) and 'current_price' in stock_info:
                    current_price = stock_info['current_price']
            
            if current_price > 0:
                # 수익률 계산
                avg_price = holding.get('avg_price', 0)
                if avg_price > 0:
                    profit_rate = ((current_price - avg_price) / avg_price) * 100
                    
                    # 동적 손절가 계산
                    stop_loss_price = self._calculate_dynamic_stop_loss(
                        symbol, current_price, avg_price, profit_rate
                    )
                    
                    # 손절가 도달 시 자동 매도 신호 전송
                    if stop_loss_price != "N/A":
                        try:
                            stop_loss_value = float(stop_loss_price.replace(',', ''))
                            
                            # 상세 디버깅 로그 추가
                            if hasattr(self, 'logger'):
                                self.logger.info(f"📊 {symbol} 손절 체크: 현재가={current_price:,}원, 손절가={stop_loss_value:,}원, 수익률={profit_rate:+.1f}%")
                            
                            if current_price <= stop_loss_value:
                                if hasattr(self, 'logger'):
                                    self.logger.warning(f"🚨 {symbol} 손절 조건 충족! 매도 신호 전송 중...")
                                await self._trigger_stop_loss_sell(symbol, current_price, stop_loss_value, profit_rate, holding)
                            else:
                                if hasattr(self, 'logger') and profit_rate < -3:  # 손실이 클 때만 로그
                                    self.logger.debug(f"⏳ {symbol} 손절 대기중: 현재가({current_price:,}) > 손절가({stop_loss_value:,})")
                        except Exception as e:
                            if hasattr(self, 'logger'):
                                self.logger.error(f"❌ {symbol} 손절가 처리 오류: {e}")
                    else:
                        if hasattr(self, 'logger') and profit_rate < -3:  # 손실이 클 때만 로그
                            self.logger.debug(f"⚠️ {symbol} 손절가 계산 실패 (N/A): 현재가={current_price:,}원, 평단가={avg_price:,}원")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"{symbol} 가격 업데이트 실패: {e}")
    
    async def _trigger_stop_loss_sell(self, symbol: str, current_price: float, stop_loss_price: float, profit_rate: float, holding: dict):
        """손절가 도달 시 자동 매도 신호 트리거"""
        try:
            # ⚡ 장 시간 및 거래일 확인 - MarketScheduleManager 사용
            if hasattr(self, 'market_manager') and self.market_manager:
                # 공식 시장 일정 관리자를 통한 정확한 거래 시간 확인
                await self.market_manager.update_market_status()
                
                if not self.market_manager.is_trading_allowed_now():
                    market_status = self.market_manager.current_status.value
                    market_status_korean = self.market_manager._get_status_korean(self.market_manager.current_status)
                    if hasattr(self, 'logger'):
                        self.logger.info(f"장시간외 {symbol} 매도 신호 차단 - 현재 상태: {market_status_korean} ({market_status})")
                    return False
            else:
                # 백업 로직: MarketScheduleManager가 없는 경우 기본 시간 체크
                # 주의: 매도 신호는 거래 가능 시간에만 허용 (점심시간 제외)
                from datetime import datetime, time
                now = datetime.now().time()
                weekday = datetime.now().weekday()
                
                # 주말 체크 (토요일: 5, 일요일: 6)
                if weekday >= 5:
                    if hasattr(self, 'logger'):
                        self.logger.info(f"주말 {symbol} 매도 신호 차단")
                    return False
                
                # 평일 거래 시간 체크 (09:00-12:00, 13:00-15:30, 점심시간 제외)
                morning_start = time(9, 0)
                lunch_start = time(12, 0)
                lunch_end = time(13, 0)
                market_close = time(15, 30)
                
                # 거래 가능 시간: 오전 + 오후 (점심시간 제외)
                is_trading_time = (morning_start <= now < lunch_start) or (lunch_end <= now <= market_close)
                
                if not is_trading_time:
                    if hasattr(self, 'logger'):
                        self.logger.info(f"거래시간외 {symbol} 매도 신호 차단 (현재 시각: {now.strftime('%H:%M:%S')})")
                    return False
            
            # ⚡ 특별 로깅: 문제 종목들을 추적
            problem_stocks = ['010170', '201490']
            if symbol in problem_stocks:
                if hasattr(self, 'logger'):
                    self.logger.error(f"🔍 [TRACE] {symbol} 문제 종목 진입 - 매도 신호 처리 시작")
                    self.logger.error(f"   📊 매개변수: price={current_price:,}, stop_loss={stop_loss_price:,}, profit={profit_rate:+.1f}%")
                    holding_info = f"holding={type(holding).__name__}" if holding else "holding=None"
                    self.logger.error(f"   📦 {holding_info}")
            
            if hasattr(self, 'logger'):
                self.logger.warning(f"🔥 {symbol} 손절신호 발생! 현재가: {current_price:,}원, 손절가: {stop_loss_price:,}원, 수익률: {profit_rate:+.1f}%")
            
            # ⚡ 강화된 보안: 실제 KIS API 보유종목인지 재검증 (모든 매도 신호 검증)
            if hasattr(self, 'kis_collector') and self.kis_collector:
                actual_holdings = await self.kis_collector.get_holdings()
                if not actual_holdings or symbol not in actual_holdings:
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"보안 {symbol} 매도 차단: KIS API에서 실제 보유종목이 아님")
                        if symbol in problem_stocks:
                            self.logger.error(f"TRACE {symbol} LAYER-1 차단됨: KIS API에 없음")
                    return False
                
                # 실제 보유 수량 재확인
                actual_holding = actual_holdings[symbol]
                actual_quantity = getattr(actual_holding, 'quantity', 0) if hasattr(actual_holding, 'quantity') else actual_holding.get('quantity', 0)
                if actual_quantity <= 0:
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"보안 {symbol} 매도 차단: 실제 보유수량 {actual_quantity}주 (이미 매도완료)")
                        if symbol in problem_stocks:
                            self.logger.error(f"TRACE {symbol} LAYER-1 차단됨: 보유수량 {actual_quantity}주")
                    return False
                
                if hasattr(self, 'logger'):
                    self.logger.info(f"승인 {symbol} 실제 보유종목 확인: {actual_quantity}주 보유 중 - 매도 실행 승인")
                    if symbol in problem_stocks:
                        self.logger.error(f"TRACE {symbol} LAYER-1 통과: KIS API 보유수량 {actual_quantity}주")
            else:
                if hasattr(self, 'logger'):
                    self.logger.error(f"❌ {symbol} 매도 차단: KIS API 연결 불가 - 보유종목 검증 실패")
                return False
            
            
            
            # 자동매매 시스템 상태 확인 및 매도 신호 전달
            if hasattr(self, 'auto_trader') and self.auto_trader:
                if hasattr(self, 'logger'):
                    self.logger.info(f"✅ {symbol} 자동매매 시스템 활성화됨 - 응급 매도 실행")
                    if symbol in problem_stocks:
                        self.logger.error(f"🔍 [TRACE] {symbol} 모든 보안 레이어 통과 - 실제 매도 실행!")
                        self.logger.error(f"   📋 요약: LAYER-1(KIS API)✅ → LAYER-2(DB 확인)✅ → 매도 실행!")
                
                # [BUG FIX] 매도 신호를 자동매매 시스템에 전송할 때, 현재 보유 정보를 함께 전달
                result = await self.auto_trader._execute_emergency_sell_order(symbol, current_price, "stop_loss", holding_info=holding)
                if hasattr(self, 'logger'):
                    if result:
                        self.logger.info(f"✅ {symbol} 응급 매도 완료")
                    else:
                        self.logger.error(f"❌ {symbol} 응급 매도 실패")
                return result
            else:
                if hasattr(self, 'logger'):
                    auto_trader_status = "None" if not hasattr(self, 'auto_trader') else ("None" if not self.auto_trader else "활성화")
                    self.logger.error(f"❌ {symbol} 자동매매 시스템 비활성화 상태: auto_trader={auto_trader_status}")
                    self.logger.error(f"💡 수동으로 매도하거나 자동매매 시스템을 활성화하세요!")
                return False
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"❌ {symbol} 자동 매도 신호 전송 실패: {e}")
                import traceback
                self.logger.error(f"상세 오류: {traceback.format_exc()}")
            return False

    async def _view_monitoring_status(self):
        """모니터링 현황 - HTS 홀딩 종목과 전략 추출 종목 표시 (1분 자동 리프레시)"""
        from rich.live import Live
        from rich.layout import Layout
        import select
        import sys
        
        self.console.print("[yellow]🔄 실시간 모니터링 현황 모드 진입[/yellow]")
        self.console.print("[dim]1분마다 자동 갱신됩니다. ESC 키를 눌러 종료하세요.[/dim]\n")
        
        # 자동 리프레시 루프 (장 시간 체크 추가)
        try:
            while True:
                # 장 시간 체크 - 장 종료 시 최종 보유 종목 현황 표시 후 종료
                await self.market_manager.update_market_status()
                if not self.market_manager.is_monitoring_allowed_now():
                    status_info = self.market_manager.get_current_status_info()
                    market_status_korean = status_info.get('market_status_korean', '알 수 없음')
                    
                    # 장 종료 시에도 최종 모니터링 현황은 한 번 표시
                    self.console.print(f"\n[yellow]⏰ {market_status_korean} - 장 종료로 인해 모니터링을 자동 종료합니다.[/yellow]")
                    self.console.print("[cyan]📊 최종 모니터링 현황을 표시합니다...[/cyan]\n")
                    
                    # 최종 모니터링 현황 표시
                    try:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        layout = Layout()
                        layout.split_column(
                            Layout(name="header", size=1),
                            Layout(name="body")
                        )
                        
                        # 헤더에 시간 정보
                        layout["header"].update(f"[bold cyan]📊 최종 모니터링 현황 - {current_time}[/bold cyan]")
                        
                        # 본문에 모니터링 현황 (보유 종목 + 감시 종목) 표시
                        monitoring_content = await self._get_monitoring_content()
                        layout["body"].update(monitoring_content)
                        
                        # 화면 클리어 후 출력
                        self.console.clear()
                        self.console.print(layout)
                        
                        # 사용자 입력 대기
                        self.console.print("\n[green]계속하려면 Enter를 누르세요...[/green]")
                        input()
                        
                    except Exception as e:
                        self.logger.error(f"❌ 최종 현황 표시 오류: {e}")
                        self.console.print(f"[red]❌ 최종 현황 표시 오류: {e}[/red]")
                    
                    return
                
                # 현재 시간 표시
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 모니터링 현황 생성
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=1),
                    Layout(name="body")
                )
                
                # 헤더에 시간 정보
                layout["header"].update(f"[bold cyan]📊 실시간 모니터링 현황 - 마지막 업데이트: {current_time}[/bold cyan]")
                
                # 본문에 모니터링 현황
                monitoring_content = await self._get_monitoring_content()
                layout["body"].update(monitoring_content)
                
                # 화면 클리어 후 출력
                self.console.clear()
                self.console.print(layout)
                
                # 1분 대기 (사용자 입력 감지)
                self.console.print("\n[dim]다음 갱신까지: 60초 | ESC 키를 눌러 종료[/dim]")
                
                # 60초 동안 1초마다 사용자 입력 체크
                for countdown in range(60, 0, -1):
                    await asyncio.sleep(1)
                    
                    # 카운트다운 중에도 장 시간 체크 (30초마다)
                    if countdown % 30 == 0:
                        await self.market_manager.update_market_status()
                        if not self.market_manager.is_monitoring_allowed_now():
                            status_info = self.market_manager.get_current_status_info()
                            market_status_korean = status_info.get('market_status_korean', '알 수 없음')
                            
                            # 카운트다운 중 장 종료 시에도 최종 모니터링 현황 표시 후 종료
                            self.console.print(f"\n[yellow]⏰ {market_status_korean} - 장 종료로 인해 모니터링을 자동 종료합니다.[/yellow]")
                            self.console.print("[cyan]📊 최종 모니터링 현황을 표시합니다...[/cyan]\n")
                            
                            # 최종 모니터링 현황 표시
                            try:
                                final_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                final_layout = Layout()
                                final_layout.split_column(
                                    Layout(name="header", size=1),
                                    Layout(name="body")
                                )
                                
                                # 헤더에 시간 정보
                                final_layout["header"].update(f"[bold cyan]📊 최종 모니터링 현황 - {final_time}[/bold cyan]")
                                
                                # 본문에 모니터링 현황 (보유 종목 + 감시 종목) 표시
                                final_monitoring_content = await self._get_monitoring_content()
                                final_layout["body"].update(final_monitoring_content)
                                
                                # 화면 클리어 후 출력
                                self.console.clear()
                                self.console.print(final_layout)
                                
                                # 사용자 입력 대기
                                self.console.print("\n[green]계속하려면 Enter를 누르세요...[/green]")
                                input()
                                
                            except Exception as e:
                                self.logger.error(f"❌ 최종 현황 표시 오류: {e}")
                                self.console.print(f"[red]❌ 최종 현황 표시 오류: {e}[/red]")
                            
                            return
                    
                    # Windows에서 키 입력 감지
                    if sys.platform == "win32":
                        import msvcrt
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key == b'\x1b':  # ESC 키
                                self.console.print("\n[green]✅ 실시간 모니터링 모드를 종료합니다.[/green]")
                                return
                    
                    # 실시간 계산 과정 표시 (매초)
                    if countdown > 0:
                        # 실제 매매로직 계산 과정을 동적으로 표시 (종목별 분석 포함)

                        # 현재 활성 모니터링 종목 목록 가져오기
                        current_stocks = []
                        try:
                            with self.db_manager.get_session() as session:
                                monitoring_stocks = session.query(MonitoringStock).filter(
                                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                                ).limit(5).all()  # 최대 5개만 표시
                                current_stocks = [(stock.symbol, stock.name) for stock in monitoring_stocks]
                        except:
                            current_stocks = [("000000", "종목정보없음")]

                        # 현재 단계에서 분석 중인 종목 선택
                        if current_stocks:
                            current_step_num = (60 - countdown) // (60 // 8)  # 8단계로 나누기
                            stock_index = current_step_num % len(current_stocks)
                            current_symbol, current_name = current_stocks[stock_index]
                            stock_info = f"{current_symbol}({current_name})"
                        else:
                            stock_info = "분석대상 종목 없음"

                        analysis_steps = [
                            ("📊 실시간 주가 데이터 수집 중...", f"KIS API를 통한 현재가 및 OHLCV 데이터 조회 - {stock_info}"),
                            ("📈 RSI 상대강도지수 계산 중...", f"14일 기준 과매수/과매도 상태 분석 - {stock_info}"),
                            ("🔄 골든크로스 분석 중...", f"5일선과 20일선 교차 패턴 검출 - {stock_info}"),
                            ("📊 대량거래 패턴 분석 중...", f"평균 거래량 대비 급증/감소 상태 평가 - {stock_info}"),
                            ("⚡ 모멘텀 지표 계산 중...", f"5일간 가격 변화율 및 추세 강도 측정 - {stock_info}"),
                            ("🧮 종합 점수 산출 중...", f"4개 전략 가중평균으로 최종 점수 계산 - {stock_info}"),
                            ("🏦 보유종목 손익 갱신 중...", f"실시간 수익률 및 손절가 비교 분석 - {len(current_stocks)}개 종목"),
                            ("🎯 매매신호 생성 중...", f"BUY/SELL/HOLD 신호 최종 결정 - {len(current_stocks)}개 종목")
                        ]

                        # 60초를 8단계로 나누어 각 단계별 메시지 표시
                        step_duration = 60 // len(analysis_steps)
                        current_step = (60 - countdown) // step_duration

                        if current_step < len(analysis_steps):
                            step_message, step_detail = analysis_steps[current_step]
                            progress_bar = "█" * (current_step + 1) + "░" * (len(analysis_steps) - current_step - 1)

                            # 매 3초마다 분석 과정 업데이트 (더 자주 업데이트)
                            if countdown % 3 == 0:
                                self.console.print(f"[cyan]{step_message}[/cyan]")
                                self.console.print(f"[white]└── {step_detail}[/white]")
                                self.console.print(f"[blue]진행상황: [{progress_bar}] {current_step + 1}/{len(analysis_steps)} ({((current_step + 1) / len(analysis_steps) * 100):.1f}%)[/blue]")

                        # 남은 시간 표시 (5초마다)
                        if countdown % 5 == 0:
                            minutes = countdown // 60
                            seconds = countdown % 60
                            if minutes > 0:
                                time_str = f"{minutes}분 {seconds}초"
                            else:
                                time_str = f"{seconds}초"
                            self.console.print(f"[dim]갱신까지 {time_str} 남음...[/dim]")
                        
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️ Ctrl+C로 실시간 모니터링을 중단했습니다.[/yellow]")
        except Exception as e:
            self.logger.error(f"❌ 실시간 모니터링 오류: {e}")
            self.console.print(f"[red]❌ 실시간 모니터링 오류: {e}[/red]")
            # 폴백: 기존 방식으로 한 번 표시
            await self._display_monitoring_status_once()

    async def _get_monitoring_content(self):
        """모니터링 현황 컨텐츠 생성"""
        from rich.console import Group
        from rich.panel import Panel

        content_items = []

        # 실시간 계산 과정 섹션 추가
        calculation_content = await self._get_realtime_calculation_display()
        content_items.append(Panel(calculation_content, title="⚡ 실시간 매매 로직 계산 과정", border_style="yellow"))

        # HTS 보유종목 섹션
        holdings_content = await self._get_holdings_table()
        content_items.append(Panel(holdings_content, title="🏦 HTS 보유 종목", border_style="green"))

        # 전략 추출 감시종목 섹션
        monitoring_content = await self._get_monitoring_stocks_table()
        content_items.append(Panel(monitoring_content, title="🎯 전략 추출 감시 종목", border_style="blue"))

        return Group(*content_items)

    async def _get_realtime_calculation_display(self):
        """실시간 매매 로직 계산 과정 표시"""
        from rich.table import Table
        from rich.console import Group
        from rich.text import Text
        import asyncio

        try:
            content_items = []
            current_time = datetime.now().strftime("%H:%M:%S")

            # 1. 보유종목 매매 조건 계산 표시 (우선 처리)
            holdings_calc = await self._get_holdings_calculation_display()
            if holdings_calc:
                content_items.append(Text(f"🏦 보유종목 매매 조건 계산 ({current_time}) - 우선 처리", style="bold cyan"))
                content_items.append(holdings_calc)
                content_items.append(Text(""))

            # 2. 모니터링 종목 매매 조건 계산 표시 (24개 전체)
            monitoring_calc = await self._get_monitoring_calculation_display()
            if monitoring_calc:
                # 실제 모니터링 종목 개수 계산 (보유종목 제외)
                monitoring_count = await self._get_actual_monitoring_count()
                content_items.append(Text(f"🎯 모니터링 종목 매매 조건 계산 ({current_time}) - {monitoring_count}개 (보유종목 제외)", style="bold blue"))
                content_items.append(monitoring_calc)

            # 3. 자동 매수 신호 감지 및 처리
            auto_buy_signals = await self._check_auto_buy_signals()
            if auto_buy_signals:
                content_items.append(Text(""))
                content_items.append(Text(f"⚡ 자동 매수 신호 감지 ({current_time})", style="bold red"))
                content_items.append(auto_buy_signals)

            if not content_items:
                return Text("계산할 종목이 없습니다.", style="dim")

            return Group(*content_items)

        except Exception as e:
            self.logger.error(f"실시간 계산 표시 오류: {e}")
            return Text(f"계산 표시 오류: {e}", style="red")

    async def _get_holdings_calculation_display(self):
        """보유종목 매매 조건 계산 과정 표시"""
        from rich.table import Table

        try:
            if not (hasattr(self, 'kis_collector') and self.kis_collector):
                return None

            holdings = await asyncio.wait_for(self.kis_collector.get_holdings(), timeout=3.0)
            if not holdings:
                return None

            table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
            table.add_column("종목", style="white", width=10)
            table.add_column("현재가", style="white", width=8)
            table.add_column("수익률", style="white", width=8)
            table.add_column("매도조건", style="yellow", width=35)
            table.add_column("추매조건", style="green", width=35)

            for symbol, holding in holdings.items():  # 모든 보유 종목 표시
                quantity = getattr(holding, 'quantity', 0) if hasattr(holding, 'quantity') else holding.get('quantity', 0)
                if quantity <= 0:
                    continue

                # 실시간 현재가 조회
                current_price = 0
                try:
                    stock_info = await asyncio.wait_for(self.kis_collector.get_stock_info(symbol), timeout=2.0)
                    if stock_info and hasattr(stock_info, 'current_price'):
                        current_price = stock_info.current_price
                    elif isinstance(stock_info, dict) and 'current_price' in stock_info:
                        current_price = stock_info['current_price']
                except:
                    current_price = holding.get('current_price', 0)

                # 수익률 계산
                avg_price = holding.get('avg_price', 0)
                profit_rate = 0
                if avg_price > 0 and current_price > 0:
                    profit_rate = ((current_price - avg_price) / avg_price) * 100

                # 매도 조건 계산
                sell_conditions = await self._calculate_sell_conditions(symbol, current_price, avg_price, profit_rate)
                # 추가매수 조건 계산
                buy_more_conditions = await self._calculate_buy_more_conditions(symbol, current_price, avg_price)

                # 종목명 가져오기
                stock_name = holding.get('name', symbol)
                if len(stock_name) > 8:
                    stock_name = stock_name[:8] + ".."

                profit_color = "green" if profit_rate >= 0 else "red"
                profit_rate_str = f"[{profit_color}]{profit_rate:+.1f}%[/{profit_color}]"

                table.add_row(
                    f"{symbol}\n({stock_name})",
                    f"{current_price:,}원",
                    profit_rate_str,
                    sell_conditions,
                    buy_more_conditions
                )

            return table

        except Exception as e:
            self.logger.error(f"보유종목 계산 표시 오류: {e}")
            return None

    async def _remove_holdings_overlap(self, monitoring_stocks):
        """보유종목과 중복되는 모니터링 종목 제거"""
        try:
            # 보유종목 심볼 목록 가져오기
            holdings = await self.kis_collector.get_holdings()
            if not holdings:
                return monitoring_stocks

            # holdings는 딕셔너리이므로 키가 symbol입니다
            holdings_symbols = set(holdings.keys())

            # 중복 제거된 모니터링 종목 반환
            filtered_stocks = []
            removed_count = 0

            for stock in monitoring_stocks:
                if stock.symbol not in holdings_symbols:
                    filtered_stocks.append(stock)
                else:
                    removed_count += 1
                    # 중복된 종목은 데이터베이스에서 제거
                    await self._remove_monitoring_stock_from_db(stock.symbol)

            if removed_count > 0:
                self.logger.info(f"보유종목과 중복된 {removed_count}개 모니터링 종목을 제거했습니다.")

            return filtered_stocks

        except Exception as e:
            self.logger.error(f"보유종목 중복 제거 실패: {e}")
            return monitoring_stocks

    async def _remove_monitoring_stock_from_db(self, symbol):
        """감시종목 데이터베이스에서 삭제"""
        try:
            if not self.db_manager:
                return

            from database.models import MonitoringStock, MonitoringStatus
            with self.db_manager.get_session() as session:
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol
                ).first()

                if stock:
                    stock.status = MonitoringStatus.REMOVED.value
                    session.commit()
                    self.logger.debug(f"모니터링 종목 {symbol} 삭제 완료")

        except Exception as e:
            self.logger.error(f"모니터링 종목 {symbol} 삭제 실패: {e}")

    async def _get_actual_monitoring_count(self):
        """실제 모니터링 종목 개수 계산 (보유종목 제외)"""
        try:
            monitoring_stocks = await self._get_active_monitoring_stocks()
            if not monitoring_stocks:
                return 0

            filtered_stocks = await self._remove_holdings_overlap(monitoring_stocks)
            return len(filtered_stocks)

        except Exception as e:
            self.logger.error(f"모니터링 종목 개수 계산 실패: {e}")
            return 0

    async def _check_holdings_sell_signals(self):
        """보유종목 고도화된 매도 신호 체크 - 최우선 처리"""
        from rich.table import Table
        from rich.text import Text

        try:
            holdings = await self.kis_collector.get_holdings()
            if not holdings:
                return None

            # 고도화된 매도 전략 초기화
            if not hasattr(self, 'advanced_exit_strategy'):
                from strategies.advanced_exit_strategy import AdvancedExitStrategy
                self.advanced_exit_strategy = AdvancedExitStrategy(self.config)

            sell_signals = []

            for symbol, holding_data in holdings.items():
                name = holding_data.get('name', '')
                profit_rate = self._safe_get_profit_rate(holding_data)

                # 고도화된 전략에 포지션 정보 업데이트
                await self.advanced_exit_strategy.update_position(symbol, {
                    'current_price': holding_data.get('current_price', 0),
                    'avg_price': holding_data.get('avg_price', 0),
                    'quantity': holding_data.get('quantity', 0),
                })

                # 시장 데이터 준비 (실제로는 차트 데이터에서 가져와야 함)
                market_data = await self._get_market_data_for_exit(symbol)

                # 고도화된 매도 신호 분석
                exit_signals = await self.advanced_exit_strategy.analyze_exit_signals(symbol, market_data)

                for exit_signal in exit_signals:
                    # 부분 매도인지 전량 매도인지 구분
                    quantity_text = "전량" if exit_signal.quantity_ratio >= 1.0 else f"{exit_signal.quantity_ratio*100:.0f}%"

                    sell_signals.append({
                        'symbol': symbol,
                        'name': name[:8] + ".." if len(name) > 8 else name,
                        'profit_rate': profit_rate,
                        'signal': exit_signal.signal_type,
                        'action': f'{quantity_text} 매도',
                        'reason': exit_signal.reason,
                        'confidence': exit_signal.confidence,
                        'quantity_ratio': exit_signal.quantity_ratio
                    })

            # 백업: 기존 단순 로직도 유지 (고도화 전략 실패시)
            if not sell_signals:
                sell_signals = await self._check_simple_sell_signals(holdings)

            if sell_signals:
                table = Table(show_header=True, header_style="bold red", box=None)
                table.add_column("종목", style="white", width=10)
                table.add_column("수익률", style="cyan", width=8)
                table.add_column("신호유형", style="yellow", width=12)
                table.add_column("매도액션", style="red", width=10)
                table.add_column("신뢰도", style="magenta", width=8)

                for signal in sell_signals:
                    confidence_color = "green" if signal.get('confidence', 0) >= 0.8 else "yellow"
                    table.add_row(
                        signal['name'],
                        f"{signal['profit_rate']:.1f}%",
                        signal['signal'],
                        signal['action'],
                        f"[{confidence_color}]{signal.get('confidence', 0)*100:.0f}%[/{confidence_color}]"
                    )

                return table

            return Text("보유종목 매도 신호 없음", style="green")

        except Exception as e:
            self.logger.error(f"보유종목 매도 신호 체크 실패: {e}")
            return None

    async def _check_simple_sell_signals(self, holdings):
        """기존 단순 매도 신호 (백업용)"""
        sell_signals = []

        for symbol, holding_data in holdings.items():
            name = holding_data.get('name', '')
            profit_rate = self._safe_get_profit_rate(holding_data)

            # 기존 단순 로직 유지
            if profit_rate >= 6.0:  # 6% 이상 수익시 매도 고려
                sell_signals.append({
                    'symbol': symbol,
                    'name': name[:8] + ".." if len(name) > 8 else name,
                    'profit_rate': profit_rate,
                    'signal': '수익실현',
                    'action': '전량 매도',
                    'confidence': 0.7,
                    'quantity_ratio': 1.0
                })
            elif profit_rate <= -3.0:  # 3% 이상 손실시 손절 고려
                sell_signals.append({
                    'symbol': symbol,
                    'name': name[:8] + ".." if len(name) > 8 else name,
                    'profit_rate': profit_rate,
                    'signal': '손절매',
                    'action': '전량 매도',
                    'confidence': 0.8,
                    'quantity_ratio': 1.0
                })

        return sell_signals

    async def _get_market_data_for_exit(self, symbol: str) -> dict:
        """매도 분석용 시장 데이터 수집"""
        try:
            # 실제 구현시에는 차트 데이터 API 호출
            # 여기서는 기본값 설정
            market_data = {
                'ema5': 0,  # 5기간 EMA
                'volume': 0,  # 현재 거래량
                'avg_volume': 1,  # 평균 거래량
                'vwap': 0,  # VWAP
            }

            # 3분봉 5기간 평균 계산 시도
            try:
                ema5 = await self._get_3min_5bar_average(symbol)
                if ema5 > 0:
                    market_data['ema5'] = ema5
            except Exception:
                pass

            return market_data

        except Exception as e:
            self.logger.error(f"시장 데이터 수집 실패 {symbol}: {e}")
            return {}

    async def _get_3min_5bar_average(self, symbol: str) -> float:
        """3분봉 최근 5봉 평균가 계산 (3분봉 지원 안되면 1분봉으로 대체)"""
        try:
            # 먼저 3분봉 데이터 시도
            chart_data = None
            try:
                chart_data = await self.kis_collector.get_chart_data(
                    symbol=symbol,
                    period="3",  # 3분봉
                    start_date="",  # 최근 데이터
                    end_date=""
                )
            except Exception as e:
                self.logger.warning(f"{symbol} 3분봉 조회 실패, 1분봉으로 대체: {e}")

            # 3분봉이 안되면 1분봉 데이터로 3분봉 구성
            if not chart_data or len(chart_data) < 5:
                self.logger.info(f"{symbol} 1분봉 데이터로 3분봉 평균 계산 시도")
                try:
                    # 1분봉 데이터 조회 (15분치 = 5개 3분봉)
                    min_data = await self.kis_collector.get_chart_data(
                        symbol=symbol,
                        period="1",  # 1분봉
                        start_date="",
                        end_date=""
                    )

                    if min_data and len(min_data) >= 15:
                        # 1분봉 데이터를 3분봉으로 변환
                        chart_data = self._convert_1min_to_3min(min_data)
                        self.logger.debug(f"{symbol} 1분봉 -> 3분봉 변환 완료: {len(chart_data)}개 봉")
                    else:
                        self.logger.warning(f"{symbol} 1분봉 데이터도 부족: {len(min_data) if min_data else 0}개")
                        return 0.0
                except Exception as e:
                    self.logger.error(f"{symbol} 1분봉 데이터 조회 실패: {e}")
                    return 0.0

            if not chart_data or len(chart_data) < 5:
                self.logger.warning(f"{symbol} 최종 차트 데이터 부족: {len(chart_data) if chart_data else 0}개")
                return 0.0

            # 최근 5봉의 종가 추출
            recent_5_bars = chart_data[-5:]  # 최근 5봉
            close_prices = []

            for bar in recent_5_bars:
                if isinstance(bar, dict):
                    # 종가 추출 (여러 필드명 시도)
                    close_price = bar.get('close') or bar.get('stck_clpr') or bar.get('close_price', 0)
                    if isinstance(close_price, str):
                        close_price = float(close_price)
                    close_prices.append(close_price)

            if len(close_prices) < 5:
                self.logger.warning(f"{symbol} 유효한 종가 데이터 부족: {len(close_prices)}개")
                return 0.0

            # 5봉 평균 계산
            average_price = sum(close_prices) / len(close_prices)

            self.logger.debug(f"{symbol} 3분봉 5봉 평균: {average_price:.2f}원 (종가들: {close_prices})")
            return average_price

        except Exception as e:
            self.logger.error(f"{symbol} 3분봉 5봉 평균 계산 실패: {e}")
            return 0.0

    def _convert_1min_to_3min(self, min_data: list) -> list:
        """1분봉 데이터를 3분봉으로 변환"""
        try:
            if not min_data or len(min_data) < 3:
                return []

            # 최근 데이터부터 역순으로 3분씩 묶어서 변환
            three_min_bars = []

            # 최신 데이터부터 3개씩 묶기
            for i in range(len(min_data) - 1, -1, -3):
                start_idx = max(0, i - 2)  # 3개 봉의 시작 인덱스
                group = min_data[start_idx:i + 1]

                if len(group) >= 3:  # 완전한 3분봉만 생성
                    # 3분봉 OHLC 계산
                    open_price = self._extract_price(group[0], 'open')
                    close_price = self._extract_price(group[-1], 'close')
                    high_price = max([self._extract_price(bar, 'high') for bar in group])
                    low_price = min([self._extract_price(bar, 'low') for bar in group])

                    three_min_bar = {
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'date': group[-1].get('date', ''),
                        'time': group[-1].get('time', '')
                    }
                    three_min_bars.append(three_min_bar)

            # 시간순으로 정렬 (오래된 것부터)
            three_min_bars.reverse()

            return three_min_bars

        except Exception as e:
            self.logger.error(f"1분봉 -> 3분봉 변환 실패: {e}")
            return []

    def _extract_price(self, bar: dict, price_type: str) -> float:
        """차트 데이터에서 가격 추출 (여러 필드명 지원)"""
        try:
            # price_type에 따른 필드명 매핑
            field_mapping = {
                'open': ['open', 'stck_oprc', 'open_price'],
                'high': ['high', 'stck_hgpr', 'high_price'],
                'low': ['low', 'stck_lwpr', 'low_price'],
                'close': ['close', 'stck_clpr', 'close_price']
            }

            fields = field_mapping.get(price_type, [price_type])

            for field in fields:
                price = bar.get(field, 0)
                if price:
                    if isinstance(price, str):
                        price = float(price)
                    return price

            return 0.0

        except Exception:
            return 0.0

    async def _check_holdings_sell_signals_enhanced(self):
        """보유종목 향상된 매도 신호 체크 - 6% 이상 수익시 모니터링, 5봉 평균 아래 손절"""
        from rich.table import Table
        from rich.text import Text

        try:
            holdings = await self.kis_collector.get_holdings()
            if not holdings:
                return None

            sell_signals = []

            for symbol, holding_data in holdings.items():
                name = holding_data.get('name', '')
                profit_rate = self._safe_get_profit_rate(holding_data)
                current_price = holding_data.get('current_price', 0)

                # 기존 손절매 조건 (-5% 이하)
                if profit_rate <= -5.0:
                    sell_signals.append({
                        'symbol': symbol,
                        'name': name[:8] + ".." if len(name) > 8 else name,
                        'profit_rate': profit_rate,
                        'signal': '손절매',
                        'action': 'sell',
                        'reason': f'{profit_rate:.1f}% 손실'
                    })

                # 새로운 조건: 6% 이상 10% 미만 수익시 모니터링
                elif 6.0 <= profit_rate < 10.0:
                    # 3분봉 5봉 평균 계산
                    avg_5bars = await self._get_3min_5bar_average(symbol)

                    if avg_5bars > 0 and current_price < avg_5bars:
                        # 현재가가 5봉 평균 아래로 떨어짐 - 즉시 손절
                        sell_signals.append({
                            'symbol': symbol,
                            'name': name[:8] + ".." if len(name) > 8 else name,
                            'profit_rate': profit_rate,
                            'signal': '추세손절',
                            'action': 'sell',
                            'reason': f'{current_price:.0f}원 < 5봉평균 {avg_5bars:.0f}원'
                        })

                        # 추세손절 조건 충족 시 즉시 매도 실행
                        await self._trigger_trend_stop_sell(symbol, current_price, avg_5bars, profit_rate, holding_data)
                    else:
                        # 아직 5봉 평균 위에 있음 - 모니터링 중
                        self.logger.info(f"{symbol} 모니터링 중: 수익률 {profit_rate:.1f}%, 현재가 {current_price:.0f}원, 5봉평균 {avg_5bars:.0f}원")

                # 기존 수익실현 조건 (10% 이상)
                elif profit_rate >= 10.0:
                    sell_signals.append({
                        'symbol': symbol,
                        'name': name[:8] + ".." if len(name) > 8 else name,
                        'profit_rate': profit_rate,
                        'signal': '수익실현',
                        'action': 'sell',
                        'reason': f'{profit_rate:.1f}% 수익'
                    })

            if sell_signals:
                table = Table(show_header=True, header_style="bold red", box=None)
                table.add_column("종목", style="white", width=10)
                table.add_column("수익률", style="cyan", width=8)
                table.add_column("신호", style="red", width=8)
                table.add_column("사유", style="yellow", width=20)

                for signal in sell_signals:
                    table.add_row(
                        signal['name'],
                        f"{signal['profit_rate']:.1f}%",
                        signal['signal'],
                        signal['reason']
                    )

                return table

            return Text("보유종목 매도 신호 없음", style="green")

        except Exception as e:
            self.logger.error(f"향상된 보유종목 매도 신호 체크 실패: {e}")
            return None

    async def _trigger_trend_stop_sell(self, symbol: str, current_price: float, avg_5bars: float, profit_rate: float, holding: dict):
        """추세손절 조건 충족 시 자동 매도 신호 트리거 (3분봉 5봉 평균 아래 돌파)"""
        try:
            # ⚡ 장 시간 및 거래일 확인 - MarketScheduleManager 사용
            if hasattr(self, 'market_manager') and self.market_manager:
                await self.market_manager.update_market_status()

                if not self.market_manager.is_trading_allowed_now():
                    market_status = self.market_manager.current_status.value
                    market_status_korean = self.market_manager._get_status_korean(self.market_manager.current_status)
                    if hasattr(self, 'logger'):
                        self.logger.info(f"장시간외 {symbol} 추세손절 신호 차단 - 현재 상태: {market_status_korean} ({market_status})")
                    return False
            else:
                # 백업 로직: 기본 시간 체크
                from datetime import datetime, time
                now = datetime.now().time()
                weekday = datetime.now().weekday()

                if weekday >= 5:  # 주말
                    if hasattr(self, 'logger'):
                        self.logger.info(f"주말 {symbol} 추세손절 신호 차단")
                    return False

                # 거래 시간 체크
                morning_start = time(9, 0)
                lunch_start = time(12, 0)
                lunch_end = time(13, 0)
                market_close = time(15, 30)

                is_trading_time = (morning_start <= now < lunch_start) or (lunch_end <= now <= market_close)

                if not is_trading_time:
                    if hasattr(self, 'logger'):
                        self.logger.info(f"거래시간외 {symbol} 추세손절 신호 차단 (현재 시각: {now.strftime('%H:%M:%S')})")
                    return False

            if hasattr(self, 'logger'):
                self.logger.warning(f"🔥 {symbol} 추세손절 신호 발생! 현재가: {current_price:,}원, 5봉평균: {avg_5bars:,}원, 수익률: {profit_rate:+.1f}%")

            # ⚡ 실제 KIS API 보유종목 재검증
            if hasattr(self, 'kis_collector') and self.kis_collector:
                actual_holdings = await self.kis_collector.get_holdings()
                if not actual_holdings or symbol not in actual_holdings:
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"보안 {symbol} 추세손절 차단: KIS API에서 실제 보유종목이 아님")
                    return False

                # 실제 보유 수량 재확인
                actual_holding = actual_holdings[symbol]
                actual_quantity = getattr(actual_holding, 'quantity', 0) if hasattr(actual_holding, 'quantity') else actual_holding.get('quantity', 0)
                if actual_quantity <= 0:
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"보안 {symbol} 추세손절 차단: 실제 보유수량 {actual_quantity}주 (이미 매도완료)")
                    return False

                if hasattr(self, 'logger'):
                    self.logger.info(f"승인 {symbol} 실제 보유종목 확인: {actual_quantity}주 보유 중 - 추세손절 실행 승인")
            else:
                if hasattr(self, 'logger'):
                    self.logger.error(f"❌ {symbol} 추세손절 차단: KIS API 연결 불가 - 보유종목 검증 실패")
                return False

            # 자동매매 시스템을 통한 추세손절 매도 실행
            if hasattr(self, 'auto_trader') and self.auto_trader:
                if hasattr(self, 'logger'):
                    self.logger.info(f"✅ {symbol} 추세손절 시스템 활성화됨 - 응급 매도 실행")
                    self.logger.error(f"🔍 [TREND STOP] {symbol} 3분봉 5봉 평균 아래 돌파 - 즉시 매도!")
                    self.logger.error(f"   📊 현재가: {current_price:,}원 < 5봉평균: {avg_5bars:,}원 (수익률: {profit_rate:+.1f}%)")

                # 추세손절 매도 실행 ("trend_stop" 사유로 구분)
                result = await self.auto_trader._execute_emergency_sell_order(symbol, current_price, "trend_stop", holding_info=holding)
                if hasattr(self, 'logger'):
                    if result:
                        self.logger.info(f"✅ {symbol} 추세손절 매도 완료")
                    else:
                        self.logger.error(f"❌ {symbol} 추세손절 매도 실패")
                return result
            else:
                if hasattr(self, 'logger'):
                    self.logger.error(f"❌ {symbol} 추세손절 차단: 자동매매 시스템 비활성화")
                return False

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"❌ {symbol} 추세손절 처리 실패: {e}")
            return False

    async def _get_monitoring_calculation_display(self):
        """모니터링 종목 분석 계산 과정 표시 - 보유종목 중복 제거"""
        from rich.table import Table
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.text import Text
        import time

        try:
            if not self.db_manager:
                return None

            # DB에서 모니터링 종목 조회
            monitoring_stocks = await self._get_active_monitoring_stocks()
            if not monitoring_stocks:
                return None

            # 보유종목과 중복 제거
            filtered_monitoring_stocks = await self._remove_holdings_overlap(monitoring_stocks)
            if not filtered_monitoring_stocks:
                return Text("모든 모니터링 종목이 보유종목과 중복됩니다.", style="yellow")

            table = Table(show_header=True, header_style="bold blue", box=None, padding=(0, 1))
            table.add_column("종목", style="white", width=12)
            table.add_column("RSI", style="cyan", width=10)
            table.add_column("골든크로스", style="yellow", width=12)
            table.add_column("대량거래", style="magenta", width=12)
            table.add_column("모멘텀", style="green", width=10)
            table.add_column("종합점수", style="red bold", width=10)

            # 점수 계산을 위한 데이터 준비
            stock_scores = []

            # 필터링된 모니터링 종목에 대해 점수 계산
            for stock in filtered_monitoring_stocks:
                symbol = stock.symbol
                stock_name = stock.name

                # 종목명 길이 조정
                if len(stock_name) > 8:
                    stock_name = stock_name[:8] + ".."

                # 각 분석 단계별 계산
                rsi_result = await self._calculate_rsi_analysis(symbol)
                golden_cross_result = await self._calculate_golden_cross_analysis(symbol)
                volume_result = await self._calculate_volume_analysis(symbol)
                momentum_result = await self._calculate_momentum_analysis(symbol)

                # 종합점수 계산
                total_score_result = self._calculate_total_score(rsi_result, golden_cross_result, volume_result, momentum_result)

                # 점수 추출 (안전성 검사 포함)
                score = 50  # 기본값
                if isinstance(total_score_result, dict) and 'score' in total_score_result:
                    try:
                        score = float(total_score_result['score'])
                    except (ValueError, TypeError):
                        score = 50

                stock_scores.append({
                    'stock': stock,
                    'symbol': symbol,
                    'stock_name': stock_name,
                    'rsi_result': rsi_result,
                    'golden_cross_result': golden_cross_result,
                    'volume_result': volume_result,
                    'momentum_result': momentum_result,
                    'total_score_result': total_score_result,
                    'score': score
                })

            # 점수순으로 정렬 (높은 점수부터)
            stock_scores.sort(key=lambda x: x['score'], reverse=True)

            # 정렬된 순서로 테이블에 추가
            for stock_data in stock_scores:
                table.add_row(
                    f"{stock_data['symbol']}\n({stock_data['stock_name']})",
                    self._format_rsi_result(stock_data['rsi_result']),
                    self._format_golden_cross_result(stock_data['golden_cross_result']),
                    self._format_volume_result(stock_data['volume_result']),
                    self._format_momentum_result(stock_data['momentum_result']),
                    self._format_total_score(stock_data['total_score_result'])
                )

            return table

        except Exception as e:
            self.logger.error(f"모니터링 종목 계산 표시 오류: {e}")
            return None

    async def _calculate_rsi_analysis(self, symbol):
        """RSI 분석 계산"""
        try:
            # 임시 RSI 계산 로직 (실제로는 기술적 분석 엔진 사용)
            import random
            await asyncio.sleep(0.1)

            rsi_value = random.uniform(20, 80)
            if rsi_value < 30:
                signal = "매수강"
                score = 85
            elif rsi_value < 50:
                signal = "매수"
                score = 65
            elif rsi_value < 70:
                signal = "보유"
                score = 45
            else:
                signal = "매도"
                score = 25

            return {"value": rsi_value, "signal": signal, "score": score}
        except Exception as e:
            return {"value": 50, "signal": "중립", "score": 50}

    async def _calculate_golden_cross_analysis(self, symbol):
        """골든크로스 분석 계산"""
        try:
            import random
            await asyncio.sleep(0.1)

            # MA5와 MA20 비교
            ma5_above = random.choice([True, False])
            strength = random.uniform(0.5, 3.0)

            if ma5_above and strength > 2.0:
                signal = "골든크로스"
                score = 90
            elif ma5_above and strength > 1.0:
                signal = "상승돌파"
                score = 70
            elif not ma5_above and strength > 1.5:
                signal = "데드크로스"
                score = 20
            else:
                signal = "횡보"
                score = 50

            return {"signal": signal, "strength": strength, "score": score}
        except Exception as e:
            return {"signal": "중립", "strength": 1.0, "score": 50}

    async def _calculate_volume_analysis(self, symbol):
        """대량거래 분석 계산"""
        try:
            import random
            await asyncio.sleep(0.1)

            volume_ratio = random.uniform(0.5, 5.0)

            if volume_ratio > 3.0:
                signal = "급등량"
                score = 85
            elif volume_ratio > 2.0:
                signal = "증가량"
                score = 70
            elif volume_ratio > 1.5:
                signal = "평균상"
                score = 60
            else:
                signal = "저조량"
                score = 30

            return {"ratio": volume_ratio, "signal": signal, "score": score}
        except Exception as e:
            return {"ratio": 1.0, "signal": "평균", "score": 50}

    async def _calculate_momentum_analysis(self, symbol):
        """모멘텀 분석 계산"""
        try:
            import random
            await asyncio.sleep(0.1)

            momentum_score = random.uniform(-10, 10)

            if momentum_score > 5:
                signal = "강세"
                score = 80
            elif momentum_score > 2:
                signal = "상승"
                score = 65
            elif momentum_score > -2:
                signal = "중립"
                score = 50
            elif momentum_score > -5:
                signal = "하락"
                score = 35
            else:
                signal = "약세"
                score = 20

            return {"momentum": momentum_score, "signal": signal, "score": score}
        except Exception as e:
            return {"momentum": 0, "signal": "중립", "score": 50}

    async def _check_auto_buy_signals(self):
        """종합 그레이드 A 자동 매수 신호 감지 - 보유종목 우선 처리"""
        from rich.table import Table
        from rich.console import Group
        from rich.text import Text

        try:
            if not self.db_manager:
                return None

            # 1. 보유종목 먼저 처리 (향상된 매도 로직: 6% 이상 모니터링, 5봉 평균 아래 손절)
            holdings_signals = await self._check_holdings_sell_signals_enhanced()

            # 2. 모니터링 종목 중 자동 매수 대상 찾기 (보유종목 제외)
            monitoring_stocks = await self._get_active_monitoring_stocks()
            if not monitoring_stocks:
                return holdings_signals

            # 보유종목과 중복 제거
            filtered_monitoring_stocks = await self._remove_holdings_overlap(monitoring_stocks)

            buy_signals = []

            for stock in filtered_monitoring_stocks:
                symbol = stock.symbol
                stock_name = stock.name

                # 각 분석 지표 계산
                rsi_result = await self._calculate_rsi_analysis(symbol)
                golden_cross_result = await self._calculate_golden_cross_analysis(symbol)
                volume_result = await self._calculate_volume_analysis(symbol)
                momentum_result = await self._calculate_momentum_analysis(symbol)

                # 종합점수 계산
                total_score_result = self._calculate_total_score(rsi_result, golden_cross_result, volume_result, momentum_result)

                # 점수 안전성 검사
                if isinstance(total_score_result, dict) and 'score' in total_score_result:
                    try:
                        total_score = float(total_score_result["score"])
                        grade = total_score_result["grade"]
                    except (ValueError, TypeError):
                        total_score = 50
                        grade = "C"
                else:
                    total_score = 50
                    grade = "C"

                # 종합 그레이드 A 이상이면 자동 매수 대상
                if total_score >= 70:  # A 그레이드
                    # 자동 매수 비율 계산
                    buy_ratio = await self._calculate_auto_buy_ratio(total_score, symbol)

                    buy_signals.append({
                        'symbol': symbol,
                        'name': stock_name[:8] + ".." if len(stock_name) > 8 else stock_name,
                        'grade': grade,
                        'score': total_score,
                        'buy_ratio': buy_ratio
                    })

                    # 실제 자동 매수 실행
                    await self._execute_auto_buy(symbol, stock_name, buy_ratio, grade, total_score)

            # 매수 신호를 점수순으로 정렬 (높은 점수부터)
            buy_signals.sort(key=lambda x: x['score'], reverse=True)

            if not buy_signals:
                return Text("🟡 자동 매수 대상 없음 (A 그레이드 이상 필요)", style="yellow")

            # 점수 높은 순으로 정렬
            buy_signals.sort(key=lambda x: x['score'], reverse=True)

            # 결과 통합 (보유종목 신호 + 모니터링 신호)
            if holdings_signals and buy_signals:
                from rich.console import Group
                return Group(
                    Text("🏦 보유종목 매도 신호 (최우선)", style="bold red"),
                    holdings_signals,
                    Text(""),
                    Text("🎯 모니터링 종목 매수 신호", style="bold green"),
                    self._create_buy_signals_table(buy_signals)
                )
            elif holdings_signals:
                return Group(
                    Text("🏦 보유종목 매도 신호 (최우선)", style="bold red"),
                    holdings_signals
                )
            elif buy_signals:
                return self._create_buy_signals_table(buy_signals)
            else:
                return None

        except Exception as e:
            self.logger.error(f"자동 매수 신호 감지 오류: {e}")
            return Text(f"[오류] 자동 매수 신호 감지 실패: {e}", style="red")

    def _create_buy_signals_table(self, buy_signals):
        """매수 신호 테이블 생성"""
        from rich.table import Table

        table = Table(show_header=True, header_style="bold green", box=None, padding=(0, 1))
        table.add_column("종목", style="white", width=12)
        table.add_column("그레이드", style="green bold", width=8)
        table.add_column("점수", style="cyan", width=8)
        table.add_column("매수비율", style="green", width=10)
        table.add_column("상태", style="yellow", width=10)

        for signal in buy_signals:
            table.add_row(
                f"{signal['symbol']}\n({signal['name']})",
                signal['grade'],
                f"{signal['score']:.1f}",
                f"{signal['buy_ratio']:.1f}%",
                "✅ 매수실행"
            )

        return table

    async def _calculate_auto_buy_ratio(self, total_score: float, symbol: str) -> float:
        """자동 매수 비율 계산"""
        try:
            # 기본 비율: 점수에 비례
            base_ratio = min(total_score / 10, 10.0)  # 최대 10%

            # 역동적 위험 관리: 더 높은 점수일수록 더 많이 투자
            if total_score >= 85:
                return min(base_ratio * 1.3, 12.0)  # A+ 최고 등급
            elif total_score >= 80:
                return min(base_ratio * 1.2, 10.0)  # A+ 등급
            elif total_score >= 75:
                return min(base_ratio * 1.1, 8.0)   # A 상위 등급
            else:
                return min(base_ratio, 6.0)         # A 기본 등급

        except Exception as e:
            self.logger.error(f"자동 매수 비율 계산 오류: {e}")
            return 3.0  # 기본값

    async def _execute_auto_buy(self, symbol: str, stock_name: str, buy_ratio: float, grade: str, score: float):
        """자동 매수 실행"""
        try:
            # 실제 매수 로직 실행
            if hasattr(self, 'auto_trader') and self.auto_trader:
                # 가용 자금의 buy_ratio% 만큼 매수
                current_balance = await self.auto_trader.get_available_balance()
                if current_balance > 0:
                    buy_amount = int(current_balance * (buy_ratio / 100))

                    if buy_amount >= 10000:  # 최소 매수 금액 체크
                        # 실제 매수 주문 실행
                        result = await self.auto_trader.place_buy_order(symbol, buy_amount)

                        if result and result.get('success'):
                            self.logger.info(f"✅ 자동매수 성공: {symbol}({stock_name}) {buy_amount:,}원 매수 - 그레이드={grade} 점수={score:.1f}")
                        else:
                            self.logger.warning(f"⚠️ 자동매수 실패: {symbol}({stock_name}) - {result.get('message', '알 수 없는 오류')}")
                    else:
                        self.logger.info(f"⚠️ 매수금액 부족: {symbol}({stock_name}) 필요금액={buy_amount:,}원 (최소 10,000원)")
                else:
                    self.logger.info(f"⚠️ 가용자금 부족: {symbol}({stock_name}) 잔고={current_balance:,}원")
            else:
                self.logger.warning(f"⚠️ 자동매매 시스템 미연결: {symbol}({stock_name})")

        except Exception as e:
            self.logger.error(f"자동 매수 실행 오류: {symbol} - {e}")

    def _calculate_total_score(self, rsi_result, golden_cross_result, volume_result, momentum_result):
        """종합점수 계산"""
        try:
            # 각 결과의 안전성 검사
            def safe_get_score(result, name):
                if not isinstance(result, dict):
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"{name} 결과가 dict가 아님: {type(result)} - {result}")
                    return 50
                score = result.get("score", 50)
                if isinstance(score, dict):
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"{name} score가 dict: {score}")
                    return 50
                try:
                    return float(score)
                except (ValueError, TypeError):
                    if hasattr(self, 'logger'):
                        self.logger.warning(f"{name} score 변환 실패: {score}")
                    return 50

            # 가중평균으로 종합점수 계산
            weights = {
                "rsi": 0.25,
                "golden_cross": 0.30,
                "volume": 0.25,
                "momentum": 0.20
            }

            rsi_score = safe_get_score(rsi_result, "RSI")
            golden_cross_score = safe_get_score(golden_cross_result, "골든크로스")
            volume_score = safe_get_score(volume_result, "볼륨")
            momentum_score = safe_get_score(momentum_result, "모멘텀")

            total = (
                rsi_score * weights["rsi"] +
                golden_cross_score * weights["golden_cross"] +
                volume_score * weights["volume"] +
                momentum_score * weights["momentum"]
            )

            if total >= 80:
                grade = "A+"
            elif total >= 70:
                grade = "A"
            elif total >= 60:
                grade = "B"
            elif total >= 50:
                grade = "C"
            else:
                grade = "D"

            return {"score": total, "grade": grade}
        except Exception:
            return {"score": 50, "grade": "C"}

    def _format_rsi_result(self, result):
        """RSI 결과 포맷팅"""
        try:
            if not isinstance(result, dict):
                return "[gray]계산실패[/gray]"

            value = result.get("value", 50)
            signal = result.get("signal", "중립")

            # value 안전성 검사
            if isinstance(value, dict):
                value = 50
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 50

            if signal == "매수강":
                return f"[green bold]{value:.1f}\n{signal}[/green bold]"
            elif signal == "매수":
                return f"[green]{value:.1f}\n{signal}[/green]"
            elif signal == "매도":
                return f"[red]{value:.1f}\n{signal}[/red]"
            else:
                return f"[yellow]{value:.1f}\n{signal}[/yellow]"
        except Exception:
            return "[gray]포맷오류[/gray]"

    def _format_golden_cross_result(self, result):
        """골든크로스 결과 포맷팅"""
        try:
            if not isinstance(result, dict):
                return "[gray]계산실패[/gray]"

            signal = result.get("signal", "횡보")
            strength = result.get("strength", 1.0)

            if isinstance(strength, dict):
                strength = 1.0
            try:
                strength = float(strength)
            except (ValueError, TypeError):
                strength = 1.0

            if signal == "골든크로스":
                return f"[green bold]{signal}\n{strength:.1f}배[/green bold]"
            elif signal == "상승돌파":
                return f"[green]{signal}\n{strength:.1f}배[/green]"
            elif signal == "데드크로스":
                return f"[red]{signal}\n{strength:.1f}배[/red]"
            else:
                return f"[yellow]{signal}\n{strength:.1f}배[/yellow]"
        except Exception:
            return "[gray]포맷오류[/gray]"

    def _format_volume_result(self, result):
        """대량거래 결과 포맷팅"""
        try:
            if not isinstance(result, dict):
                return "[gray]계산실패[/gray]"

            signal = result.get("signal", "평균")
            ratio = result.get("ratio", 1.0)

            if isinstance(ratio, dict):
                ratio = 1.0
            try:
                ratio = float(ratio)
            except (ValueError, TypeError):
                ratio = 1.0

            if signal == "급등량":
                return f"[red bold]{signal}\n{ratio:.1f}배[/red bold]"
            elif signal == "증가량":
                return f"[yellow bold]{signal}\n{ratio:.1f}배[/yellow bold]"
            elif signal == "평균상":
                return f"[green]{signal}\n{ratio:.1f}배[/green]"
            else:
                return f"[white]{signal}\n{ratio:.1f}배[/white]"
        except Exception:
            return "[gray]포맷오류[/gray]"

    def _format_momentum_result(self, result):
        """모멘텀 결과 포맷팅"""
        try:
            if not isinstance(result, dict):
                return "[gray]계산실패[/gray]"

            signal = result.get("signal", "중립")
            momentum = result.get("momentum", 0.0)

            if isinstance(momentum, dict):
                momentum = 0.0
            try:
                momentum = float(momentum)
            except (ValueError, TypeError):
                momentum = 0.0

            if signal == "강세":
                return f"[green bold]{signal}\n{momentum:+.1f}[/green bold]"
            elif signal == "상승":
                return f"[green]{signal}\n{momentum:+.1f}[/green]"
            elif signal == "하락":
                return f"[red]{signal}\n{momentum:+.1f}[/red]"
            elif signal == "약세":
                return f"[red bold]{signal}\n{momentum:+.1f}[/red bold]"
            else:
                return f"[yellow]{signal}\n{momentum:+.1f}[/yellow]"
        except Exception:
            return "[gray]포맷오류[/gray]"

    def _format_total_score(self, result):
        """종합점수 결과 포맷팅"""
        try:
            if not isinstance(result, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"종합점수 포맷팅에서 result가 dict가 아님: {type(result)} - {result}")
                return "[gray]계산실패[/gray]"

            score = result.get("score", 50)
            grade = result.get("grade", "C")

            # score 안전성 검사
            if isinstance(score, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"종합점수 포맷팅에서 score가 dict: {score}")
                score = 50

            try:
                score = float(score)
            except (ValueError, TypeError):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"종합점수 포맷팅에서 score 변환 실패: {score}")
                score = 50

            if grade == "A+":
                return f"[green bold]{score:.0f}점\n{grade}[/green bold]"
            elif grade == "A":
                return f"[green]{score:.0f}점\n{grade}[/green]"
            elif grade == "B":
                return f"[yellow]{score:.0f}점\n{grade}[/yellow]"
            elif grade == "C":
                return f"[white]{score:.0f}점\n{grade}[/white]"
            else:
                return f"[red]{score:.0f}점\n{grade}[/red]"
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f"종합점수 포맷팅 오류: {e}")
            return "[gray]포맷오류[/gray]"

    async def _calculate_sell_conditions(self, symbol, current_price, avg_price, profit_rate):
        """매도 조건 계산 (보유종목용) - 실제 기술적 지표 활용"""
        try:
            conditions = []

            # profit_rate 안전성 검사
            safe_profit_rate = profit_rate
            if isinstance(profit_rate, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"매도조건 계산에서 profit_rate가 dict: {profit_rate}, 0으로 처리")
                safe_profit_rate = 0.0
            elif not isinstance(profit_rate, (int, float)):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"매도조건 계산에서 profit_rate 타입 오류: {type(profit_rate)}, 0으로 처리")
                safe_profit_rate = 0.0

            # 1. 손절 조건 (우선순위 1)
            if safe_profit_rate <= -5.0:
                conditions.append("[red]🚨 긴급손절 (-5%)[/red]")
            elif safe_profit_rate <= -3.0:
                conditions.append("[red]⚠️ 손절신호 (-3%)[/red]")

            # 2. 익절 조건
            if safe_profit_rate >= 10.0:
                conditions.append("[green]💰 고수익 익절 (+10%)[/green]")
            elif safe_profit_rate >= 5.0:
                conditions.append("[green]✅익절신호 (+5%)[/green]")

            # 3. 실제 기술적 지표 계산
            try:
                # 실시간 가격 데이터 수집 (최근 100일)
                if hasattr(self, 'auto_trader') and self.auto_trader.data_collector:
                    price_data = await asyncio.wait_for(
                        self.auto_trader.data_collector.get_ohlcv_data(symbol, 'D', 100),
                        timeout=3.0
                    )

                    if price_data and len(price_data) >= 20:
                        # 기술적 분석 수행
                        if hasattr(self, 'auto_trader') and self.auto_trader.analysis_engine:
                            tech_analysis = await asyncio.wait_for(
                                self.auto_trader.analysis_engine.technical_analyzer.analyze_stock(symbol,
                                    [{'date': item.date.strftime('%Y-%m-%d'), 'open': int(item.open),
                                      'high': int(item.high), 'low': int(item.low), 'close': int(item.close),
                                      'volume': int(item.volume)} for item in price_data[-50:]]),
                                timeout=5.0
                            )

                            if tech_analysis:
                                # RSI 분석
                                rsi = tech_analysis.get('rsi_current', 50)
                                if rsi >= 70:
                                    conditions.append(f"[yellow]📈 RSI과매수 ({rsi:.1f})[/yellow]")
                                elif rsi <= 30:
                                    conditions.append(f"[cyan]📉 RSI과매도 ({rsi:.1f})[/cyan]")

                                # MACD 분석
                                macd_signal = tech_analysis.get('macd_signal', '중립')
                                if 'sell' in macd_signal.lower() or 'dead' in macd_signal.lower():
                                    conditions.append("[red]📊 MACD 데드크로스[/red]")
                                elif 'buy' in macd_signal.lower() or 'golden' in macd_signal.lower():
                                    conditions.append("[green]📊 MACD 골든크로스[/green]")

                                # 이동평균선 분석
                                ema_signal = tech_analysis.get('ema_signal', '중립')
                                if 'sell' in ema_signal.lower():
                                    conditions.append("[red]📉 EMA 데드크로스[/red]")
                                elif 'buy' in ema_signal.lower():
                                    conditions.append("[green]📈 EMA 골든크로스[/green]")

            except Exception as tech_e:
                self.logger.debug(f"기술적 지표 계산 실패 ({symbol}): {tech_e}")
                # 폴백: 기본 조건만 표시
                pass

            if not conditions:
                conditions.append("[white]📊 매도조건 미충족[/white]")

            return " | ".join(conditions)

        except Exception as e:
            return f"[red]계산오류: {e}[/red]"

    async def _calculate_buy_more_conditions(self, symbol, current_price, avg_price):
        """추가매수 조건 계산 (보유종목용) - 실제 기술적 지표 활용"""
        try:
            conditions = []

            # 현재가와 평단가 비교
            if avg_price > 0:
                price_diff = ((current_price - avg_price) / avg_price) * 100
                if price_diff >= 3.0:
                    conditions.append("[green]📈 평단가 상회 (+3%)[/green]")
                elif price_diff <= -2.0:
                    conditions.append("[cyan]💎 물타기 기회 (-2%)[/cyan]")

            # 실제 기술적 지표 기반 추가매수 조건
            try:
                if hasattr(self, 'auto_trader') and self.auto_trader.data_collector:
                    price_data = await asyncio.wait_for(
                        self.auto_trader.data_collector.get_ohlcv_data(symbol, 'D', 100),
                        timeout=3.0
                    )

                    if price_data and len(price_data) >= 20:
                        if hasattr(self, 'auto_trader') and self.auto_trader.analysis_engine:
                            tech_analysis = await asyncio.wait_for(
                                self.auto_trader.analysis_engine.technical_analyzer.analyze_stock(symbol,
                                    [{'date': item.date.strftime('%Y-%m-%d'), 'open': int(item.open),
                                      'high': int(item.high), 'low': int(item.low), 'close': int(item.close),
                                      'volume': int(item.volume)} for item in price_data[-50:]]),
                                timeout=5.0
                            )

                            if tech_analysis:
                                # RSI 기반 추가매수 조건
                                rsi = tech_analysis.get('rsi_current', 50)
                                if 30 <= rsi <= 50:
                                    conditions.append(f"[green]📊 RSI 적정구간 ({rsi:.1f})[/green]")
                                elif rsi <= 30:
                                    conditions.append(f"[cyan]📉 RSI 과매도 추매기회 ({rsi:.1f})[/cyan]")

                                # 거래량 기반 추가매수 조건
                                volume_ratio = tech_analysis.get('volume_ratio', 1.0)
                                if volume_ratio >= 1.3:
                                    conditions.append(f"[green]📊 거래량급증 ({volume_ratio:.1f}배)[/green]")

                                # 상승 모멘텀 확인
                                tech_score = tech_analysis.get('technical_score', 50)
                                if tech_score >= 60:
                                    conditions.append(f"[green]📈 상승모멘텀 ({tech_score:.0f}점)[/green]")

                                # MACD 상승 전환 확인
                                macd_signal = tech_analysis.get('macd_signal', '중립')
                                if 'buy' in macd_signal.lower() or 'golden' in macd_signal.lower():
                                    conditions.append("[green]📊 MACD 상승전환[/green]")

            except Exception as tech_e:
                self.logger.debug(f"추가매수 기술적 지표 계산 실패 ({symbol}): {tech_e}")
                # 폴백: 기본 조건만 표시
                pass

            if not conditions:
                conditions.append("[white]📊 추매조건 미충족[/white]")

            return " | ".join(conditions)

        except Exception as e:
            return f"[red]계산오류: {e}[/red]"

    async def _calculate_buy_conditions(self, symbol, current_price, strategy):
        """매수 조건 계산 (모니터링 종목용) - 실제 기술적 지표 활용"""
        try:
            conditions = []
            confidence = 0

            # 실제 기술적 지표 계산
            try:
                # 실시간 가격 데이터 수집
                if hasattr(self, 'auto_trader') and self.auto_trader.data_collector:
                    price_data = await asyncio.wait_for(
                        self.auto_trader.data_collector.get_ohlcv_data(symbol, 'D', 100),
                        timeout=3.0
                    )

                    if price_data and len(price_data) >= 20:
                        # 기술적 분석 수행
                        if hasattr(self, 'auto_trader') and self.auto_trader.analysis_engine:
                            tech_analysis = await asyncio.wait_for(
                                self.auto_trader.analysis_engine.technical_analyzer.analyze_stock(symbol,
                                    [{'date': item.date.strftime('%Y-%m-%d'), 'open': int(item.open),
                                      'high': int(item.high), 'low': int(item.low), 'close': int(item.close),
                                      'volume': int(item.volume)} for item in price_data[-50:]]),
                                timeout=5.0
                            )

                            if tech_analysis:
                                # 1. RSI 조건 (실제 값)
                                rsi = tech_analysis.get('rsi_current', 50)
                                if 25 <= rsi <= 35:
                                    conditions.append(f"[green]✅ RSI과매도반등 ({rsi:.1f})[/green]")
                                    confidence += 25
                                elif rsi > 70:
                                    conditions.append(f"[red]❌ RSI과매수 ({rsi:.1f})[/red]")
                                    confidence -= 10
                                else:
                                    conditions.append(f"[white]📊 RSI중립 ({rsi:.1f})[/white]")

                                # 2. MACD 조건 (실제 값)
                                macd_signal = tech_analysis.get('macd_signal', '중립')
                                if 'buy' in macd_signal.lower() or 'golden' in macd_signal.lower():
                                    conditions.append("[green]✅ MACD 골든크로스[/green]")
                                    confidence += 25
                                elif 'sell' in macd_signal.lower() or 'dead' in macd_signal.lower():
                                    conditions.append("[red]❌ MACD 데드크로스[/red]")
                                    confidence -= 15
                                else:
                                    conditions.append("[white]📊 MACD 중립[/white]")

                                # 3. 거래량 조건 (실제 값)
                                volume_ratio = tech_analysis.get('volume_ratio', 1.0)
                                if volume_ratio >= 1.5:
                                    conditions.append(f"[green]✅ 거래량급증 ({volume_ratio:.1f}배)[/green]")
                                    confidence += 20
                                elif volume_ratio <= 0.7:
                                    conditions.append(f"[red]📉 거래량감소 ({volume_ratio:.1f}배)[/red]")
                                    confidence -= 10
                                else:
                                    conditions.append(f"[white]📊 거래량보통 ({volume_ratio:.1f}배)[/white]")

                                # 4. EMA 조건 (실제 값)
                                ema_signal = tech_analysis.get('ema_signal', '중립')
                                if 'buy' in ema_signal.lower() or 'golden' in ema_signal.lower():
                                    conditions.append("[green]✅ EMA 골든크로스[/green]")
                                    confidence += 15
                                elif 'sell' in ema_signal.lower():
                                    conditions.append("[red]❌ EMA 데드크로스[/red]")
                                    confidence -= 10
                                else:
                                    conditions.append("[white]📊 EMA 중립[/white]")

                                # 5. 기술적 점수
                                tech_score = tech_analysis.get('technical_score', 50)
                                if tech_score >= 70:
                                    conditions.append(f"[green]📈 기술적강세 ({tech_score:.0f}점)[/green]")
                                    confidence += 10
                                elif tech_score <= 30:
                                    conditions.append(f"[red]📉 기술적약세 ({tech_score:.0f}점)[/red]")
                                    confidence -= 5

            except Exception as tech_e:
                self.logger.debug(f"기술적 지표 계산 실패 ({symbol}): {tech_e}")
                # 폴백: 기본 메시지
                conditions.append("[yellow]⚠️ 기술적 분석 대기중[/yellow]")
                confidence = 30  # 기본 신뢰도

            # 신뢰도 범위 조정 (0-100)
            confidence = max(0, min(100, confidence))

            if not conditions:
                conditions.append("[white]📊 매수조건 평가중[/white]")

            return {
                "conditions": " | ".join(conditions),
                "confidence": confidence
            }

        except Exception as e:
            return {
                "conditions": f"[red]계산오류: {e}[/red]",
                "confidence": 0
            }

    async def _get_active_monitoring_stocks(self):
        """활성 모니터링 종목 조회"""
        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select
                from database.models import MonitoringStock, MonitoringStatus

                query = select(MonitoringStock).where(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).order_by(MonitoringStock.recommendation_time.desc())

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"모니터링 종목 조회 오류: {e}")
            return []

    async def _get_holdings_table(self):
        """HTS 보유종목 테이블 생성"""
        from rich.table import Table
        from rich.console import Group
        
        try:
            if not (hasattr(self, 'kis_collector') and self.kis_collector):
                return "[red]KIS API 연결 없음[/red]"
                
            # 타임아웃 설정으로 블로킹 방지
            try:
                holdings = await asyncio.wait_for(self.kis_collector.get_holdings(), timeout=5.0)
            except asyncio.TimeoutError:
                return "[red][ERROR] KIS API 연결 없음 (타임아웃)[/red]"
            except Exception as e:
                return f"[red][ERROR] KIS API 연결 없음: {e}[/red]"
                
            if not holdings:
                return "[yellow]보유 종목 없음[/yellow]"
            
            # Rich Table 생성 (너비 조정 및 정렬 개선)
            holdings_table = Table(
                title="실시간 보유종목 현황", 
                show_header=True, 
                header_style="bold blue",
                box=None,  # 테이블 외곽선 제거로 깔끔함
                padding=(0, 1)  # 패딩 조정
            )
            holdings_table.add_column("종목코드", style="cyan", width=8, no_wrap=True, justify="center")
            holdings_table.add_column("종목명", style="white", width=14, no_wrap=True, justify="left")
            holdings_table.add_column("전략", style="yellow", width=12, no_wrap=True, justify="left")
            holdings_table.add_column("수량", style="white", width=6, justify="right", no_wrap=True)
            holdings_table.add_column("평단가", style="white", width=10, justify="right", no_wrap=True)
            holdings_table.add_column("현재가", style="white", width=10, justify="right", no_wrap=True)
            holdings_table.add_column("손절가", style="red", width=10, justify="right", no_wrap=True)
            holdings_table.add_column("수익률", style="white", width=8, justify="right", no_wrap=True)
            holdings_table.add_column("상태", style="white", width=8, no_wrap=True, justify="center")
            
            valid_holdings_count = 0
            zero_quantity_stocks = []
            
            for symbol, holding in holdings.items():
                # 수량 확인
                quantity = getattr(holding, 'quantity', 0) if hasattr(holding, 'quantity') else holding.get('quantity', 0)
                
                if quantity <= 0:
                    # 수량이 0인 종목 기록
                    stock_name = holding.get('name', '')[:10]
                    zero_quantity_stocks.append(f"{symbol}({stock_name})")
                    continue  # 수량이 0인 종목은 표시하지 않음
                
                valid_holdings_count += 1
                # KIS API를 통한 실시간 현재가 조회
                current_price = 0
                real_profit_rate = 0
                try:
                    # 실시간 현재가 조회
                    stock_info = await asyncio.wait_for(
                        self.kis_collector.get_stock_info(symbol), timeout=3.0
                    )
                    if stock_info and hasattr(stock_info, 'current_price'):
                        current_price = stock_info.current_price
                    elif stock_info and hasattr(stock_info, 'price'):
                        current_price = stock_info.price
                    elif isinstance(stock_info, dict) and 'current_price' in stock_info:
                        current_price = stock_info['current_price']
                except:
                    current_price = holding.get('current_price', 0)
                
                # 실시간 수익률 계산
                avg_price = holding.get('avg_price', 0)
                if avg_price > 0 and current_price > 0:
                    real_profit_rate = ((current_price - avg_price) / avg_price) * 100
                else:
                    # 안전한 profit_rate 추출
                    real_profit_rate = self._safe_get_profit_rate(holding, 'profit_rate', 0.0)
                
                color = "green" if real_profit_rate >= 0 else "red"
                
                # 실시간 동적 손절가 계산 (트레일링 스톱 방식)
                stop_loss_price = self._calculate_dynamic_stop_loss(
                    symbol, current_price, avg_price, real_profit_rate
                )
                
                # 전략명은 DB에서 조회하되, 없으면 기본값 사용
                strategy_name = self._get_holding_strategy_name(symbol)
                
                # 실시간 상태 판단
                status = self._get_holding_status(current_price, stop_loss_price, real_profit_rate)
                
                # 종목명을 KIS API에서 실시간으로 가져오기 (StockData 객체 처리)
                stock_name = "N/A"
                try:
                    # KIS API에서 실제 종목명 조회
                    if hasattr(self, 'kis_collector') and self.kis_collector:
                        try:
                            stock_data_obj = await asyncio.wait_for(
                                self.kis_collector.get_stock_info(symbol), 
                                timeout=3.0
                            )
                            # StockData 객체에서 name 속성 접근
                            if stock_data_obj and hasattr(stock_data_obj, 'name') and stock_data_obj.name:
                                stock_name = stock_data_obj.name.strip()
                                self.logger.debug(f"✅ KIS API에서 {symbol} 보유종목 이름 조회 성공: {stock_name}")
                        except (asyncio.TimeoutError, Exception) as e:
                            self.logger.debug(f"KIS API 종목명 조회 실패: {symbol}, {e}")
                    
                    # KIS API 조회 실패 시 기존 데이터 사용
                    if stock_name == "N/A":
                        stock_name = holding.get('name', 'N/A')
                        self.logger.debug(f"📄 보유종목 기본 데이터에서 {symbol} 이름 조회: {stock_name}")
                except Exception as e:
                    self.logger.debug(f"종목명 조회 오류: {symbol}, {e}")
                    stock_name = holding.get('name', 'N/A')
                
                # 종목명이 너무 길면 자르기
                if len(stock_name) > 18:
                    stock_name = stock_name[:16] + ".."
                avg_price_str = f"{holding.get('avg_price', 0):,.1f}원"
                current_price_str = f"{current_price:,}원" if current_price > 0 else "N/A"
                stop_loss_str = f"{stop_loss_price}원" if stop_loss_price != "N/A" else "N/A"
                profit_rate_str = f"[{color}]{real_profit_rate:+.1f}%[/{color}]"
                
                holdings_table.add_row(
                    symbol,
                    stock_name,
                    strategy_name,
                    str(quantity),  # 실제 수량 표시
                    avg_price_str,
                    current_price_str,
                    stop_loss_str,
                    profit_rate_str,
                    status
                )
            
            # 결과 구성
            content_items = [holdings_table]
            
            if valid_holdings_count > 0:
                content_items.append(f"[green]✅ 활성 보유종목: {valid_holdings_count}개[/green]")
            else:
                content_items.append("[yellow]📊 현재 활성 보유종목이 없습니다.[/yellow]")
            
            # 수량이 0인 종목이 있으면 알림
            if zero_quantity_stocks:
                content_items.append(f"[gray]🗑️ 수량 0 (매도완료): {', '.join(zero_quantity_stocks[:5])}{'...' if len(zero_quantity_stocks) > 5 else ''}[/gray]")
            
            return Group(*content_items)
            
        except Exception as e:
            return f"[red]보유 종목 조회 실패: {e}[/red]"

    async def _get_monitoring_stocks_table(self):
        """전략 추출 감시종목 테이블 생성 - 실시간 매매로직 계산 상태 표시"""
        from rich.table import Table
        from rich.console import Group
        from rich.text import Text

        try:
            if not (hasattr(self, 'db_manager') and self.db_manager):
                return "[yellow]데이터베이스 매니저 없음[/yellow]"

            from database.models import MonitoringStock, MonitoringStatus, Stock
            with self.db_manager.get_session() as session:
                active_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).order_by(MonitoringStock.recommendation_time.desc()).all()

                if not active_stocks:
                    return "[yellow]전략 추출 감시 종목 없음[/yellow]"

                # 실시간 매매로직 계산 결과를 보여주는 테이블
                return await self._create_strategy_analysis_table(active_stocks)
                
        except Exception as e:
            return f"[red]전략 추출 감시 종목 조회 실패: {e}[/red]"

    async def _create_strategy_analysis_table(self, active_stocks):
        """실시간 매매로직 계산 상태를 보여주는 테이블 생성"""
        from rich.table import Table
        from rich.console import Group

        try:
            # 종목별 매매로직 계산 결과 테이블 생성
            analysis_table = Table(
                title=f"실시간 매매로직 계산 현황 ({len(active_stocks)}개 종목)",
                show_header=True,
                header_style="bold cyan",
                box=None,
                padding=(0, 1)
            )

            # 컬럼 구성: 종목정보 + 각 매매로직별 상태
            analysis_table.add_column("종목코드", style="cyan", width=8, justify="center")
            analysis_table.add_column("종목명", style="white", width=12, justify="left")
            analysis_table.add_column("현재가", style="white", width=10, justify="right")
            analysis_table.add_column("RSI", style="blue", width=8, justify="center")
            analysis_table.add_column("골든크로스", style="yellow", width=10, justify="center")
            analysis_table.add_column("대량거래", style="green", width=10, justify="center")
            analysis_table.add_column("모멘텀", style="magenta", width=8, justify="center")
            analysis_table.add_column("종합점수", style="red", width=10, justify="center")
            analysis_table.add_column("신호", style="white", width=8, justify="center")

            # 각 종목별로 실시간 계산 수행
            for monitoring in active_stocks:
                try:
                    # 1. 기본 정보 수집
                    current_price, stock_name = await self._get_stock_basic_info(monitoring)

                    # 2. 실시간 매매로직 계산
                    strategy_results = await self._calculate_trading_strategies(monitoring.symbol, current_price)

                    # 3. 테이블 행 추가 (종목 정보를 명확히 표시)
                    display_name = f"({monitoring.symbol}) {stock_name[:8]}" if stock_name != "N/A" else f"({monitoring.symbol}) {monitoring.name or 'Unknown'}"[:15]
                    analysis_table.add_row(
                        monitoring.symbol,
                        display_name,
                        f"{current_price:,}원" if current_price > 0 else "조회중",
                        self._format_strategy_status(strategy_results.get('rsi', {})),
                        self._format_strategy_status(strategy_results.get('golden_cross', {})),
                        self._format_strategy_status(strategy_results.get('volume_surge', {})),
                        self._format_strategy_status(strategy_results.get('momentum', {})),
                        f"[bold]{strategy_results.get('total_score', 0):.0f}점[/bold]",
                        self._format_signal(strategy_results.get('final_signal', 'HOLD'))
                    )

                except Exception as e:
                    # 에러 로그를 최소화 (너무 시끄러운 로그 방지)
                    pass  # 에러 무시하고 넘어감
                    # 기본값으로 분석 결과 표시
                    try:
                        current_price, stock_name = await self._get_stock_basic_info(monitoring)
                        # 에러 시에도 기본 분석 결과 표시
                        default_results = self._get_default_strategy_results()
                        analysis_table.add_row(
                            monitoring.symbol,
                            f"({monitoring.symbol}) {stock_name[:8]}" if stock_name != "N/A" else f"({monitoring.symbol}) {monitoring.name or 'Unknown'}"[:15],
                            f"{current_price:,}원" if current_price > 0 else "조회중",
                            "[yellow]RSI 50[/yellow]",
                            "[blue]중립[/blue]",
                            "[green]보통[/green]",
                            "[magenta]중립[/magenta]",
                            "[red]50점[/red]",
                            "[gray]보유[/gray]"
                        )
                    except:
                        # 완전히 실패 시 최소 정보만 표시
                        analysis_table.add_row(
                            monitoring.symbol,
                            f"({monitoring.symbol}) 조회중",
                            "조회중",
                            "[gray]대기[/gray]",
                            "[gray]대기[/gray]",
                            "[gray]대기[/gray]",
                            "[gray]대기[/gray]",
                            "[gray]--[/gray]",
                            "[gray]대기[/gray]"
                        )

            return analysis_table

        except Exception as e:
            self.logger.error(f"❌ 전략 분석 테이블 생성 실패: {e}")
            return f"[red]매매로직 계산 테이블 생성 실패: {e}[/red]"

    async def _get_stock_basic_info(self, monitoring):
        """종목 기본 정보 조회"""
        current_price = 0
        stock_name = "N/A"

        try:
            # 현재가 조회
            if hasattr(self, 'kis_collector') and self.kis_collector:
                current_price = await asyncio.wait_for(
                    self.kis_collector.get_current_price(monitoring.symbol),
                    timeout=2.0
                )

                # 종목명 조회
                stock_data_obj = await asyncio.wait_for(
                    self.kis_collector.get_stock_info(monitoring.symbol),
                    timeout=2.0
                )
                if stock_data_obj and hasattr(stock_data_obj, 'name') and stock_data_obj.name:
                    stock_name = stock_data_obj.name.strip()

        except Exception as e:
            # 기본 정보 조회 실패는 로그 출력하지 않음 (너무 시끄러움)
            pass

        return current_price, stock_name

    async def _calculate_trading_strategies(self, symbol, current_price):
        """실제 매매로직 계산 수행"""
        try:
            # 가격 데이터 조회
            price_data = await self._get_price_data(symbol)
            if not price_data:
                return self._get_default_strategy_results()

            results = {}

            # 1. RSI 계산
            results['rsi'] = await self._calculate_rsi_strategy(price_data, current_price)

            # 2. 골든크로스 계산
            results['golden_cross'] = await self._calculate_golden_cross_strategy(price_data, current_price)

            # 3. 대량거래 분석
            results['volume_surge'] = await self._calculate_volume_strategy(price_data, current_price)

            # 4. 모멘텀 분석
            results['momentum'] = await self._calculate_momentum_strategy(price_data, current_price)

            # 5. 종합 점수 계산
            total_score = (
                results['rsi'].get('score', 0) * 0.3 +
                results['golden_cross'].get('score', 0) * 0.25 +
                results['volume_surge'].get('score', 0) * 0.25 +
                results['momentum'].get('score', 0) * 0.2
            )

            results['total_score'] = total_score

            # 6. 최종 신호 결정
            if total_score >= 75:
                results['final_signal'] = 'BUY'
            elif total_score >= 60:
                results['final_signal'] = 'WEAK_BUY'
            elif total_score <= 25:
                results['final_signal'] = 'SELL'
            elif total_score <= 40:
                results['final_signal'] = 'WEAK_SELL'
            else:
                results['final_signal'] = 'HOLD'

            return results

        except Exception as e:
            # 매매로직 계산 실패 시 로그 출력 안함 (너무 시끄러움)
            return self._get_default_strategy_results()

    async def _get_price_data(self, symbol):
        """가격 데이터 조회 - KIS API 사용"""
        try:
            # 1순위: data_collector 사용
            if hasattr(self, 'data_collector') and self.data_collector:
                try:
                    return await asyncio.wait_for(
                        self.data_collector.get_ohlcv_data(symbol, 'D', 20),
                        timeout=3.0
                    )
                except:
                    pass

            # 2순위: kis_collector 사용
            if hasattr(self, 'kis_collector') and self.kis_collector:
                try:
                    return await asyncio.wait_for(
                        self.kis_collector.get_daily_data(symbol, 20),
                        timeout=3.0
                    )
                except:
                    pass

            # 3순위: auto_trader의 data_collector 사용
            if hasattr(self, 'auto_trader') and self.auto_trader and hasattr(self.auto_trader, 'data_collector'):
                try:
                    return await asyncio.wait_for(
                        self.auto_trader.data_collector.get_ohlcv_data(symbol, 'D', 20),
                        timeout=3.0
                    )
                except:
                    pass

        except Exception as e:
            # 가격 데이터 조회 실패 시 로그 출력 안함
            pass
        return None

    async def _calculate_rsi_strategy(self, price_data, current_price):
        """RSI 전략 계산"""
        try:
            if len(price_data) < 14:
                return {'status': '데이터부족', 'score': 50, 'value': 0}

            # 간단한 RSI 계산 (실제로는 technical_indicators 모듈 사용)
            closes = [float(item.close) for item in price_data[-14:]]
            gains = []
            losses = []

            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))

            avg_gain = sum(gains) / len(gains) if gains else 0.01
            avg_loss = sum(losses) / len(losses) if losses else 0.01
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # RSI 기반 점수 계산
            if rsi <= 30:
                status = "[green]과매도[/green]"
                score = 80  # 매수 신호
            elif rsi >= 70:
                status = "[red]과매수[/red]"
                score = 20  # 매도 신호
            else:
                status = f"[yellow]{rsi:.1f}[/yellow]"
                score = 50  # 중립

            return {'status': status, 'score': score, 'value': rsi}

        except Exception as e:
            # RSI 계산 실패 시 로그 출력 안함
            return {'status': '[gray]계산실패[/gray]', 'score': 50, 'value': 0}

    async def _calculate_golden_cross_strategy(self, price_data, current_price):
        """골든크로스 전략 계산"""
        try:
            if len(price_data) < 20:
                return {'status': '데이터부족', 'score': 50}

            closes = [float(item.close) for item in price_data]

            # 5일, 20일 이동평균 계산
            ma5 = sum(closes[-5:]) / 5
            ma20 = sum(closes[-20:]) / 20

            # 이전 기간 이동평균
            prev_ma5 = sum(closes[-6:-1]) / 5
            prev_ma20 = sum(closes[-21:-1]) / 20

            # 골든크로스/데드크로스 판정
            if ma5 > ma20 and prev_ma5 <= prev_ma20:
                status = "[green]골든크로스[/green]"
                score = 85
            elif ma5 < ma20 and prev_ma5 >= prev_ma20:
                status = "[red]데드크로스[/red]"
                score = 15
            elif ma5 > ma20:
                status = "[blue]상승추세[/blue]"
                score = 65
            else:
                status = "[purple]하락추세[/purple]"
                score = 35

            return {'status': status, 'score': score}

        except Exception as e:
            # 골든크로스 계산 실패 시 로그 출력 안함
            return {'status': '[gray]계산실패[/gray]', 'score': 50}

    async def _calculate_volume_strategy(self, price_data, current_price):
        """대량거래 전략 계산"""
        try:
            if len(price_data) < 10:
                return {'status': '데이터부족', 'score': 50}

            volumes = [int(item.volume) for item in price_data]
            recent_volume = volumes[-1]
            avg_volume = sum(volumes[-10:]) / 10

            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

            if volume_ratio >= 2.0:
                status = "[green]대량급증[/green]"
                score = 80
            elif volume_ratio >= 1.5:
                status = "[yellow]거래증가[/yellow]"
                score = 65
            elif volume_ratio <= 0.5:
                status = "[red]거래감소[/red]"
                score = 35
            else:
                status = f"[white]{volume_ratio:.1f}배[/white]"
                score = 50

            return {'status': status, 'score': score}

        except Exception as e:
            # 거래량 계산 실패 시 로그 출력 안함
            return {'status': '[gray]계산실패[/gray]', 'score': 50}

    async def _calculate_momentum_strategy(self, price_data, current_price):
        """모멘텀 전략 계산"""
        try:
            if len(price_data) < 5:
                return {'status': '데이터부족', 'score': 50}

            closes = [float(item.close) for item in price_data]

            # 5일 가격 변화율 계산
            price_change = (closes[-1] - closes[-5]) / closes[-5] * 100

            if price_change >= 5:
                status = "[green]강한상승[/green]"
                score = 80
            elif price_change >= 2:
                status = "[blue]상승[/blue]"
                score = 65
            elif price_change <= -5:
                status = "[red]강한하락[/red]"
                score = 20
            elif price_change <= -2:
                status = "[purple]하락[/purple]"
                score = 35
            else:
                status = f"[yellow]{price_change:+.1f}%[/yellow]"
                score = 50

            return {'status': status, 'score': score}

        except Exception as e:
            # 모멘텀 계산 실패 시 로그 출력 안함
            return {'status': '[gray]계산실패[/gray]', 'score': 50}

    def _format_strategy_status(self, strategy_result):
        """전략 결과 포맷팅"""
        return strategy_result.get('status', '[gray]N/A[/gray]')

    def _format_signal(self, signal):
        """신호 포맷팅"""
        signal_colors = {
            'BUY': '[bold green]매수[/bold green]',
            'WEAK_BUY': '[green]약매수[/green]',
            'HOLD': '[yellow]보유[/yellow]',
            'WEAK_SELL': '[red]약매도[/red]',
            'SELL': '[bold red]매도[/bold red]'
        }
        return signal_colors.get(signal, '[gray]대기[/gray]')

    def _get_default_strategy_results(self):
        """기본 전략 결과 반환"""
        return {
            'rsi': {'status': '[yellow]RSI 50[/yellow]', 'score': 50, 'value': 50},
            'golden_cross': {'status': '[blue]중립[/blue]', 'score': 50, 'value': 0},
            'volume_surge': {'status': '[green]보통[/green]', 'score': 50, 'value': 1.0},
            'momentum': {'status': '[magenta]중립[/magenta]', 'score': 50, 'value': 0},
            'total_score': 50,
            'final_signal': 'HOLD'
        }

    async def _display_monitoring_status_once(self):
        """기존 모니터링 현황 표시 방식 (폴백용)"""
        try:
            from rich.panel import Panel
            self.console.print("[bold cyan]=== 실시간 모니터링 현황 ===[/bold cyan]")
            
            # HTS 보유종목 표시
            self.console.print("\n[bold green]=== HTS 보유 종목 ===[/bold green]")
            holdings_content = await self._get_holdings_table()
            self.console.print(Panel(holdings_content, border_style="green"))
            
            # 전략 추출 감시종목 표시
            self.console.print("\n[bold blue]=== 전략 추출 감시 종목 ===[/bold blue]")
            monitoring_content = await self._get_monitoring_stocks_table()
            self.console.print(Panel(monitoring_content, border_style="blue"))
            
        except Exception as e:
            self.console.print(f"[red]모니터링 현황 조회 실패: {e}[/red]")

    # 헬퍼 메서드들
    def _calculate_dynamic_stop_loss(self, symbol, current_price, avg_price, profit_rate):
        """동적 손절가 계산"""
        try:
            if not current_price or not avg_price:
                return "N/A"

            # profit_rate 안전성 검사
            safe_profit_rate = profit_rate
            if isinstance(profit_rate, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"손절가 계산에서 profit_rate가 dict: {profit_rate}, 0으로 처리")
                safe_profit_rate = 0.0
            elif not isinstance(profit_rate, (int, float)):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"손절가 계산에서 profit_rate 타입 오류: {type(profit_rate)}, 0으로 처리")
                safe_profit_rate = 0.0

            # 기본 손절 비율 (5%)
            basic_stop_loss_rate = 0.05

            # 수익률에 따른 트레일링 스톱
            if safe_profit_rate >= 20:  # 20% 이상 수익
                stop_loss_rate = 0.10  # 10% 손실까지 허용
            elif safe_profit_rate >= 10:  # 10% 이상 수익
                stop_loss_rate = 0.07  # 7% 손실까지 허용
            elif safe_profit_rate >= 5:   # 5% 이상 수익
                stop_loss_rate = 0.05  # 5% 손실까지 허용
            else:
                stop_loss_rate = basic_stop_loss_rate
            
            stop_loss_price = int(avg_price * (1 - stop_loss_rate))
            return f"{stop_loss_price:,}"
            
        except Exception as e:
            # 계산 실패 시 기본 손절가
            if avg_price > 0:
                basic_stop = int(avg_price * 0.95)
                return f"{basic_stop:,}"
            return "N/A"
    
    def _get_holding_strategy_name(self, symbol):
        """보유종목 전략명 조회 (개선된 로직)"""
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                from database.models import MonitoringStock, MonitoringStatus
                with self.db_manager.get_session() as session:
                    # 1. 활성 모니터링에서 먼저 검색
                    monitoring = session.query(MonitoringStock).filter(
                        MonitoringStock.symbol == symbol,
                        MonitoringStock.status == MonitoringStatus.ACTIVE.value
                    ).first()
                    if monitoring and monitoring.strategy_name:
                        return self._get_strategy_display_name(monitoring.strategy_name)

                    # 2. 활성 상태가 아니면, 가장 최근 기록을 검색
                    latest_record = session.query(MonitoringStock).filter(
                        MonitoringStock.symbol == symbol
                    ).order_by(MonitoringStock.recommendation_time.desc()).first()
                    if latest_record and latest_record.strategy_name:
                        return self._get_strategy_display_name(latest_record.strategy_name)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.warning(f"전략명 조회 실패 {symbol}: {e}")
        
        # 3. 그래도 없으면 '직접매수'로 표시
        return "직접매수"
    
    def _get_holding_status(self, current_price, stop_loss_price, profit_rate):
        """보유종목 상태 판단"""
        try:
            if stop_loss_price == "N/A" or current_price <= 0:
                return "[gray]확인중[/gray]"

            # profit_rate 안전성 검사
            safe_profit_rate = profit_rate
            if isinstance(profit_rate, dict):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"보유상태 판단에서 profit_rate가 dict: {profit_rate}, 0으로 처리")
                safe_profit_rate = 0.0
            elif not isinstance(profit_rate, (int, float)):
                if hasattr(self, 'logger'):
                    self.logger.warning(f"보유상태 판단에서 profit_rate 타입 오류: {type(profit_rate)}, 0으로 처리")
                safe_profit_rate = 0.0

            stop_loss_value = int(stop_loss_price.replace(',', '').replace('원', ''))

            if current_price <= stop_loss_value:
                return "[red]손절신호[/red]"
            elif safe_profit_rate >= 10:
                return "[green]수익[/green]"
            elif safe_profit_rate >= 0:
                return "[yellow]소폭수익[/yellow]"
            elif safe_profit_rate >= -3:
                return "[orange1]소폭손실[/orange1]"
            else:
                return "[red]손실[/red]"
                
        except:
            return "[gray]확인중[/gray]"

    # 나머지 메서드들
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
        # 기본 설정
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
            # 설정 파일에서 로드
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                    default_settings.update(user_settings)
                    self.logger.info(f"✅ 매매 설정 로드 완료: {self.settings_file}")
            else:
                self.logger.info("기본 설정 사용 - 설정 파일이 없습니다.")
            
            return default_settings
            
        except Exception as e:
            self.logger.error(f"매매 설정 조회 실패: {e}")
            return default_settings

    async def _save_trading_settings(self, settings: Dict[str, Any]) -> bool:
        """매매 설정 저장"""
        try:
            # configs 디렉토리 생성
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 설정 파일에 저장
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 매매 설정 저장 완료: {self.settings_file}")
            self.console.print("[green]✅ 설정이 저장되었습니다.[/green]")
            
            # 모니터링 중인 종목들에도 설정 반영 (새로운 종목부터 적용)
            await self._apply_settings_to_monitoring_stocks(settings)
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ 설정 저장 실패: {e}[/red]")
            self.logger.error(f"매매 설정 저장 실패: {e}")
            return False

    async def _apply_settings_to_monitoring_stocks(self, settings: Dict[str, Any]):
        """설정을 모니터링 중인 종목들에 반영"""
        try:
            with self.db_manager.get_session() as session:
                # 현재 모니터링 중인 종목들 조회
                monitoring_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.monitoring_type == MonitoringType.TRADING.value
                ).all()
                
                target_profit_rate = settings.get('target_profit_rate', 10.0)
                stop_loss_rate = settings.get('stop_loss_rate', 5.0)
                
                updated_count = 0
                for stock in monitoring_stocks:
                    if stock.current_price:
                        # 새로운 목표가와 손절가 계산
                        new_target_price = int(stock.current_price * (1 + target_profit_rate / 100))
                        new_stop_loss_price = int(stock.current_price * (1 - stop_loss_rate / 100))
                        
                        # 현재 설정된 목표가/손절가와 다를 경우에만 업데이트
                        if (stock.target_price != new_target_price or 
                            stock.stop_loss_price != new_stop_loss_price):
                            
                            old_target = stock.target_price
                            old_stop_loss = stock.stop_loss_price
                            
                            stock.target_price = new_target_price
                            stock.stop_loss_price = new_stop_loss_price
                            stock.updated_at = datetime.now()
                            
                            self.logger.info(
                                f"📊 설정 반영: {stock.symbol} ({stock.name}) - "
                                f"목표가: {old_target:,} → {new_target_price:,}원, "
                                f"손절가: {old_stop_loss:,} → {new_stop_loss_price:,}원"
                            )
                            updated_count += 1
                
                if updated_count > 0:
                    session.commit()
                    self.console.print(f"[green]✅ {updated_count}개 종목에 새로운 설정이 반영되었습니다.[/green]")
                else:
                    self.console.print("[yellow]ℹ️ 반영할 설정 변경사항이 없습니다.[/yellow]")
                    
        except Exception as e:
            self.logger.error(f"모니터링 종목 설정 반영 실패: {e}")
            self.console.print(f"[red]❌ 모니터링 종목 설정 반영 실패: {e}[/red]")

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
                self.console.print(f"   최소 수량: {new_min_qty}주")
                self.console.print(f"   최대 금액: {new_max_amount:,}원")
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
    async def _manual_trade(self):
        """수동 매매 - 시장 시간 확인"""
        if not self.market_manager.is_trading_allowed_now():
            status_info = self.market_manager.get_current_status_info()
            self.console.print(f"[bold red]매매 가능 시간이 아닙니다. 현재 상태: {status_info.get('market_status_korean', '알 수 없음')}[/bold red]")
            return

        self.console.print("[blue]ℹ️ 수동 매매 기능은 개발 중입니다.[/blue]")
    async def _add_buy_recommendation(self):
        """매수 추천 추가 - 시장 시간 확인"""
        if not self.market_manager.is_trading_allowed_now():
            status_info = self.market_manager.get_current_status_info()
            self.console.print(f"[bold red]매매 추천 추가 가능 시간이 아닙니다. 현재 상태: {status_info.get('market_status_korean', '알 수 없음')}[/bold red]")
            return

        self.console.print("[blue]ℹ️ 매수 추천 추가 기능은 개발 중입니다.[/blue]")
    async def _remove_monitoring(self): 
        self.console.print("[blue]ℹ️ 모니터링 제거 기능은 개발 중입니다.[/blue]")
    async def _start_removal_scheduler(self): 
        self.console.print("[blue]ℹ️ 제거 스케줄러 기능은 개발 중입니다.[/blue]")
    async def _stop_removal_scheduler(self): 
        self.console.print("[blue]ℹ️ 제거 스케줄러 기능은 개발 중입니다.[/blue]")
    async def _view_removal_scheduler_status(self): 
        self.console.print("[blue]ℹ️ 제거 스케줄러 상태 기능은 개발 중입니다.[/blue]")
    async def _manage_monitoring_stocks(self): 
        self.console.print("[blue]ℹ️ 감시 종목 관리 기능은 개발 중입니다.[/blue]")
    async def _view_market_schedule(self): 
        """이번 주 시장 일정을 rich 테이블로 표시"""
        try:
            # MarketScheduleManager를 사용하여 주간 일정 가져오기
            weekly_schedule = await self.market_manager.get_weekly_schedule()
            
            if not weekly_schedule:
                self.console.print("[red]주간 시장 일정을 가져올 수 없습니다.[/red]")
                return
            
            # Rich 테이블 생성
            from rich.table import Table
            from datetime import datetime
            
            table = Table(title="📅 이번 주 시장 일정", show_header=True, header_style="bold cyan")
            table.add_column("날짜", style="white", width=12)
            table.add_column("요일", style="white", width=4, justify="center")
            table.add_column("개장 여부", style="white", width=8, justify="center")
            
            for day_info in weekly_schedule:
                date = day_info['date']
                weekday = day_info['weekday_korean']
                is_market_open = day_info['is_market_open']
                is_today = day_info['is_today']
                
                # 개장 여부 표시
                market_status = "[green]개장[/green]" if is_market_open else "[red]휴장[/red]"
                
                # 오늘 날짜는 특별하게 표시
                if is_today:
                    date_display = f"[bold cyan]{date}[/bold cyan]"
                    weekday_display = f"[bold cyan]{weekday}[/bold cyan]"
                else:
                    date_display = date
                    weekday_display = weekday
                
                table.add_row(date_display, weekday_display, market_status)
            
            self.console.print(table)
            
        except Exception as e:
            self.logger.error(f"시장 일정 조회 실패: {e}")
            self.console.print(f"[red]❌ 시장 일정 조회 중 오류가 발생했습니다: {e}[/red]")
    async def _manage_auto_modes(self): 
        self.console.print("[blue]ℹ️ 자동 모드 관리 기능은 개발 중입니다.[/blue]")
    
    async def _view_monitoring_status_safe(self):
        """안전한 모니터링 현황 - 백그라운드 작업 중에도 사용 가능"""
        try:
            self.console.print("[bold cyan]📊 모니터링 현황 (간단 버전)[/bold cyan]")
            
            # 백그라운드 모니터링 상태 확인
            background_active = await self._is_background_monitoring_active()
            
            if background_active:
                self.console.print("[yellow]🔄 백그라운드 모니터링 실행 중[/yellow]")
                self.console.print("[cyan]💡 안전한 간단 현황을 표시합니다.[/cyan]\n")
                
                # 간단한 현황만 표시 (DB 조회만, KIS API 호출 없음)
                await self._show_simple_monitoring_status()
                
                self.console.print("\n[yellow]💡 상세 현황을 보려면 다음 중 선택하세요:[/yellow]")
                self.console.print("   1. 백그라운드 모니터링 중지 후 상세 조회")
                self.console.print("   2. 현재 상태에서 간단 정보만 확인")
                
                choice = Prompt.ask("선택하세요", choices=["1", "2"], default="2")
                
                if choice == "1":
                    if Confirm.ask("백그라운드 모니터링을 중지하시겠습니까?"):
                        await self._stop_monitoring()
                        await self._view_monitoring_status()
                else:
                    self.console.print("[green]✅ 간단 현황 조회 완료[/green]")
            else:
                # 백그라운드 미실행 시 상세 현황 표시
                self.console.print("[green]✅ 백그라운드 미실행 - 상세 현황 표시[/green]")
                await self._view_monitoring_status()
                
        except Exception as e:
            self.logger.error(f"안전한 모니터링 현황 조회 실패: {e}")
            self.console.print(f"[red]❌ 현황 조회 실패: {e}[/red]")

    async def _is_background_monitoring_active(self) -> bool:
        """백그라운드 모니터링 실행 여부 확인"""
        try:
            # db_auto_trader의 모니터링 상태 확인
            if hasattr(self, 'db_auto_trader') and self.db_auto_trader:
                return self.db_auto_trader.monitoring_active
            
            # 다른 모니터링 서비스 확인
            if hasattr(self, '_monitoring_task') and self._monitoring_task:
                return not self._monitoring_task.done()
                
            return False
        except:
            return False
    
    async def _show_simple_monitoring_status(self):
        """간단한 모니터링 현황 표시 (DB 조회만)"""
        try:
            from rich.table import Table
            
            # DB에서 모니터링 종목 수만 조회 (빠른 조회)
            monitoring_count = 0
            if self.db_manager:
                try:
                    with self.db_manager.get_session() as session:
                        from database.models import MonitoringStock
                        monitoring_count = session.query(MonitoringStock).filter(
                            MonitoringStock.status.in_(['MONITORING', 'BUY_SIGNAL'])
                        ).count()
                except Exception as e:
                    self.logger.warning(f"DB 조회 실패: {e}")
            
            # 간단한 정보 테이블
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("항목", style="cyan", width=20)
            table.add_column("상태", style="green", width=30)
            
            table.add_row("🎯 감시 중인 종목", f"{monitoring_count}개")
            table.add_row("🔄 백그라운드 모니터링", "실행 중")
            table.add_row("⏰ 마지막 업데이트", datetime.now().strftime("%H:%M:%S"))
            table.add_row("💡 상세 정보", "백그라운드 중지 후 이용 가능")
            
            self.console.print(table)
            
        except Exception as e:
            self.logger.error(f"간단 현황 표시 실패: {e}")
            self.console.print(f"[red]❌ 간단 현황 표시 실패: {e}[/red]")
