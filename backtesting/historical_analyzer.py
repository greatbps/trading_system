#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/backtesting/historical_analyzer.py

과거 데이터 분석기 - AI 예측 정확도 검증 및 시장 상황 분석
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

# Note: Historical database functions need to be implemented for full functionality
from analyzers.ai_controller import AIController
from analyzers.gemini_analyzer import GeminiAnalyzer

logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    """시장 상황"""
    BULL_MARKET = "BULL_MARKET"  # 강세장
    BEAR_MARKET = "BEAR_MARKET"  # 약세장
    SIDEWAYS = "SIDEWAYS"  # 횡보장
    HIGH_VOLATILITY = "HIGH_VOLATILITY"  # 고변동성
    LOW_VOLATILITY = "LOW_VOLATILITY"  # 저변동성

@dataclass
class HistoricalData:
    """과거 데이터"""
    date: datetime
    symbol: str
    price: float
    volume: int
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    sentiment_data: Dict[str, Any] = field(default_factory=dict)
    market_condition: Optional[MarketCondition] = None
    
    # AI 예측 데이터
    ai_prediction: Optional[Dict[str, Any]] = None
    actual_outcome: Optional[Dict[str, Any]] = None
    prediction_accuracy: Optional[float] = None

@dataclass
class MarketRegimeAnalysis:
    """시장 체제 분석"""
    period_start: datetime
    period_end: datetime
    regime: MarketCondition
    characteristics: Dict[str, float]
    key_events: List[str] = field(default_factory=list)
    
    # 성과 지표
    avg_return: float = 0.0
    volatility: float = 0.0
    max_drawdown: float = 0.0
    
    # AI 성과
    ai_accuracy: float = 0.0
    ai_prediction_count: int = 0

