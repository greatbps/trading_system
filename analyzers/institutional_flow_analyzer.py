#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/institutional_flow_analyzer.py

세력 자금 흐름 분석기 - 기관/외국인 매집 감지 및 평균 매수가 추정
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import deque
import math

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer


@dataclass
class AccumulationSignal:
    """매집 신호 데이터"""
    symbol: str
    is_accumulating: bool
    accumulation_strength: float  # 0-100
    accumulation_period_days: int
    estimated_avg_cost: float
    institutional_ownership_change: float
    foreign_ownership_change: float
    volume_profile_support: float
    price_support_level: float
    confidence_score: float
    key_indicators: List[str]
    risk_factors: List[str]
    timestamp: datetime


@dataclass
class SmartMoneyFlow:
    """스마트머니 흐름 분석"""
    net_institutional_flow: float  # 기관 순매수금액
    net_foreign_flow: float        # 외국인 순매수금액
    institutional_avg_price: float # 기관 평균 매수가
    foreign_avg_price: float       # 외국인 평균 매수가
    accumulation_zone_low: float   # 매집구간 저점
    accumulation_zone_high: float  # 매집구간 고점
    volume_weighted_avg_price: float # 거래량 가중 평균가
    flow_consistency: float        # 자금 흐름 일관성
    smart_money_confidence: float  # 스마트머니 신뢰도


