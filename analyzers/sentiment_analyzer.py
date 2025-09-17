#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/sentiment_analyzer.py

실시간 시장 감정 분석기 (Gemini AI 기반 뉴스 분석 + 실시간 감정 분석)
"""

import numpy as np
from typing import Dict, Any, Optional, List
from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer
from dataclasses import dataclass
from enum import Enum

import asyncio
from datetime import datetime, timedelta
import aiohttp
import json


class SentimentType(Enum):
    """감정 유형"""
    VERY_POSITIVE = "VERY_POSITIVE"
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    VERY_NEGATIVE = "VERY_NEGATIVE"


class ConfidenceLevel(Enum):
    """신뢰도 수준"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RealTimeSentimentData:
    """실시간 감정 분석 데이터"""
    sentiment_type: SentimentType
    confidence: float  # 0.0 - 1.0
    confidence_level: ConfidenceLevel
    score: float  # -1.0 ~ 1.0 (부정 ~ 긍정)
    source: str
    timestamp: datetime
    keywords: List[str]
    context: Dict[str, Any]


@dataclass
class MarketSentiment:
    """시장 전체 감정"""
    overall_sentiment: SentimentType
    overall_score: float  # -1.0 ~ 1.0
    confidence: float
    bullish_ratio: float  # 강세 비율
    bearish_ratio: float  # 약세 비율
    neutral_ratio: float  # 중립 비율
    news_sentiment: RealTimeSentimentData
    social_sentiment: RealTimeSentimentData
    trading_sentiment: RealTimeSentimentData
    timestamp: datetime
    analysis_period: str

