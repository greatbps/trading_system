#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/emergency_stop_loss.py

긴급 손절 실행 스크립트
- 현재 보유 종목 중 손절 기준 도달 종목 자동 매도
- 실시간 가격 확인 및 즉시 주문 실행
"""

import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import config
from utils.logger import get_logger
from database.database_manager import DatabaseManager
from data_collectors.kis_collector import KISCollector
from trading.executor import TradingExecutor

class EmergencyStopLoss:
    """긴급 손절 실행기"""

    def __init__(self):
        self.logger = get_logger("EmergencyStopLoss")
        self.config = config

        # Trading config 인스턴스 생성
        self.trading_config = config.TradingConfig()

        # 손절 기준
        self.stop_loss_ratio = getattr(self.trading_config, 'STOP_LOSS_RATIO', 0.03)  # 3%

        # 데이터베이스 매니저
        try:
            self.db_manager = DatabaseManager(config)
        except Exception as e:
            self.logger.error(f"DatabaseManager 초기화 실패: {e}")
            self.db_manager = None

        # KIS API 수집기
        try:
            self.kis_collector = KISCollector(config)
        except Exception as e:
            self.logger.error(f"KISCollector 초기화 실패: {e}")
            self.kis_collector = None

        # 거래 실행기
        try:
            self.executor = TradingExecutor(self.trading_config, self.kis_collector, self.db_manager)
        except Exception as e:
            self.logger.error(f"TradingExecutor 초기화 실패: {e}")
            self.executor = None

    def connect_db(self) -> sqlite3.Connection:
        """데이터베이스 연결"""
        return sqlite3.connect("trading_system.db")

    async def get_current_positions(self) -> List[Dict[str, Any]]:
        """현재 보유 포지션 조회"""
        try:
            positions = []

            # DB에서 활성 모니터링 종목 조회
            with self.connect_db() as conn:
                cursor = conn.cursor()

                # 보유량이 있는 활성 종목 조회
                cursor.execute("""
                    SELECT
                        symbol, name, buy_price, holding_quantity,
                        current_price, profit_loss, profit_rate,
                        buy_time, target_price, stop_loss_price
                    FROM monitoring_stocks
                    WHERE status = 'ACTIVE'
                    AND holding_quantity > 0
                    ORDER BY profit_rate ASC
                """)

                rows = cursor.fetchall()

                for row in rows:
                    position = {
                        'symbol': row[0],
                        'name': row[1],
                        'buy_price': row[2] or 0,
                        'holding_quantity': row[3] or 0,
                        'current_price': row[4] or 0,
                        'profit_loss': row[5] or 0,
                        'profit_rate': row[6] or 0,
                        'buy_time': row[7],
                        'target_price': row[8] or 0,
                        'stop_loss_price': row[9] or 0
                    }
                    positions.append(position)

                self.logger.info(f"현재 보유 포지션 {len(positions)}개 조회 완료")
                return positions

        except Exception as e:
            self.logger.error(f"포지션 조회 실패: {e}")
            return []

    async def get_real_time_prices(self, symbols: List[str]) -> Dict[str, int]:
        """실시간 가격 조회"""
        try:
            prices = {}

            if not self.kis_collector:
                self.logger.warning("KIS Collector 없음, DB 가격 사용")
                return prices

            for symbol in symbols:
                try:
                    # KIS API로 실시간 가격 조회
                    stock_info = await self.kis_collector.get_stock_info(symbol)
                    if stock_info:
                        current_price = getattr(stock_info, 'current_price', 0)
                        if current_price > 0:
                            prices[symbol] = current_price
                            self.logger.debug(f"{symbol} 현재가: {current_price:,}원")
                        else:
                            self.logger.warning(f"{symbol} 가격 정보 없음")

                    # API 호출 간격 조절
                    await asyncio.sleep(0.1)

                except Exception as e:
                    self.logger.error(f"{symbol} 가격 조회 실패: {e}")
                    continue

            self.logger.info(f"실시간 가격 조회 완료: {len(prices)}개 종목")
            return prices

        except Exception as e:
            self.logger.error(f"실시간 가격 조회 실패: {e}")
            return {}

    def identify_stop_loss_candidates(self, positions: List[Dict[str, Any]],
                                    real_time_prices: Dict[str, int]) -> List[Dict[str, Any]]:
        """손절 대상 종목 식별"""
        try:
            stop_loss_candidates = []

            for position in positions:
                symbol = position['symbol']
                buy_price = position['buy_price']
                holding_quantity = position['holding_quantity']

                if buy_price <= 0 or holding_quantity <= 0:
                    continue

                # 실시간 가격 사용 (없으면 DB 가격)
                current_price = real_time_prices.get(symbol, position['current_price'])

                if current_price <= 0:
                    self.logger.warning(f"{symbol} 현재가 정보 없음, 건너뛰기")
                    continue

                # 손실률 계산
                loss_rate = (current_price - buy_price) / buy_price
                loss_percentage = loss_rate * 100

                # 손절 기준 확인
                if loss_rate <= -self.stop_loss_ratio:  # 손실이 기준 이상
                    candidate = {
                        'symbol': symbol,
                        'name': position['name'],
                        'buy_price': buy_price,
                        'current_price': current_price,
                        'holding_quantity': holding_quantity,
                        'loss_rate': loss_rate,
                        'loss_percentage': loss_percentage,
                        'loss_amount': int((current_price - buy_price) * holding_quantity),
                        'market_value': current_price * holding_quantity,
                        'urgency': 'HIGH' if loss_rate <= -0.05 else 'MEDIUM'  # 5% 이상 손실시 고위험
                    }
                    stop_loss_candidates.append(candidate)

                    self.logger.warning(
                        f"[STOP LOSS] 손절 대상: {symbol}({position['name']}) "
                        f"매수가: {buy_price:,}원 -> 현재가: {current_price:,}원 "
                        f"손실률: {loss_percentage:.2f}% "
                        f"손실금액: {candidate['loss_amount']:,}원"
                    )

            # 손실률 순으로 정렬 (손실이 큰 순서)
            stop_loss_candidates.sort(key=lambda x: x['loss_rate'])

            self.logger.info(f"손절 대상 종목 {len(stop_loss_candidates)}개 식별")
            return stop_loss_candidates

        except Exception as e:
            self.logger.error(f"손절 대상 식별 실패: {e}")
            return []

    async def execute_emergency_sell_orders(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """긴급 매도 주문 실행"""
        try:
            sell_results = []

            if not self.executor:
                self.logger.error("TradingExecutor 없음, 매도 불가")
                return sell_results

            for candidate in candidates:
                symbol = candidate['symbol']
                quantity = candidate['holding_quantity']
                current_price = candidate['current_price']

                self.logger.critical(
                    f"[EMERGENCY SELL] 긴급 손절 실행: {symbol} {quantity}주 @ {current_price:,}원"
                )

                try:
                    # 시장가 매도 주문 실행
                    result = await self.executor.execute_sell_order(
                        symbol=symbol,
                        quantity=quantity,
                        price=None,  # 시장가
                        order_type=self.executor.OrderType.MARKET
                    )

                    if result.get('success'):
                        sell_info = {
                            'symbol': symbol,
                            'name': candidate['name'],
                            'quantity': quantity,
                            'order_id': result.get('order_id'),
                            'status': 'SUCCESS',
                            'executed_price': result.get('average_price', current_price),
                            'loss_amount': candidate['loss_amount'],
                            'loss_percentage': candidate['loss_percentage'],
                            'timestamp': datetime.now()
                        }

                        self.logger.info(
                            f"[SUCCESS] 손절 완료: {symbol} {quantity}주 "
                            f"손실: {candidate['loss_amount']:,}원 ({candidate['loss_percentage']:.2f}%)"
                        )
                    else:
                        sell_info = {
                            'symbol': symbol,
                            'name': candidate['name'],
                            'quantity': quantity,
                            'order_id': None,
                            'status': 'FAILED',
                            'error': result.get('error', '알 수 없는 오류'),
                            'loss_amount': candidate['loss_amount'],
                            'loss_percentage': candidate['loss_percentage'],
                            'timestamp': datetime.now()
                        }

                        self.logger.error(
                            f"[FAILED] 손절 실패: {symbol} - {result.get('error', '알 수 없는 오류')}"
                        )

                    sell_results.append(sell_info)

                    # 주문 간격 조절
                    await asyncio.sleep(1)

                except Exception as e:
                    self.logger.error(f"[ERROR] {symbol} 매도 주문 실행 오류: {e}")

                    sell_results.append({
                        'symbol': symbol,
                        'name': candidate['name'],
                        'quantity': quantity,
                        'status': 'ERROR',
                        'error': str(e),
                        'timestamp': datetime.now()
                    })

            return sell_results

        except Exception as e:
            self.logger.error(f"긴급 매도 실행 실패: {e}")
            return []

    def update_monitoring_status(self, sell_results: List[Dict[str, Any]]) -> None:
        """모니터링 상태 업데이트"""
        try:
            with self.connect_db() as conn:
                cursor = conn.cursor()

                for result in sell_results:
                    if result['status'] == 'SUCCESS':
                        # 성공한 매도는 상태를 COMPLETED로 변경
                        cursor.execute("""
                            UPDATE monitoring_stocks
                            SET status = 'COMPLETED',
                                sell_time = ?,
                                remove_reason = ?,
                                updated_at = ?
                            WHERE symbol = ? AND status = 'ACTIVE'
                        """, (
                            result['timestamp'],
                            f"긴급손절: {result['loss_percentage']:.2f}% 손실",
                            datetime.now(),
                            result['symbol']
                        ))

                        self.logger.info(f"{result['symbol']} 모니터링 상태 완료로 변경")

                conn.commit()

        except Exception as e:
            self.logger.error(f"모니터링 상태 업데이트 실패: {e}")

    def generate_summary_report(self, candidates: List[Dict[str, Any]],
                              sell_results: List[Dict[str, Any]]) -> str:
        """요약 보고서 생성"""
        try:
            report = f"""
