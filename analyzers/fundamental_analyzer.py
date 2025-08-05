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
        """실제 재무 데이터 조회"""
        try:
            # TODO: KIS API 또는 다른 재무 데이터 API에서 실제 데이터 조회
            # 현재는 stock_data에서 사용 가능한 데이터만 추출
            
            financial_data = {}
            
            # stock_data에서 기본 재무 지표 추출
            if hasattr(stock_data, 'pe_ratio') or (isinstance(stock_data, dict) and 'pe_ratio' in stock_data):
                financial_data['pe_ratio'] = getattr(stock_data, 'pe_ratio', stock_data.get('pe_ratio')) if hasattr(stock_data, 'pe_ratio') else stock_data.get('pe_ratio')
            
            if hasattr(stock_data, 'pbr') or (isinstance(stock_data, dict) and 'pbr' in stock_data):
                financial_data['pbr'] = getattr(stock_data, 'pbr', stock_data.get('pbr')) if hasattr(stock_data, 'pbr') else stock_data.get('pbr')
            
            if hasattr(stock_data, 'market_cap') or (isinstance(stock_data, dict) and 'market_cap' in stock_data):
                financial_data['market_cap'] = getattr(stock_data, 'market_cap', stock_data.get('market_cap')) if hasattr(stock_data, 'market_cap') else stock_data.get('market_cap')
            
            return financial_data if financial_data else None
            
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} 재무 데이터 조회 실패: {e}")
            return None
    
    async def _analyze_financial_metrics(self, financial_data: Dict, stock_data: Any) -> Dict[str, Any]:
        """실제 재무 지표 분석"""
        try:
            score = 50.0  # 기본 점수
            
            # PE 비율 분석
            pe_ratio = financial_data.get('pe_ratio')
            pe_score = 50
            if pe_ratio:
                if 8 <= pe_ratio <= 15:
                    pe_score = 80  # 적정 밸류에이션
                elif 5 <= pe_ratio < 8:
                    pe_score = 70  # 저평가
                elif 15 < pe_ratio <= 25:
                    pe_score = 40  # 약간 고평가
                elif pe_ratio > 25:
                    pe_score = 20  # 고평가
                elif pe_ratio < 5:
                    pe_score = 30  # 너무 저평가 (위험)
            
            # PBR 분석
            pbr = financial_data.get('pbr')
            pbr_score = 50
            if pbr:
                if 0.8 <= pbr <= 1.5:
                    pbr_score = 80  # 적정 수준
                elif 0.5 <= pbr < 0.8:
                    pbr_score = 70  # 저평가
                elif 1.5 < pbr <= 2.5:
                    pbr_score = 40  # 약간 고평가
                elif pbr > 2.5:
                    pbr_score = 20  # 고평가
                elif pbr < 0.5:
                    pbr_score = 30  # 위험 수준
            
            # 시가총액 기반 안정성 점수
            market_cap = financial_data.get('market_cap', 0)
            stability_score = 50
            if market_cap > 10000:  # 10조 이상
                stability_score = 80
            elif market_cap > 5000:  # 5조 이상
                stability_score = 70
            elif market_cap > 1000:  # 1조 이상
                stability_score = 60
            elif market_cap > 500:  # 5000억 이상
                stability_score = 50
            else:
                stability_score = 30  # 소형주
            
            # 종합 점수 계산
            overall_score = (pe_score * 0.4 + pbr_score * 0.4 + stability_score * 0.2)
            
            return {
                'overall_score': round(overall_score, 1),
                'signal_strength': round(overall_score * 0.8, 1),  # 보수적 접근
                'confidence': min(0.8, overall_score / 100),
                'pe_ratio': pe_ratio,
                'pbr': pbr,
                'market_cap': market_cap,
                'pe_score': pe_score,
                'pbr_score': pbr_score,
                'stability_score': stability_score,
                'financial_health': 'GOOD' if overall_score >= 70 else 'FAIR' if overall_score >= 50 else 'POOR',
                'valuation': 'UNDERVALUED' if overall_score >= 70 else 'FAIR' if overall_score >= 50 else 'OVERVALUED'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 재무 지표 분석 실패: {e}")
            return self._get_default_analysis('UNKNOWN')
    
    def _get_default_analysis(self, symbol: str) -> Dict[str, Any]:
        """기본 분석 결과 반환 (데이터 없을 때)"""
        return {
            'overall_score': 50.0,
            'signal_strength': 50.0,
            'confidence': 0.5,
            'pe_ratio': None,
            'pbr': None,
            'market_cap': 0,
            'financial_health': 'UNKNOWN',
            'valuation': 'UNKNOWN',
            'note': f'{symbol} 재무 데이터 없음 - 기본값 사용'
        }