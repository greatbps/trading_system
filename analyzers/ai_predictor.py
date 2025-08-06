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
        
        # 예측 모델 가중치
        self.prediction_weights = {
            'technical_analysis': 0.25,
            'sentiment_analysis': 0.20,
            'news_impact': 0.20,
            'market_regime': 0.15,
            'volume_analysis': 0.10,
            'correlation_analysis': 0.10
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
        """시장 트렌드 예측"""
        try:
            self.logger.info(f"🔮 {symbol} 트렌드 예측 시작")
            
            # 1. 기술적 분석 기반 예측
            technical_prediction = await self._predict_from_technical(symbol, stock_data, historical_data)
            
            # 2. 뉴스 및 감정 분석 기반 예측
            sentiment_prediction = await self._predict_from_sentiment(symbol, stock_data)
            
            # 3. 시장 체제 분석
            market_regime = await self._analyze_market_regime(symbol, stock_data, historical_data)
            
            # 4. 종합 예측 생성
            final_prediction = await self._synthesize_predictions(
                symbol, technical_prediction, sentiment_prediction, market_regime
            )
            
            self.logger.info(f"✅ {symbol} 트렌드 예측 완료: {final_prediction.direction} ({final_prediction.confidence:.1f}%)")
            return final_prediction
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 트렌드 예측 실패: {e}")
            # 기본 예측 반환
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
    
    # 추가 헬퍼 메서드들 (실제 구현에서는 더 상세히 구현)
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