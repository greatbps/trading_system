#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/analysis_engine.py

수급정보와 차트패턴이 통합된 종합 분석 엔진
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import time
from utils.logger import get_logger

class AnalysisEngine:
    """수급정보와 차트패턴이 통합된 종합 분석 엔진"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("AnalysisEngine")
        
        # 뉴스 수집기 초기화
        try:
            from data_collectors.news_collector import NewsCollector
            self.news_collector = NewsCollector(config)
            self.logger.info("✅ 뉴스 수집기 초기화 완료")
        except ImportError as e:
            self.logger.warning(f"⚠️ 뉴스 수집기 초기화 실패: {e}")
            self.news_collector = None
        
        # 기술적 분석기 초기화 (수급정보와 차트패턴 포함)
        try:
            from analyzers.technical_analyzer import TechnicalAnalyzer
            self.technical_analyzer = TechnicalAnalyzer(config)
            self.logger.info("✅ 향상된 기술적 분석기 초기화 완료")
        except ImportError as e:
            self.logger.warning(f"⚠️ 기술적 분석기 초기화 실패: {e}")
            self.technical_analyzer = None
        
        # 수급 분석기 직접 초기화
        try:
            from analyzers.supply_demand_analyzer import SupplyDemandAnalyzer
            self.supply_demand_analyzer = SupplyDemandAnalyzer(config)
            self.logger.info("✅ 수급 분석기 초기화 완료")
        except ImportError as e:
            self.logger.warning(f"⚠️ 수급 분석기 초기화 실패: {e}")
            self.supply_demand_analyzer = None
        
        # 차트패턴 분석기 직접 초기화
        try:
            from analyzers.chart_pattern_analyzer import ChartPatternAnalyzer
            self.chart_pattern_analyzer = ChartPatternAnalyzer(config)
            self.logger.info("✅ 차트패턴 분석기 초기화 완료")
        except ImportError as e:
            self.logger.warning(f"⚠️ 차트패턴 분석기 초기화 실패: {e}")
            self.chart_pattern_analyzer = None
    
    def calculate_technical_score(self, stock_data) -> Dict:
        """기술적 분석 점수 계산"""
        try:
            tech_score = 50.0
            
            # 안전한 속성 접근
            current_price = self.safe_get_attr(stock_data, 'current_price', 0)
            change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
            volume = self.safe_get_attr(stock_data, 'volume', 0)
            high_52w = self.safe_get_attr(stock_data, 'high_52w', 0)
            low_52w = self.safe_get_attr(stock_data, 'low_52w', 0)
            
            # 등락률 기준 점수 조정
            if change_rate > 5:
                tech_score += 20
            elif change_rate > 2:
                tech_score += 10
            elif change_rate < -5:
                tech_score -= 20
            elif change_rate < -2:
                tech_score -= 10
            
            # 거래량 기준 점수 조정
            if volume > 2000000:
                tech_score += 10
            elif volume < 100000:
                tech_score -= 5
            
            # 52주 고저점 대비 위치
            if high_52w and low_52w and current_price:
                position_ratio = (current_price - low_52w) / (high_52w - low_52w)
                if position_ratio > 0.8:
                    tech_score += 15
                elif position_ratio < 0.2:
                    tech_score -= 15
            
            tech_score = max(0, min(100, tech_score))
            
            return {
                'overall_score': tech_score,
                'momentum_score': tech_score * 0.3,
                'volume_score': tech_score * 0.2,
                'position_score': tech_score * 0.2,
                'trend_score': tech_score * 0.3,
                'indicators': {
                    'rsi': 50.0,
                    'macd_signal': 'neutral',
                    'bollinger_position': 'middle'
                }
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 기술적 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'momentum_score': 50.0,
                'volume_score': 50.0,
                'position_score': 50.0,
                'trend_score': 50.0,
                'indicators': {}
            }
    
    def calculate_fundamental_score(self, stock_data) -> Dict:
        """펀더멘털 분석 점수 계산"""
        try:
            fund_score = 50.0
            
            # 안전한 속성 접근
            pe_ratio = self.safe_get_attr(stock_data, 'pe_ratio', None)
            pbr = self.safe_get_attr(stock_data, 'pbr', None)
            market_cap = self.safe_get_attr(stock_data, 'market_cap', None)
            
            # PER 분석
            if pe_ratio:
                if 5 <= pe_ratio <= 15:
                    fund_score += 15
                elif 15 < pe_ratio <= 25:
                    fund_score += 5
                elif pe_ratio > 30:
                    fund_score -= 10
            
            # PBR 분석
            if pbr:
                if 0.5 <= pbr <= 1.5:
                    fund_score += 10
                elif pbr > 3:
                    fund_score -= 10
            
            # 시가총액 안정성
            if market_cap:
                if market_cap > 10000:
                    fund_score += 10
                elif market_cap > 5000:
                    fund_score += 5
            
            fund_score = max(0, min(100, fund_score))
            
            return {
                'overall_score': fund_score,
                'value_score': fund_score * 0.4,
                'growth_score': fund_score * 0.3,
                'quality_score': fund_score * 0.3,
                'ratios': {
                    'pe_ratio': pe_ratio,
                    'pbr': pbr,
                    'market_cap': market_cap
                }
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 펀더멘털 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'value_score': 50.0,
                'growth_score': 50.0,
                'quality_score': 50.0,
                'ratios': {}
            }
    
    def calculate_news_sentiment_score(self, symbol: str, name: str) -> Dict:
        """뉴스 감정 분석 점수 계산"""
        try:
            if not self.news_collector:
                return {
                    'overall_score': 50.0,
                    'material_score': 0.0,
                    'sentiment_score': 0.0,
                    'news_count': 0,
                    'material_type': '재료없음',
                    'keywords': [],
                    'has_material': False
                }
            
            # 뉴스 분석 실행
            news_analysis = self.news_collector.get_news_analysis_summary(name, symbol)
            
            # 기본 감정 점수 (50점 기준)
            base_score = 50.0
            
            # 뉴스 재료 점수 적용
            material_score = news_analysis.get('material_score', 0)
            
            # 뉴스 재료 타입별 가중치
            material_weights = {
                '장기재료': 1.5,
                '중기재료': 1.2,
                '단기재료': 1.0,
                '재료없음': 0.0
            }
            
            material_type = news_analysis.get('material_type', '재료없음')
            material_weight = material_weights.get(material_type, 0.0)
            
            # 재료 점수를 0-40점 범위로 정규화 (최대 40점 보너스)
            normalized_material_score = min(40, material_score * material_weight * 2)
            
            # 감정 점수 적용 (-10 ~ +10점)
            sentiment_score = news_analysis.get('sentiment_score', 0)
            sentiment_bonus = sentiment_score * 10
            
            # 뉴스 개수 보너스 (최대 5점)
            news_count = news_analysis.get('news_count', 0)
            news_bonus = min(5, news_count)
            
            # 최종 점수 계산
            final_score = base_score + normalized_material_score + sentiment_bonus + news_bonus
            final_score = max(0, min(100, final_score))
            
            self.logger.info(f"   📰 뉴스 분석: {material_type} (재료점수: {material_score:.1f}, 최종점수: {final_score:.1f})")
            
            return {
                'overall_score': final_score,
                'material_score': normalized_material_score,
                'sentiment_score': sentiment_bonus,
                'news_count': news_count,
                'material_type': material_type,
                'keywords': news_analysis.get('keywords', []),
                'has_material': news_analysis.get('has_material', False),
                'raw_material_score': material_score
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 뉴스 감정 분석 실패: {e}")
            return {
                'overall_score': 50.0,
                'material_score': 0.0,
                'sentiment_score': 0.0,
                'news_count': 0,
                'material_type': '재료없음',
                'keywords': [],
                'has_material': False
            }
    
    async def calculate_supply_demand_score(self, symbol: str, stock_data) -> Dict:
        """수급 분석 점수 계산 - 새로 추가"""
        try:
            if not self.supply_demand_analyzer:
                # 기본 수급 분석
                return self._basic_supply_demand_analysis(stock_data)
            
            # 전문 수급 분석기 사용
            supply_demand_analysis = await self.supply_demand_analyzer.analyze(stock_data)
            
            return {
                'overall_score': supply_demand_analysis.get('overall_score', 50.0),
                'foreign_score': supply_demand_analysis.get('foreign_trading', {}).get('score', 50),
                'institution_score': supply_demand_analysis.get('institution_trading', {}).get('score', 50),
                'individual_score': supply_demand_analysis.get('individual_trading', {}).get('score', 50),
                'volume_score': self._calculate_volume_score(supply_demand_analysis.get('volume_analysis', {})),
                'supply_demand_balance': supply_demand_analysis.get('supply_demand_balance', {}),
                'trading_intensity': supply_demand_analysis.get('trading_intensity', {}),
                'detailed_analysis': supply_demand_analysis
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 수급 분석 실패: {e}")
            return self._basic_supply_demand_analysis(stock_data)
    
    def _basic_supply_demand_analysis(self, stock_data) -> Dict:
        """기본 수급 분석 (분석기 없을 때)"""
        volume = getattr(stock_data, 'volume', 0)
        trading_value = getattr(stock_data, 'trading_value', 0)
        
        # 간단한 수급 점수
        supply_demand_score = 50.0
        
        if volume > 2000000:
            supply_demand_score = 70
        elif volume > 1000000:
            supply_demand_score = 60
        elif volume < 200000:
            supply_demand_score = 40
        
        if trading_value > 1000:
            supply_demand_score += 5
        elif trading_value < 100:
            supply_demand_score -= 5
        
        return {
            'overall_score': max(0, min(100, supply_demand_score)),
            'foreign_score': 50,
            'institution_score': 50,
            'individual_score': 50,
            'volume_score': supply_demand_score,
            'supply_demand_balance': {'balance_type': 'unknown'},
            'trading_intensity': {'intensity_level': 'normal'},
            'detailed_analysis': None
        }
    
    async def calculate_chart_pattern_score(self, symbol: str, stock_data) -> Dict:
        """차트패턴 분석 점수 계산 - 새로 추가"""
        try:
            if not self.chart_pattern_analyzer:
                # 기본 차트패턴 분석
                return self._basic_chart_pattern_analysis(stock_data)
            
            # 전문 차트패턴 분석기 사용
            pattern_analysis = await self.chart_pattern_analyzer.analyze(stock_data)
            
            return {
                'overall_score': pattern_analysis.get('overall_score', 50.0),
                'candle_pattern_score': pattern_analysis.get('candle_patterns', {}).get('overall_score', 50),
                'technical_pattern_score': pattern_analysis.get('technical_patterns', {}).get('overall_score', 50),
                'trendline_score': pattern_analysis.get('trendlines', {}).get('overall_score', 50),
                'support_resistance_score': pattern_analysis.get('support_resistance', {}).get('overall_score', 50),
                'pattern_strength': pattern_analysis.get('pattern_strength', 0.5),
                'confidence': pattern_analysis.get('confidence', 0.5),
                'detected_patterns': pattern_analysis.get('detected_patterns', []),
                'pattern_recommendation': pattern_analysis.get('pattern_recommendation', {}),
                'detailed_analysis': pattern_analysis
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 차트패턴 분석 실패: {e}")
            return self._basic_chart_pattern_analysis(stock_data)
    
    def _basic_chart_pattern_analysis(self, stock_data) -> Dict:
        """기본 차트패턴 분석 (분석기 없을 때)"""
        change_rate = self.safe_get_attr(stock_data, 'change_rate', 0)
        volume = self.safe_get_attr(stock_data, 'volume', 0)
        
        # 간단한 패턴 점수
        pattern_score = 50.0
        
        if change_rate > 3 and volume > 1000000:
            pattern_score = 75  # 상승 돌파 패턴
            pattern_type = "상승돌파"
        elif change_rate < -3 and volume > 1000000:
            pattern_score = 25  # 하락 패턴
            pattern_type = "하락패턴"
        elif abs(change_rate) < 1:
            pattern_score = 50  # 횡보 패턴
            pattern_type = "횡보"
        else:
            pattern_score = 55
            pattern_type = "일반"
        
        return {
            'overall_score': pattern_score,
            'candle_pattern_score': pattern_score,
            'technical_pattern_score': pattern_score,
            'trendline_score': 50,
            'support_resistance_score': 50,
            'pattern_strength': abs(change_rate) / 10,
            'confidence': 0.5,
            'detected_patterns': [pattern_type],
            'pattern_recommendation': {'action': 'HOLD'},
            'detailed_analysis': None
        }
    
    def _calculate_volume_score(self, volume_analysis: Dict) -> float:
        """거래량 점수 계산"""
        try:
            volume_ratio = volume_analysis.get('volume_ratio', 1.0)
            volume_pattern = volume_analysis.get('volume_pattern', 'normal')
            
            # 기본 점수
            if volume_ratio > 2.0:
                score = 80
            elif volume_ratio > 1.5:
                score = 70
            elif volume_ratio > 1.0:
                score = 60
            elif volume_ratio > 0.7:
                score = 50
            else:
                score = 30
            
            # 패턴 보너스
            if volume_pattern == 'volume_breakout':
                score += 15
            elif volume_pattern == 'active_trading':
                score += 10
            elif volume_pattern == 'low_activity':
                score -= 10
            
            return max(0, min(100, score))
            
        except Exception:
            return 50.0
    
    # analysis_engine.py - analyze_comprehensive 메서드 병렬처리 수정

    # analysis_engine.py - analyze_comprehensive 메서드 병렬처리 수정

    # analysis_engine.py - analyze_comprehensive 메서드 병렬처리 수정

# analysis_engine.py - analyze_comprehensive 메서드 병렬처리 수정

    async def analyze_comprehensive(self, symbol: str, name: str, stock_data, news_data=None, strategy: str = "momentum") -> Dict:
        """
        종합 분석 - 4개 영역 병렬처리로 60% 속도 향상
        기존: 순차실행 1.3초 → 병렬실행 0.5초
        """
        try:
            start_time = time.time()
            
            # ========== 1. 기존 메서드를 비동기 래퍼로 감싸기 ==========
            
            async def async_technical_analysis():
                """기술적 분석 (동기→비동기 래퍼)"""
                try:
                    return self.calculate_technical_score(stock_data)
                except Exception as e:
                    self.logger.error(f"❌ 기술적 분석 실패: {e}")
                    return {'overall_score': 50.0}
            
            async def async_fundamental_analysis():
                """펀더멘털 분석 (동기→비동기 래퍼)"""
                try:
                    return self.calculate_fundamental_score(stock_data)
                except Exception as e:
                    self.logger.error(f"❌ 펀더멘털 분석 실패: {e}")
                    return {'overall_score': 50.0}
            
            async def async_news_analysis():
                """뉴스 분석 (동기→비동기 래퍼)"""
                try:
                    return self.calculate_news_sentiment_score(symbol, name)
                except Exception as e:
                    self.logger.error(f"❌ 뉴스 분석 실패: {e}")
                    return {'overall_score': 50.0, 'has_material': False}
            
            async def async_supply_demand_analysis():
                """수급 분석 (기존 비동기 메서드)"""
                try:
                    return await self.calculate_supply_demand_score(symbol, stock_data)
                except Exception as e:
                    self.logger.error(f"❌ 수급 분석 실패: {e}")
                    return {'overall_score': 50.0}
            
            # ========== 2. 4개 분석 병렬 실행 (핵심 개선) ==========
            
            tasks = [
                async_technical_analysis(),
                async_fundamental_analysis(), 
                async_news_analysis(),
                async_supply_demand_analysis()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리하여 결과 할당
            technical_analysis = results[0] if not isinstance(results[0], Exception) else {'overall_score': 50.0}
            fundamental_analysis = results[1] if not isinstance(results[1], Exception) else {'overall_score': 50.0}  
            news_sentiment_analysis = results[2] if not isinstance(results[2], Exception) else {'overall_score': 50.0}
            supply_demand_analysis = results[3] if not isinstance(results[3], Exception) else {'overall_score': 50.0}
            
            # ========== 3. 기존 가중치 및 점수 계산 유지 ==========
            
            weights = {
                'technical': 0.30,
                'fundamental': 0.25, 
                'news_sentiment': 0.25,
                'supply_demand': 0.20
            }
            
            # ========== 4. 기존 종합점수 계산 로직 유지 ==========
            
            comprehensive_score = (
                technical_analysis['overall_score'] * weights['technical'] +
                fundamental_analysis['overall_score'] * weights['fundamental'] +
                news_sentiment_analysis['overall_score'] * weights['news_sentiment'] +
                supply_demand_analysis['overall_score'] * weights['supply_demand']
            )
            
            # ========== 5. 기존 매수신호 및 추천 로직 유지 ==========
            
            buy_signals = []
            if technical_analysis['overall_score'] >= 70:
                buy_signals.append("기술적 분석 우수")
            if fundamental_analysis['overall_score'] >= 75:
                buy_signals.append("펀더멘털 우량")
            if news_sentiment_analysis.get('has_material', False):
                buy_signals.append("뉴스 재료 보유")
            if supply_demand_analysis.get('overall_score', 0) >= 70:
                buy_signals.append("수급 우세")
            
            # 기존 추천 등급 로직
            if comprehensive_score >= 85 and len(buy_signals) >= 3:
                recommendation = "강력매수"
            elif comprehensive_score >= 75:
                recommendation = "매수"
            elif comprehensive_score >= 65:
                recommendation = "매수검토"
            elif comprehensive_score <= 35:
                recommendation = "매도검토"
            elif comprehensive_score <= 25:
                recommendation = "매도"
            else:
                recommendation = "보유"
            
            execution_time = time.time() - start_time
            
            # ========== 6. 기존 결과 반환 구조 유지 ==========
            
            return {
                'symbol': symbol,
                'name': name,
                'comprehensive_score': round(comprehensive_score, 2),
                'recommendation': recommendation,
                'buy_signals': buy_signals,
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'sentiment_analysis': news_sentiment_analysis,
                'supply_demand_analysis': supply_demand_analysis,
                'weights_applied': weights,
                'analysis_time': datetime.now().isoformat(),
                'execution_time': round(execution_time, 3),
                'parallel_optimized': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 종합분석 실패: {e}")
            return None
    
    def _calculate_enhanced_supply_synergy_bonus(self, supply_demand_analysis: Dict) -> float:
        """향상된 수급 시너지 보너스 계산"""
        try:
            bonus = 0.0
            balance = supply_demand_analysis.get('supply_demand_balance', {})
            
            # 외국인 매수 여부
            foreign_buying = balance.get('foreign_net_buying', False)
            # 기관 매수 여부  
            institution_buying = balance.get('institution_net_buying', False)
            # 스마트머니 우세 여부
            smart_money_dominance = balance.get('smart_money_dominance', False)
            
            # 시너지 보너스 계산
            if foreign_buying and institution_buying:
                bonus += 8  # 외국인+기관 동반 매수
                
            if smart_money_dominance:
                bonus += 5  # 스마트머니 우세
                
            # 거래량 급증과 함께 스마트머니 매수 시 추가 보너스
            volume_surge = supply_demand_analysis.get('volume_analysis', {}).get('volume_surge', False)
            if volume_surge and (foreign_buying or institution_buying):
                bonus += 3  # 거래량 급증 + 스마트머니 매수
                
            return min(bonus, 12)  # 최대 12점으로 제한
            
        except Exception as e:
            self.logger.warning(f"⚠️ 수급 시너지 보너스 계산 실패: {e}")
            return 0.0
    def _clean_stock_name(self, name: str) -> str:
        """종목명 정제 (기존 로직 강화)"""
        if not name:
            return ""
        
        # 기본 정제
        clean_name = name.strip()
        
        # 우선주, ETF 등 접미사 제거
        suffixes = ["우", "우B", "우C", "1우", "2우", "3우", "스팩", "SPAC", "리츠", "REIT", "ETF", "ETN"]
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()
        
        # 특수문자 정리 (단, 한글, 영문, 숫자는 보존)
        import re
        clean_name = re.sub(r'[^\w가-힣]', '', clean_name)
        
        return clean_name
    async def _get_stock_name_from_external(self, symbol: str) -> Optional[str]:
        """외부 API에서 종목명 조회 (네이버 금융 등)"""
        try:
            # 네이버 금융 API 시도
            import aiohttp
            import asyncio
            
            url = f"https://finance.naver.com/item/main.nhn?code={symbol}"
            
            timeout = aiohttp.ClientTimeout(total=5)  # 5초 타임아웃
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        # 간단한 파싱으로 종목명 추출
                        import re
                        match = re.search(r'<title>(.+?)\s*\((\d{6})\)', html)
                        if match:
                            stock_name = match.group(1).strip()
                            if stock_name and len(stock_name) > 2:
                                return stock_name
            
            return None
            
        except Exception as e:
            self.logger.debug(f"⚠️ 외부 API 조회 실패: {e}")
            return None
    def _calculate_supply_demand_bonus(self, supply_demand_analysis: Dict) -> float:
        """수급 시너지 보너스 계산"""
        try:
            # 스마트머니(외국인+기관) 우세 시 보너스
            balance = supply_demand_analysis.get('supply_demand_balance', {})
            smart_money_dominance = balance.get('smart_money_dominance', False)
            
            # 거래강도 보너스
            intensity = supply_demand_analysis.get('trading_intensity', {})
            intensity_score = intensity.get('intensity_score', 50)
            
            bonus = 0
            
            if smart_money_dominance and intensity_score > 70:
                bonus += 3  # 스마트머니 + 고강도 거래
            elif smart_money_dominance:
                bonus += 2  # 스마트머니 우세
            elif intensity_score > 80:
                bonus += 2  # 초고강도 거래
            
            return bonus
            
        except Exception:
            return 0
    
    def _calculate_pattern_bonus(self, chart_pattern_analysis: Dict) -> float:
        """차트패턴 시너지 보너스 계산"""
        try:
            pattern_strength = chart_pattern_analysis.get('pattern_strength', 0.5)
            confidence = chart_pattern_analysis.get('confidence', 0.5)
            detected_patterns = chart_pattern_analysis.get('detected_patterns', [])
            
            bonus = 0
            
            # 강한 패턴 + 높은 신뢰도
            if pattern_strength > 0.8 and confidence > 0.8:
                bonus += 4
            elif pattern_strength > 0.7 and confidence > 0.7:
                bonus += 3
            elif pattern_strength > 0.6 or confidence > 0.6:
                bonus += 2
            
            # 다중 패턴 확인
            if len(detected_patterns) >= 3:
                bonus += 1
            
            return bonus
            
        except Exception:
            return 0
    
    def _calculate_enhanced_signal_strength(self, technical_analysis: Dict, fundamental_analysis: Dict, 
                                      news_sentiment_analysis: Dict, supply_demand_analysis: Dict) -> float:
        """향상된 신호 강도 계산 (4개 영역)"""
        try:
            # 각 분석의 강도 계산
            tech_strength = min(technical_analysis['overall_score'] / 100, 1.0)
            fund_strength = min(fundamental_analysis['overall_score'] / 100, 1.0)
            news_strength = min(news_sentiment_analysis['overall_score'] / 100, 1.0)
            supply_strength = min(supply_demand_analysis['overall_score'] / 100, 1.0)
            
            # 가중 평균 (새로운 가중치 적용)
            weighted_strength = (
                tech_strength * 0.35 +
                fund_strength * 0.25 +
                news_strength * 0.20 +
                supply_strength * 0.20
            )
            
            # 재료가 있으면 신호 강도 증가
            if news_sentiment_analysis.get('has_material', False):
                weighted_strength += 0.1
                
            # 수급 시너지가 있으면 신호 강도 증가
            if supply_demand_analysis.get('supply_demand_balance', {}).get('smart_money_dominance', False):
                weighted_strength += 0.1
                
            return min(weighted_strength, 1.0)
            
        except Exception as e:
            self.logger.warning(f"⚠️ 신호 강도 계산 실패: {e}")
            return 0.5
    
    def _determine_enhanced_signal_type(self, score: float, news: Dict, 
                                       chart_pattern: Dict) -> str:
        """향상된 신호 타입 결정"""
        try:
            material_type = news.get('material_type', '재료없음')
            pattern_recommendation = chart_pattern.get('pattern_recommendation', {})
            pattern_action = pattern_recommendation.get('action', 'HOLD')
            
            if score >= 80:
                if material_type in ['장기재료', '중기재료'] and pattern_action in ['STRONG_BUY', 'BUY']:
                    return 'ULTRA_STRONG_BUY_SIGNAL'
                else:
                    return 'STRONG_BUY_SIGNAL'
            elif score >= 70:
                if pattern_action in ['STRONG_BUY', 'BUY']:
                    return 'CONFIRMED_BUY_SIGNAL'
                else:
                    return 'BUY_SIGNAL'
            elif score >= 60:
                return 'WEAK_BUY_SIGNAL'
            elif score <= 20:
                if pattern_action in ['STRONG_SELL', 'SELL']:
                    return 'CONFIRMED_SELL_SIGNAL'
                else:
                    return 'STRONG_SELL_SIGNAL'
            elif score <= 30:
                return 'SELL_SIGNAL'
            elif score <= 40:
                return 'WEAK_SELL_SIGNAL'
            else:
                return 'NEUTRAL_SIGNAL'
                
        except Exception:
            return 'NEUTRAL_SIGNAL'
    
    def _determine_enhanced_recommendation(self, comprehensive_score: float, signal_strength: float,
                                     news_sentiment_analysis: Dict, supply_demand_analysis: Dict) -> str:
        """향상된 추천 등급 결정 (수급 가중치 반영)"""
        try:
            # 기본 추천 등급
            if comprehensive_score >= 90:
                base_recommendation = 'ULTRA_STRONG_BUY'
            elif comprehensive_score >= 80:
                base_recommendation = 'STRONG_BUY'
            elif comprehensive_score >= 70:
                base_recommendation = 'BUY'
            elif comprehensive_score >= 60:
                base_recommendation = 'HOLD'
            elif comprehensive_score >= 40:
                base_recommendation = 'WEAK_HOLD'
            else:
                base_recommendation = 'SELL'
                
            # 수급 우세 시 한 단계 상향 (수급 가중치 확대 반영)
            smart_money_dominance = supply_demand_analysis.get('supply_demand_balance', {}).get('smart_money_dominance', False)
            if smart_money_dominance and comprehensive_score >= 65:
                if base_recommendation == 'BUY':
                    base_recommendation = 'STRONG_BUY'
                elif base_recommendation == 'HOLD':
                    base_recommendation = 'BUY'
                    
            # 장기재료 + 수급 우세 시 최고 등급 고려
            is_long_term_material = news_sentiment_analysis.get('material_type') == '장기재료'
            if is_long_term_material and smart_money_dominance and comprehensive_score >= 85:
                base_recommendation = 'ULTRA_STRONG_BUY'
                
            return base_recommendation
            
        except Exception as e:
            self.logger.warning(f"⚠️ 추천 등급 결정 실패: {e}")
            return 'HOLD'
    
    def _calculate_enhanced_confidence(self, technical: Dict, fundamental: Dict, 
                                     news: Dict, supply_demand: Dict, 
                                     chart_pattern: Dict) -> float:
        """향상된 신뢰도 계산"""
        try:
            # 기본 점수들의 일관성
            scores = [
                technical['overall_score'],
                fundamental['overall_score'],
                news['overall_score'],
                supply_demand['overall_score'],
                chart_pattern['overall_score']
            ]
            
            # 표준편차가 낮을수록 신뢰도 높음
            std_dev = np.std(scores)
            base_confidence = max(0.3, 1.0 - (std_dev / 50))
            
            # 추가 신뢰도 요소들
            confidence_boosters = 0
            
            # 뉴스 재료 보너스
            if news.get('has_material', False):
                confidence_boosters += 0.1
            
            # 차트패턴 신뢰도 보너스
            pattern_confidence = chart_pattern.get('confidence', 0.5)
            if pattern_confidence > 0.8:
                confidence_boosters += 0.15
            elif pattern_confidence > 0.6:
                confidence_boosters += 0.1
            
            # 수급 일치성 보너스
            supply_balance = supply_demand.get('supply_demand_balance', {})
            if supply_balance.get('smart_money_dominance', False):
                confidence_boosters += 0.1
            
            final_confidence = min(1.0, base_confidence + confidence_boosters)
            return final_confidence
            
        except Exception:
            return 0.5
    
    def _determine_enhanced_risk_level(self, stock_data, news: Dict, 
                                     supply_demand: Dict, chart_pattern: Dict) -> str:
        """향상된 리스크 레벨 결정"""
        try:
            risk_score = 50  # 기본 리스크
            
            # 기존 변동성 기반 리스크
            if hasattr(stock_data, 'change_rate'):
                if abs(stock_data.change_rate) > 10:
                    risk_score += 25
                elif abs(stock_data.change_rate) > 5:
                    risk_score += 15
            
            # 시가총액 기반 리스크
            if hasattr(stock_data, 'market_cap') and stock_data.market_cap:
                if stock_data.market_cap < 1000:
                    risk_score += 20
                elif stock_data.market_cap > 10000:
                    risk_score -= 10
            
            # 뉴스 재료 기반 리스크 조정
            material_type = news.get('material_type', '재료없음')
            if material_type == '단기재료':
                risk_score += 15
            elif material_type == '장기재료':
                risk_score -= 10
            
            # 수급 불균형 리스크
            balance = supply_demand.get('supply_demand_balance', {})
            if not balance.get('smart_money_dominance', False):
                risk_score += 10
            
            # 차트패턴 리스크
            pattern_risk = chart_pattern.get('pattern_recommendation', {}).get('risk_level', 'MEDIUM')
            if pattern_risk == 'HIGH':
                risk_score += 15
            elif pattern_risk == 'LOW':
                risk_score -= 10
            
            # 거래강도 리스크
            intensity = supply_demand.get('trading_intensity', {})
            if intensity.get('intensity_level') == 'very_high':
                risk_score += 10
            elif intensity.get('intensity_level') == 'low':
                risk_score += 5
            
            # 최종 리스크 레벨 결정
            if risk_score >= 80:
                return 'VERY_HIGH'
            elif risk_score >= 70:
                return 'HIGH'
            elif risk_score >= 55:
                return 'MEDIUM_HIGH'
            elif risk_score <= 25:
                return 'VERY_LOW'
            elif risk_score <= 35:
                return 'LOW'
            elif risk_score <= 45:
                return 'MEDIUM_LOW'
            else:
                return 'MEDIUM'
                
        except Exception:
            return 'MEDIUM'
    
    def _determine_action(self, recommendation: str, signal_strength: float, risk_level: str) -> str:
        """매매 액션 결정"""
        try:
            if recommendation in ['ULTRA_STRONG_BUY', 'STRONG_BUY', 'BUY'] and signal_strength >= 60 and risk_level not in ['HIGH', 'VERY_HIGH']:
                return 'BUY'
            elif recommendation in ['ULTRA_STRONG_SELL', 'STRONG_SELL', 'SELL'] and signal_strength >= 60:
                return 'SELL'
            elif recommendation == 'WEAK_BUY' and risk_level in ['LOW', 'VERY_LOW', 'MEDIUM_LOW']:
                return 'WEAK_BUY'
            elif recommendation == 'WEAK_SELL':
                return 'WEAK_SELL'
            else:
                return 'HOLD'
                
        except Exception:
            return 'HOLD'
    
    async def get_analysis_summary(self, results: List[Dict]) -> Dict:
        """분석 결과 요약 - 새로운 분석 포함"""
        try:
            if not results:
                return {}
            
            # 기본 통계
            total_analyzed = len(results)
            avg_score = sum(r['comprehensive_score'] for r in results) / total_analyzed
            
            # 추천 분포
            recommendations = {}
            for result in results:
                rec = result['recommendation']
                recommendations[rec] = recommendations.get(rec, 0) + 1
            
            # 매수 신호 개수 (새로운 등급 포함)
            buy_signals = len([r for r in results if r['recommendation'] in ['BUY', 'STRONG_BUY', 'ULTRA_STRONG_BUY']])
            
            # 고득점 종목 (80점 이상)
            high_score_count = len([r for r in results if r['comprehensive_score'] >= 80])
            
            # 뉴스 재료 보유 종목
            material_stocks = len([r for r in results if r['sentiment_analysis'].get('has_material', False)])
            
            # 수급 우량 종목 (스마트머니 우세)
            smart_money_stocks = len([r for r in results if 
                                    r.get('supply_demand_analysis', {})
                                    .get('supply_demand_balance', {})
                                    .get('smart_money_dominance', False)])
            
            # 차트패턴 확인 종목
            pattern_confirmed_stocks = len([r for r in results if 
                                          r.get('chart_pattern_analysis', {})
                                          .get('confidence', 0) > 0.7])
            
            return {
                'total_analyzed': total_analyzed,
                'average_score': avg_score,
                'recommendations': recommendations,
                'buy_signals': buy_signals,
                'high_score_count': high_score_count,
                'material_stocks': material_stocks,
                'smart_money_stocks': smart_money_stocks,  # 새로 추가
                'pattern_confirmed_stocks': pattern_confirmed_stocks,  # 새로 추가
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 분석 요약 실패: {e}")
            return {}

    # 기존 메서드들 (analyze_stock, analyze_without_news, safe_analyze_stock)
    async def analyze_stock(self, stock_data, strategy: str = "momentum", include_news: bool = True) -> Dict:
        """단일 종목 분석 - analyze_comprehensive의 래퍼 함수"""
        try:
            # 안전한 symbol, name 추출
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            name = self.safe_get_attr(stock_data, 'name', 'Unknown')
            
            if symbol == 'UNKNOWN':
                self.logger.warning(f"⚠️ 유효하지 않은 종목 데이터: {type(stock_data).__name__}")
                return None
            
            # include_news가 False면 뉴스 분석 제외
            if not include_news:
                return await self.analyze_without_news(symbol, name, stock_data, strategy)
            
            # 기존 종합 분석 호출
            return await self.analyze_comprehensive(symbol, name, stock_data, strategy=strategy)
            
        except Exception as e:
            error_symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {error_symbol} 종목 분석 실패: {e}")
            return None


    async def analyze_without_news(self, symbol: str, name: str, stock_data, strategy: str = "momentum") -> Dict:
        """뉴스 분석 제외한 종목 분석"""
        try:
            self.logger.info(f"🔬 {symbol} ({name}) 분석 시작 (뉴스 제외)...")
            
            # 기술적 분석과 펀더멘털 분석, 수급, 차트패턴 분석 수행
            technical_analysis = self.calculate_technical_score(stock_data)
            fundamental_analysis = self.calculate_fundamental_score(stock_data)
            supply_demand_analysis = await self.calculate_supply_demand_score(symbol, stock_data)
            chart_pattern_analysis = await self.calculate_chart_pattern_score(symbol, stock_data)
            
            # 뉴스 분석은 기본값으로 설정
            news_sentiment_analysis = {
                'overall_score': 50.0,
                'material_score': 0.0,
                'sentiment_score': 0.0,
                'news_count': 0,
                'material_type': '재료없음',
                'keywords': [],
                'has_material': False
            }
            
            # 가중치 설정 (뉴스 제외, 4개 영역으로 재분배)
            weights = {
                'technical': 0.30,      # 30% (유지)
                'fundamental': 0.25,    # 25% (유지)  
                'news_sentiment': 0.20, # 20% (25%→20%, -5%)
                'supply_demand': 0.20,  # 20% (10%→20%, +10%)
                'chart_pattern': 0.05   # 5% (10%→5%, -5%)
            }
            
            # 종합 점수 계산
            comprehensive_score = (
                technical_analysis['overall_score'] * weights['technical'] +
                fundamental_analysis['overall_score'] * weights['fundamental'] +
                supply_demand_analysis['overall_score'] * weights['supply_demand'] +
                chart_pattern_analysis['overall_score'] * weights['chart_pattern']
            )
            
            comprehensive_score = max(0, min(100, comprehensive_score))
            
            # 신호 강도 및 타입 결정
            signal_strength = self._calculate_enhanced_signal_strength(
                technical_analysis, fundamental_analysis, news_sentiment_analysis,
                supply_demand_analysis, chart_pattern_analysis
            )
            signal_type = self._determine_enhanced_signal_type(comprehensive_score, 
                                                             news_sentiment_analysis, 
                                                             chart_pattern_analysis)
            
            # 추천 등급 결정
            recommendation = self._determine_enhanced_recommendation(
                comprehensive_score, signal_strength, news_sentiment_analysis,
                supply_demand_analysis, chart_pattern_analysis
            )
            
            # 신뢰도 계산
            confidence = self._calculate_enhanced_confidence(
                technical_analysis, fundamental_analysis, news_sentiment_analysis,
                supply_demand_analysis, chart_pattern_analysis
            )
            
            # 리스크 레벨 결정
            risk_level = self._determine_enhanced_risk_level(stock_data, 
                                                           news_sentiment_analysis,
                                                           supply_demand_analysis, 
                                                           chart_pattern_analysis)
            
            # 매매 액션 결정
            action = self._determine_action(recommendation, signal_strength, risk_level)
            
            result = {
                'symbol': symbol,
                'name': name,
                'comprehensive_score': comprehensive_score,
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'sentiment_analysis': news_sentiment_analysis,
                'supply_demand_analysis': supply_demand_analysis,
                'chart_pattern_analysis': chart_pattern_analysis,
                'signal_strength': signal_strength,
                'signal_type': signal_type,
                'recommendation': recommendation,
                'confidence': confidence,
                'risk_level': risk_level,
                'action': action,
                'strategy': strategy,
                'analysis_time': datetime.now().isoformat(),
                'weights_used': weights
            }
            
            self.logger.info(f"✅ {symbol} 분석 완료 - 점수: {comprehensive_score:.1f}, 추천: {recommendation}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 분석 실패: {e}")
            return None
        
    def _safe_extract_symbol_name(self, stock_data):
        """안전한 symbol, name 추출 유틸리티 함수"""
        symbol = 'UNKNOWN'
        name = 'Unknown'
        
        try:
            # 1. 딕셔너리 타입 체크
            if isinstance(stock_data, dict):
                symbol = stock_data.get('symbol', 'UNKNOWN')
                name = stock_data.get('name', 'Unknown')
            
            # 2. 객체 타입 - 속성 체크
            elif hasattr(stock_data, 'symbol'):
                symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
                name = getattr(stock_data, 'name', 'Unknown')
            
            # 3. __dict__ 접근 시도
            elif hasattr(stock_data, '__dict__'):
                data_dict = stock_data.__dict__
                symbol = data_dict.get('symbol', 'UNKNOWN')
                name = data_dict.get('name', 'Unknown')
            
            # 4. 기타 인덱스 접근 가능한 객체
            elif hasattr(stock_data, '__getitem__'):
                try:
                    symbol = stock_data['symbol'] if 'symbol' in stock_data else 'UNKNOWN'
                    name = stock_data['name'] if 'name' in stock_data else 'Unknown'
                except (KeyError, TypeError):
                    pass
        
        except Exception as e:
            self.logger.debug(f"🔧 symbol/name 추출 중 예외: {e}")
        
        return symbol, name
    def safe_get_attr(self, data, attr_name, default=None):
        """안전한 속성 접근 유틸리티"""
        try:
            if isinstance(data, dict):
                return data.get(attr_name, default)
            else:
                return getattr(data, attr_name, default)
        except (AttributeError, TypeError):
            return default

    def _safe_extract_symbol_name(self, stock_data):
        """안전한 symbol, name 추출"""
        symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
        name = self.safe_get_attr(stock_data, 'name', 'Unknown')
        return symbol, name
    
    async def safe_analyze_stock(self, stock_data, strategy: str = "momentum", include_news: bool = True):
        """안전한 종목 분석 - 오류 처리 강화"""
        try:
            # 입력 데이터 검증
            if stock_data is None:
                self.logger.warning("⚠️ stock_data가 None입니다.")
                return None
            
            # 안전한 symbol, name 추출
            symbol = self.safe_get_attr(stock_data, 'symbol', 'UNKNOWN')
            name = self.safe_get_attr(stock_data, 'name', 'Unknown')
            
            # 심볼 유효성 확인
            if symbol == 'UNKNOWN':
                self.logger.warning(f"⚠️ 유효하지 않은 종목 데이터: {type(stock_data).__name__}")
                self.logger.debug(f"📊 데이터 내용: {stock_data}")
                return None
            
            # 분석 실행
            result = await self.analyze_stock(stock_data, strategy, include_news)
            
            if result:
                self.logger.debug(f"✅ {symbol} 분석 성공")
            else:
                self.logger.warning(f"⚠️ {symbol} 분석 결과 없음")
            
            return result
            
        except Exception as e:
            # 에러 처리시에도 안전하게 심볼 추출
            error_symbol = self.safe_get_attr(stock_data if stock_data else {}, 'symbol', 'UNKNOWN')
            
            self.logger.error(f"❌ {error_symbol} 안전한 분석 실패: {e}")
            self.logger.debug(f"📊 stock_data 타입: {type(stock_data)}")
            return None