#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 보유종목 상세 조회 및 디버깅
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config import Config
from data_collectors.kis_collector import KISCollector
from utils.logger import get_logger

async def main():
    """보유종목 상세 조회"""
    logger = get_logger("check_holdings")

    try:
        # 설정 로드
        config = Config()

        # KIS Collector 초기화
        kis_collector = KISCollector(config)
        await kis_collector.initialize()

        print("=" * 60)
        print("현재 보유종목 상세 조회")
        print("=" * 60)

        # 보유종목 조회
        balance_result = await kis_collector.get_holdings()

        if not balance_result.get('success'):
            print(f"[ERROR] 보유종목 조회 실패: {balance_result.get('error')}")
            return

        holdings = balance_result.get('data', [])
        print(f"[OK] 보유종목 {len(holdings)}개 조회 완료\n")

        # 013360, 045340 종목 찾기
        target_symbols = ['013360', '045340']
        found_holdings = []

        for holding in holdings:
            symbol = holding.get('pdno', '')
            if symbol in target_symbols:
                found_holdings.append(holding)

        if found_holdings:
            print(f"[FOUND] 문제 종목 발견: {len(found_holdings)}개")
            for holding in found_holdings:
                print(f"\n종목: {holding.get('pdno', 'N/A')} - {holding.get('prdt_name', 'N/A')}")
                print(f"  보유수량(hldg_qty): {holding.get('hldg_qty', 'N/A')}")
                print(f"  매도가능수량(ord_psbl_qty): {holding.get('ord_psbl_qty', 'N/A')}")
                print(f"  현재가(prpr): {holding.get('prpr', 'N/A')}")
                print(f"  평가금액(evlu_amt): {holding.get('evlu_amt', 'N/A')}")
                print(f"  평가손익(evlu_pfls_amt): {holding.get('evlu_pfls_amt', 'N/A')}")
                print(f"  손익률(evlu_pfls_rt): {holding.get('evlu_pfls_rt', 'N/A')}%")

                # 수량 관련 모든 필드 출력
                qty_fields = {k: v for k, v in holding.items() if 'qty' in k.lower() or 'psbl' in k.lower()}
                print(f"  [QTY] 수량 관련 필드: {qty_fields}")

        else:
            print("[WARNING] 문제 종목(013360, 045340)이 현재 보유종목에 없습니다.")
            print("\n현재 보유종목 목록:")
            for i, holding in enumerate(holdings[:10], 1):  # 최대 10개만 표시
                symbol = holding.get('pdno', 'N/A')
                name = holding.get('prdt_name', 'N/A')
                qty = holding.get('hldg_qty', '0')
                print(f"  [{i}] {symbol} - {name} ({qty}주)")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        logger.error(f"보유종목 조회 중 오류: {e}")

    finally:
        if 'kis_collector' in locals():
            await kis_collector.close()

if __name__ == "__main__":
    asyncio.run(main())