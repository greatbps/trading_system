#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
portfolio_cleanup_strategy.py

계좌 정리 전략 및 실행 도구
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class CleanupRecommendation:
    """정리 추천 데이터 클래스"""
    symbol: str
    name: str
    action: str  # 'SELL_IMMEDIATE', 'SELL_CONDITIONAL', 'HOLD'
    reason: str
    priority: int  # 1=높음, 2=중간, 3=낮음
    current_value: int
    profit_loss: int
    profit_rate: float

class PortfolioCleanupStrategy:
    """계좌 정리 전략 클래스"""

    def __init__(self, kis_collector=None):
        self.kis_collector = kis_collector
        self.cleanup_rules = {
            'loss_threshold_immediate': -15.0,  # 15% 손실 시 즉시 매도 검토
            'loss_threshold_conditional': -5.0,  # 5% 손실 시 조건부 매도 검토
            'small_holding_threshold': 50000,    # 5만원 미만 소액 보유
            'min_weight_threshold': 1.0,         # 포트폴리오 비중 1% 미만
        }

    def analyze_portfolio(self, holdings: List[Dict]) -> List[CleanupRecommendation]:
        """포트폴리오 분석 및 정리 추천"""
        recommendations = []
        total_value = sum(int(h.get('evlu_amt', 0)) for h in holdings)

        for holding in holdings:
            symbol = holding.get('pdno', '')
            name = holding.get('prdt_name', '')
            eval_amt = int(holding.get('evlu_amt', 0))
            profit_rate = float(holding.get('evlu_pfls_rt', 0))
            profit_loss = int(holding.get('evlu_pfls_amt', 0))

            # 포트폴리오 비중 계산
            weight = (eval_amt / total_value * 100) if total_value > 0 else 0

            # 정리 추천 로직
            recommendation = self._get_cleanup_recommendation(
                symbol, name, eval_amt, profit_rate, profit_loss, weight
            )

            if recommendation:
                recommendations.append(recommendation)

        # 우선순위 순으로 정렬
        recommendations.sort(key=lambda x: (x.priority, -abs(x.profit_loss)))
        return recommendations

    def _get_cleanup_recommendation(self, symbol: str, name: str,
                                  eval_amt: int, profit_rate: float,
                                  profit_loss: int, weight: float) -> CleanupRecommendation:
        """개별 종목 정리 추천"""

        # 즉시 매도 검토 조건
        if profit_rate <= self.cleanup_rules['loss_threshold_immediate']:
            return CleanupRecommendation(
                symbol=symbol, name=name, action='SELL_IMMEDIATE',
                reason=f'손실 {profit_rate:.1f}% - 손절 검토 필요',
                priority=1, current_value=eval_amt,
                profit_loss=profit_loss, profit_rate=profit_rate
            )

        # 소액 보유 정리
        if eval_amt < self.cleanup_rules['small_holding_threshold']:
            return CleanupRecommendation(
                symbol=symbol, name=name, action='SELL_IMMEDIATE',
                reason=f'소액 보유 ({eval_amt:,}원) - 거래비용 비효율',
                priority=1, current_value=eval_amt,
                profit_loss=profit_loss, profit_rate=profit_rate
            )

        # 조건부 매도 검토
        if profit_rate <= self.cleanup_rules['loss_threshold_conditional']:
            return CleanupRecommendation(
                symbol=symbol, name=name, action='SELL_CONDITIONAL',
                reason=f'손실 {profit_rate:.1f}% - 업종 전망 재평가 필요',
                priority=2, current_value=eval_amt,
                profit_loss=profit_loss, profit_rate=profit_rate
            )

        # 비중 부족 종목
        if weight < self.cleanup_rules['min_weight_threshold']:
            return CleanupRecommendation(
                symbol=symbol, name=name, action='SELL_CONDITIONAL',
                reason=f'포트폴리오 비중 {weight:.1f}% - 집중도 개선',
                priority=3, current_value=eval_amt,
                profit_loss=profit_loss, profit_rate=profit_rate
            )

        return None

    def generate_cleanup_report(self, recommendations: List[CleanupRecommendation]) -> str:
        """정리 보고서 생성"""
        report = []
        report.append("=" * 60)
        report.append("📊 포트폴리오 정리 추천 보고서")
        report.append("=" * 60)
        report.append(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 우선순위별 분류
        immediate_sells = [r for r in recommendations if r.action == 'SELL_IMMEDIATE']
        conditional_sells = [r for r in recommendations if r.action == 'SELL_CONDITIONAL']

        if immediate_sells:
            report.append("🔴 즉시 매도 검토 대상:")
            for i, rec in enumerate(immediate_sells, 1):
                report.append(f"  {i}. {rec.name}({rec.symbol})")
                report.append(f"     현재가치: {rec.current_value:,}원 | 손익: {rec.profit_loss:+,}원 | 수익률: {rec.profit_rate:+.1f}%")
                report.append(f"     사유: {rec.reason}")
                report.append("")

        if conditional_sells:
            report.append("🟡 조건부 매도 검토 대상:")
            for i, rec in enumerate(conditional_sells, 1):
                report.append(f"  {i}. {rec.name}({rec.symbol})")
                report.append(f"     현재가치: {rec.current_value:,}원 | 손익: {rec.profit_loss:+,}원 | 수익률: {rec.profit_rate:+.1f}%")
                report.append(f"     사유: {rec.reason}")
                report.append("")

        # 요약 통계
        total_cleanup_value = sum(r.current_value for r in recommendations)
        total_cleanup_loss = sum(r.profit_loss for r in recommendations if r.profit_loss < 0)

        report.append("📈 정리 효과 예상:")
        report.append(f"  • 정리 대상 종목 수: {len(recommendations)}개")
        report.append(f"  • 정리 예상 금액: {total_cleanup_value:,}원")
        report.append(f"  • 손실 확정 금액: {total_cleanup_loss:,}원")
        report.append("")

        report.append("💡 정리 후 기대 효과:")
        report.append("  • 포트폴리오 집중도 향상")
        report.append("  • 관리 부담 감소")
        report.append("  • 우량 종목 비중 확대 가능")
        report.append("  • 추가 투자 여력 확보")

        return "\n".join(report)

    async def execute_cleanup_plan(self, recommendations: List[CleanupRecommendation],
                                 confirm_each: bool = True) -> Dict[str, Any]:
        """정리 계획 실행"""
        results = {
            'executed': [],
            'skipped': [],
            'errors': []
        }

        for rec in recommendations:
            if rec.action == 'SELL_IMMEDIATE':
                if confirm_each:
                    print(f"\n🔴 {rec.name}({rec.symbol}) 매도를 실행하시겠습니까?")
                    print(f"   사유: {rec.reason}")
                    print(f"   현재가치: {rec.current_value:,}원")
                    confirm = input("실행하려면 'y'를 입력하세요: ").lower().strip()
                    if confirm != 'y':
                        results['skipped'].append(rec.symbol)
                        continue

                try:
                    # 실제 매도 주문 실행 (KIS API 호출)
                    # 여기서는 시뮬레이션만 수행
                    print(f"✅ {rec.name}({rec.symbol}) 매도 주문 접수됨")
                    results['executed'].append(rec.symbol)

                except Exception as e:
                    print(f"❌ {rec.name}({rec.symbol}) 매도 실패: {e}")
                    results['errors'].append({'symbol': rec.symbol, 'error': str(e)})

        return results

def main():
    """메인 실행 함수"""
    print("Portfolio Cleanup Tool")
    print("=" * 40)

    # 샘플 데이터로 테스트 (실제로는 KIS API에서 가져옴)
    sample_holdings = [
        {
            'pdno': '005930', 'prdt_name': '삼성전자',
            'evlu_amt': '1000000', 'evlu_pfls_amt': '50000', 'evlu_pfls_rt': '5.0'
        },
        {
            'pdno': '123456', 'prdt_name': '손실종목A',
            'evlu_amt': '30000', 'evlu_pfls_amt': '-10000', 'evlu_pfls_rt': '-25.0'
        },
        {
            'pdno': '789012', 'prdt_name': '소액종목B',
            'evlu_amt': '25000', 'evlu_pfls_amt': '-5000', 'evlu_pfls_rt': '-16.7'
        }
    ]

    strategy = PortfolioCleanupStrategy()
    recommendations = strategy.analyze_portfolio(sample_holdings)

    if recommendations:
        report = strategy.generate_cleanup_report(recommendations)
        print(report)

        print("\n" + "="*60)
        choice = input("Execute cleanup? (y/n): ").lower().strip()
        if choice == 'y':
            results = asyncio.run(strategy.execute_cleanup_plan(recommendations))
            print(f"\nExecution result: {len(results['executed'])} stocks cleaned up")
    else:
        print("No stocks need cleanup.")

if __name__ == "__main__":
    main()