class SentimentAnalyzer:
    """실시간 시장 감정 분석기 (Gemini AI 기반 뉴스 분석 + 실시간 감정 분석)"""
    
    # 전역 GeminiAnalyzer 인스턴스 (토큰 상태 공유를 위해)
    _shared_gemini_analyzer = None
    
    # Gemini 사용 불가 플래그 (세션 전체에서 공유)
    _gemini_unavailable = False
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("SentimentAnalyzer")
        self.session = None
        
        # 감정 분석 키워드
        self.positive_keywords = [
            "상승", "급등", "호재", "긍정", "매수", "강세", "돌파", "랠리", 
            "성장", "확대", "증가", "개선", "혁신", "기대", "투자"
        ]
        
        self.negative_keywords = [
            "하락", "급락", "악재", "부정", "매도", "약세", "붕괴", "폭락",
            "감소", "악화", "리스크", "우려", "위험", "손실", "하향"
        ]
        
        # 가중치 설정
        self.weights = {
            'news': 0.4,      # 뉴스 40%
            'social': 0.3,    # 소셜미디어 30%
            'trading': 0.3    # 거래 데이터 30%
        }

    async def _ensure_gemini_analyzer(self):
        """전역 GeminiAnalyzer 인스턴스 재사용 (토큰 상태 공유)"""
        if SentimentAnalyzer._shared_gemini_analyzer is None:
            from analyzers.gemini_analyzer import GeminiAnalyzer
            SentimentAnalyzer._shared_gemini_analyzer = GeminiAnalyzer(self.config)
            self.logger.debug("🔄 새로운 GeminiAnalyzer 인스턴스 생성 (전역 공유)")
        self.gemini_analyzer = SentimentAnalyzer._shared_gemini_analyzer
        
        # GPT 분석기도 초기화
        if not hasattr(self, 'gpt_analyzer'):
            from analyzers.gpt_analyzer import GPTAnalyzer
            self.gpt_analyzer = GPTAnalyzer(self.config)

    async def analyze(self, symbol: str, name: str, news_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """감정 분석 실행 (재료 관점 분석) - 설정에 따라 GPT 우선 또는 Gemini 우선"""
        await self._ensure_gemini_analyzer()
        
        if not news_data:
            self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 중립 분석 사용")
            return self._get_default_result()

        # 설정에서 주요 분석기 확인
        primary_analyzer = self.config.llm.PRIMARY_ANALYZER.lower() if hasattr(self.config, 'llm') else 'gpt'
        fallback_analyzer = self.config.llm.FALLBACK_ANALYZER.lower() if hasattr(self.config, 'llm') else 'gemini'
        
        # 1단계: 주요 분석기 시도
        if primary_analyzer == 'gpt':
            try:
                self.logger.info(f"🔄 {symbol} GPT로 감성 분석 실행 (주요 분석기)")
                gpt_analysis_result = await self.gpt_analyzer.analyze_news_sentiment(symbol, name, news_data)
                final_result = self._compile_final_result(gpt_analysis_result, len(news_data))
                self.logger.info(f"✅ {symbol} GPT 재료 분석 완료 - 최종 점수: {final_result['overall_score']:.1f}")
                return final_result
                
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} GPT 감정 분석 실패: {e} - {fallback_analyzer.upper()}로 대체 시도")
                
                # 2단계: 백업 분석기 시도 (Gemini)
                if fallback_analyzer == 'gemini' and not SentimentAnalyzer._gemini_unavailable:
                    try:
                        analysis_result = await self.gemini_analyzer.analyze_news_sentiment(symbol, name, news_data)
                        final_result = self._compile_final_result(analysis_result, len(news_data))
                        self.logger.info(f"✅ {symbol} Gemini 백업 분석 완료 - 최종 점수: {final_result['overall_score']:.1f}")
                        return final_result
                        
                    except Exception as gemini_error:
                        self.logger.error(f"❌ {symbol} Gemini 백업 분석도 실패: {gemini_error} - 기본값 사용")
                        SentimentAnalyzer._gemini_unavailable = True
                
        else:  # primary_analyzer == 'gemini'
            # Gemini 할당량 소진 상태 확인
            if SentimentAnalyzer._gemini_unavailable:
                self.logger.info(f"⚠️ {symbol} Gemini 사용불가 - GPT로 직접 분석")
            else:
                try:
                    self.logger.info(f"🔄 {symbol} Gemini로 감성 분석 실행 (주요 분석기)")
                    analysis_result = await self.gemini_analyzer.analyze_news_sentiment(symbol, name, news_data)
                    
                    # Gemini 분석이 기본값(50점)만 반환하거나 할당량 소진 상태인지 확인
                    short_score = analysis_result.get('short_term', {}).get('score', 50)
                    mid_score = analysis_result.get('mid_term', {}).get('score', 50)
                    long_score = analysis_result.get('long_term', {}).get('score', 50)
                    
                    # 할당량 소진 상태이거나 모든 점수가 50점이면 GPT로 대체
                    gemini_exhausted = self.gemini_analyzer.quota_exhausted if hasattr(self.gemini_analyzer, 'quota_exhausted') else False
                    all_default_scores = (short_score == 50 and mid_score == 50 and long_score == 50)
                    
                    if gemini_exhausted or all_default_scores:
                        if gemini_exhausted:
                            if not SentimentAnalyzer._gemini_unavailable:
                                self.logger.warning(f"⚠️ {symbol} Gemini API 할당량 소진 - 세션 전체에서 GPT로 전환")
                            SentimentAnalyzer._gemini_unavailable = True
                        else:
                            self.logger.warning(f"⚠️ {symbol} Gemini 분석이 기본값만 반환 - GPT로 대체")
                        raise ValueError("Gemini unavailable or fallback detected")
                    
                    # 정상적인 Gemini 분석 결과
                    final_result = self._compile_final_result(analysis_result, len(news_data))
                    self.logger.info(f"✅ {symbol} Gemini 재료 분석 완료 - 최종 점수: {final_result['overall_score']:.1f}")
                    return final_result
                    
                except Exception as e:
                    if not SentimentAnalyzer._gemini_unavailable:
                        self.logger.warning(f"⚠️ {symbol} Gemini 감정 분석 실패: {e} - GPT로 대체 시도")
                    SentimentAnalyzer._gemini_unavailable = True
            
            # 2단계: 백업 분석기 시도 (GPT)
            if fallback_analyzer == 'gpt':
                try:
                    gpt_analysis_result = await self.gpt_analyzer.analyze_news_sentiment(symbol, name, news_data)
                    final_result = self._compile_final_result(gpt_analysis_result, len(news_data))
                    self.logger.info(f"✅ {symbol} GPT 백업 분석 완료 - 최종 점수: {final_result['overall_score']:.1f}")
                    return final_result
                    
                except Exception as gpt_error:
                    self.logger.error(f"❌ {symbol} GPT 백업 분석도 실패: {gpt_error} - 기본값 사용")
        
        # 모든 분석기 실패 시 기본값 반환
        self.logger.error(f"❌ {symbol} 모든 LLM 분석기 실패 - 기본값 사용")
        return self._get_default_result()

    def _compile_final_result(self, analysis_result: Dict, total_news_count: int) -> Dict:
        """각 재료별 분석 결과를 종합하여 최종 결과 생성"""
        # 가중치: 단기 > 중기 > 장기
        weights = {'short_term': 0.5, 'mid_term': 0.3, 'long_term': 0.2}
        
        short_term_res = analysis_result.get('short_term', {})
        mid_term_res = analysis_result.get('mid_term', {})
        long_term_res = analysis_result.get('long_term', {})

        # 가중 평균 점수 계산
        weighted_score = (
            short_term_res.get('score', 50) * weights['short_term'] +
            mid_term_res.get('score', 50) * weights['mid_term'] +
            long_term_res.get('score', 50) * weights['long_term']
        )

        # 종합 요약 생성
        summary = analysis_result.get('overall_summary', '종합 요약 없음')

        # DisplayUtils 호환성을 위해 period 키 추가
        short_term_res['period'] = '단기 재료 (1개월 이내)'
        mid_term_res['period'] = '중기 재료 (1~6개월)'
        long_term_res['period'] = '장기 재료 (6개월 이상)'

        return {
            'overall_score': weighted_score,
            'news_count': total_news_count,
            'summary': summary,
            'short_term_analysis': short_term_res,
            'mid_term_analysis': mid_term_res,
            'long_term_analysis': long_term_res,
            # 기존 포맷 호환성을 위한 필드
            'news_sentiment': 'positive' if weighted_score > 60 else 'negative' if weighted_score < 40 else 'neutral',
            'positive_factors': short_term_res.get('positive_factors', []),
            'negative_factors': short_term_res.get('negative_factors', []),
            'key_keywords': analysis_result.get('key_keywords', [])
        }

    def _get_default_result(self) -> Dict[str, Any]:
        """전체 분석 기본 결과"""
        default_period = {
            'score': 50, 'summary': '분석할 뉴스가 없습니다.', 
            'positive_factors': [], 'negative_factors': []
        }
        return {
            'overall_score': 50,
            'news_count': 0,
            'summary': '분석할 뉴스가 없습니다.',
            'short_term_analysis': {**default_period, 'period': '단기 재료'},
            'mid_term_analysis': {**default_period, 'period': '중기 재료'},
            'long_term_analysis': {**default_period, 'period': '장기 재료'},
            'news_sentiment': 'neutral',
            'positive_factors': [],
            'negative_factors': [],
            'key_keywords': []
        }
