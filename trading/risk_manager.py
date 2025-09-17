#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/risk_manager.py

Risk Manager - 리스크 관리 및 손절/익절 자동화
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from enum import Enum

from utils.logger import get_logger
from database.models import Trade, TradeType, OrderStatus, OrderType


class RiskLevel(Enum):
    """위험 수준"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StopLossType(Enum):
    """손절 유형"""
    FIXED_PRICE = "FIXED_PRICE"      # 고정 가격
    PERCENTAGE = "PERCENTAGE"        # 비율 기반
    TRAILING = "TRAILING"            # 트레일링 스탑
    ATR_BASED = "ATR_BASED"         # ATR 기반


class RiskManager:
    """Risk Manager - 리스크 관리 및 자동 손절/익절"""
    
    def __init__(self, config, kis_collector, position_manager, trading_executor, db_manager=None):
        self.config = config
        self.kis_collector = kis_collector
        self.position_manager = position_manager
        self.trading_executor = trading_executor
        self.db_manager = db_manager
        self.logger = get_logger("RiskManager")
        
        # 리스크 관리 설정
        self.max_daily_loss = getattr(config.risk, 'MAX_DAILY_LOSS', 500000)  # 50만원
        self.max_position_loss = getattr(config.risk, 'MAX_POSITION_LOSS', 200000)  # 20만원
        self.default_stop_loss_pct = getattr(config.risk, 'DEFAULT_STOP_LOSS_PCT', 5.0)  # 5%
        self.default_take_profit_pct = getattr(config.risk, 'DEFAULT_TAKE_PROFIT_PCT', 10.0)  # 10%
        self.max_portfolio_risk = getattr(config.risk, 'MAX_PORTFOLIO_RISK', 0.02)  # 2%
        
        # 활성 리스크 룰
        self._active_stop_orders = {}  # {symbol: stop_order_info}
        self._daily_pnl = 0
        self._risk_monitoring_active = True
        
        self.logger.info("✅ RiskManager 초기화 완료")
    
    async def assess_portfolio_risk(self) -> Dict[str, Any]:
        """포트폴리오 전체 리스크 평가"""
        try:
            self.logger.info("📊 포트폴리오 리스크 평가 시작...")
            
            # 포트폴리오 메트릭 조회
            portfolio_metrics = await self.position_manager.calculate_portfolio_metrics()
            
            # 개별 포지션 리스크 평가
            positions = await self.position_manager.get_all_positions()
            position_risks = {}
            
            for symbol, position in positions.items():
                position_risk = await self._assess_position_risk(symbol, position)
                position_risks[symbol] = position_risk
            
            # 전체 리스크 레벨 결정
            overall_risk = self._determine_overall_risk_level(portfolio_metrics, position_risks)
            
            # 일일 손익 확인
            daily_pnl = await self._calculate_daily_pnl()
            daily_risk = self._assess_daily_risk(daily_pnl)
            
            risk_assessment = {
                'overall_risk_level': overall_risk,
                'portfolio_value': portfolio_metrics.get('total_value', 0),
                'total_pnl': portfolio_metrics.get('total_pnl', 0),
                'daily_pnl': daily_pnl,
                'daily_risk': daily_risk,
                'position_risks': position_risks,
                'risk_limits': {
                    'max_daily_loss': self.max_daily_loss,
                    'max_position_loss': self.max_position_loss,
                    'max_portfolio_risk': self.max_portfolio_risk
                },
                'recommendations': self._generate_risk_recommendations(overall_risk, daily_pnl, position_risks),
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ 리스크 평가 완료: {overall_risk}")
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 리스크 평가 실패: {e}")
            return {'overall_risk_level': RiskLevel.MEDIUM.value, 'error': str(e)}
    
    async def setup_stop_loss_order(self, symbol: str, stop_price: int, 
                                   stop_type: StopLossType = StopLossType.FIXED_PRICE,
                                   trail_amount: Optional[int] = None) -> Dict[str, Any]:
        """손절 주문 설정"""
        try:
            self.logger.info(f"🛡️ 손절 주문 설정: {symbol} @ {stop_price:,}원 ({stop_type.value})")
            
            # 현재 포지션 확인
            position = await self.position_manager.get_position(symbol)
            if not position or position.get('quantity', 0) <= 0:
                return {'success': False, 'error': f'{symbol} 포지션을 찾을 수 없습니다'}
            
            # 손절 주문 정보 생성
            stop_order = {
                'symbol': symbol,
                'stop_price': stop_price,
                'stop_type': stop_type.value,
                'quantity': position.get('quantity'),
                'trail_amount': trail_amount,
                'created_at': datetime.now(),
                'is_active': True,
                'last_check_price': position.get('current_price', 0)
            }
            
            # 활성 손절 주문에 추가
            self._active_stop_orders[symbol] = stop_order
            
            # DB에 저장 (선택사항)
            if self.db_manager:
                await self._save_stop_order_to_db(stop_order)
            
            self.logger.info(f"✅ 손절 주문 설정 완료: {symbol}")
            return {'success': True, 'stop_order': stop_order}
            
        except Exception as e:
            self.logger.error(f"❌ 손절 주문 설정 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def setup_automatic_stop_loss(self, symbol: str, stop_loss_pct: Optional[float] = None,
                                       take_profit_pct: Optional[float] = None) -> Dict[str, Any]:
        """자동 손절/익절 설정"""
        try:
            # 현재 포지션 정보
            position = await self.position_manager.get_position(symbol)
            if not position:
                return {'success': False, 'error': f'{symbol} 포지션을 찾을 수 없습니다'}
            
            avg_price = position.get('avg_price', 0)
            current_price = position.get('current_price', avg_price)
            
            # 손절가 계산
            stop_loss_rate = stop_loss_pct or self.default_stop_loss_pct
            stop_loss_price = int(avg_price * (1 - stop_loss_rate / 100))
            
            # 익절가 계산
            take_profit_rate = take_profit_pct or self.default_take_profit_pct
            take_profit_price = int(avg_price * (1 + take_profit_rate / 100))
            
            # 손절 주문 설정
            stop_result = await self.setup_stop_loss_order(symbol, stop_loss_price, StopLossType.PERCENTAGE)
            
            result = {
                'success': stop_result['success'],
                'symbol': symbol,
                'avg_price': avg_price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'stop_loss_pct': stop_loss_rate,
                'take_profit_pct': take_profit_rate
            }
            
            if stop_result['success']:
                self.logger.info(f"✅ 자동 손절/익절 설정 완료: {symbol} 손절:{stop_loss_price:,}원 익절:{take_profit_price:,}원")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 자동 손절/익절 설정 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def monitor_stop_orders(self) -> Dict[str, Any]:
        """손절 주문 모니터링 및 실행"""
        try:
            if not self._risk_monitoring_active or not self._active_stop_orders:
                return {'monitored': 0, 'triggered': 0}
            
            self.logger.debug(f"🔍 손절 주문 모니터링: {len(self._active_stop_orders)}개")
            
            triggered_orders = []
            
            for symbol, stop_order in list(self._active_stop_orders.items()):
                if not stop_order.get('is_active'):
                    continue
                
                # 현재가 조회
                stock_info = await self.kis_collector.get_stock_info(symbol)
                if not stock_info:
                    continue
                
                current_price = stock_info.get('current_price', 0)
                if current_price <= 0:
                    continue
                
                # 손절 조건 확인
                trigger_result = await self._check_stop_trigger(stop_order, current_price)
                
                if trigger_result['triggered']:
                    # 손절 주문 실행
                    execution_result = await self._execute_stop_order(symbol, stop_order, current_price)
                    triggered_orders.append({
                        'symbol': symbol,
                        'stop_price': stop_order['stop_price'],
                        'trigger_price': current_price,
                        'execution_result': execution_result
                    })
                    
                    # 활성 주문에서 제거
                    if execution_result.get('success'):
                        self._active_stop_orders[symbol]['is_active'] = False
            
            result = {
                'monitored': len(self._active_stop_orders),
                'triggered': len(triggered_orders),
                'triggered_orders': triggered_orders,
                'timestamp': datetime.now().isoformat()
            }
            
            if triggered_orders:
                self.logger.info(f"⚡ 손절 주문 실행: {len(triggered_orders)}개")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 손절 주문 모니터링 실패: {e}")
            return {'monitored': 0, 'triggered': 0, 'error': str(e)}
    
    async def check_emergency_stop_conditions(self) -> Dict[str, Any]:
        """긴급 정지 조건 확인"""
        try:
            emergency_actions = []
            
            # 1. 일일 손실 한도 확인
            daily_pnl = await self._calculate_daily_pnl()
            if daily_pnl < -self.max_daily_loss:
                emergency_actions.append({
                    'type': 'DAILY_LOSS_LIMIT',
                    'message': f'일일 손실 한도 초과: {daily_pnl:,}원 < -{self.max_daily_loss:,}원',
                    'action': 'STOP_ALL_TRADING'
                })
            
            # 2. 개별 포지션 손실 확인
            positions = await self.position_manager.get_all_positions()
            for symbol, position in positions.items():
                unrealized_pnl = position.get('unrealized_pnl', 0)
                if unrealized_pnl < -self.max_position_loss:
                    emergency_actions.append({
                        'type': 'POSITION_LOSS_LIMIT',
                        'symbol': symbol,
                        'message': f'{symbol} 포지션 손실 한도 초과: {unrealized_pnl:,}원',
                        'action': 'FORCE_CLOSE_POSITION'
                    })
            
            # 3. 시장 위험 상황 확인 (예: 급격한 하락)
            market_risk = await self._assess_market_emergency_conditions()
            if market_risk.get('emergency'):
                emergency_actions.append({
                    'type': 'MARKET_EMERGENCY',
                    'message': market_risk.get('message', '시장 긴급 상황'),
                    'action': 'REDUCE_ALL_POSITIONS'
                })
            
            return {
                'emergency_detected': len(emergency_actions) > 0,
                'emergency_count': len(emergency_actions),
                'actions': emergency_actions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 긴급 정지 조건 확인 실패: {e}")
            return {'emergency_detected': False, 'error': str(e)}
    
    async def execute_emergency_actions(self, emergency_conditions: Dict) -> Dict[str, Any]:
        """긴급 조치 실행"""
        try:
            if not emergency_conditions.get('emergency_detected'):
                return {'executed': False, 'reason': '긴급 조건 없음'}
            
            self.logger.warning("🚨 긴급 조치 실행 시작...")
            
            executed_actions = []
            
            for action in emergency_conditions.get('actions', []):
                action_type = action.get('action')
                
                if action_type == 'STOP_ALL_TRADING':
                    # 모든 매매 중단
                    self.trading_executor.disable_trading()
                    self._risk_monitoring_active = False
                    executed_actions.append('매매 중단')
                
                elif action_type == 'FORCE_CLOSE_POSITION':
                    # 특정 포지션 강제 청산
                    symbol = action.get('symbol')
                    if symbol:
                        close_result = await self._force_close_position(symbol)
                        executed_actions.append(f'{symbol} 강제 청산: {close_result}')
                
                elif action_type == 'REDUCE_ALL_POSITIONS':
                    # 모든 포지션 50% 감축
                    reduce_result = await self._reduce_all_positions(0.5)
                    executed_actions.append(f'포지션 감축: {reduce_result}')
            
            self.logger.warning(f"🚨 긴급 조치 완료: {len(executed_actions)}개 실행")
            
            return {
                'executed': True,
                'actions_taken': executed_actions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 긴급 조치 실행 실패: {e}")
            return {'executed': False, 'error': str(e)}
    
    # === 내부 메서드들 ===
    
    async def _assess_position_risk(self, symbol: str, position: Dict) -> Dict[str, Any]:
        """개별 포지션 리스크 평가"""
        try:
            unrealized_pnl = position.get('unrealized_pnl', 0)
            unrealized_pnl_rate = position.get('unrealized_pnl_rate', 0)
            position_value = position.get('market_value', 0)
            
            # 리스크 점수 계산
            risk_score = 0
            
            # 손실 비율 기반
            if unrealized_pnl_rate < -10:
                risk_score += 30
            elif unrealized_pnl_rate < -5:
                risk_score += 15
            
            # 절대 손실 금액 기반
            if unrealized_pnl < -self.max_position_loss * 0.8:
                risk_score += 25
            elif unrealized_pnl < -self.max_position_loss * 0.5:
                risk_score += 10
            
            # 포지션 크기 기반
            if position_value > self.max_position_loss * 50:  # 1천만원
                risk_score += 10
            
            # 리스크 레벨 결정
            if risk_score >= 50:
                risk_level = RiskLevel.CRITICAL.value
            elif risk_score >= 30:
                risk_level = RiskLevel.HIGH.value
            elif risk_score >= 15:
                risk_level = RiskLevel.MEDIUM.value
            else:
                risk_level = RiskLevel.LOW.value
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_rate': unrealized_pnl_rate,
                'position_value': position_value,
                'has_stop_order': symbol in self._active_stop_orders
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 포지션 리스크 평가 실패: {e}")
            return {'risk_level': RiskLevel.MEDIUM.value, 'error': str(e)}
    
    def _determine_overall_risk_level(self, portfolio_metrics: Dict, position_risks: Dict) -> str:
        """전체 리스크 레벨 결정"""
        try:
            total_pnl_rate = portfolio_metrics.get('total_pnl_rate', 0)
            
            # 전체 손익률 기반
            portfolio_risk_score = 0
            if total_pnl_rate < -15:
                portfolio_risk_score = 40
            elif total_pnl_rate < -10:
                portfolio_risk_score = 25
            elif total_pnl_rate < -5:
                portfolio_risk_score = 10
            
            # 개별 포지션 리스크 합산
            high_risk_positions = sum(1 for risk in position_risks.values() 
                                    if risk.get('risk_level') in ['HIGH', 'CRITICAL'])
            
            if high_risk_positions > 0:
                portfolio_risk_score += high_risk_positions * 15
            
            # 최종 리스크 레벨
            if portfolio_risk_score >= 50:
                return RiskLevel.CRITICAL.value
            elif portfolio_risk_score >= 30:
                return RiskLevel.HIGH.value
            elif portfolio_risk_score >= 15:
                return RiskLevel.MEDIUM.value
            else:
                return RiskLevel.LOW.value
                
        except Exception as e:
            self.logger.error(f"❌ 전체 리스크 레벨 결정 실패: {e}")
            return RiskLevel.MEDIUM.value
    
    async def _calculate_daily_pnl(self) -> int:
        """일일 손익 계산"""
        try:
            # 오늘의 거래 이력에서 실현손익 계산
            today = datetime.now().date()
            
            if self.db_manager and hasattr(self.db_manager, 'get_daily_trades'):
                daily_trades = await self.db_manager.get_daily_trades(today)
                realized_pnl = sum(trade.get('pnl', 0) for trade in daily_trades)
            else:
                realized_pnl = 0
            
            # 현재 포지션의 미실현손익 (당일 변동분)
            positions = await self.position_manager.get_all_positions()
            unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions.values())
            
            return realized_pnl + unrealized_pnl
            
        except Exception as e:
            self.logger.error(f"❌ 일일 손익 계산 실패: {e}")
            return 0
    
    def _assess_daily_risk(self, daily_pnl: int) -> str:
        """일일 리스크 평가"""
        if daily_pnl < -self.max_daily_loss * 0.8:
            return RiskLevel.CRITICAL.value
        elif daily_pnl < -self.max_daily_loss * 0.5:
            return RiskLevel.HIGH.value
        elif daily_pnl < -self.max_daily_loss * 0.2:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value
    
    def _generate_risk_recommendations(self, overall_risk: str, daily_pnl: int, 
                                     position_risks: Dict) -> List[str]:
        """리스크 기반 추천사항 생성"""
        recommendations = []
        
        if overall_risk == RiskLevel.CRITICAL.value:
            recommendations.append("즉시 모든 포지션 검토 및 손절 고려")
            recommendations.append("신규 매수 중단")
        elif overall_risk == RiskLevel.HIGH.value:
            recommendations.append("고위험 포지션 부분 매도 고려")
            recommendations.append("포지션 크기 축소")
        
        if daily_pnl < -self.max_daily_loss * 0.5:
            recommendations.append("일일 손실 한도 접근 - 매매 중단 고려")
        
        # 고위험 포지션별 추천
        for symbol, risk in position_risks.items():
            if risk.get('risk_level') == RiskLevel.CRITICAL.value:
                recommendations.append(f"{symbol} 즉시 손절 검토")
            elif risk.get('risk_level') == RiskLevel.HIGH.value and not risk.get('has_stop_order'):
                recommendations.append(f"{symbol} 손절 주문 설정 권장")
        
        return recommendations
    
    async def _check_stop_trigger(self, stop_order: Dict, current_price: int) -> Dict[str, Any]:
        """손절 조건 확인"""
        try:
            stop_type = stop_order.get('stop_type')
            stop_price = stop_order.get('stop_price', 0)
            
            if stop_type == StopLossType.FIXED_PRICE.value:
                # 고정 가격 손절
                triggered = current_price <= stop_price
            
            elif stop_type == StopLossType.TRAILING.value:
                # 트레일링 스탑 (간소화된 구현)
                last_price = stop_order.get('last_check_price', 0)
                trail_amount = stop_order.get('trail_amount', 1000)
                
                # 가격이 상승했으면 손절가도 상향 조정
                if current_price > last_price:
                    new_stop_price = current_price - trail_amount
                    stop_order['stop_price'] = max(stop_price, new_stop_price)
                    stop_order['last_check_price'] = current_price
                
                triggered = current_price <= stop_order['stop_price']
            
            else:
                # 기본적으로 고정 가격으로 처리
                triggered = current_price <= stop_price
            
            return {
                'triggered': triggered,
                'current_price': current_price,
                'stop_price': stop_order.get('stop_price'),
                'stop_type': stop_type
            }
            
        except Exception as e:
            self.logger.error(f"❌ 손절 조건 확인 실패: {e}")
            return {'triggered': False, 'error': str(e)}
    
    async def _execute_stop_order(self, symbol: str, stop_order: Dict, trigger_price: int) -> Dict[str, Any]:
        """손절 주문 실행"""
        try:
            quantity = stop_order.get('quantity', 0)
            
            self.logger.warning(f"🛑 손절 주문 실행: {symbol} {quantity}주 @ {trigger_price:,}원")
            
            # 매도 주문 실행
            execution_result = await self.trading_executor.execute_sell_order(
                symbol=symbol,
                quantity=quantity,
                price=None,  # 시장가 매도
                order_type=OrderType.MARKET
            )
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"❌ 손절 주문 실행 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _assess_market_emergency_conditions(self) -> Dict[str, Any]:
        """시장 긴급 상황 평가"""
        try:
            # 간단한 시장 위험 평가 (실제로는 더 복잡한 로직 필요)
            # KOSPI 지수, VIX, 급락 종목 비율 등을 고려
            
            # 현재는 기본적인 구조만 제공
            return {
                'emergency': False,
                'message': '정상'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 시장 긴급 상황 평가 실패: {e}")
            return {'emergency': False, 'error': str(e)}
    
    async def _force_close_position(self, symbol: str) -> str:
        """포지션 강제 청산"""
        try:
            position = await self.position_manager.get_position(symbol)
            if not position:
                return f"{symbol} 포지션 없음"
            
            quantity = position.get('quantity', 0)
            if quantity <= 0:
                return f"{symbol} 청산할 수량 없음"
            
            # 시장가 매도
            result = await self.trading_executor.execute_sell_order(
                symbol=symbol,
                quantity=quantity,
                price=None,
                order_type=OrderType.MARKET
            )
            
            if result.get('success'):
                return f"{symbol} 청산 완료"
            else:
                return f"{symbol} 청산 실패: {result.get('error')}"
                
        except Exception as e:
            return f"{symbol} 청산 오류: {str(e)}"
    
    async def _reduce_all_positions(self, reduction_ratio: float) -> str:
        """모든 포지션 일정 비율 감축"""
        try:
            positions = await self.position_manager.get_all_positions()
            reduced_count = 0
            
            for symbol, position in positions.items():
                quantity = position.get('quantity', 0)
                if quantity > 0:
                    reduce_quantity = int(quantity * reduction_ratio)
                    if reduce_quantity > 0:
                        result = await self.trading_executor.execute_sell_order(
                            symbol=symbol,
                            quantity=reduce_quantity,
                            price=None,
                            order_type=OrderType.MARKET
                        )
                        if result.get('success'):
                            reduced_count += 1
            
            return f"{reduced_count}개 포지션 감축 완료"
            
        except Exception as e:
            return f"포지션 감축 오류: {str(e)}"
    
    async def _save_stop_order_to_db(self, stop_order: Dict):
        """손절 주문을 DB에 저장"""
        try:
            if self.db_manager and hasattr(self.db_manager, 'save_stop_order'):
                await self.db_manager.save_stop_order(stop_order)
                
        except Exception as e:
            self.logger.error(f"❌ 손절 주문 DB 저장 실패: {e}")
    
    def get_active_stop_orders(self) -> Dict[str, Dict]:
        """활성 손절 주문 조회"""
        return {symbol: order for symbol, order in self._active_stop_orders.items() 
                if order.get('is_active', False)}
    
    def enable_risk_monitoring(self):
        """리스크 모니터링 활성화"""
        self._risk_monitoring_active = True
        self.logger.info("🟢 리스크 모니터링 활성화")
    
    def disable_risk_monitoring(self):
        """리스크 모니터링 비활성화"""
        self._risk_monitoring_active = False
        self.logger.info("🔴 리스크 모니터링 비활성화")