[EMERGENCY STOP LOSS REPORT] 긴급 손절 실행 보고서
=================================================

실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
손절 기준: {self.stop_loss_ratio * 100:.1f}%

[EXECUTION RESULT] 실행 결과
---------------------------
"""

            if not candidates:
                report += "\n[INFO] 손절 대상 종목 없음 (모든 포지션 정상)\n"
                return report

            total_loss = sum(c['loss_amount'] for c in candidates)
            successful_sells = len([r for r in sell_results if r['status'] == 'SUCCESS'])

            report += f"""
- 손절 대상 종목: {len(candidates)}개
- 실행 완료: {successful_sells}개
- 총 손실금액: {total_loss:,}원

[DETAIL] 상세 내역
-----------------
"""

            for i, candidate in enumerate(candidates, 1):
                result = next((r for r in sell_results if r['symbol'] == candidate['symbol']), None)
                status = result['status'] if result else 'NOT_EXECUTED'

                report += f"""
{i}. {candidate['symbol']} ({candidate['name']})
   - 매수가: {candidate['buy_price']:,}원
   - 현재가: {candidate['current_price']:,}원
   - 수량: {candidate['holding_quantity']}주
   - 손실률: {candidate['loss_percentage']:.2f}%
   - 손실금액: {candidate['loss_amount']:,}원
   - 실행결과: {status}
