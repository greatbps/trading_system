#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/config.py

시스템 설정 파일 (최소 수정)
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드 (강제 재로드)
load_dotenv(override=True)

class APIConfig:
    """API 설정"""
    # 한국투자증권 API
    KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
    KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
    KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")
    KIS_ACCOUNT_NUMBER = os.getenv("KIS_ACCOUNT_NUMBER", "")
    KIS_VIRTUAL_ACCOUNT = False
    
    # 네이버 뉴스 API
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
    
    # 텔레그램 봇 (Phase 5 Notification System)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_IDS = [id.strip() for id in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if id.strip()]
    


class KISAccountConfig:
    """KIS 계정 설정"""
    KIS_USER_ID = os.getenv("KIS_USER_ID", "")

class DatabaseConfig:
    """데이터베이스 설정"""
    # 환경변수에서 PostgreSQL 설정을 가져와서 연결 URL 구성
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "trading_system")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    
    # DATABASE_URL이 직접 설정되어 있으면 사용, 없으면 개별 설정으로 구성
    if os.getenv("DATABASE_URL"):
        DB_URL = os.getenv("DATABASE_URL")
    else:
        DB_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # url 속성 추가 (MonitoringScheduler 호환성)
    @property
    def url(self):
        return self.DB_URL
    
    DB_ECHO = False  # True로 설정 시 모든 SQL 쿼리가 로그에 출력됩니다.

class TradingConfig:
    """매매 및 전략 설정 - 실제 계좌 잔고 기반 동적 계산"""
    TRADING_ENABLED = True          # 실거래 활성화 (False로 설정 시 시뮬레이션 모드)

    # 비율 기반 설정 (실제 잔고에서 계산됨)
    MAX_POSITION_SIZE_PCT = 1.2     # 최대 포지션 크기 비율 (120% - 소액 계좌 극한 최적화, 신용 활용)
    MAX_DAILY_LOSS_PCT = 0.05       # 일일 최대 손실률 (5%)
    COMMISSION_RATE = 0.00015       # 수수료율 (0.015%)

    # 하드 리미트 (안전 장치)
    HARD_MAX_POSITION = 100000      # 절대 최대 포지션 (10만원 - 소액 계좌용 여유 설정)
    HARD_MAX_DAILY_LOSS = 50000     # 절대 최대 일일손실 (5만원)

    # 리스크 관리 (단타/스윙 최적화)
    STOP_LOSS_RATIO = 0.03      # 단타용 타이트 손절률 (3%)
    TAKE_PROFIT_RATIO = 0.06    # 단타용 익절률 (6% = 손절 × 2배)
    MAX_POSITIONS = 5           # 최대 동시 보유 종목수

    # 포트폴리오 관리 설정
    PORTFOLIO_AUTO_CLEANUP = True   # 자동 포트폴리오 정리 활성화
    PROTECTED_SYMBOLS = {           # 자동 매도 제외 종목 (주요 대형주)
        '005930',  # 삼성전자
        '035420',  # NAVER
        '000660',  # SK하이닉스
        '373220',  # LG에너지솔루션
        '207940',  # 삼성바이오로직스
    }
    AUTO_SELL_MIN_LOSS_RATE = -10.0  # 자동 매도 최소 손실률 (-10% 이상 손실 시에만 자동 매도)

    # 필터링 조건
    MIN_PRICE = 1000           # 최소 주가
    MAX_PRICE = 50000       # 최대 주가
    MIN_VOLUME = 1000     # 최소 거래량
    MIN_MARKET_CAP = 100       # 최소 시가총액 (억원)

    # 기본 종목 리스트 (API 실패 시 폴백용 - 동적 스크리닝 기반)
    DEFAULT_STOCKS = []  # 빈 리스트로 변경, 동적 스크리닝 사용

    # 전략별 HTS 조건검색식 이름 매핑 (실제 HTS 조건식 이름과 일치)
    HTS_CONDITION_NAMES = {
        'momentum': 'momentum',
        'breakout': 'Breakout',
        'eod': 'EOD',
        'supertrend_ema_rsi': 'SuperTrend',
        'vwap': 'VWAP',
        'scalping_3m': '3분봉 스캘핑 전략',
        'rsi': 'RSI (상대강도지수) 전략',
        'squeeze_momentum_pro': 'Squeeze Momentum Pro',
        'all': 'momentum'  # all 전략은 기본적으로 momentum 사용
    }

    # 전략별 HTS 조건검색식 ID 매핑 (실제 HTS 등록 순서)
    # 실제 HTS API 응답 기준: 0=3분봉, 1=Breakout, 2=EOD, 3=momentum, 4=RSI, 5=Squeeze, 6=SuperTrend, 7=VWAP
    HTS_CONDITIONAL_SEARCH_IDS = {
        'scalping_3m': '0',           # 3분봉 스캘핑 전략
        'breakout': '1',              # Breakout
        'eod': '2',                   # EOD
        'momentum': '3',              # momentum (수정됨: 7->3)
        'rsi': '4',                   # RSI (상대강도지수) 전략 (수정됨: 3->4)
        'squeeze_momentum_pro': '5',  # Squeeze Momentum Pro (수정됨: 4->5)
        'supertrend_ema_rsi': '6',    # SuperTrend (수정됨: 5->6)
        'vwap': '7',                  # VWAP (수정됨: 6->7)
        'all': '3'  # all 전략은 momentum ID 사용 (수정됨: 7->3)
    }

    def __init__(self):
        """인스턴스 생성 시 클래스 속성들을 인스턴스 속성으로 복사"""
        # 기본 설정값들을 인스턴스 속성으로 설정
        self.TRADING_ENABLED = self.__class__.TRADING_ENABLED
        self.MAX_POSITION_SIZE_PCT = self.__class__.MAX_POSITION_SIZE_PCT
        self.MAX_DAILY_LOSS_PCT = self.__class__.MAX_DAILY_LOSS_PCT
        self.COMMISSION_RATE = self.__class__.COMMISSION_RATE
        self.HARD_MAX_POSITION = self.__class__.HARD_MAX_POSITION
        self.HARD_MAX_DAILY_LOSS = self.__class__.HARD_MAX_DAILY_LOSS
        self.STOP_LOSS_RATIO = self.__class__.STOP_LOSS_RATIO
        self.TAKE_PROFIT_RATIO = self.__class__.TAKE_PROFIT_RATIO
        self.MAX_POSITIONS = self.__class__.MAX_POSITIONS
        self.MIN_PRICE = self.__class__.MIN_PRICE
        self.MAX_PRICE = self.__class__.MAX_PRICE
        self.MIN_VOLUME = self.__class__.MIN_VOLUME
        self.MIN_MARKET_CAP = self.__class__.MIN_MARKET_CAP
        self.DEFAULT_STOCKS = self.__class__.DEFAULT_STOCKS.copy()

        # HTS 설정들을 인스턴스 속성으로 복사
        self.HTS_CONDITION_NAMES = self.__class__.HTS_CONDITION_NAMES.copy()
        self.HTS_CONDITIONAL_SEARCH_IDS = self.__class__.HTS_CONDITIONAL_SEARCH_IDS.copy()

