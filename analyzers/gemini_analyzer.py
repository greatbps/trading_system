#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/gemini_analyzer_improved.py

개선된 Gemini API 기반 뉴스 및 감성 분석기
"""

import asyncio
import json
import re
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from utils.logger import get_logger

def safe_get_data(data, key: str, default=None):
    """객체 또는 dict에서 안전하게 값을 가져오는 유틸리티 함수"""
    if hasattr(data, key):
        return getattr(data, key, default)
    elif isinstance(data, dict):
        return data.get(key, default)
    else:
        return default
from config import Config


class GeminiAnalyzer:
    """Google Gemini API를 활용한 뉴스 및 감성 분석기"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger("GeminiAnalyzer")
        self.model = None
        self.api_available = False

        # 할당량 추적 변수 추가
        self.quota_exhausted = False
        self.last_quota_check = 0
        self.quota_check_interval = 86400  # 24시간마다 체크 (일일 할당량)

        # Gemini API 모듈 사용 가능성 체크
        if not GEMINI_AVAILABLE:
            self.logger.warning("⚠️ Google Generative AI 모듈이 설치되지 않음")
            self.api_available = False
            return

        # Google API 키 설정 - .env 파일 강제 재로드
        from dotenv import load_dotenv
        load_dotenv(override=True)

        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # 사용 가능한 모델들을 순서대로 시도
                models_to_try = ['gemini-1.5-flash-latest', 'gemini-1.5-flash-001', 'gemini-1.5-flash-002', 'gemini-1.5-pro-latest', 'gemini-1.5-pro-001', 'gemini-1.5-pro-002', 'gemini-pro', 'models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash-001', 'models/gemini-1.5-pro-latest']

                for model_name in models_to_try:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        self.api_available = True
                        self.logger.info(f"✅ Gemini API 클라이언트 초기화 완료 (모델: {model_name})")
                        break
                    except Exception as model_error:
                        self.logger.warning(f"⚠️ {model_name} 모델 초기화 실패: {model_error}")
                        continue

                if not self.api_available:
                    self.logger.error("❌ 모든 Gemini 모델 초기화 실패")

            except Exception as e:
                self.logger.error(f"❌ Gemini API 클라이언트 초기화 실패: {e}")
                self.api_available = False
        else:
            self.logger.warning("⚠️ Google API 키가 설정되지 않음")
            self.api_available = False

    async def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 호출 (할당량 추적 포함)"""
        if not self.api_available:
            raise Exception("Gemini API를 사용할 수 없습니다")

        # 할당량 소진 확인
        import time
        current_time = time.time()
        if self.quota_exhausted:
            # 24시간 경과했으면 재시도
            if current_time - self.last_quota_check > self.quota_check_interval:
                self.logger.info("🔄 Gemini API 할당량 재체크 시간 - 상태 초기화하여 재시도")
                self.quota_exhausted = False
            else:
                remaining_hours = int((self.quota_check_interval - (current_time - self.last_quota_check)) / 3600)
                remaining_minutes = int(((self.quota_check_interval - (current_time - self.last_quota_check)) % 3600) / 60)
                raise Exception(f"Gemini API 할당량 소진됨 (다음 재시도: {remaining_hours}시간 {remaining_minutes}분 후)")

        try:
            # 비동기 처리를 위해 ThreadPoolExecutor 사용
            import concurrent.futures
            import asyncio

            def _sync_generate():
                response = self.model.generate_content(prompt)
                return response.text.strip()

            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, _sync_generate)
                return result

        except Exception as e:
            error_msg = str(e).lower()

            # API 키 관련 에러 감지 및 처리
            if any(keyword in error_msg for keyword in ['api_key_invalid', 'expired', 'api key', 'invalid']):
                self.logger.error(f"❌ Gemini API 키 문제 감지: {e}")
                self.logger.error("🔑 Google API 키를 확인하거나 갱신해주세요.")
                self.api_available = False  # API 사용 불가능으로 표시

            # 할당량 관련 에러 감지 및 더 구체적인 메시지 추가
            elif any(keyword in error_msg for keyword in ['quota', 'limit', 'exceeded', 'rate', 'usage', '429', 'billing']):
                self.logger.warning(f"⚠️ Gemini API 할당량 소진 감지: {e}")
                self.quota_exhausted = True
                self.last_quota_check = current_time
                # 할당량 소진 시 즉시 대안 사용 안내
                self.logger.info("💡 Gemini 분석 대신 GPT 또는 기본 분석을 사용합니다")

            # 모델 접근 권한 문제
            elif any(keyword in error_msg for keyword in ['not found', '404', 'access', 'permission']):
                self.logger.error(f"❌ Gemini 모델 접근 권한 문제: {e}")
                self.logger.info("💡 다른 Gemini 모델 또는 대안 분석을 사용합니다")

            self.logger.error(f"❌ Gemini API 호출 실패: {e}")
            raise

    async def analyze_market_impact(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """시장 영향도 분석 수행"""
        if not news_data:
            self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 기본 시장 영향도 분석 사용")
            return self._get_default_market_impact()

        # 할당량 소진 시 즉시 기본값 반환
        if self.quota_exhausted:
            self.logger.warning(f"⚠️ Gemini API 할당량 소진으로 기본 분석 사용: {symbol}")
            return self._get_default_market_impact()

        try:
            # 뉴스 텍스트 준비
            news_texts = []
            for news in news_data[:10]:  # 최대 10개 뉴스만 분석
                title = news.get('title', '')
                description = news.get('description', '')
                news_texts.append(f"제목: {title}\n내용: {description}")

            news_content = "\n\n".join(news_texts)

            # Gemini용 프롬프트 구성
            prompt = self._build_market_impact_prompt(symbol, company_name, news_content)

            # Gemini API 호출
            response = await self._call_gemini_api(prompt)

            # JSON 응답 파싱
            result = self._parse_market_impact_response(response)

            self.logger.info(f"✅ Gemini 시장 영향도 분석 완료 - {symbol}: {result.get('impact_level', 'UNKNOWN')}")
            return result

        except Exception as e:
            self.logger.warning(f"⚠️ Gemini 시장 영향도 분석 실패 ({symbol}): {e}")
            return self._get_default_market_impact()

    async def analyze_news_sentiment(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """뉴스 감성 분석"""
        if not news_data:
            self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 기본 분석 사용")
            return self._get_default_sentiment()

        # 할당량 소진 시 즉시 기본값 반환
        if self.quota_exhausted:
            self.logger.warning(f"⚠️ Gemini API 할당량 소진으로 기본 분석 사용: {symbol}")
            return self._get_default_sentiment()

        try:
            # 뉴스 텍스트 준비
            news_texts = [f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}" for news in news_data]
            news_content = "\n\n".join(news_texts)

            self.logger.info(f"📰 {symbol} 뉴스 {len(news_data)}개로 Gemini 감성 분석 시작...")

            # Gemini용 통합 프롬프트 구성
            prompt = self._build_comprehensive_sentiment_prompt(symbol, company_name, news_content)

            # Gemini API 호출
            response = await self._call_gemini_api(prompt)

            # JSON 응답 파싱
            result = self._parse_comprehensive_sentiment_response(response)

            self.logger.info(f"✅ Gemini 통합 감성 분석 완료 - {symbol}: 단기={result.get('short_term', {}).get('score', 50)}, 중기={result.get('mid_term', {}).get('score', 50)}, 장기={result.get('long_term', {}).get('score', 50)}")
            return result

        except Exception as e:
            self.logger.warning(f"⚠️ Gemini 통합 감성 분석 실패 ({symbol}): {e}")
            return self._get_default_sentiment()

    def _build_market_impact_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """시장 영향도 분석용 프롬프트 구성"""
        return f"""
