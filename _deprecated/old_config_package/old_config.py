#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/config/config.py

기본 설정 클래스
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import os

@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""
    HOST: str = "localhost"
    PORT: int = 5432
    NAME: str = "trading_system"
    USER: str = "trading_user"
    PASSWORD: str = "trading_password"
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    DB_URL: str = "sqlite:///trading_system.db"  # 기본 SQLite 사용
    DB_ECHO: bool = False

@dataclass
class TradingConfig:
    """매매 설정"""
    TRADING_ENABLED: bool = False
    MAX_POSITION_SIZE: float = 0.1  # 최대 포지션 크기 (10%)
    STOP_LOSS_RATIO: float = 0.05   # 손절 비율 (5%)
    TAKE_PROFIT_RATIO: float = 0.15 # 익절 비율 (15%)
    MAX_DAILY_TRADES: int = 10      # 일일 최대 매매 횟수
    HARD_MAX_POSITION: int = 1000000  # 하드 리미트 최대 포지션 (원)
    HARD_MAX_DAILY_LOSS: int = 500000  # 하드 리미트 일일 손실 (원)

@dataclass
class KISConfig:
    """KIS API 설정"""
    APP_KEY: str = ""
    APP_SECRET: str = ""
    CANO: str = ""
    ACNT_PRDT_CD: str = "01"
    URL_BASE: str = "https://openapi.koreainvestment.com:9443"  # 실제투자

@dataclass
class APIConfig:
    """API 설정 (KIS 등) - 실거래 전용"""
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"  # 실거래 전용
    KIS_APP_KEY: str = ""
    KIS_APP_SECRET: str = ""
    KIS_ACCOUNT_NUMBER: str = ""

@dataclass
class LogConfig:
    """로그 설정"""
    LEVEL: str = "INFO"
    FILE_MAX_SIZE: int = 10  # MB
    BACKUP_COUNT: int = 5
    LOG_DIR: str = "logs"

@dataclass
class LLMConfig:
    """LLM 설정"""
    PROVIDER: str = "openai"  # openai, anthropic, local
    MODEL: str = "gpt-4"
    API_KEY: str = ""
    MAX_TOKENS: int = 4000
    TEMPERATURE: float = 0.1
    ENABLED: bool = False

@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    MAX_DAILY_LOSS: int = 500000  # 일일 최대 손실 (원)
    MAX_POSITION_LOSS: int = 200000  # 포지션당 최대 손실 (원)
    DEFAULT_STOP_LOSS_PCT: float = 5.0  # 기본 손절 비율 (%)
    DEFAULT_TAKE_PROFIT_PCT: float = 10.0  # 기본 익절 비율 (%)
    MAX_PORTFOLIO_RISK: float = 0.02  # 최대 포트폴리오 리스크 (2%)
    HARD_MAX_DAILY_LOSS: int = 100000  # 하드 리미트 일일 손실 (원)

class Config:
    """메인 설정 클래스"""

    def __init__(self):
        # 프로젝트 루트 경로
        self.PROJECT_ROOT = Path(__file__).parent.parent

        # 환경변수에서 설정 로드
        self._load_from_env()

        # 설정 초기화
        self.database = DatabaseConfig()
        self.trading = TradingConfig()
        self.kis = KISConfig()
        self.api = APIConfig()
        self.logging = LogConfig()
        self.llm = LLMConfig()
        self.risk = RiskConfig()

        # 환경변수 값들을 설정 객체에 적용
        self._apply_env_to_configs()

    def _load_from_env(self):
        """환경변수에서 설정 로드"""
        # 환경변수 파일이 있다면 로드
        env_file = self.PROJECT_ROOT / '.env'
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass  # python-dotenv가 없어도 계속 진행

    def _apply_env_to_configs(self):
        """환경변수 값들을 설정 객체에 적용"""
        import os

        # KIS API 설정 적용
        if os.getenv('KIS_APP_KEY'):
            self.api.KIS_APP_KEY = os.getenv('KIS_APP_KEY')
            self.kis.APP_KEY = os.getenv('KIS_APP_KEY')

        if os.getenv('KIS_APP_SECRET'):
            self.api.KIS_APP_SECRET = os.getenv('KIS_APP_SECRET')
            self.kis.APP_SECRET = os.getenv('KIS_APP_SECRET')

        if os.getenv('KIS_ACCOUNT_NUMBER'):
            self.kis.CANO = os.getenv('KIS_ACCOUNT_NUMBER')
            self.api.KIS_ACCOUNT_NUMBER = os.getenv('KIS_ACCOUNT_NUMBER')

        # 실거래 전용 - 가상투자 관련 로직 제거

        # 기타 환경변수 적용
        if os.getenv('LOG_LEVEL'):
            self.logging.LEVEL = os.getenv('LOG_LEVEL')

        if os.getenv('OPENAI_API_KEY'):
            self.llm.API_KEY = os.getenv('OPENAI_API_KEY')
            self.llm.ENABLED = True

    def get_db_url(self) -> str:
        """데이터베이스 연결 URL 반환"""
        return f"postgresql://{self.database.USER}:{self.database.PASSWORD}@{self.database.HOST}:{self.database.PORT}/{self.database.NAME}"

    def validate(self) -> bool:
        """설정 유효성 검사"""
        try:
            # 필수 디렉토리 생성
            log_dir = self.PROJECT_ROOT / self.logging.LOG_DIR
            log_dir.mkdir(exist_ok=True)

            # 기타 검증 로직 추가 가능
            return True

        except Exception as e:
            print(f"설정 검증 실패: {e}")
            return False

    def get(self, key: str, default=None):
        """설정 값 조회 메서드"""
        try:
            # 점 표기법으로 중첩된 설정 접근 지원 (예: "database.HOST")
            keys = key.split('.')
            value = self

            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                else:
                    return default

            return value
        except Exception:
            return default