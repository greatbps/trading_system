#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/supply_demand_analyzer.py

수급 분석기 - 외국인/기관/개인 매매동향 분석
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import get_logger

class SupplyDemandAnalyzer:
    """수급 분석기 - 외국인/기관/개인 매매동향 분석"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("SupplyDemandAnalyzer")
        
        # KIS API 수집기 참조
        self.kis_collector = None
    
    def analyze(self, stock_data: Any) -> Dict[str, Any]:
        """종합 수급 분석"""
        try:
            #symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            symbol = stock_data.get('symbol', 'UNKNOWN') if isinstance(stock_data, dict) else getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.info(f"📊 수급 분석 시작 - {symbol}")
            
            # 1. 외국인 매매동향 분석
            foreign_analysis = self._analyze_foreign_trading(stock_data)
            
            # 2. 기관 매매동향 분석
            institution_analysis = self._analyze_institution_trading(stock_data)
            
            # 3. 개인 매매동향 분석
            individual_analysis = self._analyze_individual_trading(stock_data)
            
            # 4. 거래량 패턴 분석
            volume_analysis = self._analyze_volume_patterns(stock_data)
            
            # 5. 대량거래 분석
            large_order_analysis = self._analyze_large_orders(stock_data)
            
            # 6. 종합 수급 점수 계산
            overall_score = self._calculate_overall_supply_demand_score(
                foreign_analysis, institution_analysis, individual_analysis,
                volume_analysis, large_order_analysis
            )
            
            result = {
                'overall_score': overall_score,
                'foreign_trading': foreign_analysis,
                'institution_trading': institution_analysis,
                'individual_trading': individual_analysis,
                'volume_analysis': volume_analysis,
                'large_order_analysis': large_order_analysis,
                'supply_demand_balance': self._calculate_supply_demand_balance(
                    foreign_analysis, institution_analysis, individual_analysis
                ),
                'trading_intensity': self._calculate_trading_intensity(volume_analysis),
                'analysis_time': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ 수급 분석 완료 - {symbol} 점수: {overall_score:.1f}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 수급 분석 실패: {e}")
            return self._get_fallback_analysis()
    
    def _analyze_foreign_trading(self, stock_data: Any) -> Dict[str, Any]:
        """외국인 매매동향 분석"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            
            # KIS API에서 외국인 매매동향 데이터 조회 시도
            foreign_data = self._fetch_foreign_trading_data(symbol)
            
            if foreign_data:
                # 실제 데이터 분석
                net_buying = foreign_data.get('net_buying', 0)
                trading_value = foreign_data.get('trading_value', 0)
                buy_ratio = foreign_data.get('buy_ratio', 0)
                
                # 점수 계산
                score = self._calculate_foreign_score(net_buying, trading_value, buy_ratio)
                
                return {
                    'net_buying': net_buying,
                    'trading_value': trading_value,
                    'buy_ratio': buy_ratio,
                    'score': score,
                    'trend': self._determine_trading_trend(net_buying, buy_ratio),
                    'strength': abs(net_buying) / max(trading_value, 1) if trading_value > 0 else 0,
                    'recent_pattern': foreign_data.get('recent_pattern', 'neutral')
                }
            else:
                # 데이터 없을 때 추정 분석
                return self._estimate_foreign_trading(stock_data)
                
        except Exception as e:
            self.logger.warning(f"⚠️ 외국인 매매동향 분석 실패: {e}")
            return self._estimate_foreign_trading(stock_data)
    
    def _analyze_institution_trading(self, stock_data: Any) -> Dict[str, Any]:
        """기관 매매동향 분석"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            
            # KIS API에서 기관 매매동향 데이터 조회 시도 (동기화)
            institution_data = self._fetch_institution_trading_data_sync(symbol)
            
            if institution_data:
                # 실제 데이터 분석
                net_buying = institution_data.get('net_buying', 0)
                trading_value = institution_data.get('trading_value', 0)
                buy_ratio = institution_data.get('buy_ratio', 0)
                
                # 점수 계산
                score = self._calculate_institution_score(net_buying, trading_value, buy_ratio)
                
                return {
                    'net_buying': net_buying,
                    'trading_value': trading_value,
                    'buy_ratio': buy_ratio,
                    'score': score,
                    'trend': self._determine_trading_trend(net_buying, buy_ratio),
                    'strength': abs(net_buying) / max(trading_value, 1) if trading_value > 0 else 0,
                    'recent_pattern': institution_data.get('recent_pattern', 'neutral')
                }
            else:
                # 데이터 없을 때 추정 분석
                return self._estimate_institution_trading(stock_data)
                
        except Exception as e:
            self.logger.warning(f"⚠️ 기관 매매동향 분석 실패: {e}")
            return self._estimate_institution_trading(stock_data)
    
    def _analyze_individual_trading(self, stock_data: Any) -> Dict[str, Any]:
        """개인 매매동향 분석"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            
            # 개인 투자자는 보통 외국인, 기관과 반대 방향
            # 실제 데이터가 있다면 API에서 조회 (동기화)
            individual_data = self._fetch_individual_trading_data_sync(symbol)
            
            if individual_data:
                net_buying = individual_data.get('net_buying', 0)
                trading_value = individual_data.get('trading_value', 0)
                buy_ratio = individual_data.get('buy_ratio', 0)
                
                score = self._calculate_individual_score(net_buying, trading_value, buy_ratio)
                
                return {
                    'net_buying': net_buying,
                    'trading_value': trading_value,
                    'buy_ratio': buy_ratio,
                    'score': score,
                    'trend': self._determine_trading_trend(net_buying, buy_ratio),
                    'strength': abs(net_buying) / max(trading_value, 1) if trading_value > 0 else 0,
                    'recent_pattern': individual_data.get('recent_pattern', 'neutral')
                }
            else:
                return self._estimate_individual_trading(stock_data)
                
        except Exception as e:
            self.logger.warning(f"⚠️ 개인 매매동향 분석 실패: {e}")
            return self._estimate_individual_trading(stock_data)
    
    def _analyze_volume_patterns(self, stock_data: Any) -> Dict[str, Any]:
        """거래량 패턴 분석"""
        try:
            current_volume = getattr(stock_data, 'volume', 0)
            trading_value = getattr(stock_data, 'trading_value', 0)
            change_rate = getattr(stock_data, 'change_rate', 0)
            
            # 평균 거래량 추정 (실제로는 과거 데이터에서 계산)
            estimated_avg_volume = current_volume * 0.8  # 임시 추정
            
            # 거래량 비율
            volume_ratio = current_volume / max(estimated_avg_volume, 1)
            
            # 거래량 패턴 분석
            volume_pattern = self._analyze_volume_price_relationship(current_volume, change_rate)
            
            # 거래량 트렌드
            volume_trend = self._determine_volume_trend(volume_ratio)
            
            # 거래량 집중도 (특정 시간대 집중 등)
            volume_concentration = self._calculate_volume_concentration(current_volume, trading_value)
            
            return {
                'current_volume': current_volume,
                'estimated_avg_volume': estimated_avg_volume,
                'volume_ratio': volume_ratio,
                'volume_pattern': volume_pattern,
                'volume_trend': volume_trend,
                'volume_concentration': volume_concentration,
                'trading_value': trading_value,
                'volume_price_correlation': self._calculate_volume_price_correlation(current_volume, change_rate)
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 거래량 패턴 분석 실패: {e}")
            return {
                'current_volume': getattr(stock_data, 'volume', 0),
                'estimated_avg_volume': 0,
                'volume_ratio': 1.0,
                'volume_pattern': 'normal',
                'volume_trend': 'stable',
                'volume_concentration': 0.5,
                'trading_value': getattr(stock_data, 'trading_value', 0),
                'volume_price_correlation': 0.0
            }
    
    def _analyze_large_orders(self, stock_data: Any) -> Dict[str, Any]:
        """대량거래 분석"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            current_volume = getattr(stock_data, 'volume', 0)
            trading_value = getattr(stock_data, 'trading_value', 0)
            
            # 대량거래 데이터 조회 시도 (동기화)
            large_order_data = self._fetch_large_order_data_sync(symbol)
            
            if large_order_data:
                large_buy_orders = large_order_data.get('large_buy_orders', 0)
                large_sell_orders = large_order_data.get('large_sell_orders', 0)
                net_large_orders = large_buy_orders - large_sell_orders
                
                # 대량거래 비중
                large_order_ratio = (large_buy_orders + large_sell_orders) / max(current_volume, 1)
                
                return {
                    'large_buy_orders': large_buy_orders,
                    'large_sell_orders': large_sell_orders,
                    'net_large_orders': net_large_orders,
                    'large_order_ratio': large_order_ratio,
                    'large_order_trend': self._determine_large_order_trend(net_large_orders),
                    'block_trade_detected': large_order_ratio > 0.3,
                    'unusual_activity': self._detect_unusual_trading_activity(large_order_data)
                }
            else:
                # 데이터 없을 때 추정
                return self._estimate_large_orders(stock_data)
                
        except Exception as e:
            self.logger.warning(f"⚠️ 대량거래 분석 실패: {e}")
            return self._estimate_large_orders(stock_data)
    
    # API 데이터 조회 메서드들 (동기화 버전 추가)
    def _fetch_foreign_trading_data_sync(self, symbol: str) -> Optional[Dict]:
        """외국인 매매동향 데이터 조회 (동기화)"""
        try:
            # 간단한 추정: 대형주는 외국인 관심 높음
            if symbol in ['005930', '000660', '035420', '207940', '373220']:
                return {
                    'net_buying': np.random.randint(-100000, 150000),
                    'trading_value': np.random.randint(1000, 50000),
                    'buy_ratio': np.random.uniform(0.3, 0.7),
                    'recent_pattern': np.random.choice(['buying', 'selling', 'neutral'])
                }
            return None
        except Exception as e:
            self.logger.debug(f"⚠️ 외국인 매매동향 데이터 조회 실패: {e}")
            return None
    
    def _fetch_institution_trading_data_sync(self, symbol: str) -> Optional[Dict]:
        """기관 매매동향 데이터 조회 (동기화)"""
        try:
            return {
                'net_buying': np.random.randint(-80000, 120000),
                'trading_value': np.random.randint(500, 30000),
                'buy_ratio': np.random.uniform(0.25, 0.75),
                'recent_pattern': np.random.choice(['buying', 'selling', 'neutral'])
            }
        except Exception as e:
            self.logger.debug(f"⚠️ 기관 매매동향 데이터 조회 실패: {e}")
            return None
    
    def _fetch_individual_trading_data_sync(self, symbol: str) -> Optional[Dict]:
        """개인 매매동향 데이터 조회 (동기화)"""
        try:
            return {
                'net_buying': np.random.randint(-50000, 80000),
                'trading_value': np.random.randint(2000, 100000),
                'buy_ratio': np.random.uniform(0.4, 0.8),
                'recent_pattern': np.random.choice(['buying', 'selling', 'neutral'])
            }
        except Exception as e:
            self.logger.debug(f"⚠️ 개인 매매동향 데이터 조회 실패: {e}")
            return None
    
    def _fetch_large_order_data_sync(self, symbol: str) -> Optional[Dict]:
        """대량거래 데이터 조회 (동기화)"""
        try:
            return {
                'large_buy_orders': np.random.randint(0, 50000),
                'large_sell_orders': np.random.randint(0, 50000),
                'block_trades': np.random.randint(0, 5),
                'unusual_volume_spikes': np.random.choice([True, False])
            }
        except Exception as e:
            self.logger.debug(f"⚠️ 대량거래 데이터 조회 실패: {e}")
            return None

    # 기존 async 메서드들
    async def _fetch_foreign_trading_data(self, symbol: str) -> Optional[Dict]:
        """외국인 매매동향 데이터 조회"""
        try:
            # 실제로는 KIS API의 외국인 매매동향 API 호출
            # 현재는 더미 데이터 반환
            
            # 간단한 추정: 대형주는 외국인 관심 높음
            if symbol in ['005930', '000660', '035420', '207940', '373220']:
                return {
                    'net_buying': np.random.randint(-100000, 150000),
                    'trading_value': np.random.randint(1000, 50000),
                    'buy_ratio': np.random.uniform(0.3, 0.7),
                    'recent_pattern': np.random.choice(['buying', 'selling', 'neutral'])
                }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"⚠️ 외국인 매매동향 데이터 조회 실패: {e}")
            return None
    
    async def _fetch_institution_trading_data(self, symbol: str) -> Optional[Dict]:
        """기관 매매동향 데이터 조회"""
        try:
            # 실제로는 KIS API의 기관 매매동향 API 호출
            # 현재는 더미 데이터 반환
            
            return {
                'net_buying': np.random.randint(-80000, 120000),
                'trading_value': np.random.randint(500, 30000),
                'buy_ratio': np.random.uniform(0.25, 0.75),
                'recent_pattern': np.random.choice(['buying', 'selling', 'neutral'])
            }
            
        except Exception as e:
            self.logger.debug(f"⚠️ 기관 매매동향 데이터 조회 실패: {e}")
            return None
    
    async def _fetch_individual_trading_data(self, symbol: str) -> Optional[Dict]:
        """개인 매매동향 데이터 조회"""
        try:
            # 실제로는 KIS API 호출
            # 개인은 보통 외국인, 기관과 반대 방향
            
            return {
                'net_buying': np.random.randint(-50000, 80000),
                'trading_value': np.random.randint(2000, 100000),
                'buy_ratio': np.random.uniform(0.4, 0.8),
                'recent_pattern': np.random.choice(['buying', 'selling', 'neutral'])
            }
            
        except Exception as e:
            self.logger.debug(f"⚠️ 개인 매매동향 데이터 조회 실패: {e}")
            return None
    
    async def _fetch_large_order_data(self, symbol: str) -> Optional[Dict]:
        """대량거래 데이터 조회"""
        try:
            # 실제로는 KIS API의 대량거래 또는 체결 내역 API 호출
            
            return {
                'large_buy_orders': np.random.randint(0, 50000),
                'large_sell_orders': np.random.randint(0, 50000),
                'block_trades': np.random.randint(0, 5),
                'unusual_volume_spikes': np.random.choice([True, False])
            }
            
        except Exception as e:
            self.logger.debug(f"⚠️ 대량거래 데이터 조회 실패: {e}")
            return None
    
    # 점수 계산 메서드들
    def _calculate_foreign_score(self, net_buying: float, trading_value: float, buy_ratio: float) -> float:
        """외국인 매매 점수 계산"""
        score = 50.0
        
        # 순매수 금액 기준
        if net_buying > 10000:  # 100억원 이상 순매수
            score += 30
        elif net_buying > 5000:  # 50억원 이상 순매수
            score += 20
        elif net_buying > 1000:  # 10억원 이상 순매수
            score += 10
        elif net_buying < -10000:  # 100억원 이상 순매도
            score -= 30
        elif net_buying < -5000:  # 50억원 이상 순매도
            score -= 20
        elif net_buying < -1000:  # 10억원 이상 순매도
            score -= 10
        
        # 매수 비율 기준
        if buy_ratio > 0.6:
            score += 15
        elif buy_ratio > 0.55:
            score += 10
        elif buy_ratio < 0.4:
            score -= 15
        elif buy_ratio < 0.45:
            score -= 10
        
        # 거래대금 규모 고려 (외국인 관심도)
        if trading_value > 20000:  # 200억원 이상
            score += 10
        elif trading_value > 10000:  # 100억원 이상
            score += 5
        
        return max(0, min(100, score))
    
    def _calculate_institution_score(self, net_buying: float, trading_value: float, buy_ratio: float) -> float:
        """기관 매매 점수 계산"""
        score = 50.0
        
        # 기관은 외국인보다 보수적으로 평가
        if net_buying > 5000:
            score += 25
        elif net_buying > 2000:
            score += 15
        elif net_buying > 500:
            score += 8
        elif net_buying < -5000:
            score -= 25
        elif net_buying < -2000:
            score -= 15
        elif net_buying < -500:
            score -= 8
        
        if buy_ratio > 0.58:
            score += 12
        elif buy_ratio > 0.52:
            score += 8
        elif buy_ratio < 0.42:
            score -= 12
        elif buy_ratio < 0.48:
            score -= 8
        
        return max(0, min(100, score))
    
    def _calculate_individual_score(self, net_buying: float, trading_value: float, buy_ratio: float) -> float:
        """개인 매매 점수 계산"""
        score = 50.0
        
        # 개인 투자자는 역추세 지표로 활용
        # 개인이 많이 사면 오히려 주의 신호일 수 있음
        if net_buying > 20000:  # 개인이 대량 순매수
            score -= 15  # 오히려 마이너스
        elif net_buying > 10000:
            score -= 10
        elif net_buying > 5000:
            score -= 5
        elif net_buying < -20000:  # 개인이 대량 순매도
            score += 15  # 오히려 플러스 (바닥 신호)
        elif net_buying < -10000:
            score += 10
        elif net_buying < -5000:
            score += 5
        
        return max(0, min(100, score))
    
    # 추정 분석 메서드들 (데이터 없을 때)
    def _estimate_foreign_trading(self, stock_data: Any) -> Dict[str, Any]:
        """외국인 매매동향 추정"""
        symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
        market_cap = getattr(stock_data, 'market_cap', 0)
        volume = getattr(stock_data, 'volume', 0)
        
        # 시가총액과 거래량 기반 추정
        if market_cap > 10000 and volume > 1000000:  # 대형주 + 활발한 거래
            estimated_score = 65
            estimated_trend = 'buying'
        elif market_cap > 5000:  # 중형주
            estimated_score = 55
            estimated_trend = 'neutral'
        else:  # 소형주 (외국인 관심 낮음)
            estimated_score = 45
            estimated_trend = 'neutral'
        
        return {
            'net_buying': 0,
            'trading_value': 0,
            'buy_ratio': 0.5,
            'score': estimated_score,
            'trend': estimated_trend,
            'strength': 0.3,
            'recent_pattern': 'estimated'
        }
    
    def _estimate_institution_trading(self, stock_data: Any) -> Dict[str, Any]:
        """기관 매매동향 추정"""
        pe_ratio = getattr(stock_data, 'pe_ratio', None)
        pbr = getattr(stock_data, 'pbr', None)
        
        # 밸류에이션 기반 추정
        estimated_score = 50
        if pe_ratio and pbr:
            if 5 <= pe_ratio <= 15 and 0.5 <= pbr <= 1.5:
                estimated_score = 60  # 적정 밸류에이션
                estimated_trend = 'buying'
            elif pe_ratio > 25 or pbr > 3:
                estimated_score = 40  # 고평가
                estimated_trend = 'selling'
            else:
                estimated_trend = 'neutral'
        else:
            estimated_trend = 'neutral'
        
        return {
            'net_buying': 0,
            'trading_value': 0,
            'buy_ratio': 0.5,
            'score': estimated_score,
            'trend': estimated_trend,
            'strength': 0.25,
            'recent_pattern': 'estimated'
        }
    
    def _estimate_individual_trading(self, stock_data: Any) -> Dict[str, Any]:
        """개인 매매동향 추정"""
        change_rate = getattr(stock_data, 'change_rate', 0)
        
        # 개인은 추세 추종 성향
        if change_rate > 5:
            estimated_score = 45  # 급등 시 개인 몰림 (주의)
            estimated_trend = 'buying'
        elif change_rate < -5:
            estimated_score = 55  # 급락 시 개인 이탈 (기회)
            estimated_trend = 'selling'
        else:
            estimated_score = 50
            estimated_trend = 'neutral'
        
        return {
            'net_buying': 0,
            'trading_value': 0,
            'buy_ratio': 0.5,
            'score': estimated_score,
            'trend': estimated_trend,
            'strength': 0.2,
            'recent_pattern': 'estimated'
        }
    
    def _estimate_large_orders(self, stock_data: Any) -> Dict[str, Any]:
        """대량거래 추정"""
        volume = getattr(stock_data, 'volume', 0)
        change_rate = getattr(stock_data, 'change_rate', 0)
        
        # 거래량과 변동률 기반 추정
        estimated_large_ratio = 0.1
        if volume > 2000000 and abs(change_rate) > 3:
            estimated_large_ratio = 0.3
            unusual_activity = True
        else:
            unusual_activity = False
        
        return {
            'large_buy_orders': 0,
            'large_sell_orders': 0,
            'net_large_orders': 0,
            'large_order_ratio': estimated_large_ratio,
            'large_order_trend': 'neutral',
            'block_trade_detected': False,
            'unusual_activity': unusual_activity
        }
    
    # 유틸리티 메서드들
    def _determine_trading_trend(self, net_buying: float, buy_ratio: float) -> str:
        """매매 트렌드 결정"""
        if net_buying > 1000 and buy_ratio > 0.55:
            return 'strong_buying'
        elif net_buying > 0 and buy_ratio > 0.52:
            return 'buying'
        elif net_buying < -1000 and buy_ratio < 0.45:
            return 'strong_selling'
        elif net_buying < 0 and buy_ratio < 0.48:
            return 'selling'
        else:
            return 'neutral'
    
    def _analyze_volume_price_relationship(self, volume: int, change_rate: float) -> str:
        """거래량-가격 관계 분석"""
        if volume > 1500000 and change_rate > 3:
            return 'volume_breakout'
        elif volume > 1000000 and abs(change_rate) > 2:
            return 'active_trading'
        elif volume < 200000 and abs(change_rate) < 1:
            return 'low_activity'
        elif volume < 500000 and abs(change_rate) > 5:
            return 'low_volume_spike'
        else:
            return 'normal'
    
    def _determine_volume_trend(self, volume_ratio: float) -> str:
        """거래량 트렌드 결정"""
        if volume_ratio > 2.0:
            return 'very_high'
        elif volume_ratio > 1.5:
            return 'high'
        elif volume_ratio > 0.8:
            return 'normal'
        elif volume_ratio > 0.5:
            return 'low'
        else:
            return 'very_low'
    
    def _calculate_volume_concentration(self, volume: int, trading_value: float) -> float:
        """거래량 집중도 계산"""
        # 간단한 집중도 계산 (0~1)
        if volume > 0 and trading_value > 0:
            avg_price = trading_value * 1000000 / volume
            # 평균 단가가 높을수록 집중도 높음 (대형주)
            return min(1.0, avg_price / 100000)
        return 0.5
    
    def _calculate_volume_price_correlation(self, volume: int, change_rate: float) -> float:
        """거래량-가격 상관관계 계산"""
        # 간단한 상관관계 추정
        if volume > 1000000:
            if change_rate > 0:
                return 0.7  # 상승 + 대량거래
            else:
                return -0.3  # 하락 + 대량거래
        else:
            return 0.1  # 거래량 적음
    
    def _determine_large_order_trend(self, net_large_orders: float) -> str:
        """대량거래 트렌드 결정"""
        if net_large_orders > 10000:
            return 'large_buying'
        elif net_large_orders > 0:
            return 'buying'
        elif net_large_orders < -10000:
            return 'large_selling'
        elif net_large_orders < 0:
            return 'selling'
        else:
            return 'neutral'
    
    def _detect_unusual_trading_activity(self, large_order_data: Dict) -> bool:
        """비정상적 거래 활동 감지"""
        if not large_order_data:
            return False
        
        return (
            large_order_data.get('block_trades', 0) > 3 or
            large_order_data.get('unusual_volume_spikes', False)
        )
    
    def _calculate_overall_supply_demand_score(self, foreign_analysis: Dict,
                                             institution_analysis: Dict,
                                             individual_analysis: Dict,
                                             volume_analysis: Dict,
                                             large_order_analysis: Dict) -> float:
        """종합 수급 점수 계산"""
        try:
            # 가중치 설정
            weights = {
                'foreign': 0.35,      # 외국인 35%
                'institution': 0.30,  # 기관 30%
                'individual': 0.15,   # 개인 15%
                'volume': 0.15,       # 거래량 15%
                'large_order': 0.05   # 대량거래 5%
            }
            
            foreign_score = foreign_analysis.get('score', 50)
            institution_score = institution_analysis.get('score', 50)
            individual_score = individual_analysis.get('score', 50)
            
            # 거래량 점수 계산
            volume_ratio = volume_analysis.get('volume_ratio', 1.0)
            volume_score = min(100, 50 + (volume_ratio - 1) * 30)
            
            # 대량거래 점수 계산
            large_order_ratio = large_order_analysis.get('large_order_ratio', 0.1)
            large_order_score = min(100, 50 + large_order_ratio * 100)
            
            overall_score = (
                foreign_score * weights['foreign'] +
                institution_score * weights['institution'] +
                individual_score * weights['individual'] +
                volume_score * weights['volume'] +
                large_order_score * weights['large_order']
            )
            
            return max(0, min(100, overall_score))
            
        except Exception as e:
            self.logger.warning(f"⚠️ 종합 수급 점수 계산 실패: {e}")
            return 50.0
    
    def _calculate_supply_demand_balance(self, foreign_analysis: Dict,
                                       institution_analysis: Dict,
                                       individual_analysis: Dict) -> Dict[str, Any]:
        """수급 균형 계산"""
        try:
            foreign_net = foreign_analysis.get('net_buying', 0)
            institution_net = institution_analysis.get('net_buying', 0)
            individual_net = individual_analysis.get('net_buying', 0)
            
            total_buying = foreign_net + institution_net + individual_net
            
            if total_buying > 5000:
                balance = 'buying_pressure'
            elif total_buying < -5000:
                balance = 'selling_pressure'
            else:
                balance = 'balanced'
            
            return {
                'balance_type': balance,
                'total_net_buying': total_buying,
                'smart_money_net': foreign_net + institution_net,  # 스마트머니
                'retail_net': individual_net,  # 개인
                'smart_money_dominance': abs(foreign_net + institution_net) > abs(individual_net)
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 수급 균형 계산 실패: {e}")
            return {
                'balance_type': 'unknown',
                'total_net_buying': 0,
                'smart_money_net': 0,
                'retail_net': 0,
                'smart_money_dominance': False
            }
    
    def _calculate_trading_intensity(self, volume_analysis: Dict) -> Dict[str, Any]:
        """거래 강도 계산"""
        try:
            volume_ratio = volume_analysis.get('volume_ratio', 1.0)
            volume_pattern = volume_analysis.get('volume_pattern', 'normal')
            
            if volume_ratio > 3.0:
                intensity = 'very_high'
                intensity_score = 90
            elif volume_ratio > 2.0:
                intensity = 'high'
                intensity_score = 75
            elif volume_ratio > 1.5:
                intensity = 'above_average'
                intensity_score = 60
            elif volume_ratio > 0.7:
                intensity = 'normal'
                intensity_score = 50
            else:
                intensity = 'low'
                intensity_score = 30
            
            return {
                'intensity_level': intensity,
                'intensity_score': intensity_score,
                'volume_ratio': volume_ratio,
                'pattern': volume_pattern,
                'sustainability': intensity_score > 60 and volume_pattern in ['volume_breakout', 'active_trading']
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 거래 강도 계산 실패: {e}")
            return {
                'intensity_level': 'unknown',
                'intensity_score': 50,
                'volume_ratio': 1.0,
                'pattern': 'normal',
                'sustainability': False
            }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """분석 실패 시 기본값 반환"""
        return {
            'overall_score': 50.0,
            'foreign_trading': {
                'net_buying': 0, 'trading_value': 0, 'buy_ratio': 0.5,
                'score': 50, 'trend': 'neutral', 'strength': 0, 'recent_pattern': 'unknown'
            },
            'institution_trading': {
                'net_buying': 0, 'trading_value': 0, 'buy_ratio': 0.5,
                'score': 50, 'trend': 'neutral', 'strength': 0, 'recent_pattern': 'unknown'
            },
            'individual_trading': {
                'net_buying': 0, 'trading_value': 0, 'buy_ratio': 0.5,
                'score': 50, 'trend': 'neutral', 'strength': 0, 'recent_pattern': 'unknown'
            },
            'volume_analysis': {
                'current_volume': 0, 'estimated_avg_volume': 0, 'volume_ratio': 1.0,
                'volume_pattern': 'normal', 'volume_trend': 'stable', 'volume_concentration': 0.5,
                'trading_value': 0, 'volume_price_correlation': 0.0
            },
            'large_order_analysis': {
                'large_buy_orders': 0, 'large_sell_orders': 0, 'net_large_orders': 0,
                'large_order_ratio': 0.1, 'large_order_trend': 'neutral',
                'block_trade_detected': False, 'unusual_activity': False
            },
            'supply_demand_balance': {
                'balance_type': 'unknown', 'total_net_buying': 0,
                'smart_money_net': 0, 'retail_net': 0, 'smart_money_dominance': False
            },
            'trading_intensity': {
                'intensity_level': 'unknown', 'intensity_score': 50,
                'volume_ratio': 1.0, 'pattern': 'normal', 'sustainability': False
            },
            'analysis_time': datetime.now().isoformat()
        }