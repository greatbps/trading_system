#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-LLM Integration System
===========================

Phase 8 핵심 기능: 여러 AI 모델을 동시에 활용한 종합 분석 시스템

주요 기능:
- Gemini, GPT, Claude API 통합 관리
- 모델별 특화 분석 및 결과 종합
- 신뢰도 가중치 기반 최종 판단
- 모델별 장단점 활용 최적화

작성일: 2025-08-12
Phase: 8.1 - Multi-LLM Integration
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import statistics
from concurrent.futures import ThreadPoolExecutor

from analyzers.gemini_analyzer import GeminiAnalyzer
from analyzers.gpt_analyzer import GPTAnalyzer
from analyzers.technical_indicators import PriceData
from utils.logger import get_logger


class LLMModel(Enum):
    """지원 LLM 모델 타입"""
    GEMINI = "gemini"
    GPT = "gpt"
    CLAUDE = "claude"


@dataclass
class LLMAnalysisResult:
    """개별 LLM 분석 결과"""
    model: LLMModel
    analysis_text: str
    buy_score: float  # 0-100 매수 점수
    confidence: float  # 0-100 신뢰도
    reasoning: str  # 분석 근거
    timestamp: datetime
    execution_time: float  # 실행 시간(초)
    success: bool = True
    error_message: str = None


@dataclass
class MultiLLMResult:
    """Multi-LLM 종합 분석 결과"""
    final_score: float  # 0-100 최종 매수 점수
    final_confidence: float  # 0-100 최종 신뢰도
    recommendation: str  # BUY/HOLD/SELL
    individual_results: List[LLMAnalysisResult]
    consensus_analysis: str  # 종합 분석 텍스트
    model_weights: Dict[LLMModel, float]  # 모델별 가중치
    total_execution_time: float
    timestamp: datetime


