#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfolio_manager.py

포트폴리오 관리자 - 정리 전략 통합
"""

import asyncio
from typing import Dict, List, Any
from utils.logger import get_logger
from strategies.portfolio_cleanup_strategy import PortfolioCleanupStrategy
from strategies.advanced_exit_strategy import AdvancedExitStrategy

class PortfolioManager:
    """포트폴리오 통합 관리자"""

    def __init__(self, trading_handler=None, config=None):
        self.logger = get_logger("PortfolioManager")
        self.trading_handler = trading_handler
        self.config = config

        # 전략 인스턴스
        self.cleanup_strategy = PortfolioCleanupStrategy(config)
        self.exit_strategy = AdvancedExitStrategy(config)

    async def analyze_and_cleanup_portfolio(self) -> Dict[str, Any]:
        """포트폴리오 분석 및 정리 실행"""
        try:
            self.logger.info("포트폴리오 정리 분석 시작")

            # 현재 보유 종목 조회
            holdings = await self._get_current_holdings()
            if not holdings:
                return {
                    "status": "no_holdings",
                    "message": "현재 보유 중인 종목이 없어 정리할 내용이 없습니다.",
                    "recommendations": [
                        "1. KIS API 연동 상태를 확인해주세요",
                        "2. 실제 보유 종목이 있는지 HTS에서 확인해주세요",
                        "3. 모의투자/실거래 모드가 올바른지 확인해주세요"
                    ]
                }

            # 정리 계획 생성
            cleanup_plan = await self.cleanup_strategy.generate_cleanup_plan(holdings)

            # 실행 가능한 신호만 필터링
            executable_signals = [
                signal for signal in cleanup_plan['signals']
                if signal['priority'] <= 2  # 우선순위 1,2만 실행
            ]

            result = {
                "status": "analyzed",
                "cleanup_plan": cleanup_plan,
                "executable_signals": len(executable_signals),
                "execution_results": []
            }

            # 자동 실행 (실거래 모드일 때만)
            if self.config and getattr(self.config, 'TRADING_ENABLED', False):
                execution_results = await self._execute_cleanup_signals(executable_signals)
                result["execution_results"] = execution_results
                result["status"] = "executed"

            return result

        except Exception as e:
            self.logger.error(f"포트폴리오 정리 실패: {e}")
            return {"status": "error", "message": str(e)}

    async def _get_current_holdings(self) -> List[Dict[str, Any]]:
        """현재 보유 종목 조회"""
        try:
            if not self.trading_handler:
                self.logger.warning("거래 핸들러가 초기화되지 않았습니다. 시스템 설정을 확인해주세요.")
                return []

            # 보유 종목 조회
            holdings_response = await self.trading_handler.get_balance()

            if not holdings_response or not holdings_response.get('success'):
                self.logger.error("보유 종목 조회 실패")
                return []

            holdings_data = holdings_response.get('data', [])
            if not holdings_data:
                self.logger.warning("현재 보유 중인 종목이 없습니다.")
            else:
                self.logger.info(f"보유 종목 {len(holdings_data)}개 조회 완료")

            return holdings_data

        except Exception as e:
            self.logger.error(f"보유 종목 조회 실패: {e}")
            return []

    async def _execute_cleanup_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """정리 신호 실행"""
        execution_results = []

        for signal in signals:
            try:
                result = await self._execute_single_signal(signal)
                execution_results.append({
                    "signal": signal,
                    "execution_result": result
                })

                # 실행 간격 (과도한 API 호출 방지)
                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.error(f"신호 실행 실패 {signal['symbol']}: {e}")
                execution_results.append({
                    "signal": signal,
                    "execution_result": {"success": False, "error": str(e)}
                })

        return execution_results

    async def _execute_single_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """단일 신호 실행"""
        try:
            symbol = signal['symbol']
            quantity_ratio = signal['quantity_ratio']

            if not self.trading_handler:
                return {"success": False, "error": "거래 핸들러가 없습니다"}

            # 현재 보유 수량 확인
            holdings = await self._get_current_holdings()
            current_holding = next((h for h in holdings if h.get('pdno') == symbol), None)

            if not current_holding:
                return {"success": False, "error": f"보유 종목 {symbol}을 찾을 수 없습니다"}

            current_qty = int(current_holding.get('hldg_qty', 0))
            sell_qty = int(current_qty * quantity_ratio)

            if sell_qty <= 0:
                return {"success": False, "error": "매도 수량이 0 이하입니다"}

            # 매도 주문 실행
            self.logger.info(f"매도 주문 실행: {symbol} {sell_qty}주 ({signal['reason']})")

            order_result = await self.trading_handler.place_sell_order(
                symbol=symbol,
                quantity=sell_qty,
                price=None,  # 시장가
                order_type="market"
            )

            return {
                "success": order_result.get('success', False),
                "order_id": order_result.get('order_id'),
                "message": f"{symbol} {sell_qty}주 매도 주문 완료",
                "quantity": sell_qty,
                "reason": signal['reason']
            }

        except Exception as e:
            self.logger.error(f"신호 실행 중 오류 {signal.get('symbol', 'Unknown')}: {e}")
            return {"success": False, "error": str(e)}

    async def get_portfolio_status(self) -> Dict[str, Any]:
        """포트폴리오 현재 상태"""
        try:
            holdings = await self._get_current_holdings()

            if not holdings:
                return {
                    "status": "empty",
                    "holdings_count": 0,
                    "message": "현재 보유 중인 종목이 없습니다.",
                    "suggestions": [
                        "종목을 매수하거나 감시 목록에 종목을 추가해보세요",
                        "KIS API 연동 상태와 계좌 정보를 확인해주세요"
                    ]
                }

            # cleanup_strategy에 holdings 데이터를 먼저 분석시켜서 summary를 생성
            await self.cleanup_strategy.analyze_portfolio(holdings)
            summary = self.cleanup_strategy.get_portfolio_summary()

            return {
                "status": "active",
                "holdings_count": len(holdings),
                "summary": summary,
                "cleanup_recommendation": summary.get('cleanup_needed', False)
            }

        except Exception as e:
            self.logger.error(f"포트폴리오 상태 조회 실패: {e}")
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # 테스트 실행
    async def test_portfolio_manager():
        manager = PortfolioManager()
        status = await manager.get_portfolio_status()
        print(f"포트폴리오 상태: {status}")

    asyncio.run(test_portfolio_manager())