class InstitutionalFlowAnalyzer:
    """세력 자금 흐름 분석기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("InstitutionalFlowAnalyzer")
        self.gemini_analyzer = GeminiAnalyzer(config)
        
        # 분석 파라미터
        self.analysis_params = {
            'accumulation_period': 20,      # 매집 분석 기간 (일)
            'volume_surge_threshold': 2.0,  # 거래량 급증 임계값
            'price_stability_threshold': 0.03,  # 가격 안정성 임계값 (3%)
            'institutional_threshold': 1000000000,  # 기관 매수 최소 금액 (10억)
            'consistency_period': 10,       # 일관성 체크 기간
            'confidence_threshold': 0.7     # 신뢰도 임계값
        }
        
        # 매집 패턴 가중치
        self.pattern_weights = {
            'volume_accumulation': 0.25,    # 거래량 매집
            'price_support': 0.20,          # 가격 지지
            'institutional_flow': 0.20,     # 기관 자금 흐름
            'foreign_flow': 0.15,           # 외국인 자금 흐름
            'technical_support': 0.10,      # 기술적 지지
            'market_structure': 0.10        # 시장 구조
        }
        
        self.logger.info("🏦 세력 자금 흐름 분석기 초기화 완료")
    
    async def detect_institutional_accumulation(self, symbol: str, 
                                              price_data: List[Dict],
                                              institutional_data: List[Dict] = None,
                                              foreign_data: List[Dict] = None) -> AccumulationSignal:
        """기관/외국인 매집 감지"""
        try:
            self.logger.info(f"🔍 {symbol} 세력 매집 분석 시작")
            
            if len(price_data) < self.analysis_params['accumulation_period']:
                self.logger.warning(f"⚠️ {symbol} 데이터 부족 - 분석 불가")
                return self._create_empty_accumulation_signal(symbol)
            
            # 1. 거래량 매집 분석
            volume_accumulation = await self._analyze_volume_accumulation(symbol, price_data)
            
            # 2. 가격 지지선 분석
            price_support = await self._analyze_price_support_levels(symbol, price_data)
            
            # 3. 기관 자금 흐름 분석
            institutional_flow = await self._analyze_institutional_flow(
                symbol, institutional_data or [], price_data
            )
            
            # 4. 외국인 자금 흐름 분석
            foreign_flow = await self._analyze_foreign_flow(
                symbol, foreign_data or [], price_data
            )
            
            # 5. 기술적 지지 분석
            technical_support = await self._analyze_technical_support(symbol, price_data)
            
            # 6. 시장 구조 분석
            market_structure = await self._analyze_market_structure(symbol, price_data)
            
            # 7. 종합 매집 점수 계산
            accumulation_score = self._calculate_accumulation_score(
                volume_accumulation, price_support, institutional_flow,
                foreign_flow, technical_support, market_structure
            )
            
            # 8. 세력 평균 매수가 추정
            estimated_avg_cost = await self._estimate_institutional_avg_cost(
                symbol, price_data, institutional_data, foreign_data,
                volume_accumulation, price_support
            )
            
            # 9. AI 기반 종합 분석
            ai_analysis = await self._get_ai_accumulation_analysis(
                symbol, accumulation_score, estimated_avg_cost, 
                volume_accumulation, institutional_flow, foreign_flow
            )
            
            # 10. 최종 매집 신호 생성
            accumulation_signal = self._generate_accumulation_signal(
                symbol, accumulation_score, estimated_avg_cost,
                volume_accumulation, price_support, institutional_flow, foreign_flow,
                ai_analysis
            )
            
            self.logger.info(f"✅ {symbol} 매집 분석 완료 - 강도: {accumulation_score:.1f}, 평균가: {estimated_avg_cost:,.0f}원")
            return accumulation_signal
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 매집 분석 실패: {e}")
            return self._create_empty_accumulation_signal(symbol)
    
    async def _analyze_volume_accumulation(self, symbol: str, price_data: List[Dict]) -> Dict[str, Any]:
        """거래량 매집 패턴 분석"""
        try:
            df = pd.DataFrame(price_data)
            df['volume'] = df['volume'].astype(float)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            # 평균 거래량 계산
            avg_volume = df['volume'].rolling(20).mean()
            recent_avg_volume = avg_volume.iloc[-10:].mean()
            
            # 거래량 급증일 탐지
            volume_surge_days = (df['volume'] > avg_volume * self.analysis_params['volume_surge_threshold']).sum()
            
            # 누적 거래량 추세
            volume_trend = np.polyfit(range(len(df)), df['volume'], 1)[0]
            
            # 거래량과 가격의 상관관계
            price_volume_correlation = df['close'].corr(df['volume'])
            
            # OBV (On-Balance Volume) 계산
            obv = self._calculate_obv(df)
            obv_trend = np.polyfit(range(len(obv)), obv, 1)[0]
            
            # 거래량 분포 분석
            volume_concentration = self._analyze_volume_concentration(df)
            
            # 매집 점수 계산
            accumulation_score = 0
            
            # 거래량 급증 (30점)
            if volume_surge_days >= 5:
                accumulation_score += 30
            elif volume_surge_days >= 3:
                accumulation_score += 20
            elif volume_surge_days >= 1:
                accumulation_score += 10
            
            # OBV 상승 추세 (25점)
            if obv_trend > 0:
                obv_strength = min(25, abs(obv_trend) / recent_avg_volume * 100)
                accumulation_score += obv_strength
            
            # 거래량 집중도 (20점)
            accumulation_score += min(20, volume_concentration * 20)
            
            # 가격-거래량 상관관계 (15점)
            if price_volume_correlation > 0.3:
                accumulation_score += 15
            elif price_volume_correlation > 0.1:
                accumulation_score += 10
            elif price_volume_correlation > -0.1:
                accumulation_score += 5
            
            # 거래량 추세 (10점)
            if volume_trend > 0:
                accumulation_score += 10
            
            return {
                'score': min(100, accumulation_score),
                'volume_surge_days': volume_surge_days,
                'obv_trend': obv_trend,
                'price_volume_correlation': price_volume_correlation,
                'volume_concentration': volume_concentration,
                'recent_avg_volume': recent_avg_volume,
                'indicators': self._get_volume_indicators(accumulation_score)
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 거래량 매집 분석 실패: {e}")
            return {'score': 0, 'indicators': ['분석 실패']}
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """OBV (On-Balance Volume) 계산"""
        obv = []
        obv_value = 0
        
        for i in range(len(df)):
            if i == 0:
                obv_value = df.iloc[i]['volume']
            else:
                if df.iloc[i]['close'] > df.iloc[i-1]['close']:
                    obv_value += df.iloc[i]['volume']
                elif df.iloc[i]['close'] < df.iloc[i-1]['close']:
                    obv_value -= df.iloc[i]['volume']
                # 동가면 변화없음
            
            obv.append(obv_value)
        
        return pd.Series(obv)
    
    def _analyze_volume_concentration(self, df: pd.DataFrame) -> float:
        """거래량 집중도 분석 (특정 가격대에 거래량이 집중되었는지)"""
        try:
            # 가격 구간별 거래량 집계
            price_range = df['high'].max() - df['low'].min()
            if price_range == 0:
                return 0
            
            # 5% 구간으로 나누어 거래량 집계
            num_bins = max(5, min(20, int(price_range / (df['close'].mean() * 0.05))))
            
            price_bins = pd.cut(df['close'], bins=num_bins)
            volume_by_price = df.groupby(price_bins)['volume'].sum()
            
            # 최대 거래량 구간의 비율
            max_volume_ratio = volume_by_price.max() / volume_by_price.sum()
            
            # 상위 3개 구간의 거래량 비율
            top3_volume_ratio = volume_by_price.nlargest(3).sum() / volume_by_price.sum()
            
            # 집중도 점수 (0-1)
            concentration_score = (max_volume_ratio * 0.6 + top3_volume_ratio * 0.4)
            
            return min(1.0, concentration_score)
            
        except Exception:
            return 0.0
    
    def _get_volume_indicators(self, score: float) -> List[str]:
        """거래량 매집 지표 설명"""
        indicators = []
        if score >= 80:
            indicators.extend(['대량 매집 진행중', '거래량 급증 지속'])
        elif score >= 60:
            indicators.extend(['매집 신호 강화', '거래량 증가 추세'])
        elif score >= 40:
            indicators.extend(['부분적 매집', '거래량 관심 필요'])
        else:
            indicators.extend(['매집 신호 약함', '거래량 분석 부족'])
        
        return indicators
    
    async def _analyze_price_support_levels(self, symbol: str, price_data: List[Dict]) -> Dict[str, Any]:
        """가격 지지선 분석"""
        try:
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            current_price = df['close'].iloc[-1]
            
            # 주요 지지선 찾기
            support_levels = self._find_support_levels(df)
            
            # 현재가 근처 지지선
            nearby_supports = [level for level in support_levels 
                             if abs(current_price - level) / current_price < 0.05]  # 5% 내
            
            # 가격 안정성 계산 (최근 10일간 변동성)
            recent_volatility = df['close'].iloc[-10:].std() / df['close'].iloc[-10:].mean()
            price_stability = max(0, 1 - recent_volatility / 0.05)  # 5% 기준으로 정규화
            
            # 지지선 테스트 횟수
            support_test_count = 0
            strongest_support = None
            
            if support_levels:
                strongest_support = min(support_levels, key=lambda x: abs(current_price - x))
                
                # 지지선 테스트 횟수 계산
                for _, row in df.iterrows():
                    if abs(row['low'] - strongest_support) / strongest_support < 0.02:  # 2% 내
                        support_test_count += 1
            
            # 지지선 강도 점수
            support_score = 0
            
            # 근처 지지선 존재 (40점)
            if nearby_supports:
                support_score += 40
                if len(nearby_supports) >= 2:
                    support_score += 10  # 복수 지지선
            
            # 가격 안정성 (30점)
            support_score += price_stability * 30
            
            # 지지선 테스트 (20점)
            if support_test_count >= 3:
                support_score += 20
            elif support_test_count >= 2:
                support_score += 15
            elif support_test_count >= 1:
                support_score += 10
            
            # 상승 추세 중 조정 (10점)
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            if current_price > ma20 * 0.95:  # 20일 이평선 근처
                support_score += 10
            
            return {
                'score': min(100, support_score),
                'support_levels': support_levels,
                'strongest_support': strongest_support,
                'support_test_count': support_test_count,
                'price_stability': price_stability,
                'nearby_supports': nearby_supports,
                'current_price': current_price,
                'indicators': self._get_support_indicators(support_score, support_test_count)
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 가격 지지선 분석 실패: {e}")
            return {'score': 0, 'indicators': ['분석 실패']}
    
    def _find_support_levels(self, df: pd.DataFrame) -> List[float]:
        """주요 지지선 탐지"""
        try:
            # 로컬 저점 찾기
            lows = df['low'].values
            support_levels = []
            
            window = 5  # 앞뒤 5일 체크
            
            for i in range(window, len(lows) - window):
                is_local_min = True
                current_low = lows[i]
                
                # 앞뒤 확인
                for j in range(i - window, i + window + 1):
                    if j != i and lows[j] <= current_low:
                        is_local_min = False
                        break
                
                if is_local_min:
                    support_levels.append(current_low)
            
            # 중복 제거 (2% 내 유사한 레벨)
            unique_supports = []
            support_levels.sort()
            
            for level in support_levels:
                is_unique = True
                for existing in unique_supports:
                    if abs(level - existing) / existing < 0.02:  # 2% 내
                        is_unique = False
                        break
                
                if is_unique:
                    unique_supports.append(level)
            
            return unique_supports
            
        except Exception:
            return []
    
    def _get_support_indicators(self, score: float, test_count: int) -> List[str]:
        """가격 지지선 지표 설명"""
        indicators = []
        if score >= 80:
            indicators.extend(['강력한 가격 지지', f'지지선 {test_count}회 테스트'])
        elif score >= 60:
            indicators.extend(['가격 지지 확인', '매집구간 형성'])
        elif score >= 40:
            indicators.extend(['부분적 지지', '추가 확인 필요'])
        else:
            indicators.extend(['지지선 불분명', '가격 불안정'])
        
        return indicators
    
    async def _analyze_institutional_flow(self, symbol: str, institutional_data: List[Dict], 
                                        price_data: List[Dict]) -> Dict[str, Any]:
        """기관 자금 흐름 분석"""
        try:
            if not institutional_data:
                # 실제 기관 데이터가 없으면 거래량 패턴으로 추정
                return await self._estimate_institutional_flow_from_volume(symbol, price_data)
            
            df_inst = pd.DataFrame(institutional_data)
            
            # 기관 순매수 금액 계산
            df_inst['net_buy'] = df_inst.get('buy_amount', 0) - df_inst.get('sell_amount', 0)
            
            # 최근 매집 기간의 기관 흐름
            recent_net_buy = df_inst['net_buy'].iloc[-self.analysis_params['accumulation_period']:].sum()
            
            # 연속 매수일 계산
            consecutive_buy_days = 0
            for net_buy in reversed(df_inst['net_buy'].iloc[-20:]):
                if net_buy > 0:
                    consecutive_buy_days += 1
                else:
                    break
            
            # 기관 매수 일관성
            buy_days = (df_inst['net_buy'] > 0).sum()
            total_days = len(df_inst)
            consistency = buy_days / total_days if total_days > 0 else 0
            
            # 매수 강도 (평균 대비)
            avg_net_buy = df_inst['net_buy'].mean()
            buy_intensity = recent_net_buy / avg_net_buy if avg_net_buy != 0 else 0
            
            # 기관 흐름 점수 계산
            flow_score = 0
            
            # 순매수 금액 (40점)
            if recent_net_buy > self.analysis_params['institutional_threshold']:
                flow_score += 40
            elif recent_net_buy > self.analysis_params['institutional_threshold'] * 0.5:
                flow_score += 30
            elif recent_net_buy > 0:
                flow_score += 20
            
            # 연속 매수일 (25점)
            if consecutive_buy_days >= 5:
                flow_score += 25
            elif consecutive_buy_days >= 3:
                flow_score += 20
            elif consecutive_buy_days >= 1:
                flow_score += 15
            
            # 매수 일관성 (20점)
            flow_score += consistency * 20
            
            # 매수 강도 (15점)
            if buy_intensity > 2:
                flow_score += 15
            elif buy_intensity > 1.5:
                flow_score += 12
            elif buy_intensity > 1:
                flow_score += 8
            
            return {
                'score': min(100, flow_score),
                'net_buy_amount': recent_net_buy,
                'consecutive_buy_days': consecutive_buy_days,
                'buy_consistency': consistency,
                'buy_intensity': buy_intensity,
                'indicators': self._get_institutional_indicators(flow_score, consecutive_buy_days)
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 기관 흐름 분석 실패: {e}")
            return {'score': 0, 'indicators': ['분석 실패']}
    
    async def _estimate_institutional_flow_from_volume(self, symbol: str, 
                                                     price_data: List[Dict]) -> Dict[str, Any]:
        """거래량 패턴으로 기관 흐름 추정"""
        try:
            df = pd.DataFrame(price_data)
            df['volume'] = df['volume'].astype(float)
            df['close'] = df['close'].astype(float)
            
            # 대량 거래일 탐지 (평균의 2배 이상)
            avg_volume = df['volume'].mean()
            large_volume_days = df[df['volume'] > avg_volume * 2]
            
            # 대량 거래일의 가격 변화
            institutional_buying_score = 0
            
            for _, day in large_volume_days.iterrows():
                # 대량 거래 + 상승 = 기관 매수 가능성
                day_change = day.get('change_rate', 0)
                if day_change > 1:  # 1% 이상 상승
                    institutional_buying_score += 20
                elif day_change > 0:
                    institutional_buying_score += 10
                elif day_change < -1:  # 1% 이상 하락
                    institutional_buying_score -= 10
            
            # 최근 거래량 증가 추세
            recent_volumes = df['volume'].iloc[-10:]
            earlier_volumes = df['volume'].iloc[-20:-10]
            
            if recent_volumes.mean() > earlier_volumes.mean():
                institutional_buying_score += 15
            
            estimated_score = max(0, min(100, institutional_buying_score))
            
            return {
                'score': estimated_score,
                'net_buy_amount': 0,  # 추정 불가
                'consecutive_buy_days': 0,
                'buy_consistency': estimated_score / 100,
                'buy_intensity': len(large_volume_days) / len(df),
                'indicators': [f'거래량 패턴 추정 (점수: {estimated_score})']
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 기관 흐름 추정 실패: {e}")
            return {'score': 0, 'indicators': ['추정 실패']}
    
    def _get_institutional_indicators(self, score: float, consecutive_days: int) -> List[str]:
        """기관 흐름 지표 설명"""
        indicators = []
        if score >= 80:
            indicators.extend(['기관 대량 매집', f'{consecutive_days}일 연속 매수'])
        elif score >= 60:
            indicators.extend(['기관 매수 지속', '순매수 우세'])
        elif score >= 40:
            indicators.extend(['기관 관심 증가', '부분적 매수'])
        else:
            indicators.extend(['기관 흐름 약함', '매수세 부족'])
        
        return indicators
    
    async def _analyze_foreign_flow(self, symbol: str, foreign_data: List[Dict], 
                                  price_data: List[Dict]) -> Dict[str, Any]:
        """외국인 자금 흐름 분석 (기관 분석과 유사한 로직)"""
        try:
            if not foreign_data:
                return await self._estimate_foreign_flow_from_volume(symbol, price_data)
            
            df_foreign = pd.DataFrame(foreign_data)
            df_foreign['net_buy'] = df_foreign.get('buy_amount', 0) - df_foreign.get('sell_amount', 0)
            
            recent_net_buy = df_foreign['net_buy'].iloc[-self.analysis_params['accumulation_period']:].sum()
            
            consecutive_buy_days = 0
            for net_buy in reversed(df_foreign['net_buy'].iloc[-20:]):
                if net_buy > 0:
                    consecutive_buy_days += 1
                else:
                    break
            
            buy_days = (df_foreign['net_buy'] > 0).sum()
            total_days = len(df_foreign)
            consistency = buy_days / total_days if total_days > 0 else 0
            
            # 외국인은 기관보다 임계값을 낮게 설정 (더 민감하게)
            foreign_threshold = self.analysis_params['institutional_threshold'] * 0.5
            
            flow_score = 0
            
            if recent_net_buy > foreign_threshold:
                flow_score += 40
            elif recent_net_buy > foreign_threshold * 0.5:
                flow_score += 30
            elif recent_net_buy > 0:
                flow_score += 20
            
            if consecutive_buy_days >= 3:
                flow_score += 25
            elif consecutive_buy_days >= 2:
                flow_score += 20
            elif consecutive_buy_days >= 1:
                flow_score += 15
            
            flow_score += consistency * 20
            
            return {
                'score': min(100, flow_score),
                'net_buy_amount': recent_net_buy,
                'consecutive_buy_days': consecutive_buy_days,
                'buy_consistency': consistency,
                'indicators': self._get_foreign_indicators(flow_score, consecutive_buy_days)
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 외국인 흐름 분석 실패: {e}")
            return {'score': 0, 'indicators': ['분석 실패']}
    
    async def _estimate_foreign_flow_from_volume(self, symbol: str, 
                                               price_data: List[Dict]) -> Dict[str, Any]:
        """거래량 패턴으로 외국인 흐름 추정"""
        # 기관과 유사하지만 더 변동성 있는 패턴으로 추정
        try:
            df = pd.DataFrame(price_data)
            df['volume'] = df['volume'].astype(float)
            df['close'] = df['close'].astype(float)
            
            # 외국인은 변동성을 더 선호한다고 가정
            volatility = df['close'].pct_change().std()
            high_volatility_bonus = min(20, volatility * 1000)  # 변동성 보너스
            
            avg_volume = df['volume'].mean()
            large_volume_days = df[df['volume'] > avg_volume * 1.5]  # 기관보다 낮은 임계값
            
            foreign_buying_score = high_volatility_bonus
            
            for _, day in large_volume_days.iterrows():
                day_change = day.get('change_rate', 0)
                if abs(day_change) > 2:  # 2% 이상 변동 (상승/하락 무관)
                    foreign_buying_score += 15
                elif abs(day_change) > 1:
                    foreign_buying_score += 10
            
            estimated_score = max(0, min(100, foreign_buying_score))
            
            return {
                'score': estimated_score,
                'net_buy_amount': 0,
                'consecutive_buy_days': 0,
                'buy_consistency': estimated_score / 100,
                'indicators': [f'거래량 패턴 추정 (점수: {estimated_score})']
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 외국인 흐름 추정 실패: {e}")
            return {'score': 0, 'indicators': ['추정 실패']}
    
    def _get_foreign_indicators(self, score: float, consecutive_days: int) -> List[str]:
        """외국인 흐름 지표 설명"""
        indicators = []
        if score >= 80:
            indicators.extend(['외국인 대량 매집', f'{consecutive_days}일 연속 매수'])
        elif score >= 60:
            indicators.extend(['외국인 매수 지속', '해외 자금 유입'])
        elif score >= 40:
            indicators.extend(['외국인 관심 증가', '부분적 매수'])
        else:
            indicators.extend(['외국인 흐름 약함', '해외 자금 유출'])
        
        return indicators
    
    async def _analyze_technical_support(self, symbol: str, price_data: List[Dict]) -> Dict[str, Any]:
        """기술적 지지 분석"""
        try:
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            current_price = df['close'].iloc[-1]
            
            # 이동평균선 지지
            ma5 = df['close'].rolling(5).mean().iloc[-1]
            ma10 = df['close'].rolling(10).mean().iloc[-1]
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma60 = df['close'].rolling(60).mean().iloc[-1] if len(df) >= 60 else ma20
            
            # 볼린저밴드
            bb_middle = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            bb_lower = bb_middle - (bb_std * 2)
            
            technical_score = 0
            indicators = []
            
            # 이동평균선 정배열 체크
            if ma5 > ma10 > ma20:
                technical_score += 25
                indicators.append('단기 이평선 정배열')
            elif ma5 > ma10:
                technical_score += 15
                indicators.append('단기 상승 추세')
            
            # 현재가 위치
            if current_price > ma20:
                technical_score += 20
                indicators.append('20일선 상단 유지')
            elif current_price > ma20 * 0.98:  # 2% 내
                technical_score += 15
                indicators.append('20일선 근처 지지')
            
            # 볼린저밴드 하단 근처 매수 기회
            if len(bb_lower) > 0 and current_price <= bb_lower.iloc[-1] * 1.02:
                technical_score += 20
                indicators.append('볼밴 하단 매수 기회')
            
            # 추세선 지지 (간단 버전)
            if len(df) >= 10:
                recent_lows = df['low'].iloc[-10:].min()
                if current_price <= recent_lows * 1.05:  # 최근 저점 근처
                    technical_score += 15
                    indicators.append('추세선 지지 구간')
            
            return {
                'score': min(100, technical_score),
                'ma_support': {
                    'ma5': ma5,
                    'ma10': ma10,
                    'ma20': ma20,
                    'ma60': ma60
                },
                'bb_lower': bb_lower.iloc[-1] if len(bb_lower) > 0 else current_price,
                'current_price': current_price,
                'indicators': indicators
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 기술적 지지 분석 실패: {e}")
            return {'score': 0, 'indicators': ['분석 실패']}
    
    async def _analyze_market_structure(self, symbol: str, price_data: List[Dict]) -> Dict[str, Any]:
        """시장 구조 분석"""
        try:
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            structure_score = 0
            indicators = []
            
            # 고점/저점 패턴 분석
            highs = df['high'].rolling(5, center=True).max()
            lows = df['low'].rolling(5, center=True).min()
            
            higher_lows = 0
            lower_highs = 0
            
            for i in range(5, len(df)-5):
                if lows.iloc[i] == df['low'].iloc[i] and i > 5:
                    # 저점 발견
                    prev_low_idx = None
                    for j in range(i-1, max(0, i-15), -1):
                        if lows.iloc[j] == df['low'].iloc[j]:
                            prev_low_idx = j
                            break
                    
                    if prev_low_idx is not None and df['low'].iloc[i] > df['low'].iloc[prev_low_idx]:
                        higher_lows += 1
                
                if highs.iloc[i] == df['high'].iloc[i] and i > 5:
                    # 고점 발견
                    prev_high_idx = None
                    for j in range(i-1, max(0, i-15), -1):
                        if highs.iloc[j] == df['high'].iloc[j]:
                            prev_high_idx = j
                            break
                    
                    if prev_high_idx is not None and df['high'].iloc[i] < df['high'].iloc[prev_high_idx]:
                        lower_highs += 1
            
            # 상승 구조 (higher lows)
            if higher_lows >= 2:
                structure_score += 40
                indicators.append(f'상승 구조 ({higher_lows}개 고저점)')
            elif higher_lows >= 1:
                structure_score += 25
                indicators.append('부분적 상승 구조')
            
            # 하락 구조 페널티
            if lower_highs >= 2:
                structure_score -= 20
                indicators.append(f'하락 구조 위험 ({lower_highs}개)')
            
            # 거래량과 가격의 건전성
            volume_price_health = df['volume'].corr(df['close'])
            if volume_price_health > 0.2:
                structure_score += 20
                indicators.append('거래량-가격 건전성 양호')
            elif volume_price_health > 0:
                structure_score += 10
                indicators.append('거래량-가격 관계 보통')
            
            # 변동성 안정성
            volatility = df['close'].pct_change().std()
            if volatility < 0.03:  # 3% 미만
                structure_score += 15
                indicators.append('변동성 안정')
            elif volatility < 0.05:  # 5% 미만
                structure_score += 10
                indicators.append('변동성 보통')
            
            return {
                'score': max(0, min(100, structure_score)),
                'higher_lows': higher_lows,
                'lower_highs': lower_highs,
                'volume_price_correlation': volume_price_health,
                'volatility': volatility,
                'indicators': indicators
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 시장 구조 분석 실패: {e}")
            return {'score': 0, 'indicators': ['분석 실패']}
    
    def _calculate_accumulation_score(self, volume_acc: Dict, price_support: Dict,
                                    institutional: Dict, foreign: Dict,
                                    technical: Dict, market_structure: Dict) -> float:
        """종합 매집 점수 계산"""
        try:
            total_score = (
                volume_acc.get('score', 0) * self.pattern_weights['volume_accumulation'] +
                price_support.get('score', 0) * self.pattern_weights['price_support'] +
                institutional.get('score', 0) * self.pattern_weights['institutional_flow'] +
                foreign.get('score', 0) * self.pattern_weights['foreign_flow'] +
                technical.get('score', 0) * self.pattern_weights['technical_support'] +
                market_structure.get('score', 0) * self.pattern_weights['market_structure']
            )
            
            return min(100, max(0, total_score))
            
        except Exception:
            return 0
    
    async def _estimate_institutional_avg_cost(self, symbol: str, price_data: List[Dict],
                                             institutional_data: List[Dict],
                                             foreign_data: List[Dict],
                                             volume_acc: Dict, price_support: Dict) -> float:
        """세력 평균 매수가 추정"""
        try:
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # 방법 1: 거래량 가중 평균가 (VWAP)
            df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
            df['price_volume'] = df['typical_price'] * df['volume']
            
            # 최근 매집 기간의 VWAP
            accumulation_period = self.analysis_params['accumulation_period']
            recent_data = df.iloc[-accumulation_period:]
            
            total_pv = recent_data['price_volume'].sum()
            total_volume = recent_data['volume'].sum()
            
            vwap_avg_cost = total_pv / total_volume if total_volume > 0 else df['close'].iloc[-1]
            
            # 방법 2: 지지선 기반 추정
            support_levels = price_support.get('support_levels', [])
            if support_levels:
                support_avg_cost = np.mean(support_levels)
            else:
                support_avg_cost = vwap_avg_cost
            
            # 방법 3: 대량 거래일 가중 평균
            avg_volume = df['volume'].mean()
            high_volume_days = df[df['volume'] > avg_volume * 1.5]
            
            if len(high_volume_days) > 0:
                high_volume_avg_cost = (
                    (high_volume_days['typical_price'] * high_volume_days['volume']).sum() / 
                    high_volume_days['volume'].sum()
                )
            else:
                high_volume_avg_cost = vwap_avg_cost
            
            # 방법들의 가중 평균
            estimated_avg_cost = (
                vwap_avg_cost * 0.5 +
                support_avg_cost * 0.3 +
                high_volume_avg_cost * 0.2
            )
            
            # 현재가와의 비교를 통한 합리성 체크
            current_price = df['close'].iloc[-1]
            
            # 추정가가 현재가보다 과도하게 높거나 낮으면 조정
            if estimated_avg_cost > current_price * 1.2:  # 20% 이상 높음
                estimated_avg_cost = current_price * 1.1
            elif estimated_avg_cost < current_price * 0.7:  # 30% 이상 낮음
                estimated_avg_cost = current_price * 0.9
            
            return round(estimated_avg_cost, 0)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 평균 매수가 추정 실패: {e}")
            # 폴백: 현재가의 95%
            try:
                return round(float(price_data[-1].get('close', 0)) * 0.95, 0)
            except:
                return 0
    
    async def _get_ai_accumulation_analysis(self, symbol: str, accumulation_score: float,
                                          estimated_avg_cost: float, volume_acc: Dict,
                                          institutional: Dict, foreign: Dict) -> Dict:
        """AI 기반 매집 분석"""
        try:
            analysis_prompt = f"""
