#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/analysis_engine.py

2차 필터링을 수행하는 종합 분석 엔진.
여러 분석기(기술, 감성, 수급, 차트 패턴)를 병렬로 호출하여 종합 점수를 산출합니다.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List

import numpy as np

from utils.logger import get_logger
# 각 분석기 모듈 임포트
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.supply_demand_analyzer import SupplyDemandAnalyzer
from analyzers.chart_pattern_analyzer import ChartPatternAnalyzer


class AnalysisEngine:
    """종합 분석 엔진 (2차 필터링)"""

    def __init__(self, config, data_collector=None):
        self.config = config
        self.logger = get_logger("AnalysisEngine")
        self.data_collector = data_collector

        # 각 분석기 초기화
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.sentiment_analyzer = SentimentAnalyzer(config)
        self.supply_demand_analyzer = SupplyDemandAnalyzer(config)
        self.chart_pattern_analyzer = ChartPatternAnalyzer(config)
        self.logger.info("✅ 모든 하위 분석기 초기화 완료")

    async def analyze_comprehensive(self, symbol: str, name: str, stock_data: Dict, strategy: str = "momentum") -> Dict:
        """
        종합 분석을 병렬로 수행하여 최종 점수와 추천 등급을 반환합니다.

        Args:
            symbol (str): 종목 코드
            name (str): 종목명
            stock_data (Dict): KIS API 등을 통해 수집된 현재 주식 데이터
            strategy (str): 적용할 전략명

        Returns:
            Dict: 종합 분석 결과
        """
        try:
            start_time = time.time()
            self.logger.info(f"🚀 {symbol}({name}) 종합 분석 시작...")

            # 1. 각 분석 작업을 비동기 태스크로 생성
            # 기술적 분석용 차트 데이터 수집 (실제 KIS API 사용)
            try:
                if self.data_collector:
                    price_data = await self.data_collector.get_ohlcv_data(symbol, 'D', 100)
                    if price_data:
                        # OHLCV 데이터를 분석기가 기대하는 형식으로 변환
                        price_data = [
                            {
                                'date': item.date.strftime('%Y-%m-%d'),
                                'open': int(item.open),
                                'high': int(item.high),
                                'low': int(item.low),
                                'close': int(item.close),
                                'volume': int(item.volume)
                            }
                            for item in price_data
                        ]
                        self.logger.info(f"📊 {symbol} 실제 가격 데이터 수집: {len(price_data)}개")
                    else:
                        self.logger.error(f"❌ {symbol} KIS API에서 가격 데이터를 가져올 수 없습니다")
                        return self._get_fallback_analysis('comprehensive', symbol=symbol, name=name)
                else:
                    self.logger.error(f"❌ 데이터 수집기가 초기화되지 않았습니다")
                    return self._get_fallback_analysis('comprehensive', symbol=symbol, name=name)
            except Exception as e:
                self.logger.error(f"❌ {symbol} 가격 데이터 수집 중 오류: {e}")
                return self._get_fallback_analysis('comprehensive', symbol=symbol, name=name)
            
            # 각 분석기가 비동기인지 확인하고 적절히 처리
            tasks = []
            
            # 기술적 분석 (비동기)
            tasks.append(('technical', self.technical_analyzer.analyze_stock(symbol, price_data)))
            
            # 감성 분석 (비동기)
            tasks.append(('sentiment', self.sentiment_analyzer.analyze(symbol, name)))
            
            # 수급 분석 (동기 -> 비동기 래퍼)
            tasks.append(('supply_demand', self._async_wrapper(self.supply_demand_analyzer.analyze, stock_data)))
            
            # 차트 패턴 분석 (비동기)
            tasks.append(('chart_pattern', self.chart_pattern_analyzer.analyze(stock_data)))

            # 2. 병렬 실행
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            # 3. 결과 매핑 및 예외 처리
            analysis_results = {}
            for i, (task_name, _) in enumerate(tasks):
                if isinstance(results[i], Exception):
                    self.logger.error(f"❌ {symbol} {task_name} 분석 중 오류: {results[i]}")
                    analysis_results[task_name] = self._get_fallback_analysis(task_name)
                else:
                    analysis_results[task_name] = results[i]

            # 4. 가중치에 따른 종합 점수 계산
            weights = self.config.analysis.WEIGHTS
            comprehensive_score = (
                analysis_results['technical'].get('technical_score', 50) * weights['technical'] +
                analysis_results['sentiment'].get('overall_score', 50) * weights['sentiment'] +
                analysis_results['supply_demand'].get('overall_score', 50) * weights['supply_demand'] +
                analysis_results['chart_pattern'].get('overall_score', 50) * weights['chart_pattern']
            )

            # 5. 최종 추천 등급 결정
            recommendation = self._determine_recommendation(comprehensive_score, analysis_results)
            
            execution_time = time.time() - start_time
            self.logger.info(f"✅ {symbol}({name}) 종합 분석 완료 (점수: {comprehensive_score:.2f}, 추천: {recommendation}) - 소요시간: {execution_time:.2f}초")

            # 6. 최종 결과 객체 반환 (AnalysisResult 테이블 스키마와 유사하게)
            return {
                'symbol': symbol,
                'name': name,
                'comprehensive_score': round(comprehensive_score, 2),
                'recommendation': recommendation,
                'technical_score': analysis_results['technical'].get('technical_score', 50),
                'sentiment_score': analysis_results['sentiment'].get('overall_score', 50),
                'supply_demand_score': analysis_results['supply_demand'].get('overall_score', 50),
                'chart_pattern_score': analysis_results['chart_pattern'].get('overall_score', 50),
                'technical_details': analysis_results['technical'],
                'sentiment_details': analysis_results['sentiment'],
                'supply_demand_details': analysis_results['supply_demand'],
                'chart_pattern_details': analysis_results['chart_pattern'],
                'weights_applied': weights,
                'analysis_time': datetime.now().isoformat(),
                'execution_time_seconds': round(execution_time, 3)
            }

        except Exception as e:
            self.logger.error(f"❌ {symbol} 종합 분석 중 치명적 오류: {e}")
            return self._get_fallback_analysis('comprehensive', symbol=symbol, name=name)

    def _determine_recommendation(self, score: float, results: Dict) -> str:
        """종합 점수와 세부 분석 결과를 바탕으로 최종 추천 등급을 결정합니다."""
        
        # 수급과 차트 패턴에서 긍정적 신호가 있는지 확인
        strong_supply = results['supply_demand'].get('overall_score', 50) > 75
        strong_pattern = results['chart_pattern'].get('overall_score', 50) > 75

        if score >= 85:
            return "STRONG_BUY"
        elif score >= 75:
            if strong_supply and strong_pattern:
                return "STRONG_BUY"
            return "BUY"
        elif score >= 60:
            return "HOLD"
        elif score <= 40:
            return "SELL"
        else:
            return "STRONG_SELL"

    def _get_fallback_analysis(self, analyzer_name: str, symbol: str = "N/A", name: str = "N/A") -> Dict[str, Any]:
        """분석 실패 시 반환할 기본 결과 객체"""
        self.logger.warning(f"⚠️ {analyzer_name} 분석 실패. Fallback 데이터를 사용합니다.")
        if analyzer_name == 'technical':
            return {'technical_score': 50.0, 'signals': {'overall_signal': 'HOLD'}, 'confidence': 50.0}
        if analyzer_name == 'sentiment':
            return {'overall_score': 50.0, 'news_sentiment': 'neutral'}
        if analyzer_name == 'supply_demand':
            return {'overall_score': 50.0, 'supply_demand_balance': {'smart_money_dominance': False}}
        if analyzer_name == 'chart_pattern':
            return {'overall_score': 50.0, 'detected_patterns': []}
        if analyzer_name == 'comprehensive':
            return {
                'symbol': symbol, 'name': name, 'comprehensive_score': 50.0, 'recommendation': 'HOLD',
                'technical_details': self._get_fallback_analysis('technical'),
                'sentiment_details': self._get_fallback_analysis('sentiment'),
                'supply_demand_details': self._get_fallback_analysis('supply_demand'),
                'chart_pattern_details': self._get_fallback_analysis('chart_pattern'),
                'error': 'Comprehensive analysis failed'
            }
        return {}
    
    async def _async_wrapper(self, sync_func, *args, **kwargs):
        """동기 함수를 비동기로 래핑"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, sync_func, *args, **kwargs)
        except Exception as e:
            self.logger.warning(f"⚠️ {sync_func.__name__} 분석 실패: {e}")
            return {'overall_score': 50.0, 'error': str(e)}
    
    async def _get_real_trading_data(self, symbol: str) -> Optional[Dict]:
        """실제 KIS API에서 매매동향 데이터 조회"""
        try:
            if not self.data_collector:
                return None
                
            # 실제 KIS API 호출로 외국인/기관/개인 매매동향 조회
            # TODO: KIS API에 실제 매매동향 API가 있다면 구현
            # 현재는 None 반환하여 분석기에서 적절히 처리하도록 함
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 매매동향 데이터 조회 실패: {e}")
            return None
