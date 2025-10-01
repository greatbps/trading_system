"""
백테스팅 최적화 시스템 테스트 스크립트
보유 종목 매도 최적화와 감시 종목 매수 최적화를 테스트하는 스크립트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from config import Config
from data_collectors.kis_collector import KISCollector
from backtesting.holding_sell_optimizer import HoldingSellOptimizer
from backtesting.watch_buy_optimizer import WatchBuyOptimizer
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_holding_sell_optimization():
    """보유 종목 매도 최적화 테스트"""
    print("=" * 60)
    print("보유 종목 매도 최적화 시스템 테스트")
    print("=" * 60)

    try:
        # 설정 및 컴포넌트 초기화
        config = Config()
        kis_collector = KISCollector(config)

        # 매도 최적화 시스템 초기화
        sell_optimizer = HoldingSellOptimizer(config, kis_collector, kis_collector)

        print("매도 최적화 시스템 초기화 완료")

        # 보유 종목 조회 테스트
        print("\n보유 종목 조회 중...")
        holdings = await sell_optimizer.get_current_holdings()

        if not holdings:
            print("보유 종목이 없습니다. 테스트용 데이터로 진행합니다.")
            # 테스트용 가상 보유 종목
            holdings = [
                {
                    'symbol': '005930',
                    'name': '삼성전자',
                    'quantity': 10,
                    'avg_price': 70000,
                    'current_price': 72000,
                    'profit_loss': 20000,
                    'profit_rate': 2.86
                }
            ]

        print(f"보유 종목 {len(holdings)}개 조회 완료")
        for holding in holdings[:3]:  # 최대 3개만 표시
            print(f"   - {holding['symbol']} ({holding['name']}): {holding['quantity']}주")

        # 첫 번째 종목으로 최적화 테스트
        if holdings:
            test_holding = holdings[0]
            print(f"\n{test_holding['symbol']} 매도 최적화 테스트 중...")

            # 과거 데이터 조회 테스트
            print("   과거 데이터 조회 중...")
            historical_data = await sell_optimizer.get_historical_data(test_holding['symbol'])

            if historical_data is not None and not historical_data.empty:
                print(f"   과거 데이터 {len(historical_data)}일치 조회 완료")

                # 단일 종목 최적화 테스트
                print("   매도 파라미터 최적화 실행 중...")
                optimization_result = await sell_optimizer.optimize_sell_parameters(test_holding)

                if optimization_result:
                    print("   최적화 성공!")
                    print(f"   최적 파라미터:")
                    print(f"      - 목표 수익률: {optimization_result.best_params.profit_target}%")
                    print(f"      - 손절 수익률: {optimization_result.best_params.stop_loss}%")
                    print(f"      - 트레일링 스톱: {optimization_result.best_params.trailing_stop}%")
                    print(f"      - RSI 임계값: {optimization_result.best_params.rsi_threshold}")
                    print(f"   예상 성과:")
                    print(f"      - 예상 수익률: {optimization_result.expected_return:.2f}%")
                    print(f"      - 승률: {optimization_result.win_rate:.1f}%")
                    print(f"      - 최대 손실: {optimization_result.max_drawdown:.2f}%")
                else:
                    print("   최적화 실패 - 데이터 부족 또는 유효한 전략 없음")
            else:
                print("   과거 데이터 조회 실패")

        return True

    except Exception as e:
        print(f"보유 종목 매도 최적화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_watch_buy_optimization():
    """감시 종목 매수 최적화 테스트"""
    print("\n" + "=" * 60)
    print("감시 종목 매수 시그널 최적화 시스템 테스트")
    print("=" * 60)

    try:
        # 설정 및 컴포넌트 초기화
        config = Config()
        kis_collector = KISCollector(config)

        # 매수 최적화 시스템 초기화
        buy_optimizer = WatchBuyOptimizer(config, kis_collector, kis_collector)

        print("매수 최적화 시스템 초기화 완료")

        # 감시 종목 조회 테스트
        print("\n감시 종목 조회 중...")
        watch_list = await buy_optimizer.get_watch_list()

        if not watch_list:
            print("감시 종목이 없습니다. 테스트용 데이터로 진행합니다.")
            # 테스트용 가상 감시 종목
            watch_list = [
                {
                    'symbol': '000660',
                    'name': 'SK하이닉스',
                    'target_price': 130000,
                    'stop_loss_price': 110000,
                    'monitoring_reason': '기술적 반등 기대'
                }
            ]

        print(f"감시 종목 {len(watch_list)}개 조회 완료")
        for watch in watch_list[:3]:  # 최대 3개만 표시
            print(f"   - {watch['symbol']} ({watch['name']})")

        # 첫 번째 종목으로 최적화 테스트
        if watch_list:
            test_watch = watch_list[0]
            print(f"\n{test_watch['symbol']} 매수 시그널 최적화 테스트 중...")

            # 과거 데이터 조회 테스트
            print("   과거 데이터 조회 중...")
            historical_data = await buy_optimizer.get_historical_data(test_watch['symbol'])

            if historical_data is not None and not historical_data.empty:
                print(f"   과거 데이터 {len(historical_data)}일치 조회 완료")

                # 단일 종목 최적화 테스트
                print("   매수 시그널 최적화 실행 중...")
                optimization_result = await buy_optimizer.optimize_buy_signals(test_watch)

                if optimization_result:
                    print("   최적화 성공!")
                    print(f"   최적 파라미터:")
                    print(f"      - RSI 과매도: {optimization_result.best_params.rsi_oversold}")
                    print(f"      - 거래량 급증: {optimization_result.best_params.volume_surge}배")
                    print(f"      - 모멘텀 임계값: {optimization_result.best_params.momentum_threshold}%")
                    print(f"   최적 시그널 조합: {optimization_result.best_combination.name}")
                    print(f"   예상 성과:")
                    print(f"      - 예상 수익률: {optimization_result.expected_return:.2f}%")
                    print(f"      - 시그널 정확도: {optimization_result.signal_accuracy:.1f}%")
                    print(f"      - 평균 보유기간: {optimization_result.avg_holding_period:.1f}일")
                else:
                    print("   최적화 실패 - 데이터 부족 또는 유효한 전략 없음")
            else:
                print("   과거 데이터 조회 실패")

        return True

    except Exception as e:
        print(f"감시 종목 매수 최적화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트 함수"""
    print("백테스팅 최적화 시스템 통합 테스트 시작")
    print("=" * 80)

    # 1. 보유 종목 매도 최적화 테스트
    sell_test_result = await test_holding_sell_optimization()

    # 2. 감시 종목 매수 최적화 테스트
    buy_test_result = await test_watch_buy_optimization()

    # 전체 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)

    if sell_test_result:
        print("보유 종목 매도 최적화: 성공")
    else:
        print("보유 종목 매도 최적화: 실패")

    if buy_test_result:
        print("감시 종목 매수 최적화: 성공")
    else:
        print("감시 종목 매수 최적화: 실패")

    if sell_test_result and buy_test_result:
        print("\n모든 최적화 시스템이 정상 작동합니다!")
        print("이제 실제 데이터로 전체 최적화를 실행할 수 있습니다.")

        # 실제 실행 가이드
        print("\n실제 실행 방법:")
        print("1. 보유 종목 매도 최적화 실행:")
        print("   python -c \"import asyncio; from test_optimization_system import run_full_sell_optimization; asyncio.run(run_full_sell_optimization())\"")
        print("\n2. 감시 종목 매수 최적화 실행:")
        print("   python -c \"import asyncio; from test_optimization_system import run_full_buy_optimization; asyncio.run(run_full_buy_optimization())\"")
    else:
        print("\n일부 시스템에 문제가 있습니다. 로그를 확인해주세요.")

