#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리스크 기반 주문 검증 테스트
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from trading.executor import TradingExecutor
from data_collectors.kis_collector import KISCollector


class MockDBManager:
    """Mock DB Manager for testing"""
    def __init__(self):
        self.test_stop_loss = None

    def get_session(self):
        from contextlib import contextmanager

        @contextmanager
        def session():
            class MockSession:
                def query(self, *args):
                    return self

                def filter(self, *args):
                    return self

                def first(self):
                    class MockStock:
                        def __init__(self):
                            self.stop_loss_price = self.parent.test_stop_loss

                    mock_stock = MockStock()
                    mock_stock.parent = self.parent
                    return mock_stock if self.parent.test_stop_loss else None

                def __init__(self, parent):
                    self.parent = parent

            yield MockSession(self)

        return session()


class MockKISCollector:
    """Mock KIS Collector for testing"""
    def __init__(self, test_balance=1000000, test_price=10000):
        self.test_balance = test_balance
        self.test_price = test_price

    async def get_balance(self):
        return {
            'available': self.test_balance,
            'total': self.test_balance,
            'details': []
        }

    async def get_current_price(self, symbol):
        return self.test_price

    async def get_stock_info(self, symbol):
        """종목 정보 조회 (Mock)"""
        return {
            'symbol': symbol,
            'current_price': self.test_price,
            'name': 'Test Stock'
        }

    async def get_holdings(self):
        """보유 종목 조회 (Mock)"""
        return []

    async def get_orderable_cash(self):
        """매수가능금액 조회 (Mock)"""
        return self.test_balance


