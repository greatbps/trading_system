#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 12개 보유종목 → 4개 집중투자 전환 전략
"""

class PositionCleanupStrategy:
    """보유종목 정리 전략"""

    @staticmethod
    def get_cleanup_plan():
        """12개 → 4개 정리 계획"""

        plan = {
            "phase_1": {
                "name": "손실 종목 우선 정리",
                "criteria": [
                    "수익률 -5% 이하인 종목",
                    "거래량 감소 추세 종목",
                    "기술적 지표 약세 종목"
                ],
                "target_reduce": "4개 → 8개",
                "timeline": "1-2일"
            },

            "phase_2": {
                "name": "평범한 종목 정리",
                "criteria": [
                    "수익률 -2% ~ +2% 종목",
                    "모멘텀 약한 종목",
                    "AI 점수 70점 미만 종목"
                ],
                "target_reduce": "8개 → 6개",
                "timeline": "2-3일"
            },

            "phase_3": {
                "name": "최종 선별",
                "criteria": [
                    "AI 점수 80점 이상만 유지",
                    "강한 모멘텀 유지 종목",
                    "수익률 +3% 이상 종목"
                ],
                "target_reduce": "6개 → 4개",
                "timeline": "3-4일"
            }
        }

        return plan

    @staticmethod
    def get_selection_criteria():
        """최종 4개 선별 기준"""

        return {
            "technical_score": {
                "weight": 30,
                "criteria": "RSI, MACD, 볼린저밴드 종합점수"
            },
            "momentum_score": {
                "weight": 25,
                "criteria": "최근 5일 가격 모멘텀"
            },
            "volume_score": {
                "weight": 20,
                "criteria": "거래량 증가 추세"
            },
            "ai_analysis_score": {
                "weight": 15,
                "criteria": "AI 종합 분석 점수"
            },
            "profit_potential": {
                "weight": 10,
                "criteria": "단기 수익 가능성"
            }
        }

    @staticmethod
    def get_position_sizes():
        """4개 종목 포지션 크기 배분"""

        return {
            "top_pick": {
                "ratio": 35,
                "amount": "33,080원",
                "description": "AI 점수 90점 이상 최고 종목"
            },
            "strong_pick": {
                "ratio": 25,
                "amount": "23,629원",
                "description": "AI 점수 80-89점 강세 종목"
            },
            "good_pick_1": {
                "ratio": 20,
                "amount": "18,903원",
                "description": "AI 점수 70-79점 양호 종목"
            },
            "good_pick_2": {
                "ratio": 20,
                "amount": "18,903원",
                "description": "AI 점수 70-79점 양호 종목"
            }
        }

if __name__ == "__main__":
    strategy = PositionCleanupStrategy()

    print("=== 12개 → 4개 포지션 정리 전략 ===\n")

    # 정리 계획
    plan = strategy.get_cleanup_plan()
    for phase, details in plan.items():
        print(f"[{details['name']}]")
        print(f"- 기준: {', '.join(details['criteria'])}")
        print(f"- 목표: {details['target_reduce']}")
        print(f"- 기간: {details['timeline']}")
        print()

    # 선별 기준
    print("=== 최종 4개 선별 기준 ===")
    criteria = strategy.get_selection_criteria()
    for name, details in criteria.items():
        print(f"- {details['criteria']} ({details['weight']}%)")
    print()

    # 포지션 배분
    print("=== 4개 종목 포지션 배분 ===")
    sizes = strategy.get_position_sizes()
    total_amount = 0

    for pick, details in sizes.items():
        amount = int(details['amount'].replace('원', '').replace(',', ''))
        total_amount += amount
        print(f"- {details['description']}: {details['ratio']}% ({details['amount']})")

    print(f"\n총 투자금액: {total_amount:,}원 (잔고의 80%)")
    print(f"현금 여유: {94515 - total_amount:,}원 (잔고의 20%)")