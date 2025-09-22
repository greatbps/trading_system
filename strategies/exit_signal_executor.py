#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exit_signal_executor.py

고도화된 매도 신호 실행기
부분 매도, ATR 트레일링 등 처리
"""

import asyncio
from typing import Dict, List, Optional, Any
from utils.logger import get_logger

class ExitSignalExecutor:
    """매도 신호 실행기"""

    def __init__(self, config, kis_collector, executor, db_manager=None):
        self.config = config
        self.kis_collector = kis_collector
        self.executor = executor
        self.db_manager = db_manager
        self.logger = get_logger("ExitSignalExecutor")

    async def execute_exit_signal(self, symbol: str, exit_signal: Any, holding_info: Dict[str, Any] = None) -> bool:
        """매도 신호 실행"""
        try:
            # 현재 보유 수량 확인
            holdings = await self.kis_collector.get_holdings()
            if not holdings or symbol not in holdings:
                self.logger.warning(f"⚠️ {symbol} 현재 보유하지 않은 종목 - 매도 불가")
                return False

            holding = holdings[symbol]
            total_quantity = getattr(holding, 'quantity', 0)
            current_price = getattr(holding, 'current_price', 0)

            if total_quantity <= 0:
                self.logger.warning(f"⚠️ {symbol} 보유 수량 없음 - 매도 불가")
                return True  # 이미 매도된 상태

            # 매도할 수량 계산
            sell_quantity = int(total_quantity * exit_signal.quantity_ratio)
            if sell_quantity <= 0:
                self.logger.warning(f"⚠️ {symbol} 계산된 매도 수량이 0 - 매도 불가")
                return False

            self.logger.info(f"🚨 {symbol} 고도화된 매도 신호 실행:")
            self.logger.info(f"   📊 신호유형: {exit_signal.signal_type}")
            self.logger.info(f"   📈 현재가: {current_price:,}원")
            self.logger.info(f"   📦 매도수량: {sell_quantity:,}주 / 전체: {total_quantity:,}주 ({exit_signal.quantity_ratio*100:.1f}%)")
            self.logger.info(f"   🎯 사유: {exit_signal.reason}")
            self.logger.info(f"   🎲 신뢰도: {exit_signal.confidence*100:.1f}%")

            # 매도 주문 실행
            result = await self._execute_sell_order(symbol, sell_quantity, exit_signal)

            if result and result.get('success'):
                self.logger.info(f"✅ {symbol} 매도 주문 성공!")
                self.logger.info(f"   📋 주문번호: {result.get('order_id')}")

                # DB에 매도 기록 저장
                await self._record_exit_signal(symbol, exit_signal, sell_quantity, current_price)

                return True
            else:
                self.logger.error(f"❌ {symbol} 매도 주문 실패: {result.get('error', '알 수 없는 오류')}")
                return False

        except Exception as e:
            self.logger.error(f"❌ {symbol} 매도 신호 실행 실패: {e}")
            return False

    async def _execute_sell_order(self, symbol: str, quantity: int, exit_signal: Any) -> Dict[str, Any]:
        """실제 매도 주문 실행"""
        try:
            # 매도 신호 유형에 따른 주문 방식 결정
            if exit_signal.signal_type in ['hard_stop', 'trailing_stop']:
                # 손절/트레일링은 시장가로 즉시 매도
                order_type = 'MARKET'
                price = None
            elif exit_signal.signal_type == 'partial_profit':
                # 부분 익절은 지정가로 매도 (현재가 기준)
                order_type = 'LIMIT'
                price = exit_signal.price  # 목표가 있으면 사용, 없으면 현재가
            else:
                # 기타 신호는 시장가
                order_type = 'MARKET'
                price = None

            # 실제 매도 주문 실행
            result = await self.executor.sell_stock(
                symbol=symbol,
                quantity=quantity,
                price=price,
                order_type=order_type
            )

            return result

        except Exception as e:
            self.logger.error(f"매도 주문 실행 실패 {symbol}: {e}")
            return {'success': False, 'error': str(e)}

    async def _record_exit_signal(self, symbol: str, exit_signal: Any, quantity: int, price: float) -> None:
        """매도 신호 기록 저장"""
        try:
            if not self.db_manager:
                return

            # DB에 매도 기록 저장
            record = {
                'symbol': symbol,
                'signal_type': exit_signal.signal_type,
                'quantity': quantity,
                'price': price,
                'reason': exit_signal.reason,
                'confidence': exit_signal.confidence,
                'timestamp': asyncio.get_event_loop().time()
            }

            # 실제 DB 저장 로직은 구현 필요
            self.logger.info(f"매도 기록 저장: {record}")

        except Exception as e:
            self.logger.error(f"매도 기록 저장 실패 {symbol}: {e}")

    async def batch_execute_exit_signals(self, exit_signals: List[Any]) -> Dict[str, bool]:
        """여러 매도 신호 일괄 처리"""
        results = {}

        for exit_signal in exit_signals:
            try:
                result = await self.execute_exit_signal(
                    exit_signal.symbol,
                    exit_signal
                )
                results[exit_signal.symbol] = result

                # 각 주문 사이에 약간의 지연 (API 제한 고려)
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"일괄 매도 처리 실패 {exit_signal.symbol}: {e}")
                results[exit_signal.symbol] = False

        return results

    async def monitor_trailing_stops(self, advanced_exit_strategy) -> None:
        """트레일링 스탑 모니터링 (백그라운드 작업)"""
        try:
            while True:
                # 트레일링 스탑 업데이트
                await advanced_exit_strategy.update_trailing_stops()

                # 모든 포지션의 트레일링 스탑 체크
                for symbol in list(advanced_exit_strategy.positions.keys()):
                    exit_signals = await advanced_exit_strategy.analyze_exit_signals(symbol)

                    for exit_signal in exit_signals:
                        if exit_signal.signal_type == 'trailing_stop':
                            await self.execute_exit_signal(symbol, exit_signal)

                # 5초마다 체크
                await asyncio.sleep(5)

        except Exception as e:
            self.logger.error(f"트레일링 스탑 모니터링 실패: {e}")