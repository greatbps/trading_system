"""
감시 종목 매수 시그널 최적화 시스템
최근 3개월간 최적의 매수 시그널 발생 조합을 찾아 감시 종목에 적용하는 시스템
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
from sqlalchemy.orm import sessionmaker
from database.database_manager import DatabaseManager
from database.monitoring_models import MonitoringStock

@dataclass
class BuySignalParameters:
    """매수 시그널 파라미터 클래스"""
    rsi_oversold: float        # RSI 과매도 임계값
    macd_signal: bool          # MACD 신호 사용 여부
    volume_surge: float        # 거래량 급증 배수
    price_support: bool        # 지지선 터치 확인
    momentum_threshold: float   # 모멘텀 임계값
    bb_position: float         # 볼린저밴드 하단 근접도 (%)

@dataclass
class SignalCombination:
    """시그널 조합 클래스"""
    name: str
    conditions: List[str]
    weight: float

@dataclass
class BuyOptimizationResult:
    """매수 최적화 결과 클래스"""
    symbol: str
    best_params: BuySignalParameters
    best_combination: SignalCombination
    expected_return: float
    signal_accuracy: float
    avg_holding_period: float
    total_signals: int
    simulation_period: str

class WatchBuyOptimizer:
    """감시 종목 매수 시그널 최적화"""

    def __init__(self, config, kis_collector, data_collector):
        self.config = config
        self.kis_collector = kis_collector
        self.data_collector = data_collector
        self.logger = logging.getLogger(__name__)

        # 데이터베이스 연결
        self.db_manager = DatabaseManager(config)
        self.Session = sessionmaker(bind=self.db_manager.sync_engine)

        # 시그널 파라미터 범위
        self.param_ranges = {
            'rsi_oversold': [20, 25, 30, 35],
            'volume_surge': [1.5, 2.0, 2.5, 3.0],
            'momentum_threshold': [0.02, 0.03, 0.05, 0.07],  # 2%~7%
            'bb_position': [0, 10, 20, 30]  # 하단으로부터 %
        }

        # 시그널 조합 정의
        self.signal_combinations = [
            SignalCombination("단순_RSI", ["rsi_oversold"], 1.0),
            SignalCombination("RSI_거래량", ["rsi_oversold", "volume_surge"], 1.2),
            SignalCombination("기술적_종합", ["rsi_oversold", "macd_signal", "volume_surge"], 1.5),
            SignalCombination("지지선_반등", ["rsi_oversold", "price_support", "volume_surge"], 1.3),
            SignalCombination("모멘텀_돌파", ["momentum_threshold", "volume_surge", "bb_position"], 1.4),
            SignalCombination("완전_종합", ["rsi_oversold", "macd_signal", "volume_surge", "price_support", "momentum_threshold"], 2.0)
        ]

        # 결과 저장 경로
        self.results_dir = Path("reports/buy_optimization")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def get_watch_list(self) -> List[Dict[str, Any]]:
        """감시 종목 목록 조회"""
        try:
            session = self.Session()
            try:
                # 활성 감시 종목 조회
                monitoring_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.is_active == True
                ).all()

                watch_list = []
                for stock in monitoring_stocks:
                    stock_info = {
                        'symbol': stock.symbol,
                        'name': stock.name,
                        'target_price': stock.target_price,
                        'stop_loss_price': stock.stop_loss_price,
                        'created_at': stock.created_at,
                        'monitoring_reason': stock.monitoring_reason
                    }
                    watch_list.append(stock_info)

                self.logger.info(f"감시 종목 {len(watch_list)}개 조회 완료")
                return watch_list

            finally:
                session.close()

        except Exception as e:
            self.logger.error(f"감시 종목 조회 실패: {e}")
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

            # 필수 컬럼 확인
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    self.logger.warning(f"{symbol} 데이터에 {col} 컬럼이 없습니다")
                    return None

            # 날짜 정렬 및 기술적 지표 계산
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
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

            # MACD 계산
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']

            # 이동평균
            df['ma_5'] = df['close'].rolling(window=5).mean()
            df['ma_20'] = df['close'].rolling(window=20).mean()
            df['ma_60'] = df['close'].rolling(window=60).mean()

            # 볼린저 밴드
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_position'] = ((df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])) * 100

            # 거래량 지표
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']

            # 지지선/저항선 (단순화 버전)
            df['support_level'] = df['low'].rolling(window=20).min()
            df['resistance_level'] = df['high'].rolling(window=20).max()
            df['support_distance'] = ((df['close'] - df['support_level']) / df['support_level']) * 100

            # 모멘텀 지표
            df['momentum'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100

            return df

        except Exception as e:
            self.logger.error(f"기술적 지표 계산 실패: {e}")
            return df

    def generate_buy_signals(self, df: pd.DataFrame, params: BuySignalParameters, combination: SignalCombination) -> pd.DataFrame:
        """매수 시그널 생성"""
        try:
            df = df.copy()
            df['buy_signal'] = False
            df['signal_reasons'] = ''

            for i in range(len(df)):
                signals = []
                signal_count = 0
                total_weight = 0

                # 각 조건 확인
                if "rsi_oversold" in combination.conditions:
                    if df.loc[i, 'rsi'] <= params.rsi_oversold:
                        signals.append("RSI과매도")
                        signal_count += 1

                if "macd_signal" in combination.conditions:
                    if (df.loc[i, 'macd'] > df.loc[i, 'macd_signal'] and
                        i > 0 and df.loc[i-1, 'macd'] <= df.loc[i-1, 'macd_signal']):
                        signals.append("MACD상승")
                        signal_count += 1

                if "volume_surge" in combination.conditions:
                    if df.loc[i, 'volume_ratio'] >= params.volume_surge:
                        signals.append("거래량급증")
                        signal_count += 1

                if "price_support" in combination.conditions:
                    if df.loc[i, 'support_distance'] <= 2:  # 지지선 2% 이내
                        signals.append("지지선근접")
                        signal_count += 1

                if "momentum_threshold" in combination.conditions:
                    if df.loc[i, 'momentum'] >= params.momentum_threshold:
                        signals.append("모멘텀상승")
                        signal_count += 1

                if "bb_position" in combination.conditions:
                    if df.loc[i, 'bb_position'] <= params.bb_position:
                        signals.append("볼밴하단")
                        signal_count += 1

                # 시그널 조합 조건 확인
                required_signals = len(combination.conditions)
                if signal_count >= max(1, required_signals * 0.7):  # 70% 이상 조건 만족
                    df.loc[i, 'buy_signal'] = True
                    df.loc[i, 'signal_reasons'] = '+'.join(signals)

            return df

        except Exception as e:
            self.logger.error(f"매수 시그널 생성 실패: {e}")
            return df

    def simulate_buy_strategy(self, df: pd.DataFrame, params: BuySignalParameters, combination: SignalCombination) -> Dict[str, Any]:
        """매수 전략 시뮬레이션"""
        try:
            # 시그널 생성
            df = self.generate_buy_signals(df, params, combination)

            results = {
                'trades': [],
                'total_signals': 0,
                'successful_trades': 0,
                'total_return': 0,
                'holding_periods': []
            }

            # 매수 시그널이 있는 날짜들
            buy_signals = df[df['buy_signal'] == True]
            results['total_signals'] = len(buy_signals)

            if results['total_signals'] == 0:
                return results

            # 각 시그널에 대해 시뮬레이션
            for _, signal_row in buy_signals.iterrows():
                buy_date = signal_row['date']
                buy_price = signal_row['close']
                buy_index = signal_row.name

                # 매수 후 데이터 (최대 30일 후까지)
                future_data = df[df.index > buy_index].head(30)
                if future_data.empty:
                    continue

                # 매도 조건 확인 (간단한 전략)
                sell_triggered = False
                for _, future_row in future_data.iterrows():
                    current_price = future_row['close']
                    holding_period = (future_row['date'] - buy_date).days

                    # 매도 조건
                    profit_rate = ((current_price - buy_price) / buy_price) * 100

                    # 1. 10% 수익 달성
                    if profit_rate >= 10:
                        sell_triggered = True
                        sell_reason = "목표수익"
                    # 2. -5% 손절
                    elif profit_rate <= -5:
                        sell_triggered = True
                        sell_reason = "손절"
                    # 3. 20일 경과
                    elif holding_period >= 20:
                        sell_triggered = True
                        sell_reason = "기간만료"

                    if sell_triggered:
                        trade_result = {
                            'buy_date': buy_date,
                            'sell_date': future_row['date'],
                            'buy_price': buy_price,
                            'sell_price': current_price,
                            'profit_rate': profit_rate,
                            'holding_period': holding_period,
                            'sell_reason': sell_reason,
                            'signal_reasons': signal_row['signal_reasons']
                        }

                        results['trades'].append(trade_result)
                        results['total_return'] += profit_rate
                        results['holding_periods'].append(holding_period)

                        if profit_rate > 0:
                            results['successful_trades'] += 1

                        break

            # 결과 계산
            if len(results['trades']) > 0:
                results['avg_return'] = results['total_return'] / len(results['trades'])
                results['success_rate'] = (results['successful_trades'] / len(results['trades'])) * 100
                results['avg_holding_period'] = np.mean(results['holding_periods'])
                results['signal_accuracy'] = (len(results['trades']) / results['total_signals']) * 100
            else:
                results['avg_return'] = 0
                results['success_rate'] = 0
                results['avg_holding_period'] = 0
                results['signal_accuracy'] = 0

            return results

        except Exception as e:
            self.logger.error(f"매수 전략 시뮬레이션 실패: {e}")
            return {}

    async def optimize_buy_signals(self, watch_info: Dict) -> Optional[BuyOptimizationResult]:
        """특정 감시 종목의 매수 시그널 최적화"""
        try:
            symbol = watch_info['symbol']
            self.logger.info(f"{symbol} 매수 시그널 최적화 시작")

            # 과거 데이터 조회
            df = await self.get_historical_data(symbol, days=90)
            if df is None or df.empty:
                self.logger.warning(f"{symbol} 데이터 부족으로 최적화 불가")
                return None

            best_score = -float('inf')
            best_params = None
            best_combination = None
            best_result = None

            # 모든 시그널 조합에 대해 테스트
            for combination in self.signal_combinations:
                self.logger.debug(f"{symbol} - {combination.name} 조합 테스트 중")

                # 각 조합에 대해 파라미터 최적화
                for rsi_oversold in self.param_ranges['rsi_oversold']:
                    for volume_surge in self.param_ranges['volume_surge']:
                        for momentum_threshold in self.param_ranges['momentum_threshold']:
                            for bb_position in self.param_ranges['bb_position']:

                                params = BuySignalParameters(
                                    rsi_oversold=rsi_oversold,
                                    macd_signal=True,
                                    volume_surge=volume_surge,
                                    price_support=True,
                                    momentum_threshold=momentum_threshold,
                                    bb_position=bb_position
                                )

                                # 시뮬레이션 실행
                                sim_result = self.simulate_buy_strategy(df, params, combination)

                                if not sim_result or len(sim_result.get('trades', [])) == 0:
                                    continue

                                # 성과 점수 계산
                                score = self._calculate_buy_performance_score(sim_result, combination)

                                if score > best_score:
                                    best_score = score
                                    best_params = params
                                    best_combination = combination
                                    best_result = sim_result

            if best_params is None:
                self.logger.warning(f"{symbol} 최적화 실패 - 유효한 결과 없음")
                return None

            # 최적화 결과 생성
            optimization_result = BuyOptimizationResult(
                symbol=symbol,
                best_params=best_params,
                best_combination=best_combination,
                expected_return=best_result['avg_return'],
                signal_accuracy=best_result['signal_accuracy'],
                avg_holding_period=best_result['avg_holding_period'],
                total_signals=best_result['total_signals'],
                simulation_period="3개월"
            )

            self.logger.info(f"{symbol} 최적화 완료 - 예상 수익률: {optimization_result.expected_return:.2f}%")

            return optimization_result

        except Exception as e:
            self.logger.error(f"{watch_info.get('symbol', 'Unknown')} 최적화 실패: {e}")
            return None

    def _calculate_buy_performance_score(self, sim_result: Dict, combination: SignalCombination) -> float:
        """매수 성과 점수 계산"""
        try:
            avg_return = sim_result.get('avg_return', 0)
            success_rate = sim_result.get('success_rate', 0)
            signal_accuracy = sim_result.get('signal_accuracy', 0)
            total_signals = sim_result.get('total_signals', 0)

            # 기본 점수: 평균 수익률
            score = avg_return

            # 성공률 보너스
            score += (success_rate - 50) * 0.15

            # 시그널 정확도 보너스
            score += signal_accuracy * 0.1

            # 조합 가중치 적용
            score *= combination.weight

            # 시그널 수 보정 (너무 적으면 신뢰성 낮음)
            if total_signals < 3:
                score *= 0.3
            elif total_signals > 15:
                score *= 1.1

            return score

        except Exception as e:
            self.logger.error(f"매수 성과 점수 계산 실패: {e}")
            return -float('inf')

    async def optimize_all_watch_list(self) -> List[BuyOptimizationResult]:
        """모든 감시 종목의 매수 시그널 최적화"""
        try:
            self.logger.info("모든 감시 종목 매수 시그널 최적화 시작")

            # 감시 종목 조회
            watch_list = await self.get_watch_list()
            if not watch_list:
                self.logger.warning("감시 종목이 없어 최적화를 실행할 수 없습니다")
                return []

            results = []

            for i, watch_info in enumerate(watch_list, 1):
                symbol = watch_info['symbol']
                self.logger.info(f"[{i}/{len(watch_list)}] {symbol} 최적화 중...")

                try:
                    result = await self.optimize_buy_signals(watch_info)
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
            await self._save_buy_optimization_results(results)

            self.logger.info(f"감시 종목 매수 최적화 완료 - {len(results)}개 종목 최적화됨")
            return results

        except Exception as e:
            self.logger.error(f"전체 감시 종목 최적화 실패: {e}")
            return []

    async def _save_buy_optimization_results(self, results: List[BuyOptimizationResult]):
        """매수 최적화 결과 저장"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"buy_optimization_{timestamp}.json"
            filepath = self.results_dir / filename

            # 결과를 딕셔너리로 변환
            results_dict = []
            for result in results:
                result_dict = {
                    'symbol': result.symbol,
                    'best_params': {
                        'rsi_oversold': result.best_params.rsi_oversold,
                        'macd_signal': result.best_params.macd_signal,
                        'volume_surge': result.best_params.volume_surge,
                        'price_support': result.best_params.price_support,
                        'momentum_threshold': result.best_params.momentum_threshold,
                        'bb_position': result.best_params.bb_position
                    },
                    'best_combination': {
                        'name': result.best_combination.name,
                        'conditions': result.best_combination.conditions,
                        'weight': result.best_combination.weight
                    },
                    'expected_return': result.expected_return,
                    'signal_accuracy': result.signal_accuracy,
                    'avg_holding_period': result.avg_holding_period,
                    'total_signals': result.total_signals,
                    'simulation_period': result.simulation_period,
                    'optimization_date': timestamp
                }
                results_dict.append(result_dict)

            # JSON 파일로 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, ensure_ascii=False, indent=2)

            self.logger.info(f"매수 최적화 결과 저장 완료: {filepath}")

        except Exception as e:
            self.logger.error(f"매수 최적화 결과 저장 실패: {e}")

    def get_optimized_buy_parameters(self, symbol: str) -> Optional[Tuple[BuySignalParameters, SignalCombination]]:
        """저장된 최적화 매수 파라미터 조회"""
        try:
            # 가장 최근 결과 파일 찾기
            result_files = list(self.results_dir.glob("buy_optimization_*.json"))
            if not result_files:
                return None

            latest_file = max(result_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # 해당 종목의 최적화 파라미터 찾기
            for result in results:
                if result['symbol'] == symbol:
                    params_dict = result['best_params']
                    combo_dict = result['best_combination']

                    params = BuySignalParameters(
                        rsi_oversold=params_dict['rsi_oversold'],
                        macd_signal=params_dict['macd_signal'],
                        volume_surge=params_dict['volume_surge'],
                        price_support=params_dict['price_support'],
                        momentum_threshold=params_dict['momentum_threshold'],
                        bb_position=params_dict['bb_position']
                    )

                    combination = SignalCombination(
                        name=combo_dict['name'],
                        conditions=combo_dict['conditions'],
                        weight=combo_dict['weight']
                    )

                    return params, combination

            return None

        except Exception as e:
            self.logger.error(f"{symbol} 최적화 매수 파라미터 조회 실패: {e}")
            return None