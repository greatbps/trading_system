#!/usr/bin/env python3
"""
근본적 해결책: 자동화된 거래 실행 스크립트

EOF 에러와 시간대 문제를 해결하는 완전 자동화 실행 스크립트
"""

import sys
import asyncio
import logging
import os
from datetime import datetime, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

from config import Config
from time_based_strategy_mapper import TimeBasedStrategyMapper

class AutomatedTradingRunner:
    """완전 자동화된 거래 실행기"""
    
    def __init__(self):
        self.config = Config()
        self.strategy_mapper = TimeBasedStrategyMapper()
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(f'logs/automated_trading_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def is_market_hours(self) -> bool:
        """정규장 시간 확인"""
        now = datetime.now().time()
        market_open = time(9, 0)
        market_close = time(15, 30)
        
        return market_open <= now <= market_close
        
    def should_execute_strategy(self, session_info) -> bool:
        """전략 실행 조건 확인"""
        current_time = datetime.now().time()
        
        # EOD 전략은 장 마감 후 실행
        if session_info.strategy_name == 'eod':
            return time(15, 30) <= current_time <= time(18, 0)
            
        # 기타 전략은 정규장 시간에 실행
        return self.is_market_hours()
        
    async def execute_non_interactive_trading(self):
        """비대화형 거래 실행"""
        try:
            # main.py의 TradingSystem을 비대화형 모드로 실행
            from core.trading_system import TradingSystem
            
            self.logger.info("🚀 비대화형 거래 시스템 시작")
            
            # 시스템 초기화
            trading_system = TradingSystem(self.config)
            await trading_system.initialize()
            
            # 현재 세션과 전략 확인
            current_session = self.strategy_mapper.get_current_market_session()
            optimal_strategies = self.strategy_mapper.get_optimal_strategies_for_session(current_session)
            
            if not optimal_strategies:
                self.logger.warning("현재 세션에 최적화된 전략이 없습니다")
                return
                
            strategy = optimal_strategies[0]
            self.logger.info(f"현재 세션: {current_session.value}, 전략: {strategy.strategy_name}")
            
            # 전략 실행 조건 확인
            if not self.should_execute_strategy(strategy):
                self.logger.info("현재 시간대에서 전략 실행 조건이 맞지 않습니다")
                return
                
            # 비대화형 거래 실행 - EOF 에러 방지
            await self.execute_strategy_safely(trading_system, strategy)
            
        except Exception as e:
            self.logger.error(f"거래 실행 중 오류: {e}", exc_info=True)
            
    async def execute_strategy_safely(self, trading_system, strategy):
        """안전한 전략 실행 (EOF 에러 방지)"""
        try:
            self.logger.info(f"🎯 {strategy.strategy_name} 전략 실행 시작")
            
            # HTS 조건명으로 종목 검색
            condition_name = strategy.hts_condition
            
            # 조건 검색 실행 (비대화형)
            stocks = await self.get_condition_stocks_non_interactive(trading_system, condition_name)
            
            if not stocks:
                self.logger.warning("조건 검색 결과가 없습니다")
                return
                
            # 각 종목에 대해 분석 및 거래 실행
            for stock_code in stocks[:strategy.max_stocks]:
                try:
                    await self.analyze_and_trade_stock(trading_system, stock_code, strategy)
                except Exception as e:
                    self.logger.error(f"{stock_code} 처리 중 오류: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"전략 실행 중 오류: {e}", exc_info=True)
            
    async def get_condition_stocks_non_interactive(self, trading_system, condition_name):
        """비대화형 조건 검색"""
        try:
            # DatabaseAutoTrader를 통한 조건 검색
            auto_trader = trading_system.database_auto_trader
            
            # 조건명으로 직접 검색 (input 없이)
            stocks = await auto_trader.search_stocks_by_condition(condition_name)
            
            self.logger.info(f"조건 검색 완료: {len(stocks)}개 종목 발견")
            return stocks
            
        except Exception as e:
            self.logger.error(f"조건 검색 오류: {e}")
            return []
            
    async def analyze_and_trade_stock(self, trading_system, stock_code, strategy):
        """종목 분석 및 거래"""
        try:
            self.logger.info(f"📊 {stock_code} 분석 시작")
            
            # 종합 분석 실행
            analysis_result = await trading_system.analysis_engine.analyze_comprehensive(stock_code)
            
            if not analysis_result or analysis_result.get('error'):
                self.logger.warning(f"{stock_code} 분석 실패")
                return
                
            # 거래 신호 확인
            signal = analysis_result.get('signal', 'HOLD')
            confidence = analysis_result.get('confidence', 0)
            
            self.logger.info(f"{stock_code} 분석 결과: {signal} (신뢰도: {confidence:.2f})")
            
            # 매수 신호이고 신뢰도가 충분한 경우 거래 실행
            if signal == 'BUY' and confidence >= 0.7:
                await self.execute_buy_order(trading_system, stock_code, analysis_result)
            elif signal == 'SELL' and confidence >= 0.7:
                await self.execute_sell_order(trading_system, stock_code, analysis_result)
            else:
                self.logger.info(f"{stock_code} 거래 조건 미달 - 대기")
                
        except Exception as e:
            self.logger.error(f"{stock_code} 분석/거래 오류: {e}")
            
    async def execute_buy_order(self, trading_system, stock_code, analysis_result):
        """매수 주문 실행"""
        try:
            self.logger.info(f"💰 {stock_code} 매수 주문 실행")
            
            # 포지션 사이징
            position_size = self.calculate_position_size(analysis_result)
            
            # 매수 주문
            order_result = await trading_system.place_buy_order(
                stock_code=stock_code,
                quantity=position_size,
                order_type='market'
            )
            
            if order_result and order_result.get('success'):
                self.logger.info(f"✅ {stock_code} 매수 완료: {position_size}주")
            else:
                self.logger.error(f"❌ {stock_code} 매수 실패")
                
        except Exception as e:
            self.logger.error(f"매수 주문 오류: {e}")
            
    async def execute_sell_order(self, trading_system, stock_code, analysis_result):
        """매도 주문 실행"""
        try:
            self.logger.info(f"💸 {stock_code} 매도 주문 실행")
            
            # 보유 수량 확인
            holdings = await trading_system.get_holdings(stock_code)
            
            if not holdings or holdings.get('quantity', 0) <= 0:
                self.logger.warning(f"{stock_code} 보유 수량 없음")
                return
                
            # 매도 주문
            order_result = await trading_system.place_sell_order(
                stock_code=stock_code,
                quantity=holdings['quantity'],
                order_type='market'
            )
            
            if order_result and order_result.get('success'):
                self.logger.info(f"✅ {stock_code} 매도 완료: {holdings['quantity']}주")
            else:
                self.logger.error(f"❌ {stock_code} 매도 실패")
                
        except Exception as e:
            self.logger.error(f"매도 주문 오류: {e}")
            
    def calculate_position_size(self, analysis_result):
        """포지션 크기 계산"""
        try:
            # 기본 포지션 크기 (추후 AI 기반 포지션 사이징으로 개선)
            confidence = analysis_result.get('confidence', 0.7)
            base_position = 100  # 기본 100주
            
            # 신뢰도에 따른 포지션 조정
            adjusted_position = int(base_position * confidence)
            
            return max(1, min(adjusted_position, 1000))  # 1주~1000주 제한
            
        except Exception as e:
            self.logger.error(f"포지션 크기 계산 오류: {e}")
            return 100  # 기본값
            
    async def run_scheduled_execution(self):
        """스케줄된 실행"""
        try:
            self.logger.info("📅 자동화 거래 스케줄 실행")
            
            # 시장 상황 확인
            current_session = self.strategy_mapper.get_current_market_session()
            self.logger.info(f"현재 세션: {current_session.value}")
            
            # 거래 실행
            await self.execute_non_interactive_trading()
            
        except Exception as e:
            self.logger.error(f"스케줄 실행 오류: {e}", exc_info=True)

async def main():
    """메인 실행 함수"""
    runner = AutomatedTradingRunner()
    
    # 명령행 인수 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # 스케줄 모드
        await runner.run_scheduled_execution()
    else:
        # 즉시 실행 모드
        await runner.execute_non_interactive_trading()

if __name__ == "__main__":
    # 완전 자동화 실행 - EOF 에러 없음
    asyncio.run(main())