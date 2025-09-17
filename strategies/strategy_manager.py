#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/strategy_manager.py

전략 통합 관리자 - 모든 전략을 조화롭게 운영
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import time
import numpy as np

from .base_strategy import BaseStrategy
from .enhanced_multi_timeframe_strategy import EnhancedMultiTimeframeStrategy
from .momentum_strategy import MomentumStrategy
from .eod_strategy import EodStrategy
from .supertrend_ema_rsi_strategy import SupertrendEmaRsiStrategy
from .scalping_3m_strategy import Scalping3mStrategy

# Phase 1: 신호 품질 개선 모듈들
from signal_processing.consensus_engine import ConsensusEngine
from signal_processing.mtf_analyzer import MTFAnalyzer
from signal_processing.liquidity_gate import LiquidityGate
from signal_processing.news_gate import NewsGate
from signal_processing.regime_gate import RegimeGate
from monitoring.phase1_performance_monitor import phase1_monitor, SignalQualityMetrics

class StrategyType(Enum):
    """전략 타입"""
    MULTI_TIMEFRAME = "multi_timeframe"
    MOMENTUM = "momentum"
    EOD = "eod"
    SUPERTREND_EMA_RSI = "supertrend_ema_rsi"
    SCALPING_3M = "scalping_3m"

