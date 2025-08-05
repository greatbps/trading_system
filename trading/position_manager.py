#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/position_manager.py

Position Manager - 포지션 관리 및 추적
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from utils.logger import get_logger
from database.models import Portfolio, Trade, TradeType, OrderStatus


class PositionManager:
    """Position Manager - 포지션 관리 및 추적"""
    
    def __init__(self, config, kis_collector, db_manager=None):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.logger = get_logger("PositionManager")
        
        # 포지션 관리 설정
        self.max_positions = getattr(config.trading, 'MAX_POSITIONS', 10)
        self.max_position_value = getattr(config.trading, 'MAX_POSITION_VALUE', 10000000)  # 1천만원
        self.rebalance_threshold = getattr(config.trading, 'REBALANCE_THRESHOLD', 0.05)  # 5%
        
        # 포지션 캐시
        self._position_cache = {}
        self._last_update = None
        
        self.logger.info("✅ PositionManager 초기화 완료")
    
    async def get_all_positions(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """모든 포지션 조회"""
        try:
            # 캐시 확인
            if not force_refresh and self._is_cache_valid():
                self.logger.debug("📦 캐시된 포지션 정보 반환")
                return self._position_cache
            
            self.logger.info("📊 포지션 정보 업데이트 중...")
            
            # DB에서 포지션 조회
            positions = {}
            if self.db_manager:
                db_positions = await self._get_positions_from_db()
                for pos in db_positions:
                    symbol = pos.get('symbol')
                    if symbol:
                        positions[symbol] = pos
            
            # KIS API에서 실시간 가격 업데이트
            if positions:
                await self._update_positions_with_current_prices(positions)
            
            # 캐시 업데이트
            self._position_cache = positions
            self._last_update = datetime.now()
            
            self.logger.info(f"✅ 포지션 업데이트 완료: {len(positions)}개 포지션")
            return positions
            
        except Exception as e:
            self.logger.error(f"❌ 포지션 조회 실패: {e}")
            return {}
    
    async def get_position(self, symbol: str, force_refresh: bool = False) -> Optional[Dict]:
        """특정 종목 포지션 조회"""
        try:
            positions = await self.get_all_positions(force_refresh)
            return positions.get(symbol)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 포지션 조회 실패: {e}")
            return None
    
    async def update_position(self, symbol: str, trade_type: TradeType, quantity: int, 
                            price: int, commission: int = 0) -> Dict[str, Any]:
        """포지션 업데이트 (매매 발생 시)"""
        try:
            self.logger.info(f"📈 포지션 업데이트: {symbol} {trade_type.value} {quantity}주 @ {price:,}원")
            
            # 현재 포지션 조회
            current_position = await self.get_position(symbol)
            
            if trade_type == TradeType.BUY:
                updated_position = await self._handle_buy_position(
                    symbol, current_position, quantity, price, commission
                )
            else:  # SELL
                updated_position = await self._handle_sell_position(
                    symbol, current_position, quantity, price, commission
                )
            
            # DB 업데이트
            if self.db_manager and updated_position:
                await self._save_position_to_db(updated_position)
            
            # 캐시 업데이트
            if updated_position:
                self._position_cache[symbol] = updated_position
                self.logger.info(f"✅ 포지션 업데이트 완료: {symbol}")
            
            return updated_position
            
        except Exception as e:
            self.logger.error(f"❌ 포지션 업데이트 실패: {symbol} - {e}")
            return {}
    
    async def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """포트폴리오 메트릭 계산"""
        try:
            positions = await self.get_all_positions()
            
            if not positions:
                return self._get_empty_portfolio_metrics()
            
            # 기본 메트릭 계산
            total_value = sum(pos.get('market_value', 0) for pos in positions.values())
            total_cost = sum(pos.get('total_cost', 0) for pos in positions.values())
            total_pnl = total_value - total_cost
            total_pnl_rate = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            
            # 개별 종목 비중 계산
            position_weights = {}
            for symbol, pos in positions.items():
                weight = (pos.get('market_value', 0) / total_value * 100) if total_value > 0 else 0
                position_weights[symbol] = round(weight, 2)
            
            # 위험 메트릭
            risk_metrics = await self._calculate_risk_metrics(positions)
            
            return {
                'total_positions': len(positions),
                'total_value': total_value,
                'total_cost': total_cost,
                'total_pnl': total_pnl,
                'total_pnl_rate': round(total_pnl_rate, 2),
                'position_weights': position_weights,
                'largest_position': max(position_weights.values()) if position_weights else 0,
                'risk_metrics': risk_metrics,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 메트릭 계산 실패: {e}")
            return self._get_empty_portfolio_metrics()
    
    async def check_rebalancing_needed(self) -> Dict[str, Any]:
        """리밸런싱 필요 여부 확인"""
        try:
            metrics = await self.calculate_portfolio_metrics()
            position_weights = metrics.get('position_weights', {})
            
            # 목표 비중 계산 (균등 분산)
            num_positions = len(position_weights)
            if num_positions == 0:
                return {'needed': False, 'reason': '보유 포지션 없음'}
            
            target_weight = 100 / num_positions
            
            # 편차 확인
            rebalancing_suggestions = []
            max_deviation = 0
            
            for symbol, current_weight in position_weights.items():
                deviation = abs(current_weight - target_weight)
                max_deviation = max(max_deviation, deviation)
                
                if deviation > (self.rebalance_threshold * 100):
                    action = "REDUCE" if current_weight > target_weight else "INCREASE"
                    rebalancing_suggestions.append({
                        'symbol': symbol,
                        'current_weight': current_weight,
                        'target_weight': target_weight,
                        'deviation': round(deviation, 2),
                        'action': action
                    })
            
            return {
                'needed': len(rebalancing_suggestions) > 0,
                'max_deviation': round(max_deviation, 2),
                'threshold': self.rebalance_threshold * 100,
                'suggestions': rebalancing_suggestions,
                'target_weight_per_position': round(target_weight, 2)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 리밸런싱 확인 실패: {e}")
            return {'needed': False, 'error': str(e)}
    
    async def get_position_performance(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """포지션별 성과 분석"""
        try:
            position = await self.get_position(symbol)
            if not position:
                return {'error': f'{symbol} 포지션을 찾을 수 없습니다'}
            
            # 거래 이력 조회
            trade_history = await self._get_trade_history(symbol, days)
            
            # 성과 메트릭 계산
            total_buy_amount = sum(t.get('amount', 0) for t in trade_history if t.get('type') == 'BUY')
            total_sell_amount = sum(t.get('amount', 0) for t in trade_history if t.get('type') == 'SELL')
            
            realized_pnl = total_sell_amount - total_buy_amount
            unrealized_pnl = position.get('unrealized_pnl', 0)
            total_pnl = realized_pnl + unrealized_pnl
            
            return {
                'symbol': symbol,
                'position_value': position.get('market_value', 0),
                'cost_basis': position.get('total_cost', 0),
                'realized_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_pnl': total_pnl,
                'total_pnl_rate': (total_pnl / position.get('total_cost', 1) * 100),
                'trade_count': len(trade_history),
                'holding_period': self._calculate_holding_period(position),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 성과 분석 실패: {e}")
            return {'error': str(e)}
    
    # === 내부 메서드들 ===
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        if not self._last_update:
            return False
        
        cache_duration = timedelta(minutes=5)  # 5분 캐시
        return datetime.now() - self._last_update < cache_duration
    
    async def _get_positions_from_db(self) -> List[Dict]:
        """DB에서 포지션 조회"""
        try:
            if not self.db_manager:
                return []
            
            # Portfolio 테이블에서 포지션 조회
            if hasattr(self.db_manager, 'get_all_portfolio_positions'):
                positions = await self.db_manager.get_all_portfolio_positions()
                return [self._convert_portfolio_to_dict(pos) for pos in positions]
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ DB 포지션 조회 실패: {e}")
            return []
    
    async def _update_positions_with_current_prices(self, positions: Dict[str, Dict]):
        """현재가로 포지션 업데이트"""
        try:
            for symbol, position in positions.items():
                stock_info = await self.kis_collector.get_stock_info(symbol)
                if stock_info:
                    current_price = stock_info.get('current_price', 0)
                    if current_price > 0:
                        quantity = position.get('quantity', 0)
                        market_value = current_price * quantity
                        unrealized_pnl = market_value - position.get('total_cost', 0)
                        unrealized_pnl_rate = (unrealized_pnl / position.get('total_cost', 1) * 100)
                        
                        position.update({
                            'current_price': current_price,
                            'market_value': market_value,
                            'unrealized_pnl': unrealized_pnl,
                            'unrealized_pnl_rate': round(unrealized_pnl_rate, 2)
                        })
                        
        except Exception as e:
            self.logger.error(f"❌ 현재가 업데이트 실패: {e}")
    
    async def _handle_buy_position(self, symbol: str, current_position: Optional[Dict], 
                                 quantity: int, price: int, commission: int) -> Dict[str, Any]:
        """매수 포지션 처리"""
        try:
            if current_position:
                # 기존 포지션에 추가
                existing_quantity = current_position.get('quantity', 0)
                existing_cost = current_position.get('total_cost', 0)
                
                new_quantity = existing_quantity + quantity
                new_cost = existing_cost + (price * quantity) + commission
                new_avg_price = new_cost // new_quantity if new_quantity > 0 else price
                
                updated_position = current_position.copy()
                updated_position.update({
                    'quantity': new_quantity,
                    'avg_price': new_avg_price,
                    'total_cost': new_cost,
                    'last_buy_date': datetime.now(),
                    'last_update': datetime.now()
                })
            else:
                # 신규 포지션
                total_cost = (price * quantity) + commission
                updated_position = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'avg_price': price,
                    'total_cost': total_cost,
                    'current_price': price,
                    'market_value': price * quantity,
                    'unrealized_pnl': 0,
                    'unrealized_pnl_rate': 0,
                    'first_buy_date': datetime.now(),
                    'last_buy_date': datetime.now(),
                    'last_update': datetime.now()
                }
            
            return updated_position
            
        except Exception as e:
            self.logger.error(f"❌ 매수 포지션 처리 실패: {e}")
            return {}
    
    async def _handle_sell_position(self, symbol: str, current_position: Optional[Dict], 
                                  quantity: int, price: int, commission: int) -> Dict[str, Any]:
        """매도 포지션 처리"""
        try:
            if not current_position:
                self.logger.error(f"❌ {symbol} 매도하려는 포지션이 존재하지 않습니다")
                return {}
            
            existing_quantity = current_position.get('quantity', 0)
            if existing_quantity < quantity:
                self.logger.error(f"❌ {symbol} 매도 수량이 보유 수량을 초과합니다")
                return {}
            
            # 포지션 수량 차감
            new_quantity = existing_quantity - quantity
            
            # 평균단가는 유지 (FIFO 방식)
            avg_price = current_position.get('avg_price', 0)
            new_total_cost = avg_price * new_quantity
            
            # 실현손익 계산
            sell_amount = (price * quantity) - commission
            cost_basis = avg_price * quantity
            realized_pnl = sell_amount - cost_basis
            
            updated_position = current_position.copy()
            updated_position.update({
                'quantity': new_quantity,
                'total_cost': new_total_cost,
                'realized_pnl': current_position.get('realized_pnl', 0) + realized_pnl,
                'last_sell_date': datetime.now(),
                'last_update': datetime.now()
            })
            
            # 포지션 완전 청산 시
            if new_quantity == 0:
                updated_position['status'] = 'CLOSED'
            
            return updated_position
            
        except Exception as e:
            self.logger.error(f"❌ 매도 포지션 처리 실패: {e}")
            return {}
    
    async def _calculate_risk_metrics(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """위험 메트릭 계산"""
        try:
            if not positions:
                return {}
            
            # 변동성 기반 위험도 계산
            total_value = sum(pos.get('market_value', 0) for pos in positions.values())
            
            # 개별 포지션 위험도
            position_risks = {}
            for symbol, position in positions.items():
                weight = position.get('market_value', 0) / total_value if total_value > 0 else 0
                # 간단한 위험도 계산 (실제로는 변동성, 베타 등 사용)
                risk_score = min(100, weight * 100 + abs(position.get('unrealized_pnl_rate', 0)))
                position_risks[symbol] = round(risk_score, 1)
            
            # 집중도 위험
            max_weight = max(pos.get('market_value', 0) / total_value for pos in positions.values()) if total_value > 0 else 0
            concentration_risk = "HIGH" if max_weight > 0.3 else "MEDIUM" if max_weight > 0.2 else "LOW"
            
            return {
                'position_risks': position_risks,
                'concentration_risk': concentration_risk,
                'max_position_weight': round(max_weight * 100, 2),
                'diversification_score': min(100, len(positions) * 10)  # 간단한 분산도 점수
            }
            
        except Exception as e:
            self.logger.error(f"❌ 위험 메트릭 계산 실패: {e}")
            return {}
    
    async def _get_trade_history(self, symbol: str, days: int) -> List[Dict]:
        """거래 이력 조회"""
        try:
            if not self.db_manager:
                return []
            
            # 최근 N일간의 거래 이력 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            if hasattr(self.db_manager, 'get_trade_history'):
                return await self.db_manager.get_trade_history(symbol, start_date, end_date)
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ 거래 이력 조회 실패: {e}")
            return []
    
    def _calculate_holding_period(self, position: Dict) -> int:
        """보유 기간 계산 (일)"""
        try:
            first_buy_date = position.get('first_buy_date')
            if isinstance(first_buy_date, str):
                first_buy_date = datetime.fromisoformat(first_buy_date)
            elif not isinstance(first_buy_date, datetime):
                return 0
            
            return (datetime.now() - first_buy_date).days
            
        except Exception as e:
            self.logger.debug(f"⚠️ 보유 기간 계산 실패: {e}")
            return 0
    
    def _convert_portfolio_to_dict(self, portfolio_obj) -> Dict:
        """Portfolio 객체를 딕셔너리로 변환"""
        try:
            if hasattr(portfolio_obj, '__dict__'):
                return {
                    'symbol': getattr(portfolio_obj, 'symbol', ''),
                    'quantity': getattr(portfolio_obj, 'quantity', 0),
                    'avg_price': getattr(portfolio_obj, 'avg_price', 0),
                    'total_cost': getattr(portfolio_obj, 'total_cost', 0),
                    'current_price': getattr(portfolio_obj, 'current_price', 0),
                    'market_value': getattr(portfolio_obj, 'market_value', 0),
                    'unrealized_pnl': getattr(portfolio_obj, 'unrealized_pnl', 0),
                    'unrealized_pnl_rate': getattr(portfolio_obj, 'unrealized_pnl_rate', 0),
                    'realized_pnl': getattr(portfolio_obj, 'realized_pnl', 0),
                    'first_buy_date': getattr(portfolio_obj, 'first_buy_date', None),
                    'last_update': getattr(portfolio_obj, 'last_update', None)
                }
            else:
                return portfolio_obj
                
        except Exception as e:
            self.logger.error(f"❌ Portfolio 객체 변환 실패: {e}")
            return {}
    
    async def _save_position_to_db(self, position: Dict):
        """포지션을 DB에 저장"""
        try:
            if not self.db_manager or not position:
                return
            
            if hasattr(self.db_manager, 'save_portfolio_position'):
                await self.db_manager.save_portfolio_position(position)
                
        except Exception as e:
            self.logger.error(f"❌ 포지션 DB 저장 실패: {e}")
    
    def _get_empty_portfolio_metrics(self) -> Dict[str, Any]:
        """빈 포트폴리오 메트릭"""
        return {
            'total_positions': 0,
            'total_value': 0,
            'total_cost': 0,
            'total_pnl': 0,
            'total_pnl_rate': 0,
            'position_weights': {},
            'largest_position': 0,
            'risk_metrics': {},
            'last_updated': datetime.now().isoformat()
        }