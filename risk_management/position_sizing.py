#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/risk_management/position_sizing.py

적응형 포지션 사이징 시스템 - Phase 4 Advanced AI Features
"""

import asyncio
import math
from typing import Dict, Any
from dataclasses import dataclass

from utils.logger import get_logger

@dataclass
class PositionSizingRecommendation:
    """포지션 사이징 추천 정보"""
    recommended_size_ratio: float  # 전체 계좌 대비 추천 포지션 비율 (0.0 ~ 1.0)
    max_shares: int                # 최대 매수 가능 주식 수
    risk_per_trade_usd: float      # 개별 거래당 허용되는 최대 손실 금액
    reason: str                    # 추천 사유
    confidence: float              # 추천 신뢰도 (0-100)
    adjusted_by_regime: bool       # 시장 체제에 의해 조정되었는지 여부

class AdaptivePositionSizing:
    """
    시장 체제 및 기타 요인에 따라 포지션 크기를 동적으로 조절하는 시스템.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("AdaptivePositionSizing")
        self.default_risk_per_trade_ratio = config.get('position_sizing', {}).get('default_risk_per_trade_ratio', 0.01) # 기본 1%
        self.max_account_risk_ratio = config.get('position_sizing', {}).get('max_account_risk_ratio', 0.05) # 최대 5%
        self.regime_adjustment_factors = config.get('position_sizing', {}).get('regime_adjustment_factors', {
            'BULL_TREND': 1.2,
            'BEAR_TREND': 0.7,
            'SIDEWAYS': 0.9,
            'HIGH_VOLATILITY': 0.6,
            'LOW_VOLATILITY': 1.1
        })
        self.min_position_ratio = config.get('position_sizing', {}).get('min_position_ratio', 0.005) # 최소 0.5%
        self.max_position_ratio = config.get('position_sizing', {}).get('max_position_ratio', 0.20) # 최대 20%

        self.logger.info("✅ 적응형 포지션 사이징 시스템 초기화 완료")

    async def get_adaptive_position_sizing(
        self,
        regime_type: str,
        regime_confidence: float,
        account_balance: float,
        stock_price: float,
        stop_loss_price: float,
        signal_strength: float = 0.7, # 0.0 ~ 1.0, 신호 강도 (예: AI 예측 신뢰도)
        risk_tolerance_level: str = "MEDIUM" # LOW, MEDIUM, HIGH
    ) -> PositionSizingRecommendation:
        """
        현재 시장 체제, 계좌 잔고, 주식 가격, 손절가 등을 기반으로
        적응형 포지션 사이징을 계산하여 추천합니다.
        """
        try:
            # Handle zero account balance or invalid stock price upfront
            if account_balance <= 0 or stock_price <= 0:
                self.logger.warning("⚠️ 계좌 잔고 또는 주식 가격이 0 이하입니다. 포지션 사이징 불가.")
                return PositionSizingRecommendation(
                    recommended_size_ratio=0.0, # Explicitly 0.0 for zero balance
                    max_shares=0,
                    risk_per_trade_usd=0.0,
                    reason="계좌 잔고 또는 주식 가격이 유효하지 않아 포지션 사이징 불가.",
                    confidence=0.0,
                    adjusted_by_regime=False
                )

            self.logger.info(f"📊 포지션 사이징 계산 시작 (체제: {regime_type}, 잔고: {account_balance})")

            # 1. 기본 위험 금액 계산 (계좌 잔고 대비)
            risk_per_trade_usd = account_balance * self.default_risk_per_trade_ratio

            # 2. 시장 체제에 따른 위험 금액 조정
            regime_factor = self.regime_adjustment_factors.get(regime_type, 1.0)
            risk_per_trade_usd *= regime_factor
            self.logger.debug(f"체제 ({regime_type}) 조정 후 위험 금액: {risk_per_trade_usd:.2f} USD (팩터: {regime_factor:.2f})")

            # 3. 신호 강도에 따른 위험 금액 조정 (신호가 강할수록 더 많은 위험 허용)
            signal_adjustment_factor = 0.5 + (signal_strength * 0.5) # 0.5 ~ 1.0
            risk_per_trade_usd *= signal_adjustment_factor
            self.logger.debug(f"신호 강도 ({signal_strength:.2f}) 조정 후 위험 금액: {risk_per_trade_usd:.2f} USD (팩터: {signal_adjustment_factor:.2f})")

            # 4. 리스크 허용 수준에 따른 조정 (LOW, MEDIUM, HIGH)
            if risk_tolerance_level == "LOW":
                risk_per_trade_usd *= 0.8
            elif risk_tolerance_level == "HIGH":
                risk_per_trade_usd *= 1.2
            self.logger.debug(f"리스크 허용 수준 ({risk_tolerance_level}) 조정 후 위험 금액: {risk_per_trade_usd:.2f} USD")

            # 5. 개별 주식당 허용 손실액 계산
            loss_per_share = stock_price - stop_loss_price
            reason = f"시장 체제({regime_type})와 신호 강도({signal_strength:.2f})에 따라 조정됨."
            if loss_per_share <= 0: # 손절가가 매수가보다 높거나 같으면 (잘못된 입력 또는 손절 없음)
                self.logger.warning("⚠️ 손절가가 매수가보다 높거나 같습니다. 포지션 사이징 계산에 문제가 있을 수 있습니다.")
                # If stop loss is invalid, we cannot calculate risk-based shares, so set to 0
                max_shares_by_risk = 0
                reason = "손절가가 매수가보다 높거나 같아 포지션 사이징 불가."
            else:
                shares_per_risk_unit = risk_per_trade_usd / loss_per_share
                max_shares_by_risk = math.floor(shares_per_risk_unit)

            # 6. 최대 매수 가능 주식 수 계산
            max_shares_by_balance = math.floor(account_balance / stock_price)

            # 최종 매수 가능 주식 수는 위험 기반과 잔고 기반 중 더 작은 값
            max_shares = min(max_shares_by_risk, max_shares_by_balance)

            # 7. 추천 포지션 비율 계산
            recommended_value = max_shares * stock_price
            recommended_size_ratio = recommended_value / account_balance if account_balance > 0 else 0.0

            # Dynamically adjust max_position_ratio based on regime factor
            # For bear markets, we want a much smaller position size.
            # Instead of scaling max_position_ratio, we can scale the default_risk_per_trade_ratio
            # more aggressively, or set a lower absolute max for bear markets.
            # Let's try scaling the default_risk_per_trade_ratio more aggressively for bear markets
            # by using a lower base for dynamic_max_position_ratio.
            
            # Use a base for dynamic max position ratio that is influenced by the default risk per trade
            # This makes it more sensitive to the regime factor for overall position size.
            base_for_dynamic_max_ratio = self.default_risk_per_trade_ratio * 5 # e.g., 0.01 * 5 = 0.05
            dynamic_max_position_ratio = base_for_dynamic_max_ratio * regime_factor
            
            # Ensure dynamic_max_position_ratio doesn't exceed the absolute max or go below min
            dynamic_max_position_ratio = max(self.min_position_ratio, min(self.max_position_ratio, dynamic_max_position_ratio))

            # Apply min/max position ratio limits, but only if max_shares is not 0
            if max_shares > 0:
                recommended_size_ratio = max(self.min_position_ratio, min(dynamic_max_position_ratio, recommended_size_ratio))
            else:
                recommended_size_ratio = 0.0 # If max_shares is 0, ratio must be 0

            # Recalculate max_shares based on the final recommended_size_ratio to ensure consistency
            max_shares = math.floor((account_balance * recommended_size_ratio) / stock_price) if stock_price > 0 else 0


            # 8. 추천 사유 및 신뢰도
            confidence = regime_confidence * signal_strength # 체제 신뢰도와 신호 강도 곱으로 계산

            self.logger.info(f"✅ 포지션 사이징 계산 완료: 추천 비율 {recommended_size_ratio:.2%}, 최대 주식 수 {max_shares}주")

            return PositionSizingRecommendation(
                recommended_size_ratio=recommended_size_ratio,
                max_shares=max_shares,
                risk_per_trade_usd=risk_per_trade_usd,
                reason=reason,
                confidence=confidence,
                adjusted_by_regime=True
            )

        except Exception as e:
            self.logger.error(f"❌ 포지션 사이징 계산 실패: {e}")
            # 오류 발생 시 기본값 반환
            return PositionSizingRecommendation(
                recommended_size_ratio=0.0, # Changed to 0.0 for error case
                max_shares=0,
                risk_per_trade_usd=0.0, # Changed to 0.0 for error case
                reason="포지션 사이징 계산 중 오류 발생. 기본값 적용.",
                confidence=0.0,
                adjusted_by_regime=False
            )