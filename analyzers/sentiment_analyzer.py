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

class SentimentAnalyzer:
    """Gemini AI 기반 감정 분석기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("SentimentAnalyzer")
        self.gemini_analyzer = None  # Initially None

    async def _ensure_gemini_analyzer(self):
        if self.gemini_analyzer is None:
            from analyzers.gemini_analyzer import GeminiAnalyzer
            self.gemini_analyzer = GeminiAnalyzer(self.config)

    async def analyze(self, symbol: str, name: str, news_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """감정 분석 실행"""
        await self._ensure_gemini_analyzer()
        try:
            if news_data and len(news_data) > 0:
                # Gemini AI를 사용한 실제 뉴스 분석
                sentiment_result = await self.gemini_analyzer.analyze_news_sentiment(
                    symbol, name, news_data
                )
                
                # 기존 포맷에 맞게 결과 변환
                result = self._convert_to_legacy_format(sentiment_result, len(news_data))
                
                self.logger.info(f"✅ Gemini 감정 분석 완료 - {symbol} 감정: {sentiment_result.get('sentiment', 'NEUTRAL')}")
                return result
            else:
                # 뉴스 데이터가 없을 때 기본값 (로그 레벨 낮춤)
                self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 중립 분석 사용")
                return self._get_default_result()
            
        except Exception as e:
            self.logger.error(f"❌ 감정 분석 실패: {e}")
            return self._get_default_result()
    
    def _convert_to_legacy_format(self, gemini_result: Dict, news_count: int) -> Dict[str, Any]:
        """Gemini 결과를 기존 포맷으로 변환"""
        # 감정을 숫자 점수로 변환
        sentiment_scores = {
            'VERY_POSITIVE': 90,
            'POSITIVE': 75,
            'NEUTRAL': 50,
            'NEGATIVE': 25,
            'VERY_NEGATIVE': 10
        }
        
        sentiment = gemini_result.get('sentiment', 'NEUTRAL')
        # Gemini에서 overall_score를 제공하지 않으면 sentiment를 기반으로 점수 계산
        overall_score = gemini_result.get('overall_score')
        if overall_score is None or overall_score == 50:
            overall_score = sentiment_scores.get(sentiment, 50)
        confidence = gemini_result.get('confidence', 0.5)
        
        # 신호 강도 계산
        signal_strength = overall_score * confidence
        
        # 긍정/부정 비율 계산
        positive_factors = len(gemini_result.get('positive_factors', []))
        negative_factors = len(gemini_result.get('negative_factors', []))
        total_factors = positive_factors + negative_factors
        
        if total_factors > 0:
            positive_ratio = positive_factors / total_factors
            negative_ratio = negative_factors / total_factors
        else:
            positive_ratio = 0.5
            negative_ratio = 0.5
        
        return {
            'overall_score': overall_score,
            'signal_strength': signal_strength,
            'confidence': confidence,
            'news_sentiment': sentiment.lower(),
            'news_count': news_count,
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'sentiment_score': (overall_score - 50) / 50,  # -1 to 1 범위로 변환
            'trend': gemini_result.get('trend', 'STABLE'),
            # Gemini 추가 정보
            'positive_factors': gemini_result.get('positive_factors', []),
            'negative_factors': gemini_result.get('negative_factors', []),
            'key_keywords': gemini_result.get('key_keywords', []),
            'short_term_outlook': gemini_result.get('short_term_outlook', ''),
            'medium_term_outlook': gemini_result.get('medium_term_outlook', ''),
            'summary': gemini_result.get('summary', '')
        }
    
    def _get_default_result(self) -> Dict[str, Any]:
        """기본 결과값"""
        return {
            'overall_score': 50,
            'signal_strength': 50,
            'confidence': 0.5,
            'news_sentiment': 'neutral',
            'news_count': 0,
            'positive_ratio': 0.5,
            'negative_ratio': 0.5,
            'sentiment_score': 0.0,
            'trend': 'STABLE',
            'positive_factors': [],
            'negative_factors': [],
            'key_keywords': [],
            'short_term_outlook': '정보 부족',
            'medium_term_outlook': '정보 부족',
            'summary': '뉴스 정보 부족으로 중립 판정'
        }