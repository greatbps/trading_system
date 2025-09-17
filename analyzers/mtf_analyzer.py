#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/mtf_analyzer.py

Multi-Time Frame Analyzer
"""
import pandas as pd
from typing import Dict, List, Optional

from utils.logger import get_logger
from analyzers.technical_analyzer import TechnicalAnalyzer

class MTFAnalyzer:
    """
    Multi-Time Frame (MTF) Analyzer.
    Analyzes trend alignment across different time frames (e.g., daily, weekly, monthly).
    """

    def __init__(self, config=None, data_collector=None):
        self.config = config
        self.data_collector = data_collector
        self.logger = get_logger("MTFAnalyzer")
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.timeframes = {
            'daily': 'D',
            'weekly': 'W-MON',
            'monthly': 'ME'
        }
        self.logger.info("✅ MTF 분석기 초기화 완료")

    async def analyze(self, symbol: str, price_data: List[Dict]) -> Dict:
        """
        Performs multi-time frame analysis.
        If data is insufficient, it attempts to fetch more data.
        If still insufficient, it analyzes available timeframes.
        """
        TARGET_DATA_POINTS = 250  # Aim for about 1 year of data
        MIN_DATA_POINTS = 30      # Absolute minimum for daily analysis

        # 1. Check if we have enough data, if not, try to fetch more
        if len(price_data) < TARGET_DATA_POINTS and self.data_collector:
            self.logger.info(f"ℹ️ {symbol} 데이터 부족 ({len(price_data)}개), 추가 데이터 수집 시도...")
            try:
                # Assuming get_ohlcv_data returns a list of objects with date attributes
                more_data_raw = await self.data_collector.get_ohlcv_data(symbol, 'D', count=TARGET_DATA_POINTS)
                
                # Convert raw data to list of dicts
                more_data = [
                    {'date': item.date.strftime('%Y-%m-%d'), 'open': int(item.open), 'high': int(item.high), 'low': int(item.low), 'close': int(item.close), 'volume': int(item.volume)}
                    for item in more_data_raw
                ]

                if len(more_data) > len(price_data):
                    self.logger.info(f"✅ {symbol} 추가 데이터 수집 성공 ({len(more_data)}개)")
                    price_data = more_data
                else:
                    self.logger.warning(f"⚠️ {symbol} 추가 데이터 수집 실패, 기존 데이터로 분석 진행.")
            except Exception as e:
                self.logger.error(f"❌ {symbol} 추가 데이터 수집 중 오류: {e}, 기존 데이터로 분석 진행.")

        # 2. Final check on data availability
        if len(price_data) < MIN_DATA_POINTS:
            self.logger.warning(f"⚠️ {symbol} 데이터가 너무 부족하여 ({len(price_data)}개) - MTF 분석 불가능")
            return self._generate_neutral_result("데이터 절대 부족")

        self.logger.info(f"🔍 {symbol} MTF 분석 시작 (데이터: {len(price_data)}개)...")
        
        try:
            df = self._convert_to_dataframe(price_data)
            
            timeframe_results = {}
            MIN_RESAMPLED_POINTS = 12 # Minimum points needed for a meaningful analysis on a timeframe

            for name, rule in self.timeframes.items():
                resampled_df = self._resample_data(df, rule)
                if resampled_df is not None and len(resampled_df) >= MIN_RESAMPLED_POINTS:
                    resampled_price_data = resampled_df.reset_index().to_dict('records')
                    for item in resampled_price_data:
                        if 'index' in item:
                            item['date'] = item.pop('index').strftime('%Y-%m-%d')

                    try:
                        analysis = await self.technical_analyzer.analyze_stock(symbol, resampled_price_data)
                        timeframe_results[name] = {
                            'score': analysis.get('technical_score', 50),
                            'signal': analysis.get('signals', {}).get('overall_signal', 'HOLD'),
                            'trend': analysis.get('indicators', {}).get('supertrend_trend', 'NEUTRAL')
                        }
                    except ValueError as e:
                        # MTF용으로 데이터 부족은 정상적인 상황임 (경고 없이 기본값 처리)
                        timeframe_results[name] = {
                            'score': 50,
                            'signal': 'HOLD', 
                            'trend': 'NEUTRAL'
                        }
                    self.logger.info(f"✅ {symbol} {name} 시간대 분석 완료.")
                else:
                    # 데이터 부족 시 해당 타임프레임 건너뜀 (정상적인 상황)
                    timeframe_results[name] = None
            
            return self._synthesize_results(timeframe_results)

        except Exception as e:
            self.logger.error(f"❌ {symbol} MTF 분석 중 오류 발생: {e}", exc_info=True)
            return self._generate_neutral_result(f"분석 오류: {str(e)}")

    def _convert_to_dataframe(self, price_data: List[Dict]) -> pd.DataFrame:
        """Converts price data to a pandas DataFrame."""
        df = pd.DataFrame(price_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df.astype(float)

    def _resample_data(self, df: pd.DataFrame, rule: str) -> Optional[pd.DataFrame]:
        """Resamples OHLCV data to a different timeframe."""
        try:
            resampled_df = df.resample(rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            resampled_df.dropna(inplace=True)
            return resampled_df
        except Exception as e:
            self.logger.warning(f"⚠️ 데이터 리샘플링 실패 (rule: {rule}): {e}")
            return None

    def _synthesize_results(self, timeframe_results: Dict) -> Dict:
        """
        Synthesizes the analysis results from different timeframes into a final score.
        """
        final_score = 50.0
        valid_analyses = [res for res in timeframe_results.values() if res is not None]
        
        if not valid_analyses:
            return self._generate_neutral_result("모든 타임프레임 분석 실패")

        # Trend alignment check
        trends = [res['trend'] for res in valid_analyses]
        num_bullish = trends.count('BULLISH')
        num_bearish = trends.count('BEARISH')

        alignment_score = 0
        if num_bullish == len(valid_analyses):
            alignment_score = 100  # All bullish
            alignment_status = "STRONG_BULLISH_ALIGNMENT"
        elif num_bearish == len(valid_analyses):
            alignment_score = 0    # All bearish
            alignment_status = "STRONG_BEARISH_ALIGNMENT"
        elif num_bullish > num_bearish:
            alignment_score = 65
            alignment_status = "MODERATE_BULLISH_ALIGNMENT"
        elif num_bearish > num_bullish:
            alignment_score = 35
            alignment_status = "MODERATE_BEARISH_ALIGNMENT"
        else:
            alignment_score = 50
            alignment_status = "MIXED_SIGNALS"

        # Weighted average of scores
        weights = {'daily': 0.5, 'weekly': 0.3, 'monthly': 0.2}
        weighted_score = 0
        total_weight = 0
        
        for name, result in timeframe_results.items():
            if result and name in weights:
                weighted_score += result['score'] * weights[name]
                total_weight += weights[name]
        
        if total_weight > 0:
            weighted_score /= total_weight
        else:
            weighted_score = 50

        # Combine alignment and weighted score
        final_score = (weighted_score * 0.6) + (alignment_score * 0.4)

        return {
            'mtf_score': round(final_score, 2),
            'alignment_status': alignment_status,
            'details': timeframe_results
        }

    def _generate_neutral_result(self, reason: str) -> Dict:
        """Generates a neutral result in case of errors or insufficient data."""
        return {
            'mtf_score': 50.0,
            'alignment_status': 'NEUTRAL',
            'details': {},
            'error': reason
        }