한국 주식 시장 전문가로서 다음 뉴스들이 {company_name}({symbol})의 시장에 미칠 영향을 분석해주세요.

뉴스 내용:
{news_content}

다음 JSON 형식으로 정확히 응답해주세요. JSON 외에 다른 텍스트는 포함하지 마세요.

{{
    "impact_level": "HIGH|MEDIUM|LOW",
    "impact_score": (0-100 숫자),
    "duration": "SHORT_TERM|MEDIUM_TERM|LONG_TERM",
    "price_direction": "UP|DOWN|NEUTRAL",
    "volatility_expected": "HIGH|MEDIUM|LOW",
    "trading_volume_impact": "INCREASE|DECREASE|NORMAL",
    "sector_impact": "섹터 영향 설명",
    "key_risks": ["리스크1", "리스크2"],
    "catalysts": ["촉매1", "촉매2"],
    "target_price_change": "예상 목표가 변동률 (예: +5%, -3%)",
    "recommendation": "BUY|HOLD|SELL"
}}

주의사항:
1. 모든 열거형 값은 정확히 지정된 값 중 선택해주세요
2. 한국 주식 시장과 해당 업종 특성을 고려해주세요
3. JSON 형식을 정확히 지켜주세요
4. 응답은 반드시 JSON 객체만 포함해야 합니다
"""

    def _build_comprehensive_sentiment_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """통합 감성 분석용 프롬프트 구성"""
        news_count = news_content.count('제목:') if news_content else 0

        return f"""You are a Korean stock market analyst. Analyze ALL the news for {company_name}({symbol}) and respond ONLY with JSON format.