class AnalysisConfig:
    """분석 설정"""
    # 각 분석 모듈의 가중치 (총합 1.0)
    WEIGHTS = {
        'technical': 0.30,      # 기술적 분석
        'sentiment': 0.25,      # 뉴스/감성 분석
        'supply_demand': 0.25,  # 수급 분석
        'chart_pattern': 0.20   # 차트 패턴 분석
    }

    # 기술적 분석 파라미터
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    BB_STD = 2
    
    # 뉴스 분석
    NEWS_LOOKBACK_DAYS = 7
    MIN_NEWS_SCORE = 0.3
    
    # 감정 분석
    SENTIMENT_THRESHOLD = 0.6

class SystemConfig:
    """시스템 설정"""
    # 로깅
    LOG_LEVEL = "DEBUG"
    LOG_FILE = "logs/trading_system.log"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    
    # 스케줄링
    MARKET_OPEN_TIME = "09:00"
    MARKET_CLOSE_TIME = "15:30"
    ANALYSIS_TIME = "08:30"
    
    # 데이터 수집
    DATA_UPDATE_INTERVAL = 60  # 초
    MAX_RETRY_COUNT = 3
    REQUEST_TIMEOUT = 30

class RiskConfig:
    """리스크 관리 설정 - 실제 계좌 잔고 기반 동적 계산"""
    # 비율 기반 설정
    MAX_DAILY_LOSS_PCT = 0.05        # 일일 최대 손실률 (5%)
    MAX_POSITION_LOSS_PCT = 0.02     # 포지션별 최대 손실률 (2%)
    DEFAULT_STOP_LOSS_PCT = 5.0      # 기본 손절매 비율 (5%)
    DEFAULT_TAKE_PROFIT_PCT = 10.0   # 기본 익절매 비율 (10%)
    MAX_PORTFOLIO_RISK = 0.05        # 최대 포트폴리오 위험도 (5%)
    
    # 하드 리미트 (안전 장치)
    HARD_MAX_DAILY_LOSS = 100000     # 절대 최대 일일손실 (10만원)
    HARD_MAX_POSITION_LOSS = 50000   # 절대 최대 포지션손실 (5만원)

class Config:
    """통합 설정 클래스"""
    api = APIConfig()
    database = DatabaseConfig()
    def __init__(self):
        # 인스턴스 속성으로 설정 - 현재 모듈의 클래스를 명시적으로 사용
        self.api = APIConfig()
        self.database = DatabaseConfig()

        # 현재 모듈의 TradingConfig 클래스 사용
        self.trading = TradingConfig()

        self.analysis = AnalysisConfig()
        self.system = SystemConfig()
        self.risk = RiskConfig()
        self.kis_account = KISAccountConfig()
        
        
        # 실행 환경
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development, production
        self.DEBUG = self.ENVIRONMENT == "development"
    
    @property
    def DATABASE_URL(self):
        """PostgreSQL 데이터베이스 URL 생성"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "trading_system")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    def get(self, key, default=None):
        """Dictionary-style access to config attributes"""
        return getattr(self, key, default)
    
    @classmethod
    def validate(cls):
        """설정 유효성 검사"""
        errors = []
        
        # API 키 확인
        if not APIConfig.KIS_APP_KEY:
            errors.append("KIS_APP_KEY가 설정되지 않았습니다.")
        if not APIConfig.KIS_APP_SECRET:
            errors.append("KIS_APP_SECRET이 설정되지 않았습니다.")
            
        # 필수 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        if errors:
            raise ValueError("설정 오류:\n" + "\n".join(errors))
        
        return True