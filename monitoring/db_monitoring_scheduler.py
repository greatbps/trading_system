#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/monitoring/db_monitoring_scheduler.py

DB 연동 모니터링 스케줄러 - 감시 제거 자동화
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session
from utils.logger import get_logger
from database.models import (
    MonitoringStock, MonitoringSchedulerState, MonitoringType, MonitoringStatus
)
from data_collectors.chart_data_collector import ChartDataCollector


class DatabaseMonitoringRemovalScheduler:
    """DB 연동 모니터링 제거 스케줄러"""
    
    def __init__(self, config, kis_collector, db_manager):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.logger = get_logger("DatabaseMonitoringRemovalScheduler")
        
        # 차트 데이터 수집기
        self.chart_data_collector = ChartDataCollector(kis_collector)
        
        # 스케줄러 설정
        self.scheduler_type = "removal_scheduler"
        self.interval_seconds = 1800  # 30분
        self.is_running = False
        self.scheduler_task = None
        
        # 제거 조건 설정
        self.volume_decline_threshold = 0.7  # 70% 이하로 떨어지면
        self.volume_check_days = 3  # 3일 연속
        
        self.logger.info("📊 DatabaseMonitoringRemovalScheduler 초기화 완료")
    
    async def start_scheduler(self) -> bool:
        """스케줄러 시작"""
        try:
            if self.is_running:
                self.logger.warning("이미 스케줄러가 실행 중입니다")
                return True
            
            # DB에서 스케줄러 상태 초기화
            with self.db_manager.get_session() as session:
                scheduler_state = MonitoringSchedulerState.create_or_update_scheduler(
                    session, self.scheduler_type, self.interval_seconds
                )
                scheduler_state.start_scheduler()
                session.commit()
            
            self.is_running = True
            
            # 백그라운드 태스크 시작
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            self.logger.info(f"🚀 감시 제거 스케줄러 시작 - {self.interval_seconds}초 간격")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 시작 실패: {e}")
            return False
    
    async def stop_scheduler(self) -> bool:
        """스케줄러 중지"""
        try:
            if not self.is_running:
                self.logger.warning("스케줄러가 실행되지 않고 있습니다")
                return True
            
            self.is_running = False
            
            # 태스크 취소
            if self.scheduler_task and not self.scheduler_task.done():
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
            
            # DB 상태 업데이트
            with self.db_manager.get_session() as session:
                scheduler_state = MonitoringSchedulerState.get_scheduler_state(
                    session, self.scheduler_type
                )
                if scheduler_state:
                    scheduler_state.stop_scheduler()
                    session.commit()
            
            self.logger.info("🛑 감시 제거 스케줄러 중지")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 중지 실패: {e}")
            return False
    
    async def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        try:
            while self.is_running:
                try:
                    # 스케줄러 실행
                    await self._execute_monitoring_removal()
                    
                    # 다음 실행까지 대기
                    await asyncio.sleep(self.interval_seconds)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"❌ 스케줄러 실행 오류: {e}")
                    
                    # DB에 실패 기록
                    with self.db_manager.get_session() as session:
                        scheduler_state = MonitoringSchedulerState.get_scheduler_state(
                            session, self.scheduler_type
                        )
                        if scheduler_state:
                            scheduler_state.record_run_failure(str(e))
                            session.commit()
                    
                    await asyncio.sleep(self.interval_seconds)
            
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 루프 오류: {e}")
            self.is_running = False
    
    async def _execute_monitoring_removal(self):
        """모니터링 제거 실행"""
        try:
            self.logger.info("📊 감시 제거 스케줄러 실행 시작")
            
            # DB에서 감시 대상 종목들 가져오기
            with self.db_manager.get_session() as session:
                removal_stocks = MonitoringStock.get_active_monitoring(
                    session, MonitoringType.REMOVAL_WATCH
                )
            
            if not removal_stocks:
                self.logger.info("감시 대상 종목이 없습니다")
                self._record_success()
                return
            
            self.logger.info(f"📋 감시 대상 종목: {len(removal_stocks)}개")
            
            # 각 종목 분석
            removal_candidates = []
            
            for stock in removal_stocks:
                try:
                    should_remove = await self._analyze_stock_for_removal(stock)
                    if should_remove:
                        removal_candidates.append(stock)
                        
                except Exception as e:
                    self.logger.error(f"❌ {stock.symbol} 분석 오류: {e}")
            
            # 제거 대상 처리
            if removal_candidates:
                self.logger.info(f"🗑️ 제거 대상: {len(removal_candidates)}개")
                await self._remove_stocks(removal_candidates)
            else:
                self.logger.info("제거 대상 종목이 없습니다")
            
            # 성공 기록
            self._record_success()
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 제거 실행 실패: {e}")
            self._record_failure(str(e))
    
    async def _analyze_stock_for_removal(self, stock: MonitoringStock) -> bool:
        """종목 제거 여부 분석"""
        try:
            symbol = stock.symbol
            name = stock.name
            
            self.logger.debug(f"🔍 {symbol}({name}) 제거 분석 시작")
            
            # 30분봉 차트 데이터 가져오기 (최근 7일)
            chart_data = await self._get_30min_chart_data(symbol, days=7)
            
            if not chart_data or len(chart_data) < 10:
                self.logger.warning(f"❌ {symbol} 차트 데이터 부족")
                return False
            
            # 거래량 분석
            volume_analysis = self._analyze_volume_trend(chart_data)
            
            # 제거 조건 확인
            should_remove = self._check_removal_conditions(
                symbol, volume_analysis, stock
            )
            
            if should_remove:
                self.logger.info(f"🗑️ {symbol}({name}) 제거 대상 확인")
                return True
            else:
                self.logger.debug(f"✅ {symbol}({name}) 계속 감시")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 제거 분석 실패: {e}")
            return False
    
    async def _get_30min_chart_data(self, symbol: str, days: int = 7) -> List[Dict]:
        """30분봉 차트 데이터 수집"""
        try:
            # 30분봉 데이터 요청
            request = {
                'symbol': symbol,
                'period': '30',  # 30분봉
                'count': days * 16  # 하루 16개 (30분 * 16 = 8시간)
            }
            
            # 차트 데이터 수집
            chart_data = await self.chart_data_collector._fetch_chart_data(request)
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 30분봉 데이터 수집 실패: {e}")
            return []
    
    def _analyze_volume_trend(self, chart_data: List[Dict]) -> Dict[str, Any]:
        """거래량 추세 분석"""
        try:
            if not chart_data:
                return {'trend': 'unknown', 'decline_rate': 0.0, 'analysis': '데이터 부족'}
            
            # 최근 데이터와 과거 데이터 비교
            recent_data = chart_data[-24:]  # 최근 12시간 (24개 30분봉)
            older_data = chart_data[-72:-24] if len(chart_data) >= 72 else chart_data[:-24]  # 그 전 24시간
            
            if not older_data:
                return {'trend': 'unknown', 'decline_rate': 0.0, 'analysis': '비교 데이터 부족'}
            
            # 평균 거래량 계산
            recent_avg_volume = sum(int(d.get('volume', 0)) for d in recent_data) / len(recent_data)
            older_avg_volume = sum(int(d.get('volume', 0)) for d in older_data) / len(older_data)
            
            # 감소율 계산
            if older_avg_volume > 0:
                decline_rate = (older_avg_volume - recent_avg_volume) / older_avg_volume
            else:
                decline_rate = 0.0
            
            # 추세 판단
            if decline_rate >= 0.3:  # 30% 이상 감소
                trend = 'declining'
                analysis = f"거래량 {decline_rate*100:.1f}% 감소"
            elif decline_rate >= 0.1:  # 10% 이상 감소
                trend = 'weakening'
                analysis = f"거래량 {decline_rate*100:.1f}% 약화"
            elif decline_rate <= -0.1:  # 10% 이상 증가
                trend = 'increasing'
                analysis = f"거래량 {abs(decline_rate)*100:.1f}% 증가"
            else:
                trend = 'stable'
                analysis = "거래량 안정적"
            
            return {
                'trend': trend,
                'decline_rate': decline_rate,
                'recent_avg_volume': recent_avg_volume,
                'older_avg_volume': older_avg_volume,
                'analysis': analysis
            }
            
        except Exception as e:
            self.logger.error(f"❌ 거래량 추세 분석 실패: {e}")
            return {'trend': 'error', 'decline_rate': 0.0, 'analysis': f'분석 오류: {e}'}
    
    def _check_removal_conditions(
        self, 
        symbol: str, 
        volume_analysis: Dict, 
        stock: MonitoringStock
    ) -> bool:
        """제거 조건 확인"""
        try:
            # 조건 1: 거래량 지속적 감소
            if volume_analysis['trend'] == 'declining' and volume_analysis['decline_rate'] >= 0.3:
                self.logger.info(f"🔍 {symbol} 조건 1 충족: 거래량 대폭 감소 ({volume_analysis['decline_rate']*100:.1f}%)")
                return True
            
            # 조건 2: 등록된지 오래된 종목 (7일 이상) + 거래량 약화
            if stock.recommendation_time:
                days_since_added = (datetime.now() - stock.recommendation_time).days
                if days_since_added >= 7 and volume_analysis['trend'] in ['declining', 'weakening']:
                    self.logger.info(f"🔍 {symbol} 조건 2 충족: 오래된 종목 ({days_since_added}일) + 거래량 약화")
                    return True
            
            # 조건 3: 마지막 체크로부터 24시간 이상 경과 + 관심도 저하
            if stock.last_check_time:
                hours_since_check = (datetime.now() - stock.last_check_time).total_seconds() / 3600
                if hours_since_check >= 24 and volume_analysis['trend'] == 'declining':
                    self.logger.info(f"🔍 {symbol} 조건 3 충족: 장기간 미체크 ({hours_since_check:.1f}시간) + 관심도 저하")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 제거 조건 확인 오류: {e}")
            return False
    
    async def _remove_stocks(self, removal_candidates: List[MonitoringStock]):
        """제거 대상 종목들 처리"""
        try:
            with self.db_manager.get_session() as session:
                for stock in removal_candidates:
                    # DB에서 종목 찾기
                    db_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.id == stock.id
                    ).first()
                    
                    if db_stock:
                        # 제거 처리
                        removal_reason = f"자동 제거: 거래량 감소 및 관심도 저하"
                        db_stock.remove_monitoring(removal_reason)
                        
                        self.logger.info(f"🗑️ {db_stock.symbol}({db_stock.name}) 감시 제거 완료")
                
                # 변경사항 저장
                session.commit()
                
                self.logger.info(f"✅ 총 {len(removal_candidates)}개 종목 제거 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 종목 제거 처리 실패: {e}")
    
    def _record_success(self):
        """성공 기록"""
        try:
            with self.db_manager.get_session() as session:
                scheduler_state = MonitoringSchedulerState.get_scheduler_state(
                    session, self.scheduler_type
                )
                if scheduler_state:
                    scheduler_state.record_run_success()
                    session.commit()
            
        except Exception as e:
            self.logger.error(f"❌ 성공 기록 실패: {e}")
    
    def _record_failure(self, error_msg: str):
        """실패 기록"""
        try:
            with self.db_manager.get_session() as session:
                scheduler_state = MonitoringSchedulerState.get_scheduler_state(
                    session, self.scheduler_type
                )
                if scheduler_state:
                    scheduler_state.record_run_failure(error_msg)
                    session.commit()
            
        except Exception as e:
            self.logger.error(f"❌ 실패 기록 실패: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """스케줄러 상태 정보"""
        try:
            with self.db_manager.get_session() as session:
                scheduler_state = MonitoringSchedulerState.get_scheduler_state(
                    session, self.scheduler_type
                )
                
                removal_stocks = MonitoringStock.get_active_monitoring(
                    session, MonitoringType.REMOVAL_WATCH
                )
                
                if scheduler_state:
                    return {
                        'is_running': self.is_running,
                        'interval_seconds': scheduler_state.interval_seconds,
                        'total_runs': scheduler_state.total_runs,
                        'successful_runs': scheduler_state.successful_runs,
                        'failed_runs': scheduler_state.failed_runs,
                        'success_rate': scheduler_state.get_success_rate(),
                        'last_run_time': scheduler_state.last_run_time.isoformat() if scheduler_state.last_run_time else None,
                        'next_run_time': scheduler_state.next_run_time.isoformat() if scheduler_state.next_run_time else None,
                        'last_error': scheduler_state.last_error,
                        'monitoring_count': len(removal_stocks)
                    }
                else:
                    return {
                        'is_running': self.is_running,
                        'interval_seconds': self.interval_seconds,
                        'monitoring_count': len(removal_stocks),
                        'status': 'not_initialized'
                    }
                    
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 상태 조회 실패: {e}")
            return {'error': str(e)}