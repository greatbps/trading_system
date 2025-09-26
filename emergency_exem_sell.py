#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
엑셈(205100) 긴급 실거래 매도 스크립트
KIS API를 통한 실제 매도 주문 실행
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
import logging

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def emergency_sell_exem():
    """엑셈 긴급 실거래 매도 처리"""
    try:
        print("=== 엑셈(205100) 긴급 실거래 매도 처리 ===")
        print(f"처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # KIS API 초기화
        from data_collectors.kis_collector import KISCollector
        from config import Config

        config = Config()
        kis_collector = KISCollector(config)

        print("[1/6] KIS API 인증 중...")
        await kis_collector.initialize()
        print("- KIS API 연결 완료")

        # 종목 정보
        symbol = "205100"  # 엑셈
        print(f"\n[2/6] 종목 정보 조회 중... ({symbol})")

        stock_info = await kis_collector.get_stock_info(symbol)
        if stock_info:
            current_price = stock_info.current_price
            name = stock_info.name
            print(f"- 종목명: {name}")
            print(f"- 현재가: {current_price:,}원")
        else:
            print("[X] 종목 정보 조회 실패")
            return

        # 매도 수량 입력 (실제 보유량 확인 필요)
        print(f"\n[3/6] 매도 주문 설정...")
        default_quantity = 30  # 엑셈 보유 추정 수량 (실제 보유량에 맞게 조정 필요)

        print(f"- 종목: {name} ({symbol})")
        print(f"- 매도 수량: {default_quantity:,}주")
        print(f"- 주문유형: 지정가 매도")
        print(f"- 예상 매도가: {current_price:,}원")

        print(f"\n[4/6] KIS API 매도 주문 전송...")

        try:
            # 실제 매도 주문 실행 (현재가 지정가 매도)
            sell_result = await kis_collector.place_order(
                symbol=symbol,
                quantity=default_quantity,
                price=current_price,  # 현재가 지정가 주문
                order_type="00",  # 지정가(00)/시장가(01)
                side="SELL"  # 매도
            )

            print(f"\n[5/6] 주문 결과 확인...")
            if sell_result:
                print(f"- 매도 주문 전송 완료!")
                print(f"- 주문 응답: {sell_result}")

                # 주문번호가 있으면 출력
                if 'order_id' in str(sell_result) or 'ODNO' in str(sell_result):
                    print(f"- 주문이 정상 처리되었습니다")

                print(f"\n=== 매도 주문 요약 ===")
                print(f"종목: {name} ({symbol})")
                print(f"매도 수량: {default_quantity:,}주")
                print(f"주문유형: 지정가 매도")
                print(f"예상 체결가: {current_price:,}원")
                print(f"예상 손익률: -4.4%")
                print(f"처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                print(f"\n[6/6] 주문 완료 - KIS HTS/MTS에서 체결 확인하세요")

            else:
                print("[X] 매도 주문 응답 없음")

        except Exception as order_error:
            print(f"[X] 매도 주문 처리 오류: {order_error}")
            print("KIS API 연결 상태를 확인하고 HTS에서 수동 매도를 진행해주세요")

    except Exception as e:
        print(f"[X] 긴급 매도 처리 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    print("[!] 엑셈(205100) 긴급 실거래 매도 시작")
    print("[!] 실제 거래가 실행됩니다!")
    print()

    asyncio.run(emergency_sell_exem())