IMPORTANT: Your response MUST be ONLY a valid JSON object. DO NOT include any other text.

News content ({news_count} articles):
{news_content}

Analyze each piece of news and categorize by impact timeline:
- SHORT_TERM (단기): 1 month or less impact
- MEDIUM_TERM (중기): 1-6 months impact
- LONG_TERM (장기): 6+ months impact

Required JSON response format:
{{
  "short_term": {{
    "score": 65,
    "summary": "Short-term investment outlook based on news analysis",
    "positive_factors": ["specific positive factor from news", "another factor"],
    "negative_factors": ["specific negative factor from news", "another factor"]
  }},
  "mid_term": {{
    "score": 70,
    "summary": "Medium-term investment outlook based on news analysis",
    "positive_factors": ["specific positive factor from news", "another factor"],
    "negative_factors": ["specific negative factor from news", "another factor"]
  }},
  "long_term": {{
    "score": 60,
    "summary": "Long-term investment outlook based on news analysis",
    "positive_factors": ["specific positive factor from news", "another factor"],
    "negative_factors": ["specific negative factor from news", "another factor"]
  }},
  "key_keywords": ["keyword1 from news", "keyword2 from news"],
  "overall_summary": "Overall analysis summary from all {news_count} articles"
}}

SCORING GUIDELINES:
- 0-30: Very negative news dominates
- 31-49: Mostly negative news
- 50: Neutral/mixed news
- 51-69: Mostly positive news
- 70-100: Very positive news dominates

Respond with ONLY the JSON object above, no additional text.
"""

    def _parse_market_impact_response(self, response: str) -> Dict[str, Any]:
        """시장 영향도 분석 응답 파싱"""
        try:
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)

                # 필수 필드 검증 및 기본값 설정
                return {
                    'impact_level': result.get('impact_level', 'MEDIUM'),
                    'impact_score': float(result.get('impact_score', 50)),
                    'duration': result.get('duration', 'MEDIUM_TERM'),
                    'price_direction': result.get('price_direction', 'NEUTRAL'),
                    'volatility_expected': result.get('volatility_expected', 'MEDIUM'),
                    'trading_volume_impact': result.get('trading_volume_impact', 'NORMAL'),
                    'sector_impact': result.get('sector_impact', '정보 부족'),
                    'key_risks': result.get('key_risks', []),
                    'catalysts': result.get('catalysts', []),
                    'target_price_change': result.get('target_price_change', '0%'),
                    'recommendation': result.get('recommendation', 'HOLD')
                }
            else:
                raise ValueError("JSON 형식을 찾을 수 없음")

        except Exception as e:
            self.logger.warning(f"Gemini 시장 영향도 분석 응답 파싱 실패: {e}")
            return self._get_default_market_impact()

    def _parse_comprehensive_sentiment_response(self, response: str) -> Dict[str, Any]:
        """통합 감성 분석 응답 파싱"""
        try:
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)

                # 필수 필드 검증 및 기본값 설정
                return {
                    'short_term': result.get('short_term', {
                        'score': 50, 'summary': 'Gemini 분석 파싱 실패',
                        'positive_factors': [], 'negative_factors': []
                    }),
                    'mid_term': result.get('mid_term', {
                        'score': 50, 'summary': 'Gemini 분석 파싱 실패',
                        'positive_factors': [], 'negative_factors': []
                    }),
                    'long_term': result.get('long_term', {
                        'score': 50, 'summary': 'Gemini 분석 파싱 실패',
                        'positive_factors': [], 'negative_factors': []
                    }),
                    'key_keywords': result.get('key_keywords', ['분석실패']),
                    'overall_summary': result.get('overall_summary', 'Gemini 통합 분석 완료')
                }
            else:
                self.logger.warning(f"JSON 형식을 찾을 수 없음: {response[:200]}...")
                raise ValueError("JSON 형식을 찾을 수 없음")

        except Exception as e:
            self.logger.warning(f"Gemini 통합 감성 분석 응답 파싱 실패: {e}")
            return self._get_default_sentiment()

    async def analyze_comprehensive(
        self,
        symbol: str,
        name: str,
        stock_data,  # Can be Dict or StockData object
        price_data: Optional[List] = None,
        strategy: str = "comprehensive"
    ) -> str:
        """Multi-LLM 통합용 종합 분석 메소드"""
        try:
            self.logger.info(f"🤖 Gemini 종합 분석 시작: {symbol}({name})")

            if not self.api_available or self.quota_exhausted:
                return self._get_fallback_comprehensive_analysis(symbol, name, stock_data)

            # 종합 분석 프롬프트 생성
            prompt = self._create_comprehensive_prompt(symbol, name, stock_data, price_data, strategy)

            # Gemini API 호출
            response = await self._call_gemini_api(prompt)

            if response and response.strip():
                self.logger.info(f"✅ Gemini 종합 분석 완료: {symbol}")
                return response
            else:
                self.logger.warning(f"⚠️ Gemini 응답 없음: {symbol}")
                return self._get_fallback_comprehensive_analysis(symbol, name, stock_data)

        except Exception as e:
            self.logger.warning(f"⚠️ Gemini 종합 분석 실패: {symbol} - {e}")
            return self._get_fallback_comprehensive_analysis(symbol, name, stock_data)

    def _create_comprehensive_prompt(
        self,
        symbol: str,
        name: str,
        stock_data,  # Can be Dict or StockData object
        price_data: Optional[List],
        strategy: str
    ) -> str:
        """종합 분석용 프롬프트 생성"""

        # StockData 객체인지 Dict인지 확인하여 처리
        if hasattr(stock_data, 'current_price'):
            # StockData 객체인 경우
            current_price = float(stock_data.current_price or 0)
            volume = int(stock_data.volume or 0)
            market_cap = float(stock_data.market_cap or 0)
        else:
            # Dict인 경우
            current_price = float(safe_get_data(stock_data,'current_price', 0) or 0)
            volume = int(safe_get_data(stock_data,'volume', 0) or 0)
            market_cap = float(safe_get_data(stock_data,'market_cap', 0) or 0)

        # 가격 데이터 요약
        price_summary = ""
        if price_data and len(price_data) > 0:
            recent_price = price_data[-1].get('close', current_price) if isinstance(price_data[-1], dict) else current_price
            if isinstance(recent_price, (int, float)):
                price_summary = f"최근 가격 데이터: {len(price_data)}일, 최근가: {recent_price:,.0f}원"

        prompt = f"""
