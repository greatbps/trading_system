#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 매매 플로우 관리자 - 모니터링 → 매수 → 보유 → 매도 전체 플로우
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio
import logging

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from database.models import MonitoringStock, MonitoringStatus
from data_collectors.kis_collector import KISCollector
from trading.profit_calculator import ProfitCalculator
from config import Config

class TradingFlowManager:
    """통합 매매 플로우 관리자"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.kis_collector = KISCollector(config)
        self.profit_calculator = ProfitCalculator(config, self.db_manager, self.kis_collector)
        self.logger = logging.getLogger(__name__)
        
        # 매수 설정
        self.default_buy_amount = 1000000  # 기본 매수금액 100만원
        self.max_holdings = 5  # 최대 보유종목 수
        
    async def initialize(self):
        """시스템 초기화"""
        await self.kis_collector.initialize()
        self.logger.info("매매 플로우 관리자 초기화 완료")
    
    async def check_buy_signals(self) -> List[Dict[str, Any]]:
        """매수 신호 체크 - 모니터링 종목 중 기술적 분석 기반 매수 조건 확인"""
        try:
            buy_candidates = []

            with self.db_manager.get_session() as session:
                # 활성 모니터링 종목 중 아직 매수하지 않은 종목들
                monitoring_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.buy_price.is_(None)  # 아직 매수하지 않은 종목
                ).all()

                print(f"매수 신호 체크: {len(monitoring_stocks)}개 모니터링 종목")

                for stock in monitoring_stocks:
                    print(f"📊 {stock.symbol}({stock.name}) 매수 시그널 분석 중...")

                    # 현재가 조회
                    current_price = await self.kis_collector.get_current_price(stock.symbol)
                    if not current_price:
                        print(f"  ❌ 현재가 조회 실패")
                        continue

                    # 기술적 분석을 위한 차트 데이터 수집
                    try:
                        from data_collectors.chart_data_collector import ChartDataCollector
                        chart_collector = ChartDataCollector(self.config, self.kis_collector)
                        chart_data = await chart_collector.get_chart_data(stock.symbol, period="D", count=60)

                        if not chart_data or len(chart_data) < 20:
                            print(f"  ❌ 차트 데이터 부족 (최소 20일 필요)")
                            continue

                        # 기술적 분석 수행
                        from analyzers.trading_signals import TradingSignalAnalyzer
                        signal_analyzer = TradingSignalAnalyzer()

                        # 매수 신호 확인
                        signals_df = signal_analyzer.check_buy_signals(chart_data.copy())
                        latest_signals = signal_analyzer.get_latest_signals(signals_df)

                        # 매수 조건 확인: 신호 강도 60% 이상 또는 신호 개수 3개 이상
                        signal_strength = latest_signals.get('signal_strength', 0)
                        signal_count = latest_signals.get('signal_count', 0)

                        print(f"  📈 시그널 강도: {signal_strength}%, 신호 개수: {signal_count}/5")

                        if signal_strength >= 60 or signal_count >= 3:  # 60% 이상 또는 3개 이상 신호시 매수
                            # 매수가능수량 조회
                            orderable_qty = await self.kis_collector.get_orderable_quantity(stock.symbol)
                            if not orderable_qty or orderable_qty <= 0:
                                print(f"  ❌ 매수 가능 수량 없음")
                                continue

                            # 매수 수량 계산 (기본 금액 기준)
                            target_quantity = min(self.default_buy_amount // current_price, orderable_qty)
                            if target_quantity <= 0:
                                print(f"  ❌ 매수 수량 계산 오류")
                                continue

                            buy_candidates.append({
                                'stock': stock,
                                'current_price': current_price,
                                'target_quantity': target_quantity,
                                'estimated_amount': current_price * target_quantity,
                                'signal_strength': signal_strength,
                                'signal_details': latest_signals
                            })

                            print(f"  ✅ 매수 후보 추가 - 강도: {signal_strength}%, 수량: {target_quantity:,}주")
                        else:
                            print(f"  📊 매수 조건 미충족 - 강도: {signal_strength}% < 60% 또는 신호개수 {signal_count} < 3개")

                    except Exception as e:
                        print(f"  ❌ 기술적 분석 실패: {e}")
                        continue

                print(f"매수 후보: {len(buy_candidates)}개 종목")
                return buy_candidates

        except Exception as e:
            self.logger.error(f"매수 신호 체크 중 오류: {e}")
            return []
    
    async def execute_buy_order(self, candidate: Dict[str, Any]) -> bool:
        """매수 주문 실행"""
        try:
            stock = candidate['stock']
            target_quantity = candidate['target_quantity']
            current_price = candidate['current_price']
            
            # KIS API를 통한 실제 매수 주문
            order_result = await self.kis_collector.place_order(
                symbol=stock.symbol,
                order_type="01",  # 시장가
                side="BUY",
                quantity=target_quantity,
                price=current_price
            )
            
            if order_result and order_result.get('success'):
                # 매수 성공시 DB 업데이트
                with self.db_manager.get_session() as session:
                    monitoring_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.id == stock.id
                    ).first()
                    
                    if monitoring_stock:
                        monitoring_stock.buy_price = current_price
                        monitoring_stock.buy_quantity = target_quantity
                        monitoring_stock.buy_amount = current_price * target_quantity
                        monitoring_stock.avg_price = current_price
                        monitoring_stock.holding_quantity = target_quantity
                        monitoring_stock.buy_time = datetime.now()
                        monitoring_stock.profit_loss = 0
                        monitoring_stock.profit_rate = 0.0
                        
                        session.commit()
                        
                print(f"✅ 매수 완료: {stock.symbol}({stock.name}) {target_quantity:,}주 @ {current_price:,}원")
                return True
            else:
                print(f"❌ 매수 실패: {stock.symbol}({stock.name}) - {order_result}")
                return False
                
        except Exception as e:
            self.logger.error(f"매수 주문 실행 중 오류: {e}")
            return False
    
    async def check_sell_signals(self) -> List[Dict[str, Any]]:
        """매도 신호 체크 - 보유종목 중 매도 조건 확인"""
        try:
            sell_candidates = []
            
            with self.db_manager.get_session() as session:
                # 보유 중인 종목들
                holding_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.buy_price.isnot(None),
                    MonitoringStock.holding_quantity > 0
                ).all()
                
                print(f"매도 신호 체크: {len(holding_stocks)}개 보유 종목")
                
                for stock in holding_stocks:
                    # 현재가 조회
                    current_price = await self.kis_collector.get_current_price(stock.symbol)
                    if not current_price:
                        continue
                    
                    # 손익률 계산
                    profit_rate = ((current_price - stock.buy_price) / stock.buy_price) * 100
                    
                    # 매도 조건 체크
                    should_sell = False
                    sell_reason = ""
                    
                    # 익절 조건: +10% 이상 수익
                    if profit_rate >= 10.0:
                        should_sell = True
                        sell_reason = f"익절 (+{profit_rate:.2f}%)"
                    
                    # 손절 조건: -5% 이상 손실
                    elif profit_rate <= -5.0:
                        should_sell = True
                        sell_reason = f"손절 ({profit_rate:.2f}%)"
                    
                    if should_sell:
                        sell_candidates.append({
                            'stock': stock,
                            'current_price': current_price,
                            'profit_rate': profit_rate,
                            'sell_quantity': stock.holding_quantity,
                            'sell_reason': sell_reason
                        })
                
                print(f"매도 후보: {len(sell_candidates)}개 종목")
                return sell_candidates
                
        except Exception as e:
            self.logger.error(f"매도 신호 체크 중 오류: {e}")
            return []
    
    async def execute_sell_order(self, candidate: Dict[str, Any]) -> bool:
        """매도 주문 실행"""
        try:
            stock = candidate['stock']
            sell_quantity = candidate['sell_quantity']
            current_price = candidate['current_price']
            sell_reason = candidate['sell_reason']
            
            # KIS API를 통한 실제 매도 주문
            order_result = await self.kis_collector.place_order(
                symbol=stock.symbol,
                order_type="01",  # 시장가
                side="SELL", 
                quantity=sell_quantity,
                price=current_price
            )
            
            if order_result and order_result.get('success'):
                # 매도 성공시 DB 업데이트
                with self.db_manager.get_session() as session:
                    monitoring_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.id == stock.id
                    ).first()
                    
                    if monitoring_stock:
                        # 최종 손익 계산
                        final_profit_loss = (current_price - stock.buy_price) * sell_quantity
                        final_profit_rate = ((current_price - stock.buy_price) / stock.buy_price) * 100
                        
                        # current_price는 DB에 저장하지 않음 - 실시간 조회만 사용
                        monitoring_stock.profit_loss = final_profit_loss
                        monitoring_stock.profit_rate = final_profit_rate
                        monitoring_stock.sell_time = datetime.now()
                        monitoring_stock.holding_quantity = 0
                        monitoring_stock.status = MonitoringStatus.COMPLETED
                        monitoring_stock.completed_time = datetime.now()
                        monitoring_stock.remove_reason = sell_reason
                        
                        session.commit()
                        
                print(f"✅ 매도 완료: {stock.symbol}({stock.name}) {sell_quantity:,}주 @ {current_price:,}원 ({sell_reason})")
                return True
            else:
                print(f"❌ 매도 실패: {stock.symbol}({stock.name}) - {order_result}")
                return False
                
        except Exception as e:
            self.logger.error(f"매도 주문 실행 중 오류: {e}")
            return False
    
    async def update_holdings_profit_loss(self) -> Dict[str, Any]:
        """보유종목 손익 실시간 업데이트"""
        return await self.profit_calculator.update_all_holdings_profit_loss()
    
    async def run_trading_cycle(self) -> Dict[str, Any]:
        """전체 매매 사이클 실행"""
        results = {
            'buy_executed': 0,
            'sell_executed': 0, 
            'profit_updated': 0,
            'errors': []
        }
        
        try:
            print("매매 사이클 시작")
            print("=" * 50)
            
            # 1. 보유종목 손익 업데이트
            print("\n1단계: 보유종목 손익 업데이트")
            profit_result = await self.update_holdings_profit_loss()
            results['profit_updated'] = profit_result.get('updated_count', 0)
            
            # 2. 매도 신호 체크 및 실행 (먼저 처리)
            print("\n2단계: 매도 신호 체크 및 실행")
            sell_candidates = await self.check_sell_signals()
            for candidate in sell_candidates:
                success = await self.execute_sell_order(candidate)
                if success:
                    results['sell_executed'] += 1
            
            # 3. 매수 신호 체크 및 실행
            print("\n3단계: 매수 신호 체크 및 실행")
            buy_candidates = await self.check_buy_signals()
            
            # 현재 보유종목 수 확인
            with self.db_manager.get_session() as session:
                current_holdings = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.holding_quantity > 0
                ).count()
                
                available_slots = self.max_holdings - current_holdings
                print(f"매수 가능 슬롯: {available_slots}개")
                
                # 매수 실행 (최대 보유종목 수 제한)
                executed_buys = 0
                for candidate in buy_candidates[:available_slots]:
                    success = await self.execute_buy_order(candidate)
                    if success:
                        results['buy_executed'] += 1
                        executed_buys += 1
            
            print(f"\n매매 사이클 완료: 매수 {results['buy_executed']}건, 매도 {results['sell_executed']}건")
            return results
            
        except Exception as e:
            error_msg = f"매매 사이클 실행 중 오류: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """포트폴리오 현재 상태 조회"""
        try:
            with self.db_manager.get_session() as session:
                # 보유종목 조회
                holdings = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.holding_quantity > 0
                ).all()
                
                # 모니터링 중인 종목 (아직 매수하지 않은)
                monitoring = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.buy_price.is_(None)
                ).count()
                
                # 완료된 거래
                completed = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.COMPLETED
                ).count()
                
                total_investment = 0
                total_current_value = 0
                total_profit_loss = 0
                
                for stock in holdings:
                    if stock.buy_amount:
                        total_investment += stock.buy_amount
                    if stock.current_price and stock.holding_quantity:
                        current_value = stock.current_price * stock.holding_quantity
                        total_current_value += current_value
                    if stock.profit_loss:
                        total_profit_loss += stock.profit_loss
                
                return {
                    'holdings_count': len(holdings),
                    'monitoring_count': monitoring,
                    'completed_count': completed,
                    'total_investment': total_investment,
                    'total_current_value': total_current_value,
                    'total_profit_loss': total_profit_loss,
                    'total_profit_rate': (total_profit_loss / total_investment * 100) if total_investment > 0 else 0.0,
                    'holdings': [
                        {
                            'symbol': stock.symbol,
                            'name': stock.name,
                            'quantity': stock.holding_quantity,
                            'buy_price': stock.buy_price,
                            'current_price': stock.current_price,
                            'profit_rate': stock.profit_rate
                        }
                        for stock in holdings
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"포트폴리오 상태 조회 중 오류: {e}")
            return {}

async def main():
    """테스트 실행"""
    try:
        config = Config()
        flow_manager = TradingFlowManager(config)
        
        await flow_manager.initialize()
        
        # 매매 사이클 실행
        results = await flow_manager.run_trading_cycle()
        print(f"\n매매 사이클 결과: {results}")
        
        # 포트폴리오 상태 조회
        portfolio = await flow_manager.get_portfolio_status()
        print(f"\n포트폴리오 상태:")
        print(f"  보유종목: {portfolio.get('holdings_count', 0)}개")
        print(f"  모니터링: {portfolio.get('monitoring_count', 0)}개")
        print(f"  완료거래: {portfolio.get('completed_count', 0)}개")
        print(f"  총투자금: {portfolio.get('total_investment', 0):,}원")
        print(f"  현재평가: {portfolio.get('total_current_value', 0):,}원")
        print(f"  총손익: {portfolio.get('total_profit_loss', 0):+,}원")
        print(f"  수익률: {portfolio.get('total_profit_rate', 0):+.2f}%")
        
    except Exception as e:
        print(f"테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())