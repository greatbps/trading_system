#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import os
from pathlib import Path

# UTF-8 인코딩 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

async def test_buy_signals():
    """매수 시그널 로직 테스트"""
    try:
        print("매수 시그널 로직 테스트")
        print("=" * 50)

        from config import Config
        from data_collectors.kis_collector import KISCollector
        from database.database_manager import DatabaseManager
        from core.trading_flow_manager import TradingFlowManager

        # 초기화
        config = Config()

        # 매매 플로우 관리자 생성 (내부에서 kis_collector, db_manager 생성)
        flow_manager = TradingFlowManager(config)

        # 내부 시스템 초기화
        await flow_manager.initialize()

        # 매수 시그널 체크 실행
        print("매수 시그널 체크 실행...")
        buy_candidates = await flow_manager.check_buy_signals()

        print(f"\n결과:")
        print(f"- 매수 후보 종목: {len(buy_candidates)}개")

        for i, candidate in enumerate(buy_candidates, 1):
            stock = candidate['stock']
            signal_score = candidate.get('signal_score', 0)
            signal_details = candidate.get('signal_details', {})

            print(f"\n{i}. {stock.symbol}({stock.name})")
            print(f"   - 현재가: {candidate['current_price']:,}원")
            print(f"   - 매수 수량: {candidate['target_quantity']:,}주")
            print(f"   - 예상 금액: {candidate['estimated_amount']:,}원")
            print(f"   - 시그널 점수: {signal_score}/5")

            if signal_details:
                print(f"   - 신호 상세:")
                for key, value in signal_details.items():
                    if key not in ['total_score', 'signal_count']:
                        print(f"     {key}: {value}")

        return True

    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_buy_signals())
    if success:
        print("\n매수 시그널 테스트 성공!")
    else:
        print("\n매수 시그널 테스트 실패!")