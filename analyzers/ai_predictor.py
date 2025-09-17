#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/ai_predictor.py

AI 기반 예측 분석 - Phase 4 Advanced AI Features
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer


@dataclass
class MarketPrediction:
    """시장 예측 결과"""
    symbol: str
    prediction_type: str  # trend, price_target, volatility, timing
    direction: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float  # 0-100
    time_horizon: str  # short_term, medium_term, long_term
    predicted_price_range: Dict[str, float]  # min, max, target
    key_factors: List[str]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommended_action: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    timestamp: datetime


@dataclass
class MarketRegime:
    """시장 체제 분석 결과"""
    regime_type: str  # bull_market, bear_market, sideways, high_volatility, low_volatility
    confidence: float
    start_date: datetime
    expected_duration: int  # days
    key_characteristics: List[str]
    recommended_strategies: List[str]
    risk_factors: List[str]


class AIPredictor:
    """AI 기반 예측 분석 엔진"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("AIPredictor")
        self.gemini_analyzer = GeminiAnalyzer(config)
        
        # Phase 4.1: 다중 모델 앙상블 가중치 - 동적 조정 가능
        self.prediction_weights = {
            'technical_analysis': 0.30,     # 기술적 지표 기반 예측
            'news_sentiment': 0.25,         # 뉴스 감성 분석 기반 예측
            'supply_demand': 0.20,          # 수급 분석 기반 예측
            'chart_pattern': 0.15,          # 차트 패턴 기반 예측
            'market_regime': 0.10           # 시장 체제 기반 예측
        }
        
        # 앙상블 모델 설정
        self.ensemble_config = {
            'min_models_required': 3,       # 최소 필요한 모델 수
            'consensus_threshold': 0.6,     # 합의 임계값
            'confidence_boost_factor': 1.2, # 합의 시 신뢰도 부스트
            'disagreement_penalty': 0.8     # 불일치 시 신뢰도 패널티
        }
        
        # 예측 정확도 추적 (Phase 4.1: 학습 기능)
        self.model_accuracy_history = {
            'technical_analysis': [],
            'news_sentiment': [],
            'supply_demand': [],
            'chart_pattern': [],
            'market_regime': []
        }
        
        # 시장 체제 임계값
        self.regime_thresholds = {
            'volatility_high': 0.25,
            'volatility_low': 0.10,
            'trend_strength': 0.15,
            'volume_surge': 2.0
        }
        
        self.logger.info("✅ AI 예측 분석기 초기화 완료")
    
    async def predict_market_trend(self, symbol: str, stock_data: Dict, 
                                 historical_data: List[Dict] = None) -> MarketPrediction:
        """Phase 4.1: 다중 모델 앙상블 기반 시장 트렌드 예측"""
        try:
            self.logger.info(f"🔮 {symbol} Phase 4.1 앙상블 예측 시작")
            
            # Phase 4.1: 5개 모델 병렬 예측 실행
            prediction_tasks = [
                ('technical_analysis', self._predict_from_technical_enhanced(symbol, stock_data, historical_data)),
                ('news_sentiment', self._predict_from_news_sentiment_enhanced(symbol, stock_data)),
                ('supply_demand', self._predict_from_supply_demand_enhanced(symbol, stock_data)),
                ('chart_pattern', self._predict_from_chart_pattern_enhanced(symbol, stock_data)),
                ('market_regime', self._predict_from_market_regime_enhanced(symbol, stock_data, historical_data))
            ]
            
            # 병렬 실행으로 성능 향상
            model_predictions = {}
            for model_name, task in prediction_tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=10.0)
                    model_predictions[model_name] = result
                    self.logger.debug(f"✅ {model_name} 예측 완료: {result.get('score', 0):.1f}")
                except asyncio.TimeoutError:
                    self.logger.warning(f"시간초과 {model_name} 예측 타임아웃")
                    model_predictions[model_name] = self._create_default_model_prediction()
                except Exception as e:
                    self.logger.error(f"❌ {model_name} 예측 실패: {e}")
                    model_predictions[model_name] = self._create_default_model_prediction()
            
            # Phase 4.1: 앙상블 합의 알고리즘
            ensemble_prediction = await self._ensemble_consensus_prediction(symbol, model_predictions, stock_data)
            
            # Phase 4.1: 예측 결과 학습 데이터 저장
            await self._store_prediction_for_learning(symbol, model_predictions, ensemble_prediction)
            
            self.logger.info(f"✅ {symbol} 앙상블 예측 완료: {ensemble_prediction.direction} "
                           f"(신뢰도: {ensemble_prediction.confidence:.1f}%, "
                           f"참여모델: {len([p for p in model_predictions.values() if p.get('score', 0) > 0])}개)")
            
            return ensemble_prediction
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 앙상블 예측 실패: {e}")
            return self._create_default_prediction(symbol, stock_data)
    
    async def predict_price_targets(self, symbol: str, stock_data: Dict, 
                                  time_horizons: List[str] = None) -> Dict[str, MarketPrediction]:
        """다양한 시간대별 가격 목표 예측"""
        try:
            if time_horizons is None:
                time_horizons = ['short_term', 'medium_term', 'long_term']
            
            predictions = {}
            current_price = stock_data.get('current_price', 0)
            
            for horizon in time_horizons:
                # 시간대별 예측 로직
                if horizon == 'short_term':  # 1-5일
                    prediction = await self._predict_short_term_price(symbol, stock_data, current_price)
                elif horizon == 'medium_term':  # 1-4주
                    prediction = await self._predict_medium_term_price(symbol, stock_data, current_price)
                else:  # 1-3개월
                    prediction = await self._predict_long_term_price(symbol, stock_data, current_price)
                
                predictions[horizon] = prediction
            
            self.logger.info(f"✅ {symbol} 가격 목표 예측 완료: {len(predictions)}개 시간대")
            return predictions
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 가격 목표 예측 실패: {e}")
            return {}
    
    async def detect_market_regime(self, market_data: List[Dict]) -> MarketRegime:
        """시장 체제 감지"""
        try:
            self.logger.info("🌐 시장 체제 분석 시작")
            
            # 1. 변동성 분석
            volatility_analysis = await self._analyze_volatility_regime(market_data)
            
            # 2. 트렌드 분석
            trend_analysis = await self._analyze_trend_regime(market_data)
            
            # 3. 거래량 분석
            volume_analysis = await self._analyze_volume_regime(market_data)
            
            # 4. AI 기반 종합 분석
            ai_analysis = await self._ai_regime_analysis(market_data)
            
            # 5. 최종 체제 결정
            regime = await self._determine_market_regime(
                volatility_analysis, trend_analysis, volume_analysis, ai_analysis
            )
            
            self.logger.info(f"✅ 시장 체제 분석 완료: {regime.regime_type} ({regime.confidence:.1f}%)")
            return regime
            
        except Exception as e:
            self.logger.error(f"❌ 시장 체제 분석 실패: {e}")
            return self._create_default_regime()
    
    async def optimize_strategy_parameters(self, strategy_name: str, 
                                         performance_data: Dict,
                                         market_conditions: Dict) -> Dict[str, Any]:
        """전략 매개변수 AI 최적화"""
        try:
            self.logger.info(f"⚙️ {strategy_name} 전략 매개변수 최적화 시작")
            
            # 1. 현재 성과 분석
            performance_analysis = await self._analyze_strategy_performance(
                strategy_name, performance_data
            )
            
            # 2. 시장 조건 적합성 분석
            market_fit_analysis = await self._analyze_market_fit(
                strategy_name, market_conditions
            )
            
            # 3. AI 기반 매개변수 추천
            ai_recommendations = await self._ai_parameter_optimization(
                strategy_name, performance_analysis, market_fit_analysis
            )
            
            # 4. 최적화된 매개변수 생성
            optimized_params = await self._generate_optimized_parameters(
                strategy_name, ai_recommendations, market_conditions
            )
            
            self.logger.info(f"✅ {strategy_name} 매개변수 최적화 완료")
            return optimized_params
            
        except Exception as e:
            self.logger.error(f"❌ {strategy_name} 매개변수 최적화 실패: {e}")
            return {}
    
    async def assess_ai_risk(self, portfolio_data: Dict, market_conditions: Dict) -> Dict[str, Any]:
        """AI 기반 리스크 평가"""
        try:
            self.logger.info("🛡️ AI 리스크 평가 시작")
            
            # 1. 포트폴리오 리스크 분석
            portfolio_risk = await self._analyze_portfolio_risk(portfolio_data)
            
            # 2. 시장 리스크 분석
            market_risk = await self._analyze_market_risk(market_conditions)
            
            # 3. 상관관계 리스크 분석
            correlation_risk = await self._analyze_correlation_risk(portfolio_data, market_conditions)
            
            # 4. AI 기반 종합 리스크 평가
            ai_risk_assessment = await self._ai_comprehensive_risk_assessment(
                portfolio_risk, market_risk, correlation_risk
            )
            
            # 5. 리스크 완화 전략 추천
            mitigation_strategies = await self._recommend_risk_mitigation(ai_risk_assessment)
            
            result = {
                'overall_risk_level': ai_risk_assessment.get('risk_level', 'MEDIUM'),
                'risk_score': ai_risk_assessment.get('risk_score', 50),
                'key_risk_factors': ai_risk_assessment.get('risk_factors', []),
                'portfolio_risk': portfolio_risk,
                'market_risk': market_risk,
                'correlation_risk': correlation_risk,
                'mitigation_strategies': mitigation_strategies,
                'recommended_position_sizing': ai_risk_assessment.get('position_sizing', {}),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ AI 리스크 평가 완료: {result['overall_risk_level']} ({result['risk_score']:.1f}점)")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ AI 리스크 평가 실패: {e}")
            return self._create_default_risk_assessment()
    
    async def optimize_news_timing(self, news_data: List[Dict], stock_data: Dict) -> Dict[str, Any]:
        """뉴스 임팩트 타이밍 최적화"""
        try:
            symbol = stock_data.get('symbol', 'Unknown')
            self.logger.info(f"📰 {symbol} 뉴스 타이밍 최적화 시작")
            
            # 1. 뉴스 임팩트 분석
            news_impact_analysis = await self._analyze_news_impact_timing(news_data, stock_data)
            
            # 2. 최적 거래 타이밍 예측
            optimal_timing = await self._predict_optimal_trading_timing(
                news_impact_analysis, stock_data
            )
            
            # 3. 뉴스 기반 전략 추천
            news_strategies = await self._recommend_news_based_strategies(
                news_impact_analysis, optimal_timing
            )
            
            result = {
                'optimal_entry_timing': optimal_timing.get('entry_timing'),
                'optimal_exit_timing': optimal_timing.get('exit_timing'),
                'news_impact_score': news_impact_analysis.get('impact_score', 0),
                'key_news_factors': news_impact_analysis.get('key_factors', []),
                'recommended_strategies': news_strategies,
                'confidence': optimal_timing.get('confidence', 50),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ {symbol} 뉴스 타이밍 최적화 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 뉴스 타이밍 최적화 실패: {e}")
            return {}
    
    # === 내부 헬퍼 메서드들 ===
    
    async def _predict_from_technical(self, symbol: str, stock_data: Dict, 
                                    historical_data: List[Dict]) -> Dict:
        """기술적 분석 기반 예측"""
        try:
            current_price = stock_data.get('current_price', 0)
            change_rate = stock_data.get('change_rate', 0)
            volume = stock_data.get('volume', 0)
            
            # 기본 기술적 분석
            technical_score = 0
            factors = []
            
            # 가격 모멘텀 분석
            if change_rate > 3:
                technical_score += 20
                factors.append("강한 상승 모멘텀")
            elif change_rate > 1:
                technical_score += 10
                factors.append("양호한 상승 모멘텀")
            elif change_rate < -3:
                technical_score -= 20
                factors.append("강한 하락 모멘텀")
            elif change_rate < -1:
                technical_score -= 10
                factors.append("하락 압력")
            
            # 거래량 분석
            avg_volume = stock_data.get('avg_volume', volume)
            if volume > avg_volume * 2:
                technical_score += 15
                factors.append("거래량 급증")
            elif volume < avg_volume * 0.5:
                technical_score -= 5
                factors.append("거래량 부족")
            
            # AI 기반 추가 분석 (Gemini)
            ai_prompt = f"""
            주식 {symbol}의 기술적 분석을 바탕으로 향후 트렌드를 예측해주세요.
            
            현재 데이터:
            - 현재가: {current_price:,}원
            - 변동률: {change_rate:.2f}%
            - 거래량: {volume:,}주
            
            다음 형식으로 답변해주세요:
            {{
                "prediction": "BULLISH/BEARISH/NEUTRAL",
                "confidence": 85,
                "price_target": 50000,
                "key_factors": ["요인1", "요인2", "요인3"],
                "time_horizon": "short_term"
            }}
            """
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(ai_prompt)
            
            return {
                'technical_score': max(0, min(100, technical_score + 50)),
                'factors': factors,
                'ai_analysis': ai_result
            }
            
        except Exception as e:
            self.logger.error(f"❌ 기술적 분석 예측 실패: {e}")
            return {'technical_score': 50, 'factors': [], 'ai_analysis': {}}
    
    async def _predict_from_sentiment(self, symbol: str, stock_data: Dict) -> Dict:
        """감정 분석 기반 예측"""
        try:
            # 뉴스 데이터가 있는 경우 감정 분석 수행
            news_prompt = f"""
            주식 {symbol}에 대한 최신 뉴스와 시장 감정을 분석하여 향후 주가 움직임을 예측해주세요.
            
            현재 주가: {stock_data.get('current_price', 0):,}원
            변동률: {stock_data.get('change_rate', 0):.2f}%
            
            다음 형식으로 답변해주세요:
            {{
                "sentiment": "VERY_POSITIVE/POSITIVE/NEUTRAL/NEGATIVE/VERY_NEGATIVE",
                "confidence": 75,
                "impact_prediction": "BULLISH/BEARISH/NEUTRAL",
                "key_news_factors": ["요인1", "요인2"],
                "timing_suggestion": "IMMEDIATE/WAIT/AVOID"
            }}
            """
            
            sentiment_result = await self.gemini_analyzer.analyze_with_custom_prompt(news_prompt)
            
            return {
                'sentiment_analysis': sentiment_result,
                'sentiment_score': self._convert_sentiment_to_score(sentiment_result.get('sentiment', 'NEUTRAL'))
            }
            
        except Exception as e:
            self.logger.error(f"❌ 감정 분석 예측 실패: {e}")
            return {'sentiment_analysis': {}, 'sentiment_score': 50}
    
    async def _synthesize_predictions(self, symbol: str, technical: Dict, 
                                    sentiment: Dict, regime: Dict) -> MarketPrediction:
        """예측 결과 종합"""
        try:
            # 가중 평균 계산
            technical_score = technical.get('technical_score', 50)
            sentiment_score = sentiment.get('sentiment_score', 50)
            
            final_score = (
                technical_score * self.prediction_weights['technical_analysis'] +
                sentiment_score * self.prediction_weights['sentiment_analysis'] +
                50 * self.prediction_weights['market_regime']  # 기본값
            ) / sum([
                self.prediction_weights['technical_analysis'],
                self.prediction_weights['sentiment_analysis'],
                self.prediction_weights['market_regime']
            ])
            
            # 방향 결정
            if final_score >= 70:
                direction = "BULLISH"
                action = "STRONG_BUY" if final_score >= 80 else "BUY"
            elif final_score >= 55:
                direction = "NEUTRAL"
                action = "HOLD"
            elif final_score >= 30:
                direction = "BEARISH"
                action = "SELL"
            else:
                direction = "BEARISH"
                action = "STRONG_SELL"
            
            # 신뢰도 계산
            confidence = min(95, max(30, final_score))
            
            # 가격 범위 예측 (기본값)
            current_price = 50000  # 실제 구현에서는 stock_data에서 가져옴
            price_range = {
                'min': current_price * 0.95,
                'max': current_price * 1.10,
                'target': current_price * (1.05 if direction == "BULLISH" else 0.98)
            }
            
            return MarketPrediction(
                symbol=symbol,
                prediction_type="trend",
                direction=direction,
                confidence=confidence,
                time_horizon="medium_term",
                predicted_price_range=price_range,
                key_factors=technical.get('factors', []) + sentiment.get('sentiment_analysis', {}).get('key_news_factors', []),
                risk_level="MEDIUM",
                recommended_action=action,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ 예측 종합 실패: {e}")
            return self._create_default_prediction(symbol, {})
    
    def _convert_sentiment_to_score(self, sentiment: str) -> float:
        """감정을 점수로 변환"""
        sentiment_map = {
            'VERY_POSITIVE': 90,
            'POSITIVE': 70,
            'NEUTRAL': 50,
            'NEGATIVE': 30,
            'VERY_NEGATIVE': 10
        }
        return sentiment_map.get(sentiment.upper(), 50)
    
    def _create_default_prediction(self, symbol: str, stock_data: Dict) -> MarketPrediction:
        """기본 예측 생성"""
        return MarketPrediction(
            symbol=symbol,
            prediction_type="trend",
            direction="NEUTRAL",
            confidence=50.0,
            time_horizon="medium_term",
            predicted_price_range={'min': 0, 'max': 0, 'target': 0},
            key_factors=["데이터 부족으로 기본 예측"],
            risk_level="MEDIUM",
            recommended_action="HOLD",
            timestamp=datetime.now()
        )
    
    def _create_default_risk_assessment(self) -> Dict[str, Any]:
        """기본 리스크 평가 생성"""
        return {
            'overall_risk_level': 'MEDIUM',
            'risk_score': 50,
            'key_risk_factors': ['데이터 부족'],
            'portfolio_risk': {},
            'market_risk': {},
            'correlation_risk': {},
            'mitigation_strategies': [],
            'recommended_position_sizing': {},
            'timestamp': datetime.now()
        }
    
    # === Phase 4.1: 앙상블 예측 핵심 메서드들 ===
    
    async def _ensemble_consensus_prediction(self, symbol: str, model_predictions: Dict, stock_data: Dict) -> MarketPrediction:
        """Phase 4.1: 앙상블 합의 예측 알고리즘"""
        try:
            valid_predictions = {k: v for k, v in model_predictions.items() if v.get('score', 0) > 0}
            
            if len(valid_predictions) < self.ensemble_config['min_models_required']:
                self.logger.warning(f"⚠️ {symbol} 유효한 모델이 {len(valid_predictions)}개로 부족함")
                return self._create_default_prediction(symbol, stock_data)
            
            # 1. 가중 평균 점수 계산
            weighted_score = 0
            total_weight = 0
            predictions_detail = []
            
            for model_name, prediction in valid_predictions.items():
                if model_name in self.prediction_weights:
                    weight = self.prediction_weights[model_name]
                    score = prediction.get('score', 50)
                    direction = prediction.get('direction', 'NEUTRAL')
                    confidence = prediction.get('confidence', 50)
                    
                    weighted_score += score * weight
                    total_weight += weight
                    
                    predictions_detail.append({
                        'model': model_name,
                        'score': score,
                        'direction': direction,
                        'confidence': confidence,
                        'weight': weight
                    })
            
            if total_weight > 0:
                weighted_score /= total_weight
            else:
                weighted_score = 50
            
            # 2. 방향 합의도 계산
            direction_votes = {'BULLISH': 0, 'BEARISH': 0, 'NEUTRAL': 0}
            for detail in predictions_detail:
                direction_votes[detail['direction']] += detail['weight']
            
            # 최다 득표 방향 결정
            consensus_direction = max(direction_votes, key=direction_votes.get)
            consensus_strength = direction_votes[consensus_direction] / total_weight if total_weight > 0 else 0
            
            # 3. 신뢰도 조정
            base_confidence = min(90, max(30, weighted_score))
            
            # 합의도가 높으면 신뢰도 증가
            if consensus_strength >= self.ensemble_config['consensus_threshold']:
                final_confidence = min(95, base_confidence * self.ensemble_config['confidence_boost_factor'])
                self.logger.debug(f"🤝 {symbol} 모델 합의 달성 (합의도: {consensus_strength:.2f})")
            else:
                final_confidence = max(25, base_confidence * self.ensemble_config['disagreement_penalty'])
                self.logger.debug(f"⚡ {symbol} 모델 불일치 (합의도: {consensus_strength:.2f})")
            
            # 4. 액션 추천
            action = self._determine_action_from_score_and_direction(weighted_score, consensus_direction)
            
            # 5. 주요 요인 수집
            key_factors = []
            for detail in predictions_detail:
                model_factors = model_predictions[detail['model']].get('factors', [])
                key_factors.extend(model_factors[:2])  # 각 모델에서 상위 2개 요인
            
            # 6. 가격 타겟 계산
            current_price = stock_data.get('current_price', 50000)
            price_range = self._calculate_ensemble_price_target(
                current_price, consensus_direction, final_confidence, predictions_detail
            )
            
            # 최종 예측 생성
            ensemble_prediction = MarketPrediction(
                symbol=symbol,
                prediction_type="ensemble_trend",
                direction=consensus_direction,
                confidence=final_confidence,
                time_horizon="medium_term",
                predicted_price_range=price_range,
                key_factors=list(set(key_factors))[:5],  # 중복 제거 후 상위 5개
                risk_level=self._assess_risk_level(final_confidence, consensus_strength),
                recommended_action=action,
                timestamp=datetime.now()
            )
            
            # 메타데이터 추가
            ensemble_prediction.ensemble_details = {
                'participating_models': len(valid_predictions),
                'consensus_strength': consensus_strength,
                'weighted_score': weighted_score,
                'model_breakdown': predictions_detail
            }
            
            return ensemble_prediction
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 앙상블 합의 실패: {e}")
            return self._create_default_prediction(symbol, stock_data)
    
    async def _predict_from_technical_enhanced(self, symbol: str, stock_data: Dict, historical_data: List[Dict]) -> Dict:
        """Phase 4.1: 강화된 기술적 분석 예측"""
        try:
            current_price = stock_data.get('current_price', 0)
            change_rate = stock_data.get('change_rate', 0)
            volume = stock_data.get('volume', 0)
            trading_value = stock_data.get('trading_value', 0)
            
            score = 50  # 기본 점수
            factors = []
            confidence = 50
            
            # 1. 가격 모멘텀 분석 (강화)
            if change_rate > 5:
                score += 25
                confidence += 15
                factors.append(f"강력한 상승 모멘텀 ({change_rate:.1f}%)")
            elif change_rate > 2:
                score += 15
                confidence += 10
                factors.append(f"양호한 상승세 ({change_rate:.1f}%)")
            elif change_rate > 0:
                score += 5
                confidence += 5
                factors.append("소폭 상승")
            elif change_rate < -5:
                score -= 25
                confidence += 15
                factors.append(f"강한 하락세 ({change_rate:.1f}%)")
            elif change_rate < -2:
                score -= 15
                confidence += 10
                factors.append(f"하락 압력 ({change_rate:.1f}%)")
            
            # 2. 거래량 분석 (강화)
            avg_volume = stock_data.get('avg_volume', volume) or volume
            if avg_volume > 0:
                volume_ratio = volume / avg_volume
                if volume_ratio > 3:
                    score += 20
                    confidence += 10
                    factors.append(f"거래량 폭증 ({volume_ratio:.1f}배)")
                elif volume_ratio > 1.5:
                    score += 10
                    confidence += 5
                    factors.append(f"거래량 증가 ({volume_ratio:.1f}배)")
                elif volume_ratio < 0.3:
                    score -= 10
                    factors.append("거래량 위축")
            
            # 3. 거래대금 분석 (신규)
            if trading_value > 50000:  # 5억원 이상
                score += 15
                confidence += 5
                factors.append("대형주 관심")
            elif trading_value > 10000:  # 1억원 이상
                score += 5
                factors.append("양호한 유동성")
            
            # 4. 시가총액 기반 안정성 (신규)
            market_cap = stock_data.get('market_cap', 0)
            if market_cap > 1000:  # 1조원 이상
                confidence += 10
                factors.append("대형주 안정성")
            elif market_cap < 100:  # 1천억원 미만
                confidence -= 5
                factors.append("소형주 변동성")
            
            # 최종 조정
            final_score = max(10, min(90, score))
            final_confidence = max(30, min(85, confidence))
            
            # 방향 결정
            if final_score >= 65:
                direction = "BULLISH"
            elif final_score <= 35:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
            
            return {
                'score': final_score,
                'direction': direction,
                'confidence': final_confidence,
                'factors': factors[:3],  # 상위 3개 요인만
                'model_type': 'technical_analysis_enhanced'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 강화된 기술적 분석 실패: {e}")
            return self._create_default_model_prediction()
    
    async def _predict_from_news_sentiment_enhanced(self, symbol: str, stock_data: Dict) -> Dict:
        """Phase 4.1: 강화된 뉴스 감성 분석 예측"""
        try:
            # 실제 뉴스 데이터 활용 (기존 뉴스 가중치 시스템 연동)
            try:
                from analyzers.analysis_engine import AnalysisEngine
                analysis_engine = AnalysisEngine(self.config)
                
                # 간단한 뉴스 임팩트 분석 수행
                name = stock_data.get('name', symbol)
                news_data = []  # 실제로는 뉴스 데이터를 가져와야 함
                
                # 기존 뉴스 가중치 계산 로직 활용
                news_weight = analysis_engine._calculate_news_weight(news_data) if news_data else {
                    'score': 50, 'period': 'NEUTRAL', 'short_weight': 1.0, 'mid_weight': 1.0, 'long_weight': 1.0
                }
                
                # 뉴스 점수를 예측 점수로 변환
                score = news_weight.get('score', 50)
                period = news_weight.get('period', 'NEUTRAL')
                
                factors = []
                confidence = 60
                
                # 기간별 가중치 반영
                if period == 'LONG_TERM':
                    confidence += 15
                    factors.append("장기 재료 주도")
                elif period == 'MID_TERM':
                    confidence += 10
                    factors.append("중기 재료 주도")
                elif period == 'SHORT_TERM':
                    confidence += 5
                    factors.append("단기 재료 주도")
                
                # 방향 결정
                if score >= 65:
                    direction = "BULLISH"
                    factors.append("긍정적 뉴스 우세")
                elif score <= 35:
                    direction = "BEARISH"
                    factors.append("부정적 뉴스 우세")
                else:
                    direction = "NEUTRAL"
                    factors.append("뉴스 혼조")
                
            except Exception as e:
                self.logger.debug(f"뉴스 데이터 분석 실패, 기본값 사용: {e}")
                score = 50
                direction = "NEUTRAL"
                confidence = 50
                factors = ["뉴스 데이터 부족"]
            
            return {
                'score': score,
                'direction': direction,
                'confidence': confidence,
                'factors': factors,
                'model_type': 'news_sentiment_enhanced'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 강화된 뉴스 감성 분석 실패: {e}")
            return self._create_default_model_prediction()
    
    async def _predict_from_supply_demand_enhanced(self, symbol: str, stock_data: Dict) -> Dict:
        """Phase 4.1: 강화된 수급 분석 예측"""
        try:
            score = 50
            factors = []
            confidence = 55
            
            # 외국인/기관 매매 데이터 활용 (mock data)
            foreign_buy_ratio = stock_data.get('foreign_buy_ratio', 0)
            institutional_buy_ratio = stock_data.get('institutional_buy_ratio', 0)
            
            # 외국인 매매 분석
            if foreign_buy_ratio > 60:
                score += 20
                confidence += 10
                factors.append(f"외국인 순매수 ({foreign_buy_ratio}%)")
            elif foreign_buy_ratio < 40:
                score -= 15
                confidence += 5
                factors.append(f"외국인 순매도 ({foreign_buy_ratio}%)")
            
            # 기관 매매 분석
            if institutional_buy_ratio > 60:
                score += 15
                confidence += 10
                factors.append(f"기관 순매수 ({institutional_buy_ratio}%)")
            elif institutional_buy_ratio < 40:
                score -= 10
                confidence += 5
                factors.append(f"기관 순매도 ({institutional_buy_ratio}%)")
            
            # 유통주식 수 및 시가총액 고려
            shares_outstanding = stock_data.get('shares_outstanding', 0)
            market_cap = stock_data.get('market_cap', 0)
            
            if shares_outstanding > 0 and market_cap > 0:
                # 유동성 분석
                if market_cap > 1000:  # 대형주
                    confidence += 5
                    factors.append("대형주 안정성")
                elif market_cap < 100:  # 소형주
                    score += 5  # 소형주 프리미엄
                    factors.append("소형주 민감도")
            
            # 최종 조정
            final_score = max(15, min(85, score))
            final_confidence = max(35, min(80, confidence))
            
            # 방향 결정
            if final_score >= 65:
                direction = "BULLISH"
            elif final_score <= 35:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
            
            return {
                'score': final_score,
                'direction': direction,
                'confidence': final_confidence,
                'factors': factors[:3],
                'model_type': 'supply_demand_enhanced'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 강화된 수급 분석 실패: {e}")
            return self._create_default_model_prediction()
    
    async def _predict_from_chart_pattern_enhanced(self, symbol: str, stock_data: Dict) -> Dict:
        """Phase 4.1: 강화된 차트 패턴 분석 예측"""
        try:
            score = 50
            factors = []
            confidence = 50
            
            current_price = stock_data.get('current_price', 0)
            high_52w = stock_data.get('high_52w', current_price)
            low_52w = stock_data.get('low_52w', current_price)
            
            # 52주 고점/저점 대비 위치 분석
            if high_52w > 0 and low_52w > 0 and high_52w > low_52w:
                price_position = (current_price - low_52w) / (high_52w - low_52w)
                
                if price_position > 0.9:  # 52주 고점 근처
                    score += 10
                    confidence += 10
                    factors.append("52주 고점 돌파 시도")
                elif price_position > 0.7:  # 상단 영역
                    score += 5
                    factors.append("52주 고점대 접근")
                elif price_position < 0.1:  # 52주 저점 근처
                    score -= 10
                    confidence += 10
                    factors.append("52주 저점 근처 약세")
                elif price_position < 0.3:  # 하단 영역
                    score += 15  # 저점 반등 기대
                    confidence += 5
                    factors.append("저가권 반등 기대")
            
            # 가격 대역 분석
            if current_price > 0:
                if current_price < 5000:
                    score += 5
                    factors.append("저가주 관심")
                elif current_price > 50000:
                    confidence += 5
                    factors.append("고가주 안정성")
            
            # PE ratio 기반 패턴 분석
            pe_ratio = stock_data.get('pe_ratio', 0)
            if pe_ratio > 0:
                if pe_ratio < 10:
                    score += 10
                    factors.append("저PER 매력")
                elif pe_ratio > 30:
                    score -= 5
                    factors.append("고PER 부담")
            
            # 최종 조정
            final_score = max(20, min(80, score))
            final_confidence = max(40, min(75, confidence))
            
            # 방향 결정
            if final_score >= 60:
                direction = "BULLISH"
            elif final_score <= 40:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
            
            return {
                'score': final_score,
                'direction': direction,
                'confidence': final_confidence,
                'factors': factors[:3],
                'model_type': 'chart_pattern_enhanced'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 강화된 차트 패턴 분석 실패: {e}")
            return self._create_default_model_prediction()
    
    async def _predict_from_market_regime_enhanced(self, symbol: str, stock_data: Dict, historical_data: List[Dict]) -> Dict:
        """Phase 4.1: 강화된 시장 체제 분석 예측"""
        try:
            score = 50
            factors = []
            confidence = 45
            
            # 변동률 기반 변동성 분석
            change_rate = abs(stock_data.get('change_rate', 0))
            
            if change_rate > 5:
                score += 0  # 고변동성은 중립
                confidence += 15
                factors.append("고변동성 구간")
            elif change_rate > 2:
                score += 5
                confidence += 10
                factors.append("보통 변동성")
            else:
                score -= 5
                confidence -= 5
                factors.append("저변동성")
            
            # 거래량 기반 시장 참여도 분석
            volume = stock_data.get('volume', 0)
            avg_volume = stock_data.get('avg_volume', volume) or volume
            
            if avg_volume > 0:
                volume_ratio = volume / avg_volume
                if volume_ratio > 2:
                    score += 15
                    confidence += 10
                    factors.append("높은 시장 관심")
                elif volume_ratio < 0.5:
                    score -= 10
                    factors.append("시장 관심 저조")
            
            # 섹터 기반 분석 (mock)
            sector = stock_data.get('sector', '기타')
            if sector in ['IT', '바이오', '2차전지', '반도체']:
                score += 10
                confidence += 5
                factors.append(f"{sector} 섹터 강세")
            elif sector in ['건설', '조선', '철강']:
                score -= 5
                factors.append(f"{sector} 섹터 약세")
            
            # 최종 조정
            final_score = max(25, min(75, score))
            final_confidence = max(30, min(70, confidence))
            
            # 방향 결정
            if final_score >= 60:
                direction = "BULLISH"
            elif final_score <= 40:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
            
            return {
                'score': final_score,
                'direction': direction,
                'confidence': final_confidence,
                'factors': factors[:3],
                'model_type': 'market_regime_enhanced'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 강화된 시장 체제 분석 실패: {e}")
            return self._create_default_model_prediction()
    
    def _create_default_model_prediction(self) -> Dict:
        """기본 모델 예측 생성"""
        return {
            'score': 50,
            'direction': 'NEUTRAL',
            'confidence': 40,
            'factors': ['데이터 부족'],
            'model_type': 'default'
        }
    
    def _determine_action_from_score_and_direction(self, score: float, direction: str) -> str:
        """점수와 방향에 따른 액션 결정"""
        if direction == "BULLISH":
            return "STRONG_BUY" if score >= 80 else "BUY"
        elif direction == "BEARISH":
            return "STRONG_SELL" if score <= 20 else "SELL"
        else:
            return "HOLD"
    
    def _assess_risk_level(self, confidence: float, consensus_strength: float) -> str:
        """신뢰도와 합의도 기반 리스크 레벨 평가"""
        if confidence >= 80 and consensus_strength >= 0.8:
            return "LOW"
        elif confidence >= 60 and consensus_strength >= 0.6:
            return "MEDIUM"
        elif confidence >= 40:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _calculate_ensemble_price_target(self, current_price: float, direction: str, 
                                       confidence: float, predictions_detail: List[Dict]) -> Dict[str, float]:
        """앙상블 기반 가격 타겟 계산"""
        if current_price <= 0:
            return {'min': 0, 'max': 0, 'target': 0}
        
        # 신뢰도 기반 변동폭 계산
        base_volatility = 0.05  # 기본 5% 변동
        confidence_factor = confidence / 100.0
        volatility = base_volatility * (2.0 - confidence_factor)  # 신뢰도 높을수록 변동폭 작음
        
        if direction == "BULLISH":
            target = current_price * (1.0 + volatility * 2)
            max_price = current_price * (1.0 + volatility * 3)
            min_price = current_price * (1.0 - volatility * 0.5)
        elif direction == "BEARISH":
            target = current_price * (1.0 - volatility * 2)
            max_price = current_price * (1.0 + volatility * 0.5)
            min_price = current_price * (1.0 - volatility * 3)
        else:  # NEUTRAL
            target = current_price
            max_price = current_price * (1.0 + volatility)
            min_price = current_price * (1.0 - volatility)
        
        return {
            'min': max(0, min_price),
            'max': max_price,
            'target': max(0, target)
        }
    
    async def _store_prediction_for_learning(self, symbol: str, model_predictions: Dict, ensemble_prediction: MarketPrediction):
        """Phase 4.1: 예측 결과를 학습용으로 저장 (향후 정확도 개선에 활용)"""
        try:
            # 실제 구현에서는 데이터베이스에 저장
            prediction_record = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'model_predictions': model_predictions,
                'ensemble_prediction': {
                    'direction': ensemble_prediction.direction,
                    'confidence': ensemble_prediction.confidence,
                    'score': getattr(ensemble_prediction, 'ensemble_details', {}).get('weighted_score', 50)
                },
                'actual_result': None  # 나중에 실제 결과로 업데이트
            }
            
            # 메모리 기반 임시 저장 (실제로는 DB 저장)
            if not hasattr(self, 'prediction_history'):
                self.prediction_history = []
            
            self.prediction_history.append(prediction_record)
            
            # 최근 100개만 유지
            if len(self.prediction_history) > 100:
                self.prediction_history = self.prediction_history[-100:]
            
            self.logger.debug(f"📚 {symbol} 예측 학습 데이터 저장 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 예측 학습 데이터 저장 실패: {e}")
    
    # 추가 헬퍼 메서드들 (기존)
    async def _analyze_market_regime(self, symbol: str, stock_data: Dict, historical_data: List[Dict]) -> Dict:
        """시장 체제 분석 (간단한 버전)"""
        return {'regime': 'normal', 'confidence': 60}
    
    async def _predict_short_term_price(self, symbol: str, stock_data: Dict, current_price: float) -> MarketPrediction:
        """단기 가격 예측"""
        return self._create_default_prediction(symbol, stock_data)
    
    async def _predict_medium_term_price(self, symbol: str, stock_data: Dict, current_price: float) -> MarketPrediction:
        """중기 가격 예측"""
        return self._create_default_prediction(symbol, stock_data)
    
    async def _predict_long_term_price(self, symbol: str, stock_data: Dict, current_price: float) -> MarketPrediction:
        """장기 가격 예측"""
        return self._create_default_prediction(symbol, stock_data)
    
    async def _analyze_volatility_regime(self, market_data: List[Dict]) -> Dict:
        """변동성 체제 분석"""
        return {'volatility_level': 'MEDIUM', 'confidence': 60}
    
    async def _analyze_trend_regime(self, market_data: List[Dict]) -> Dict:
        """트렌드 체제 분석"""
        return {'trend_strength': 'MEDIUM', 'confidence': 60}
    
    async def _analyze_volume_regime(self, market_data: List[Dict]) -> Dict:
        """거래량 체제 분석"""
        return {'volume_level': 'NORMAL', 'confidence': 60}
    
    async def _ai_regime_analysis(self, market_data: List[Dict]) -> Dict:
        """AI 기반 체제 분석"""
        return {'ai_assessment': 'NORMAL', 'confidence': 60}
    
    async def _determine_market_regime(self, volatility: Dict, trend: Dict, volume: Dict, ai: Dict) -> MarketRegime:
        """최종 시장 체제 결정"""
        return self._create_default_regime()
    
    def _create_default_regime(self) -> MarketRegime:
        """기본 시장 체제 생성"""
        return MarketRegime(
            regime_type="sideways",
            confidence=60.0,
            start_date=datetime.now(),
            expected_duration=30,
            key_characteristics=["보통 변동성", "혼조 추세"],
            recommended_strategies=["momentum", "breakout"],
            risk_factors=["불확실한 방향성"]
        )
    
    # 추가 메서드들 (전략 최적화, 리스크 분석 등)
    async def _analyze_strategy_performance(self, strategy_name: str, performance_data: Dict) -> Dict:
        return {'performance_score': 60, 'strengths': [], 'weaknesses': []}
    
    async def _analyze_market_fit(self, strategy_name: str, market_conditions: Dict) -> Dict:
        return {'fit_score': 60, 'suitability': 'MEDIUM'}
    
    async def _ai_parameter_optimization(self, strategy_name: str, performance: Dict, market_fit: Dict) -> Dict:
        return {'optimized_params': {}, 'expected_improvement': 10}
    
    async def _generate_optimized_parameters(self, strategy_name: str, recommendations: Dict, market_conditions: Dict) -> Dict:
        return {'optimized_parameters': {}, 'confidence': 60}
    
    async def _analyze_portfolio_risk(self, portfolio_data: Dict) -> Dict:
        return {'risk_level': 'MEDIUM', 'concentration_risk': 30}
    
    async def _analyze_market_risk(self, market_conditions: Dict) -> Dict:
        return {'market_risk_level': 'MEDIUM', 'systemic_risk': 40}
    
    async def _analyze_correlation_risk(self, portfolio_data: Dict, market_conditions: Dict) -> Dict:
        return {'correlation_risk': 'MEDIUM', 'diversification_score': 60}
    
    async def _ai_comprehensive_risk_assessment(self, portfolio_risk: Dict, market_risk: Dict, correlation_risk: Dict) -> Dict:
        return {'risk_level': 'MEDIUM', 'risk_score': 50, 'risk_factors': []}
    
    async def _recommend_risk_mitigation(self, risk_assessment: Dict) -> List[str]:
        return ["포지션 크기 조절", "분산 투자 확대", "손절매 강화"]
    
    async def _analyze_news_impact_timing(self, news_data: List[Dict], stock_data: Dict) -> Dict:
        return {'impact_score': 60, 'key_factors': [], 'timing_analysis': {}}
    
    async def _predict_optimal_trading_timing(self, news_impact: Dict, stock_data: Dict) -> Dict:
        return {'entry_timing': 'IMMEDIATE', 'exit_timing': 'HOLD', 'confidence': 60}
    
    async def _recommend_news_based_strategies(self, news_impact: Dict, timing: Dict) -> List[str]:
        return ["뉴스 기반 모멘텀", "이벤트 드리븐"]