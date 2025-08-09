#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/sentiment_analyzer.py

감정 분석기 (Gemini AI 기반 뉴스 분석)
"""

import numpy as np
from typing import Dict, Any, Optional, List
from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer

import asyncio
from datetime import datetime, timedelta

class SentimentAnalyzer:
    """Gemini AI 기반 감정 분석기 (장/중/단기 분석 기능 추가)"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("SentimentAnalyzer")
        self.gemini_analyzer = None

    async def _ensure_gemini_analyzer(self):
        if self.gemini_analyzer is None:
            from analyzers.gemini_analyzer import GeminiAnalyzer
            self.gemini_analyzer = GeminiAnalyzer(self.config)

    async def analyze(self, symbol: str, name: str, news_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """감정 분석 실행 (재료 관점 분석)"""
        await self._ensure_gemini_analyzer()
        try:
            if not news_data:
                self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 중립 분석 사용")
                return self._get_default_result()

            # Gemini에 모든 뉴스를 전달하여 단기/중기/장기 재료 분석 요청
            analysis_result = await self.gemini_analyzer.analyze_news_sentiment(
                symbol, name, news_data
            )

            # 최종 점수 및 요약 생성
            final_result = self._compile_final_result(analysis_result, len(news_data))
            
            self.logger.info(f"✅ {symbol} 재료 관점 감정 분석 완료 - 최종 점수: {final_result['overall_score']:.1f}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 감정 분석 실패: {e}")
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
