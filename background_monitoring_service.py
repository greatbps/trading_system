#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/background_monitoring_service.py

백그라운드 모니터링 서비스 - UI와 독립적으로 실행되는 감시 시스템
"""

import asyncio
import sys
import os
import signal
from pathlib import Path
from datetime import datetime
import json
import logging

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import get_logger
from core.trading_system import TradingSystem
from datetime import datetime, time

class BackgroundMonitoringService:
    """백그라운드 모니터링 서비스"""

    def __init__(self, trading_system=None):
        self.logger = get_logger("BackgroundService")
        self.trading_system = trading_system  # 기존 TradingSystem 인스턴스 재사용
        self.running = False
        self.service_state_file = Path("data/service_state.json")
        
        # 시간대별 전략 스케줄 정의
        self.strategy_schedule = {
            time(9, 0): {"strategy": "breakout", "name": "2번 Breakout 전략", "duration_minutes": 30},
            time(9, 30): {"strategy": "momentum", "name": "1번 Momentum 전략", "duration_minutes": 60},
            time(10, 0): {"strategy": "supertrend_ema_rsi", "name": "4번 Supertrend EMA RSI 전략", "duration_minutes": 90},
            time(10, 30): {"strategy": "squeeze_momentum_pro", "name": "8번 Squeeze Momentum Pro 전략", "duration_minutes": 90},
            time(11, 0): {"strategy": "vwap", "name": "5번 VWAP 전략", "duration_minutes": 180},
            time(13, 0): {"strategy": "rsi", "name": "7번 RSI 전략", "duration_minutes": 90},
            time(13, 30): {"strategy": "scalping_3m", "name": "6번 3분봉 스캘핑 전략", "duration_minutes": 90},
            time(14, 30): {"strategy": "eod", "name": "3번 EOD 전략", "duration_minutes": 50}
        }
        
        # 전략 실행 상태 추적
        self.executed_strategies = set()  # 오늘 실행된 전략들
        self.last_strategy_check = None
        self.current_date = None
        
    async def initialize(self):
        """서비스 초기화"""
        try:
            self.logger.info("🚀 백그라운드 모니터링 서비스 초기화 시작...")

            # 기존 TradingSystem 인스턴스가 없으면 새로 생성
            if self.trading_system is None:
                self.logger.info("새로운 TradingSystem 인스턴스 생성...")
                self.trading_system = TradingSystem()
                success = await self.trading_system.initialize_components()

                if not success:
                    self.logger.error("❌ Trading System 초기화 실패")
                    return False
            else:
                self.logger.info("✅ 기존 초기화된 TradingSystem 재사용 - 중복 초기화 방지")

            self.logger.info("✅ 백그라운드 모니터링 서비스 초기화 완료")
            return True

        except Exception as e:
            self.logger.error(f"❌ 백그라운드 서비스 초기화 실패: {e}")
            return False
    
    async def check_and_execute_strategies(self):
        """시간대별 전략 자동 실행 체크"""
        try:
            now = datetime.now()
            current_time = now.time()
            current_date = now.date()
            
            # 날짜가 바뀌면 실행된 전략 목록 초기화
            if self.current_date != current_date:
                self.executed_strategies.clear()
                self.current_date = current_date
                self.logger.info(f"📅 새로운 거래일 시작: {current_date}")
            
            # 시장 시간 확인
            market_manager = self.trading_system.market_schedule_manager if hasattr(self.trading_system, 'market_schedule_manager') else None
            if not market_manager:
                return
                
            await market_manager.update_market_status()
            is_market_time = market_manager.is_monitoring_allowed_now()
            
            if not is_market_time:
                return
            
            # 실행할 전략 찾기
            strategy_to_execute = None
            strategy_info = None
            
            for schedule_time, info in self.strategy_schedule.items():
                # 현재 시간이 스케줄 시간 이후이고, 아직 실행되지 않은 전략
                if (current_time >= schedule_time and 
                    schedule_time not in self.executed_strategies):
                    
                    # 전략 유효 시간 체크 (duration_minutes 내)
                    strategy_end_time = datetime.combine(current_date, schedule_time)
                    strategy_end_time = strategy_end_time.replace(
                        minute=strategy_end_time.minute + info['duration_minutes']
                    ).time()
                    
                    if current_time <= strategy_end_time:
                        strategy_to_execute = schedule_time
                        strategy_info = info
                        break
            
            # 전략 실행
            if strategy_to_execute and strategy_info:
                await self._execute_strategy_automatically(strategy_to_execute, strategy_info)
                
        except Exception as e:
            self.logger.error(f"❌ 전략 자동실행 체크 오류: {e}")
    
    async def _execute_strategy_automatically(self, schedule_time, strategy_info):
        """전략 자동 실행"""
        try:
            strategy_name = strategy_info['strategy']
            strategy_display_name = strategy_info['name']
            
            self.logger.info(f"🚀 {strategy_display_name} 자동 실행 시작 ({schedule_time.strftime('%H:%M')})")
            
            # 전략 실행됨으로 표시
            self.executed_strategies.add(schedule_time)
            
            # 분석 핸들러 초기화
            from core.analysis_handlers import AnalysisHandlers
            analysis_handler = AnalysisHandlers(self.trading_system)
            
            # 전략 실행 및 종목 추출
            analysis_results = await self._run_strategy_analysis(strategy_name, analysis_handler)
            
            if analysis_results:
                # 매수 추천 종목을 자동으로 감시 대상에 추가
                added_count = await analysis_handler.auto_add_buy_recommendations_to_monitoring(analysis_results)
                
                self.logger.info(f"✅ {strategy_display_name} 실행 완료: {len(analysis_results)}개 분석, {added_count}개 감시 추가")
                
                # 상태 저장
                self.save_service_state({
                    'status': 'running',
                    'last_strategy_execution': {
                        'time': schedule_time.strftime('%H:%M'),
                        'strategy': strategy_name,
                        'display_name': strategy_display_name,
                        'analyzed_count': len(analysis_results),
                        'added_count': added_count,
                        'executed_at': datetime.now().isoformat()
                    }
                })
            else:
                self.logger.warning(f"⚠️ {strategy_display_name} 실행 결과 없음")
                
        except Exception as e:
            self.logger.error(f"❌ {strategy_info['name']} 자동실행 실패: {e}")
    
    async def _run_strategy_analysis(self, strategy_name, analysis_handler):
        """전략 분석 실행"""
        try:
            # 전략별 분석 메서드 매핑
            strategy_methods = {
                'momentum': 'analyze_momentum_strategy',
                'breakout': 'analyze_breakout_strategy', 
                'eod': 'analyze_eod_strategy',
                'supertrend_ema_rsi': 'analyze_supertrend_ema_rsi_strategy',
                'vwap': 'analyze_vwap_strategy',
                'scalping_3m': 'analyze_scalping_3m_strategy',
                'rsi': 'analyze_rsi_strategy',
                'squeeze_momentum_pro': 'analyze_squeeze_momentum_pro_strategy'
            }
            
            method_name = strategy_methods.get(strategy_name)
            if not method_name:
                self.logger.warning(f"⚠️ 알 수 없는 전략: {strategy_name}")
                return []
            
            # 분석 메서드 실행
            if hasattr(analysis_handler, method_name):
                self.logger.info(f"📊 {strategy_name} 전략 분석 실행 중...")
                results = await getattr(analysis_handler, method_name)()
                return results if results else []
            else:
                # 일반적인 분석 메서드로 대체
                self.logger.info(f"📊 {strategy_name} 전략 일반 분석 실행 중...")
                if hasattr(analysis_handler, 'run_comprehensive_analysis'):
                    results = await analysis_handler.run_comprehensive_analysis(strategy_name)
                    return results if results else []
                else:
                    self.logger.warning(f"⚠️ 분석 메서드를 찾을 수 없음: {method_name}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"❌ {strategy_name} 전략 분석 실패: {e}")
            return []
    
    def save_service_state(self, state: dict):
        """서비스 상태 저장"""
        try:
            self.service_state_file.parent.mkdir(exist_ok=True)
            state['last_update'] = datetime.now().isoformat()
            
            with open(self.service_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"❌ 서비스 상태 저장 실패: {e}")
    
    def load_service_state(self) -> dict:
        """서비스 상태 로드"""
        try:
            if self.service_state_file.exists():
                with open(self.service_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"❌ 서비스 상태 로드 실패: {e}")
        
        return {'monitoring_enabled': True, 'auto_start': True}
    
    async def start_service(self):
        """백그라운드 서비스 시작"""
        try:
            self.running = True
            self.logger.info("🟢 백그라운드 모니터링 서비스 시작")
            
            # 상태 저장
            self.save_service_state({
                'status': 'running',
                'monitoring_enabled': True,
                'started_at': datetime.now().isoformat()
            })
            
            # 초기 시장 시간 체크 후 조건부 모니터링 시작
            market_manager = self.trading_system.market_schedule_manager if hasattr(self.trading_system, 'market_schedule_manager') else None
            
            if market_manager:
                await market_manager.update_market_status()
                is_market_time = market_manager.is_monitoring_allowed_now()
                market_status_korean = market_manager._get_status_korean(market_manager.current_status)
                
                if is_market_time and self.trading_system.db_auto_trader:
                    await self.trading_system.db_auto_trader.start_monitoring()
                    self.logger.info(f"📊 {market_status_korean} - DB 자동매매 모니터링 시작됨")
                else:
                    self.logger.info(f"⏳ {market_status_korean} - 장 시간 외 대기 모드")
            
            # 서비스 상태 모니터링 루프
            while self.running:
                try:
                    # 시장 시간 확인 - MarketScheduleManager 사용
                    is_market_time = False
                    market_status = "Unknown"
                    market_status_korean = "알 수 없음"
                    
                    if market_manager:
                        await market_manager.update_market_status()
                        is_market_time = market_manager.is_monitoring_allowed_now()
                        market_status = market_manager.current_status.value
                        market_status_korean = market_manager._get_status_korean(market_manager.current_status)
                        
                        self.logger.debug(f"🕐 시장 상태: {market_status_korean} ({market_status}), 모니터링 허용: {is_market_time}")
                    
                    # 시간대별 전략 자동실행 체크 (장 시간에만)
                    if is_market_time:
                        await self.check_and_execute_strategies()
                    
                    # 모니터링 상태 확인 및 제어
                    is_monitoring = False
                    if self.trading_system and self.trading_system.db_auto_trader:
                        is_monitoring = self.trading_system.db_auto_trader.is_monitoring
                        
                        if is_market_time:
                            # 장 시간 중: 모니터링이 중단된 경우 재시작
                            if not is_monitoring:
                                self.logger.info(f"🟢 {market_status_korean} - 모니터링 시작")
                                await self.trading_system.db_auto_trader.start_monitoring()
                                is_monitoring = True
                        else:
                            # 장 시간 외: 모니터링이 실행 중이면 중지
                            if is_monitoring:
                                self.logger.info(f"🔴 {market_status_korean} - 모니터링 중지")
                                await self.trading_system.db_auto_trader.stop_monitoring()
                                is_monitoring = False
                    
                    # 서비스 상태 업데이트
                    self.save_service_state({
                        'status': 'running',
                        'monitoring_enabled': True,
                        'monitoring_active': is_monitoring,
                        'market_status': market_status,
                        'market_status_korean': market_status_korean,
                        'market_time_allowed': is_market_time,
                        'health_check': datetime.now().isoformat()
                    })
                    
                    # 장 시간에는 더 자주 체크, 장 시간 외에는 덜 자주 체크
                    sleep_interval = 300 if is_market_time else 900  # 5분 vs 15분
                    self.logger.debug(f"⏰ 다음 체크까지 {sleep_interval//60}분 대기...")
                    await asyncio.sleep(sleep_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"❌ 서비스 루프 오류: {e}")
                    await asyncio.sleep(60)  # 1분 대기 후 재시도
            
        except Exception as e:
            self.logger.error(f"❌ 백그라운드 서비스 시작 실패: {e}")
    
    async def stop_service(self):
        """백그라운드 서비스 중지"""
        try:
            self.running = False
            self.logger.info("🛑 백그라운드 모니터링 서비스 중지")
            
            # 모니터링 중지 (선택사항 - 보통은 계속 실행)
            if self.trading_system and self.trading_system.db_auto_trader:
                # 여기서는 모니터링을 중지하지 않음 - 계속 실행
                self.logger.info("📊 모니터링은 계속 실행됩니다")
            
            # 상태 저장
            self.save_service_state({
                'status': 'stopped',
                'stopped_at': datetime.now().isoformat(),
                'monitoring_enabled': True  # 모니터링 자체는 계속 실행
            })
            
        except Exception as e:
            self.logger.error(f"❌ 백그라운드 서비스 중지 실패: {e}")
    
    async def get_service_status(self) -> dict:
        """서비스 상태 조회"""
        try:
            base_status = {
                'service_running': self.running,
                'monitoring_active': False,
                'active_stocks': 0,
                'last_check': None
            }
            
            if self.trading_system and self.trading_system.db_auto_trader:
                base_status['monitoring_active'] = self.trading_system.db_auto_trader.is_monitoring
                
                # 모니터링 상태 상세 정보
                status = self.trading_system.db_auto_trader.get_monitoring_status()
                if hasattr(status, '__await__'):  # async 메서드인 경우
                    status = await status
                    
                base_status['active_stocks'] = len(status.get('monitoring_stocks', []))
                
            return base_status
            
        except Exception as e:
            self.logger.error(f"❌ 서비스 상태 조회 실패: {e}")
            return {'error': str(e)}

# 글로벌 서비스 인스턴스
service = None

async def start_background_service():
    """백그라운드 서비스 시작"""
    global service
    try:
        service = BackgroundMonitoringService()
        success = await service.initialize()
        
        if success:
            await service.start_service()
        else:
            print("❌ 백그라운드 서비스 초기화 실패")
            
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의한 서비스 중지")
        if service:
            await service.stop_service()
    except Exception as e:
        print(f"❌ 백그라운드 서비스 오류: {e}")

def signal_handler(signum, frame):
    """시그널 핸들러"""
    print(f"\n📡 신호 수신: {signum}")
    if service:
        asyncio.create_task(service.stop_service())

if __name__ == "__main__":
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 백그라운드 모니터링 서비스 시작 중...")
    print("Ctrl+C 또는 SIGTERM으로 중지할 수 있습니다.")
    
    try:
        asyncio.run(start_background_service())
    except KeyboardInterrupt:
        print("\n✅ 백그라운드 서비스 정상 종료")
    except Exception as e:
        print(f"\n❌ 백그라운드 서비스 오류: {e}")