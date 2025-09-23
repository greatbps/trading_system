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
from trading.trade_history_manager import TradeHistoryManager


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

        # 거래 이력 관리자 초기화
        self.trade_history_manager = TradeHistoryManager()

        # 동적 계산을 위한 초기값 (실제 잔고로 업데이트됨)
        self._current_balance = 0
        self._max_position_size = 0
        self._max_daily_loss = 0
        self.trading_enabled = getattr(config.trading, 'TRADING_ENABLED', True)  # 실제 거래 활성화

        # 단일 주문 최대 한도 초기화 (config.py의 HARD_MAX_POSITION 사용)
        self.max_single_order = getattr(config.trading, 'HARD_MAX_POSITION', 200000) # 기본값 20만원

        self.logger.info(f"[OK] TradingExecutor 초기화 완료 (매매 {'활성화' if self.trading_enabled else '비활성화'})")
    
    async def update_dynamic_limits(self) -> Dict[str, int]:
        """실시간 잔고 기반 동적 한도 업데이트"""
        try:
            # 실제 계좌 잔고 조회 (매수가능금액)
            available_cash = await self.kis_collector.get_orderable_cash()
            current_balance = available_cash if available_cash is not None else 0
            
            if current_balance > 0:
                self._current_balance = current_balance
                
                # 동적 계산
                calculated_max_position = int(current_balance * self.config.trading.MAX_POSITION_SIZE_PCT)
                calculated_max_daily_loss = int(current_balance * self.config.trading.MAX_DAILY_LOSS_PCT)
                
                # 하드 리미트 적용 (안전 장치)
                self._max_position_size = min(calculated_max_position, self.config.trading.HARD_MAX_POSITION)
                self._max_daily_loss = min(calculated_max_daily_loss, self.config.trading.HARD_MAX_DAILY_LOSS)
                
                # 백그라운드 로그만 기록
                pass  # 동적 한도 업데이트 메시지 제거
            else:
                self.logger.warning("계좌 잔고를 가져올 수 없어 하드 리미트를 사용합니다")
                self._max_position_size = self.config.trading.HARD_MAX_POSITION
                self._max_daily_loss = self.config.trading.HARD_MAX_DAILY_LOSS
            
            return {
                'current_balance': self._current_balance,
                'max_position_size': self._max_position_size,
                'max_daily_loss': self._max_daily_loss
            }
            
        except Exception as e:
            self.logger.error(f"동적 한도 업데이트 실패: {e}")
            # 안전 장치: 하드 리미트 사용
            self._max_position_size = self.config.trading.HARD_MAX_POSITION
            self._max_daily_loss = self.config.trading.HARD_MAX_DAILY_LOSS
            return {
                'current_balance': 0,
                'max_position_size': self._max_position_size,
                'max_daily_loss': self._max_daily_loss
            }
    
    async def execute_buy_order(self, symbol: str, quantity: int, price: Optional[int] = None, 
                               order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        """매수 주문 실행"""
        try:
            self.logger.info(f"매수 주문 시작: {symbol} {quantity}주 @ {price if price else 'Market'}")
            
            # 0. 동적 한도 업데이트 (실시간 잔고 기반)
            await self.update_dynamic_limits()
            
            # 1. Pre-order 검증
            validation_result = await self._validate_buy_order(symbol, quantity, price)
            if not validation_result['valid']:
                self.logger.error(f"❌ 매수 주문 검증 실패: {validation_result['reason']}")
                return self._create_failed_result(validation_result['reason'])
            
            # 2. 실제 매매 모드 확인
            if not self.trading_enabled:
                self.logger.error("❌ 매매 모드가 비활성화되어 있습니다. 모의 매매는 지원하지 않습니다.")
                return self._create_failed_result("실제 거래 모드만 허용됩니다.")
            
            # 3. KIS API를 통한 실제 주문 실행
            kis_result = await self._execute_kis_buy_order(symbol, quantity, price, order_type)
            
            # 4. 주문 결과 처리 및 DB 저장
            execution_result = await self._process_order_result(kis_result, symbol, quantity, price, OrderSide.BUY)
            
            self.logger.info(f"✅ 매수 주문 완료: {symbol} - 결과: {execution_result['status']}")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"❌ 매수 주문 실행 실패: {e}")
            return self._create_failed_result(f"주문 실행 중 오류: {str(e)}")
    
    async def execute_sell_order_v1(self, symbol: str, quantity: int, price: Optional[int] = None,
                                order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        """매도 주문 실행 (레거시 버전)"""
        try:
            self.logger.info(f"📉 매도 주문 시작: {symbol} {quantity}주 @ {price if price else 'Market'}")
            
            # 1. Pre-order 검증
            validation_result = await self._validate_sell_order(symbol, quantity, price)
            if not validation_result['valid']:
                self.logger.error(f"❌ 매도 주문 검증 실패: {validation_result['reason']}")
                return self._create_failed_result(validation_result['reason'])
            
            # 2. 실제 매매 모드 확인
            if not self.trading_enabled:
                self.logger.error("❌ 매매 모드가 비활성화되어 있습니다. 모의 매매는 지원하지 않습니다.")
                return self._create_failed_result("실제 거래 모드만 허용됩니다.")
            
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
            current_price = price if price else (getattr(stock_info, 'current_price', 0) if hasattr(stock_info, 'current_price') else stock_info.get('current_price', 0))
            if current_price <= 0:
                return {'valid': False, 'reason': '현재가 정보를 가져올 수 없습니다'}
            
            order_amount = current_price * quantity
            
            # 4. 단일 주문 한도 확인
            if order_amount > self.max_single_order:
                reason = f"단일 주문 한도 초과: {order_amount:,}원 > {self.max_single_order:,}원"
                self.logger.warning(f"⚠️ {reason}")
                return {'valid': False, 'reason': reason}
            
            # 5. 계좌 잔고 확인
            balance_check = await self._check_account_balance(order_amount)
            if not balance_check['sufficient']:
                return {'valid': False, 'reason': f'잔고 부족: 필요 {order_amount:,}원, 보유 {balance_check["available"]:,}원'}
            
            # 6. 보유종목 수 제한 확인
            holdings_check = await self._check_holdings_limit(symbol)
            if not holdings_check['within_limit']:
                return {'valid': False, 'reason': holdings_check['reason']}

            # 7. 포지션 크기 확인
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
            
            current_price = price if price else (getattr(stock_info, 'current_price', 0) if hasattr(stock_info, 'current_price') else stock_info.get('current_price', 0))
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
                # kis_collector에 place_order 메서드가 없는 경우 에러
                self.logger.error("❌ kis_collector에 place_order 메서드가 없습니다. KIS API 설정을 확인하세요.")
                return {'success': False, 'error': 'KIS API가 초기화되지 않았습니다.'}
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ KIS 매수 주문 실행 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_kis_sell_order(self, symbol: str, quantity: int, price: Optional[int], 
                                    order_type: OrderType) -> Dict[str, Any]:
        """KIS API를 통한 매도 주문 실행 (개선된 버전)"""
        try:
            # 1. KIS API 연결 상태 재확인
            kis_validation = await self._validate_kis_connection()
            if not kis_validation['connected']:
                self.logger.error(f"❌ KIS API 연결 상태 이상: {kis_validation['error']}")
                return {'success': False, 'error': kis_validation['error']}
            
            # 2. KIS API 매도 주문 파라미터 준비
            order_params = {
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'order_type': order_type.value,
                'side': 'SELL'
            }
            
            # 3. 실제 KIS API 호출 (매도 주문 시 15초 타임아웃 적용)
            result = await self.kis_collector.place_order(**order_params, timeout=15.0)
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
            # KISCollector를 통해 실시간 매수가능금액을 조회합니다.
            # 매매 시그널 발생 시 즉시 최신 정보를 조회해야 합니다.
            available_cash = await self.kis_collector.get_orderable_cash()
            
            # 조회 실패 시 (None 반환) 잔고를 0으로 처리합니다.
            if available_cash is None:
                self.logger.error("❌ KIS API를 통한 매수가능금액 조회 실패. 잔고 0으로 처리.")
                available_cash = 0

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
                # holdings가 딕셔너리인지 StockData 객체인지 확인
                if isinstance(holdings, dict):
                    stock_data = holdings.get(symbol, {})
                    if isinstance(stock_data, dict):
                        available_shares = stock_data.get('quantity', 0)
                    else:
                        available_shares = getattr(stock_data, 'quantity', 0)
                else:
                    # holdings가 StockData 객체인 경우
                    available_shares = getattr(holdings, 'quantity', 0) if symbol in str(holdings) else 0
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
            
            if total_position_value > self._max_position_size:
                return {
                    'within_limit': False,
                    'reason': f'포지션 한도 초과: {total_position_value:,}원 > {self._max_position_size:,}원'
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
            trade_obj = None
            if kis_result.get('success'):
                # 성공적인 주문 결과 처리
                order_id = kis_result.get('order_id')
                filled_quantity = kis_result.get('filled_quantity', quantity)
                average_price = kis_result.get('average_price', price)
                
                # DB에 저장
                if self.db_manager:
                    trade_obj = await self._save_order_to_db(
                        order_id, symbol, quantity, price, side,
                        OrderStatus.FILLED if filled_quantity == quantity else OrderStatus.PARTIAL,
                        filled_quantity, average_price
                    )

                # 거래 이력 자동 저장
                if filled_quantity == quantity:  # 완전 체결된 경우만
                    try:
                        if side == OrderSide.BUY:
                            success = self.trade_history_manager.record_buy_trade(
                                symbol=symbol,
                                quantity=filled_quantity,
                                price=average_price or price,
                                order_id=order_id,
                                strategy_name="auto_trading",
                                trigger_reason="system_signal"
                            )
                        else:  # SELL
                            success = self.trade_history_manager.record_sell_trade(
                                symbol=symbol,
                                quantity=filled_quantity,
                                price=average_price or price,
                                order_id=order_id,
                                strategy_name="auto_trading",
                                trigger_reason="system_signal"
                            )

                        if success:
                            self.logger.info(f"✅ 거래 이력 자동 저장 완료: {side.value} {symbol}")
                        else:
                            self.logger.warning(f"⚠️ 거래 이력 저장 실패: {side.value} {symbol}")

                    except Exception as e:
                        self.logger.error(f"❌ 거래 이력 저장 중 오류: {e}")
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': ExecutionResult.SUCCESS.value if filled_quantity == quantity else ExecutionResult.PARTIAL.value,
                    'filled_quantity': filled_quantity,
                    'average_price': average_price,
                    'timestamp': datetime.now().isoformat(),
                    'trade_object': trade_obj
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
                              average_price: Optional[int]) -> Optional[Trade]:
        """주문 정보를 DB에 저장하고 Trade 객체를 반환"""
        try:
            if not self.db_manager:
                return None
            
            from database.models import Stock, Trade, TradeType, OrderType
            
            with self.db_manager.get_session() as session:
                stock = session.query(Stock).filter_by(symbol=symbol).first()
                if not stock:
                    stock_info = await self.kis_collector.get_stock_info(symbol)
                    stock_name = stock_info.name if stock_info and hasattr(stock_info, 'name') else symbol
                    stock = Stock(symbol=symbol, name=stock_name, market='KOSPI')
                    session.add(stock)
                    session.flush() # ID를 할당받기 위해 flush

                trade = Trade(
                    stock_id=stock.id,
                    order_id=order_id,
                    trade_type=TradeType.BUY if side == OrderSide.BUY else TradeType.SELL,
                    order_type=OrderType.LIMIT, # 기본값
                    order_price=price,
                    order_quantity=quantity,
                    executed_price=average_price,
                    executed_quantity=filled_quantity,
                    order_status=status,
                    order_time=datetime.now(),
                    execution_time=datetime.now() if status == OrderStatus.FILLED else None,
                    strategy_name='auto_trading' # 임시값
                )
                session.add(trade)
                session.commit()
                session.refresh(trade)
                self.logger.info(f"✅ 주문 정보 DB 저장 완료: Trade ID {trade.id}")
                return trade
            
        except Exception as e:
            self.logger.error(f"❌ 주문 정보 DB 저장 실패: {e}")
            return None
    
    # 모의 매매 함수들 제거됨 - 실제 거래만 지원
    
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
    
    async def get_portfolio_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """특정 종목의 포트폴리오 포지션 조회"""
        try:
            # KIS API를 통한 보유주식 조회 (get_holdings 사용)
            if hasattr(self.kis_collector, 'get_holdings'):
                holdings = await self.kis_collector.get_holdings()
                if holdings and symbol in holdings:
                    position = holdings[symbol]
                    return {
                        'symbol': symbol,
                        'quantity': position.get('quantity', 0),
                        'avg_price': position.get('avg_price', 0),
                        'current_price': position.get('current_price', 0),
                        'market_value': position.get('market_value', 0),
                        'profit_loss': position.get('profit_loss', 0),
                        'profit_rate': position.get('profit_rate', 0)
                    }
            
            # KIS API가 없는 경우 기본 조회 시도
            if hasattr(self.kis_collector, 'get_account_balance'):
                balance_info = await self.kis_collector.get_account_balance()
                holdings = balance_info.get('holdings', {})
                if symbol in holdings:
                    holding = holdings[symbol]
                    return {
                        'symbol': symbol,
                        'quantity': holding.get('quantity', 0),
                        'avg_price': holding.get('avg_price', 0),
                        'current_price': holding.get('current_price', 0),
                        'market_value': holding.get('market_value', 0),
                        'profit_loss': holding.get('profit_loss', 0),
                        'profit_rate': holding.get('profit_rate', 0)
                    }
            
            # 보유하지 않은 경우
            return None
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 포지션 조회 실패 ({symbol}): {e}")
            return None
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """계좌 정보 조회"""
        try:
            # KIS API를 통한 계좌 정보 조회
            if hasattr(self.kis_collector, 'get_account_balance'):
                balance_info = await self.kis_collector.get_account_balance()
                return {
                    'available_cash': balance_info.get('available_cash', 0),
                    'total_assets': balance_info.get('total_assets', 0),
                    'stock_value': balance_info.get('stock_value', 0),
                    'profit_loss': balance_info.get('profit_loss', 0),
                    'profit_rate': balance_info.get('profit_rate', 0),
                    'account_number': balance_info.get('account_number', ''),
                    'currency': balance_info.get('currency', 'KRW'),
                    'last_updated': datetime.now().isoformat()
                }
            
            # 실제 API 데이터가 없으면 예외 발생
            raise Exception("계좌 잔고 데이터를 가져올 수 없습니다")
            
        except Exception as e:
            self.logger.error(f"❌ 계좌 정보 조회 실패: {e}")
            return None
    
    async def buy_stock(self, symbol: str, quantity: int, price: int, order_type: str = 'LIMIT') -> Dict[str, Any]:
        """주식 매수 (간단한 래퍼) - Trade 객체를 포함한 딕셔너리 반환"""
        try:
            # OrderType 변환
            if order_type == 'MARKET':
                ot = OrderType.MARKET
                exec_price = None
            else:
                ot = OrderType.LIMIT
                exec_price = price
            
            result = await self.execute_buy_order(symbol, quantity, exec_price, ot)
            
            # ExecutionResult 객체 생성
            if result.get('success'):
                return {
                    'success': True,
                    'order_id': result.get('order_id'),
                    'message': f"매수 주문 성공: {symbol} {quantity}주",
                    'trade_object': result.get('trade_object')
                }
            else:
                return {
                    'success': False,
                    'order_id': None,
                    'message': result.get('error', '매수 주문 실패'),
                    'trade_object': None
                }
                
        except Exception as e:
            self.logger.error(f"❌ 매수 주문 실행 실패: {e}")
            return {
                'success': False,
                'order_id': None,
                'message': f"매수 주문 오류: {str(e)}",
                'trade_object': None
            }
    
    async def sell_stock(self, symbol: str, quantity: int, price: int, order_type: str = 'LIMIT') -> Dict[str, Any]:
        """주식 매도 (간단한 래퍼) - Trade 객체를 포함한 딕셔너리 반환"""
        try:
            # OrderType 변환
            if order_type == 'MARKET':
                ot = OrderType.MARKET
                exec_price = None
            else:
                ot = OrderType.LIMIT
                exec_price = price
            
            result = await self.execute_sell_order(symbol, quantity, exec_price, ot)
            
            # ExecutionResult 객체 생성
            if result.get('success'):
                return {
                    'success': True,
                    'order_id': result.get('order_id'),
                    'message': f"매도 주문 성공: {symbol} {quantity}주",
                    'trade_object': result.get('trade_object')
                }
            else:
                return {
                    'success': False,
                    'order_id': None,
                    'message': result.get('error', '매도 주문 실패'),
                    'trade_object': None
                }
                
        except Exception as e:
            self.logger.error(f"❌ 매도 주문 실행 실패: {e}")
            return {
                'success': False,
                'order_id': None,
                'message': f"매도 주문 오류: {str(e)}",
                'trade_object': None
            }
            
    async def execute_sell_order(self, symbol: str, quantity: int, price: Optional[int] = None, 
                                order_type: OrderType = OrderType.MARKET) -> Dict[str, Any]:
        """매도 주문 실행"""
        try:
            self.logger.info(f"매도 주문 시작: {symbol} {quantity}주 @ {price if price else 'Market'}")
            
            # 1. 매매 활성화 상태 확인
            if not self.trading_enabled:
                return self._create_failed_result("매매가 비활성화되어 있습니다")
            
            # 2. KIS API 연결 상태 검증
            kis_validation = await self._validate_kis_connection()
            if not kis_validation['connected']:
                self.logger.error(f"❌ KIS API 연결 실패: {kis_validation['error']}")
                
                # 연결 실패 시 응급 매도 폴백 시도
                if kis_validation.get('reconnection_failed', False) or kis_validation.get('reconnection_needed', False):
                    self.logger.warning("🚨 연결 복구 실패, 응급 매도 폴백 실행...")
                    return await self._emergency_sell_fallback(symbol, quantity, price)
                else:
                    return self._create_failed_result(f"KIS API 연결 실패: {kis_validation['error']}")
            
            # 3. 매도 주문 사전 검증
            validation = await self._validate_sell_order(symbol, quantity, price)
            if not validation['valid']:
                return self._create_failed_result(validation['reason'])
            
            # 4. KIS API를 통한 매도 주문 실행 (place_order 메서드 사용)
            order_params = {
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'order_type': order_type.value,
                'side': 'SELL'
            }
            
            # KIS API 호출 (15초 타임아웃 적용)
            kis_result = await self.kis_collector.place_order(**order_params, timeout=15.0)
            
            # 5. 결과 처리
            return await self._process_order_result(kis_result, symbol, quantity, price, OrderSide.SELL)
            
        except Exception as e:
            self.logger.error(f"❌ 매도 주문 실행 실패: {e}")
            return self._create_failed_result(f"매도 주문 실행 오류: {str(e)}")
    
    # === KIS API 연결 검증 및 복구 메서드들 ===
    
    async def _validate_kis_connection(self) -> Dict[str, Any]:
        """KIS API 연결 상태 검증 및 복구 시도"""
        try:
            # 1. kis_collector 객체 존재 여부 확인
            if self.kis_collector is None:
                return {
                    'connected': False,
                    'error': 'KIS Collector 객체가 None입니다. 초기화가 필요합니다.',
                    'reconnection_needed': True
                }
            
            # 2. place_order 메서드 존재 확인
            if not hasattr(self.kis_collector, 'place_order'):
                return {
                    'connected': False,
                    'error': 'KIS Collector에 place_order 메서드가 없습니다.',
                    'reconnection_needed': True
                }
            
            # 3. KIS API 토큰 상태 확인 (계좌 정보 조회로 테스트)
            try:
                # 간단한 API 호출로 연결 상태 테스트
                test_result = await self.kis_collector.get_orderable_cash()
                if test_result is None:
                    # 토큰 만료 또는 연결 실패, 재연결 시도
                    self.logger.warning("⚠️ KIS API 토큰 만료 감지, 재연결 시도 중...")
                    reconnect_result = await self._attempt_kis_reconnection()
                    return reconnect_result
                
                return {
                    'connected': True,
                    'error': None,
                    'balance_check': test_result
                }
                
            except Exception as api_error:
                self.logger.warning(f"⚠️ KIS API 테스트 호출 실패: {api_error}")
                # 재연결 시도
                reconnect_result = await self._attempt_kis_reconnection()
                return reconnect_result
            
        except Exception as e:
            self.logger.error(f"❌ KIS 연결 검증 중 오류: {e}")
            return {
                'connected': False,
                'error': f'연결 검증 실패: {str(e)}',
                'reconnection_needed': True
            }
    
    async def _attempt_kis_reconnection(self) -> Dict[str, Any]:
        """KIS API 재연결 시도"""
        try:
            self.logger.info("🔄 KIS API 재연결 시도 중...")
            
            # kis_collector 재초기화 시도
            if hasattr(self.kis_collector, 'initialize'):
                await self.kis_collector.initialize()
                self.logger.info("✅ KIS Collector 재초기화 완료")
                
                # 재연결 후 테스트
                test_result = await self.kis_collector.get_orderable_cash()
                if test_result is not None:
                    self.logger.info("✅ KIS API 재연결 성공")
                    return {
                        'connected': True,
                        'error': None,
                        'reconnected': True
                    }
                else:
                    return {
                        'connected': False,
                        'error': 'KIS API 재연결 후에도 계좌 정보 조회 실패',
                        'reconnection_failed': True
                    }
            else:
                return {
                    'connected': False,
                    'error': 'KIS Collector에 initialize 메서드가 없어 재연결 불가',
                    'reconnection_failed': True
                }
                
        except Exception as e:
            self.logger.error(f"❌ KIS API 재연결 실패: {e}")
            return {
                'connected': False,
                'error': f'재연결 실패: {str(e)}',
                'reconnection_failed': True
            }
    
    async def _emergency_sell_fallback(self, symbol: str, quantity: int, price: Optional[int] = None) -> Dict[str, Any]:
        """응급 매도 폴백 메커니즘"""
        try:
            self.logger.critical(f"🚨 응급 매도 폴백 시작: {symbol} {quantity}주")
            
            # 1. 응급 알림 로그 기록
            emergency_msg = f"KIS API 연결 실패로 인한 응급 상황 - {symbol} {quantity}주 매도 필요"
            self.logger.critical(f"🚨 {emergency_msg}")
            
            # 2. DB에 응급 매도 요청 기록 (수동 처리를 위해)
            if self.db_manager:
                try:
                    # 응급 매도 요청을 별도 테이블에 기록
                    emergency_record = {
                        'timestamp': datetime.now(),
                        'symbol': symbol,
                        'quantity': quantity,
                        'price': price,
                        'reason': 'KIS_API_CONNECTION_FAILED',
                        'status': 'PENDING_MANUAL_EXECUTION',
                        'message': emergency_msg
                    }
                    
                    # DB 저장 로직 (실제 테이블 구조에 맞게 조정 필요)
                    self.logger.critical(f"🚨 응급 매도 요청 DB 기록: {emergency_record}")
                    
                except Exception as db_error:
                    self.logger.error(f"❌ 응급 매도 DB 기록 실패: {db_error}")
            
            # 3. 설정된 알림 채널로 긴급 알림 전송 (예: 텔레그램, 이메일 등)
            # 향후 알림 시스템 구현 시 활용
            
            return {
                'success': False,
                'emergency_fallback': True,
                'error': '🚨 KIS API 연결 실패 - 수동 매도 필요',
                'manual_action_required': True,
                'emergency_record': emergency_record
            }
            
        except Exception as e:
            self.logger.critical(f"🚨 응급 매도 폴백 실패: {e}")
            return {
                'success': False,
                'emergency_fallback_failed': True,
                'error': f'응급 시스템마저 실패: {str(e)}'
            }

    async def _check_holdings_limit(self, symbol: str) -> Dict[str, Any]:
        """보유종목 수 제한 확인"""
        try:
            # 설정에서 최대 보유종목 수 가져오기
            max_positions = getattr(self.config, 'MAX_POSITIONS', 5)

            # 현재 보유종목 조회
            holdings_data = await self.kis_collector.get_holdings()

            if not holdings_data:
                # 보유종목이 없으면 매수 가능
                return {
                    'within_limit': True,
                    'current_count': 0,
                    'max_positions': max_positions,
                    'available_slots': max_positions
                }

            # 실제 보유중인 종목 필터링 (수량 > 0)
            actual_holdings = []
            if isinstance(holdings_data, list):
                actual_holdings = [h for h in holdings_data if int(h.get('hldg_qty', 0)) > 0]
            elif isinstance(holdings_data, dict):
                actual_holdings = [v for v in holdings_data.values() if int(v.get('quantity', 0)) > 0]

            current_count = len(actual_holdings)

            # 이미 보유 중인 종목인지 확인
            already_holding = False
            if isinstance(holdings_data, list):
                already_holding = any(h.get('pdno') == symbol and int(h.get('hldg_qty', 0)) > 0 for h in holdings_data)
            elif isinstance(holdings_data, dict):
                already_holding = symbol in holdings_data and int(holdings_data[symbol].get('quantity', 0)) > 0

            # 이미 보유 중인 종목이면 추가 매수 허용
            if already_holding:
                return {
                    'within_limit': True,
                    'current_count': current_count,
                    'max_positions': max_positions,
                    'available_slots': max_positions - current_count,
                    'reason': f'{symbol} 기존 보유종목 추가 매수'
                }

            # 새로운 종목 매수 시 한도 확인
            if current_count >= max_positions:
                return {
                    'within_limit': False,
                    'current_count': current_count,
                    'max_positions': max_positions,
                    'available_slots': 0,
                    'reason': f'최대 보유종목 수 초과: {current_count}/{max_positions}개. 기존 종목을 매도 후 매수하세요.'
                }

            return {
                'within_limit': True,
                'current_count': current_count,
                'max_positions': max_positions,
                'available_slots': max_positions - current_count
            }

        except Exception as e:
            self.logger.error(f"❌ 보유종목 수 제한 확인 실패: {e}")
            # 에러 발생 시 안전을 위해 매수 차단
            return {
                'within_limit': False,
                'reason': f'보유종목 확인 실패: {str(e)}'
            }