"""

                if result and result['status'] == 'FAILED':
                    report += f"   - 실패사유: {result.get('error', '알 수 없음')}\n"

            if successful_sells > 0:
                report += f"""
[WARNING] 후속 조치 필요사항
--------------------------
1. 매도 체결 확인 및 정산
2. 손절 사유 분석 및 기록
3. 향후 동일 종목 진입 시 주의
4. 리스크 관리 전략 재검토

[RECOMMENDATION] 개선 권장사항
----------------------------
- 손절 기준 재검토: 현재 {self.stop_loss_ratio * 100:.1f}%
- 포지션 사이즈 조정 고려
- 진입 타이밍 정밀도 향상
"""

            return report

        except Exception as e:
            self.logger.error(f"보고서 생성 실패: {e}")
            return f"보고서 생성 실패: {str(e)}"

    async def run_emergency_stop_loss(self) -> None:
        """긴급 손절 전체 프로세스 실행"""
        try:
            self.logger.critical("[EMERGENCY] 긴급 손절 프로세스 시작")

            # 1. 현재 포지션 조회
            positions = await self.get_current_positions()

            if not positions:
                self.logger.info("[INFO] 현재 보유 포지션 없음")
                return

            # 2. 실시간 가격 조회
            symbols = [pos['symbol'] for pos in positions]
            real_time_prices = await self.get_real_time_prices(symbols)

            # 3. 손절 대상 식별
            candidates = self.identify_stop_loss_candidates(positions, real_time_prices)

            if not candidates:
                self.logger.info("[INFO] 손절 대상 종목 없음")
                return

            # 4. 긴급 매도 실행
            self.logger.critical(f"[EMERGENCY] {len(candidates)}개 종목 긴급 손절 실행")
            sell_results = await self.execute_emergency_sell_orders(candidates)

            # 5. 모니터링 상태 업데이트
            self.update_monitoring_status(sell_results)

            # 6. 결과 보고서
            report = self.generate_summary_report(candidates, sell_results)
            print(report)

            # 로그 파일에도 기록
            self.logger.critical("[EMERGENCY COMPLETE] 긴급 손절 완료:\n" + report)

        except Exception as e:
            self.logger.error(f"긴급 손절 프로세스 실패: {e}")
            print(f"[FAILED] 긴급 손절 실행 실패: {e}")


async def main():
    """메인 실행 함수"""
    emergency_system = EmergencyStopLoss()

    print("[EMERGENCY SYSTEM] 긴급 손절 시스템 시작")
    print("=" * 50)

    await emergency_system.run_emergency_stop_loss()

    print("=" * 50)
    print("[EMERGENCY SYSTEM] 긴급 손절 시스템 완료")


if __name__ == "__main__":
    asyncio.run(main())