class MultiLLMAnalyzer:
    """
    Multi-LLM Integration Analyzer
    
    여러 AI 모델을 동시에 활용하여 종합적인 투자 분석 제공
    각 모델의 장점을 살려 신뢰도 높은 분석 결과 도출
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("MultiLLMAnalyzer")
        
        # 개별 분석기 초기화
        self.gemini_analyzer = GeminiAnalyzer(config)
        self.gpt_analyzer = GPTAnalyzer(config)
        self.claude_analyzer = None
        
        # 모델별 기본 가중치 (설정에 따라 동적 조정)
        primary_analyzer = getattr(config.llm, 'PRIMARY_ANALYZER', 'gpt').lower()
        if primary_analyzer == 'gpt':
            self.model_weights = {
                LLMModel.GPT: 1.0,     # GPT를 주요 분석기로 설정
                LLMModel.GEMINI: 0.9,   # Gemini는 백업
                LLMModel.CLAUDE: 0.0
            }
        else:
            self.model_weights = {
                LLMModel.GEMINI: 1.0,
                LLMModel.GPT: 0.9,     
                LLMModel.CLAUDE: 0.0
            }
        
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.gemini_timeout_threshold = getattr(config.llm, 'GEMINI_TIMEOUT_THRESHOLD', 30) # 초
        self.gpt_timeout_threshold = getattr(config.llm, 'GPT_TIMEOUT_THRESHOLD', 60) # 초
        self.gemini_failed_once = False # Gemini 타임아웃 발생 여부를 추적하는 플래그
        
        # 주요 분석기 설정
        self.primary_analyzer = primary_analyzer
        self.fallback_analyzer = getattr(config.llm, 'FALLBACK_ANALYZER', 'gemini').lower()

        self.logger.info(f"🧠 Multi-LLM Analyzer 초기화 완료 (Primary: {self.primary_analyzer}, Fallback: {self.fallback_analyzer})")
    
    async def analyze_comprehensive(
        self,
        symbol: str,
        name: str,
        stock_data: Dict,
        price_data: List[PriceData] = None,
        strategy: str = "comprehensive"
    ) -> MultiLLMResult:
        """
        Multi-LLM 종합 분석 실행 (설정에 따라 주요 분석기 우선)
        """
        start_time = datetime.now()
        try:
            self.logger.info(f"🧠 Multi-LLM 종합 분석 시작: {symbol}({name})")
            
            results = []
            primary_result = None
            fallback_result = None

            # 1단계: 주요 분석기 시도
            if self.primary_analyzer == 'gpt':
                try:
                    self.logger.info(f"🧠 Multi-LLM 종합 분석 시작: {symbol}({name}) - GPT")
                    gpt_task = self._analyze_with_model(
                        LLMModel.GPT, symbol, name, stock_data, price_data, strategy
                    )
                    primary_result = await asyncio.wait_for(gpt_task, timeout=self.gpt_timeout_threshold)
                    results.append(primary_result)
                    self.logger.info(f"✅ {symbol} GPT 분석 성공")
                except asyncio.TimeoutError:
                    self.logger.warning(f"시간초과 {symbol} GPT 분석 타임아웃 - {self.fallback_analyzer.upper()}로 대체 분석 시도...")
                    primary_timeout_result = LLMAnalysisResult(
                        model=LLMModel.GPT, analysis_text="Timeout", buy_score=50.0,
                        confidence=0.0, reasoning="GPT analysis timed out.",
                        timestamp=datetime.now(), execution_time=self.gpt_timeout_threshold, success=False, error_message="Timeout"
                    )
                    results.append(primary_timeout_result)
                except Exception as e:
                    self.logger.error(f"❌ {symbol} GPT 분석 실패: {e}")
                    primary_fail_result = LLMAnalysisResult(
                        model=LLMModel.GPT, analysis_text=f"분석 실패: {e}", buy_score=50.0,
                        confidence=0.0, reasoning=f"API 오류: {e}", timestamp=datetime.now(),
                        execution_time=0.0, success=False, error_message=str(e)
                    )
                    results.append(primary_fail_result)

            else:  # primary_analyzer == 'gemini'
                # Gemini 분석 시도 (이전에 실패하지 않은 경우에만)
                if not self.gemini_failed_once:
                    try:
                        self.logger.info(f"🧠 Multi-LLM 종합 분석 시작: {symbol}({name}) - Gemini")
                        gemini_task = self._analyze_with_model(
                            LLMModel.GEMINI, symbol, name, stock_data, price_data, strategy
                        )
                        primary_result = await asyncio.wait_for(gemini_task, timeout=self.gemini_timeout_threshold)
                        results.append(primary_result)
                        self.logger.info(f"✅ {symbol} Gemini 분석 성공")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"시간초과 {symbol} Gemini 분석 타임아웃 - GPT로 대체 분석 시도...")
                        self.gemini_failed_once = True # 타임아웃 시 플래그 설정
                        primary_timeout_result = LLMAnalysisResult(
                            model=LLMModel.GEMINI, analysis_text="Timeout", buy_score=50.0,
                            confidence=0.0, reasoning="Gemini analysis timed out.",
                            timestamp=datetime.now(), execution_time=self.gemini_timeout_threshold, success=False, error_message="Timeout"
                        )
                        results.append(primary_timeout_result)
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} Gemini 분석 실패: {e}")
                        self.gemini_failed_once = True # 다른 오류 시에도 플래그 설정
                        primary_fail_result = LLMAnalysisResult(
                            model=LLMModel.GEMINI, analysis_text=f"분석 실패: {e}", buy_score=50.0,
                            confidence=0.0, reasoning=f"API 오류: {e}", timestamp=datetime.now(),
                            execution_time=0.0, success=False, error_message=str(e)
                        )
                        results.append(primary_fail_result)
                else:
                    self.logger.info(f"⚠️ {symbol} Gemini 이전에 타임아웃/실패 발생, GPT로 바로 전환합니다.")

            # 2단계: 주요 분석기가 실패했거나 백업이 필요한 경우 백업 분석기 시도
            if primary_result is None:
                if self.fallback_analyzer == 'gpt':
                    try:
                        self.logger.info(f"🧠 Multi-LLM 종합 분석 시작: {symbol}({name}) - GPT")
                        gpt_task = self._analyze_with_model(
                            LLMModel.GPT, symbol, name, stock_data, price_data, strategy
                        )
                        fallback_result = await asyncio.wait_for(gpt_task, timeout=self.gpt_timeout_threshold)
                        results.append(fallback_result)
                        self.logger.info(f"✅ {symbol} GPT 대체 분석 성공")
                    except asyncio.TimeoutError:
                        self.logger.error(f"❌ {symbol} GPT 분석 타임아웃")
                        fallback_fail_result = LLMAnalysisResult(
                            model=LLMModel.GPT, analysis_text="Timeout", buy_score=50.0,
                            confidence=0.0, reasoning="GPT analysis timed out.",
                            timestamp=datetime.now(), execution_time=self.gpt_timeout_threshold, success=False, error_message="Timeout"
                        )
                        results.append(fallback_fail_result)
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} GPT 분석 실패: {e}")
                        fallback_fail_result = LLMAnalysisResult(
                            model=LLMModel.GPT, analysis_text=f"분석 실패: {e}", buy_score=50.0,
                            confidence=0.0, reasoning=f"API 오류: {e}", timestamp=datetime.now(),
                            execution_time=0.0, success=False, error_message=str(e)
                        )
                        results.append(fallback_fail_result)

                elif self.fallback_analyzer == 'gemini' and not self.gemini_failed_once:
                    try:
                        self.logger.info(f"🧠 Multi-LLM 종합 분석 시작: {symbol}({name}) - Gemini")
                        gemini_task = self._analyze_with_model(
                            LLMModel.GEMINI, symbol, name, stock_data, price_data, strategy
                        )
                        fallback_result = await asyncio.wait_for(gemini_task, timeout=self.gemini_timeout_threshold)
                        results.append(fallback_result)
                        self.logger.info(f"✅ {symbol} Gemini 백업 분석 성공")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"시간초과 {symbol} Gemini 백업 분석도 타임아웃")
                        self.gemini_failed_once = True
                        fallback_timeout_result = LLMAnalysisResult(
                            model=LLMModel.GEMINI, analysis_text="Timeout", buy_score=50.0,
                            confidence=0.0, reasoning="Gemini analysis timed out.",
                            timestamp=datetime.now(), execution_time=self.gemini_timeout_threshold, success=False, error_message="Timeout"
                        )
                        results.append(fallback_timeout_result)
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} Gemini 백업 분석 실패: {e}")
                        self.gemini_failed_once = True
                        fallback_fail_result = LLMAnalysisResult(
                            model=LLMModel.GEMINI, analysis_text=f"분석 실패: {e}", buy_score=50.0,
                            confidence=0.0, reasoning=f"API 오류: {e}", timestamp=datetime.now(),
                            execution_time=0.0, success=False, error_message=str(e)
                        )
                        results.append(fallback_fail_result)

            final_result = self._synthesize_results(results, symbol, name, start_time)
            
            self.logger.info(
                f"✅ Multi-LLM 분석 완료: {symbol} | 최종점수: {final_result.final_score:.1f}"
            )
            return final_result
            
        except Exception as e:
            self.logger.error(f"❌ Multi-LLM 분석 오류: {e}")
            return self._create_fallback_result(symbol, name, error=str(e))

    async def _analyze_with_model(
        self,
        model: LLMModel,
        symbol: str,
        name: str,
        stock_data: Dict,
        price_data: List[PriceData],
        strategy: str
    ) -> LLMAnalysisResult:
        start_time = datetime.now()
        try:
            if model == LLMModel.GEMINI and self.gemini_analyzer:
                analyzer = self.gemini_analyzer
            elif model == LLMModel.GPT and self.gpt_analyzer:
                analyzer = self.gpt_analyzer
            else:
                raise Exception(f"{model.value} 분석기가 초기화되지 않았습니다.")

            analysis_text = await analyzer.analyze_comprehensive(
                symbol=symbol, name=name, stock_data=stock_data,
                price_data=price_data, strategy=strategy
            )
            buy_score, confidence, reasoning = self._parse_llm_result(analysis_text)
            
            return LLMAnalysisResult(
                model=model, analysis_text=analysis_text, buy_score=buy_score,
                confidence=confidence, reasoning=reasoning, timestamp=datetime.now(),
                execution_time=(datetime.now() - start_time).total_seconds(), success=True
            )
        except Exception as e:
            raise e

    def _parse_llm_result(self, analysis_text: str) -> Tuple[float, float, str]:
        try:
            buy_score, confidence, reasoning = 50.0, 70.0, "일반적인 분석"
            if '{' in analysis_text and '}' in analysis_text:
                try:
                    json_str = analysis_text[analysis_text.find('{'):analysis_text.rfind('}')+1]
                    parsed = json.loads(json_str)
                    buy_score = float(parsed.get('buy_score', buy_score))
                    confidence = float(parsed.get('confidence', confidence))
                    reasoning = parsed.get('reasoning', reasoning)
                except (json.JSONDecodeError, TypeError): pass
            
            return max(0.0, min(100.0, buy_score)), max(0.0, min(100.0, confidence)), reasoning
        except Exception:
            return 50.0, 50.0, "파싱 오류"

    def _synthesize_results(
        self,
        individual_results: List[LLMAnalysisResult],
        symbol: str,
        name: str,
        start_time: datetime
    ) -> MultiLLMResult:
        successful_results = [r for r in individual_results if r.success]
        if not successful_results:
            return self._create_fallback_result(symbol, name, "모든 AI 분석 실패")
        
        final_score = statistics.mean([r.buy_score for r in successful_results])
        final_confidence = statistics.mean([r.confidence for r in successful_results])
        
        if final_score >= 70.0 and final_confidence >= 70.0: recommendation = "BUY"
        elif final_score <= 30.0 and final_confidence >= 70.0: recommendation = "SELL"
        else: recommendation = "HOLD"
        
        return MultiLLMResult(
            final_score=final_score, final_confidence=final_confidence, recommendation=recommendation,
            individual_results=individual_results,
            consensus_analysis=f"종합 분석 완료. 최종 점수: {final_score:.1f}",
            model_weights=self.model_weights.copy(),
            total_execution_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )

    def _create_fallback_result(self, symbol: str, name: str, error: str = None) -> MultiLLMResult:
        return MultiLLMResult(
            final_score=50.0, final_confidence=0.0, recommendation="HOLD", individual_results=[],
            consensus_analysis=f"❌ {symbol}({name}): Multi-LLM 분석 실패" + (f" - {error}" if error else ""),
            model_weights=self.model_weights.copy(), total_execution_time=0.0, timestamp=datetime.now()
        )

    def __del__(self):
        if hasattr(self, 'executor'): self.executor.shutdown(wait=False)