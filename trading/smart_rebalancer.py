#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/smart_rebalancer.py

스마트 리밸런싱 시스템 - 매매 조건 기반 동적 포트폴리오 관리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert
from utils.logger import get_logger
from database.models import MonitoringStock, MonitoringStatus, MonitoringType


@dataclass 
class StockEvaluation:
    """종목 평가 결과"""
    symbol: str
    name: str
    
    # 기존 5개 평가 항목
    recommendation_score: float      # 추천 점수 (0-100)
    technical_score: float          # 기술적 분석 점수 (0-100)
    fundamental_score: float        # 펀더멘털 점수 (0-100)
    momentum_score: float           # 모멘텀 점수 (0-100)
    risk_score: float               # 리스크 점수 (0-100, 낮을수록 좋음)
    
    # 새로운 매매 조건 점수 (가중치 높음)
    trading_signal_score: float     # 매매 신호 점수 (0-100)
    
    # 종합 점수
    total_score: float              # 최종 종합 점수
    
    # 메타 정보
    current_price: float
    change_rate: float
    volume_ratio: float
    last_updated: datetime
    
    # 매매 관련 정보
    is_holding: bool = False        # 현재 보유 중인지
    entry_price: Optional[float] = None
    holding_days: int = 0
    unrealized_pnl_pct: float = 0.0


