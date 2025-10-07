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
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from utils.logger import get_logger
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.supply_demand_analyzer import SupplyDemandAnalyzer
from analyzers.chart_pattern_analyzer import ChartPatternAnalyzer
from analyzers.fundamental_analyzer import FundamentalAnalyzer
from analyzers.mtf_analyzer import MTFAnalyzer
from analyzers.consensus_engine import ConsensusEngine
from analyzers.multi_strategy_analyzer import MultiStrategyAnalyzer, StrategyWeight
from analyzers.technical_indicators import PriceData

class AnalysisEngine:
    """종합 분석 엔진 (2차 필터링)"""

    def __init__(self, config, data_collector=None, kis_collector=None):
        self.config = config
        self.logger = get_logger("AnalysisEngine")
        self.data_collector = data_collector

        self.technical_analyzer = TechnicalAnalyzer(config)
        self.sentiment_analyzer = SentimentAnalyzer(config)
        self.supply_demand_analyzer = SupplyDemandAnalyzer(config, kis_collector=kis_collector)
        self.chart_pattern_analyzer = ChartPatternAnalyzer(config)
        self.fundamental_analyzer = FundamentalAnalyzer(config)
        self.mtf_analyzer = MTFAnalyzer(config, data_collector=self.data_collector)
        self.consensus_engine = ConsensusEngine(config)

        self.logger.info("✅ 모든 하위 분석기 초기화 완료")

    async def analyze_comprehensive(self, symbol: str, name: str, stock_data: Dict, strategy: str = "momentum") -> Dict:
        start_time = time.time()
        self.logger.info(f"🚀 {symbol}({name}) 종합 분석 시작...")

        price_data, news_data = await self._gather_initial_data(symbol, name)
        tasks = self._create_analysis_tasks(symbol, name, stock_data, price_data, news_data, strategy)

        task_names = [task[0] for task in tasks]
        task_coroutines = [task[1] for task in tasks]
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)

        analysis_results = {}
        for i, task_name in enumerate(task_names):
            result = results[i]
            if isinstance(result, Exception):
                error_type = type(result).__name__
                error_msg = str(result) if str(result) else f"{error_type} occurred"
                self.logger.warning(f"⚠️ {symbol} {task_name} 분석 실패 [{error_type}]: {error_msg} - 해당 분석 제외")
                analysis_results[task_name] = self._get_empty_analysis(task_name)
            else:
                analysis_results[task_name] = self._process_successful_result(result, task_name, symbol)

        comprehensive_score, score_details = self.consensus_engine.synthesize(
            analysis_results, strategy
        )

        # 디버깅: 점수 분포 로깅
        self.logger.info(f"🔍 {symbol} 점수 상세:")
        self.logger.info(f"   최종점수: {comprehensive_score:.2f}")
        self.logger.info(f"   개별점수: {score_details.get('individual_scores', {})}")
        self.logger.info(f"   분석결과: {[(k, v.get('overall_score', v.get('technical_score', 'N/A'))) for k, v in analysis_results.items()]}")

        recommendation = self._determine_recommendation(comprehensive_score, analysis_results, score_details)
        execution_time = time.time() - start_time
        self.logger.info(f"✅ {symbol}({name}) 종합 분석 완료 (점수: {comprehensive_score:.2f}, 추천: {recommendation}) - 소요시간: {execution_time:.2f}초")

        return self._create_final_result(
            symbol, name, comprehensive_score, recommendation, analysis_results, 
            score_details, strategy, execution_time
        )

    async def _gather_initial_data(self, symbol: str, name: str) -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        price_data, news_data = None, None
        try:
            if self.data_collector:
                price_task = asyncio.wait_for(self.data_collector.get_ohlcv_data(symbol, 'D', 100), timeout=10.0)
                news_task = asyncio.wait_for(self.data_collector.get_news_data(symbol, name), timeout=5.0) if hasattr(self.data_collector, 'get_news_data') else asyncio.sleep(0, result=None)
                results = await asyncio.gather(price_task, news_task, return_exceptions=True)
                if not isinstance(results[0], Exception) and results[0]:
                    price_data = [{'date': item.date.strftime('%Y-%m-%d'), 'open': int(item.open), 'high': int(item.high), 'low': int(item.low), 'close': int(item.close), 'volume': int(item.volume)} for item in results[0]]
                    self.logger.info(f"📊 {symbol} 가격 데이터 수집: {len(price_data)}개")
                else:
                    if isinstance(results[0], Exception):
                        error_type = type(results[0]).__name__
                        error_msg = str(results[0]) if str(results[0]) else f"{error_type} occurred"
                    else:
                        error_type = "NoData"
                        error_msg = "데이터 없음"

                    if "HTTP session not initialized" in error_msg:
                        self.logger.error(f"❌ {symbol} KIS API 세션 미초기화 - 데이터 수집기 재초기화 필요")
                    elif "timeout" in error_msg.lower() or error_type == "TimeoutError":
                        self.logger.warning(f"⏰ {symbol} 가격 데이터 수집 타임아웃 [{error_type}]: 10초 초과")
                    else:
                        self.logger.warning(f"⚠️ {symbol} 가격 데이터 수집 실패 [{error_type}]: {error_msg}")
                if not isinstance(results[1], Exception) and results[1]:
                    news_data = results[1]
                    self.logger.info(f"📰 {symbol} 뉴스 데이터 수집: {len(news_data)}개")
                else:
                    error_msg = str(results[1]) if isinstance(results[1], Exception) else "데이터 없음"
                    if "timeout" in error_msg.lower():
                        self.logger.warning(f"⏰ {symbol} 뉴스 데이터 수집 타임아웃 (5초 초과)")
                    else:
                        self.logger.debug(f"ℹ️ {symbol} 뉴스 데이터 수집 실패: {error_msg}")
        except Exception as e:
            self.logger.error(f"❌ 초기 데이터 수집 중 오류 발생: {e}")
        return price_data, news_data

    def _create_analysis_tasks(self, symbol: str, name: str, stock_data: Dict, price_data: Optional[List[Dict]], news_data: Optional[List[Dict]], strategy: str) -> List[Tuple[str, asyncio.Task]]:
        tasks = []
        if price_data:
            tasks.append(('technical', asyncio.wait_for(self.technical_analyzer.analyze_stock(symbol, price_data), timeout=15.0)))
            tasks.append(('chart_pattern', self.chart_pattern_analyzer.analyze_with_ohlcv(stock_data, price_data)))
            tasks.append(('mtf', asyncio.wait_for(self.mtf_analyzer.analyze(symbol, price_data), timeout=20.0)))
        
        # Correctly call the sentiment analyzer
        if news_data:
            tasks.append(('sentiment', asyncio.wait_for(self.sentiment_analyzer.analyze(symbol, name, news_data), timeout=30.0)))
        else:
            # If no news, add a task that returns a default neutral result
            async def empty_sentiment_task():
                return self.sentiment_analyzer._get_default_result()
            tasks.append(('sentiment', asyncio.create_task(empty_sentiment_task())))

        tasks.append(('supply_demand', asyncio.wait_for(self.supply_demand_analyzer.analyze(stock_data), timeout=10.0)))
        tasks.append(('fundamental', asyncio.wait_for(self.fundamental_analyzer.analyze(stock_data), timeout=5.0)))
        return tasks

    def _process_successful_result(self, result: Any, task_name: str, symbol: str) -> Dict:
        if hasattr(result, 'final_score'):
            return {
                'score': float(result.final_score),
                'confidence': float(result.final_confidence) / 100.0,
                'reasoning': getattr(result, 'consensus_analysis', ''),
                'recommendation': getattr(result, 'recommendation', 'HOLD'),
                'timestamp': getattr(result, 'timestamp', datetime.now()),
                'execution_time': getattr(result, 'total_execution_time', 0.0),
                'error': getattr(result, 'error_message', None)
            }
        if isinstance(result, dict):
            return result
        if hasattr(result, '__dict__'):
            return result.__dict__
        self.logger.warning(f"⚠️ {symbol} {task_name} 분석 결과가 예상된 형식이 아닙니다: {type(result)}")
        return self._get_empty_analysis(task_name)

    def _convert_to_price_data_objects(self, price_data: Optional[List[Dict]]) -> Optional[List[PriceData]]:
        if not price_data: return None
        try:
            return [PriceData(timestamp=datetime.strptime(item['date'], '%Y-%m-%d'), open=float(item['open']), high=float(item['high']), low=float(item['low']), close=float(item['close']), volume=int(item['volume'])) for item in price_data]
        except Exception as e:
            self.logger.warning(f"PriceData 객체 변환 실패: {e}")
            return None

    def _create_final_result(self, symbol, name, comprehensive_score, recommendation, analysis_results, score_details, strategy, execution_time) -> Dict:
        result = {
            'symbol': symbol, 'name': name, 'comprehensive_score': round(comprehensive_score, 2),
            'recommendation': recommendation,
            'technical_score': self._safe_get_score(analysis_results.get('technical', {}), 'technical_score', 50),
            'sentiment_score': self._safe_get_score(analysis_results.get('sentiment', {}), 'overall_score', 50),
            'supply_demand_score': self._safe_get_score(analysis_results.get('supply_demand', {}), 'overall_score', 50),
            'chart_pattern_score': self._safe_get_score(analysis_results.get('chart_pattern', {}), 'overall_score', 50),
            'fundamental_score': self._safe_get_score(analysis_results.get('fundamental', {}), 'overall_score', 50),
            'mtf_score': self._safe_get_score(analysis_results.get('mtf', {}), 'mtf_score', 50),
            'technical_details': analysis_results.get('technical'),
            'sentiment_details': analysis_results.get('sentiment'),
            'supply_demand_details': analysis_results.get('supply_demand'),
            'chart_pattern_details': analysis_results.get('chart_pattern'),
            'mtf_details': analysis_results.get('mtf'),
            'score_details': score_details, 'strategy_used': strategy,
            'analysis_time': datetime.now().isoformat(),
            'execution_time_seconds': round(execution_time, 3),
            'confidence_level': self._calculate_confidence_level(analysis_results, score_details),
            'risk_assessment': self._assess_risk_level(analysis_results, comprehensive_score)
        }
        return result

    def _determine_recommendation(self, score: float, results: Dict, score_details: Dict = None) -> str:
        """
        개선된 추천 로직 - 더 엄격하고 균형잡힌 기준 적용
        """
        # 강력한 매수/매도 신호를 위한 추가 검증
        strong_supply = results.get('supply_demand', {}).get('overall_score', 50) > 80
        strong_pattern = results.get('chart_pattern', {}).get('overall_score', 50) > 80
        technical_strong = results.get('technical', {}).get('technical_score', 50) > 75
        
        # 다중 분석기의 일치도 확인
        high_scores = sum(1 for analyzer in ['technical', 'supply_demand', 'chart_pattern', 'sentiment'] 
                         if results.get(analyzer, {}).get('overall_score', 50) > 70 
                         or results.get(analyzer, {}).get('technical_score', 50) > 70)
        
        low_scores = sum(1 for analyzer in ['technical', 'supply_demand', 'chart_pattern', 'sentiment'] 
                        if results.get(analyzer, {}).get('overall_score', 50) < 40 
                        or results.get(analyzer, {}).get('technical_score', 50) < 40)
        
        # 완화된 기준 적용 - 더 많은 매수 기회 제공
        if score >= 92 and strong_supply and strong_pattern and technical_strong and high_scores >= 4:
            return "STRONG_BUY"
        elif score >= 78 and high_scores >= 2:  # 완화된 매수 기준: 85→78점, 3개→2개 분석기
            return "BUY"  
        elif score >= 68 and high_scores >= 1:  # 완화된 약매수 기준: 75→68점, 2개→1개 분석기
            return "WEAK_BUY"
        elif score >= 25 and score <= 75 and low_scores <= 2:  # 중립 범위 확대
            return "HOLD"
        elif score >= 15 and score < 25 and low_scores >= 2:    # 낮은 점수
            return "WEAK_SELL"
        else:
            return "SELL"

    def _get_empty_analysis(self, analyzer_name: str) -> Dict[str, Any]:
        """실패한 분석에 대해 보수적인 점수 반환"""
        return {'overall_score': 35.0, 'technical_score': 35.0, 'error': f'{analyzer_name} analysis failed'}

    def _calculate_synergy_effects(self, analysis_results: Dict) -> float: return 0.0
    def _calculate_consistency_bonus(self, analysis_results: Dict) -> float: return 0.0
    def _calculate_confidence_level(self, analysis_results: Dict, score_details: Dict) -> str: return "MEDIUM"
    def _assess_risk_level(self, analysis_results: Dict, comprehensive_score: float) -> str: return "MEDIUM"
    def _safe_get_score(self, analysis_data: Dict, score_key: str, default_score: float) -> float:
        score = analysis_data.get(score_key, default_score)
        return score if isinstance(score, (int, float)) and 0 <= score <= 100 else default_score