다음 주식의 세력 매집 상황을 분석해주세요:

종목: {symbol}
종합 매집 점수: {accumulation_score:.1f}/100
추정 평균 매수가: {estimated_avg_cost:,.0f}원

세부 분석:
- 거래량 매집: {volume_acc.get('score', 0):.1f}점
- 기관 흐름: {institutional.get('score', 0):.1f}점  
- 외국인 흐름: {foreign.get('score', 0):.1f}점
- 거래량 급증일: {volume_acc.get('volume_surge_days', 0)}일
- 기관 연속 매수일: {institutional.get('consecutive_buy_days', 0)}일

다음 JSON 형식으로 답변해주세요:
{{
    "accumulation_probability": 0.0~1.0,
    "accumulation_phase": "early/middle/late/complete",
    "institutional_confidence": 0.0~1.0,
    "price_target_vs_avg_cost": 1.1~2.0,
    "key_strengths": ["강점1", "강점2", "강점3"],
    "risk_factors": ["리스크1", "리스크2"],
    "recommendation": "strong_buy/buy/hold/avoid",
    "ai_confidence": 0.0~1.0
}}
"""
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(analysis_prompt)
            
            if ai_result and isinstance(ai_result, dict):
                return ai_result
            else:
                return self._get_default_ai_analysis()
                
        except Exception as e:
            self.logger.warning(f"⚠️ AI 매집 분석 실패: {e}")
            return self._get_default_ai_analysis()
    
    def _get_default_ai_analysis(self) -> Dict:
        """기본 AI 분석 결과"""
        return {
            'accumulation_probability': 0.5,
            'accumulation_phase': 'unknown',
            'institutional_confidence': 0.5,
            'price_target_vs_avg_cost': 1.2,
            'key_strengths': ['분석 데이터 부족'],
            'risk_factors': ['AI 분석 실패'],
            'recommendation': 'hold',
            'ai_confidence': 0.3
        }
    
    def _generate_accumulation_signal(self, symbol: str, accumulation_score: float,
                                    estimated_avg_cost: float, volume_acc: Dict,
                                    price_support: Dict, institutional: Dict,
                                    foreign: Dict, ai_analysis: Dict) -> AccumulationSignal:
        """최종 매집 신호 생성"""
        try:
            # 매집 여부 판단
            is_accumulating = accumulation_score >= 60 and ai_analysis.get('accumulation_probability', 0) >= 0.6
            
            # 매집 기간 추정
            accumulation_days = 0
            if volume_acc.get('volume_surge_days', 0) > 0 or institutional.get('consecutive_buy_days', 0) > 0:
                accumulation_days = max(
                    volume_acc.get('volume_surge_days', 0) * 2,  # 거래량 급증일의 2배
                    institutional.get('consecutive_buy_days', 0),
                    foreign.get('consecutive_buy_days', 0)
                )
            
            # 신뢰도 점수
            confidence_factors = [
                accumulation_score / 100,
                ai_analysis.get('ai_confidence', 0.5),
                min(1.0, (institutional.get('score', 0) + foreign.get('score', 0)) / 100)
            ]
            confidence_score = np.mean(confidence_factors)
            
            # 핵심 지표
            key_indicators = []
            key_indicators.extend(volume_acc.get('indicators', [])[:2])
            key_indicators.extend(institutional.get('indicators', [])[:2])
            key_indicators.extend(ai_analysis.get('key_strengths', [])[:2])
            
            # 리스크 요인
            risk_factors = []
            if accumulation_score < 70:
                risk_factors.append('매집 신호 약함')
            if confidence_score < 0.7:
                risk_factors.append('신뢰도 부족')
            risk_factors.extend(ai_analysis.get('risk_factors', [])[:2])
            
            return AccumulationSignal(
                symbol=symbol,
                is_accumulating=is_accumulating,
                accumulation_strength=accumulation_score,
                accumulation_period_days=accumulation_days,
                estimated_avg_cost=estimated_avg_cost,
                institutional_ownership_change=institutional.get('buy_consistency', 0),
                foreign_ownership_change=foreign.get('buy_consistency', 0),
                volume_profile_support=volume_acc.get('score', 0),
                price_support_level=price_support.get('strongest_support', estimated_avg_cost),
                confidence_score=confidence_score,
                key_indicators=key_indicators,
                risk_factors=risk_factors,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 매집 신호 생성 실패: {e}")
            return self._create_empty_accumulation_signal(symbol)
    
    def _create_empty_accumulation_signal(self, symbol: str) -> AccumulationSignal:
        """빈 매집 신호 생성"""
        return AccumulationSignal(
            symbol=symbol,
            is_accumulating=False,
            accumulation_strength=0,
            accumulation_period_days=0,
            estimated_avg_cost=0,
            institutional_ownership_change=0,
            foreign_ownership_change=0,
            volume_profile_support=0,
            price_support_level=0,
            confidence_score=0.3,
            key_indicators=['분석 실패'],
            risk_factors=['데이터 부족'],
            timestamp=datetime.now()
        )
    
    async def calculate_smart_money_flow(self, symbol: str, 
                                       price_data: List[Dict],
                                       institutional_data: List[Dict] = None,
                                       foreign_data: List[Dict] = None) -> SmartMoneyFlow:
        """스마트머니 흐름 종합 계산"""
        try:
            self.logger.info(f"💰 {symbol} 스마트머니 흐름 계산 시작")
            
            # 기관/외국인 흐름 분석
            institutional_flow = await self._analyze_institutional_flow(symbol, institutional_data or [], price_data)
            foreign_flow = await self._analyze_foreign_flow(symbol, foreign_data or [], price_data)
            
            # 거래량 가중 평균가 계산
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            df['typical_price'] = (df['high'].astype(float) + df['low'].astype(float) + df['close']) / 3
            
            total_pv = (df['typical_price'] * df['volume']).sum()
            total_volume = df['volume'].sum()
            vwap = total_pv / total_volume if total_volume > 0 else df['close'].iloc[-1]
            
            # 매집 구간 계산
            accumulation_zone_low = df['low'].quantile(0.2)  # 하위 20%
            accumulation_zone_high = df['high'].quantile(0.8)  # 상위 80%
            
            # 자금 흐름 일관성
            institutional_consistency = institutional_flow.get('buy_consistency', 0)
            foreign_consistency = foreign_flow.get('buy_consistency', 0)
            flow_consistency = (institutional_consistency + foreign_consistency) / 2
            
            # 스마트머니 신뢰도
            confidence_factors = [
                institutional_flow.get('score', 0) / 100,
                foreign_flow.get('score', 0) / 100,
                flow_consistency,
                min(1.0, len(price_data) / 30)  # 데이터 충분성
            ]
            smart_money_confidence = np.mean(confidence_factors)
            
            return SmartMoneyFlow(
                net_institutional_flow=institutional_flow.get('net_buy_amount', 0),
                net_foreign_flow=foreign_flow.get('net_buy_amount', 0),
                institutional_avg_price=vwap * 0.98,  # 약간 낮게 추정
                foreign_avg_price=vwap * 1.02,       # 약간 높게 추정
                accumulation_zone_low=accumulation_zone_low,
                accumulation_zone_high=accumulation_zone_high,
                volume_weighted_avg_price=vwap,
                flow_consistency=flow_consistency,
                smart_money_confidence=smart_money_confidence
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 스마트머니 흐름 계산 실패: {e}")
            return SmartMoneyFlow(
                net_institutional_flow=0,
                net_foreign_flow=0,
                institutional_avg_price=0,
                foreign_avg_price=0,
                accumulation_zone_low=0,
                accumulation_zone_high=0,
                volume_weighted_avg_price=0,
                flow_consistency=0,
                smart_money_confidence=0.3
            )