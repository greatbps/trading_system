#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수동 매매 전략 - Claude 기준 설정
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class TradingSignal:
    """매매 신호 클래스"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0-1 사이 신뢰도
    reason: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    quantity: Optional[int] = None

class ManualTradingStrategy:
    """수동 매매 전략 클래스"""

    def __init__(self):
        """초기화"""
        self.current_positions = {}
        self.cash_balance = 1000000  # 100만원 가정
        self.max_position_size = 200000  # 최대 포지션 20만원
        self.stop_loss_pct = 0.03  # 3% 손절
        self.take_profit_pct = 0.06  # 6% 익절

        # 현재 시장 데이터 (샘플 데이터 기반)
        self.market_data = {
            "005930": {"name": "삼성전자", "price": 71000, "change": 1.5},
            "000660": {"name": "SK하이닉스", "price": 89000, "change": 2.1},
            "035420": {"name": "NAVER", "price": 185000, "change": -0.8},
            "051910": {"name": "LG화학", "price": 410000, "change": 1.2},
            "006400": {"name": "삼성SDI", "price": 390000, "change": 3.2}
        }

    def analyze_market_condition(self) -> str:
        """시장 상황 분석"""
        positive_count = 0
        total_count = len(self.market_data)

        for symbol, data in self.market_data.items():
            if data["change"] > 0:
                positive_count += 1

        positive_ratio = positive_count / total_count

        if positive_ratio >= 0.7:
            return "BULLISH"  # 강세장
        elif positive_ratio <= 0.3:
            return "BEARISH"  # 약세장
        else:
            return "NEUTRAL"  # 중립

    def get_trading_signals(self) -> List[TradingSignal]:
        """매매 신호 생성"""
        signals = []
        market_condition = self.analyze_market_condition()

        for symbol, data in self.market_data.items():
            signal = self._analyze_individual_stock(symbol, data, market_condition)
            if signal:
                signals.append(signal)

        return signals

    def _analyze_individual_stock(self, symbol: str, data: Dict, market_condition: str) -> Optional[TradingSignal]:
        """개별 종목 분석"""
        name = data["name"]
        price = data["price"]
        change = data["change"]

        # 기본 필터링
        if price < 10000 or price > 500000:  # 가격 범위 제한
            return None

        # 매매 신호 로직
        confidence = 0.0
        action = "HOLD"
        reason = ""

        # 1. 급등주 포착 (3% 이상 상승)
        if change >= 3.0 and market_condition in ["BULLISH", "NEUTRAL"]:
            action = "BUY"
            confidence = min(0.8, change / 5.0)  # 최대 80% 신뢰도
            reason = f"급등 신호 (+{change}%), 시장상황: {market_condition}"

        # 2. 강세장에서 소폭 상승 (안정적 매수)
        elif 1.0 <= change < 3.0 and market_condition == "BULLISH":
            action = "BUY"
            confidence = 0.6
            reason = f"강세장 안정 상승 (+{change}%)"

        # 3. 급락주 (2% 이상 하락) - 약세장에서는 매도
        elif change <= -2.0:
            if market_condition == "BEARISH":
                action = "SELL"
                confidence = 0.7
                reason = f"약세장 급락 신호 ({change}%)"
            else:
                action = "HOLD"
                confidence = 0.3
                reason = f"급락 관망 ({change}%)"

        # 4. 박스권 (소폭 등락)
        else:
            action = "HOLD"
            confidence = 0.2
            reason = f"박스권 관망 ({change}%)"

        # 신호 생성
        if action != "HOLD" and confidence >= 0.5:
            # 목표가/손절가 계산
            if action == "BUY":
                target_price = price * (1 + self.take_profit_pct)
                stop_loss = price * (1 - self.stop_loss_pct)
                quantity = min(100, int(self.max_position_size / price))
            else:
                target_price = None
                stop_loss = None
                quantity = None

            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                reason=reason,
                target_price=target_price,
                stop_loss=stop_loss,
                quantity=quantity
            )

        return None

    def execute_manual_analysis(self) -> Dict:
        """수동 매매 분석 실행"""
        analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        market_condition = self.analyze_market_condition()
        signals = self.get_trading_signals()

        # 결과 정리
        result = {
            "analysis_time": analysis_time,
            "market_condition": market_condition,
            "total_signals": len(signals),
            "buy_signals": len([s for s in signals if s.action == "BUY"]),
            "sell_signals": len([s for s in signals if s.action == "SELL"]),
            "signals": []
        }

        # 신호 정리
        for signal in sorted(signals, key=lambda x: x.confidence, reverse=True):
            stock_data = self.market_data[signal.symbol]
            signal_info = {
                "symbol": signal.symbol,
                "name": stock_data["name"],
                "current_price": stock_data["price"],
                "change_pct": stock_data["change"],
                "action": signal.action,
                "confidence": round(signal.confidence * 100, 1),
                "reason": signal.reason,
                "target_price": signal.target_price,
                "stop_loss": signal.stop_loss,
                "quantity": signal.quantity
            }
            result["signals"].append(signal_info)

        return result

def main():
    """메인 실행 함수"""
    strategy = ManualTradingStrategy()
    analysis_result = strategy.execute_manual_analysis()

    print("=" * 60)
    print("[Claude] 수동 매매 분석 결과")
    print("=" * 60)

    print(f"분석 시간: {analysis_result['analysis_time']}")
    print(f"시장 상황: {analysis_result['market_condition']}")
    print(f"총 신호: {analysis_result['total_signals']}개")
    print(f"   ├─ 매수 신호: {analysis_result['buy_signals']}개")
    print(f"   └─ 매도 신호: {analysis_result['sell_signals']}개")

    if analysis_result['signals']:
        print("\n[매매 신호 상세]")
        print("-" * 60)

        for i, signal in enumerate(analysis_result['signals'], 1):
            print(f"{i}. {signal['name']} ({signal['symbol']})")
            print(f"   현재가: {signal['current_price']:,}원 ({signal['change_pct']:+.1f}%)")
            print(f"   신호: {signal['action']} (신뢰도: {signal['confidence']}%)")
            print(f"   사유: {signal['reason']}")

            if signal['action'] == 'BUY':
                print(f"   수량: {signal['quantity']}주")
                print(f"   목표가: {signal['target_price']:,.0f}원")
                print(f"   손절가: {signal['stop_loss']:,.0f}원")
                estimated_investment = signal['current_price'] * signal['quantity']
                print(f"   투자금액: {estimated_investment:,}원")

            print()
    else:
        print("\n[관망] 현재 매매 신호 없음 - 관망 추천")

    # 결과 저장
    with open("data/manual_trading_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print("[저장] 분석 결과가 data/manual_trading_analysis.json에 저장되었습니다.")

    return analysis_result

if __name__ == "__main__":
    main()