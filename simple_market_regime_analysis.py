#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 AI 시장 체제 분석 (샘플 데이터 기반)
KIS API 문제 해결 전까지 임시 대안
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
import random

class SimpleMarketRegimeAnalyzer:
    """간단한 시장 체제 분석기 (샘플 데이터 기반)"""
    
    def __init__(self):
        self.analysis_time = datetime.now()
    
    def _generate_sample_market_data(self) -> Dict[str, Any]:
        """샘플 시장 데이터 생성"""
        # 현실적인 KOSPI/KOSDAQ 데이터 시뮬레이션
        kospi_base = 2450.0  # 대략적인 KOSPI 수준
        kosdaq_base = 850.0  # 대략적인 KOSDAQ 수준
        
        # -2% ~ +2% 범위의 변동률
        kospi_change = random.uniform(-2.0, 2.0)
        kosdaq_change = random.uniform(-2.0, 2.0)
        
        return {
            'KOSPI': {
                'current_price': round(kospi_base * (1 + kospi_change/100), 2),
                'change_rate': kospi_change,
                'volume': random.randint(400000, 800000),  # 40만~80만 거래량
                'market_cap': 1950000000  # 약 1,950조원
            },
            'KOSDAQ': {
                'current_price': round(kosdaq_base * (1 + kosdaq_change/100), 2),
                'change_rate': kosdaq_change,
                'volume': random.randint(800000, 1500000),  # 80만~150만 거래량
                'market_cap': 320000000  # 약 320조원
            }
        }
    
    def _analyze_market_regime(self, market_data: Dict[str, Any]) -> str:
        """시장 체제 분석"""
        kospi_change = market_data['KOSPI']['change_rate']
        kosdaq_change = market_data['KOSDAQ']['change_rate']
        
        avg_change = (kospi_change + kosdaq_change) / 2
        
        # 시장 체제 판단 로직
        if avg_change > 1.0:
            return "강세장 (Bull Market)"
        elif avg_change < -1.0:
            return "약세장 (Bear Market)"
        else:
            return "횡보장 (Sideways Market)"
    
    def _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """신뢰도 계산"""
        kospi_change = abs(market_data['KOSPI']['change_rate'])
        kosdaq_change = abs(market_data['KOSDAQ']['change_rate'])
        
        # 변동폭이 클수록 신뢰도 높음
        avg_volatility = (kospi_change + kosdaq_change) / 2
        confidence = min(50 + avg_volatility * 15, 95)  # 50% ~ 95% 범위
        
        return round(confidence, 1)
    
    async def analyze(self) -> Dict[str, Any]:
        """AI 시장 체제 분석 실행"""
        print("AI 시장 체제 분석 시작...")
        
        # 샘플 데이터 생성
        market_data = self._generate_sample_market_data()
        
        # 시장 체제 분석
        regime_type = self._analyze_market_regime(market_data)
        confidence = self._calculate_confidence(market_data)
        
        # 추가 분석 정보
        kospi_strength = "상승" if market_data['KOSPI']['change_rate'] > 0 else "하락"
        kosdaq_strength = "상승" if market_data['KOSDAQ']['change_rate'] > 0 else "하락"
        
        result = {
            'analysis_time': self.analysis_time.strftime('%Y-%m-%d %H:%M:%S'),
            'regime_type': regime_type,
            'confidence': confidence,
            'market_data': market_data,
            'market_analysis': {
                'kospi_direction': kospi_strength,
                'kosdaq_direction': kosdaq_strength,
                'correlation': "높음" if abs(market_data['KOSPI']['change_rate'] - market_data['KOSDAQ']['change_rate']) < 1.0 else "낮음"
            },
            'recommendations': self._generate_recommendations(regime_type, market_data),
            'note': "샘플 데이터 기반 분석 (KIS API 연결 후 실제 데이터로 전환 예정)"
        }
        
        return result
    
    def _generate_recommendations(self, regime_type: str, market_data: Dict[str, Any]) -> Dict[str, str]:
        """투자 권고 생성"""
        recommendations = {}
        
        if "강세장" in regime_type:
            recommendations['strategy'] = "적극적 매수 전략"
            recommendations['focus'] = "성장주 중심 포트폴리오"
            recommendations['risk_level'] = "중위험"
        elif "약세장" in regime_type:
            recommendations['strategy'] = "방어적 포지션"
            recommendations['focus'] = "안전자산 및 배당주"
            recommendations['risk_level'] = "저위험"
        else:  # 횡보장
            recommendations['strategy'] = "단기 매매 전략"
            recommendations['focus'] = "섹터 로테이션"
            recommendations['risk_level'] = "중위험"
        
        return recommendations

async def main():
    """메인 실행 함수"""
    analyzer = SimpleMarketRegimeAnalyzer()
    result = await analyzer.analyze()
    
    print("\n" + "="*60)
    print("AI 시장 체제 분석 결과")
    print("="*60)
    print(f"분석 시간: {result['analysis_time']}")
    print(f"시장 체제: {result['regime_type']}")
    print(f"신뢰도: {result['confidence']}%")
    print()
    
    print("시장 데이터:")
    kospi = result['market_data']['KOSPI']
    kosdaq = result['market_data']['KOSDAQ']
    print(f"  KOSPI: {kospi['current_price']} ({kospi['change_rate']:+.2f}%)")
    print(f"  KOSDAQ: {kosdaq['current_price']} ({kosdaq['change_rate']:+.2f}%)")
    print()
    
    print("시장 분석:")
    analysis = result['market_analysis']
    print(f"  KOSPI 방향: {analysis['kospi_direction']}")
    print(f"  KOSDAQ 방향: {analysis['kosdaq_direction']}")
    print(f"  상관관계: {analysis['correlation']}")
    print()
    
    print("투자 권고:")
    rec = result['recommendations']
    print(f"  전략: {rec['strategy']}")
    print(f"  포커스: {rec['focus']}")
    print(f"  위험도: {rec['risk_level']}")
    print()
    
    print(f"참고사항: {result['note']}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())