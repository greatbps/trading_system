#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Scoring & Size Configuration
점수 기반 포지션 사이징 설정
"""

class PositionScoringConfig:
    """점수 기반 포지션 사이징 설정"""

    # 기본 설정
    MAX_POSITIONS = 4                    # 최대 보유종목 (단타/스윙 최적화)
    BASE_POSITION_SIZE = 0.2            # 기본 포지션 크기 (20%)
    CASH_RESERVE = 0.2                  # 현금 여유 비율 (20%)

    # 점수별 포지션 배수 (AI 분석 점수: 0-100)
    SCORE_MULTIPLIERS = {
        90: 1.5,    # 90점 이상: 1.5배 (30%)
        80: 1.25,   # 80-89점: 1.25배 (25%)
        70: 1.0,    # 70-79점: 1.0배 (20%) - 기본
        60: 0.75,   # 60-69점: 0.75배 (15%)
        50: 0.5,    # 50-59점: 0.5배 (10%)
        0:  0.0     # 50점 미만: 매수 안함
    }

    # 전략별 조정 계수
    STRATEGY_ADJUSTMENTS = {
        'momentum': 1.0,        # 모멘텀: 기본
        'breakout': 1.2,        # 돌파: 1.2배 (더 공격적)
        'reversal': 0.8,        # 반전: 0.8배 (더 보수적)
        'scalping': 0.6,        # 스캘핑: 0.6배 (빠른 회전)
    }

    # 리스크 관리
    MAX_SINGLE_POSITION = 0.35          # 단일 종목 최대 35%
    STOP_LOSS_TIGHT = 0.03             # 단타용 타이트 손절 (3%)
    STOP_LOSS_SWING = 0.05             # 스윙용 손절 (5%)
    TAKE_PROFIT_MULTIPLIER = 2.0       # 익절 = 손절 × 2배

    @classmethod
    def get_position_size(cls, score: float, strategy: str = 'momentum') -> float:
        """
        점수와 전략에 따른 포지션 크기 계산

        Args:
            score: AI 분석 점수 (0-100)
            strategy: 매매 전략

        Returns:
            포지션 크기 비율 (0.0-0.35)
        """
        # 점수별 배수 찾기
        multiplier = 0.0
        for threshold, mult in sorted(cls.SCORE_MULTIPLIERS.items(), reverse=True):
            if score >= threshold:
                multiplier = mult
                break

        # 전략별 조정
        strategy_adj = cls.STRATEGY_ADJUSTMENTS.get(strategy, 1.0)

        # 최종 포지션 크기 계산
        position_size = cls.BASE_POSITION_SIZE * multiplier * strategy_adj

        # 최대 한도 적용
        return min(position_size, cls.MAX_SINGLE_POSITION)

    @classmethod
    def get_examples(cls):
        """사용 예시 반환"""
        examples = []
        scores = [95, 85, 75, 65, 55, 45]

        for score in scores:
            for strategy in ['momentum', 'breakout', 'scalping']:
                size = cls.get_position_size(score, strategy)
                examples.append({
                    'score': score,
                    'strategy': strategy,
                    'position_size': f"{size*100:.1f}%",
                    'amount_94k': f"{94515 * size:,.0f}원"
                })

        return examples

# 사용 예시
if __name__ == "__main__":
    config = PositionScoringConfig()

    print("=== 점수별 포지션 크기 예시 ===")
    examples = config.get_examples()

    current_strategy = 'momentum'
    print(f"\n전략: {current_strategy}")
    print("점수  포지션크기  투자금액")
    print("-" * 25)

    for ex in examples:
        if ex['strategy'] == current_strategy:
            print(f"{ex['score']:3d}점  {ex['position_size']:>7s}  {ex['amount_94k']:>10s}")