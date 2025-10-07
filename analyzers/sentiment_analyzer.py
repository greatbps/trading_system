#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/sentiment_analyzer.py

실시간 시장 감정 분석기 (Gemini AI 기반 뉴스 분석 + 실시간 감정 분석)
"""

import numpy as np
from typing import Dict, Any, Optional, List
from utils.logger import get_logger
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
    """실시간 시장 감정 분석기 (키워드 기반 뉴스 분석 + 실시간 감정 분석)"""
    
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
        """LLM 제거됨 - 더 이상 사용하지 않음"""
        pass

    async def analyze(self, symbol: str, name: str, news_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        감정 분석 실행 (키워드 기반)
        """

        if not news_data or len(news_data) == 0:
            self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 중립 분석 사용")
            return self._get_default_result()

        # 키워드 기반 분석만 사용
        return await self._try_keyword_analysis(symbol, name, news_data)

    async def _try_gemini_analysis(self, symbol: str, name: str, news_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """LLM 제거됨 - 더 이상 사용하지 않음"""
        return None

    async def _try_gpt_analysis(self, symbol: str, name: str, news_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """LLM 제거됨 - 더 이상 사용하지 않음"""
        try:
            return self._get_enhanced_fallback_analysis(symbol, name, news_data)
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['quota', 'limit', 'exceeded', 'rate', 'usage', '429', 'billing']):
                self.logger.warning(f"⚠️ {symbol} 백업 분석 쿼터 초과")
                return self._get_enhanced_fallback_analysis(symbol, name, news_data)
            else:
                self.logger.warning(f"⚠️ {symbol} GPT 분석 오류: {e}")
                return None

    async def _try_keyword_analysis(self, symbol: str, name: str, news_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """키워드 기반 간단 분석 (AI API 모두 실패시 사용) - 향상된 백업 분석"""
        self.logger.info(f"🔍 {symbol} 키워드 기반 감성분석 실행 (향상된 백업 분석)")
        return self._get_enhanced_fallback_analysis(symbol, name, news_data)


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

    @classmethod
    def get_gemini_status(cls) -> Dict[str, Any]:
        """LLM 제거됨 - 기본 상태 반환"""
        return {
            "api_available": False,
            "quota_exhausted": False,
            "gemini_analyzer_available": False,
            "gemini_unavailable_flag": True
        }

    def _get_enhanced_fallback_analysis(self, symbol: str, name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """API 쿼터 초과 시 향상된 백업 감성 분석"""
        from datetime import datetime
        import re

        news_count = len(news_data) if news_data else 0
        current_hour = datetime.now().hour

        # 시간대별 기본 점수 설정
        if 9 <= current_hour <= 15:  # 장중
            base_score = 47  # 보수적
            time_context = "장중"
        elif 8 <= current_hour <= 9 or 15 <= current_hour <= 16:  # 장 전후
            base_score = 49
            time_context = "장 전후"
        else:
            base_score = 50
            time_context = "장외"

        # 뉴스 제목에서 간단한 키워드 분석
        positive_keywords = ['상승', '증가', '성장', '확대', '호재', '급등', '강세', '개선', '성공']
        negative_keywords = ['하락', '감소', '축소', '악재', '급락', '약세', '우려', '위험', '부진', '실패']

        positive_count = 0
        negative_count = 0
        key_keywords = []

        if news_data:
            for news in news_data:
                title = news.get('title', '') + ' ' + news.get('content', '')
                title_lower = title.lower()

                for keyword in positive_keywords:
                    if keyword in title_lower:
                        positive_count += 1
                        if keyword not in key_keywords:
                            key_keywords.append(keyword)

                for keyword in negative_keywords:
                    if keyword in title_lower:
                        negative_count += 1
                        if keyword not in key_keywords:
                            key_keywords.append(keyword)

        # 키워드 기반 점수 보정
        if positive_count > negative_count:
            score_adjustment = min(3, positive_count - negative_count)
            sentiment_direction = "긍정적 키워드 우세"
        elif negative_count > positive_count:
            score_adjustment = -min(3, negative_count - positive_count)
            sentiment_direction = "부정적 키워드 우세"
        else:
            score_adjustment = 0
            sentiment_direction = "중립적 키워드 균형"

        final_score = max(30, min(70, base_score + score_adjustment))

        analysis_summary = f"API 제한으로 기본 분석 사용 - {sentiment_direction} ({time_context})"

        return {
            'overall_score': final_score,
            'news_count': news_count,
            'summary': analysis_summary,
            'short_term_analysis': {
                'score': final_score,
                'summary': analysis_summary,
                'positive_factors': key_keywords[:3] if positive_count > 0 else ['시장 기본 전망'],
                'negative_factors': key_keywords[-2:] if negative_count > 0 else ['API 제한으로 상세 분석 불가'],
                'period': '단기 재료'
            },
            'mid_term_analysis': {
                'score': final_score,
                'summary': analysis_summary,
                'positive_factors': ['기본 시장 동향'] + (key_keywords[:2] if positive_count > 0 else []),
                'negative_factors': ['상세 분석 제한'] + (key_keywords[-1:] if negative_count > 0 else []),
                'period': '중기 재료'
            },
            'long_term_analysis': {
                'score': final_score,
                'summary': f"장기 전망 - {sentiment_direction}",
                'positive_factors': ['장기 기본 추세'],
                'negative_factors': ['정보 부족으로 보수적 접근'],
                'period': '장기 재료'
            },
            'news_sentiment': 'positive' if final_score > 52 else 'negative' if final_score < 48 else 'neutral',
            'positive_factors': key_keywords[:3] if positive_count > 0 else ['기본 전망'],
            'negative_factors': key_keywords[-2:] if negative_count > 0 else ['API 제한'],
            'key_keywords': key_keywords[:5] if key_keywords else ['API제한', '기본분석'],
            'fallback_analysis': True,
            'analysis_limitation': f'API 할당량 초과로 키워드 기반 백업 분석 사용 (뉴스 {news_count}개 분석)'
        }

    @classmethod
    def reset_gemini_status(cls):
        """LLM 제거됨 - 더 이상 사용하지 않음"""
        return "LLM 분석이 제거되었습니다."
