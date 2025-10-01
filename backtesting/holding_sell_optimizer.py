"""
보유 종목 매도 최적화 시스템
최근 3개월간 매도 조건 충족 시 파라미터를 변경하며 최적 매도 타이밍을 찾는 시스템
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from pathlib import Path
import json

@dataclass
class SellParameters:
    """매도 파라미터 클래스"""
    profit_target: float  # 목표 수익률 (%)
    stop_loss: float      # 손절 수익률 (%)
    trailing_stop: float  # 트레일링 스톱 (%)
    rsi_threshold: float  # RSI 임계값
    volume_threshold: float  # 거래량 임계값

@dataclass
class OptimizationResult:
    """최적화 결과 클래스"""
    symbol: str
    best_params: SellParameters
    expected_return: float
    win_rate: float
    max_drawdown: float
    total_trades: int
    simulation_period: str

class HoldingSellOptimizer:
    """보유 종목 매도 최적화"""

    def __init__(self, config, kis_collector, data_collector):
        self.config = config
        self.kis_collector = kis_collector
        self.data_collector = data_collector
        self.logger = logging.getLogger(__name__)

        # 최적화 파라미터 범위 설정
        self.param_ranges = {
            'profit_target': [3, 5, 7, 10, 15, 20],  # %
            'stop_loss': [-3, -5, -7, -10, -15, -20],  # %
            'trailing_stop': [1, 2, 3, 5],  # %
            'rsi_threshold': [70, 75, 80, 85],
            'volume_threshold': [1.2, 1.5, 2.0, 2.5]  # 평균 대비 배수
        }

        # 결과 저장 경로
        self.results_dir = Path("reports/sell_optimization")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def get_current_holdings(self) -> List[Dict[str, Any]]:
        """현재 보유 종목 조회"""
        try:
            holdings = await self.kis_collector.get_holdings()
            if not holdings:
                self.logger.warning("보유 종목이 없습니다")
                return []

            # 실제 보유 종목만 필터링 (수량 > 0)
            actual_holdings = []
            for symbol, info in holdings.items():
                if info.get('quantity', 0) > 0:
                    holding_data = {
                        'symbol': symbol,
                        'name': info.get('name', ''),
                        'quantity': info.get('quantity', 0),
                        'avg_price': info.get('avg_price', 0),
                        'current_price': info.get('current_price', 0),
                        'profit_loss': info.get('profit_loss', 0),
                        'profit_rate': info.get('profit_rate', 0)
                    }
                    actual_holdings.append(holding_data)

            self.logger.info(f"실제 보유 종목 {len(actual_holdings)}개 조회 완료")
            return actual_holdings

        except Exception as e:
            self.logger.error(f"보유 종목 조회 실패: {e}")
            return []

    async def get_historical_data(self, symbol: str, days: int = 90) -> Optional[pd.DataFrame]:
        """과거 데이터 조회 (3개월)"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 데이터 수집기를 통해 과거 데이터 조회
            data = await self.data_collector.get_chart_data(
                symbol=symbol,
                period="D",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )

            if not data:
                self.logger.warning(f"{symbol} 과거 데이터 조회 실패")
                return None

            # DataFrame으로 변환
            df = pd.DataFrame(data)
            if df.empty:
                return None

            # 필수 컬럼 확인 및 추가
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    self.logger.warning(f"{symbol} 데이터에 {col} 컬럼이 없습니다")
                    return None

            # 날짜 정렬
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            # 기술적 지표 계산
            df = self._calculate_technical_indicators(df)

            return df

        except Exception as e:
            self.logger.error(f"{symbol} 과거 데이터 조회 실패: {e}")
            return None

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        try:
            # RSI 계산
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

            # 이동평균 계산
            df['ma_5'] = df['close'].rolling(window=5).mean()
            df['ma_20'] = df['close'].rolling(window=20).mean()

            # 거래량 이동평균
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']

            # 볼린저 밴드
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

            return df

        except Exception as e:
            self.logger.error(f"기술적 지표 계산 실패: {e}")
            return df

    def simulate_sell_strategy(self, df: pd.DataFrame, holding_info: Dict, params: SellParameters) -> Dict[str, Any]:
        """매도 전략 시뮬레이션"""
        try:
            buy_price = holding_info['avg_price']
            results = {
                'trades': [],
                'total_return': 0,
                'win_count': 0,
                'loss_count': 0,
                'max_drawdown': 0,
                'holding_periods': []
            }

            position_open = False
            entry_price = buy_price
            entry_date = None
            max_price_since_entry = buy_price

            for i, row in df.iterrows():
                current_price = row['close']
                current_date = row['date']

                if not position_open:
                    # 매수 시점부터 시뮬레이션 시작
                    position_open = True
                    entry_price = buy_price
                    entry_date = current_date
                    max_price_since_entry = buy_price
                    continue

                # 트레일링 스톱 업데이트
                if current_price > max_price_since_entry:
                    max_price_since_entry = current_price

                # 매도 조건 확인
                profit_rate = ((current_price - entry_price) / entry_price) * 100
                trailing_stop_price = max_price_since_entry * (1 - params.trailing_stop / 100)

                sell_signal = False
                sell_reason = ""

                # 1. 목표 수익률 달성
                if profit_rate >= params.profit_target:
                    sell_signal = True
                    sell_reason = "profit_target"

                # 2. 손절 조건
                elif profit_rate <= params.stop_loss:
                    sell_signal = True
                    sell_reason = "stop_loss"

                # 3. 트레일링 스톱
                elif current_price <= trailing_stop_price:
                    sell_signal = True
                    sell_reason = "trailing_stop"

                # 4. RSI 과매수
                elif row['rsi'] >= params.rsi_threshold and profit_rate > 0:
                    sell_signal = True
                    sell_reason = "rsi_overbought"

                # 5. 거래량 급증 + 수익 상태
                elif row['volume_ratio'] >= params.volume_threshold and profit_rate > 5:
                    sell_signal = True
                    sell_reason = "volume_spike"

                if sell_signal:
                    # 거래 기록
                    holding_period = (current_date - entry_date).days
                    trade_result = {
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'profit_rate': profit_rate,
                        'holding_period': holding_period,
                        'sell_reason': sell_reason
                    }

                    results['trades'].append(trade_result)
                    results['total_return'] += profit_rate
                    results['holding_periods'].append(holding_period)

                    if profit_rate > 0:
                        results['win_count'] += 1
                    else:
                        results['loss_count'] += 1

                    # 새로운 포지션 시작 (연속 매매 시뮬레이션)
                    position_open = True
                    entry_price = current_price
                    entry_date = current_date
                    max_price_since_entry = current_price

            # 결과 계산
            total_trades = len(results['trades'])
            if total_trades > 0:
                results['avg_return'] = results['total_return'] / total_trades
                results['win_rate'] = (results['win_count'] / total_trades) * 100
                results['avg_holding_period'] = np.mean(results['holding_periods'])

                # 최대 손실 계산
                returns = [trade['profit_rate'] for trade in results['trades']]
                cumulative_returns = np.cumsum(returns)
                peak = np.maximum.accumulate(cumulative_returns)
                drawdown = cumulative_returns - peak
                results['max_drawdown'] = np.min(drawdown)
            else:
                results['avg_return'] = 0
                results['win_rate'] = 0
                results['avg_holding_period'] = 0
                results['max_drawdown'] = 0

            return results

        except Exception as e:
            self.logger.error(f"매도 전략 시뮬레이션 실패: {e}")
            return {}

    async def optimize_sell_parameters(self, holding_info: Dict) -> Optional[OptimizationResult]:
        """특정 종목의 매도 파라미터 최적화"""
        try:
            symbol = holding_info['symbol']
            self.logger.info(f"{symbol} 매도 파라미터 최적화 시작")

            # 과거 데이터 조회
            df = await self.get_historical_data(symbol, days=90)
            if df is None or df.empty:
                self.logger.warning(f"{symbol} 데이터 부족으로 최적화 불가")
                return None

            best_score = -float('inf')
            best_params = None
            best_result = None

            # 모든 파라미터 조합 테스트
            total_combinations = (
                len(self.param_ranges['profit_target']) *
                len(self.param_ranges['stop_loss']) *
                len(self.param_ranges['trailing_stop']) *
                len(self.param_ranges['rsi_threshold']) *
                len(self.param_ranges['volume_threshold'])
            )

            combination_count = 0

            for profit_target in self.param_ranges['profit_target']:
                for stop_loss in self.param_ranges['stop_loss']:
                    for trailing_stop in self.param_ranges['trailing_stop']:
                        for rsi_threshold in self.param_ranges['rsi_threshold']:
                            for volume_threshold in self.param_ranges['volume_threshold']:
                                combination_count += 1

                                # 파라미터 유효성 검사
                                if abs(stop_loss) >= profit_target:
                                    continue  # 손절이 목표수익보다 크면 스킵

                                params = SellParameters(
                                    profit_target=profit_target,
                                    stop_loss=stop_loss,
                                    trailing_stop=trailing_stop,
                                    rsi_threshold=rsi_threshold,
                                    volume_threshold=volume_threshold
                                )

                                # 시뮬레이션 실행
                                sim_result = self.simulate_sell_strategy(df, holding_info, params)

                                if not sim_result or len(sim_result.get('trades', [])) == 0:
                                    continue

                                # 성과 점수 계산 (복합 지표)
                                score = self._calculate_performance_score(sim_result)

                                if score > best_score:
                                    best_score = score
                                    best_params = params
                                    best_result = sim_result

                                # 진행률 로깅 (10%마다)
                                if combination_count % (total_combinations // 10) == 0:
                                    progress = (combination_count / total_combinations) * 100
                                    self.logger.info(f"{symbol} 최적화 진행률: {progress:.1f}%")

            if best_params is None:
                self.logger.warning(f"{symbol} 최적화 실패 - 유효한 결과 없음")
                return None

            # 최적화 결과 생성
            optimization_result = OptimizationResult(
                symbol=symbol,
                best_params=best_params,
                expected_return=best_result['avg_return'],
                win_rate=best_result['win_rate'],
                max_drawdown=best_result['max_drawdown'],
                total_trades=len(best_result['trades']),
                simulation_period="3개월"
            )

            self.logger.info(f"{symbol} 최적화 완료 - 예상 수익률: {optimization_result.expected_return:.2f}%")

            return optimization_result

        except Exception as e:
            self.logger.error(f"{holding_info.get('symbol', 'Unknown')} 최적화 실패: {e}")
            return None

    def _calculate_performance_score(self, sim_result: Dict) -> float:
        """성과 점수 계산"""
        try:
            avg_return = sim_result.get('avg_return', 0)
            win_rate = sim_result.get('win_rate', 0)
            max_drawdown = sim_result.get('max_drawdown', 0)
            total_trades = len(sim_result.get('trades', []))

            # 기본 점수: 평균 수익률
            score = avg_return

            # 승률 보너스 (승률이 높을수록 가점)
            score += (win_rate - 50) * 0.1

            # 최대 손실 페널티 (손실이 클수록 감점)
            score += max_drawdown * 0.5  # max_drawdown은 음수

            # 거래 횟수 보정 (너무 적으면 신뢰성 낮음)
            if total_trades < 5:
                score *= 0.5
            elif total_trades > 20:
                score *= 1.1

            return score

        except Exception as e:
            self.logger.error(f"성과 점수 계산 실패: {e}")
            return -float('inf')

    async def optimize_all_holdings(self) -> List[OptimizationResult]:
        """모든 보유 종목의 매도 파라미터 최적화"""
        try:
            self.logger.info("모든 보유 종목 매도 최적화 시작")

            # 보유 종목 조회
            holdings = await self.get_current_holdings()
            if not holdings:
                self.logger.warning("보유 종목이 없어 최적화를 실행할 수 없습니다")
                return []

            results = []

            for i, holding in enumerate(holdings, 1):
                symbol = holding['symbol']
                self.logger.info(f"[{i}/{len(holdings)}] {symbol} 최적화 중...")

                try:
                    result = await self.optimize_sell_parameters(holding)
                    if result:
                        results.append(result)
                        self.logger.info(f"{symbol} 최적화 성공")
                    else:
                        self.logger.warning(f"{symbol} 최적화 실패")

                except Exception as e:
                    self.logger.error(f"{symbol} 최적화 중 오류: {e}")
                    continue

                # 과도한 API 호출 방지
                await asyncio.sleep(1)

            # 결과 저장
            await self._save_optimization_results(results)

            self.logger.info(f"보유 종목 매도 최적화 완료 - {len(results)}개 종목 최적화됨")
            return results

        except Exception as e:
            self.logger.error(f"전체 보유 종목 최적화 실패: {e}")
            return []

    async def _save_optimization_results(self, results: List[OptimizationResult]):
        """최적화 결과 저장"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sell_optimization_{timestamp}.json"
            filepath = self.results_dir / filename

            # 결과를 딕셔너리로 변환
            results_dict = []
            for result in results:
                result_dict = {
                    'symbol': result.symbol,
                    'best_params': {
                        'profit_target': result.best_params.profit_target,
                        'stop_loss': result.best_params.stop_loss,
                        'trailing_stop': result.best_params.trailing_stop,
                        'rsi_threshold': result.best_params.rsi_threshold,
                        'volume_threshold': result.best_params.volume_threshold
                    },
                    'expected_return': result.expected_return,
                    'win_rate': result.win_rate,
                    'max_drawdown': result.max_drawdown,
                    'total_trades': result.total_trades,
                    'simulation_period': result.simulation_period,
                    'optimization_date': timestamp
                }
                results_dict.append(result_dict)

            # JSON 파일로 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, ensure_ascii=False, indent=2)

            self.logger.info(f"최적화 결과 저장 완료: {filepath}")

        except Exception as e:
            self.logger.error(f"최적화 결과 저장 실패: {e}")

    def get_optimized_parameters(self, symbol: str) -> Optional[SellParameters]:
        """저장된 최적화 파라미터 조회"""
        try:
            # 가장 최근 결과 파일 찾기
            result_files = list(self.results_dir.glob("sell_optimization_*.json"))
            if not result_files:
                return None

            latest_file = max(result_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # 해당 종목의 최적화 파라미터 찾기
            for result in results:
                if result['symbol'] == symbol:
                    params_dict = result['best_params']
                    return SellParameters(
                        profit_target=params_dict['profit_target'],
                        stop_loss=params_dict['stop_loss'],
                        trailing_stop=params_dict['trailing_stop'],
                        rsi_threshold=params_dict['rsi_threshold'],
                        volume_threshold=params_dict['volume_threshold']
                    )

            return None

        except Exception as e:
            self.logger.error(f"{symbol} 최적화 파라미터 조회 실패: {e}")
            return None