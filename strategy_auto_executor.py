#!/usr/bin/env python3
"""
전략 자동 실행 시스템
- 시간대별 최적 전략 자동 선택 및 실행
- 모니터링 연동으로 자동 리밸런싱
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

from time_based_strategy_mapper import TimeBasedStrategyMapper, StrategyConfig
from config import Config
from database.database_manager import DatabaseManager
from core.analysis_handlers import AnalysisHandlers

class StrategyAutoExecutor:
    """전략 자동 실행 시스템"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.strategy_mapper = TimeBasedStrategyMapper()
        self.logger = logging.getLogger('StrategyAutoExecutor')
        
        # 상태 관리
        self.is_running = False
        self.last_execution_time = None
        self.execution_interval = 30 * 60  # 30분마다 실행 (기존 모니터링 주기와 동일)
        self.current_strategy = None
        
    async def initialize_system(self):
        """시스템 초기화"""
        try:
            # Mock TradingSystem 생성 (분석 핸들러를 위해)
            class MockTradingSystem:
                def __init__(self, config, db_manager):
                    self.config = config
                    self.db_manager = db_manager
                    self.logger = logging.getLogger('MockTradingSystem')
                    
            mock_system = MockTradingSystem(self.config, self.db_manager)
            self.analysis_handlers = AnalysisHandlers(mock_system)
            
            self.logger.info("전략 자동 실행 시스템 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"시스템 초기화 실패: {e}")
            return False
    
    def should_execute_strategy(self) -> bool:
        """전략 실행 시점 확인"""
        now = datetime.now()
        
        # 첫 실행이거나 설정된 간격이 지났으면 실행
        if (self.last_execution_time is None or 
            now - self.last_execution_time >= timedelta(seconds=self.execution_interval)):
            return True
        
        return False
    
    def get_optimal_strategy_for_current_time(self) -> Optional[StrategyConfig]:
        """현재 시점 최적 전략 선택"""
        return self.strategy_mapper.get_best_strategy_for_now()
    
    async def execute_strategy_and_add_to_monitoring(self, strategy: StrategyConfig) -> bool:
        """전략 실행 및 모니터링 추가"""
        try:
            self.logger.info(f"전략 실행 시작: {strategy.strategy_id}번 - {strategy.strategy_name}")
            
            # 전략별 분석 실행
            analysis_results = await self.analysis_handlers.run_analysis_for_strategy(
                strategy.strategy_name, 
                limit=strategy.max_stocks
            )
            
            if not analysis_results:
                self.logger.warning(f"{strategy.strategy_name} 전략: 분석 결과 없음")
                return False
            
            # BUY 추천 종목만 필터링
            buy_recommendations = [
                result for result in analysis_results 
                if result.get('recommendation') in ['BUY', 'STRONG_BUY', 'WEAK_BUY']
            ]
            
            if not buy_recommendations:
                self.logger.info(f"{strategy.strategy_name} 전략: 매수 추천 종목 없음")
                return False
            
            # 모니터링에 추가 (실제 구현은 menu_handlers의 _add_recommendations_to_monitoring 로직 활용)
            success_count = await self._add_to_monitoring_system(buy_recommendations, strategy)
            
            self.logger.info(f"전략 실행 완료: {success_count}개 종목 모니터링 추가")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"전략 실행 실패: {e}")
            return False
    
    async def _add_to_monitoring_system(self, recommendations: List[Dict], strategy: StrategyConfig) -> int:
        """모니터링 시스템에 종목 추가"""
        try:
            from database.models import MonitoringStock, MonitoringType
            from datetime import datetime
            
            success_count = 0
            
            async with self.db_manager.get_async_session() as session:
                for rec in recommendations:
                    symbol = rec.get('symbol')
                    name = rec.get('name')
                    
                    # 이미 모니터링 중인지 확인
                    existing = await session.execute(
                        f"SELECT symbol FROM monitoring_stocks WHERE symbol = '{symbol}' AND monitoring_active = true"
                    )
                    if existing.fetchone():
                        continue
                    
                    # 새로운 모니터링 종목 추가
                    monitoring_stock = MonitoringStock(
                        symbol=symbol,
                        name=name,
                        target_ratio=1.0 / strategy.max_stocks,  # 균등 분배
                        current_ratio=0.0,
                        monitoring_active=True,
                        monitoring_type=MonitoringType.TRADING,
                        strategy_name=strategy.strategy_name,
                        confidence_score=rec.get('confidence', 0.75),
                        last_rebalance_date=datetime.now(),
                        notes=f"자동추가-{strategy.strategy_name}-{datetime.now().strftime('%Y%m%d_%H%M')}"
                    )
                    
                    session.add(monitoring_stock)
                    success_count += 1
                
                await session.commit()
                self.logger.info(f"모니터링 추가 완료: {success_count}개 종목")
                
            return success_count
            
        except Exception as e:
            self.logger.error(f"모니터링 추가 실패: {e}")
            return 0
    
    async def run_auto_execution_cycle(self):
        """자동 실행 주기"""
        try:
            if not self.should_execute_strategy():
                return
            
            # 현재 시점 최적 전략 선택
            optimal_strategy = self.get_optimal_strategy_for_current_time()
            if not optimal_strategy:
                self.logger.warning("현재 시점에 적합한 전략을 찾을 수 없음")
                return
            
            # 이전과 동일한 전략이면 스킵 (너무 자주 실행 방지)
            if (self.current_strategy and 
                self.current_strategy.strategy_id == optimal_strategy.strategy_id):
                self.logger.info(f"이전과 동일한 전략({optimal_strategy.strategy_name}) - 실행 스킵")
                return
            
            self.logger.info(f"전략 변경: {optimal_strategy.strategy_id}번 - {optimal_strategy.strategy_name}")
            
            # 전략 실행
            success = await self.execute_strategy_and_add_to_monitoring(optimal_strategy)
            
            if success:
                self.current_strategy = optimal_strategy
                self.last_execution_time = datetime.now()
                self.logger.info(f"전략 자동 실행 성공: {optimal_strategy.strategy_name}")
            else:
                self.logger.warning(f"전략 자동 실행 실패: {optimal_strategy.strategy_name}")
                
        except Exception as e:
            self.logger.error(f"자동 실행 주기 오류: {e}")
    
    async def start_auto_execution(self):
        """자동 실행 시작"""
        self.is_running = True
        self.logger.info("전략 자동 실행 시스템 시작")
        
        try:
            while self.is_running:
                await self.run_auto_execution_cycle()
                
                # 30초마다 체크 (실제 실행은 execution_interval에 따라)
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            self.logger.info("전략 자동 실행 시스템 중지됨")
        except Exception as e:
            self.logger.error(f"전략 자동 실행 시스템 오류: {e}")
        finally:
            self.is_running = False
    
    def stop_auto_execution(self):
        """자동 실행 중지"""
        self.is_running = False
        self.logger.info("전략 자동 실행 시스템 중지 요청")
    
    def get_current_status(self) -> Dict:
        """현재 상태 조회"""
        current_session = self.strategy_mapper.get_current_market_session()
        optimal_strategy = self.strategy_mapper.get_best_strategy_for_now()
        
        return {
            'is_running': self.is_running,
            'current_time': datetime.now().isoformat(),
            'current_session': current_session.value,
            'optimal_strategy': {
                'id': optimal_strategy.strategy_id,
                'name': optimal_strategy.strategy_name,
                'priority': optimal_strategy.priority_score,
                'max_stocks': optimal_strategy.max_stocks
            } if optimal_strategy else None,
            'current_executing_strategy': {
                'id': self.current_strategy.strategy_id,
                'name': self.current_strategy.strategy_name
            } if self.current_strategy else None,
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'next_execution_in_seconds': self.execution_interval - (
                (datetime.now() - self.last_execution_time).total_seconds()
                if self.last_execution_time else 0
            ) if self.last_execution_time else 0
        }


