"""
모니터링 종목 데이터베이스 모델
=============================

모니터링 종목의 영속성과 감시 조건 관리를 위한 DB 스키마
재시작 후에도 모니터링 상태가 유지되도록 설계

주요 테이블:
- monitoring_stocks: 감시 중인 종목들
- monitoring_history: 점수 변화 이력
- removal_conditions: 감시 제외 조건들
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

Base = declarative_base()


class MonitoringStatus(Enum):
    """모니터링 상태"""
    ACTIVE = "active"           # 활성 감시
    PAUSED = "paused"           # 일시 정지
    COMPLETED = "completed"     # 매매 완료
    REMOVED = "removed"         # 감시 제외


class RemovalReason(Enum):
    """감시 제외 사유"""
    LOW_SCORE = "low_score"                 # 종합 점수 미달
    SELL_SIGNAL = "sell_signal"             # 매도 신호 발생
    TIME_LIMIT = "time_limit"               # 시간 제한 도달
    MANUAL_REMOVE = "manual_remove"         # 수동 제거
    VOLUME_DECLINE = "volume_decline"       # 거래량 급감
    DISTRIBUTION_PATTERN = "distribution"   # 분산 패턴 감지


class MonitoringStock(Base):
    """
    모니터링 종목 마스터 테이블
    
    재시작 후에도 감시 상태를 유지하기 위한 영속성 제공
    """
    __tablename__ = 'monitoring_stocks'
    
    id = Column(Integer, primary_key=True)
    
    # 종목 기본 정보
    symbol = Column(String(10), nullable=False, unique=True)  # 종목 코드
    name = Column(String(100), nullable=True)                 # 종목명
    
    # 모니터링 설정
    status = Column(String(20), nullable=False, default='active')     # 상태
    strategy_name = Column(String(50), nullable=False)               # 전략명
    
    # 매매 설정
    target_price = Column(Integer, nullable=True)        # 목표가
    stop_loss_price = Column(Integer, nullable=True)     # 손절가
    position_size = Column(Integer, nullable=False)      # 포지션 크기
    
    # 감시 조건
    min_score_threshold = Column(Float, default=40.0)    # 최소 점수 임계값
    max_monitoring_days = Column(Integer, default=30)    # 최대 감시 일수
    
    # 시간 정보
    added_at = Column(DateTime, default=datetime.now)    # 추가 시간
    last_check_at = Column(DateTime, nullable=True)      # 마지막 체크 시간
    last_score = Column(Float, nullable=True)            # 마지막 점수
    
    # 상태 정보  
    check_count = Column(Integer, default=0)             # 체크 횟수
    
    # 제거 관련
    removed_at = Column(DateTime, nullable=True)         # 제거 시간
    removal_reason = Column(String(50), nullable=True)   # 제거 사유
    removal_details = Column(Text, nullable=True)        # 제거 상세 정보
    
    # 관계 설정
    score_history = relationship("MonitoringScoreHistory", back_populates="stock")
    
    def __repr__(self):
        return f"<MonitoringStock(symbol='{self.symbol}', status='{self.status}', score={self.last_score})>"
    
    def is_active(self) -> bool:
        """활성 상태인지 확인"""
        return self.status == 'active'
    
    def should_remove(self) -> tuple[bool, str]:
        """감시 제외 여부 판단"""
        
        # 1. 점수 기준
        if self.last_score is not None and self.last_score < self.min_score_threshold:
            return True, f"점수 {self.last_score:.1f} < 임계값 {self.min_score_threshold}"
        
        # 2. 시간 제한
        if self.max_monitoring_days > 0:
            days_monitored = (datetime.now() - self.added_at).days
            if days_monitored > self.max_monitoring_days:
                return True, f"모니터링 기간 {days_monitored}일 > 한계 {self.max_monitoring_days}일"
        
        # 3. 장기간 미체크 (24시간)
        if self.last_check_at and (datetime.now() - self.last_check_at).hours > 24:
            return True, "24시간 이상 미체크"
        
        return False, "감시 조건 유지"


class MonitoringScoreHistory(Base):
    """
    모니터링 점수 이력 테이블
    
    1시간마다 계산되는 종합 점수를 기록하여
    점수 변화 추이를 추적하고 제거 판단에 활용
    """
    __tablename__ = 'monitoring_score_history'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('monitoring_stocks.id'), nullable=False)
    
    # 점수 정보
    total_score = Column(Float, nullable=False)           # 종합 점수
    technical_score = Column(Float, nullable=False)       # 기술적 지표 점수
    volume_score = Column(Float, nullable=False)          # 거래량 점수
    trend_score = Column(Float, nullable=False)           # 추세 점수
    momentum_score = Column(Float, nullable=False)        # 모멘텀 점수
    
    # 상태 정보
    keep_monitoring = Column(Boolean, nullable=False)     # 계속 감시 여부
    reason = Column(Text, nullable=True)                  # 판단 근거
    
    # 시장 데이터
    current_price = Column(Integer, nullable=True)        # 당시 현재가
    current_volume = Column(Integer, nullable=True)       # 당시 거래량
    
    # 시간 정보
    calculated_at = Column(DateTime, default=datetime.now)
    
    # 관계 설정
    stock = relationship("MonitoringStock", back_populates="score_history")
    
    def __repr__(self):
        return f"<MonitoringScoreHistory(stock_id={self.stock_id}, score={self.total_score}, keep={self.keep_monitoring})>"


class RemovalCondition(Base):
    """
    감시 제외 조건 설정 테이블
    
    다양한 제거 조건들을 설정하고 관리
    """
    __tablename__ = 'removal_conditions'
    
    id = Column(Integer, primary_key=True)
    
    # 조건 정보
    condition_name = Column(String(100), nullable=False)  # 조건명
    condition_type = Column(String(50), nullable=False)   # 조건 유형
    
    # 임계값
    score_threshold = Column(Float, nullable=True)        # 점수 임계값
    time_threshold_hours = Column(Integer, nullable=True) # 시간 임계값 (시간)
    volume_ratio_threshold = Column(Float, nullable=True) # 거래량 비율 임계값
    
    # 설정
    is_active = Column(Boolean, default=True)             # 활성화 여부
    priority = Column(Integer, default=1)                 # 우선순위 (낮을수록 높음)
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<RemovalCondition(name='{self.condition_name}', type='{self.condition_type}')>"


# 기본 제거 조건들
DEFAULT_REMOVAL_CONDITIONS = [
    {
        'condition_name': '종합점수 미달',
        'condition_type': 'score_based',
        'score_threshold': 40.0,
        'priority': 1
    },
    {
        'condition_name': '매도신호 발생',
        'condition_type': 'signal_based',
        'priority': 2
    },
    {
        'condition_name': '거래량 급감',
        'condition_type': 'volume_based',
        'volume_ratio_threshold': 0.3,  # 20일 평균 대비 30% 미만
        'priority': 3
    },
    {
        'condition_name': '장기간 미체크',
        'condition_type': 'time_based',
        'time_threshold_hours': 24,
        'priority': 4
    },
    {
        'condition_name': '최대 감시 기간 초과',
        'condition_type': 'time_based',
        'time_threshold_hours': 30 * 24,  # 30일
        'priority': 5
    }
]


def create_monitoring_tables(engine):
    """모니터링 관련 테이블 생성"""
    
    # 테이블 생성
    Base.metadata.create_all(engine)
    
    # 기본 제거 조건 삽입
    from sqlalchemy.orm import sessionmaker
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 기존 조건이 있는지 확인
        existing_count = session.query(RemovalCondition).count()
        
        if existing_count == 0:
            # 기본 조건들 삽입
            for condition_data in DEFAULT_REMOVAL_CONDITIONS:
                condition = RemovalCondition(**condition_data)
                session.add(condition)
            
            session.commit()
            print(f"[PASS] {len(DEFAULT_REMOVAL_CONDITIONS)} default removal conditions created")
        else:
            print(f"[PASS] {existing_count} existing removal conditions found")
            
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Failed to create removal conditions: {e}")
        raise
    finally:
        session.close()


def get_monitoring_stats(session) -> dict:
    """모니터링 통계 조회"""
    
    try:
        stats = {
            'total_stocks': session.query(MonitoringStock).count(),
            'active_stocks': session.query(MonitoringStock).filter(
                MonitoringStock.status == 'active'
            ).count(),
            'removed_stocks': session.query(MonitoringStock).filter(
                MonitoringStock.status == 'removed'
            ).count(),
            'avg_score': session.query(MonitoringStock).filter(
                MonitoringStock.last_score.isnot(None)
            ).with_entities(
                MonitoringStock.last_score
            ).all()
        }
        
        # 평균 점수 계산
        scores = [score[0] for score in stats['avg_score'] if score[0] is not None]
        stats['avg_score'] = sum(scores) / len(scores) if scores else 0
        
        return stats
        
    except Exception as e:
        print(f"[ERROR] Failed to get monitoring stats: {e}")
        return {
            'total_stocks': 0,
            'active_stocks': 0,
            'removed_stocks': 0,
            'avg_score': 0
        }


# 테스트 함수
def test_monitoring_database():
    """모니터링 DB 테스트"""
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    print("=== Monitoring Database Test ===")
    
    # 테스트 DB (SQLite 메모리)
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    try:
        # 테이블 생성
        create_monitoring_tables(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 테스트 모니터링 종목 추가
        test_stock = MonitoringStock(
            symbol='005930',
            name='삼성전자',
            strategy_name='Buy 추천',
            position_size=1000000,
            min_score_threshold=45.0
        )
        
        session.add(test_stock)
        session.commit()
        
        # 점수 이력 추가
        score_history = MonitoringScoreHistory(
            stock_id=test_stock.id,
            total_score=75.5,
            technical_score=70.0,
            volume_score=85.0,
            trend_score=80.0,
            momentum_score=65.0,
            keep_monitoring=True,
            reason="종합점수 양호, 거래량 급증 확인",
            current_price=75000,
            current_volume=15000000
        )
        
        session.add(score_history)
        session.commit()
        
        # 통계 확인
        stats = get_monitoring_stats(session)
        
        print(f"[PASS] Database tables created successfully")
        print(f"[PASS] Test stock added: {test_stock.symbol}")
        print(f"[PASS] Score history recorded: {score_history.total_score}")
        print(f"[PASS] Stats: {stats['active_stocks']} active, avg score {stats['avg_score']:.1f}")
        print("[SUCCESS] Monitoring database system is working!")
        
        session.close()
        
    except Exception as e:
        print(f"[ERROR] Database test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_monitoring_database()