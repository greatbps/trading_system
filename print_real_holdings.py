#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 KIS 계좌 보유종목 상세 출력
"""

import asyncio
import os
import sys
from datetime import datetime

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.logger import get_logger
from data_collectors.kis_collector import KISCollector

async def main():
    """실제 보유종목 상세 출력"""
    logger = get_logger("RealHoldings")

    try:
        # config를 APIConfig 객체로 변환
        class ConfigWrapper:
            def __init__(self):
                self.api = config.APIConfig()

        wrapped_config = ConfigWrapper()
        kis_collector = KISCollector(wrapped_config)

        print("=" * 80)
        print("실제 KIS 계좌 보유종목 상세 정보")
        print("=" * 80)

        # 보유종목 조회
        holdings = await kis_collector.get_holdings()

        if not holdings:
            print("보유종목이 없거나 조회에 실패했습니다.")
            return

        print(f"총 보유종목 수: {len(holdings)}개")
        print()

        # 종목별 상세 정보 출력
        total_value = 0
        total_profit_loss = 0

        print(f"{'종목코드':>8} {'종목명':<15} {'수량':>8} {'평균가':>8} {'현재가':>8} {'수익률':>8} {'평가금액':>10} {'손익금액':>10}")
        print("-" * 90)

        for symbol, data in holdings.items():
            name = data.get('name', '')[:12]  # 종목명 12자리로 제한
            quantity = data.get('quantity', 0)
            avg_price = data.get('avg_price', 0)
            current_price = data.get('current_price', 0)
            evaluation = data.get('evaluation', 0)
            profit_loss = data.get('profit_loss', 0)
            profit_rate = data.get('profit_rate', 0)

            print(f"{symbol:>8} {name:<15} {quantity:>8} {avg_price:>8.0f} {current_price:>8} {profit_rate:>7.2f}% {evaluation:>10} {profit_loss:>10}")

            total_value += evaluation
            total_profit_loss += profit_loss

        print("-" * 90)
        print(f"{'합계':<32} {'':>16} {'':>8} {total_value:>10} {total_profit_loss:>10}")
        print()

        # 손절 대상 확인 (3% 손실 기준)
        stop_loss_candidates = []
        for symbol, data in holdings.items():
            profit_rate = data.get('profit_rate', 0)
            if profit_rate <= -3.0:  # 3% 이상 손실
                stop_loss_candidates.append((symbol, data))

        if stop_loss_candidates:
            print("*** 손절 대상 종목 (3% 이상 손실) ***")
            print("-" * 60)
            for symbol, data in stop_loss_candidates:
                name = data.get('name', '')
                profit_rate = data.get('profit_rate', 0)
                profit_loss = data.get('profit_loss', 0)
                print(f"{symbol} {name:<15} 손실률: {profit_rate:.2f}% 손실금액: {profit_loss:,}원")
        else:
            print("현재 손절이 필요한 종목이 없습니다.")

        print("=" * 80)

    except Exception as e:
        logger.error(f"보유종목 조회 실패: {e}")
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())