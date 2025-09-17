#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Squeeze Momentum Pro 전략 설정 파일
"""

from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class SqueezeMomentumConfig:
    """Squeeze Momentum Pro 설정"""
    
    # === Squeeze Momentum Pro 지표 설정 ===
    bb_period: int = 20              # Bollinger Bands 기간
    bb_multiplier: float = 2.0       # BB 표준편차 배수
    kc_period: int = 20              # Keltner Channel 기간
    kc_multiplier: float = 1.5       # KC ATR 배수
    momentum_length: int = 20        # 모멘텀 계산 기간
    
    # === 1차 필터링 기준 ===
    primary_filter_criteria = {
        'squeeze_detection': True,           # Squeeze 상태 감지 필수
        'momentum_strength_min': 0.5,        # 최소 모멘텀 강도
        'volume_multiplier': 1.5,            # 평균 거래량 대비 배수
        'price_movement_min': 2.0,           # 최소 가격 움직임 (%)
        'trend_alignment': True,             # 추세 정렬 여부
        'atr_percentile_min': 0.3,          # ATR 백분위수 최소값
        'consecutive_squeeze_max': 10,       # 최대 연속 squeeze 허용
        'breakout_volume_confirm': True      # 돌파 시 거래량 확인
    }
    
    # === 2차 필터링 기준 (Phase 1 품질 게이트) ===
    secondary_filter_criteria = {
        'consensus_threshold': 2.0,          # 전략 합의 임계값
        'mtf_threshold': 0.6,               # MTF 컨플루언스 임계값
        'liquidity_gate': True,             # 유동성 게이트 적용
        'news_gate': True,                  # 뉴스 게이트 적용
        'regime_gate': True,                # 레짐 게이트 적용
        'min_signal_confidence': 0.7,       # 최소 신호 신뢰도
        'risk_level_max': 'MEDIUM'          # 최대 허용 리스크 레벨
    }
    
    # === 신호 생성 설정 ===
    signal_settings = {
        'min_squeeze_duration': 5,           # 최소 squeeze 지속 기간 (봉)
        'breakout_confirmation': 2,          # 돌파 확인 봉 수
        'momentum_smoothing': 3,             # 모멘텀 스무딩 기간
        'signal_strength_weight': {
            'squeeze_duration': 0.2,         # squeeze 지속 기간 가중치
            'momentum_strength': 0.3,        # 모멘텀 강도 가중치
            'volume_confirmation': 0.2,      # 거래량 확인 가중치
            'trend_alignment': 0.15,         # 추세 정렬 가중치
            'volatility_expansion': 0.15     # 변동성 확장 가중치
        }
    }
    
    # === 추천 등급 설정 ===
    recommendation_grades = {
        'STRONG_BUY': {
            'min_score': 85,
            'criteria': {
                'phase1_quality': 'high',
                'momentum_strength': 0.8,
                'volume_confirmation': True,
                'squeeze_duration_min': 7,
                'all_gates_passed': True
            }
        },
        'BUY': {
            'min_score': 70,
            'criteria': {
                'phase1_quality': 'medium',
                'momentum_strength': 0.6,
                'volume_confirmation': True,
                'squeeze_duration_min': 5,
                'major_gates_passed': 3  # 4개 게이트 중 3개 이상 통과
            }
        },
        'HOLD': {
            'min_score': 50,
            'criteria': {
                'phase1_quality': 'low',
                'momentum_strength': 0.3,
                'volume_confirmation': False,
                'squeeze_duration_min': 3,
                'major_gates_passed': 2
            }
        }
    }
    
    # === 성능 임계값 ===
    performance_thresholds = {
        'primary_filter_time_ms': 500,      # 1차 필터링 최대 시간
        'secondary_filter_time_ms': 200,    # 2차 필터링 최대 시간
        'total_processing_time_ms': 5000,   # 전체 처리 시간
        'memory_usage_mb': 500,             # 메모리 사용량 제한
        'max_candidates': 100,              # 1차 필터링 최대 후보 수
        'max_recommendations': 20           # 최대 추천 종목 수
    }
    
    # === 리스크 관리 ===
    risk_management = {
        'position_sizing': {
            'max_position_per_stock': 0.05,  # 종목당 최대 포지션 비율
            'max_total_exposure': 0.8,       # 전체 최대 노출 비율
            'volatility_adjustment': True,   # 변동성 기반 조정
            'correlation_limit': 0.7         # 종목 간 상관관계 제한
        },
        'stop_loss': {
            'default_sl_pct': 3.0,          # 기본 손절 비율
            'adaptive_sl': True,             # 적응형 손절
            'atr_based_sl': True,           # ATR 기반 손절
            'sl_multiplier': 2.0            # ATR 손절 배수
        },
        'take_profit': {
            'default_tp_pct': 6.0,          # 기본 익절 비율
            'trailing_tp': True,             # 트레일링 익절
            'tp_ratio': 2.0,                # 손익비율 (TP:SL)
            'partial_tp': True              # 부분 익절
        }
    }
    
    # === 백테스팅 설정 ===
    backtesting = {
        'lookback_period': 252,             # 백테스팅 기간 (거래일)
        'benchmark': 'KOSPI',               # 벤치마크
        'transaction_cost': 0.003,          # 거래 비용 (0.3%)
        'slippage': 0.001,                  # 슬리피지 (0.1%)
        'min_holding_period': 3,            # 최소 보유 기간
        'rebalancing_frequency': 'daily'     # 리밸런싱 주기
    }

# 전역 설정 인스턴스
squeeze_momentum_config = SqueezeMomentumConfig()