class SmartRebalancer:
    """스마트 리밸런싱 시스템 - DB 연동"""
    
    def __init__(self, config, db_manager=None):
        self.config = config
        self.db_manager = db_manager
        self.logger = get_logger("SmartRebalancer")
        
        # 리밸런싱 설정 (config에서 가져오기)
        self.max_positions = getattr(config.trading, 'MAX_POSITIONS', 10)  # config.py에서 10개
        self.rebalance_threshold = 10   # 리밸런싱 임계점 (점수 차이)
        
        # 평가 가중치 (매매 조건 점수 비중을 높게)
        self.evaluation_weights = {
            'recommendation': 0.15,      # 추천 점수
            'technical': 0.15,           # 기술적 분석  
            'fundamental': 0.10,         # 펀더멘털
            'momentum': 0.15,            # 모멘텀
            'risk': 0.10,                # 리스크 (역가중치)
            'trading_signal': 0.35       # 매매 신호 (가장 높은 비중)
        }
        
        # 현재 평가된 종목들
        self.evaluated_stocks = {}      # symbol -> StockEvaluation
        self.current_top_positions = []         # 현재 Top N 종목 리스트 (10개)
        self.last_rebalance_time = None
        
        self.logger.info(f"✅ 스마트 리밸런서 초기화 완료 (최대 {self.max_positions}개 포지션)")
        self.logger.info(f"📊 평가 가중치: {self.evaluation_weights}")
        
        # DB에서 기존 모니터링 종목 복원 (중복 방지)
        self._restored = False  # 복원 상태 추적
        if self.db_manager:
            # 즉시 실행하지 않고 지연 실행으로 중복 방지
            self._restore_task = None
    
    async def ensure_restored(self):
        """DB 복원이 완료되었는지 확인하고 필요시 실행"""
        if not self._restored and self.db_manager:
            await self._restore_from_database()

    async def add_new_candidate(self, symbol: str, stock_data: Dict, tech_data: Dict, 
                              trading_signal_score: float) -> Dict[str, Any]:
        """새로운 매수 후보 추가 및 리밸런싱"""
        try:
            # DB 복원 확인
            await self.ensure_restored()
            
            self.logger.info(f"🆕 {symbol} 새로운 후보 추가 - 매매신호점수: {trading_signal_score:.1f}")
            
            # 1. 새 종목 평가
            evaluation = await self._evaluate_stock(symbol, stock_data, tech_data, trading_signal_score)
            self.evaluated_stocks[symbol] = evaluation
            
            # 2. 전체 종목 재평가 및 순위 계산
            rebalance_result = await self._perform_smart_rebalancing()
            
            # 3. 결과 반환
            result = {
                'new_stock': {
                    'symbol': symbol,
                    'evaluation': evaluation,
                    'rank': rebalance_result['rankings'].get(symbol, {}).get('rank', 0)
                },
                'rebalancing': rebalance_result,
                'action_required': rebalance_result['changes_needed'],
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ {symbol} 후보 추가 완료 - 순위: {result['new_stock']['rank']}/5")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 후보 추가 실패: {e}")
            return {'error': str(e)}
    
    async def _evaluate_stock(self, symbol: str, stock_data: Dict, tech_data: Dict,
                            trading_signal_score: float) -> StockEvaluation:
        """종목 종합 평가"""
        try:
            # 기본 정보 추출
            current_price = stock_data.get('current_price', tech_data.get('current_price', 0))
            change_rate = stock_data.get('change_rate', tech_data.get('change_rate', 0))
            volume = tech_data.get('volume', 0)
            volume_avg = tech_data.get('volume_avg', volume)
            volume_ratio = volume / volume_avg if volume_avg > 0 else 1.0
            
            # 1. 추천 점수 (외부 추천 시스템 점수)
            recommendation_score = stock_data.get('recommendation_score', 70)
            
            # 2. 기술적 분석 점수
            technical_score = await self._calculate_technical_score(tech_data)
            
            # 3. 펀더멘털 점수 
            fundamental_score = await self._calculate_fundamental_score(stock_data)
            
            # 4. 모멘텀 점수
            momentum_score = await self._calculate_momentum_score(stock_data, tech_data)
            
            # 5. 리스크 점수 (낮을수록 좋음)
            risk_score = await self._calculate_risk_score(stock_data, tech_data)
            
            # 6. 종합 점수 계산 (가중평균)
            total_score = (
                recommendation_score * self.evaluation_weights['recommendation'] +
                technical_score * self.evaluation_weights['technical'] +
                fundamental_score * self.evaluation_weights['fundamental'] +
                momentum_score * self.evaluation_weights['momentum'] +
                (100 - risk_score) * self.evaluation_weights['risk'] +  # 리스크는 역가중치
                trading_signal_score * self.evaluation_weights['trading_signal']
            )
            
            return StockEvaluation(
                symbol=symbol,
                name=stock_data.get('name', symbol),
                recommendation_score=recommendation_score,
                technical_score=technical_score,
                fundamental_score=fundamental_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                trading_signal_score=trading_signal_score,
                total_score=total_score,
                current_price=current_price,
                change_rate=change_rate,
                volume_ratio=volume_ratio,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 평가 실패: {e}")
            # 기본값으로 평가 객체 생성
            return StockEvaluation(
                symbol=symbol,
                name=stock_data.get('name', symbol),
                recommendation_score=50,
                technical_score=50,
                fundamental_score=50,
                momentum_score=50,
                risk_score=50,
                trading_signal_score=trading_signal_score,
                total_score=50,
                current_price=current_price,
                change_rate=0,
                volume_ratio=1.0,
                last_updated=datetime.now()
            )
    
    async def _calculate_technical_score(self, tech_data: Dict) -> float:
        """기술적 분석 점수 계산"""
        try:
            score = 50  # 기본값
            
            ema_5 = tech_data.get('ema_5', 0)
            ema_20 = tech_data.get('ema_20', 0)
            rsi = tech_data.get('rsi', 50)
            current_price = tech_data.get('current_price', 0)
            
            # EMA 관계
            if ema_5 > ema_20 > 0:
                score += 20  # 상승 추세
                gap_ratio = (ema_5 - ema_20) / ema_20 * 100
                if 0.5 < gap_ratio < 2.0:
                    score += 10  # 적정 확산
            
            # RSI 
            if 30 < rsi < 70:
                score += 15  # 정상 범위
            elif 20 < rsi <= 30:
                score += 10  # 과매도 (매수 기회)
            elif rsi >= 80:
                score -= 10  # 과매수 위험
            
            # 현재가와 EMA 관계
            if current_price > ema_5 > 0:
                score += 15  # EMA 위에 위치
            
            return max(0, min(100, score))
            
        except Exception:
            return 50
    
    async def _calculate_fundamental_score(self, stock_data: Dict) -> float:
        """펀더멘털 점수 계산"""
        try:
            score = 50  # 기본값
            
            # 시가총액 (단위: 억원)
            market_cap = stock_data.get('market_cap', 0)
            if market_cap > 10000:  # 1조 이상
                score += 20
            elif market_cap > 5000:  # 5천억 이상
                score += 15
            elif market_cap > 1000:  # 1천억 이상
                score += 10
            elif market_cap < 500:   # 500억 미만
                score -= 10
            
            # 거래량
            volume = stock_data.get('volume', 0)
            if volume > 1000000:  # 100만주 이상
                score += 10
            elif volume < 100000:  # 10만주 미만
                score -= 10
            
            # 업종/섹터 (간단한 예시)
            sector = stock_data.get('sector', '')
            if sector in ['반도체', 'IT', '바이오']:
                score += 5  # 성장 섹터 보너스
            
            return max(0, min(100, score))
            
        except Exception:
            return 50
    
    async def _calculate_momentum_score(self, stock_data: Dict, tech_data: Dict) -> float:
        """모멘텀 점수 계산"""
        try:
            score = 50  # 기본값
            
            change_rate = tech_data.get('change_rate', 0)
            volume_ratio = tech_data.get('volume', 0) / tech_data.get('volume_avg', 1)
            
            # 가격 모멘텀
            if change_rate > 3:
                score += 25  # 강한 상승
            elif change_rate > 1:
                score += 15  # 상승
            elif change_rate > 0:
                score += 5   # 약한 상승
            elif change_rate < -3:
                score -= 20  # 강한 하락
            elif change_rate < -1:
                score -= 10  # 하락
            
            # 거래량 모멘텀
            if volume_ratio > 2:
                score += 15  # 거래량 폭증
            elif volume_ratio > 1.5:
                score += 10  # 거래량 증가
            elif volume_ratio < 0.5:
                score -= 10  # 거래량 감소
            
            return max(0, min(100, score))
            
        except Exception:
            return 50
    
    async def _calculate_risk_score(self, stock_data: Dict, tech_data: Dict) -> float:
        """리스크 점수 계산 (높을수록 위험)"""
        try:
            risk_score = 20  # 기본값 (낮은 리스크)
            
            change_rate = tech_data.get('change_rate', 0)
            volume = tech_data.get('volume', 0)
            market_cap = stock_data.get('market_cap', 1000)
            
            # 변동성 리스크
            if abs(change_rate) > 5:
                risk_score += 25  # 고변동성
            elif abs(change_rate) > 3:
                risk_score += 15  # 중변동성
            
            # 유동성 리스크
            if volume < 100000:  # 10만주 미만
                risk_score += 20
            elif volume < 500000:  # 50만주 미만
                risk_score += 10
            
            # 시가총액 리스크
            if market_cap < 500:  # 500억 미만
                risk_score += 20
            elif market_cap < 1000:  # 1000억 미만
                risk_score += 10
            
            return max(0, min(100, risk_score))
            
        except Exception:
            return 50
    
    async def _perform_smart_rebalancing(self) -> Dict[str, Any]:
        """스마트 리밸런싱 수행"""
        try:
            self.logger.info("🔄 스마트 리밸런싱 시작")
            
            # 1. 모든 종목을 점수순으로 정렬
            sorted_stocks = sorted(
                self.evaluated_stocks.values(),
                key=lambda x: x.total_score,
                reverse=True
            )
            
            # 2. Top N 선정 (최대 10개)
            new_top_positions = sorted_stocks[:self.max_positions]
            new_top_symbols = [stock.symbol for stock in new_top_positions]
            
            # 3. 기존 Top N과 비교
            old_top_symbols = [stock.symbol for stock in self.current_top_positions]
            
            # 4. 변경사항 분석
            changes = {
                'added': [s for s in new_top_symbols if s not in old_top_symbols],
                'removed': [s for s in old_top_symbols if s not in new_top_symbols],
                'maintained': [s for s in new_top_symbols if s in old_top_symbols]
            }
            
            # 5. 순위 정보 생성
            rankings = {}
            for i, stock in enumerate(sorted_stocks):
                rankings[stock.symbol] = {
                    'rank': i + 1,
                    'total_score': stock.total_score,
                    'in_top_5': i < self.max_positions,
                    'score_breakdown': {
                        'recommendation': stock.recommendation_score,
                        'technical': stock.technical_score,
                        'fundamental': stock.fundamental_score,
                        'momentum': stock.momentum_score,
                        'risk': stock.risk_score,
                        'trading_signal': stock.trading_signal_score
                    }
                }
            
            # 6. Top N 업데이트
            self.current_top_positions = new_top_positions
            self.last_rebalance_time = datetime.now()
            
            # 7. DB 동기화
            if self.db_manager and (changes['added'] or changes['removed']):
                await self._sync_to_database(changes, new_top_positions)
            
            # 8. 결과 로깅
            if changes['added'] or changes['removed']:
                self.logger.info("🔄 포트폴리오 변경 필요:")
                if changes['added']:
                    self.logger.info(f"  ➕ 추가: {', '.join(changes['added'])}")
                if changes['removed']:
                    self.logger.info(f"  ➖ 제거: {', '.join(changes['removed'])}")
                if changes['maintained']:
                    self.logger.info(f"  ✅ 유지: {', '.join(changes['maintained'])}")
            else:
                self.logger.info("✅ 포트폴리오 변경 불필요")
            
            # 9. Top N 상세 로깅
            self.logger.info(f"🏆 현재 Top {len(new_top_positions)} 종목:")
            for i, stock in enumerate(new_top_positions):
                self.logger.info(f"  {i+1}위. {stock.symbol} ({stock.name}) - "
                               f"점수: {stock.total_score:.1f} "
                               f"(신호: {stock.trading_signal_score:.1f}, "
                               f"기술: {stock.technical_score:.1f}, "
                               f"모멘텀: {stock.momentum_score:.1f})")
            
            return {
                'changes_needed': bool(changes['added'] or changes['removed']),
                'changes': changes,
                'new_top_positions': new_top_symbols,
                'old_top_positions': old_top_symbols,
                'rankings': rankings,
                'rebalance_time': datetime.now(),
                'total_evaluated': len(self.evaluated_stocks)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 스마트 리밸런싱 실패: {e}")
            return {'changes_needed': False, 'error': str(e)}
    
    def get_current_top_positions(self) -> List[StockEvaluation]:
        """현재 Top N 종목 반환"""
        return self.current_top_positions.copy()
    
    def get_stock_rank(self, symbol: str) -> Optional[int]:
        """특정 종목의 현재 순위 반환"""
        for i, stock in enumerate(self.current_top_positions):
            if stock.symbol == symbol:
                return i + 1
        return None
    
    async def update_trading_signal_score(self, symbol: str, new_score: float) -> bool:
        """매매 신호 점수 업데이트 (실시간 모니터링용)"""
        try:
            if symbol in self.evaluated_stocks:
                old_evaluation = self.evaluated_stocks[symbol]
                
                # 새 점수로 종합 점수 재계산
                new_total_score = (
                    old_evaluation.recommendation_score * self.evaluation_weights['recommendation'] +
                    old_evaluation.technical_score * self.evaluation_weights['technical'] +
                    old_evaluation.fundamental_score * self.evaluation_weights['fundamental'] +
                    old_evaluation.momentum_score * self.evaluation_weights['momentum'] +
                    (100 - old_evaluation.risk_score) * self.evaluation_weights['risk'] +
                    new_score * self.evaluation_weights['trading_signal']
                )
                
                # 평가 업데이트
                self.evaluated_stocks[symbol].trading_signal_score = new_score
                self.evaluated_stocks[symbol].total_score = new_total_score
                self.evaluated_stocks[symbol].last_updated = datetime.now()
                
                self.logger.debug(f"📊 {symbol} 매매신호 점수 업데이트: {new_score:.1f} → 종합: {new_total_score:.1f}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 점수 업데이트 실패: {e}")
            return False
    
    # ========== DB 연동 메서드들 ==========
    
    async def _restore_from_database(self):
        """DB에서 기존 모니터링 종목 복원 (중복 방지)"""
        try:
            # 이미 복원되었거나 복원 중이면 스킵
            if self._restored or not self.db_manager:
                return
                
            self._restored = True  # 복원 시작 표시
            self.logger.info("🔄 DB에서 모니터링 종목 복원 시작")
            
            with Session(self.db_manager.engine) as session:
                # 활성 상태인 모니터링 종목들 조회
                monitoring_stocks = session.query(MonitoringStock)\
                    .filter(MonitoringStock.status == MonitoringStatus.ACTIVE.value)\
                    .filter(MonitoringStock.monitoring_active == True)\
                    .order_by(MonitoringStock.recommendation_time.desc())\
                    .limit(self.max_positions)\
                    .all()
                
                self.logger.info(f"📦 DB에서 {len(monitoring_stocks)}개 모니터링 종목 발견")
                
                # 복원된 종목들을 current_top_positions에 추가
                restored_stocks = []
                for ms in monitoring_stocks:
                    # StockEvaluation 객체 생성 (기본값 사용)
                    evaluation = StockEvaluation(
                        symbol=ms.symbol,
                        name=ms.name,
                        recommendation_score=70.0,  # 기본값
                        technical_score=70.0,
                        fundamental_score=70.0, 
                        momentum_score=70.0,
                        risk_score=30.0,
                        trading_signal_score=75.0,  # DB 복원 시 기본값
                        total_score=72.0,  # 계산된 기본 종합 점수
                        current_price=float(ms.current_price or 0),
                        change_rate=0.0,
                        volume_ratio=1.0,
                        last_updated=datetime.now(),
                        is_holding=True
                    )
                    
                    self.evaluated_stocks[ms.symbol] = evaluation
                    restored_stocks.append(evaluation)
                
                self.current_top_positions = restored_stocks
                self.logger.info(f"✅ {len(restored_stocks)}개 종목 복원 완료")
                
                # 복원된 종목 로그
                for i, stock in enumerate(restored_stocks):
                    self.logger.info(f"  {i+1}. {stock.symbol}({stock.name}) - 점수: {stock.total_score:.1f}")
                    
        except Exception as e:
            self.logger.error(f"❌ DB 복원 실패: {e}")
    
    async def _sync_to_database(self, changes: Dict, new_top_positions: List[StockEvaluation]):
        """DB에 변경사항 동기화"""
        try:
            if not self.db_manager:
                return
                
            self.logger.info("💾 DB 동기화 시작")
            
            with Session(self.db_manager.engine) as session:
                # 1. 제거된 종목들을 INACTIVE로 변경
                for symbol in changes['removed']:
                    monitoring_stock = session.query(MonitoringStock)\
                        .filter(MonitoringStock.symbol == symbol)\
                        .filter(MonitoringStock.status == MonitoringStatus.ACTIVE.value)\
                        .first()
                    
                    if monitoring_stock:
                        monitoring_stock.status = MonitoringStatus.INACTIVE
                        monitoring_stock.monitoring_active = False
                        monitoring_stock.completed_time = datetime.now()
                        self.logger.info(f"  ➖ DB에서 제거: {symbol}")
                
                # 2. 새로 추가된 종목들을 DB에 INSERT
                for symbol in changes['added']:
                    if symbol in self.evaluated_stocks:
                        evaluation = self.evaluated_stocks[symbol]
                        
                        # 기존에 같은 종목이 있다면 업데이트, 없다면 새로 생성
                        existing = session.query(MonitoringStock)\
                            .filter(MonitoringStock.symbol == symbol)\
                            .filter(MonitoringStock.status == MonitoringStatus.ACTIVE.value)\
                            .first()
                        
                        if existing:
                            # 기존 레코드 업데이트
                            # current_price는 DB에 저장하지 않음 - 실시간 조회만 사용
                            existing.last_check_time = datetime.now()
                        else:
                            # 새 레코드 생성
                            new_monitoring = MonitoringStock(
                                symbol=symbol,
                                name=evaluation.name,
                                monitoring_type=MonitoringType.TRADING,
                                strategy_name="smart_rebalancer",
                                current_price=int(evaluation.current_price),
                                status=MonitoringStatus.ACTIVE.value,
                                monitoring_active=True,
                                recommendation_time=datetime.now(),
                                last_check_time=datetime.now()
                            )
                            session.add(new_monitoring)
                        
                        self.logger.info(f"  ➕ DB에 추가: {symbol}")
                
                # 3. 변경사항 커밋
                session.commit()
                self.logger.info("✅ DB 동기화 완료")
                
        except SQLAlchemyError as e:
            self.logger.error(f"❌ DB 동기화 실패: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()  # 세션 누수 방지
        except Exception as e:
            self.logger.error(f"❌ DB 동기화 오류: {e}")
            if 'session' in locals():
                session.close()  # 세션 누수 방지
    
    async def get_monitoring_stocks_from_db(self) -> List[Dict]:
        """DB에서 현재 모니터링 종목 조회"""
        try:
            if not self.db_manager:
                return []
                
            with Session(self.db_manager.engine) as session:
                monitoring_stocks = session.query(MonitoringStock)\
                    .filter(MonitoringStock.status == MonitoringStatus.ACTIVE.value)\
                    .filter(MonitoringStock.monitoring_active == True)\
                    .order_by(MonitoringStock.recommendation_time.desc())\
                    .all()
                
                result = []
                for ms in monitoring_stocks:
                    result.append({
                        'symbol': ms.symbol,
                        'name': ms.name,
                        'strategy_name': ms.strategy_name,
                        'current_price': ms.current_price,
                        'recommendation_time': ms.recommendation_time,
                        'last_check_time': ms.last_check_time
                    })
                
                return result
                
        except Exception as e:
            self.logger.error(f"❌ DB 조회 실패: {e}")
            return []
    
    async def add_candidate_and_rebalance(self, candidate_data: Dict[str, Any]) -> bool:
        """새로운 후보 종목을 평가하고 리밸런싱 수행"""
        try:
            symbol = candidate_data.get('symbol')
            name = candidate_data.get('name', symbol)
            
            self.logger.info(f"🔍 후보 종목 평가: {symbol}({name})")
            
            # 1. 후보 종목의 점수 계산
            candidate_stock = await self._evaluate_candidate_stock(candidate_data)
            if not candidate_stock:
                self.logger.warning(f"⚠️ 후보 종목 평가 실패: {symbol}")
                return False
            
            # 2. 현재 포지션들을 DB에서 로드 (보유종목 제외)
            current_positions = await self._load_current_positions_from_db()
            total_active_stocks = await self._get_total_active_count()
            
            if total_active_stocks < self.max_positions:
                # 전체 슬롯에 여유가 있으면 바로 추가
                self.logger.info(f"✅ 여유 슬롯 있음 ({total_active_stocks}/{self.max_positions}): {symbol} 바로 추가")
                await self._add_to_database(candidate_data)
                return True
            
            if not current_positions:
                # 리밸런싱 가능한 종목이 없으면 (모두 보유종목)
                self.logger.warning(f"⚠️ 리밸런싱 불가: 모든 종목이 실제 보유종목입니다")
                return False
            
            # 3. 점수 비교: 가장 낮은 점수와 비교 (리밸런싱 가능한 종목 중)
            lowest_score_stock = min(current_positions, key=lambda x: x['total_score'])
            
            if candidate_stock.total_score > lowest_score_stock['total_score']:
                self.logger.info(f"🔄 리밸런싱 실행: {lowest_score_stock['symbol']}({lowest_score_stock['total_score']:.2f}) → {symbol}({candidate_stock.total_score:.2f})")
                
                # 4. 기존 종목 제거 및 새 종목 추가
                success = await self._replace_stock_in_db(lowest_score_stock['symbol'], candidate_data)
                
                if success:
                    self.logger.info(f"✅ 리밸런싱 성공: {symbol} 추가완료")
                    return True
                else:
                    self.logger.error(f"❌ 리밸런싱 실패: DB 업데이트 오류")
                    return False
            else:
                self.logger.info(f"⚠️ 후보 점수 부족: {symbol}({candidate_stock.total_score:.2f}) < 최저({lowest_score_stock['total_score']:.2f})")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 후보 종목 리밸런싱 실패: {e}")
            return False
    
    async def _evaluate_candidate_stock(self, candidate_data: Dict[str, Any]):
        """후보 종목 평가"""
        try:
            symbol = candidate_data.get('symbol')
            name = candidate_data.get('name', symbol)
            
            # 기본 점수 생성 (실제로는 분석 엔진을 통해 계산해야 함)
            recommendation_score = 70.0
            technical_score = 60.0
            fundamental_score = 55.0
            momentum_score = 65.0
            risk_score = 20.0  # 리스크는 낮을수록 좋음 (0-100)
            trading_signal_score = 75.0
            
            # 종합 점수 계산 (기존 로직과 동일)
            total_score = (
                recommendation_score * self.evaluation_weights['recommendation'] +
                technical_score * self.evaluation_weights['technical'] +
                fundamental_score * self.evaluation_weights['fundamental'] +
                momentum_score * self.evaluation_weights['momentum'] +
                (100 - risk_score) * self.evaluation_weights['risk'] +  # 리스크는 역가중치
                trading_signal_score * self.evaluation_weights['trading_signal']
            )
            
            stock_data = StockEvaluation(
                symbol=symbol,
                name=name,
                recommendation_score=recommendation_score,
                technical_score=technical_score,
                fundamental_score=fundamental_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                trading_signal_score=trading_signal_score,
                total_score=total_score,
                current_price=0.0,  # 기본값
                change_rate=0.0,    # 기본값
                volume_ratio=1.0,   # 기본값
                last_updated=datetime.now()
            )
            
            self.logger.debug(f"📊 {symbol} 평가 완료: {stock_data.total_score:.2f}점")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 평가 실패: {e}")
            return None
    
    async def _load_current_positions_from_db(self) -> List[Dict[str, Any]]:
        """DB에서 현재 포지션 로드 - 보유종목 제외"""
        try:
            positions = []
            with Session(self.db_manager.engine) as session:
                monitoring_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE'
                ).all()
                
                for stock in monitoring_stocks:
                    # 보유종목 확인 (실제 매수한 종목인지 체크)
                    is_holding = await self._is_holding_stock(stock.symbol)
                    
                    # 보유종목은 리밸런싱 대상에서 제외
                    if is_holding:
                        self.logger.debug(f"🔒 {stock.symbol}({stock.name}) - 보유종목으로 리밸런싱에서 제외")
                        continue
                    
                    # 모니터링 전용 종목만 리밸런싱 대상에 포함
                    positions.append({
                        'symbol': stock.symbol,
                        'name': stock.name,
                        'total_score': 50.0 + len(stock.symbol) * 2,  # 임시 점수 계산
                        'is_holding': False
                    })
            
            self.logger.info(f"📊 리밸런싱 대상: {len(positions)}개 (보유종목 제외)")
            return positions
            
        except Exception as e:
            self.logger.error(f"❌ DB 포지션 로드 실패: {e}")
            return []
    
    async def _is_holding_stock(self, symbol: str) -> bool:
        """종목 보유 여부 확인"""
        try:
            with Session(self.db_manager.engine) as session:
                stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == 'ACTIVE'
                ).first()
                
                if stock:
                    # holding_stock 전략인 경우 실제 보유종목으로 간주
                    is_holding = stock.strategy_name == 'holding_stock'
                    
                    if is_holding:
                        self.logger.debug(f"🏠 {symbol} - 실제 보유종목 (전략: {stock.strategy_name})")
                    else:
                        self.logger.debug(f"📊 {symbol} - 모니터링 전용 (전략: {stock.strategy_name})")
                    
                    return is_holding
                
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 보유 상태 확인 실패: {e}")
            return False  # 확실하지 않으면 보유종목이 아닌 것으로 처리
    
    async def _get_total_active_count(self) -> int:
        """전체 활성 종목 수 조회 (보유종목 포함)"""
        try:
            with Session(self.db_manager.engine) as session:
                count = session.query(MonitoringStock).filter(
                    MonitoringStock.status == 'ACTIVE'
                ).count()
                return count
        except Exception as e:
            self.logger.error(f"❌ 활성 종목 수 조회 실패: {e}")
            return 0
    
    async def _add_to_database(self, candidate_data: Dict[str, Any]) -> bool:
        """새 종목을 DB에 추가"""
        try:
            with Session(self.db_manager.engine) as session:
                new_stock = MonitoringStock(
                    symbol=candidate_data.get('symbol'),
                    name=candidate_data.get('name'),
                    status='ACTIVE',
                    strategy_name=candidate_data.get('strategy_name', 'rebalanced'),
                    target_price=candidate_data.get('target_price'),
                    stop_loss_price=candidate_data.get('stop_loss_price'),
                    monitoring_type=candidate_data.get('monitoring_type', 'TRADING'),
                    recommendation_time=datetime.now()
                )
                
                session.add(new_stock)
                session.commit()
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ DB 추가 실패: {e}")
            return False
    
    async def _replace_stock_in_db(self, old_symbol: str, new_candidate: Dict[str, Any]) -> bool:
        """DB에서 기존 종목을 새 종목으로 교체"""
        try:
            with Session(self.db_manager.engine) as session:
                # 기존 종목 제거
                old_stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == old_symbol,
                    MonitoringStock.status == 'ACTIVE'
                ).first()
                
                if old_stock:
                    old_stock.status = MonitoringStatus.REMOVED.value
                    old_stock.remove_reason = f"리밸런싱: {new_candidate.get('symbol')}로 교체"
                    old_stock.completed_time = datetime.now()
                
                # PostgreSQL UPSERT 방식으로 안전하게 종목 추가/업데이트
                symbol_to_add = new_candidate.get('symbol')
                self.logger.info(f"🔍 {symbol_to_add} UPSERT 실행 중...")
                
                stmt = insert(MonitoringStock).values(
                    symbol=symbol_to_add,
                    name=new_candidate.get('name'),
                    status=MonitoringStatus.ACTIVE.value,
                    strategy_name=new_candidate.get('strategy_name', 'AI_ANALYSIS'),
                    target_price=new_candidate.get('target_price'),
                    stop_loss_price=new_candidate.get('stop_loss_price'),
                    monitoring_type=new_candidate.get('monitoring_type', MonitoringType.TRADING.value),
                    monitoring_active=True,
                    recommendation_time=datetime.now(),
                    remove_reason=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # ON CONFLICT DO UPDATE
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol'],
                    set_=dict(
                        status=MonitoringStatus.ACTIVE.value,
                        strategy_name=stmt.excluded.strategy_name,
                        target_price=stmt.excluded.target_price,
                        stop_loss_price=stmt.excluded.stop_loss_price,
                        monitoring_type=stmt.excluded.monitoring_type,
                        monitoring_active=True,
                        recommendation_time=stmt.excluded.recommendation_time,
                        remove_reason=None,
                        completed_time=None,
                        updated_at=datetime.now()
                    )
                )
                
                session.execute(upsert_stmt)
                self.logger.info(f"🔄 종목 UPSERT 완료: {symbol_to_add}")
                
                session.commit()
                
                self.logger.info(f"🔄 교체 완료: {old_symbol} → {new_candidate.get('symbol')}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ DB 교체 실패: {e}")
            return False