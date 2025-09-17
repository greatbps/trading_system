#!/usr/bin/env python3
"""
시간대별 전략 매핑 시스템
- 기존 시스템에 영향 없는 독립 모듈
- 시간대별 최적 전략 자동 선택
"""

import sys
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# 프로젝트 루트 경로 추가
sys.path.append('D:/trading_system')

class MarketSession(Enum):
    """시장 세션 구분"""
    PRE_MARKET = "pre_market"      # 장 시작 전 (08:00-09:00)
    OPENING = "opening"            # 장 시작 (09:00-09:30)
    MORNING = "morning"            # 오전장 (09:30-11:00)
    MIDDAY = "midday"              # 점심시간 (11:00-13:00)
    AFTERNOON = "afternoon"        # 오후장 (13:00-15:00)
    CLOSING = "closing"            # 장 마감 (15:00-15:30)
    POST_MARKET = "post_market"    # 장 마감 후 (15:30-18:00)
    AFTER_HOURS = "after_hours"    # 시간 외 (18:00-08:00)

@dataclass
class StrategyConfig:
    """전략 설정"""
    strategy_id: int
    strategy_name: str
    hts_condition: str
    optimal_sessions: List[MarketSession]
    priority_score: float
    max_stocks: int
    description: str

class TimeBasedStrategyMapper:
    """시간대별 전략 매핑 시스템"""
    
    def __init__(self):
        self.strategy_configs = self._initialize_strategy_configs()
        self.session_time_map = self._initialize_session_times()
        
    def _initialize_strategy_configs(self) -> Dict[int, StrategyConfig]:
        """전략 설정 초기화"""
        
        # 기존 config.py의 HTS_CONDITION_NAMES와 매핑
        strategies = {
            1: StrategyConfig(
                strategy_id=1,
                strategy_name="momentum",
                hts_condition="momentum", 
                optimal_sessions=[MarketSession.OPENING, MarketSession.MORNING],
                priority_score=0.9,
                max_stocks=5,
                description="모멘텀 전략 - 장 시작과 오전장에 최적"
            ),
            2: StrategyConfig(
                strategy_id=2,
                strategy_name="breakout",
                hts_condition="Breakout",
                optimal_sessions=[MarketSession.MORNING, MarketSession.AFTERNOON],
                priority_score=0.85,
                max_stocks=4,
                description="돌파 전략 - 상승 돌파 시 최적"
            ),
            3: StrategyConfig(
                strategy_id=3,
                strategy_name="eod", 
                hts_condition="EOD",
                optimal_sessions=[MarketSession.CLOSING, MarketSession.POST_MARKET],
                priority_score=0.8,
                max_stocks=3,
                description="종가 전략 - 장 마감 시간에 최적"
            ),
            4: StrategyConfig(
                strategy_id=4,
                strategy_name="supertrend_ema_rsi",
                hts_condition="SuperTrend",
                optimal_sessions=[MarketSession.MORNING, MarketSession.AFTERNOON],
                priority_score=0.88,
                max_stocks=4,
                description="SuperTrend EMA RSI - 트렌드 추종"
            ),
            5: StrategyConfig(
                strategy_id=5,
                strategy_name="vwap",
                hts_condition="VWAP", 
                optimal_sessions=[MarketSession.MIDDAY, MarketSession.AFTERNOON],
                priority_score=0.82,
                max_stocks=4,
                description="VWAP 전략 - 거래량 가중 평균가 기준"
            ),
            6: StrategyConfig(
                strategy_id=6,
                strategy_name="scalping_3m",
                hts_condition="3분봉 스캘핑 전략",
                optimal_sessions=[MarketSession.OPENING, MarketSession.AFTERNOON],
                priority_score=0.75,
                max_stocks=6,
                description="3분봉 스캘핑 - 단기 매매"
            ),
            7: StrategyConfig(
                strategy_id=7,
                strategy_name="rsi",
                hts_condition="RSI (과매도과매수) 전략",
                optimal_sessions=[MarketSession.MORNING, MarketSession.CLOSING],
                priority_score=0.78,
                max_stocks=4,
                description="RSI 전략 - 과매수/과매도 구간 활용"
            ),
            8: StrategyConfig(
                strategy_id=8,
                strategy_name="squeeze_momentum_pro",
                hts_condition="Squeeze Momentum Pro",
                optimal_sessions=[MarketSession.MORNING, MarketSession.AFTERNOON, MarketSession.CLOSING],
                priority_score=0.86,
                max_stocks=4,
                description="Squeeze Momentum Pro - 변동성 돌파 전략"
            )
        }
        
        return strategies
    
    def _initialize_session_times(self) -> Dict[MarketSession, Tuple[time, time]]:
        """세션별 시간 구간 정의"""
        return {
            MarketSession.PRE_MARKET: (time(8, 0), time(9, 0)),
            MarketSession.OPENING: (time(9, 0), time(9, 30)),
            MarketSession.MORNING: (time(9, 30), time(11, 0)),
            MarketSession.MIDDAY: (time(11, 0), time(13, 0)),
            MarketSession.AFTERNOON: (time(13, 0), time(15, 0)),
            MarketSession.CLOSING: (time(15, 0), time(15, 30)),
            MarketSession.POST_MARKET: (time(15, 30), time(18, 0)),
            MarketSession.AFTER_HOURS: (time(18, 0), time(8, 0)),  # 다음날까지
        }
    
    def get_current_market_session(self, current_time: datetime = None) -> MarketSession:
        """현재 시장 세션 확인"""
        if current_time is None:
            current_time = datetime.now()
        
        current_time_only = current_time.time()
        
        for session, (start_time, end_time) in self.session_time_map.items():
            if session == MarketSession.AFTER_HOURS:
                # 18:00 이후 또는 08:00 이전
                if current_time_only >= start_time or current_time_only < time(8, 0):
                    return session
            else:
                if start_time <= current_time_only < end_time:
                    return session
        
        return MarketSession.AFTER_HOURS
    
    def get_optimal_strategies_for_session(self, session: MarketSession) -> List[StrategyConfig]:
        """특정 세션에 최적인 전략들 반환 (우선순위 순)"""
        optimal_strategies = []
        
        for strategy in self.strategy_configs.values():
            if session in strategy.optimal_sessions:
                optimal_strategies.append(strategy)
        
        # 우선순위 점수로 정렬 (내림차순)
        optimal_strategies.sort(key=lambda x: x.priority_score, reverse=True)
        
        return optimal_strategies
    
    def get_best_strategy_for_now(self, current_time: datetime = None) -> Optional[StrategyConfig]:
        """현재 시점 최적 전략 1개 선택"""
        current_session = self.get_current_market_session(current_time)
        optimal_strategies = self.get_optimal_strategies_for_session(current_session)
        
        if optimal_strategies:
            return optimal_strategies[0]  # 최고 우선순위 전략
        else:
            # 세션에 최적화된 전략이 없으면 전체 중 최고 점수
            all_strategies = list(self.strategy_configs.values())
            all_strategies.sort(key=lambda x: x.priority_score, reverse=True)
            return all_strategies[0] if all_strategies else None
    
    def get_strategy_schedule_for_day(self) -> Dict[str, Dict]:
        """하루 전체 전략 스케줄 생성"""
        schedule = {}
        
        for session in MarketSession:
            session_name = session.value
            optimal_strategies = self.get_optimal_strategies_for_session(session)
            
            start_time, end_time = self.session_time_map[session]
            
            schedule[session_name] = {
                'time_range': f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}",
                'optimal_strategies': [
                    {
                        'id': s.strategy_id,
                        'name': s.strategy_name,
                        'priority': s.priority_score,
                        'max_stocks': s.max_stocks,
                        'description': s.description
                    }
                    for s in optimal_strategies
                ],
                'recommended_strategy': optimal_strategies[0].strategy_name if optimal_strategies else None
            }
        
        return schedule
    
    def test_strategy_mapping(self):
        """전략 매핑 테스트"""
        print("=== 시간대별 전략 매핑 테스트 ===")
        
        # 현재 시점 테스트
        current_session = self.get_current_market_session()
        best_strategy = self.get_best_strategy_for_now()
        
        print(f"\n[현재 상태]")
        print(f"  현재 시간: {datetime.now().strftime('%H:%M:%S')}")
        print(f"  현재 세션: {current_session.value}")
        
        if best_strategy:
            print(f"  권장 전략: {best_strategy.strategy_id}번 - {best_strategy.strategy_name}")
            print(f"  최대 종목수: {best_strategy.max_stocks}개")
            print(f"  우선순위: {best_strategy.priority_score}")
        else:
            print(f"  권장 전략: 없음")
        
        # 하루 스케줄 출력
        print(f"\n[하루 전략 스케줄]")
        schedule = self.get_strategy_schedule_for_day()
        
        for session_name, info in schedule.items():
            print(f"  {info['time_range']} ({session_name})")
            if info['recommended_strategy']:
                print(f"    권장: {info['recommended_strategy']}")
                for strategy in info['optimal_strategies'][:2]:  # 상위 2개만 표시
                    print(f"      {strategy['id']}번. {strategy['name']} (우선순위: {strategy['priority']})")
            else:
                print(f"    권장 전략 없음")
            print()

def main():
    """메인 테스트 함수"""
    mapper = TimeBasedStrategyMapper()
    mapper.test_strategy_mapping()

if __name__ == "__main__":
    main()