async def main():
    """테스트 메인 함수"""
    # 기본 설정
    config = Config()
    db_manager = DatabaseManager(config)
    
    # 자동 실행기 생성
    executor = StrategyAutoExecutor(config, db_manager)
    
    # 초기화
    if not await executor.initialize_system():
        print("시스템 초기화 실패")
        return
    
    print("=== 전략 자동 실행 시스템 테스트 ===")
    
    # 현재 상태 출력
    status = executor.get_current_status()
    print(f"\n[현재 상태]")
    print(f"  현재 시간: {status['current_time']}")
    print(f"  시장 세션: {status['current_session']}")
    
    if status['optimal_strategy']:
        print(f"  권장 전략: {status['optimal_strategy']['id']}번 - {status['optimal_strategy']['name']}")
        print(f"  우선순위: {status['optimal_strategy']['priority']}")
        print(f"  최대 종목: {status['optimal_strategy']['max_stocks']}개")
    
    # 테스트 실행 (한 번만)
    optimal_strategy = executor.strategy_mapper.get_best_strategy_for_now()
    if optimal_strategy:
        print(f"\n[테스트 실행] {optimal_strategy.strategy_name} 전략")
        success = await executor.execute_strategy_and_add_to_monitoring(optimal_strategy)
        print(f"실행 결과: {'성공' if success else '실패'}")
    
    print("\n전략 자동 실행 시스템 테스트 완료")


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )
    
    asyncio.run(main())