class MarketCondition(Enum):
    """시장 상황"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    LOW_VOLUME = "low_volume"

class StrategyManager:
    """전략 통합 관리자"""
    
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        
        # 전략 인스턴스 초기화
        self.strategies = {
            StrategyType.MULTI_TIMEFRAME: EnhancedMultiTimeframeStrategy(config),
            StrategyType.MOMENTUM: MomentumStrategy(config),
            StrategyType.EOD: EodStrategy(config),
            StrategyType.SUPERTREND_EMA_RSI: SupertrendEmaRsiStrategy(config),
            StrategyType.SCALPING_3M: Scalping3mStrategy(config)
        }
        
        # Phase 1: 신호 품질 개선 시스템 초기화
        self.phase1_enabled = getattr(config, 'phase1_enabled', True)
        if self.phase1_enabled:
            self._setup_phase1_systems()
        
        # 시장 상황별 전략 가중치
        self.strategy_weights = {
            MarketCondition.TRENDING_UP: {
                StrategyType.MOMENTUM: 0.35,
                StrategyType.MULTI_TIMEFRAME: 0.30,
                StrategyType.SUPERTREND_EMA_RSI: 0.25,
                StrategyType.EOD: 0.05,
                StrategyType.SCALPING_3M: 0.05
            },
            MarketCondition.TRENDING_DOWN: {
                StrategyType.MULTI_TIMEFRAME: 0.40,
                StrategyType.MOMENTUM: 0.20,
                StrategyType.SUPERTREND_EMA_RSI: 0.20,
                StrategyType.EOD: 0.10,
                StrategyType.SCALPING_3M: 0.10
            },
            MarketCondition.SIDEWAYS: {
                StrategyType.SCALPING_3M: 0.40,
                StrategyType.MULTI_TIMEFRAME: 0.25,
                StrategyType.SUPERTREND_EMA_RSI: 0.20,
                StrategyType.MOMENTUM: 0.10,
                StrategyType.EOD: 0.05
            },
            MarketCondition.VOLATILE: {
                StrategyType.SCALPING_3M: 0.35,
                StrategyType.MULTI_TIMEFRAME: 0.30,
                StrategyType.MOMENTUM: 0.20,
                StrategyType.SUPERTREND_EMA_RSI: 0.10,
                StrategyType.EOD: 0.05
            },
            MarketCondition.LOW_VOLUME: {
                StrategyType.MULTI_TIMEFRAME: 0.50,
                StrategyType.EOD: 0.30,
                StrategyType.MOMENTUM: 0.15,
                StrategyType.SUPERTREND_EMA_RSI: 0.05,
                StrategyType.SCALPING_3M: 0.00
            }
        }
        
        # 신호 합의 임계값
        self.consensus_thresholds = {
            'strong_consensus': 0.8,    # 80% 이상 합의
            'weak_consensus': 0.6,      # 60% 이상 합의
            'no_consensus': 0.4         # 40% 미만 합의
        }
        
        self.logger.info("🎯 전략 통합 관리자 초기화 완료")

    def _setup_phase1_systems(self):
        """Phase 1: 신호 품질 개선 시스템 설정"""
        try:
            # 전략 이름 매핑 (Phase 1 모듈과 기존 전략 연결)
            strategy_names = ['momentum', 'mean_reversion', 'volume_spike', 'sentiment']
            
            # 1. 멀티전략 합의 엔진
            self.consensus_engine = ConsensusEngine(
                strategies=strategy_names,
                lookback_days=getattr(self.config, 'phase1_lookback_days', 60)
            )
            
            # 2. MTF 컨플루언스 분석기
            timeframes = getattr(self.config, 'phase1_timeframes', ['3m', '15m', '1h', '1d'])
            self.mtf_analyzer = MTFAnalyzer(timeframes)
            
            # 3. 게이트 시스템들
            self.liquidity_gate = LiquidityGate(
                atr_min_pct=getattr(self.config, 'phase1_atr_min', 2.0),
                trade_value_min=getattr(self.config, 'phase1_trade_value_min', 1000000),
                spread_max_pct=getattr(self.config, 'phase1_spread_max', 0.5)
            )
            
            self.news_gate = NewsGate(
                sentiment_threshold=getattr(self.config, 'phase1_sentiment_threshold', -0.5),
                disclosure_cooldown_minutes=getattr(self.config, 'phase1_cooldown_minutes', 60)
            )
            
            self.regime_gate = RegimeGate(
                adx_threshold=getattr(self.config, 'phase1_adx_threshold', 25)
            )
            
            # 4. 성능 임계값 설정
            self.phase1_thresholds = {
                'consensus_threshold': getattr(self.config, 'phase1_consensus_threshold', 2.0),
                'mtf_threshold': getattr(self.config, 'phase1_mtf_threshold', 0.6),
                'min_signal_confidence': getattr(self.config, 'phase1_min_confidence', 0.7)
            }
            
            self.logger.info("✅ Phase 1 신호 품질 개선 시스템 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"❌ Phase 1 시스템 초기화 실패: {e}")
            self.phase1_enabled = False

    def _setup_logger(self):
        """로거 설정"""
        import logging
        logger = logging.getLogger("StrategyManager")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    async def generate_consensus_signal(self, stock_data: Any, analysis_result: Dict, price_data: Dict = None) -> Dict[str, Any]:
        """전략 합의 신호 생성 - Phase 1 품질 개선 적용"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"🎯 {symbol} 전략 합의 신호 생성 시작")
            
            # Phase 1이 활성화된 경우 고품질 신호 생성
            if self.phase1_enabled:
                return await self._generate_phase1_enhanced_signal(stock_data, analysis_result, price_data)
            else:
                # 기존 방식 사용
                return await self._generate_legacy_signal(stock_data, analysis_result, price_data)
                
        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} 전략 합의 신호 생성 실패: {e}")
            return self._create_default_signal()

    async def _generate_phase1_enhanced_signal(self, stock_data: Any, analysis_result: Dict, price_data: Dict = None) -> Dict[str, Any]:
        """Phase 1: 고품질 신호 생성"""
        import time
        symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
        
        # 성능 모니터링 시작
        timing_data = phase1_monitor.start_signal_timing()
        
        try:
            # 1. 기존 전략 실행
            phase1_monitor.record_consensus_timing(timing_data)
            market_condition = await self._analyze_market_condition(stock_data, analysis_result, price_data)
            strategy_results = await self._execute_strategies(stock_data, analysis_result, price_data, market_condition)
            
            # 2. 전략 신호를 Phase 1 형식으로 변환
            strategy_signals = self._convert_to_phase1_signals(strategy_results)
            
            # 3. 멀티전략 합의 계산
            consensus_start = time.perf_counter()
            consensus_score = self.consensus_engine.calculate_consensus_score(strategy_signals)
            consensus_reached = self.consensus_engine.is_consensus_reached(
                consensus_score, self.phase1_thresholds['consensus_threshold']
            )
            consensus_time = (time.perf_counter() - consensus_start) * 1000
            
            # 4. MTF 컨플루언스 분석
            phase1_monitor.record_mtf_timing(timing_data)
            mtf_signals = self._extract_mtf_signals(price_data, analysis_result)
            
            mtf_start = time.perf_counter()
            mtf_score = self.mtf_analyzer.calculate_confluence_score(mtf_signals)
            mtf_confluence = self.mtf_analyzer.is_confluence_met(
                mtf_score, self.phase1_thresholds['mtf_threshold']
            )
            mtf_time = (time.perf_counter() - mtf_start) * 1000
            
            # 5. 게이트 시스템 평가
            phase1_monitor.record_gate_timing(timing_data)
            gate_start = time.perf_counter()
            
            # 5-1. 유동성 게이트
            market_data = self._prepare_market_data_for_gates(stock_data, analysis_result)
            liquidity_pass = self.liquidity_gate.evaluate(symbol, market_data)
            
            # 5-2. 뉴스 게이트
            news_data = self._prepare_news_data_for_gates(stock_data, analysis_result)
            news_pass = self.news_gate.evaluate(symbol, news_data)
            
            # 5-3. 레짐 게이트
            regime_data = self._prepare_regime_data_for_gates(stock_data, analysis_result, price_data)
            current_regime = self.regime_gate.detect_regime(regime_data)
            
            gate_time = (time.perf_counter() - gate_start) * 1000
            
            # 6. 레짐별 전략 적합도 조정
            regime_adjusted_signals = self._adjust_signals_for_regime(strategy_signals, current_regime)
            
            # 7. 최종 신호 결정
            final_signal_strength = self._calculate_final_signal_strength(
                consensus_score, mtf_score, liquidity_pass, news_pass, regime_adjusted_signals
            )
            
            signal_confidence = self._calculate_signal_confidence(
                consensus_reached, mtf_confluence, liquidity_pass, news_pass, final_signal_strength
            )
            
            # 8. 성능 메트릭 기록
            total_time = (time.perf_counter() - timing_data['start_time']) * 1000
            
            metrics = SignalQualityMetrics(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                consensus_score=consensus_score,
                participating_strategies=len(strategy_signals),
                consensus_time_ms=consensus_time,
                mtf_score=mtf_score,
                timeframe_alignment=mtf_signals,
                mtf_calculation_time_ms=mtf_time,
                liquidity_gate_passed=liquidity_pass,
                news_gate_passed=news_pass,
                regime_gate_passed=True,  # 레짐은 항상 통과, 신호 조정만
                total_gate_time_ms=gate_time,
                final_signal_strength=final_signal_strength,
                signal_confidence=signal_confidence
            )
            
            phase1_monitor.record_signal_metrics(metrics)
            
            # 9. Phase 1 최종 신호 구성
            return self._build_phase1_final_signal(
                consensus_score, consensus_reached, mtf_score, mtf_confluence,
                liquidity_pass, news_pass, current_regime, final_signal_strength,
                signal_confidence, strategy_results, market_condition, symbol
            )
            
        except Exception as e:
            self.logger.error(f"❌ Phase 1 신호 생성 실패 ({symbol}): {e}")
            return self._create_default_signal()

    async def _generate_legacy_signal(self, stock_data: Any, analysis_result: Dict, price_data: Dict = None) -> Dict[str, Any]:
        """기존 방식의 신호 생성"""
        symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
        
        # 1. 시장 상황 분석
        market_condition = await self._analyze_market_condition(stock_data, analysis_result, price_data)
        
        # 2. 시장 상황에 맞는 전략 선택 및 실행
        strategy_results = await self._execute_strategies(stock_data, analysis_result, price_data, market_condition)
        
        # 3. 전략 결과 통합 및 합의 도출
        consensus_signal = await self._build_consensus(strategy_results, market_condition, stock_data)
        
        # 4. 최종 신호 검증 및 조정
        final_signal = await self._validate_and_adjust_signal(consensus_signal, stock_data, market_condition)
        
        self.logger.info(f"✅ {symbol} 기존 방식 합의 완료 - 최종: {final_signal['signal_type']}")
        
        return final_signal

    async def _analyze_market_condition(self, stock_data: Any, analysis_result: Dict, price_data: Dict) -> MarketCondition:
        """시장 상황 분석"""
        try:
            # 기본 데이터 추출
            change_rate = getattr(stock_data, 'change_rate', 0)
            volume = getattr(stock_data, 'volume', 0)
            avg_volume = getattr(stock_data, 'avg_volume_30d', volume)
            
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            
            # 기술적 지표에서 변동성 추정
            technical_details = analysis_result.get('technical_details', {})
            volatility_indicator = abs(change_rate)
            
            # 조건별 판단
            conditions_score = {
                MarketCondition.TRENDING_UP: 0,
                MarketCondition.TRENDING_DOWN: 0,
                MarketCondition.SIDEWAYS: 0,
                MarketCondition.VOLATILE: 0,
                MarketCondition.LOW_VOLUME: 0
            }
            
            # 1. 추세 분석
            if change_rate > 2.0:
                conditions_score[MarketCondition.TRENDING_UP] += 30
            elif change_rate > 1.0:
                conditions_score[MarketCondition.TRENDING_UP] += 20
            elif change_rate < -2.0:
                conditions_score[MarketCondition.TRENDING_DOWN] += 30
            elif change_rate < -1.0:
                conditions_score[MarketCondition.TRENDING_DOWN] += 20
            else:
                conditions_score[MarketCondition.SIDEWAYS] += 25
            
            # 2. 변동성 분석
            if volatility_indicator > 5.0:
                conditions_score[MarketCondition.VOLATILE] += 40
            elif volatility_indicator > 3.0:
                conditions_score[MarketCondition.VOLATILE] += 25
            
            # 3. 거래량 분석
            if volume_ratio < 0.5:
                conditions_score[MarketCondition.LOW_VOLUME] += 40
            elif volume_ratio > 2.0:
                conditions_score[MarketCondition.VOLATILE] += 15
                conditions_score[MarketCondition.TRENDING_UP] += 10
            
            # 4. 시간대별 패턴 분석 (price_data 활용)
            if price_data:
                recent_volatility = self._calculate_recent_volatility(price_data)
                if recent_volatility > 0.8:
                    conditions_score[MarketCondition.VOLATILE] += 20
                elif recent_volatility < 0.3:
                    conditions_score[MarketCondition.SIDEWAYS] += 15
            
            # 최고 점수 조건 선택
            best_condition = max(conditions_score, key=conditions_score.get)
            
            self.logger.debug(f"시장 상황 분석: {best_condition.value} (점수: {conditions_score[best_condition]})")
            
            return best_condition
            
        except Exception as e:
            self.logger.error(f"❌ 시장 상황 분석 실패: {e}")
            return MarketCondition.SIDEWAYS  # 기본값

    def _calculate_recent_volatility(self, price_data: Dict) -> float:
        """최근 변동성 계산"""
        try:
            # 여러 시간대에서 변동성 계산
            volatilities = []
            
            for timeframe, data in price_data.items():
                if data and len(data) >= 10:
                    prices = [float(item['close']) for item in data[-10:]]
                    if len(prices) > 1:
                        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
                        volatility = np.std(returns) if returns else 0
                        volatilities.append(volatility)
            
            return np.mean(volatilities) if volatilities else 0.5
            
        except:
            return 0.5

    async def _execute_strategies(self, stock_data: Any, analysis_result: Dict, price_data: Dict, market_condition: MarketCondition) -> Dict[StrategyType, Dict]:
        """시장 상황에 맞는 전략 실행"""
        strategy_results = {}
        
        # 현재 시장 상황에 맞는 가중치 가져오기
        weights = self.strategy_weights.get(market_condition, self.strategy_weights[MarketCondition.SIDEWAYS])
        
        # 가중치가 있는 전략들만 실행
        active_strategies = [strategy_type for strategy_type, weight in weights.items() if weight > 0]
        
        for strategy_type in active_strategies:
            try:
                strategy = self.strategies[strategy_type]
                
                # 전략별 맞춤 실행
                if strategy_type == StrategyType.SCALPING_3M:
                    # 스캘핑 전략은 다른 입력 형식 사용
                    result = await strategy.generate_signals(self._convert_to_scalping_format(stock_data, analysis_result))
                else:
                    # 나머지 전략들
                    result = await strategy.generate_signals(stock_data, analysis_result, price_data)
                
                if result:
                    strategy_results[strategy_type] = {
                        'result': result,
                        'weight': weights[strategy_type],
                        'executed_at': datetime.now().isoformat()
                    }
                    
                    self.logger.debug(f"✅ {strategy_type.value} 전략 실행 완료: {result.get('signal_type', 'UNKNOWN')}")
                
            except Exception as e:
                self.logger.error(f"❌ {strategy_type.value} 전략 실행 실패: {e}")
                continue
        
        return strategy_results

    def _convert_to_scalping_format(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """스캘핑 전략용 데이터 형식으로 변환"""
        try:
            return {
                'symbol': getattr(stock_data, 'symbol', 'UNKNOWN'),
                'current_price': getattr(stock_data, 'current_price', 0),
                'change_rate': getattr(stock_data, 'change_rate', 0),
                'volume': getattr(stock_data, 'volume', 0),
                'avg_volume_30d': getattr(stock_data, 'avg_volume_30d', getattr(stock_data, 'volume', 0)),
                'high_52w': getattr(stock_data, 'high_52w', getattr(stock_data, 'current_price', 0) * 1.5),
                'low_52w': getattr(stock_data, 'low_52w', getattr(stock_data, 'current_price', 0) * 0.5),
                'technical_indicators': analysis_result.get('technical_details', {})
            }
        except Exception as e:
            self.logger.error(f"❌ 스캘핑 형식 변환 실패: {e}")
            return {}

    async def _build_consensus(self, strategy_results: Dict[StrategyType, Dict], market_condition: MarketCondition, stock_data: Any) -> Dict[str, Any]:
        """전략 결과 통합 및 합의 도출"""
        try:
            if not strategy_results:
                return self._create_default_signal()
            
            # 1. 신호별 가중 점수 계산
            signal_scores = {}
            total_weight = 0
            
            for strategy_type, strategy_data in strategy_results.items():
                result = strategy_data['result']
                weight = strategy_data['weight']
                
                signal_type = result.get('signal_type', 'HOLD')
                signal_strength = result.get('signal_strength', 50)
                confidence = result.get('confidence', 0.5)
                
                # 신호 점수 계산 (강도 * 신뢰도 * 가중치)
                score = signal_strength * confidence * weight
                
                if signal_type not in signal_scores:
                    signal_scores[signal_type] = 0
                
                signal_scores[signal_type] += score
                total_weight += weight
            
            # 2. 정규화
            if total_weight > 0:
                for signal_type in signal_scores:
                    signal_scores[signal_type] /= total_weight
            
            # 3. 최고 점수 신호 선택
            if signal_scores:
                consensus_signal = max(signal_scores, key=signal_scores.get)
                consensus_strength = signal_scores[consensus_signal]
            else:
                consensus_signal = 'HOLD'
                consensus_strength = 50.0
            
            # 4. 합의도 계산
            consensus_level = self._calculate_consensus_level(strategy_results)
            
            # 5. 리스크 평가
            risk_assessment = self._assess_consensus_risk(strategy_results, market_condition)
            
            # 6. 상세 정보 구성
            strategy_details = {}
            for strategy_type, strategy_data in strategy_results.items():
                strategy_details[strategy_type.value] = {
                    'signal': strategy_data['result'].get('signal_type', 'HOLD'),
                    'strength': strategy_data['result'].get('signal_strength', 50),
                    'weight': strategy_data['weight']
                }
            
            return {
                'consensus_signal': consensus_signal,
                'consensus_strength': consensus_strength,
                'consensus_level': consensus_level,
                'market_condition': market_condition.value,
                'strategy_count': len(strategy_results),
                'strategy_details': strategy_details,
                'risk_assessment': risk_assessment,
                'signal_scores': signal_scores
            }
            
        except Exception as e:
            self.logger.error(f"❌ 전략 합의 도출 실패: {e}")
            return self._create_default_signal()

    def _calculate_consensus_level(self, strategy_results: Dict) -> str:
        """합의 수준 계산"""
        try:
            if len(strategy_results) < 2:
                return 'insufficient_data'
            
            # 신호 타입별 개수 세기
            signal_counts = {}
            total_strategies = len(strategy_results)
            
            for strategy_data in strategy_results.values():
                signal_type = strategy_data['result'].get('signal_type', 'HOLD')
                signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
            
            # 최다 신호의 비율 계산
            max_count = max(signal_counts.values()) if signal_counts else 0
            consensus_ratio = max_count / total_strategies
            
            if consensus_ratio >= self.consensus_thresholds['strong_consensus']:
                return 'strong_consensus'
            elif consensus_ratio >= self.consensus_thresholds['weak_consensus']:
                return 'weak_consensus'
            else:
                return 'no_consensus'
                
        except Exception as e:
            self.logger.error(f"❌ 합의 수준 계산 실패: {e}")
            return 'no_consensus'

    def _assess_consensus_risk(self, strategy_results: Dict, market_condition: MarketCondition) -> Dict[str, Any]:
        """합의 리스크 평가"""
        try:
            risk_factors = {
                'strategy_divergence': 0,
                'market_uncertainty': 0,
                'signal_weakness': 0,
                'volatility_risk': 0
            }
            
            # 1. 전략 간 분산도
            signal_types = [data['result'].get('signal_type', 'HOLD') for data in strategy_results.values()]
            unique_signals = len(set(signal_types))
            risk_factors['strategy_divergence'] = min(unique_signals / len(strategy_results), 1.0) if strategy_results else 0
            
            # 2. 시장 불확실성
            volatile_conditions = [MarketCondition.VOLATILE, MarketCondition.LOW_VOLUME]
            if market_condition in volatile_conditions:
                risk_factors['market_uncertainty'] = 0.7
            else:
                risk_factors['market_uncertainty'] = 0.3
            
            # 3. 신호 약함
            avg_strength = np.mean([data['result'].get('signal_strength', 50) for data in strategy_results.values()])
            if avg_strength < 40 or avg_strength > 90:
                risk_factors['signal_weakness'] = 0.8
            elif avg_strength < 50 or avg_strength > 80:
                risk_factors['signal_weakness'] = 0.5
            else:
                risk_factors['signal_weakness'] = 0.2
            
            # 4. 변동성 리스크
            if market_condition == MarketCondition.VOLATILE:
                risk_factors['volatility_risk'] = 0.9
            elif market_condition == MarketCondition.SIDEWAYS:
                risk_factors['volatility_risk'] = 0.3
            else:
                risk_factors['volatility_risk'] = 0.5
            
            # 총 리스크 계산
            total_risk = np.mean(list(risk_factors.values()))
            
            return {
                'total_risk': total_risk,
                'risk_level': 'high' if total_risk > 0.7 else 'medium' if total_risk > 0.4 else 'low',
                'risk_factors': risk_factors
            }
            
        except Exception as e:
            self.logger.error(f"❌ 합의 리스크 평가 실패: {e}")
            return {'total_risk': 0.7, 'risk_level': 'high', 'risk_factors': {}}

    async def _validate_and_adjust_signal(self, consensus_signal: Dict, stock_data: Any, market_condition: MarketCondition) -> Dict[str, Any]:
        """최종 신호 검증 및 조정"""
        try:
            signal = consensus_signal['consensus_signal']
            strength = consensus_signal['consensus_strength']
            consensus_level = consensus_signal['consensus_level']
            risk_assessment = consensus_signal['risk_assessment']
            
            # 1. 합의 수준에 따른 신호 조정
            if consensus_level == 'no_consensus':
                signal = 'HOLD'
                strength = 50.0
                adjustment_reason = "전략 간 합의 부족으로 HOLD로 조정"
            elif consensus_level == 'weak_consensus' and risk_assessment['risk_level'] == 'high':
                # 약한 합의 + 고위험인 경우 보수적으로 조정
                if signal in ['STRONG_BUY', 'STRONG_SELL']:
                    signal = 'WEAK_BUY' if 'BUY' in signal else 'WEAK_SELL'
                    strength *= 0.7
                    adjustment_reason = "약한 합의 + 고위험으로 신호 강도 조정"
                else:
                    adjustment_reason = None
            else:
                adjustment_reason = None
            
            # 2. 시장 상황에 따른 추가 조정
            if market_condition == MarketCondition.LOW_VOLUME and signal in ['STRONG_BUY', 'STRONG_SELL']:
                signal = 'HOLD'
                strength = 50.0
                adjustment_reason = "저거래량 상황으로 신호 비활성화"
            
            # 3. 최종 액션 결정
            action_mapping = {
                'STRONG_BUY': 'BUY',
                'BUY': 'BUY', 
                'WEAK_BUY': 'HOLD',
                'HOLD': 'HOLD',
                'WEAK_SELL': 'HOLD',
                'SELL': 'SELL',
                'STRONG_SELL': 'SELL'
            }
            
            final_action = action_mapping.get(signal, 'HOLD')
            
            # 4. 신뢰도 계산
            confidence_factors = [
                consensus_level == 'strong_consensus',
                risk_assessment['risk_level'] == 'low',
                consensus_signal['strategy_count'] >= 3,
                strength > 60 and strength < 90
            ]
            
            base_confidence = strength / 100
            confidence_bonus = sum(confidence_factors) * 0.1
            final_confidence = min(0.95, base_confidence + confidence_bonus)
            
            # 5. 포지션 사이징 팩터
            position_factor = self._calculate_position_factor(signal, consensus_level, risk_assessment, market_condition)
            
            return {
                'signal_strength': round(strength, 1),
                'signal_type': signal,
                'action': final_action,
                'confidence': round(final_confidence, 3),
                'position_sizing_factor': position_factor,
                'details': {
                    'consensus_level': consensus_level,
                    'market_condition': market_condition.value,
                    'strategy_count': consensus_signal['strategy_count'],
                    'strategy_breakdown': consensus_signal['strategy_details'],
                    'risk_assessment': risk_assessment,
                    'adjustment_reason': adjustment_reason,
                    'signal_scores': consensus_signal.get('signal_scores', {})
                },
                'risk_level': risk_assessment['risk_level'].upper(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 최종 신호 검증 실패: {e}")
            return self._create_default_signal()

    def _calculate_position_factor(self, signal: str, consensus_level: str, risk_assessment: Dict, market_condition: MarketCondition) -> float:
        """포지션 사이징 팩터 계산"""
        try:
            base_factor = 0.5  # 기본 50%
            
            # 신호 강도별 조정
            if signal in ['STRONG_BUY', 'STRONG_SELL']:
                base_factor = 0.8
            elif signal in ['BUY', 'SELL']:
                base_factor = 0.6
            elif signal in ['WEAK_BUY', 'WEAK_SELL']:
                base_factor = 0.3
            else:  # HOLD
                base_factor = 0.0
            
            # 합의 수준별 조정
            if consensus_level == 'strong_consensus':
                consensus_multiplier = 1.2
            elif consensus_level == 'weak_consensus':
                consensus_multiplier = 0.8
            else:
                consensus_multiplier = 0.5
            
            # 리스크별 조정
            risk_level = risk_assessment.get('risk_level', 'medium')
            if risk_level == 'low':
                risk_multiplier = 1.1
            elif risk_level == 'medium':
                risk_multiplier = 0.9
            else:  # high
                risk_multiplier = 0.6
            
            # 시장 상황별 조정
            market_multipliers = {
                MarketCondition.TRENDING_UP: 1.0,
                MarketCondition.TRENDING_DOWN: 0.8,
                MarketCondition.SIDEWAYS: 0.7,
                MarketCondition.VOLATILE: 0.6,
                MarketCondition.LOW_VOLUME: 0.4
            }
            
            market_multiplier = market_multipliers.get(market_condition, 0.7)
            
            # 최종 계산
            final_factor = base_factor * consensus_multiplier * risk_multiplier * market_multiplier
            
            return round(min(1.0, max(0.0, final_factor)), 2)
            
        except Exception as e:
            self.logger.error(f"❌ 포지션 팩터 계산 실패: {e}")
            return 0.3

    def _create_default_signal(self) -> Dict[str, Any]:
        """기본 신호 생성"""
        return {
            'signal_strength': 50.0,
            'signal_type': 'HOLD',
            'action': 'HOLD',
            'confidence': 0.5,
            'position_sizing_factor': 0.0,
            'details': {
                'consensus_level': 'no_data',
                'market_condition': 'unknown',
                'strategy_count': 0,
                'error': 'Failed to generate consensus signal'
            },
            'risk_level': 'HIGH',
            'timestamp': datetime.now().isoformat()
        }

    async def get_strategy_status(self) -> Dict[str, Any]:
        """전략 상태 조회"""
        try:
            status = {
                'total_strategies': len(self.strategies),
                'active_strategies': list(self.strategies.keys()),
                'market_conditions': [condition.value for condition in MarketCondition],
                'consensus_thresholds': self.consensus_thresholds,
                'last_updated': datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ 전략 상태 조회 실패: {e}")
            return {'error': str(e)}

    def _convert_to_phase1_signals(self, strategy_results: Dict) -> Dict[str, float]:
        """기존 전략 결과를 Phase 1 신호 형식으로 변환"""
        phase1_signals = {}
        
        # 전략 타입을 Phase 1 이름으로 매핑
        strategy_mapping = {
            'momentum': StrategyType.MOMENTUM,
            'mean_reversion': StrategyType.EOD,  # EOD를 평균회귀로 매핑
            'volume_spike': StrategyType.SCALPING_3M,  # 스캘핑을 볼륨스파이크로 매핑
            'sentiment': StrategyType.MULTI_TIMEFRAME  # MTF를 센티먼트로 매핑
        }
        
        for phase1_name, strategy_type in strategy_mapping.items():
            if strategy_type in strategy_results:
                strategy_data = strategy_results[strategy_type]
                result = strategy_data['result']
                
                # 신호 강도를 -1 ~ 1 범위로 정규화
                signal_type = result.get('signal_type', 'HOLD')
                signal_strength = result.get('signal_strength', 50)
                
                # BUY/SELL을 -1~1 범위로 변환
                if 'BUY' in signal_type:
                    normalized_signal = (signal_strength - 50) / 50  # 50~100 -> 0~1
                elif 'SELL' in signal_type:
                    normalized_signal = -(signal_strength - 50) / 50  # 50~100 -> 0~-1
                else:  # HOLD
                    normalized_signal = 0.0
                
                # -1 ~ 1 범위로 클램핑
                phase1_signals[phase1_name] = max(-1.0, min(1.0, normalized_signal))
        
        return phase1_signals

    def _extract_mtf_signals(self, price_data: Dict, analysis_result: Dict) -> Dict[str, float]:
        """멀티 타임프레임 신호 추출"""
        mtf_signals = {}
        target_timeframes = ['3m', '15m', '1h', '1d']
        
        try:
            if price_data:
                # 가격 데이터에서 추세 강도 계산
                for timeframe in target_timeframes:
                    if timeframe in price_data and price_data[timeframe]:
                        data = price_data[timeframe]
                        if len(data) >= 5:
                            # 간단한 추세 강도 계산 (최근 5개 봉의 종가 기울기)
                            closes = [float(item['close']) for item in data[-5:]]
                            trend_strength = (closes[-1] - closes[0]) / closes[0]
                            # -1 ~ 1 범위로 정규화 (±10% 변동을 최대로 가정)
                            normalized = max(-1.0, min(1.0, trend_strength * 10))
                            mtf_signals[timeframe] = max(0.0, normalized)  # 양수만 사용 (상승 신호)
                        else:
                            mtf_signals[timeframe] = 0.5
                    else:
                        mtf_signals[timeframe] = 0.5
            else:
                # 기본값으로 채우기
                for timeframe in target_timeframes:
                    mtf_signals[timeframe] = 0.5
                    
        except Exception as e:
            self.logger.error(f"❌ MTF 신호 추출 실패: {e}")
            for timeframe in target_timeframes:
                mtf_signals[timeframe] = 0.5
        
        return mtf_signals

    def _prepare_market_data_for_gates(self, stock_data: Any, analysis_result: Dict) -> Dict:
        """게이트 시스템용 시장 데이터 준비"""
        try:
            current_price = getattr(stock_data, 'current_price', 0)
            volume = getattr(stock_data, 'volume', 0)
            avg_volume = getattr(stock_data, 'avg_volume_30d', volume)
            
            # ATR 추정 (변동성 기반)
            change_rate = getattr(stock_data, 'change_rate', 0)
            estimated_atr = current_price * (abs(change_rate) / 100) if current_price > 0 else 0
            
            # 거래대금 계산
            avg_trade_value = current_price * avg_volume if current_price > 0 else 0
            
            # 스프레드 추정 (거래량 역비례)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            estimated_spread = max(0.1, min(1.0, 1.0 / volume_ratio)) * 0.5  # 0.05% ~ 0.5%
            
            return {
                'price': current_price,
                'atr': estimated_atr,
                'avg_trade_value': avg_trade_value,
                'spread_pct': estimated_spread
            }
            
        except Exception as e:
            self.logger.error(f"❌ 시장 데이터 준비 실패: {e}")
            return {
                'price': 1000,
                'atr': 50,
                'avg_trade_value': 1000000,
                'spread_pct': 0.5
            }

    def _prepare_news_data_for_gates(self, stock_data: Any, analysis_result: Dict) -> List[Dict]:
        """게이트 시스템용 뉴스 데이터 준비"""
        try:
            # 실제 뉴스 데이터가 없으므로 기본 중립 뉴스로 생성
            default_news = [{
                'type': 'news',
                'timestamp': datetime.now() - timedelta(hours=2),
                'sentiment': 0.1,  # 중립적
                'content': '일반적인 시장 뉴스'
            }]
            
            # analysis_result에서 뉴스 관련 정보 추출 시도
            if 'news' in analysis_result:
                news_info = analysis_result['news']
                if isinstance(news_info, dict):
                    sentiment = news_info.get('sentiment', 0.1)
                    content = news_info.get('content', '분석 결과')
                    return [{
                        'type': 'news',
                        'timestamp': datetime.now() - timedelta(hours=1),
                        'sentiment': sentiment,
                        'content': content
                    }]
            
            return default_news
            
        except Exception as e:
            self.logger.error(f"❌ 뉴스 데이터 준비 실패: {e}")
            return [{
                'type': 'news',
                'timestamp': datetime.now() - timedelta(hours=2),
                'sentiment': 0.0,
                'content': '기본 뉴스'
            }]

    def _prepare_regime_data_for_gates(self, stock_data: Any, analysis_result: Dict, price_data: Dict) -> Dict:
        """게이트 시스템용 레짐 데이터 준비"""
        try:
            # ADX 추정 (변동성 기반)
            change_rate = getattr(stock_data, 'change_rate', 0)
            estimated_adx = min(50, max(10, abs(change_rate) * 5))  # 10-50 범위
            
            # 이동평균 추정
            current_price = getattr(stock_data, 'current_price', 0)
            if current_price > 0:
                # 단순히 현재가 기준으로 추정
                sma_short = current_price * (1 + change_rate / 200)  # 약간의 차이
                sma_long = current_price * (1 + change_rate / 400)   # 더 작은 차이
            else:
                sma_short = 50000
                sma_long = 49000
            
            return {
                'adx': estimated_adx,
                'sma_short': sma_short,
                'sma_long': sma_long
            }
            
        except Exception as e:
            self.logger.error(f"❌ 레짐 데이터 준비 실패: {e}")
            return {
                'adx': 25,
                'sma_short': 50000,
                'sma_long': 49000
            }

    def _adjust_signals_for_regime(self, strategy_signals: Dict[str, float], current_regime: str) -> Dict[str, float]:
        """레짐에 따른 전략 신호 조정"""
        try:
            adjusted_signals = strategy_signals.copy()
            
            # 레짐별 전략 적합도로 신호 조정
            for strategy_name in strategy_signals:
                regime_score = self.regime_gate.evaluate_strategy_for_regime(strategy_name, current_regime)
                adjusted_signals[strategy_name] *= regime_score
            
            return adjusted_signals
            
        except Exception as e:
            self.logger.error(f"❌ 레짐 신호 조정 실패: {e}")
            return strategy_signals

    def _calculate_final_signal_strength(self, consensus_score: float, mtf_score: float, 
                                        liquidity_pass: bool, news_pass: bool, 
                                        regime_adjusted_signals: Dict[str, float]) -> float:
        """최종 신호 강도 계산"""
        try:
            # 기본 강도는 합의 점수와 MTF 점수의 가중 평균
            base_strength = (consensus_score * 0.6 + mtf_score * 100 * 0.4)
            
            # 게이트 통과 여부에 따른 조정
            gate_multiplier = 1.0
            if not liquidity_pass:
                gate_multiplier *= 0.5
            if not news_pass:
                gate_multiplier *= 0.3
            
            # 레짐 조정된 신호들의 평균 강도
            if regime_adjusted_signals:
                regime_strength = np.mean(list(regime_adjusted_signals.values())) * 100
                final_strength = (base_strength * 0.7 + regime_strength * 0.3) * gate_multiplier
            else:
                final_strength = base_strength * gate_multiplier
            
            return max(0.0, min(100.0, final_strength))
            
        except Exception as e:
            self.logger.error(f"❌ 최종 신호 강도 계산 실패: {e}")
            return 50.0

    def _calculate_signal_confidence(self, consensus_reached: bool, mtf_confluence: bool,
                                   liquidity_pass: bool, news_pass: bool, 
                                   signal_strength: float) -> float:
        """신호 신뢰도 계산"""
        try:
            confidence_factors = [
                consensus_reached,
                mtf_confluence, 
                liquidity_pass,
                news_pass,
                40 <= signal_strength <= 90  # 극단적이지 않은 신호
            ]
            
            # 통과한 조건의 비율
            base_confidence = sum(confidence_factors) / len(confidence_factors)
            
            # 신호 강도에 따른 조정
            if signal_strength > 80 or signal_strength < 20:
                strength_multiplier = 0.8  # 극단적 신호는 신뢰도 감소
            else:
                strength_multiplier = 1.0
            
            final_confidence = base_confidence * strength_multiplier
            
            return max(0.0, min(1.0, final_confidence))
            
        except Exception as e:
            self.logger.error(f"❌ 신호 신뢰도 계산 실패: {e}")
            return 0.5

    def _build_phase1_final_signal(self, consensus_score: float, consensus_reached: bool,
                                  mtf_score: float, mtf_confluence: bool,
                                  liquidity_pass: bool, news_pass: bool, current_regime: str,
                                  final_signal_strength: float, signal_confidence: float,
                                  strategy_results: Dict, market_condition: MarketCondition,
                                  symbol: str) -> Dict[str, Any]:
        """Phase 1 최종 신호 구성"""
        try:
            # 신호 타입 결정
            all_gates_pass = liquidity_pass and news_pass
            high_quality = consensus_reached and mtf_confluence and all_gates_pass
            
            if not all_gates_pass:
                signal_type = 'HOLD'
                action = 'HOLD'
            elif high_quality and final_signal_strength > 70:
                signal_type = 'STRONG_BUY' if final_signal_strength > 80 else 'BUY'
                action = 'BUY'
            elif high_quality and final_signal_strength < 30:
                signal_type = 'STRONG_SELL' if final_signal_strength < 20 else 'SELL'
                action = 'SELL'
            elif final_signal_strength > 60:
                signal_type = 'WEAK_BUY'
                action = 'HOLD'  # 약한 신호는 보수적으로
            elif final_signal_strength < 40:
                signal_type = 'WEAK_SELL'
                action = 'HOLD'  # 약한 신호는 보수적으로
            else:
                signal_type = 'HOLD'
                action = 'HOLD'
            
            # Phase 1 품질 정보
            phase1_quality = {
                'consensus_score': round(consensus_score, 3),
                'consensus_reached': consensus_reached,
                'mtf_score': round(mtf_score, 3),
                'mtf_confluence': mtf_confluence,
                'liquidity_gate_passed': liquidity_pass,
                'news_gate_passed': news_pass,
                'current_regime': current_regime,
                'all_gates_passed': all_gates_pass,
                'high_quality_signal': high_quality
            }
            
            # 리스크 레벨 결정
            if not all_gates_pass:
                risk_level = 'HIGH'
            elif high_quality and signal_confidence > 0.8:
                risk_level = 'LOW'
            else:
                risk_level = 'MEDIUM'
            
            # 포지션 사이징 팩터
            if action == 'HOLD':
                position_factor = 0.0
            elif high_quality:
                position_factor = min(0.8, signal_confidence)
            else:
                position_factor = min(0.4, signal_confidence * 0.6)
            
            return {
                'signal_strength': round(final_signal_strength, 1),
                'signal_type': signal_type,
                'action': action,
                'confidence': round(signal_confidence, 3),
                'position_sizing_factor': round(position_factor, 2),
                'details': {
                    'phase1_enhanced': True,
                    'market_condition': market_condition.value,
                    'strategy_count': len(strategy_results),
                    'phase1_quality': phase1_quality,
                    'regime_info': {
                        'current_regime': current_regime,
                        'regime_suitable': True  # 레짐은 신호 조정으로 처리됨
                    }
                },
                'risk_level': risk_level,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Phase 1 최종 신호 구성 실패: {e}")
            return self._create_default_signal()