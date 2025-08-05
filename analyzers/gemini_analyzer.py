#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/gemini_analyzer.py

Google Gemini API를 활용한 뉴스 및 감성 분석기
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai

from utils.logger import get_logger
from config import Config


class GeminiAnalyzer:
    """Gemini AI를 활용한 뉴스 및 감성 분석기"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger("GeminiAnalyzer")
        
        # Gemini API 설정
        if config.api.GEMINI_API_KEY:
            genai.configure(api_key=config.api.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
            self.logger.info("✅ Gemini API 초기화 완료")
        else:
            self.model = None
            self.logger.warning("⚠️ GEMINI_API_KEY가 설정되지 않았습니다. 기본 분석을 사용합니다.")
    
    async def analyze_news_sentiment(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """뉴스 데이터를 바탕으로 감성 분석 수행"""
        if not self.model or not news_data:
            return self._get_default_sentiment()
        
        try:
            # 뉴스 텍스트 준비
            news_texts = []
            for news in news_data[:10]:  # 최근 10개 뉴스만 분석
                title = news.get('title', '')
                description = news.get('description', '')
                news_texts.append(f"제목: {title}\n내용: {description}")
            
            news_content = "\n\n".join(news_texts)
            
            # Gemini 프롬프트 생성
            prompt = self._create_sentiment_prompt(symbol, company_name, news_content)
            
            # Gemini API 호출
            response = await self._call_gemini_api(prompt)
            
            # 응답 파싱
            sentiment_result = self._parse_sentiment_response(response)
            
            self.logger.info(f"✅ Gemini 감성 분석 완료 - {symbol}: {sentiment_result.get('sentiment', 'NEUTRAL')}")
            return sentiment_result
            
        except Exception as e:
            self.logger.error(f"❌ Gemini 감성 분석 실패: {e}")
            return self._get_default_sentiment()
    
    async def analyze_market_impact(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """뉴스가 주가에 미치는 영향도 분석"""
        if not self.model or not news_data:
            return self._get_default_impact()
        
        try:
            # 주요 뉴스만 선별
            important_news = [news for news in news_data[:5] if self._is_important_news(news)]
            
            if not important_news:
                return self._get_default_impact()
            
            news_content = "\n\n".join([
                f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}"
                for news in important_news
            ])
            
            # 시장 영향도 분석 프롬프트
            prompt = self._create_impact_prompt(symbol, company_name, news_content)
            
            # Gemini API 호출
            response = await self._call_gemini_api(prompt)
            
            # 응답 파싱
            impact_result = self._parse_impact_response(response)
            
            self.logger.info(f"✅ Gemini 시장 영향도 분석 완료 - {symbol}: {impact_result.get('impact_level', 'MEDIUM')}")
            return impact_result
            
        except Exception as e:
            self.logger.error(f"❌ Gemini 시장 영향도 분석 실패: {e}")
            return self._get_default_impact()
    
    def _create_sentiment_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """감성 분석용 프롬프트 생성"""
        return f"""
주식 투자 분석가로서 다음 뉴스들을 분석하여 해당 기업의 주가에 대한 감성을 평가해주세요.

기업 정보:
- 종목코드: {symbol}
- 기업명: {company_name}

뉴스 내용:
{news_content}

다음 JSON 형식으로 분석 결과를 제공해주세요:
{{
    "sentiment": "VERY_POSITIVE|POSITIVE|NEUTRAL|NEGATIVE|VERY_NEGATIVE",
    "confidence": 0.0-1.0,
    "overall_score": 0-100,
    "positive_factors": ["긍정 요인들"],
    "negative_factors": ["부정 요인들"],
    "key_keywords": ["핵심 키워드들"],
    "short_term_outlook": "단기 전망 (1-2주)",
    "medium_term_outlook": "중기 전망 (1-3개월)",
    "summary": "한줄 요약"
}}

분석 기준:
- VERY_POSITIVE (90-100점): 매우 강한 호재, 즉시 주가 상승 기대
- POSITIVE (70-89점): 명확한 호재, 주가 상승 가능성 높음
- NEUTRAL (40-69점): 중립적, 큰 영향 없음
- NEGATIVE (20-39점): 악재, 주가 하락 우려
- VERY_NEGATIVE (0-19점): 매우 강한 악재, 즉시 주가 하락 우려
"""
    
    def _create_impact_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """시장 영향도 분석용 프롬프트 생성"""
        return f"""
주식 시장 분석가로서 다음 뉴스가 해당 기업의 주가와 시장에 미치는 영향을 분석해주세요.

기업 정보:
- 종목코드: {symbol}  
- 기업명: {company_name}

뉴스 내용:
{news_content}

다음 JSON 형식으로 분석 결과를 제공해주세요:
{{
    "impact_level": "VERY_HIGH|HIGH|MEDIUM|LOW|VERY_LOW",
    "impact_score": 0-100,
    "duration": "IMMEDIATE|SHORT_TERM|MEDIUM_TERM|LONG_TERM",
    "price_direction": "STRONG_UP|UP|NEUTRAL|DOWN|STRONG_DOWN",
    "volatility_expected": "VERY_HIGH|HIGH|MEDIUM|LOW",
    "trading_volume_impact": "SURGE|INCREASE|NORMAL|DECREASE",
    "sector_impact": "업종에 미치는 영향",
    "key_risks": ["주요 리스크들"],
    "catalysts": ["상승 촉매들"],
    "target_price_change": "예상 주가 변동률 (%)",
    "recommendation": "BUY|HOLD|SELL"
}}

