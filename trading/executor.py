#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/executor.py

Trading Execution Module - KIS API를 통한 실제 주문 실행
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from enum import Enum

from utils.logger import get_logger
from database.models import Trade, TradeExecution, OrderStatus, OrderType, TradeType


class OrderSide(Enum):
    """주문 구분"""
    BUY = "BUY"
    SELL = "SELL"


class ExecutionResult(Enum):
    """실행 결과"""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"


class TradingExecutor:
    """Trading Executor - 실제 주문 실행 및 관리"""
    
    def __init__(self, config, kis_collector, db_manager=None):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.logger = get_logger("TradingExecutor")
        
        # 실행 설정
        self.max_position_size = getattr(config.trading, 'MAX_POSITION_SIZE', 10000000)  # 1천만원
        self.max_single_order = getattr(config.trading, 'MAX_SINGLE_ORDER', 5000000)   # 500만원
        self.trading_enabled = getattr(config.trading, 'TRADING_ENABLED', False)
        
        self.logger.info(f"✅ TradingExecutor 초기화 완료 (매매 {'활성화' if self.trading_enabled else '비활성화'})")
    
    async def execute_buy_order(self, symbol: str, quantity: int, price: Optional[int] = None, 
                               order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        """매수 주문 실행"""
        try:
            self.logger.info(f"🚀 매수 주문 시작: {symbol} {quantity}주 @ {price if price else 'Market'}")
            
            # 1. Pre-order 검증
            validation_result = await self._validate_buy_order(symbol, quantity, price)
            if not validation_result['valid']:
                self.logger.error(f"❌ 매수 주문 검증 실패: {validation_result['reason']}")
                return self._create_failed_result(validation_result['reason'])
            
            # 2. 실제 매매 모드 확인
            if not self.trading_enabled:
                self.logger.warning("⚠️ 매매 모드가 비활성화되어 있습니다. 시뮬레이션 모드로 실행합니다.")
                return await self._simulate_order(symbol, quantity, price, OrderSide.BUY, order_type)
            
            # 3. KIS API를 통한 실제 주문 실행
            kis_result = await self._execute_kis_buy_order(symbol, quantity, price, order_type)
            
            # 4. 주문 결과 처리 및 DB 저장
            execution_result = await self._process_order_result(kis_result, symbol, quantity, price, OrderSide.BUY)
            
            self.logger.info(f"✅ 매수 주문 완료: {symbol} - 결과: {execution_result['status']}")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"❌ 매수 주문 실행 실패: {e}")
            return self._create_failed_result(f"주문 실행 중 오류: {str(e)}")
    
    async def execute_sell_order(self, symbol: str, quantity: int, price: Optional[int] = None,
                                order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        """매도 주문 실행"""
        try:
            self.logger.info(f"📉 매도 주문 시작: {symbol} {quantity}주 @ {price if price else 'Market'}")
            
            # 1. Pre-order 검증
            validation_result = await self._validate_sell_order(symbol, quantity, price)
            if not validation_result['valid']:
                self.logger.error(f"❌ 매도 주문 검증 실패: {validation_result['reason']}")
                return self._create_failed_result(validation_result['reason'])
            
            # 2. 실제 매매 모드 확인
            if not self.trading_enabled:
                self.logger.warning("⚠️ 매매 모드가 비활성화되어 있습니다. 시뮬레이션 모드로 실행합니다.")
                return await self._simulate_order(symbol, quantity, price, OrderSide.SELL, order_type)
            
            # 3. KIS API를 통한 실제 주문 실행
            kis_result = await self._execute_kis_sell_order(symbol, quantity, price, order_type)
            
            # 4. 주문 결과 처리 및 DB 저장
            execution_result = await self._process_order_result(kis_result, symbol, quantity, price, OrderSide.SELL)
            
            self.logger.info(f"✅ 매도 주문 완료: {symbol} - 결과: {execution_result['status']}")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"❌ 매도 주문 실행 실패: {e}")
            return self._create_failed_result(f"주문 실행 중 오류: {str(e)}")
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """주문 취소"""
        try:
            self.logger.info(f"🚫 주문 취소 요청: {order_id}")
            
            if not self.trading_enabled:
                self.logger.warning("⚠️ 매매 모드가 비활성화되어 있습니다.")
                return self._create_failed_result("매매 모드 비활성화")
            
            # KIS API를 통한 주문 취소
            kis_result = await self._execute_kis_cancel_order(order_id)
            
            # 결과 처리
            if kis_result.get('success'):
                self.logger.info(f"✅ 주문 취소 완료: {order_id}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': ExecutionResult.CANCELLED.value,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                error_msg = kis_result.get('error', '알 수 없는 오류')
                self.logger.error(f"❌ 주문 취소 실패: {order_id} - {error_msg}")
                return self._create_failed_result(f"주문 취소 실패: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"❌ 주문 취소 중 오류: {e}")
            return self._create_failed_result(f"주문 취소 중 오류: {str(e)}")
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """주문 상태 조회"""
        try:
            self.logger.debug(f"📊 주문 상태 조회: {order_id}")
            
            # KIS API를 통한 주문 상태 조회
            kis_result = await self._get_kis_order_status(order_id)
            
            if kis_result.get('success'):
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': kis_result.get('status'),
                    'filled_quantity': kis_result.get('filled_quantity', 0),
                    'remaining_quantity': kis_result.get('remaining_quantity', 0),
                    'average_price': kis_result.get('average_price', 0),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                error_msg = kis_result.get('error', '조회 실패')
                return self._create_failed_result(f"주문 상태 조회 실패: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"❌ 주문 상태 조회 실패: {e}")
            return self._create_failed_result(f"주문 상태 조회 실패: {str(e)}")
    
    # === Pre-order 검증 메서드들 ===
    
    async def _validate_buy_order(self, symbol: str, quantity: int, price: Optional[int]) -> Dict[str, Any]:
        """매수 주문 사전 검증"""
        try:
            # 1. 기본 파라미터 검증
            if quantity <= 0:
                return {'valid': False, 'reason': '주문 수량이 유효하지 않습니다'}
            
            if price is not None and price <= 0:
                return {'valid': False, 'reason': '주문 가격이 유효하지 않습니다'}
            
            # 2. 종목 정보 확인
            stock_info = await self.kis_collector.get_stock_info(symbol)
            if not stock_info:
                return {'valid': False, 'reason': f'종목 정보를 찾을 수 없습니다: {symbol}'}
            
            # 3. 현재가 기준 주문 금액 계산
            current_price = price if price else stock_info.get('current_price', 0)
            if current_price <= 0:
                return {'valid': False, 'reason': '현재가 정보를 가져올 수 없습니다'}
            
            order_amount = current_price * quantity
            
            # 4. 단일 주문 한도 확인
            if order_amount > self.max_single_order:
                return {'valid': False, 'reason': f'단일 주문 한도 초과: {order_amount:,}원 > {self.max_single_order:,}원'}
            
            # 5. 계좌 잔고 확인
            balance_check = await self._check_account_balance(order_amount)
            if not balance_check['sufficient']:
                return {'valid': False, 'reason': f'잔고 부족: 필요 {order_amount:,}원, 보유 {balance_check["available"]:,}원'}
            
            # 6. 포지션 크기 확인
            position_check = await self._check_position_limit(symbol, order_amount)
            if not position_check['within_limit']:
                return {'valid': False, 'reason': f'포지션 한도 초과: {position_check["reason"]}'}
            
            return {
                'valid': True,
                'order_amount': order_amount,
                'current_price': current_price,
                'available_balance': balance_check['available']
            }
            
        except Exception as e:
            self.logger.error(f"❌ 매수 주문 검증 실패: {e}")
            return {'valid': False, 'reason': f'검증 중 오류: {str(e)}'}
    
    async def _validate_sell_order(self, symbol: str, quantity: int, price: Optional[int]) -> Dict[str, Any]:
        """매도 주문 사전 검증"""
        try:
            # 1. 기본 파라미터 검증
            if quantity <= 0:
                return {'valid': False, 'reason': '주문 수량이 유효하지 않습니다'}
            
            if price is not None and price <= 0:
                return {'valid': False, 'reason': '주문 가격이 유효하지 않습니다'}
            
            # 2. 보유 주식 확인
            holdings_check = await self._check_holdings(symbol, quantity)
            if not holdings_check['sufficient']:
                return {'valid': False, 'reason': f'보유 주식 부족: 필요 {quantity}주, 보유 {holdings_check["available"]}주'}
            
            # 3. 종목 정보 확인
            stock_info = await self.kis_collector.get_stock_info(symbol)
            if not stock_info:
                return {'valid': False, 'reason': f'종목 정보를 찾을 수 없습니다: {symbol}'}
            
            current_price = price if price else stock_info.get('current_price', 0)
            if current_price <= 0:
                return {'valid': False, 'reason': '현재가 정보를 가져올 수 없습니다'}
            
            expected_amount = current_price * quantity
            
            return {
                'valid': True,
                'expected_amount': expected_amount,
                'current_price': current_price,
                'available_shares': holdings_check['available']
            }
            
        except Exception as e:
            self.logger.error(f"❌ 매도 주문 검증 실패: {e}")
            return {'valid': False, 'reason': f'검증 중 오류: {str(e)}'}
    
    # === KIS API 연동 메서드들 ===
    
    async def _execute_kis_buy_order(self, symbol: str, quantity: int, price: Optional[int], 
                                   order_type: OrderType) -> Dict[str, Any]:
        """KIS API를 통한 매수 주문 실행"""
        try:
            # KIS API 매수 주문 파라미터 준비
            order_params = {
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'order_type': order_type.value,
                'side': 'BUY'
            }
            
            # 실제 KIS API 호출 (kis_collector 사용)
            if hasattr(self.kis_collector, 'place_order'):
                result = await self.kis_collector.place_order(**order_params)
            else:
                # kis_collector에 place_order 메서드가 없는 경우 임시 구현
                self.logger.warning("⚠️ kis_collector에 place_order 메서드가 없습니다. 임시 시뮬레이션으로 실행합니다.")
                result = await self._simulate_kis_order(order_params)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ KIS 매수 주문 실행 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_kis_sell_order(self, symbol: str, quantity: int, price: Optional[int], 
                                    order_type: OrderType) -> Dict[str, Any]:
        """KIS API를 통한 매도 주문 실행"""
        try:
            # KIS API 매도 주문 파라미터 준비
            order_params = {
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'order_type': order_type.value,
                'side': 'SELL'
            }
            
            # 실제 KIS API 호출
            if hasattr(self.kis_collector, 'place_order'):
                result = await self.kis_collector.place_order(**order_params)
            else:
                # kis_collector에 place_order 메서드가 없는 경우 임시 구현
                self.logger.warning("⚠️ kis_collector에 place_order 메서드가 없습니다. 임시 시뮬레이션으로 실행합니다.")
                result = await self._simulate_kis_order(order_params)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ KIS 매도 주문 실행 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_kis_cancel_order(self, order_id: str) -> Dict[str, Any]:
        """KIS API를 통한 주문 취소"""
        try:
            if hasattr(self.kis_collector, 'cancel_order'):
                result = await self.kis_collector.cancel_order(order_id)
            else:
                # 임시 시뮬레이션
                self.logger.warning("⚠️ kis_collector에 cancel_order 메서드가 없습니다.")
                result = {'success': True, 'order_id': order_id, 'status': 'CANCELLED'}
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ KIS 주문 취소 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_kis_order_status(self, order_id: str) -> Dict[str, Any]:
        """KIS API를 통한 주문 상태 조회"""
        try:
            if hasattr(self.kis_collector, 'get_order_status'):
                result = await self.kis_collector.get_order_status(order_id)
            else:
                # 임시 시뮬레이션
                result = {
                    'success': True,
                    'order_id': order_id,
                    'status': 'FILLED',
                    'filled_quantity': 100,
                    'remaining_quantity': 0,
                    'average_price': 50000
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ KIS 주문 상태 조회 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    # === 보조 메서드들 ===
    
    async def _check_account_balance(self, required_amount: int) -> Dict[str, Any]:
        """계좌 잔고 확인"""
        try:
            if hasattr(self.kis_collector, 'get_account_balance'):
                balance_info = await self.kis_collector.get_account_balance()
                available_cash = balance_info.get('available_cash', 0)
            else:
                # 임시 시뮬레이션 (충분한 잔고 가정)
                available_cash = 100000000  # 1억원
            
            return {
                'sufficient': available_cash >= required_amount,
                'available': available_cash,
                'required': required_amount
            }
            
        except Exception as e:
            self.logger.error(f"❌ 계좌 잔고 확인 실패: {e}")
            return {'sufficient': False, 'available': 0, 'required': required_amount}
    
    async def _check_holdings(self, symbol: str, required_quantity: int) -> Dict[str, Any]:
        """보유 주식 확인"""
        try:
            if hasattr(self.kis_collector, 'get_holdings'):
                holdings = await self.kis_collector.get_holdings()
                available_shares = holdings.get(symbol, {}).get('quantity', 0)
            else:
                # 임시 시뮬레이션 (충분한 보유량 가정)
                available_shares = 1000
            
            return {
                'sufficient': available_shares >= required_quantity,
                'available': available_shares,
                'required': required_quantity
            }
            
        except Exception as e:
            self.logger.error(f"❌ 보유 주식 확인 실패: {e}")
            return {'sufficient': False, 'available': 0, 'required': required_quantity}
    
    async def _check_position_limit(self, symbol: str, order_amount: int) -> Dict[str, Any]:
        """포지션 한도 확인"""
        try:
            # 현재 포지션 크기 조회 (DB 또는 KIS API)
            current_position_value = await self._get_current_position_value(symbol)
            
            total_position_value = current_position_value + order_amount
            
            if total_position_value > self.max_position_size:
                return {
                    'within_limit': False,
                    'reason': f'포지션 한도 초과: {total_position_value:,}원 > {self.max_position_size:,}원'
                }
            
            return {
                'within_limit': True,
                'current_position': current_position_value,
                'total_after_order': total_position_value
            }
            
        except Exception as e:
            self.logger.error(f"❌ 포지션 한도 확인 실패: {e}")
            return {'within_limit': False, 'reason': f'포지션 확인 실패: {str(e)}'}
    
    async def _get_current_position_value(self, symbol: str) -> int:
        """현재 포지션 가치 조회"""
        try:
            # DB에서 포트폴리오 조회 또는 KIS API 활용
            if self.db_manager and hasattr(self.db_manager, 'get_portfolio_position'):
                position = await self.db_manager.get_portfolio_position(symbol)
                if position:
                    return position.get('market_value', 0)
            
            return 0  # 포지션 없음
            
        except Exception as e:
            self.logger.debug(f"⚠️ 포지션 가치 조회 실패: {e}")
            return 0
    
    async def _process_order_result(self, kis_result: Dict, symbol: str, quantity: int, 
                                  price: Optional[int], side: OrderSide) -> Dict[str, Any]:
        """주문 결과 처리 및 DB 저장"""
        try:
            if kis_result.get('success'):
                # 성공적인 주문 결과 처리
                order_id = kis_result.get('order_id')
                filled_quantity = kis_result.get('filled_quantity', quantity)
                average_price = kis_result.get('average_price', price)
                
                # DB에 저장
                if self.db_manager:
                    await self._save_order_to_db(
                        order_id, symbol, quantity, price, side, 
                        OrderStatus.FILLED if filled_quantity == quantity else OrderStatus.PARTIAL,
                        filled_quantity, average_price
                    )
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': ExecutionResult.SUCCESS.value if filled_quantity == quantity else ExecutionResult.PARTIAL.value,
                    'filled_quantity': filled_quantity,
                    'average_price': average_price,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # 실패한 주문 처리
                error_msg = kis_result.get('error', '알 수 없는 오류')
                return self._create_failed_result(f"KIS API 오류: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"❌ 주문 결과 처리 실패: {e}")
            return self._create_failed_result(f"결과 처리 오류: {str(e)}")
    
    async def _save_order_to_db(self, order_id: str, symbol: str, quantity: int, price: Optional[int], 
                              side: OrderSide, status: OrderStatus, filled_quantity: int, 
                              average_price: Optional[int]):
        """주문 정보를 DB에 저장"""
        try:
            if not self.db_manager:
                return
            
            # Trade 테이블에 저장할 데이터 준비
            trade_data = {
                'stock_symbol': symbol,
                'trade_type': TradeType.BUY if side == OrderSide.BUY else TradeType.SELL,
                'order_type': OrderType.MARKET,  # 기본값, 실제로는 파라미터로 받아야 함
                'quantity': quantity,
                'order_price': price,
                'executed_price': average_price,
                'executed_quantity': filled_quantity,
                'order_status': status,
                'order_datetime': datetime.now(),
                'execution_datetime': datetime.now() if status == OrderStatus.FILLED else None,
                'kis_order_id': order_id
            }
            
            # DB 저장 (실제 구현은 db_manager에 따라 다름)
            if hasattr(self.db_manager, 'save_trade'):
                await self.db_manager.save_trade(trade_data)
            
            self.logger.info(f"✅ 주문 정보 DB 저장 완료: {order_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 주문 정보 DB 저장 실패: {e}")
    
    async def _simulate_order(self, symbol: str, quantity: int, price: Optional[int], 
                            side: OrderSide, order_type: OrderType) -> Dict[str, Any]:
        """시뮬레이션 모드에서의 주문 처리"""
        try:
            # 현재가 정보 가져오기
            stock_info = await self.kis_collector.get_stock_info(symbol)
            current_price = stock_info.get('current_price', 50000) if stock_info else 50000
            
            # 시뮬레이션 주문 ID 생성
            order_id = f"SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}"
            
            # 시뮬레이션 결과
            simulated_price = price if price else current_price
            
            self.logger.info(f"📊 시뮬레이션 주문: {side.value} {symbol} {quantity}주 @ {simulated_price:,}원")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': ExecutionResult.SUCCESS.value,
                'filled_quantity': quantity,
                'average_price': simulated_price,
                'simulation': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 시뮬레이션 주문 실패: {e}")
            return self._create_failed_result(f"시뮬레이션 오류: {str(e)}")
    
    async def _simulate_kis_order(self, order_params: Dict) -> Dict[str, Any]:
        """KIS API 시뮬레이션"""
        try:
            order_id = f"KIS_SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return {
                'success': True,
                'order_id': order_id,
                'filled_quantity': order_params['quantity'],
                'average_price': order_params.get('price', 50000),
                'status': 'FILLED'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_failed_result(self, reason: str) -> Dict[str, Any]:
        """실패 결과 객체 생성"""
        return {
            'success': False,
            'status': ExecutionResult.FAILED.value,
            'error': reason,
            'timestamp': datetime.now().isoformat()
        }
    
    def is_trading_enabled(self) -> bool:
        """매매 활성화 상태 확인"""
        return self.trading_enabled
    
    def enable_trading(self):
        """매매 활성화"""
        self.trading_enabled = True
        self.logger.info("🟢 매매 모드 활성화")
    
    def disable_trading(self):
        """매매 비활성화"""
        self.trading_enabled = False
        self.logger.info("🔴 매매 모드 비활성화")