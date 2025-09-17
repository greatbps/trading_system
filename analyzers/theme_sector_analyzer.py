#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/theme_sector_analyzer.py

테마/섹터 대장주 분석기 - 핫 테마 발굴 및 대장주 식별
"""

import asyncio
import numpy as np
import pandas as pd
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer
from data_collectors.news_collector import NewsCollector


@dataclass
class ThemeInfo:
    """테마 정보"""
    theme_name: str
    theme_keywords: List[str]
    related_stocks: List[str]
    leader_stock: Optional[str]
    theme_strength: float  # 0-100
    momentum_score: float  # 0-100
    news_sentiment: float  # -1 to 1
    duration_days: int
    market_cap_total: float
    avg_volume_increase: float
    confidence: float
    timestamp: datetime


@dataclass
class LeaderStockInfo:
    """대장주 정보"""
    symbol: str
    stock_name: str
    theme_name: str
    leader_score: float  # 0-100
    market_cap: float
    volume_increase_ratio: float
    price_performance: float
    correlation_with_theme: float
    institutional_interest: float
    news_frequency: int
    leadership_strength: str  # 'STRONG', 'MODERATE', 'WEAK'
    competitive_advantage: List[str]
    risk_factors: List[str]
    timestamp: datetime


@dataclass
class SectorAnalysis:
    """섹터 분석"""
    sector_name: str
    sector_performance: float
    relative_strength: float  # vs 코스피
    hot_themes: List[ThemeInfo]
    leader_stocks: List[LeaderStockInfo]
    sector_rotation_signal: str
    investment_attractiveness: float
    timestamp: datetime


class ThemeSectorAnalyzer:
    """테마/섹터 분석기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("ThemeSectorAnalyzer")
        self.gemini_analyzer = GeminiAnalyzer(config)
        self.news_collector = NewsCollector(config) if hasattr(self, 'news_collector') else None
        
        # 테마 키워드 매핑
        self.theme_keywords = {
            '인공지능': ['AI', '인공지능', '딥러닝', '머신러닝', 'ChatGPT', 'LLM', '생성AI'],
            '반도체': ['반도체', '메모리', '시스템반도체', '파운드리', 'AI반도체', 'HBM'],
            '2차전지': ['배터리', '2차전지', 'ESS', '양극재', '음극재', '전해질', '분리막'],
            '바이오': ['바이오', '제약', '신약', '백신', '의료기기', '진단키트'],
            '자율주행': ['자율주행', '전기차', 'EV', '모빌리티', '라이다', '센서'],
            '우주항공': ['우주', '항공', '위성', '발사체', '드론', 'UAM'],
            '메타버스': ['메타버스', 'VR', 'AR', '가상현실', '증강현실'],
            '게임': ['게임', '모바일게임', 'PC게임', '콘솔게임', 'e스포츠'],
            '디스플레이': ['디스플레이', 'OLED', 'QLED', '폴더블', '투명디스플레이'],
            '5G': ['5G', '6G', '통신장비', '기지국', '네트워크'],
            '신재생에너지': ['태양광', '풍력', '수소', '연료전지', '신재생'],
            'K-방역': ['방역', '진단', '마스크', '소독', '검사키트'],
            '콘텐츠': ['콘텐츠', 'OTT', '웹툰', '음악', '영화', 'K컨텐츠']
        }
        
        # 섹터 분류
        self.sector_classification = {
            '기술주': ['삼성전자', 'SK하이닉스', 'NAVER', '카카오', 'LG전자'],
            '바이오': ['셀트리온', '삼성바이오로직스', '유한양행', '종근당'],
            '화학': ['LG화학', 'SK이노베이션', '한화솔루션', '롯데케미칼'],
            '자동차': ['현대차', '기아', '현대모비스', '한온시스템'],
            '금융': ['KB금융', '신한지주', '하나금융지주', '우리금융지주'],
            '건설': ['삼성물산', '대림산업', 'GS건설', '현대건설'],
            '소비재': ['아모레퍼시픽', 'LG생활건강', '오리온', '농심']
        }
        
        # 분석 파라미터
        self.analysis_params = {
            'theme_detection_period': 30,    # 테마 감지 기간 (일)
            'leader_qualification_cap': 1000,  # 대장주 최소 시가총액 (억원)
            'volume_surge_threshold': 2.0,   # 거래량 급증 임계값
            'price_performance_period': 10,  # 가격 성과 기간 (일)
            'news_analysis_period': 7,       # 뉴스 분석 기간 (일)
            'correlation_threshold': 0.6     # 상관관계 임계값
        }
        
        self.logger.info("🎯 테마/섹터 분석기 초기화 완료")
    
    async def detect_hot_themes(self, market_data: Dict[str, List[Dict]], 
                               news_data: List[Dict] = None) -> List[ThemeInfo]:
        """핫 테마 감지"""
        try:
            self.logger.info("🔥 핫 테마 감지 시작")
            
            if not market_data:
                self.logger.warning("⚠️ 시장 데이터 부족")
                return []
            
            hot_themes = []
            
            # 1. 뉴스 기반 테마 감지
            news_themes = await self._detect_themes_from_news(news_data or [])
            
            # 2. 가격/거래량 패턴 기반 테마 감지
            pattern_themes = await self._detect_themes_from_patterns(market_data)
            
            # 3. AI 기반 테마 트렌드 분석
            ai_themes = await self._detect_themes_with_ai(news_data or [], market_data)
            
            # 4. 테마 통합 및 검증
            all_themes = {}
            
            # 뉴스 테마 추가
            for theme in news_themes:
                all_themes[theme.theme_name] = theme
            
            # 패턴 테마 추가/보강
            for theme in pattern_themes:
                if theme.theme_name in all_themes:
                    # 기존 테마 보강
                    existing = all_themes[theme.theme_name]
                    existing.theme_strength = (existing.theme_strength + theme.theme_strength) / 2
                    existing.momentum_score = max(existing.momentum_score, theme.momentum_score)
                    existing.related_stocks.extend(theme.related_stocks)
                    existing.related_stocks = list(set(existing.related_stocks))  # 중복 제거
                else:
                    all_themes[theme.theme_name] = theme
            
            # AI 테마 추가/보강
            for theme in ai_themes:
                if theme.theme_name in all_themes:
                    existing = all_themes[theme.theme_name]
                    existing.confidence = (existing.confidence + theme.confidence) / 2
                    existing.theme_strength = max(existing.theme_strength, theme.theme_strength)
                else:
                    all_themes[theme.theme_name] = theme
            
            # 5. 테마 필터링 및 정렬
            filtered_themes = []
            for theme in all_themes.values():
                # 최소 조건 체크
                if (theme.theme_strength >= 50 and 
                    len(theme.related_stocks) >= 3 and 
                    theme.confidence >= 0.5):
                    filtered_themes.append(theme)
            
            # 강도순 정렬
            hot_themes = sorted(filtered_themes, key=lambda x: x.theme_strength, reverse=True)[:10]
            
            self.logger.info(f"✅ 핫 테마 {len(hot_themes)}개 발견")
            return hot_themes
            
        except Exception as e:
            self.logger.error(f"❌ 핫 테마 감지 실패: {e}")
            return []
    
    async def _detect_themes_from_news(self, news_data: List[Dict]) -> List[ThemeInfo]:
        """뉴스 기반 테마 감지"""
        try:
            if not news_data:
                return []
            
            # 키워드 빈도 분석
            keyword_counts = defaultdict(int)
            keyword_news = defaultdict(list)
            
            for news_item in news_data:
                title = news_item.get('title', '')
                content = news_item.get('content', '')
                text = title + ' ' + content
                
                # 테마 키워드 검색
                for theme_name, keywords in self.theme_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in text.lower():
                            keyword_counts[theme_name] += 1
                            keyword_news[theme_name].append(news_item)
                            break
            
            # 테마별 정보 생성
            themes = []
            for theme_name, count in keyword_counts.items():
                if count >= 3:  # 최소 3개 뉴스
                    # 감정 분석
                    sentiment = await self._analyze_theme_sentiment(keyword_news[theme_name])
                    
                    theme_info = ThemeInfo(
                        theme_name=theme_name,
                        theme_keywords=self.theme_keywords[theme_name],
                        related_stocks=[],  # 나중에 보강
                        leader_stock=None,
                        theme_strength=min(100, count * 10),  # 뉴스 개수 * 10
                        momentum_score=min(100, count * 8),
                        news_sentiment=sentiment,
                        duration_days=self._estimate_theme_duration(keyword_news[theme_name]),
                        market_cap_total=0,
                        avg_volume_increase=0,
                        confidence=min(1.0, count / 10),
                        timestamp=datetime.now()
                    )
                    themes.append(theme_info)
            
            return themes
            
        except Exception as e:
            self.logger.error(f"❌ 뉴스 기반 테마 감지 실패: {e}")
            return []
    
    async def _detect_themes_from_patterns(self, market_data: Dict[str, List[Dict]]) -> List[ThemeInfo]:
        """가격/거래량 패턴 기반 테마 감지"""
        try:
            # 종목별 성과 분석
            stock_performances = {}
            
            for symbol, data in market_data.items():
                if len(data) >= self.analysis_params['price_performance_period']:
                    recent_data = data[-self.analysis_params['price_performance_period']:]
                    
                    # 가격 성과
                    price_performance = (recent_data[-1]['close'] - recent_data[0]['close']) / recent_data[0]['close']
                    
                    # 거래량 증가율
                    avg_volume = np.mean([d['volume'] for d in data[:-self.analysis_params['price_performance_period']]])
                    recent_volume = np.mean([d['volume'] for d in recent_data])
                    volume_increase = recent_volume / avg_volume if avg_volume > 0 else 1
                    
                    stock_performances[symbol] = {
                        'price_performance': price_performance,
                        'volume_increase': volume_increase,
                        'momentum_score': price_performance * 50 + (volume_increase - 1) * 25
                    }
            
            # 성과 상위 종목들의 테마 분류
            top_performers = sorted(stock_performances.items(), 
                                  key=lambda x: x[1]['momentum_score'], reverse=True)[:20]
            
            # 테마별 그룹핑
            theme_groups = defaultdict(list)
            
            for symbol, performance in top_performers:
                # 종목명으로 테마 추정 (실제로는 더 정교한 분류 필요)
                estimated_theme = await self._estimate_stock_theme(symbol)
                if estimated_theme:
                    theme_groups[estimated_theme].append((symbol, performance))
            
            # 테마 정보 생성
            themes = []
            for theme_name, stocks in theme_groups.items():
                if len(stocks) >= 3:  # 최소 3개 종목
                    avg_performance = np.mean([stock[1]['price_performance'] for stock in stocks])
                    avg_volume_increase = np.mean([stock[1]['volume_increase'] for stock in stocks])
                    
                    theme_info = ThemeInfo(
                        theme_name=theme_name,
                        theme_keywords=self.theme_keywords.get(theme_name, [theme_name]),
                        related_stocks=[stock[0] for stock in stocks],
                        leader_stock=stocks[0][0],  # 성과 1위
                        theme_strength=min(100, avg_performance * 100 + 30),
                        momentum_score=min(100, np.mean([stock[1]['momentum_score'] for stock in stocks])),
                        news_sentiment=0.0,  # 패턴 기반이므로 중립
                        duration_days=self.analysis_params['price_performance_period'],
                        market_cap_total=0,
                        avg_volume_increase=avg_volume_increase,
                        confidence=min(1.0, len(stocks) / 10),
                        timestamp=datetime.now()
                    )
                    themes.append(theme_info)
            
            return themes
            
        except Exception as e:
            self.logger.error(f"❌ 패턴 기반 테마 감지 실패: {e}")
            return []
    
    async def _detect_themes_with_ai(self, news_data: List[Dict], 
                                   market_data: Dict[str, List[Dict]]) -> List[ThemeInfo]:
        """AI 기반 테마 트렌드 분석"""
        try:
            if not news_data and not market_data:
                return []
            
            # AI 분석을 위한 종합 데이터 요약
            news_summary = self._create_news_summary(news_data)
            market_summary = self._create_market_summary(market_data)
            
            analysis_prompt = f"""
다음 시장 데이터와 뉴스를 분석하여 현재 주목받는 투자 테마를 찾아주세요:

최근 뉴스 요약:
{news_summary}

시장 동향 요약:
{market_summary}

다음 JSON 배열 형식으로 상위 5개 테마를 답변해주세요:
[
  {{
    "theme_name": "테마명",
    "theme_strength": 0~100,
    "momentum_score": 0~100,
    "key_keywords": ["키워드1", "키워드2", "키워드3"],
    "related_events": ["관련 이벤트1", "관련 이벤트2"],
    "investment_outlook": "positive/neutral/negative",
    "confidence": 0.0~1.0
  }}
]
"""
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(analysis_prompt)
            
            themes = []
            if ai_result and isinstance(ai_result, list):
                for theme_data in ai_result:
                    if isinstance(theme_data, dict):
                        theme_info = ThemeInfo(
                            theme_name=theme_data.get('theme_name', '알 수 없음'),
                            theme_keywords=theme_data.get('key_keywords', []),
                            related_stocks=[],  # AI는 종목 추천 안함
                            leader_stock=None,
                            theme_strength=theme_data.get('theme_strength', 50),
                            momentum_score=theme_data.get('momentum_score', 50),
                            news_sentiment=1.0 if theme_data.get('investment_outlook') == 'positive' else -1.0 if theme_data.get('investment_outlook') == 'negative' else 0.0,
                            duration_days=7,  # AI 기본값
                            market_cap_total=0,
                            avg_volume_increase=0,
                            confidence=theme_data.get('confidence', 0.5),
                            timestamp=datetime.now()
                        )
                        themes.append(theme_info)
            
            return themes
            
        except Exception as e:
            self.logger.warning(f"⚠️ AI 테마 분석 실패: {e}")
            return []
    
    async def _analyze_theme_sentiment(self, news_items: List[Dict]) -> float:
        """테마 뉴스 감정 분석"""
        try:
            if not news_items:
                return 0.0
            
            # 긍정/부정 키워드 카운트
            positive_keywords = ['상승', '급등', '호재', '기대', '성장', '확대', '투자', '개발', '혁신']
            negative_keywords = ['하락', '급락', '악재', '우려', '위험', '감소', '축소', '철회', '지연']
            
            positive_count = 0
            negative_count = 0
            total_count = 0
            
            for news_item in news_items:
                text = news_item.get('title', '') + ' ' + news_item.get('content', '')
                total_count += 1
                
                for keyword in positive_keywords:
                    if keyword in text:
                        positive_count += 1
                        break
                
                for keyword in negative_keywords:
                    if keyword in text:
                        negative_count += 1
                        break
            
            if total_count == 0:
                return 0.0
            
            # -1 ~ 1 범위로 정규화
            sentiment = (positive_count - negative_count) / total_count
            return max(-1.0, min(1.0, sentiment))
            
        except Exception:
            return 0.0
    
    def _estimate_theme_duration(self, news_items: List[Dict]) -> int:
        """테마 지속 기간 추정"""
        try:
            if not news_items:
                return 0
            
            # 뉴스 날짜 분석
            dates = []
            for news_item in news_items:
                date_str = news_item.get('date', '')
                if date_str:
                    try:
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        dates.append(date)
                    except:
                        continue
            
            if len(dates) < 2:
                return 1
            
            dates.sort()
            duration = (dates[-1] - dates[0]).days
            return max(1, duration)
            
        except Exception:
            return 1
    
    async def _estimate_stock_theme(self, symbol: str) -> Optional[str]:
        """종목의 테마 추정"""
        try:
            # 실제로는 종목명이나 업종 정보로 판단해야 함
            # 여기서는 간단한 매핑 예시
            
            # 섹터별 대표 종목으로 테마 추정
            for sector, stocks in self.sector_classification.items():
                if symbol in stocks:
                    return sector
            
            # 종목코드나 이름 패턴으로 추정 (더 정교한 로직 필요)
            if '전자' in symbol or '반도체' in symbol:
                return '반도체'
            elif '바이오' in symbol or '제약' in symbol:
                return '바이오'
            elif '전기' in symbol or '배터리' in symbol:
                return '2차전지'
            
            return None
            
        except Exception:
            return None
    
    def _create_news_summary(self, news_data: List[Dict]) -> str:
        """뉴스 요약 생성"""
        try:
            if not news_data:
                return "뉴스 데이터 없음"
            
            # 최근 뉴스 제목들만 요약
            recent_titles = [news.get('title', '') for news in news_data[:10]]
            return "주요 뉴스: " + " | ".join(recent_titles[:5])
            
        except Exception:
            return "뉴스 요약 실패"
    
    def _create_market_summary(self, market_data: Dict[str, List[Dict]]) -> str:
        """시장 요약 생성"""
        try:
            if not market_data:
                return "시장 데이터 없음"
            
            # 상위 성과 종목들
            performances = []
            for symbol, data in list(market_data.items())[:20]:  # 상위 20개만
                if len(data) >= 5:
                    recent_change = (data[-1]['close'] - data[-5]['close']) / data[-5]['close'] * 100
                    performances.append((symbol, recent_change))
            
            performances.sort(key=lambda x: x[1], reverse=True)
            top_5 = performances[:5]
            
            summary = "상승주: " + ", ".join([f"{stock}(+{change:.1f}%)" for stock, change in top_5])
            return summary
            
        except Exception:
            return "시장 요약 실패"
    
    async def identify_leader_stocks(self, theme_info: ThemeInfo, 
                                   market_data: Dict[str, List[Dict]],
                                   institutional_data: Dict[str, List[Dict]] = None) -> List[LeaderStockInfo]:
        """테마 내 대장주 식별"""
        try:
            self.logger.info(f"👑 {theme_info.theme_name} 테마 대장주 식별 시작")
            
            if not theme_info.related_stocks:
                return []
            
            leader_candidates = []
            
            for symbol in theme_info.related_stocks:
                if symbol not in market_data:
                    continue
                
                data = market_data[symbol]
                if len(data) < 10:
                    continue
                
                # 대장주 스코어 계산
                leader_score = await self._calculate_leader_score(
                    symbol, data, institutional_data.get(symbol, []) if institutional_data else []
                )
                
                if leader_score['total_score'] >= 60:  # 최소 조건
                    leader_info = LeaderStockInfo(
                        symbol=symbol,
                        stock_name=symbol,  # 실제로는 종목명 조회 필요
                        theme_name=theme_info.theme_name,
                        leader_score=leader_score['total_score'],
                        market_cap=leader_score.get('market_cap', 0),
                        volume_increase_ratio=leader_score.get('volume_ratio', 1.0),
                        price_performance=leader_score.get('price_performance', 0),
                        correlation_with_theme=leader_score.get('theme_correlation', 0.5),
                        institutional_interest=leader_score.get('institutional_score', 0),
                        news_frequency=leader_score.get('news_count', 0),
                        leadership_strength=self._determine_leadership_strength(leader_score['total_score']),
                        competitive_advantage=leader_score.get('advantages', []),
                        risk_factors=leader_score.get('risks', []),
                        timestamp=datetime.now()
                    )
                    leader_candidates.append(leader_info)
            
            # 점수순 정렬
            leaders = sorted(leader_candidates, key=lambda x: x.leader_score, reverse=True)[:5]
            
            self.logger.info(f"✅ {theme_info.theme_name} 대장주 후보 {len(leaders)}개 식별")
            return leaders
            
        except Exception as e:
            self.logger.error(f"❌ {theme_info.theme_name} 대장주 식별 실패: {e}")
            return []
    
    async def _calculate_leader_score(self, symbol: str, price_data: List[Dict], 
                                    institutional_data: List[Dict] = None) -> Dict[str, Any]:
        """대장주 점수 계산"""
        try:
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            score_components = {}
            total_score = 0
            
            # 1. 시가총액 (20점) - 대장주는 어느 정도 규모가 있어야 함
            latest_price = df['close'].iloc[-1]
            # 시가총액 추정 (실제로는 상장주식수 필요)
            estimated_market_cap = latest_price * 1000000  # 임시값
            
            if estimated_market_cap > 10000:  # 1조 이상
                cap_score = 20
            elif estimated_market_cap > 5000:  # 5천억 이상
                cap_score = 15
            elif estimated_market_cap > 1000:  # 1천억 이상
                cap_score = 10
            else:
                cap_score = 5
            
            score_components['market_cap'] = estimated_market_cap
            total_score += cap_score
            
            # 2. 가격 성과 (25점)
            if len(df) >= 10:
                price_performance = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
                performance_score = min(25, max(0, price_performance * 100 + 10))
                score_components['price_performance'] = price_performance
                total_score += performance_score
            
            # 3. 거래량 급증 (20점)
            avg_volume = df['volume'].iloc[:-5].mean() if len(df) > 5 else df['volume'].mean()
            recent_volume = df['volume'].iloc[-5:].mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            if volume_ratio > 3.0:
                volume_score = 20
            elif volume_ratio > 2.0:
                volume_score = 15
            elif volume_ratio > 1.5:
                volume_score = 10
            else:
                volume_score = 5
            
            score_components['volume_ratio'] = volume_ratio
            total_score += volume_score
            
            # 4. 기관/외국인 관심도 (15점)
            institutional_score = 0
            if institutional_data:
                # 기관 순매수 분석
                net_buys = [item.get('net_buy', 0) for item in institutional_data[-10:]]
                if sum(net_buys) > 0:
                    institutional_score = min(15, len([x for x in net_buys if x > 0]) * 2)
            else:
                # 거래량 패턴으로 추정
                if volume_ratio > 2.0:
                    institutional_score = 10
            
            score_components['institutional_score'] = institutional_score
            total_score += institutional_score
            
            # 5. 테마 연관성 (10점)
            theme_correlation = 0.7  # 임시값 (실제로는 뉴스 분석 등으로 계산)
            correlation_score = theme_correlation * 10
            score_components['theme_correlation'] = theme_correlation
            total_score += correlation_score
            
            # 6. 뉴스 언급 빈도 (10점)
            news_count = 5  # 임시값 (실제로는 뉴스 검색 필요)
            news_score = min(10, news_count)
            score_components['news_count'] = news_count
            total_score += news_score
            
            # 경쟁우위 요소
            advantages = []
            if cap_score >= 15:
                advantages.append('대형주 안정성')
            if volume_ratio > 2.5:
                advantages.append('높은 거래 관심도')
            if price_performance > 0.1:
                advantages.append('강한 가격 모멘텀')
            if institutional_score > 10:
                advantages.append('기관 투자자 선호')
            
            # 리스크 요인
            risks = []
            if cap_score < 10:
                risks.append('소형주 변동성 위험')
            if price_performance < -0.05:
                risks.append('부정적 가격 흐름')
            if volume_ratio < 1.2:
                risks.append('낮은 거래 관심도')
            
            score_components.update({
                'total_score': min(100, total_score),
                'advantages': advantages,
                'risks': risks
            })
            
            return score_components
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 대장주 점수 계산 실패: {e}")
            return {'total_score': 0}
    
    def _determine_leadership_strength(self, score: float) -> str:
        """대장주 리더십 강도 판단"""
        if score >= 80:
            return 'STRONG'
        elif score >= 65:
            return 'MODERATE'
        else:
            return 'WEAK'
    
    async def analyze_sector_rotation(self, market_data: Dict[str, List[Dict]]) -> List[SectorAnalysis]:
        """섹터 로테이션 분석"""
        try:
            self.logger.info("🔄 섹터 로테이션 분석 시작")
            
            sector_analyses = []
            
            for sector_name, representative_stocks in self.sector_classification.items():
                # 섹터별 대표 종목들의 성과 계산
                sector_performance = 0
                valid_stocks = 0
                
                for stock in representative_stocks:
                    if stock in market_data and len(market_data[stock]) >= 10:
                        data = market_data[stock]
                        stock_performance = (data[-1]['close'] - data[-10]['close']) / data[-10]['close']
                        sector_performance += stock_performance
                        valid_stocks += 1
                
                if valid_stocks > 0:
                    avg_sector_performance = sector_performance / valid_stocks
                    
                    # 코스피 대비 상대 강도 (임시값)
                    kospi_performance = 0.02  # 2% 가정
                    relative_strength = avg_sector_performance - kospi_performance
                    
                    # 섹터 로테이션 신호
                    if relative_strength > 0.03:  # 3% 이상 아웃퍼폼
                        rotation_signal = 'STRONG_INFLOW'
                    elif relative_strength > 0.01:
                        rotation_signal = 'INFLOW'
                    elif relative_strength > -0.01:
                        rotation_signal = 'NEUTRAL'
                    elif relative_strength > -0.03:
                        rotation_signal = 'OUTFLOW'
                    else:
                        rotation_signal = 'STRONG_OUTFLOW'
                    
                    # 투자 매력도
                    attractiveness = 50 + relative_strength * 1000  # 간단한 계산
                    attractiveness = max(0, min(100, attractiveness))
                    
                    sector_analysis = SectorAnalysis(
                        sector_name=sector_name,
                        sector_performance=avg_sector_performance,
                        relative_strength=relative_strength,
                        hot_themes=[],  # 별도로 계산
                        leader_stocks=[],  # 별도로 계산
                        sector_rotation_signal=rotation_signal,
                        investment_attractiveness=attractiveness,
                        timestamp=datetime.now()
                    )
                    
                    sector_analyses.append(sector_analysis)
            
            # 상대 강도순 정렬
            sector_analyses.sort(key=lambda x: x.relative_strength, reverse=True)
            
            self.logger.info(f"✅ 섹터 로테이션 분석 완료: {len(sector_analyses)}개 섹터")
            return sector_analyses
            
        except Exception as e:
            self.logger.error(f"❌ 섹터 로테이션 분석 실패: {e}")
            return []
    
    async def get_investment_recommendations(self, themes: List[ThemeInfo], 
                                          leaders: List[LeaderStockInfo]) -> Dict[str, Any]:
        """투자 추천 생성"""
        try:
            recommendations = {
                'top_themes': [],
                'recommended_stocks': [],
                'sector_allocation': {},
                'risk_assessment': {},
                'action_plan': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # 상위 3개 테마
            top_themes = sorted(themes, key=lambda x: x.theme_strength, reverse=True)[:3]
            recommendations['top_themes'] = [
                {
                    'theme_name': theme.theme_name,
                    'strength': theme.theme_strength,
                    'momentum': theme.momentum_score,
                    'confidence': theme.confidence
                }
                for theme in top_themes
            ]
            
            # 추천 종목 (각 테마별 대장주)
            for theme in top_themes:
                theme_leaders = [leader for leader in leaders if leader.theme_name == theme.theme_name]
                if theme_leaders:
                    best_leader = max(theme_leaders, key=lambda x: x.leader_score)
                    recommendations['recommended_stocks'].append({
                        'symbol': best_leader.symbol,
                        'theme': best_leader.theme_name,
                        'leader_score': best_leader.leader_score,
                        'leadership_strength': best_leader.leadership_strength
                    })
            
            # 섹터 배분 추천
            sector_weights = {}
            for theme in top_themes:
                # 테마를 섹터로 매핑 (간단한 버전)
                sector = self._map_theme_to_sector(theme.theme_name)
                weight = theme.theme_strength / 100 * 0.3  # 최대 30%
                sector_weights[sector] = weight
            
            recommendations['sector_allocation'] = sector_weights
            
            # 리스크 평가
            avg_confidence = np.mean([theme.confidence for theme in top_themes])
            risk_level = 'HIGH' if avg_confidence < 0.6 else 'MEDIUM' if avg_confidence < 0.8 else 'LOW'
            
            recommendations['risk_assessment'] = {
                'overall_risk': risk_level,
                'confidence_level': avg_confidence,
                'diversification_needed': len(set([self._map_theme_to_sector(theme.theme_name) for theme in top_themes])) < 3
            }
            
            # 실행 계획
            action_items = []
            for theme in top_themes:
                action_items.append(f"{theme.theme_name} 테마 모니터링")
                if theme.momentum_score > 70:
                    action_items.append(f"{theme.theme_name} 대장주 매수 검토")
            
            recommendations['action_plan'] = action_items
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"❌ 투자 추천 생성 실패: {e}")
            return {}
    
    def _map_theme_to_sector(self, theme_name: str) -> str:
        """테마를 섹터로 매핑"""
        theme_sector_map = {
            '인공지능': '기술주',
            '반도체': '기술주',
            '2차전지': '화학',
            '바이오': '바이오',
            '자율주행': '자동차',
            '우주항공': '기술주',
            '메타버스': '기술주',
            '게임': '기술주',
            '디스플레이': '기술주',
            '5G': '기술주',
            '신재생에너지': '화학',
            'K-방역': '바이오',
            '콘텐츠': '소비재'
        }
        
        return theme_sector_map.get(theme_name, '기타')
    
    def get_theme_summary_report(self, themes: List[ThemeInfo], 
                               leaders: List[LeaderStockInfo]) -> str:
        """테마 요약 보고서 생성"""
        try:
            report = "🎯 테마/섹터 분석 보고서\n"
            report += "=" * 50 + "\n\n"
            
            # 핫 테마 요약
            report += "🔥 핫 테마 TOP 5:\n"
            for i, theme in enumerate(themes[:5], 1):
                report += f"  {i}. {theme.theme_name} (강도: {theme.theme_strength:.1f}, 모멘텀: {theme.momentum_score:.1f})\n"
                report += f"     관련주: {len(theme.related_stocks)}개, 신뢰도: {theme.confidence:.2f}\n"
            
            report += "\n"
            
            # 대장주 요약
            report += "👑 대장주 후보:\n"
            for leader in leaders[:5]:
                report += f"  • {leader.symbol} ({leader.theme_name})\n"
                report += f"    리더십: {leader.leadership_strength} (점수: {leader.leader_score:.1f})\n"
                report += f"    거래량증가: {leader.volume_increase_ratio:.1f}배\n"
            
            report += "\n"
            
            # 투자 포인트
            report += "💡 주요 투자 포인트:\n"
            if themes:
                best_theme = max(themes, key=lambda x: x.theme_strength)
                report += f"  • 최강 테마: {best_theme.theme_name}\n"
                report += f"  • 평균 신뢰도: {np.mean([t.confidence for t in themes[:3]]):.2f}\n"
            
            if leaders:
                best_leader = max(leaders, key=lambda x: x.leader_score)
                report += f"  • 최고 대장주: {best_leader.symbol} ({best_leader.leader_score:.1f}점)\n"
            
            report += f"\n📊 분석 시점: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ 요약 보고서 생성 실패: {e}")
            return "보고서 생성 실패"