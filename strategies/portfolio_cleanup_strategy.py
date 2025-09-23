#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfolio_cleanup_strategy.py

포트폴리오 정리 전략
1. 익절 종목 우선 매도
2. 손실 큰 종목(-2% 기준) 정리
3. 하드코딩된 종목 제외
"""

import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from utils.logger import get_logger

@dataclass
class CleanupSignal:
    """포트폴리오 정리 신호"""
    symbol: str
    action: str  # 'profit_taking', 'loss_cutting', 'hold'
    priority: int  # 1=최우선, 2=우선, 3=보통
    quantity_ratio: float  # 매도할 비율 (0.0 ~ 1.0)
    profit_rate: float
    reason: str
    price: Optional[float] = None

@dataclass
class HoldingInfo:
    """보유 종목 정보"""
    symbol: str
    name: str
    quantity: int
    avg_price: float
    current_price: float
    profit_loss: float
    profit_rate: float
    is_hardcoded: bool = False

class PortfolioCleanupStrategy:
    """포트폴리오 정리 전략"""

    def __init__(self, config=None):
        self.logger = get_logger("PortfolioCleanup")
        self.config = config

        # 하드코딩된 종목 리스트 (제외 대상)
        self.hardcoded_stocks = {
            '005930',  # 삼성전자
            '000660',  # SK하이닉스
            '035420',  # NAVER
            '207940',  # 삼성바이오로직스
            '005380',  # 현대차
            '051910',  # LG화학
            '006400',  # 삼성SDI
            '035720',  # 카카오
            '003670',  # 포스코홀딩스
            '096770',  # SK이노베이션
        }

        # 정리 기준
        self.cleanup_params = {
            'profit_threshold': 0.02,    # +2% 이상 익절 대상
            'loss_threshold': -0.02,     # -2% 이하 손절 대상
            'max_positions': 5,          # 최대 보유 종목 수
            'exclude_hardcoded': True,   # 하드코딩 종목 제외
        }

        self.holdings: Dict[str, HoldingInfo] = {}

    async def analyze_portfolio(self, holdings_data: List[Dict[str, Any]]) -> List[CleanupSignal]:
        """포트폴리오 분석 및 정리 신호 생성"""
        signals = []

        try:
            # 보유 종목 정보 업데이트
            self._update_holdings(holdings_data)

            # 하드코딩된 종목 마킹
            self._mark_hardcoded_stocks()

            # 1단계: 익절 종목 우선 선별
            profit_signals = self._analyze_profit_taking()
            signals.extend(profit_signals)

            # 2단계: 손실 큰 종목 정리
            loss_signals = self._analyze_loss_cutting()
            signals.extend(loss_signals)

            # 3단계: 포지션 수 관리
            position_signals = self._analyze_position_management()
            signals.extend(position_signals)

            # 신호 정렬 (우선순위별)
            signals.sort(key=lambda x: (x.priority, -x.profit_rate))

            self.logger.info(f"포트폴리오 정리 신호 {len(signals)}개 생성")

        except Exception as e:
            self.logger.error(f"포트폴리오 분석 실패: {e}")

        return signals

    def _update_holdings(self, holdings_data: List[Dict[str, Any]]) -> None:
        """보유 종목 정보 업데이트"""
        self.holdings.clear()
        self.logger.info(f"보유종목 업데이트 시작: {len(holdings_data)}개 데이터")

        for holding in holdings_data:
            try:
                # KIS API 원본 형태와 변환된 형태 모두 지원
                symbol = holding.get('pdno', holding.get('symbol', ''))
                name = holding.get('prdt_name', holding.get('name', ''))

# 디버깅 완료로 주석 처리
                # self.logger.info(f"원본 데이터: symbol키들={list(holding.keys())}, pdno={holding.get('pdno')}, symbol={holding.get('symbol')}, name={name}")
                quantity = int(holding.get('hldg_qty', holding.get('quantity', 0)))
                avg_price = float(holding.get('pchs_avg_pric', holding.get('avg_price', 0)))
                current_price = float(holding.get('prpr', holding.get('current_price', 0)))

                # profit_loss와 profit_rate도 직접 가져올 수 있다면 사용
                profit_loss = holding.get('profit_loss')
                profit_rate = holding.get('profit_rate')

                if quantity > 0 and avg_price > 0 and current_price > 0:
                    # profit_loss와 profit_rate가 없으면 계산
                    if profit_loss is None:
                        profit_loss = (current_price - avg_price) * quantity
                    if profit_rate is None:
                        profit_rate = (current_price / avg_price - 1) * 100

                    self.holdings[symbol] = HoldingInfo(
                        symbol=symbol,
                        name=name,
                        quantity=quantity,
                        avg_price=avg_price,
                        current_price=current_price,
                        profit_loss=profit_loss,
                        profit_rate=profit_rate
                    )

                    self.logger.info(f"종목 '{symbol}'({name}) 업데이트: 수량={quantity}, 평균가={avg_price}, 현재가={current_price}, 수익률={profit_rate:.2f}%")

            except Exception as e:
                self.logger.error(f"보유 종목 데이터 처리 실패 {holding}: {e}")

        self.logger.info(f"보유종목 업데이트 완료: {len(self.holdings)}개 종목")

    def _mark_hardcoded_stocks(self) -> None:
        """하드코딩된 종목 마킹"""
        for symbol, holding in self.holdings.items():
            if symbol in self.hardcoded_stocks:
                holding.is_hardcoded = True
                self.logger.info(f"하드코딩 종목 제외: {holding.name}({symbol})")

    def _analyze_profit_taking(self) -> List[CleanupSignal]:
        """익절 종목 분석"""
        signals = []

        # 수익률 높은 순으로 정렬
        profit_holdings = [
            h for h in self.holdings.values()
            if (h.profit_rate >= self.cleanup_params['profit_threshold'] * 100 and
                not h.is_hardcoded)
        ]
        profit_holdings.sort(key=lambda x: x.profit_rate, reverse=True)

        for holding in profit_holdings:
            # 수익률에 따른 매도 비율 결정
            if holding.profit_rate >= 5.0:  # +5% 이상
                quantity_ratio = 1.0  # 전량 매도
                priority = 1
            elif holding.profit_rate >= 3.0:  # +3% 이상
                quantity_ratio = 0.7  # 70% 매도
                priority = 1
            else:  # +2% 이상
                quantity_ratio = 0.5  # 50% 매도
                priority = 2

            signals.append(CleanupSignal(
                symbol=holding.symbol,
                action='profit_taking',
                priority=priority,
                quantity_ratio=quantity_ratio,
                profit_rate=holding.profit_rate,
                reason=f"익절 (+{holding.profit_rate:.1f}%)",
                price=holding.current_price
            ))

        self.logger.info(f"익절 대상 {len(signals)}개 종목 선별")
        return signals

    def _analyze_loss_cutting(self) -> List[CleanupSignal]:
        """손절 종목 분석"""
        signals = []

        # 손실률 큰 순으로 정렬
        loss_holdings = [
            h for h in self.holdings.values()
            if (h.profit_rate <= self.cleanup_params['loss_threshold'] * 100 and
                not h.is_hardcoded)
        ]
        loss_holdings.sort(key=lambda x: x.profit_rate)

        for holding in loss_holdings:
            # 손실률에 따른 매도 비율 결정
            if holding.profit_rate <= -5.0:  # -5% 이하
                quantity_ratio = 1.0  # 전량 매도
                priority = 1
            elif holding.profit_rate <= -3.0:  # -3% 이하
                quantity_ratio = 0.8  # 80% 매도
                priority = 2
            else:  # -2% 이하
                quantity_ratio = 0.6  # 60% 매도
                priority = 3

            signals.append(CleanupSignal(
                symbol=holding.symbol,
                action='loss_cutting',
                priority=priority,
                quantity_ratio=quantity_ratio,
                profit_rate=holding.profit_rate,
                reason=f"손절 ({holding.profit_rate:.1f}%)",
                price=holding.current_price
            ))

        self.logger.info(f"손절 대상 {len(signals)}개 종목 선별")
        return signals

    def _analyze_position_management(self) -> List[CleanupSignal]:
        """포지션 수 관리"""
        signals = []

        # 하드코딩 제외 종목 수 확인
        active_holdings = [h for h in self.holdings.values() if not h.is_hardcoded]

        if len(active_holdings) > self.cleanup_params['max_positions']:
            # 초과 종목은 수익률 낮은 순으로 정리
            excess_count = len(active_holdings) - self.cleanup_params['max_positions']
            active_holdings.sort(key=lambda x: x.profit_rate)

            for holding in active_holdings[:excess_count]:
                signals.append(CleanupSignal(
                    symbol=holding.symbol,
                    action='position_management',
                    priority=3,
                    quantity_ratio=1.0,
                    profit_rate=holding.profit_rate,
                    reason=f"포지션 수 관리 ({holding.profit_rate:.1f}%)",
                    price=holding.current_price
                ))

        return signals

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """포트폴리오 요약"""
        active_holdings = [h for h in self.holdings.values() if not h.is_hardcoded]
        hardcoded_holdings = [h for h in self.holdings.values() if h.is_hardcoded]

        profit_holdings = [h for h in active_holdings if h.profit_rate >= 2.0]
        loss_holdings = [h for h in active_holdings if h.profit_rate <= -2.0]

        total_profit_loss = sum(h.profit_loss for h in active_holdings)

        return {
            'total_holdings': len(self.holdings),
            'active_holdings': len(active_holdings),
            'hardcoded_holdings': len(hardcoded_holdings),
            'profit_candidates': len(profit_holdings),
            'loss_candidates': len(loss_holdings),
            'total_profit_loss': total_profit_loss,
            'hardcoded_list': [f"{h.name}({h.symbol})" for h in hardcoded_holdings],
            'cleanup_needed': len(profit_holdings) + len(loss_holdings) > 0
        }

    async def generate_cleanup_plan(self, holdings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """포트폴리오 정리 계획 생성"""
        signals = await self.analyze_portfolio(holdings_data)
        summary = self.get_portfolio_summary()

        # 실행 순서별 그룹화
        priority_groups = {}
        for signal in signals:
            if signal.priority not in priority_groups:
                priority_groups[signal.priority] = []
            priority_groups[signal.priority].append(signal)

        return {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'signals': [
                {
                    'symbol': s.symbol,
                    'action': s.action,
                    'priority': s.priority,
                    'quantity_ratio': s.quantity_ratio,
                    'profit_rate': s.profit_rate,
                    'reason': s.reason,
                    'price': s.price
                } for s in signals
            ],
            'execution_plan': {
                'step1_profit_taking': [s for s in signals if s.action == 'profit_taking'],
                'step2_loss_cutting': [s for s in signals if s.action == 'loss_cutting'],
                'step3_position_mgmt': [s for s in signals if s.action == 'position_management']
            }
        }

if __name__ == "__main__":
    # 테스트 실행
    async def test_cleanup():
        strategy = PortfolioCleanupStrategy()

        # 샘플 데이터
        sample_holdings = [
            {'pdno': '005930', 'prdt_name': '삼성전자', 'hldg_qty': '100', 'pchs_avg_pric': '70000', 'prpr': '72000'},
            {'pdno': '123456', 'prdt_name': '테스트A', 'hldg_qty': '50', 'pchs_avg_pric': '10000', 'prpr': '10500'},
            {'pdno': '789012', 'prdt_name': '테스트B', 'hldg_qty': '30', 'pchs_avg_pric': '20000', 'prpr': '19500'},
        ]

        plan = await strategy.generate_cleanup_plan(sample_holdings)
        print("포트폴리오 정리 계획:")
        print(f"요약: {plan['summary']}")
        print(f"신호 수: {len(plan['signals'])}")

    asyncio.run(test_cleanup())