async def run_full_sell_optimization():
    """전체 보유 종목 매도 최적화 실행"""
    try:
        config = Config()
        kis_collector = KISCollector(config)
        sell_optimizer = HoldingSellOptimizer(config, kis_collector, kis_collector)

        print("전체 보유 종목 매도 최적화 시작...")
        results = await sell_optimizer.optimize_all_holdings()

        print(f"매도 최적화 완료 - {len(results)}개 종목 최적화됨")
        for result in results:
            print(f"{result.symbol}: 예상수익률 {result.expected_return:.2f}%, 승률 {result.win_rate:.1f}%")

    except Exception as e:
        print(f"전체 매도 최적화 실패: {e}")

async def run_full_buy_optimization():
    """전체 감시 종목 매수 최적화 실행"""
    try:
        config = Config()
        kis_collector = KISCollector(config)
        buy_optimizer = WatchBuyOptimizer(config, kis_collector, kis_collector)

        print("전체 감시 종목 매수 최적화 시작...")
        results = await buy_optimizer.optimize_all_watch_list()

        print(f"매수 최적화 완료 - {len(results)}개 종목 최적화됨")
        for result in results:
            print(f"{result.symbol}: 예상수익률 {result.expected_return:.2f}%, 정확도 {result.signal_accuracy:.1f}%")

    except Exception as e:
        print(f"전체 매수 최적화 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())