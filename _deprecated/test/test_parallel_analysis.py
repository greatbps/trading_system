#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병렬 분석 성능 테스트 - asyncio.FIRST_COMPLETED 검증
"""

import asyncio
import time
from typing import List


async def mock_stock_analysis(stock_id: int, delay: float) -> dict:
    """Mock 종목 분석 (다양한 지연 시간)"""
    await asyncio.sleep(delay)
    return {
        'stock_id': stock_id,
        'delay': delay,
        'result': f'분석 완료 (ID: {stock_id})'
    }


async def test_sequential_vs_parallel():
    """순차 vs 병렬 처리 성능 비교"""
    print("\n" + "="*80)
    print("순차 vs 병렬 처리 성능 비교")
    print("="*80 + "\n")

    # 테스트 데이터: 10개 종목, 다양한 처리 시간 (0.1~3.0초)
    stocks = [
        (1, 0.5), (2, 1.0), (3, 0.3), (4, 2.0), (5, 0.8),
        (6, 1.5), (7, 0.2), (8, 3.0), (9, 0.6), (10, 1.2)
    ]

    print(f"📊 테스트 조건:")
    print(f"  종목 수: {len(stocks)}개")
    print(f"  처리 시간: {[delay for _, delay in stocks]}초")
    print()

    # 1. 순차 처리
    print(f"{'─'*80}")
    print(f"1️⃣ 순차 처리 (기존 방식)")
    print(f"{'─'*80}")

    start_time = time.time()
    sequential_results = []

    for stock_id, delay in stocks:
        result = await mock_stock_analysis(stock_id, delay)
        sequential_results.append(result)
        print(f"  ✅ {stock_id}번 종목 완료 ({delay}초)")

    sequential_time = time.time() - start_time
    print(f"\n총 소요 시간: {sequential_time:.2f}초")
    print(f"완료 종목: {len(sequential_results)}개")

    # 2. 병렬 처리 (asyncio.wait with FIRST_COMPLETED)
    print(f"\n{'─'*80}")
    print(f"2️⃣ 병렬 처리 (FIRST_COMPLETED)")
    print(f"{'─'*80}")

    start_time = time.time()
    parallel_results = []

    tasks = [
        asyncio.create_task(mock_stock_analysis(stock_id, delay))
        for stock_id, delay in stocks
    ]

    pending = set(tasks)
    completed_count = 0

    while pending:
        done, pending = await asyncio.wait(
            pending,
            timeout=5.0,  # 5초 타임아웃
            return_when=asyncio.FIRST_COMPLETED
        )

        if not done:
            # 타임아웃: 느린 작업 취소
            slow_tasks = list(pending)[: max(1, len(pending) // 3)]
            for task in slow_tasks:
                task.cancel()
                pending.remove(task)
            print(f"  ⚠️ {len(slow_tasks)}개 느린 태스크 취소")
            continue

        # 완료된 태스크 처리
        for task in done:
            try:
                result = task.result()
                parallel_results.append(result)
                completed_count += 1
                print(f"  ✅ {result['stock_id']}번 종목 완료 ({result['delay']}초)")
            except asyncio.CancelledError:
                print(f"  ❌ 태스크 취소됨")
            except Exception as e:
                print(f"  ❌ 오류: {e}")

    parallel_time = time.time() - start_time
    print(f"\n총 소요 시간: {parallel_time:.2f}초")
    print(f"완료 종목: {len(parallel_results)}개")

    # 3. 성능 비교
    print(f"\n{'─'*80}")
    print(f"📊 성능 비교")
    print(f"{'─'*80}")

    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    time_saved = sequential_time - parallel_time

    print(f"  순차 처리: {sequential_time:.2f}초")
    print(f"  병렬 처리: {parallel_time:.2f}초")
    print(f"  단축 시간: {time_saved:.2f}초 ({(time_saved/sequential_time)*100:.1f}% 감소)")
    print(f"  속도 향상: {speedup:.2f}배")

    if speedup > 1.5:
        print(f"\n💡 평가: ✅ 병렬 처리로 {speedup:.1f}배 성능 향상")
    else:
        print(f"\n💡 평가: ⚠️ 병렬 처리 효과 미미 ({speedup:.1f}배)")

    print("\n" + "="*80)
    print("✅ 순차 vs 병렬 비교 테스트 완료")
    print("="*80 + "\n")


async def test_timeout_cancellation():
    """타임아웃 및 취소 메커니즘 테스트"""
    print("\n" + "="*80)
    print("타임아웃 및 취소 메커니즘 테스트")
    print("="*80 + "\n")

    # 테스트 데이터: 빠른 종목 5개 + 느린 종목 5개
    stocks = [
        (1, 0.3), (2, 0.4), (3, 0.2), (4, 0.5), (5, 0.3),  # 빠름
        (6, 5.0), (7, 6.0), (8, 7.0), (9, 8.0), (10, 9.0)  # 느림
    ]

    print(f"📊 테스트 조건:")
    print(f"  빠른 종목 5개: 0.2~0.5초")
    print(f"  느린 종목 5개: 5~9초")
    print(f"  타임아웃: 2.0초")
    print()

    start_time = time.time()
    completed_results = []
    cancelled_count = 0

    tasks = [
        asyncio.create_task(mock_stock_analysis(stock_id, delay))
        for stock_id, delay in stocks
    ]

    pending = set(tasks)

    while pending:
        done, pending = await asyncio.wait(
            pending,
            timeout=2.0,  # 2초 타임아웃
            return_when=asyncio.FIRST_COMPLETED
        )

        if not done:
            # 타임아웃: 느린 작업의 1/3 취소
            slow_tasks = list(pending)[: max(1, len(pending) // 3)]
            for task in slow_tasks:
                task.cancel()
                pending.remove(task)
                cancelled_count += 1
            print(f"  ⚠️ 타임아웃: {len(slow_tasks)}개 태스크 취소 (남은 태스크: {len(pending)}개)")
            continue

        # 완료된 태스크 처리
        for task in done:
            try:
                result = task.result()
                completed_results.append(result)
                print(f"  ✅ {result['stock_id']}번 종목 완료 ({result['delay']}초)")
            except asyncio.CancelledError:
                print(f"  ❌ 태스크 취소됨")

    total_time = time.time() - start_time

    print(f"\n📋 결과:")
    print(f"  총 소요 시간: {total_time:.2f}초")
    print(f"  완료 종목: {len(completed_results)}개")
    print(f"  취소된 종목: {cancelled_count}개")

    # 평가
    if len(completed_results) >= 5 and total_time < 5.0:
        print(f"\n💡 평가: ✅ 빠른 종목만 처리하고 느린 종목 적절히 취소됨")
        print(f"           (5개 이상 완료, 5초 이내 종료)")
    else:
        print(f"\n💡 평가: ⚠️ 취소 메커니즘 검증 필요")

    print("\n" + "="*80)
    print("✅ 타임아웃 및 취소 테스트 완료")
    print("="*80 + "\n")


async def test_error_handling():
    """오류 처리 테스트"""
    print("\n" + "="*80)
    print("오류 처리 테스트")
    print("="*80 + "\n")

    async def failing_analysis(stock_id: int, should_fail: bool):
        """실패 가능한 분석"""
        await asyncio.sleep(0.5)
        if should_fail:
            raise Exception(f"종목 {stock_id} 분석 실패")
        return {'stock_id': stock_id, 'result': 'Success'}

    print(f"📊 테스트 조건:")
    print(f"  총 10개 종목")
    print(f"  3개는 분석 실패")
    print()

    stocks = [
        (1, False), (2, True), (3, False), (4, False), (5, True),
        (6, False), (7, False), (8, True), (9, False), (10, False)
    ]

    tasks = [
        asyncio.create_task(failing_analysis(stock_id, should_fail))
        for stock_id, should_fail in stocks
    ]

    pending = set(tasks)
    success_count = 0
    error_count = 0

    while pending:
        done, pending = await asyncio.wait(
            pending,
            timeout=5.0,
            return_when=asyncio.FIRST_COMPLETED
        )

        if not done:
            break

        for task in done:
            try:
                result = task.result()
                success_count += 1
                print(f"  ✅ {result['stock_id']}번 종목 성공")
            except asyncio.CancelledError:
                print(f"  ❌ 태스크 취소됨")
            except Exception as e:
                error_count += 1
                print(f"  ❌ 오류: {e}")

    print(f"\n📋 결과:")
    print(f"  성공: {success_count}개")
    print(f"  실패: {error_count}개")

    if success_count == 7 and error_count == 3:
        print(f"\n💡 평가: ✅ 오류 발생해도 다른 종목 분석 계속 진행")
    else:
        print(f"\n💡 평가: ⚠️ 예상과 다름 (성공: {success_count}, 실패: {error_count})")

    print("\n" + "="*80)
    print("✅ 오류 처리 테스트 완료")
    print("="*80 + "\n")


async def main():
    """메인 테스트 실행"""
    try:
        await test_sequential_vs_parallel()
        await test_timeout_cancellation()
        await test_error_handling()

        print("\n" + "="*80)
        print("✅ 모든 병렬 분석 테스트 완료")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