영향도 기준:
- VERY_HIGH: 즉시 10% 이상 주가 변동 예상
- HIGH: 1주일 내 5-10% 주가 변동 예상
- MEDIUM: 1개월 내 3-5% 주가 변동 예상
- LOW: 소폭 변동 또는 장기적 영향
- VERY_LOW: 거의 영향 없음
"""
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 비동기 호출"""
        try:
            # 동기 호출을 비동기로 래핑
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            return response.text
        except Exception as e:
            self.logger.error(f"❌ Gemini API 호출 실패: {e}")
            raise
    
    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """Gemini 감성 분석 응답 파싱"""
        try:
            # JSON 추출
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # 데이터 검증 및 정규화
                return {
                    'sentiment': result.get('sentiment', 'NEUTRAL'),
                    'confidence': max(0, min(1, float(result.get('confidence', 0.5)))),
                    'overall_score': max(0, min(100, int(result.get('overall_score', 50)))),
                    'positive_factors': result.get('positive_factors', []),
                    'negative_factors': result.get('negative_factors', []),
                    'key_keywords': result.get('key_keywords', []),
                    'short_term_outlook': result.get('short_term_outlook', ''),
                    'medium_term_outlook': result.get('medium_term_outlook', ''),
                    'summary': result.get('summary', ''),
                    'signal_strength': self._calculate_signal_strength(result),
                    'trend': self._determine_trend(result.get('sentiment', 'NEUTRAL'))
                }
            else:
                return self._get_default_sentiment()
                
        except Exception as e:
            self.logger.error(f"❌ 감성 분석 응답 파싱 실패: {e}")
            return self._get_default_sentiment()
    
    def _parse_impact_response(self, response: str) -> Dict[str, Any]:
        """Gemini 시장 영향도 분석 응답 파싱"""
        try:
            # JSON 추출
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                return {
                    'impact_level': result.get('impact_level', 'MEDIUM'),
                    'impact_score': max(0, min(100, int(result.get('impact_score', 50)))),
                    'duration': result.get('duration', 'MEDIUM_TERM'),
                    'price_direction': result.get('price_direction', 'NEUTRAL'),
                    'volatility_expected': result.get('volatility_expected', 'MEDIUM'),
                    'trading_volume_impact': result.get('trading_volume_impact', 'NORMAL'),
                    'sector_impact': result.get('sector_impact', ''),
                    'key_risks': result.get('key_risks', []),
                    'catalysts': result.get('catalysts', []),
                    'target_price_change': result.get('target_price_change', '0%'),
                    'recommendation': result.get('recommendation', 'HOLD')
                }
            else:
                return self._get_default_impact()
                
        except Exception as e:
            self.logger.error(f"❌ 시장 영향도 응답 파싱 실패: {e}")
            return self._get_default_impact()
    
    def _is_important_news(self, news: Dict) -> bool:
        """뉴스의 중요도 판단"""
        title = news.get('title', '').lower()
        description = news.get('description', '').lower()
        
        important_keywords = [
            '실적', '매출', '영업이익', '순이익', '배당', 
            '인수', '합병', 'm&a', '투자', '계약', '수주',
            '신제품', '신사업', '특허', '기술개발',
            '상장', '분할', '증자', '감자',
            '경영진', '대표이사', '이사회'
        ]
        
        for keyword in important_keywords:
            if keyword in title or keyword in description:
                return True
        
        return False
    
    def _calculate_signal_strength(self, result: Dict) -> float:
        """시그널 강도 계산"""
        sentiment = result.get('sentiment', 'NEUTRAL')
        confidence = result.get('confidence', 0.5)
        
        strength_map = {
            'VERY_POSITIVE': 0.9,
            'POSITIVE': 0.7,
            'NEUTRAL': 0.5,
            'NEGATIVE': 0.7,
            'VERY_NEGATIVE': 0.9
        }
        
        base_strength = strength_map.get(sentiment, 0.5)
        return base_strength * confidence
    
    def _determine_trend(self, sentiment: str) -> str:
        """트렌드 결정"""
        trend_map = {
            'VERY_POSITIVE': 'IMPROVING',
            'POSITIVE': 'IMPROVING',
            'NEUTRAL': 'STABLE',
            'NEGATIVE': 'DECLINING',
            'VERY_NEGATIVE': 'DECLINING'
        }
        return trend_map.get(sentiment, 'STABLE')
    
    def _get_default_sentiment(self) -> Dict[str, Any]:
        """기본 감성 분석 결과"""
        return {
            'sentiment': 'NEUTRAL',
            'confidence': 0.5,
            'overall_score': 50,
            'positive_factors': [],
            'negative_factors': [],
            'key_keywords': [],
            'short_term_outlook': '정보 부족으로 중립적 전망',
            'medium_term_outlook': '정보 부족으로 중립적 전망',
            'summary': 'AI 분석 정보 부족',
            'signal_strength': 50,
            'trend': 'STABLE'
        }
    
    def _get_default_impact(self) -> Dict[str, Any]:
        """기본 시장 영향도 분석 결과"""
        return {
            'impact_level': 'MEDIUM',
            'impact_score': 50,
            'duration': 'MEDIUM_TERM',
            'price_direction': 'NEUTRAL',
            'volatility_expected': 'MEDIUM',
            'trading_volume_impact': 'NORMAL',
            'sector_impact': '정보 부족',
            'key_risks': [],
            'catalysts': [],
            'target_price_change': '0%',
            'recommendation': 'HOLD'
        }