class HistoricalAnalyzer:
    """과거 데이터 분석기 - AI 예측 검증 및 시장 분석"""
    
    def __init__(self, config=None):
        """과거 데이터 분석기 초기화"""
        try:
            if config:
                self.ai_controller = AIController(config)
            else:
                # 기본 설정으로 초기화
                from config import get_config
                default_config = get_config()
                self.ai_controller = AIController(default_config)
            self.gemini_analyzer = GeminiAnalyzer()
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            self.logger = logging.getLogger(__name__)
            self.logger.warning(f"AI 컨트롤러 초기화 실패: {e}")
            self.ai_controller = None
            self.gemini_analyzer = None
    
    async def analyze_ai_prediction_accuracy(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        AI 예측 정확도 분석
        
        Args:
            start_date: 분석 시작일
            end_date: 분석 종료일
            symbols: 분석 대상 종목
        
        Returns:
            Dict: AI 예측 정확도 분석 결과
        """
        try:
            self.logger.info(f"AI 예측 정확도 분석 시작: {start_date} ~ {end_date}")
            
            accuracy_results = {
                'overall_accuracy': 0.0,
                'symbol_accuracy': {},
                'prediction_types': {},
                'confidence_correlation': 0.0,
                'detailed_analysis': []
            }
            
            total_predictions = 0
            correct_predictions = 0
            confidence_scores = []
            accuracy_scores = []
            
            for symbol in symbols:
                symbol_correct = 0
                symbol_total = 0
                
                # 해당 기간의 과거 데이터 가져오기
                historical_data = await self._get_historical_data(symbol, start_date, end_date)
                
                for data_point in historical_data:
                    if data_point.ai_prediction and data_point.actual_outcome:
                        
                        # 예측 정확도 계산
                        accuracy = await self._calculate_prediction_accuracy(
                            data_point.ai_prediction, data_point.actual_outcome
                        )
                        
                        if accuracy is not None:
                            symbol_total += 1
                            total_predictions += 1
                            
                            if accuracy > 0.6:  # 60% 이상을 정확한 예측으로 간주
                                symbol_correct += 1
                                correct_predictions += 1
                            
                            # 신뢰도와 정확도 상관관계 분석
                            confidence = data_point.ai_prediction.get('confidence', 0)
                            confidence_scores.append(confidence)
                            accuracy_scores.append(accuracy)
                            
                            # 상세 분석 데이터 저장
                            accuracy_results['detailed_analysis'].append({
                                'date': data_point.date,
                                'symbol': symbol,
                                'prediction': data_point.ai_prediction,
                                'actual': data_point.actual_outcome,
                                'accuracy': accuracy,
                                'confidence': confidence
                            })
                
                # 종목별 정확도 계산
                if symbol_total > 0:
                    accuracy_results['symbol_accuracy'][symbol] = {
                        'accuracy': (symbol_correct / symbol_total) * 100,
                        'total_predictions': symbol_total,
                        'correct_predictions': symbol_correct
                    }
            
            # 전체 정확도 계산
            if total_predictions > 0:
                accuracy_results['overall_accuracy'] = (correct_predictions / total_predictions) * 100
            
            # 신뢰도와 정확도 상관관계
            if len(confidence_scores) > 10:
                correlation = np.corrcoef(confidence_scores, accuracy_scores)[0, 1]
                accuracy_results['confidence_correlation'] = correlation if not np.isnan(correlation) else 0.0
            
            # 예측 유형별 정확도 분석
            accuracy_results['prediction_types'] = await self._analyze_prediction_types(
                accuracy_results['detailed_analysis']
            )
            
            self.logger.info(f"AI 예측 정확도 분석 완료: {accuracy_results['overall_accuracy']:.2f}%")
            
            return accuracy_results
            
        except Exception as e:
            self.logger.error(f"AI 예측 정확도 분석 오류: {e}")
            raise
    
    async def identify_market_regimes(
        self,
        start_date: datetime,
        end_date: datetime,
        market_index: str = "KOSPI"
    ) -> List[MarketRegimeAnalysis]:
        """
        시장 체제 식별 및 분석
        
        Args:
            start_date: 분석 시작일
            end_date: 분석 종료일
            market_index: 시장 지수 (기본값: KOSPI)
        
        Returns:
            List[MarketRegimeAnalysis]: 시장 체제 분석 결과
        """
        try:
            self.logger.info(f"시장 체제 분석 시작: {start_date} ~ {end_date}")
            
            # 시장 데이터 가져오기
            market_data = await self._get_market_index_data(market_index, start_date, end_date)
            
            if not market_data:
                return []
            
            # 체제 변화점 식별
            regime_changes = await self._identify_regime_changes(market_data)
            
            # 각 체제별 분석
            regime_analyses = []
            
            for i, change_point in enumerate(regime_changes):
                period_start = change_point['start_date']
                period_end = change_point['end_date']
                regime = change_point['regime']
                
                # 해당 기간 데이터 필터링
                period_data = [
                    d for d in market_data 
                    if period_start <= d.date <= period_end
                ]
                
                if not period_data:
                    continue
                
                # 체제별 특성 분석
                analysis = MarketRegimeAnalysis(
                    period_start=period_start,
                    period_end=period_end,
                    regime=regime,
                    characteristics=await self._analyze_regime_characteristics(period_data)
                )
                
                # 성과 지표 계산
                analysis.avg_return = await self._calculate_period_return(period_data)
                analysis.volatility = await self._calculate_period_volatility(period_data)
                analysis.max_drawdown = await self._calculate_period_drawdown(period_data)
                
                # AI 성과 분석
                ai_performance = await self._analyze_ai_performance_in_regime(
                    period_start, period_end, regime
                )
                analysis.ai_accuracy = ai_performance.get('accuracy', 0.0)
                analysis.ai_prediction_count = ai_performance.get('prediction_count', 0)
                
                # 주요 이벤트 식별
                analysis.key_events = await self._identify_key_events(period_start, period_end)
                
                regime_analyses.append(analysis)
            
            self.logger.info(f"시장 체제 분석 완료: {len(regime_analyses)}개 체제 식별")
            
            return regime_analyses
            
        except Exception as e:
            self.logger.error(f"시장 체제 분석 오류: {e}")
            raise
    
    async def validate_historical_news_impact(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        과거 뉴스 영향 검증
        
        Args:
            start_date: 분석 시작일
            end_date: 분석 종료일
            symbols: 분석 대상 종목
        
        Returns:
            Dict: 뉴스 영향 검증 결과
        """
        try:
            self.logger.info(f"과거 뉴스 영향 검증 시작: {start_date} ~ {end_date}")
            
            validation_results = {
                'overall_correlation': 0.0,
                'symbol_correlations': {},
                'sentiment_accuracy': 0.0,
                'impact_predictions': {},
                'detailed_analysis': []
            }
            
            for symbol in symbols:
                # TODO: 해당 기간의 뉴스 데이터 가져오기 (구현 필요)
                news_data = []  # await get_historical_news(symbol, start_date, end_date)
                
                if not news_data:
                    continue
                
                symbol_correlations = []
                sentiment_accuracies = []
                
                for news_item in news_data:
                    # 뉴스 발표일 이후 주가 변동 분석
                    price_impact = await self._analyze_news_price_impact(
                        symbol, news_item['date'], news_item
                    )
                    
                    if price_impact:
                        # AI 감정 분석과 실제 가격 변동 상관관계
                        predicted_sentiment = news_item.get('sentiment_score', 0)
                        actual_impact = price_impact['price_change_pct']
                        
                        correlation = self._calculate_sentiment_correlation(
                            predicted_sentiment, actual_impact
                        )
                        
                        if correlation is not None:
                            symbol_correlations.append(correlation)
                        
                        # 감정 분석 정확도
                        sentiment_accuracy = self._validate_sentiment_prediction(
                            predicted_sentiment, actual_impact
                        )
                        
                        if sentiment_accuracy is not None:
                            sentiment_accuracies.append(sentiment_accuracy)
                        
                        # 상세 분석 데이터
                        validation_results['detailed_analysis'].append({
                            'date': news_item['date'],
                            'symbol': symbol,
                            'news_title': news_item.get('title', ''),
                            'predicted_sentiment': predicted_sentiment,
                            'actual_impact': actual_impact,
                            'correlation': correlation,
                            'sentiment_accuracy': sentiment_accuracy
                        })
                
                # 종목별 결과 집계
                if symbol_correlations:
                    validation_results['symbol_correlations'][symbol] = {
                        'avg_correlation': np.mean(symbol_correlations),
                        'sentiment_accuracy': np.mean(sentiment_accuracies) if sentiment_accuracies else 0.0,
                        'sample_count': len(symbol_correlations)
                    }
            
            # 전체 결과 계산
            all_correlations = []
            all_accuracies = []
            
            for symbol_data in validation_results['symbol_correlations'].values():
                all_correlations.append(symbol_data['avg_correlation'])
                all_accuracies.append(symbol_data['sentiment_accuracy'])
            
            if all_correlations:
                validation_results['overall_correlation'] = np.mean(all_correlations)
            
            if all_accuracies:
                validation_results['sentiment_accuracy'] = np.mean(all_accuracies)
            
            self.logger.info(f"과거 뉴스 영향 검증 완료: 상관관계 {validation_results['overall_correlation']:.3f}")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"과거 뉴스 영향 검증 오류: {e}")
            raise
    
    async def _get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[HistoricalData]:
        """과거 데이터 가져오기"""
        try:
            historical_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # TODO: 데이터베이스에서 해당 날짜 데이터 가져오기 (구현 필요)
                analysis_data = None  # await get_historical_analysis(symbol, current_date)
                
                if analysis_data:
                    data_point = HistoricalData(
                        date=current_date,
                        symbol=symbol,
                        price=analysis_data.get('current_price', 0),
                        volume=analysis_data.get('volume', 0),
                        technical_indicators=analysis_data.get('technical_indicators', {}),
                        sentiment_data=analysis_data.get('sentiment_data', {})
                    )
                    
                    # AI 예측 데이터가 있는 경우
                    if 'ai_prediction' in analysis_data:
                        data_point.ai_prediction = analysis_data['ai_prediction']
                    
                    # TODO: 실제 결과 데이터 (다음날 데이터에서 계산) (구현 필요)
                    next_day_data = None  # await get_historical_analysis(symbol, current_date + timedelta(days=1))
                    
                    if next_day_data:
                        next_price = next_day_data.get('current_price', 0)
                        if data_point.price > 0 and next_price > 0:
                            price_change = (next_price - data_point.price) / data_point.price
                            data_point.actual_outcome = {
                                'price_change': price_change,
                                'direction': 'UP' if price_change > 0 else 'DOWN'
                            }
                    
                    historical_data.append(data_point)
                
                current_date += timedelta(days=1)
            
            return historical_data
            
        except Exception as e:
            self.logger.error(f"과거 데이터 가져오기 오류: {e}")
            return []
    
    async def _calculate_prediction_accuracy(
        self,
        prediction: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> Optional[float]:
        """예측 정확도 계산"""
        try:
            # 방향 예측 정확도
            predicted_direction = prediction.get('direction', 'NEUTRAL')
            actual_direction = actual.get('direction', 'NEUTRAL')
            
            direction_accuracy = 1.0 if predicted_direction == actual_direction else 0.0
            
            # 크기 예측 정확도 (선택적)
            predicted_change = prediction.get('expected_change', 0)
            actual_change = actual.get('price_change', 0)
            
            if predicted_change != 0 and actual_change != 0:
                # 예측 변화율과 실제 변화율 비교
                magnitude_error = abs(predicted_change - actual_change) / abs(actual_change)
                magnitude_accuracy = max(0, 1 - magnitude_error)
                
                # 방향 정확도 70%, 크기 정확도 30% 가중평균
                total_accuracy = direction_accuracy * 0.7 + magnitude_accuracy * 0.3
            else:
                total_accuracy = direction_accuracy
            
            return total_accuracy
            
        except Exception as e:
            self.logger.error(f"예측 정확도 계산 오류: {e}")
            return None
    
    async def _analyze_prediction_types(self, detailed_analysis: List[Dict]) -> Dict[str, Any]:
        """예측 유형별 정확도 분석"""
        try:
            prediction_types = {
                'directional': {'correct': 0, 'total': 0},
                'magnitude': {'correct': 0, 'total': 0},
                'confidence_high': {'correct': 0, 'total': 0},
                'confidence_low': {'correct': 0, 'total': 0}
            }
            
            for analysis in detailed_analysis:
                accuracy = analysis.get('accuracy', 0)
                confidence = analysis.get('confidence', 0)
                
                # 방향 예측
                prediction_types['directional']['total'] += 1
                if accuracy > 0.5:  # 방향이 맞으면
                    prediction_types['directional']['correct'] += 1
                
                # 크기 예측 (정확도 0.7 이상을 정확한 것으로 간주)
                prediction_types['magnitude']['total'] += 1
                if accuracy > 0.7:
                    prediction_types['magnitude']['correct'] += 1
                
                # 신뢰도별 분석
                if confidence > 0.7:
                    prediction_types['confidence_high']['total'] += 1
                    if accuracy > 0.6:
                        prediction_types['confidence_high']['correct'] += 1
                else:
                    prediction_types['confidence_low']['total'] += 1
                    if accuracy > 0.6:
                        prediction_types['confidence_low']['correct'] += 1
            
            # 정확도 계산
            results = {}
            for pred_type, data in prediction_types.items():
                if data['total'] > 0:
                    results[pred_type] = {
                        'accuracy': (data['correct'] / data['total']) * 100,
                        'sample_count': data['total']
                    }
                else:
                    results[pred_type] = {'accuracy': 0.0, 'sample_count': 0}
            
            return results
            
        except Exception as e:
            self.logger.error(f"예측 유형별 분석 오류: {e}")
            return {}
    
    async def _get_market_index_data(
        self,
        index: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[HistoricalData]:
        """시장 지수 데이터 가져오기 (간단화)"""
        try:
            # 실제 구현에서는 시장 지수 데이터를 가져와야 함
            # 여기서는 대표 종목들의 평균으로 근사
            representative_symbols = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
            
            market_data = []
            current_date = start_date
            
            while current_date <= end_date:
                daily_prices = []
                daily_volumes = []
                
                for symbol in representative_symbols:
                    analysis_data = None  # TODO: await get_historical_analysis(symbol, current_date) 구현 필요
                    if analysis_data:
                        daily_prices.append(analysis_data.get('current_price', 0))
                        daily_volumes.append(analysis_data.get('volume', 0))
                
                if daily_prices:
                    avg_price = np.mean(daily_prices)
                    total_volume = sum(daily_volumes)
                    
                    market_data.append(HistoricalData(
                        date=current_date,
                        symbol=index,
                        price=avg_price,
                        volume=total_volume
                    ))
                
                current_date += timedelta(days=1)
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"시장 지수 데이터 가져오기 오류: {e}")
            return []
    
    async def _identify_regime_changes(self, market_data: List[HistoricalData]) -> List[Dict]:
        """체제 변화점 식별 (간단화된 구현)"""
        try:
            if len(market_data) < 30:
                return []
            
            regime_changes = []
            
            # 이동평균을 이용한 간단한 체제 식별
            prices = [d.price for d in market_data]
            short_ma = pd.Series(prices).rolling(window=20).mean()
            long_ma = pd.Series(prices).rolling(window=60).mean()
            
            current_regime = None
            regime_start = market_data[0].date
            
            for i, data_point in enumerate(market_data[60:], 60):  # 60일 이후부터 시작
                
                # 현재 체제 결정
                if short_ma.iloc[i] > long_ma.iloc[i] * 1.02:
                    new_regime = MarketCondition.BULL_MARKET
                elif short_ma.iloc[i] < long_ma.iloc[i] * 0.98:
                    new_regime = MarketCondition.BEAR_MARKET
                else:
                    new_regime = MarketCondition.SIDEWAYS
                
                # 체제 변화 감지
                if current_regime != new_regime and current_regime is not None:
                    regime_changes.append({
                        'start_date': regime_start,
                        'end_date': data_point.date,
                        'regime': current_regime
                    })
                    regime_start = data_point.date
                
                current_regime = new_regime
            
            # 마지막 체제 추가
            if current_regime is not None:
                regime_changes.append({
                    'start_date': regime_start,
                    'end_date': market_data[-1].date,
                    'regime': current_regime
                })
            
            return regime_changes
            
        except Exception as e:
            self.logger.error(f"체제 변화점 식별 오류: {e}")
            return []
    
    async def _analyze_regime_characteristics(self, period_data: List[HistoricalData]) -> Dict[str, float]:
        """체제별 특성 분석"""
        try:
            if not period_data:
                return {}
            
            prices = [d.price for d in period_data]
            volumes = [d.volume for d in period_data]
            
            # 기본 통계
            characteristics = {
                'avg_price': np.mean(prices),
                'price_volatility': np.std(prices) / np.mean(prices) * 100,
                'avg_volume': np.mean(volumes),
                'volume_volatility': np.std(volumes) / np.mean(volumes) * 100,
                'trend_strength': self._calculate_trend_strength(prices),
                'momentum': self._calculate_momentum(prices)
            }
            
            return characteristics
            
        except Exception as e:
            self.logger.error(f"체제 특성 분석 오류: {e}")
            return {}
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """트렌드 강도 계산"""
        try:
            if len(prices) < 2:
                return 0.0
            
            # 선형 회귀의 R-squared 값으로 트렌드 강도 측정
            x = np.arange(len(prices))
            y = np.array(prices)
            
            correlation = np.corrcoef(x, y)[0, 1]
            r_squared = correlation ** 2
            
            return r_squared * 100
            
        except Exception as e:
            return 0.0
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """모멘텀 계산"""
        try:
            if len(prices) < 20:
                return 0.0
            
            # 20일 모멘텀 (현재가 / 20일전 가격 - 1)
            current_price = prices[-1]
            past_price = prices[-20]
            
            if past_price > 0:
                momentum = (current_price / past_price - 1) * 100
                return momentum
            
            return 0.0
            
        except Exception as e:
            return 0.0
    
    async def _calculate_period_return(self, period_data: List[HistoricalData]) -> float:
        """기간 수익률 계산"""
        try:
            if len(period_data) < 2:
                return 0.0
            
            start_price = period_data[0].price
            end_price = period_data[-1].price
            
            if start_price > 0:
                return (end_price / start_price - 1) * 100
            
            return 0.0
            
        except Exception as e:
            return 0.0
    
    async def _calculate_period_volatility(self, period_data: List[HistoricalData]) -> float:
        """기간 변동성 계산"""
        try:
            if len(period_data) < 2:
                return 0.0
            
            returns = []
            for i in range(1, len(period_data)):
                prev_price = period_data[i-1].price
                curr_price = period_data[i].price
                
                if prev_price > 0:
                    daily_return = (curr_price / prev_price - 1)
                    returns.append(daily_return)
            
            if returns:
                return np.std(returns) * np.sqrt(252) * 100  # 연변동성
            
            return 0.0
            
        except Exception as e:
            return 0.0
    
    async def _calculate_period_drawdown(self, period_data: List[HistoricalData]) -> float:
        """기간 최대 낙폭 계산"""
        try:
            if len(period_data) < 2:
                return 0.0
            
            prices = [d.price for d in period_data]
            max_price = prices[0]
            max_drawdown = 0.0
            
            for price in prices[1:]:
                if price > max_price:
                    max_price = price
                else:
                    drawdown = (max_price - price) / max_price
                    max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown * 100
            
        except Exception as e:
            return 0.0
    
    async def _analyze_ai_performance_in_regime(
        self,
        start_date: datetime,
        end_date: datetime,
        regime: MarketCondition
    ) -> Dict[str, Any]:
        """특정 체제에서의 AI 성과 분석"""
        try:
            # 해당 기간의 AI 예측 데이터 분석
            # 실제 구현에서는 데이터베이스에서 AI 예측 결과를 가져와야 함
            
            return {
                'accuracy': 65.0,  # 임시값
                'prediction_count': 100,  # 임시값
                'regime_specific_insights': f"{regime.value} 시장에서의 AI 성과"
            }
            
        except Exception as e:
            self.logger.error(f"체제별 AI 성과 분석 오류: {e}")
            return {'accuracy': 0.0, 'prediction_count': 0}
    
    async def _identify_key_events(self, start_date: datetime, end_date: datetime) -> List[str]:
        """주요 이벤트 식별"""
        try:
            # 해당 기간의 주요 뉴스나 이벤트 식별
            # 실제 구현에서는 뉴스 데이터베이스에서 중요한 뉴스를 필터링
            
            key_events = []
            
            # 예시: 특정 날짜의 주요 이벤트들
            if start_date <= datetime(2024, 3, 1) <= end_date:
                key_events.append("금리 인상 발표")
            
            if start_date <= datetime(2024, 6, 1) <= end_date:
                key_events.append("반도체 업황 개선")
            
            return key_events
            
        except Exception as e:
            self.logger.error(f"주요 이벤트 식별 오류: {e}")
            return []
    
    async def _analyze_news_price_impact(
        self,
        symbol: str,
        news_date: datetime,
        news_item: Dict
    ) -> Optional[Dict[str, Any]]:
        """뉴스의 주가 영향 분석"""
        try:
            # 뉴스 발표일 전후 주가 데이터 가져오기
            before_date = news_date - timedelta(days=1)
            after_date = news_date + timedelta(days=1)
            
            # TODO: 뉴스 전후 데이터 가져오기 (구현 필요)
            before_data = None  # await get_historical_analysis(symbol, before_date)
            after_data = None   # await get_historical_analysis(symbol, after_date)
            
            if not before_data or not after_data:
                return None
            
            before_price = before_data.get('current_price', 0)
            after_price = after_data.get('current_price', 0)
            
            if before_price > 0 and after_price > 0:
                price_change = after_price - before_price
                price_change_pct = (price_change / before_price) * 100
                
                return {
                    'price_change': price_change,
                    'price_change_pct': price_change_pct,
                    'before_price': before_price,
                    'after_price': after_price
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"뉴스 주가 영향 분석 오류: {e}")
            return None
    
    def _calculate_sentiment_correlation(self, predicted_sentiment: float, actual_impact: float) -> Optional[float]:
        """감정 점수와 실제 영향의 상관관계 계산"""
        try:
            # 감정 점수를 -1 ~ 1 범위로 정규화
            normalized_sentiment = (predicted_sentiment - 50) / 50
            
            # 실제 영향을 -1 ~ 1 범위로 정규화 (±10% 기준)
            normalized_impact = max(-1, min(1, actual_impact / 10))
            
            # 간단한 상관관계 (부호가 같으면 양의 상관관계)
            if (normalized_sentiment > 0 and normalized_impact > 0) or (normalized_sentiment < 0 and normalized_impact < 0):
                correlation = abs(normalized_sentiment * normalized_impact)
            else:
                correlation = -abs(normalized_sentiment * normalized_impact)
            
            return correlation
            
        except Exception as e:
            return None
    
    def _validate_sentiment_prediction(self, predicted_sentiment: float, actual_impact: float) -> Optional[float]:
        """감정 예측 정확도 검증"""
        try:
            # 감정 점수를 방향으로 변환
            if predicted_sentiment > 55:
                predicted_direction = 'POSITIVE'
            elif predicted_sentiment < 45:
                predicted_direction = 'NEGATIVE'
            else:
                predicted_direction = 'NEUTRAL'
            
            # 실제 영향을 방향으로 변환
            if actual_impact > 1:
                actual_direction = 'POSITIVE'
            elif actual_impact < -1:
                actual_direction = 'NEGATIVE'
            else:
                actual_direction = 'NEUTRAL'
            
            # 방향이 일치하면 정확도 100%, 아니면 0%
            return 100.0 if predicted_direction == actual_direction else 0.0
            
        except Exception as e:
            return None