async def test_risk_validation():
    """리스크 기반 주문 검증 테스트"""
    print("\n" + "="*80)
    print("리스크 기반 주문 검증 테스트")
    print("="*80 + "\n")

    config = Config()
    # 테스트용 한도 조정
    config.trading.HARD_MAX_POSITION = 10000000  # 1000만원으로 상향

    test_cases = [
        {
            'name': '정상 케이스: 리스크 한도 내 주문',
            'balance': 1000000,  # 100만원
            'current_price': 10000,
            'quantity': 10,
            'stop_loss_price': 9500,
            'expected_valid': True,
            'description': '예상손실 5,000원 (잔고의 0.5%) < 한도 20,000원 (2%)'
        },
        {
            'name': '경계 케이스: 리스크 한도 정확히 2%',
            'balance': 1000000,
            'current_price': 10000,
            'quantity': 40,
            'stop_loss_price': 9500,
            'expected_valid': True,
            'description': '예상손실 20,000원 (잔고의 2%) = 한도 20,000원'
        },
        {
            'name': '거부 케이스: 리스크 한도 초과',
            'balance': 1000000,
            'current_price': 10000,
            'quantity': 50,
            'stop_loss_price': 9500,
            'expected_valid': False,
            'description': '예상손실 25,000원 (잔고의 2.5%) > 한도 20,000원 (2%)'
        },
        {
            'name': '소액 계좌: 리스크 한도 초과',
            'balance': 100000,  # 10만원
            'current_price': 5000,
            'quantity': 5,
            'stop_loss_price': 4500,
            'expected_valid': False,  # 수정: 2.5% > 2% 이므로 거부됨
            'description': '예상손실 2,500원 (2.5%) > 한도 2,000원 (2%)'
        },
        {
            'name': '고가 주식: 소량 매수',
            'balance': 1000000,
            'current_price': 100000,
            'quantity': 1,
            'stop_loss_price': 95000,
            'expected_valid': True,
            'description': '예상손실 5,000원 (0.5%) < 한도 20,000원'
        },
        {
            'name': 'DB 손절가 없을 때: fallback 5% 적용',
            'balance': 1000000,
            'current_price': 10000,
            'quantity': 50,
            'stop_loss_price': None,  # DB에 없음
            'expected_valid': False,
            'description': '기본 5% 손절 적용 → 예상손실 25,000원 > 한도 20,000원'
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─'*80}")
        print(f"테스트 {i}: {case['name']}")
        print(f"{'─'*80}")
        print(f"📊 조건:")
        print(f"  계좌 잔고: {case['balance']:,}원")
        print(f"  현재가: {case['current_price']:,}원")
        print(f"  수량: {case['quantity']}주")
        print(f"  손절가: {case['stop_loss_price']:,}원" if case['stop_loss_price'] else "  손절가: None (DB 없음)")
        print(f"  {case['description']}")

        # Mock 객체 생성
        mock_db = MockDBManager()
        mock_db.test_stop_loss = case['stop_loss_price']

        mock_kis = MockKISCollector(
            test_balance=case['balance'],
            test_price=case['current_price']
        )

        executor = TradingExecutor(
            config=config,
            kis_collector=mock_kis,
            db_manager=mock_db
        )

        # 동적 한도 업데이트 (실제 매수 주문에서 호출됨)
        await executor.update_dynamic_limits()

        # 검증 실행
        try:
            result = await executor._validate_buy_order(
                symbol='005930',
                quantity=case['quantity'],
                price=case['current_price'],
                stop_loss_price=case['stop_loss_price']
            )

            is_valid = result.get('valid', False)

            print(f"\n📋 검증 결과:")
            print(f"  유효성: {'✅ 통과' if is_valid else '❌ 거부'}")

            if is_valid:
                print(f"  주문금액: {result.get('order_amount', 0):,}원")
                print(f"  예상 손실: {result.get('expected_loss', 0):,}원")
                print(f"  허용 한도: {result.get('max_loss_allowed', 0):,}원")
                print(f"  리스크 비율: {result.get('risk_ratio', 0)*100:.2f}%")
            else:
                print(f"  거부 사유: {result.get('reason', 'Unknown')}")

            # 예상 결과와 비교
            if is_valid == case['expected_valid']:
                print(f"\n💡 평가: ✅ 예상대로 {'통과' if is_valid else '거부'}됨")
            else:
                print(f"\n💡 평가: ❌ 예상과 다름 (예상: {'통과' if case['expected_valid'] else '거부'}, 실제: {'통과' if is_valid else '거부'})")

        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("✅ 리스크 검증 테스트 완료")
    print("="*80 + "\n")


async def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "="*80)
    print("엣지 케이스 테스트")
    print("="*80 + "\n")

    config = Config()
    # 테스트용 한도 조정
    config.trading.HARD_MAX_POSITION = 100000000  # 1억원

    edge_cases = [
        {
            'name': '잔고 0원',
            'balance': 0,
            'current_price': 10000,
            'quantity': 1,
            'stop_loss_price': 9500,
            'expected_valid': False
        },
        {
            'name': '수량 0',
            'balance': 1000000,
            'current_price': 10000,
            'quantity': 0,
            'stop_loss_price': 9500,
            'expected_valid': False
        },
        {
            'name': '손절가 > 현재가 (역전)',
            'balance': 1000000,
            'current_price': 10000,
            'quantity': 10,
            'stop_loss_price': 10500,
            'expected_valid': True  # 예상손실 0원
        },
        {
            'name': '매우 큰 수량',
            'balance': 10000000,
            'current_price': 1000,
            'quantity': 10000,
            'stop_loss_price': 950,
            'expected_valid': False
        }
    ]

    for i, case in enumerate(edge_cases, 1):
        print(f"\n{'─'*80}")
        print(f"엣지 케이스 {i}: {case['name']}")
        print(f"{'─'*80}")

        mock_db = MockDBManager()
        mock_db.test_stop_loss = case['stop_loss_price']

        mock_kis = MockKISCollector(
            test_balance=case['balance'],
            test_price=case['current_price']
        )

        executor = TradingExecutor(
            config=config,
            kis_collector=mock_kis,
            db_manager=mock_db
        )

        # 동적 한도 업데이트
        await executor.update_dynamic_limits()

        try:
            result = await executor._validate_buy_order(
                symbol='005930',
                quantity=case['quantity'],
                price=case['current_price'],
                stop_loss_price=case['stop_loss_price']
            )

            is_valid = result.get('valid', False)
            print(f"결과: {'✅ 통과' if is_valid else '❌ 거부'}")
            print(f"사유: {result.get('reason', 'N/A')}")

            if is_valid == case['expected_valid']:
                print(f"평가: ✅ 정상")
            else:
                print(f"평가: ⚠️ 예상과 다름")

        except Exception as e:
            print(f"❌ 예외 발생: {e}")

    print("\n" + "="*80)
    print("✅ 엣지 케이스 테스트 완료")
    print("="*80 + "\n")


async def main():
    """메인 테스트 실행"""
    try:
        await test_risk_validation()
        await test_edge_cases()

        print("\n" + "="*80)
        print("✅ 모든 리스크 검증 테스트 완료")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
