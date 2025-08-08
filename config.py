#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/config.py

시스템 설정 파일 (최소 수정)
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class APIConfig:
    """API 설정"""
    # 한국투자증권 API
    KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
    KIS_APP_KEY = os.getenv("KIS_APP_KEY", "")
    KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "")
    KIS_VIRTUAL_ACCOUNT = True
    
    # 네이버 뉴스 API
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
    
    # 텔레그램 봇 (Phase 5 Notification System)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_IDS = [id.strip() for id in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if id.strip()]
    
    # Google Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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
    
    DB_ECHO = False  # True로 설정 시 모든 SQL 쿼리가 로그에 출력됩니다.

class TradingConfig:
    """매매 및 전략 설정"""
    # HTS 조건검색식 ID (.env 파일 또는 직접 수정)
    # 사용자는 KIS HTS에서 생성한 자신의 조건검색식 ID를 여기에 입력해야 합니다.
    HTS_CONDITIONAL_SEARCH_IDS = {
        'momentum': os.getenv("HTS_MOMENTUM_ID", "001"),
        'breakout': os.getenv("HTS_BREAKOUT_ID", "002"),
        'eod': os.getenv("HTS_EOD_ID", "003"),
        'supertrend_ema_rsi': os.getenv("HTS_SUPERTREND_ID", "004"), # Supertrend+EMA+RSI 전략
        'vwap': os.getenv("HTS_VWAP_ID", "005"),                   # VWAP 전략
        'scalping_3m': os.getenv("HTS_SCALPING_3M_ID", "006"),    # 3분봉 스캘핑 전략
        'rsi': os.getenv("HTS_RSI_ID", "007"),                     # RSI 전략
    }

    # 기본 설정
    INITIAL_CAPITAL = 10000000  # 초기 자본금 (1천만원)
    MAX_POSITION_SIZE = 0.1     # 최대 포지션 크기 (10%)
    MAX_DAILY_LOSS = 0.03       # 일일 최대 손실률 (3%)
    COMMISSION_RATE = 0.00015   # 수수료율 (0.015%)

    # 리스크 관리
    STOP_LOSS_RATIO = 0.05      # 기본 손절률 (5%)
    TAKE_PROFIT_RATIO = 0.10    # 기본 익절률 (10%)
    MAX_POSITIONS = 5           # 최대 동시 보유 종목수
    
    # 필터링 조건
    MIN_PRICE = 1000           # 최소 주가
    MAX_PRICE = 50000       # 최대 주가
    MIN_VOLUME = 1000     # 최소 거래량
    MIN_MARKET_CAP = 100       # 최소 시가총액 (억원)

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
    LOG_LEVEL = "INFO"
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
    """리스크 관리 설정"""
    MAX_DAILY_LOSS = 500000  # 일일 최대 손실 (50만원)
    MAX_POSITION_LOSS = 200000  # 포지션별 최대 손실 (20만원)
    DEFAULT_STOP_LOSS_PCT = 5.0  # 기본 손절매 비율 (5%)
    DEFAULT_TAKE_PROFIT_PCT = 10.0  # 기본 익절매 비율 (10%)
    MAX_PORTFOLIO_RISK = 0.02  # 최대 포트폴리오 위험도 (2%)

class Config:
    """통합 설정 클래스"""
    api = APIConfig()
    database = DatabaseConfig()
    def __init__(self):
        # 인스턴스 속성으로 설정
        self.api = APIConfig()
        self.database = DatabaseConfig()
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
    
    @classmethod
    def validate(cls):
        """설정 유효성 검사"""
        errors = []
        
        # API 키 확인
        if not APIConfig.KIS_APP_KEY:
            errors.append("KIS_APP_KEY가 설정되지 않았습니다.")
        if not APIConfig.KIS_APP_SECRET:
            errors.append("KIS_APP_SECRET이 설정되지 않았습니다.")
        if not APIConfig.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY가 설정되지 않았습니다.")
            
        # 필수 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        
        if errors:
            raise ValueError("설정 오류:\n" + "\n".join(errors))
        
        return True