다음 종목에 대한 종합적인 투자 분석을 수행해주세요.

## 기본 정보
- 종목: {symbol} ({name})
- 현재가: {current_price:,}원
- 거래량: {volume:,}주
- 시가총액: {market_cap:,}원
{price_summary}

## 분석 전략: {strategy}

다음 형식으로 JSON 응답을 제공해주세요:

{{
    "buy_score": 매수점수(0-100),
    "confidence": 신뢰도(0-100),
    "reasoning": "분석 근거 설명",
    "recommendation": "BUY/HOLD/SELL",
    "key_factors": ["핵심 요인1", "핵심 요인2", "핵심 요인3"],
    "risks": ["위험 요인1", "위험 요인2"],
    "opportunities": ["기회 요인1", "기회 요인2"],
    "target_price": "목표가 추정",
    "time_horizon": "투자 기간 권장"
}}

반드시 JSON 형식으로만 응답해주세요.
"""
        return prompt.strip()

    def _get_default_market_impact(self) -> Dict[str, Any]:
        """기본 시장 영향도 분석 결과 (개선된 백업 분석)"""
        from datetime import datetime
        current_hour = datetime.now().hour

        # 시간대별 보정
        if 9 <= current_hour <= 15:  # 장중
            impact_score = 38.0  # 보수적 접근
            volatility = 'NORMAL'
            recommendation = 'WATCH'
        else:
            impact_score = 40.0
            volatility = 'LOW'
            recommendation = 'HOLD'

        return {
            'impact_level': 'LOW',
            'impact_score': impact_score,
            'duration': 'SHORT_TERM',
            'price_direction': 'NEUTRAL',
            'volatility_expected': volatility,
            'trading_volume_impact': 'NORMAL',
            'sector_impact': 'Gemini API 할당량 소진으로 분석 불가',
            'key_risks': ['API 제한으로 인한 분석 제한'],
            'catalysts': [],
            'target_price_change': '0%',
            'recommendation': recommendation,
            'fallback_analysis': True,
            'analysis_limitation': 'Gemini API 할당량 초과로 기본 분석 사용'
        }

    def _get_default_sentiment(self) -> Dict[str, Any]:
        """기본 감성 분석 결과 (개선된 백업 분석)"""
        from datetime import datetime
        current_hour = datetime.now().hour

        # 시간대별 보정된 점수
        if 9 <= current_hour <= 15:  # 장중
            base_score = 48  # 약간 보수적
            time_context = "장중"
        elif 8 <= current_hour <= 9 or 15 <= current_hour <= 16:  # 장 전후
            base_score = 49
            time_context = "장 전후"
        else:
            base_score = 50
            time_context = "장외"

        return {
            'short_term': {
                'score': base_score,
                'summary': f'Gemini API 할당량 소진 - 보수적 중립 분석 ({time_context})',
                'positive_factors': ['시장 평균 기준 분석'],
                'negative_factors': ['API 제한으로 상세 분석 불가', '보수적 접근 필요']
            },
            'mid_term': {
                'score': base_score,
                'summary': f'Gemini API 할당량 소진 - 보수적 중립 분석 ({time_context})',
                'positive_factors': ['기본 시장 동향 반영'],
                'negative_factors': ['상세 뉴스 분석 불가']
            },
            'long_term': {
                'score': base_score,
                'summary': f'Gemini API 할당량 소진 - 보수적 중립 분석 ({time_context})',
                'positive_factors': ['장기 기본 전망'],
                'negative_factors': ['충분한 정보 부족으로 보수적 접근']
            },
            'key_keywords': ['API제한', '보수적분석', '기본전망', time_context],
            'overall_summary': f'Gemini API 할당량 초과로 백업 분석 사용 - {time_context} 보정 적용',
            'fallback_analysis': True,
            'analysis_limitation': 'Gemini API 할당량 초과로 기본 분석 사용'
        }

    def _get_fallback_comprehensive_analysis(
        self,
        symbol: str,
        name: str,
        stock_data  # Can be Dict or StockData object
    ) -> str:
        """Gemini 사용 불가 시 폴백 분석"""

        # StockData 객체인지 Dict인지 확인하여 처리
        if hasattr(stock_data, 'current_price'):
            current_price = stock_data.current_price or 0
        else:
            current_price = safe_get_data(stock_data,'current_price', 0)

        fallback_analysis = {
            "buy_score": 50,
            "confidence": 30,
            "reasoning": f"{name}({symbol})에 대한 기본 분석입니다. Gemini API가 사용 불가능하여 제한된 분석을 제공합니다.",
            "recommendation": "HOLD",
            "key_factors": [
                "Gemini 분석 서비스 일시 중단",
                "기본 정보 기반 중립 평가",
                f"현재가 {current_price:,}원"
            ],
            "risks": [
                "상세 분석 부족",
                "시장 상황 반영 제한"
            ],
            "opportunities": [
                "추후 정밀 분석 가능",
                "기본 투자 정보 확보"
            ],
            "target_price": f"{current_price:,}원 (현재가 유지)",
            "time_horizon": "중기 (3-6개월)"
        }

        return json.dumps(fallback_analysis, ensure_ascii=False, indent=2)

    def reset_quota_status(self):
        """할당량 상태를 수동으로 리셋"""
        self.quota_exhausted = False
        self.last_quota_check = 0
        self.logger.info("🔄 Gemini API 할당량 상태가 수동으로 리셋되었습니다")

    def get_quota_status(self) -> Dict[str, Any]:
        """할당량 상태 정보 반환"""
        import time
        current_time = time.time()

        if self.quota_exhausted:
            remaining_hours = int((self.quota_check_interval - (current_time - self.last_quota_check)) / 3600)
            remaining_minutes = int(((self.quota_check_interval - (current_time - self.last_quota_check)) % 3600) / 60)
        else:
            remaining_hours = 0
            remaining_minutes = 0

        return {
            "api_available": self.api_available,
            "quota_exhausted": self.quota_exhausted,
            "remaining_hours": max(0, remaining_hours),
            "remaining_minutes": max(0, remaining_minutes),
            "last_check": datetime.fromtimestamp(self.last_quota_check) if self.last_quota_check else None
        }

    @property
    def model_name(self):
        """호환성을 위한 model 속성"""
        return "gemini-1.5-flash-latest" if self.api_available else None

    async def analyze_with_custom_prompt(self, prompt: str) -> str:
        """커스텀 프롬프트로 Gemini API 호출"""
        try:
            if self.quota_exhausted:
                self.logger.warning("⚠️ Gemini API 할당량 소진으로 인해 스킵")
                return "할당량 소진으로 인해 분석을 수행할 수 없습니다."

            # Gemini API를 통해 분석 요청
            result = await self._call_gemini_api(prompt)

            if result:
                return result
            else:
                return "Gemini 분석을 수행할 수 없습니다."

        except Exception as e:
            self.logger.error(f"❌ Gemini 커스텀 분석 실패: {e}")
            return "분석 중 오류가 발생했습니다."