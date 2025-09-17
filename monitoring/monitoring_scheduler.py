"""
모니터링 제외 스케줄러 (Monitoring Removal Scheduler)
==================================================

30분 간격으로 실행되어 감시 중인 종목들의 종합 점수를 평가하고
Buy 신호가 사라진 종목을 감시에서 자동 제외하는 시스템

매매 모니터링과는 별개로 동작하는 감시 관리 전용 시스템

주요 기능:
- 30분 간격 자동 실행
- 30분봉 거래량 증가 분석 포함
- 종합 점수 기반 감시 제외 판단
- DB 영속성 지원 (재시작 후에도 유지)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from analyzers.volume_analyzer import VolumeAnalyzer, MonitoringScoreCalculator
from analyzers.technical_indicators import RealTechnicalIndicators
from data_collectors.chart_data_collector import ChartDataCollector
from database.monitoring_models import (
    MonitoringStock, MonitoringScoreHistory, RemovalCondition,
    MonitoringStatus, RemovalReason, create_monitoring_tables, get_monitoring_stats
)
import traceback


@dataclass
class MonitoringRemovalResult:
    """감시 제외 결과"""
    symbol: str
    name: str
    removed: bool
    removal_reason: str
    final_score: float
    detailed_scores: Dict[str, float]
    calculation_time: datetime


class MonitoringRemovalScheduler:
    """
    감시 제외 전용 스케줄러
    
    매매 모니터링과 분리된 독립적인 시스템으로
    30분마다 감시 중인 종목들의 종합 점수를 평가하여
    Buy 신호가 사라진 종목을 자동으로 감시에서 제외
    """
    
    def __init__(self, config, kis_collector):
        self.config = config
        self.kis_collector = kis_collector
        self.logger = logging.getLogger("MonitoringRemovalScheduler")
        
        # 컴포넌트 초기화
        self.chart_data_collector = ChartDataCollector(kis_collector)
        self.technical_indicators = RealTechnicalIndicators()
        self.volume_analyzer = VolumeAnalyzer()
        self.score_calculator = MonitoringScoreCalculator(
            self.technical_indicators, 
            self.volume_analyzer
        )
        
        # 데이터베이스 설정
        self.engine = create_engine(config.database.url)
        create_monitoring_tables(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 스케줄러 설정
        self.is_running = False
        self.check_interval = 1800  # 30분 (1800초)
        self.removal_threshold = 40.0  # 40점 이하 시 제외
        
        # 30분봉 거래량 분석 설정
        self.volume_surge_threshold_30m = 1.5  # 30분봉 거래량 1.5배 이상
        self.volume_decline_threshold_30m = 0.7  # 30분봉 거래량 0.7배 이하
        
        self.logger.info("🕐 모니터링 제외 스케줄러 초기화 완료 (30분 간격)")
    
    async def start_scheduler(self):
        """감시 제외 스케줄러 시작"""
        if self.is_running:
            self.logger.warning("⚠️ 감시 제외 스케줄러가 이미 실행 중입니다")
            return
        
        self.is_running = True
        self.logger.info("🚀 감시 제외 스케줄러 시작 (30분 간격)")
        
        try:
            while self.is_running:
                # 감시 제외 체크 실행
                await self._execute_removal_check()
                
                # 30분 대기
                if self.is_running:  # 중간에 중지되었는지 확인
                    self.logger.info(f"💤 다음 체크까지 {self.check_interval // 60}분 대기...")
                    await asyncio.sleep(self.check_interval)
                
        except Exception as e:
            self.logger.error(f"❌ 감시 제외 스케줄러 오류: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            self.logger.info("🔴 감시 제외 스케줄러 종료")
    
    async def stop_scheduler(self):
        """감시 제외 스케줄러 중지"""
        self.is_running = False
        self.logger.info("🛑 감시 제외 스케줄러 중지 요청")
    
    async def _execute_removal_check(self):
        """감시 제외 체크 실행"""
        try:
            session = self.SessionLocal()
            
            # 활성 감시 종목들 조회
            active_stocks = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'active'
            ).all()
            
            if not active_stocks:
                self.logger.info("ℹ️ 활성 감시 종목이 없습니다")
                session.close()
                return
            
            self.logger.info(f"🔍 {len(active_stocks)}개 종목 감시 제외 체크 시작")
            
            removal_results = []
            
            # 각 종목별 병렬 처리
            for stock in active_stocks:
                try:
                    result = await self._check_stock_for_removal(stock, session)
                    if result:
                        removal_results.append(result)
                except Exception as e:
                    self.logger.error(f"❌ {stock.symbol} 체크 실패: {e}")
                    continue
            
            # 결과 요약
            removed_count = len([r for r in removal_results if r.removed])
            kept_count = len([r for r in removal_results if not r.removed])
            
            self.logger.info(f"📊 감시 제외 체크 완료: 제거 {removed_count}개, 유지 {kept_count}개")
            
            # 상세 결과 로깅
            for result in removal_results:
                if result.removed:
                    self.logger.info(f"🗑️ {result.symbol}({result.name}) 감시 제외: {result.removal_reason}")
                else:
                    self.logger.debug(f"✅ {result.symbol}({result.name}) 감시 유지: 점수 {result.final_score:.1f}")
            
            session.commit()
            session.close()
            
        except Exception as e:
            self.logger.error(f"❌ 감시 제외 체크 실행 오류: {e}")
            traceback.print_exc()
    
    async def _check_stock_for_removal(self, stock: MonitoringStock, session: Session) -> Optional[MonitoringRemovalResult]:
        """개별 종목 감시 제외 체크"""
        try:
            symbol = stock.symbol
            
            # 1. 차트 데이터 수집 (일봉 30일)
            daily_data = await self.chart_data_collector.get_daily_chart_data(symbol, days=30)
            if not daily_data or len(daily_data) < 5:
                self.logger.warning(f"⚠️ {symbol}: 차트 데이터 부족, 감시 유지")
                return None
            
            # 2. 30분봉 데이터 수집 (거래량 증가 분석용)
            minute_30_data = await self.chart_data_collector.get_minute_chart_data(symbol, minutes=30, periods=10)
            
            # 3. 종합 점수 계산 (기존 점수 계산 시스템 사용)
            score_result = await self.score_calculator.calculate_monitoring_score(symbol, daily_data)
            
            # 4. 30분봉 거래량 분석 추가
            volume_30m_analysis = await self._analyze_30min_volume(symbol, minute_30_data)
            
            # 5. 최종 점수 조정 (30분봉 거래량 반영)
            final_score = score_result['total_score']
            detailed_scores = score_result['detailed_scores'].copy()
            
            # 30분봉 거래량 점수 추가
            detailed_scores['volume_30m_score'] = volume_30m_analysis['volume_score']
            
            # 30분봉 거래량이 급감한 경우 점수 차감
            if volume_30m_analysis['volume_declining']:
                final_score -= 15  # 15점 차감
                score_result['reason'] += " + 30분봉 거래량 급감"
            
            # 30분봉 거래량이 급증한 경우 점수 가산
            elif volume_30m_analysis['volume_surging']:
                final_score += 10  # 10점 가산
                score_result['reason'] += " + 30분봉 거래량 급증"
            
            final_score = max(0, min(100, final_score))  # 0-100 범위 보정
            
            # 6. 감시 제외 판단
            should_remove = final_score < self.removal_threshold
            removal_reason = ""
            
            if should_remove:
                if final_score < self.removal_threshold:
                    removal_reason = f"종합점수 {final_score:.1f}점 미달 (기준: {self.removal_threshold}점)"
                
                # 추가 제외 조건들
                if volume_30m_analysis['volume_declining']:
                    removal_reason += " + 30분봉 거래량 급감"
                
                if not score_result['keep_monitoring']:
                    removal_reason += " + Buy 신호 소멸"
            
            # 7. 점수 이력 저장
            score_history = MonitoringScoreHistory(
                stock_id=stock.id,
                total_score=final_score,
                technical_score=detailed_scores.get('technical_score', 0),
                volume_score=detailed_scores.get('volume_score', 0),
                trend_score=detailed_scores.get('trend_score', 0),
                momentum_score=detailed_scores.get('momentum_score', 0),
                keep_monitoring=not should_remove,
                reason=removal_reason if should_remove else f"감시 유지: 점수 {final_score:.1f}점",
                current_price=daily_data[-1].close if daily_data else None,
                current_volume=daily_data[-1].volume if daily_data else None
            )
            
            session.add(score_history)
            
            # 8. 감시 제외 처리
            if should_remove:
                stock.status = 'removed'
                stock.removed_at = datetime.now()
                stock.removal_reason = 'low_score'
                stock.removal_details = removal_reason
                
                self.logger.info(f"🚮 {symbol}({stock.name}) 감시 제외 처리: {removal_reason}")
            else:
                # 감시 유지 시 정보 업데이트
                stock.last_check_at = datetime.now()
                stock.last_score = final_score
                # current_price는 DB에 저장하지 않음 - 실시간 조회만 사용
                stock.check_count = (stock.check_count or 0) + 1
            
            # 9. 결과 반환
            return MonitoringRemovalResult(
                symbol=symbol,
                name=stock.name,
                removed=should_remove,
                removal_reason=removal_reason if should_remove else "감시 유지",
                final_score=final_score,
                detailed_scores=detailed_scores,
                calculation_time=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ {stock.symbol} 개별 체크 오류: {e}")
            return None
    
    async def _analyze_30min_volume(self, symbol: str, minute_30_data: List) -> Dict[str, Any]:
        """30분봉 거래량 분석"""
        try:
            if not minute_30_data or len(minute_30_data) < 3:
                return {
                    'volume_score': 50,  # 중립
                    'volume_surging': False,
                    'volume_declining': False,
                    'volume_trend': 'stable',
                    'analysis_success': False
                }
            
            # 거래량 데이터 추출
            volumes = [data.volume for data in minute_30_data]
            current_volume = volumes[-1]
            
            # 평균 거래량 (최근 5개 30분봉)
            if len(volumes) >= 5:
                avg_volume_5periods = sum(volumes[-5:]) / 5
            else:
                avg_volume_5periods = sum(volumes) / len(volumes)
            
            # 거래량 비율 계산
            volume_ratio = current_volume / avg_volume_5periods if avg_volume_5periods > 0 else 1.0
            
            # 거래량 패턴 분석
            volume_surging = volume_ratio >= self.volume_surge_threshold_30m  # 1.5배 이상
            volume_declining = volume_ratio <= self.volume_decline_threshold_30m  # 0.7배 이하
            
            # 거래량 트렌드 (최근 3개 vs 이전 3개)
            if len(volumes) >= 6:
                recent_avg = sum(volumes[-3:]) / 3
                previous_avg = sum(volumes[-6:-3]) / 3
                if recent_avg > previous_avg * 1.2:
                    volume_trend = 'increasing'
                elif recent_avg < previous_avg * 0.8:
                    volume_trend = 'decreasing'
                else:
                    volume_trend = 'stable'
            else:
                volume_trend = 'stable'
            
            # 30분봉 거래량 점수 계산 (0-100)
            volume_score = 50  # 기본 점수
            
            if volume_surging:
                volume_score += 25  # 거래량 급증 보너스
            elif volume_declining:
                volume_score -= 20  # 거래량 급감 페널티
            
            if volume_trend == 'increasing':
                volume_score += 15
            elif volume_trend == 'decreasing':
                volume_score -= 15
            
            volume_score = max(0, min(100, volume_score))
            
            self.logger.debug(f"{symbol}: 30분봉 거래량 분석 - 비율 {volume_ratio:.1f}x, 점수 {volume_score:.1f}")
            
            return {
                'volume_score': volume_score,
                'volume_surging': volume_surging,
                'volume_declining': volume_declining,
                'volume_trend': volume_trend,
                'volume_ratio': volume_ratio,
                'avg_volume_5periods': avg_volume_5periods,
                'current_volume': current_volume,
                'analysis_success': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 30분봉 거래량 분석 오류: {e}")
            return {
                'volume_score': 50,
                'volume_surging': False,
                'volume_declining': False,
                'volume_trend': 'stable',
                'analysis_success': False
            }
    
    async def add_stock_to_monitoring(self, symbol: str, name: str, strategy_name: str, 
                                    position_size: int = 1000000, min_score: float = 40.0) -> bool:
        """감시 종목 추가"""
        try:
            session = self.SessionLocal()
            
            # 기존 종목 확인
            existing = session.query(MonitoringStock).filter(
                MonitoringStock.symbol == symbol,
                MonitoringStock.status == 'active'
            ).first()
            
            if existing:
                self.logger.warning(f"⚠️ {symbol}({name})은 이미 감시 중입니다")
                session.close()
                return False
            
            # 새 감시 종목 추가
            new_stock = MonitoringStock(
                symbol=symbol,
                name=name,
                strategy_name=strategy_name,
                position_size=position_size,
                min_score_threshold=min_score,
                status='active'
            )
            
            session.add(new_stock)
            session.commit()
            
            self.logger.info(f"📋 감시 추가: {symbol}({name}) - {strategy_name}")
            session.close()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 감시 종목 추가 실패: {e}")
            return False
    
    async def remove_stock_from_monitoring(self, symbol: str, reason: str = "manual_remove") -> bool:
        """감시 종목 수동 제거"""
        try:
            session = self.SessionLocal()
            
            stock = session.query(MonitoringStock).filter(
                MonitoringStock.symbol == symbol,
                MonitoringStock.status == 'active'
            ).first()
            
            if not stock:
                self.logger.warning(f"⚠️ {symbol}은 활성 감시 종목이 아닙니다")
                session.close()
                return False
            
            # 감시 제거 처리
            stock.status = 'removed'
            stock.removed_at = datetime.now()
            stock.removal_reason = reason
            stock.removal_details = f"수동 제거: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            session.commit()
            
            self.logger.info(f"🗑️ 수동 감시 제거: {symbol}({stock.name})")
            session.close()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 감시 종목 제거 실패: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """현재 감시 상태 조회"""
        try:
            session = self.SessionLocal()
            stats = get_monitoring_stats(session)
            
            # 최근 제거된 종목들 (24시간 내)
            recent_removed = session.query(MonitoringStock).filter(
                MonitoringStock.status == 'removed',
                MonitoringStock.removed_at >= datetime.now() - timedelta(hours=24)
            ).all()
            
            status = {
                'scheduler_running': self.is_running,
                'check_interval_minutes': self.check_interval // 60,
                'removal_threshold': self.removal_threshold,
                'total_stocks': stats['total_stocks'],
                'active_stocks': stats['active_stocks'],
                'removed_stocks': stats['removed_stocks'],
                'avg_score': stats['avg_score'],
                'recent_removals_24h': len(recent_removed),
                'recent_removed_stocks': [
                    {
                        'symbol': stock.symbol,
                        'name': stock.name,
                        'removed_at': stock.removed_at.isoformat(),
                        'removal_reason': stock.removal_reason,
                        'last_score': stock.last_score
                    }
                    for stock in recent_removed
                ]
            }
            
            session.close()
            return status
            
        except Exception as e:
            self.logger.error(f"❌ 감시 상태 조회 실패: {e}")
            return {
                'scheduler_running': self.is_running,
                'error': str(e)
            }


# 테스트 함수
async def test_monitoring_scheduler():
    """모니터링 스케줄러 테스트"""
    from config import Config
    from data_collectors.kis_collector import KISCollector
    
    print("=== Monitoring Removal Scheduler Test ===")
    
    config = Config()
    kis_collector = KISCollector(config)
    scheduler = MonitoringRemovalScheduler(config, kis_collector)
    
    try:
        # 테스트 종목 추가
        await scheduler.add_stock_to_monitoring(
            symbol="005930",
            name="삼성전자",
            strategy_name="Buy 추천",
            position_size=1000000,
            min_score=45.0
        )
        
        # 한 번 체크 실행
        await scheduler._execute_removal_check()
        
        # 상태 확인
        status = scheduler.get_monitoring_status()
        print(f"감시 상태: 활성 {status['active_stocks']}개, 제거 {status['removed_stocks']}개")
        print("[SUCCESS] 감시 제외 스케줄러 테스트 완료!")
        
    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(test_monitoring_scheduler())