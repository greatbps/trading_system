#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/fundamental_analyzer.py

펀더멘털 분석기
"""

import numpy as np
from typing import Dict, Any
from utils.logger import get_logger

class FundamentalAnalyzer:
    """펀더멘털 분석기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("FundamentalAnalyzer")
    
    async def analyze(self, stock_data: Any) -> Dict[str, Any]:
        """펀더멘털 분석 실행 - 실제 재무 데이터 기반"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN') if hasattr(stock_data, 'symbol') else stock_data.get('symbol', 'UNKNOWN') if isinstance(stock_data, dict) else 'UNKNOWN'
            
            # 실제 재무 데이터 조회 시도
            financial_data = await self._get_financial_data(symbol, stock_data)
            
            if not financial_data:
                self.logger.warning(f"⚠️ {symbol} 재무 데이터를 가져올 수 없어 기본값 사용")
                return self._get_default_analysis(symbol)
            
            # 실제 데이터 기반 분석
            result = await self._analyze_financial_metrics(financial_data, stock_data)
            
            self.logger.info(f"✅ {symbol} 펀더멘털 분석 완료 - 점수: {result['overall_score']:.1f}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 펀더멘털 분석 실패: {e}")
            return self._get_default_analysis('UNKNOWN')
    
    async def _get_financial_data(self, symbol: str, stock_data: Any) -> Optional[Dict]:
        """stock_data에서 사용 가능한 모든 재무 데이터 추출"""
        try:
            if not stock_data:
                return None

            financial_data = {}
            data_source = stock_data if isinstance(stock_data, dict) else stock_data.__dict__

            # 사용 가능한 모든 재무 관련 필드 추출
            for field in ['pe_ratio', 'pbr', 'eps', 'bps', 'market_cap', 'shares_outstanding']:
                if field in data_source and data_source[field] is not None:
                    financial_data[field] = data_source[field]
            
            self.logger.debug(f"Extracted financial data for {symbol}: {financial_data}")
            return financial_data if financial_data else None
            
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} 재무 데이터 추출 실패: {e}")
            return None
    
    async def _analyze_financial_metrics(self, financial_data: Dict, stock_data: Any) -> Dict[str, Any]:
        """실제 재무 지표 분석"""
        try:
            # 점수 초기화
            pe_score, pbr_score, stability_score, growth_score, profitability_score = 50, 50, 50, 50, 50

            # PE 비율 분석
            pe_ratio = financial_data.get('pe_ratio')
            if pe_ratio and pe_ratio > 0:
                if 5 <= pe_ratio <= 12:
                    pe_score = 90  # 이상적
                elif 12 < pe_ratio <= 18:
                    pe_score = 70  # 양호
                elif pe_ratio < 5:
                    pe_score = 40  # 너무 낮음 (위험 가능성)
                else:
                    pe_score = 30  # 고평가
            
            # PBR 분석
            pbr = financial_data.get('pbr')
            if pbr and pbr > 0:
                if 0.5 <= pbr <= 1.2:
                    pbr_score = 90 # 이상적
                elif 1.2 < pbr <= 2.0:
                    pbr_score = 70 # 양호
                elif pbr < 0.5:
                    pbr_score = 40 # 너무 낮음 (위험 가능성)
                else:
                    pbr_score = 30 # 고평가

            # 성장성 (EPS) 분석 - 현재는 값의 유무만 판단
            eps = financial_data.get('eps')
            if eps and eps > 0:
                growth_score = 75 # 긍정적 EPS
            elif eps is not None and eps <= 0:
                growth_score = 25 # 부정적 EPS

            # 수익성 (ROE) 근사치 분석
            if pe_ratio and pbr and pe_ratio > 0:
                roe_approx = (pbr / pe_ratio) * 100
                if roe_approx >= 15:
                    profitability_score = 90 # 매우 높음
                elif 10 <= roe_approx < 15:
                    profitability_score = 75 # 높음
                elif 5 <= roe_approx < 10:
                    profitability_score = 60 # 양호
                else:
                    profitability_score = 40 # 낮음
            else:
                roe_approx = None

            # 시가총액 기반 안정성 점수
            market_cap = financial_data.get('market_cap', 0)
            if market_cap > 10000: stability_score = 90
            elif market_cap > 5000: stability_score = 80
            elif market_cap > 1000: stability_score = 70
            else: stability_score = 50
            
            # 종합 점수 계산 (가중치 조정)
            weights = {'pe': 0.25, 'pbr': 0.25, 'stability': 0.2, 'growth': 0.15, 'profitability': 0.15}
            overall_score = (
                pe_score * weights['pe'] + 
                pbr_score * weights['pbr'] + 
                stability_score * weights['stability'] + 
                growth_score * weights['growth'] + 
                profitability_score * weights['profitability']
            )
            
            return {
                'overall_score': round(overall_score, 1),
                'pe_ratio': pe_ratio,
                'pbr': pbr,
                'eps': eps,
                'bps': financial_data.get('bps'),
                'market_cap': market_cap,
                'roe_approx': roe_approx,
                'scores': {
                    'pe': pe_score,
                    'pbr': pbr_score,
                    'stability': stability_score,
                    'growth': growth_score,
                    'profitability': profitability_score
                },
                'financial_health': 'GOOD' if overall_score >= 75 else 'FAIR' if overall_score >= 55 else 'POOR',
                'valuation': 'UNDERVALUED' if (pe_score + pbr_score) / 2 >= 75 else 'FAIR' if (pe_score + pbr_score) / 2 >= 55 else 'OVERVALUED'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 재무 지표 분석 실패: {e}")
            return self._get_default_analysis(financial_data.get('symbol', 'UNKNOWN'))
    
    def _get_default_analysis(self, symbol: str) -> Dict[str, Any]:
        """기본 분석 결과 반환 (데이터 없을 때)"""
        return {
            'overall_score': 50.0,
            'pe_ratio': None,
            'pbr': None,
            'eps': None,
            'bps': None,
            'market_cap': 0,
            'roe_approx': None,
            'scores': {
                'pe': 50,
                'pbr': 50,
                'stability': 50,
                'growth': 50,
                'profitability': 50
            },
            'financial_health': 'UNKNOWN',
            'valuation': 'UNKNOWN',
            'note': f'{symbol} 재무 데이터 없음 - 기본값 사용'
        }