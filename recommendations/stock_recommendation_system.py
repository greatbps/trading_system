#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
종목 추천 시스템 - Squeeze Momentum Pro 전략과 Phase 1 통합
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from dataclasses import asdict

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from recommendations.squeeze_momentum_engine import (
    SqueezeMomentumRecommendationEngine, 
    SqueezeMomentumCandidate,
    QualityAssessment
)
from configs.squeeze_momentum_config import squeeze_momentum_config

class StockRecommendationSystem:
    """종합 종목 추천 시스템"""
    
    def __init__(self, config=None):
        self.config = config or squeeze_momentum_config
        self.logger = self._setup_logger()
        
        # 2차 필터링 엔진 초기화
        self.recommendation_engine = SqueezeMomentumRecommendationEngine(config)
        
        # 추천 이력 및 성과 추적
        self.recommendation_history = []
        self.performance_stats = {
            'daily_recommendations': {},
            'success_tracking': {},
            'processing_metrics': []
        }
        
        self.logger.info("🎯 종목 추천 시스템 초기화 완료")
    
    def _setup_logger(self):
        """로거 설정"""
        import logging
        logger = logging.getLogger("RecommendationSystem")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    async def generate_daily_recommendations(self, primary_candidates: List[Dict] = None) -> Dict[str, Any]:
        """일일 종목 추천 생성"""
        start_time = time.perf_counter()
        today = datetime.now().strftime('%Y-%m-%d')
        
        self.logger.info(f"📊 {today} 종목 추천 생성 시작")
        
        try:
            # 1. 1차 필터링 결과 처리 (제미나이가 제공할 데이터)
            if primary_candidates is None:
                primary_candidates = await self._get_mock_primary_candidates()
            
            # SqueezeMomentumCandidate 객체로 변환
            candidates = [self._convert_to_candidate(data) for data in primary_candidates]
            
            # 2. 2차 필터링 적용 (Phase 1 품질 게이트)
            high_quality_recommendations = await self.recommendation_engine.apply_secondary_filter(candidates)
            
            # 3. 최종 추천 리스트 구성
            final_recommendations = self._build_final_recommendations(high_quality_recommendations)
            
            # 4. 추천 등급별 그룹핑
            grouped_recommendations = self._group_by_recommendation_grade(final_recommendations)
            
            # 5. 리스크 분산 및 포트폴리오 최적화
            optimized_recommendations = self._optimize_portfolio_allocation(grouped_recommendations)
            
            # 6. 추천 리포트 생성
            recommendation_report = self._generate_recommendation_report(
                today, optimized_recommendations, len(primary_candidates), len(final_recommendations)
            )
            
            # 7. 성과 추적을 위한 이력 저장
            self._save_recommendation_history(today, recommendation_report)
            
            # 8. 처리 시간 기록
            processing_time = (time.perf_counter() - start_time) * 1000
            self.performance_stats['processing_metrics'].append({
                'date': today,
                'processing_time_ms': processing_time,
                'primary_candidates': len(primary_candidates),
                'final_recommendations': len(final_recommendations)
            })
            
            self.logger.info(f"✅ {today} 종목 추천 완료 - "
                           f"최종 추천: {len(final_recommendations)}개 ({processing_time:.1f}ms)")
            
            return recommendation_report
            
        except Exception as e:
            self.logger.error(f"❌ 종목 추천 생성 실패: {e}")
            return self._create_error_report(today, str(e))
    
    async def _get_mock_primary_candidates(self) -> List[Dict]:
        """테스트용 모의 1차 필터링 후보 데이터"""
        return [
            {
                'symbol': '005930',
                'name': '삼성전자',
                'current_price': 72000,
                'squeeze_duration': 8,
                'squeeze_release_signal': True,
                'momentum_strength': 0.75,
                'momentum_direction': 'bullish',
                'bb_squeeze_ratio': 0.8,
                'kc_position': 0.6,
                'volume_ratio': 2.1,
                'atr_percentile': 0.7,
                'sector': '전기전자',
                'market_cap': 430000000000000,
                'trading_value': 5000000000,
                'volatility': 0.04
            },
            {
                'symbol': '000660',
                'name': 'SK하이닉스',
                'current_price': 135000,
                'squeeze_duration': 12,
                'squeeze_release_signal': True,
                'momentum_strength': 0.65,
                'momentum_direction': 'bullish',
                'bb_squeeze_ratio': 0.9,
                'kc_position': 0.7,
                'volume_ratio': 1.8,
                'atr_percentile': 0.8,
                'sector': '반도체',
                'market_cap': 98000000000000,
                'trading_value': 3200000000,
                'volatility': 0.06
            },
            {
                'symbol': '035420',
                'name': 'NAVER',
                'current_price': 185000,
                'squeeze_duration': 6,
                'squeeze_release_signal': True,
                'momentum_strength': 0.55,
                'momentum_direction': 'bullish',
                'bb_squeeze_ratio': 0.7,
                'kc_position': 0.5,
                'volume_ratio': 1.6,
                'atr_percentile': 0.6,
                'sector': '인터넷',
                'market_cap': 30000000000000,
                'trading_value': 1800000000,
                'volatility': 0.05
            }
        ]
    
    def _convert_to_candidate(self, data: Dict) -> SqueezeMomentumCandidate:
        """딕셔너리 데이터를 SqueezeMomentumCandidate 객체로 변환"""
        return SqueezeMomentumCandidate(
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            current_price=data.get('current_price', 0),
            squeeze_duration=data.get('squeeze_duration', 0),
            squeeze_release_signal=data.get('squeeze_release_signal', False),
            momentum_strength=data.get('momentum_strength', 0.0),
            momentum_direction=data.get('momentum_direction', 'neutral'),
            bb_squeeze_ratio=data.get('bb_squeeze_ratio', 0.0),
            kc_position=data.get('kc_position', 0.0),
            volume_ratio=data.get('volume_ratio', 1.0),
            atr_percentile=data.get('atr_percentile', 0.5),
            sector=data.get('sector', 'Unknown'),
            market_cap=data.get('market_cap', 0.0),
            trading_value=data.get('trading_value', 0.0),
            volatility=data.get('volatility', 0.03)
        )
    
    def _build_final_recommendations(self, high_quality_candidates: List[Dict]) -> List[Dict]:
        """최종 추천 리스트 구성"""
        final_recommendations = []
        
        for candidate in high_quality_candidates:
            # 추가 메타 정보 보강
            recommendation = candidate.copy()
            
            # 예상 수익률 계산 (Squeeze Momentum 기반)
            expected_return = self._calculate_expected_return(candidate)
            recommendation['expected_return_pct'] = expected_return
            
            # 적정 보유기간 추천
            holding_period = self._recommend_holding_period(candidate)
            recommendation['recommended_holding_days'] = holding_period
            
            # 포지션 사이징 권장
            position_size = self._recommend_position_size(candidate)
            recommendation['recommended_position_pct'] = position_size
            
            # 진입/청산 포인트
            entry_exit_points = self._calculate_entry_exit_points(candidate)
            recommendation.update(entry_exit_points)
            
            final_recommendations.append(recommendation)
        
        return final_recommendations
    
    def _calculate_expected_return(self, candidate: Dict) -> float:
        """예상 수익률 계산"""
        # Squeeze duration과 momentum strength를 기반으로 수익률 추정
        base_return = candidate['squeeze_info']['momentum_strength'] * 10  # 0.5 강도 = 5%
        
        # Squeeze 지속기간 보너스
        duration_bonus = min(5, candidate['squeeze_info']['duration'] - 5) * 0.5
        
        # 품질 등급 가중치
        quality_multiplier = {
            'high': 1.2,
            'medium': 1.0,
            'low': 0.7
        }.get(candidate['quality_assessment']['grade'], 0.7)
        
        expected_return = (base_return + duration_bonus) * quality_multiplier
        
        return round(min(20, max(3, expected_return)), 1)  # 3-20% 범위로 제한
    
    def _recommend_holding_period(self, candidate: Dict) -> int:
        """적정 보유기간 추천"""
        # Squeeze 지속기간 기반
        base_days = candidate['squeeze_info']['duration'] * 2
        
        # 변동성 조정
        volatility = candidate['metadata']['volatility']
        if volatility > 0.06:  # 고변동성
            base_days = int(base_days * 0.7)  # 짧게
        elif volatility < 0.03:  # 저변동성
            base_days = int(base_days * 1.3)  # 길게
        
        return max(5, min(30, base_days))  # 5-30일 범위
    
    def _recommend_position_size(self, candidate: Dict) -> float:
        """포지션 사이징 권장"""
        # 기본 포지션 크기
        base_position = 5.0  # 5%
        
        # 품질 등급별 조정
        quality_multiplier = {
            'high': 1.5,
            'medium': 1.0,
            'low': 0.6
        }.get(candidate['quality_assessment']['grade'], 0.5)
        
        # 리스크 레벨별 조정
        risk_multiplier = {
            'LOW': 1.2,
            'MEDIUM': 1.0,
            'HIGH': 0.5
        }.get(candidate['quality_assessment']['risk_level'], 0.5)
        
        recommended_size = base_position * quality_multiplier * risk_multiplier
        
        return round(min(10, max(1, recommended_size)), 1)  # 1-10% 범위
    
    def _calculate_entry_exit_points(self, candidate: Dict) -> Dict[str, float]:
        """진입/청산 포인트 계산"""
        current_price = candidate['current_price']
        volatility = candidate['metadata']['volatility']
        
        # 진입 포인트 (현재가 기준)
        entry_price = current_price
        
        # 손절가 (ATR 기반)
        atr_estimate = current_price * volatility * 2
        stop_loss = current_price - (atr_estimate * 2)
        
        # 목표가 (위험 대비 2:1 수익)
        risk_amount = current_price - stop_loss
        take_profit = current_price + (risk_amount * 2)
        
        return {
            'entry_price': round(entry_price, 0),
            'stop_loss': round(stop_loss, 0),
            'take_profit': round(take_profit, 0),
            'risk_reward_ratio': 2.0
        }
    
    def _group_by_recommendation_grade(self, recommendations: List[Dict]) -> Dict[str, List[Dict]]:
        """추천 등급별 그룹핑"""
        grouped = {
            'STRONG_BUY': [],
            'BUY': [],
            'HOLD': [],
            'WATCH': []
        }
        
        for rec in recommendations:
            grade = rec.get('recommendation_grade', 'WATCH')
            if grade in grouped:
                grouped[grade].append(rec)
        
        # 각 그룹 내에서 점수순으로 정렬
        for grade in grouped:
            grouped[grade].sort(key=lambda x: x['overall_score'], reverse=True)
        
        return grouped
    
    def _optimize_portfolio_allocation(self, grouped_recommendations: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """포트폴리오 분산 최적화"""
        optimized = {}
        
        # 등급별 최대 추천 수 제한
        max_counts = {
            'STRONG_BUY': 5,
            'BUY': 8,
            'HOLD': 5,
            'WATCH': 10
        }
        
        for grade, candidates in grouped_recommendations.items():
            max_count = max_counts.get(grade, 10)
            
            # 섹터 분산을 고려한 선별
            sector_balanced = self._apply_sector_diversification(candidates, max_count)
            optimized[grade] = sector_balanced
        
        return optimized
    
    def _apply_sector_diversification(self, candidates: List[Dict], max_count: int) -> List[Dict]:
        """섹터 분산 적용"""
        if len(candidates) <= max_count:
            return candidates
        
        # 섹터별 그룹핑
        sectors = {}
        for candidate in candidates:
            sector = candidate['metadata']['sector']
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(candidate)
        
        # 각 섹터에서 최고 점수 종목 선별
        selected = []
        remaining_slots = max_count
        
        # 1차: 각 섹터에서 1개씩
        for sector, sector_candidates in sectors.items():
            if remaining_slots > 0:
                best_candidate = max(sector_candidates, key=lambda x: x['overall_score'])
                selected.append(best_candidate)
                sector_candidates.remove(best_candidate)
                remaining_slots -= 1
        
        # 2차: 남은 슬롯에 최고 점수 순으로
        all_remaining = []
        for sector_candidates in sectors.values():
            all_remaining.extend(sector_candidates)
        
        all_remaining.sort(key=lambda x: x['overall_score'], reverse=True)
        selected.extend(all_remaining[:remaining_slots])
        
        return selected
    
    def _generate_recommendation_report(self, date: str, recommendations: Dict[str, List[Dict]], 
                                      primary_count: int, final_count: int) -> Dict[str, Any]:
        """추천 리포트 생성"""
        # 등급별 통계
        grade_stats = {}
        total_expected_return = 0
        total_recommended_position = 0
        
        for grade, candidates in recommendations.items():
            if candidates:
                scores = [c['overall_score'] for c in candidates]
                returns = [c['expected_return_pct'] for c in candidates]
                positions = [c['recommended_position_pct'] for c in candidates]
                
                grade_stats[grade] = {
                    'count': len(candidates),
                    'avg_score': round(sum(scores) / len(scores), 1),
                    'avg_expected_return': round(sum(returns) / len(returns), 1),
                    'total_position': round(sum(positions), 1)
                }
                
                total_expected_return += sum(returns)
                total_recommended_position += sum(positions)
        
        # 포트폴리오 요약
        portfolio_summary = {
            'total_stocks': final_count,
            'total_position_pct': round(total_recommended_position, 1),
            'portfolio_expected_return': round(total_expected_return / max(1, final_count), 1),
            'risk_distribution': self._calculate_risk_distribution(recommendations)
        }
        
        # 최종 리포트 구성
        report = {
            'date': date,
            'generation_time': datetime.now().isoformat(),
            'filter_summary': {
                'primary_candidates': primary_count,
                'final_recommendations': final_count,
                'filter_success_rate': round((final_count / max(1, primary_count)) * 100, 1)
            },
            'recommendations_by_grade': recommendations,
            'grade_statistics': grade_stats,
            'portfolio_summary': portfolio_summary,
            'market_context': self._get_market_context(),
            'disclaimer': self._get_disclaimer()
        }
        
        return report
    
    def _calculate_risk_distribution(self, recommendations: Dict[str, List[Dict]]) -> Dict[str, int]:
        """리스크 분산 분석"""
        risk_count = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0}
        
        for grade, candidates in recommendations.items():
            for candidate in candidates:
                risk_level = candidate['quality_assessment']['risk_level']
                risk_count[risk_level] += 1
        
        return risk_count
    
    def _get_market_context(self) -> Dict[str, str]:
        """시장 컨텍스트 정보"""
        return {
            'strategy_focus': 'Squeeze Momentum Pro - 볼린저 밴드 압축 후 돌파 전략',
            'market_regime': '중립/상승 시장에 최적화',
            'recommended_allocation': '포트폴리오의 20-40% 내에서 분산 투자 권장',
            'holding_period': '단기-중기 (5-30일) 트레이딩 전략'
        }
    
    def _get_disclaimer(self) -> str:
        """면책 조항"""
        return ("본 추천은 Squeeze Momentum Pro 전략과 AI 분석에 기반한 참고 자료이며, "
                "투자의 최종 책임은 투자자 본인에게 있습니다. 실제 투자 시 충분한 검토 후 결정하시기 바랍니다.")
    
    def _save_recommendation_history(self, date: str, report: Dict[str, Any]):
        """추천 이력 저장"""
        self.recommendation_history.append({
            'date': date,
            'total_recommendations': report['filter_summary']['final_recommendations'],
            'grade_breakdown': {
                grade: len(candidates) 
                for grade, candidates in report['recommendations_by_grade'].items()
            },
            'portfolio_summary': report['portfolio_summary']
        })
        
        # 이력을 파일로 저장
        try:
            filename = f"recommendation_history_{date.replace('-', '')}.json"
            filepath = PROJECT_ROOT / 'results' / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"💾 추천 이력 저장: {filename}")
            
        except Exception as e:
            self.logger.error(f"❌ 추천 이력 저장 실패: {e}")
    
    def _create_error_report(self, date: str, error_message: str) -> Dict[str, Any]:
        """에러 리포트 생성"""
        return {
            'date': date,
            'generation_time': datetime.now().isoformat(),
            'status': 'ERROR',
            'error_message': error_message,
            'recommendations_by_grade': {
                'STRONG_BUY': [],
                'BUY': [],
                'HOLD': [],
                'WATCH': []
            },
            'filter_summary': {
                'primary_candidates': 0,
                'final_recommendations': 0,
                'filter_success_rate': 0
            }
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        engine_stats = self.recommendation_engine.get_processing_statistics()
        
        return {
            'system_status': 'ACTIVE',
            'last_run': self.recommendation_history[-1]['date'] if self.recommendation_history else None,
            'total_sessions': len(self.recommendation_history),
            'engine_performance': engine_stats,
            'average_recommendations_per_day': (
                sum(h['total_recommendations'] for h in self.recommendation_history) /
                max(1, len(self.recommendation_history))
            ) if self.recommendation_history else 0
        }