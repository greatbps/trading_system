#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/utils/logger.py

로깅 유틸리티 모듈
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """컬러 포맷터"""
    
    # ANSI 색상 코드
    COLORS = {
        'DEBUG': '\033[36m',    # 청록색
        'INFO': '\033[32m',     # 초록색
        'WARNING': '\033[33m',  # 노란색
        'ERROR': '\033[31m',    # 빨간색
        'CRITICAL': '\033[41m', # 빨간 배경
        'RESET': '\033[0m'      # 리셋
    }
    
    def format(self, record):
        # 원본 포맷팅
        formatted = super().format(record)
        
        # 색상 적용
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        return f"{color}{formatted}{reset}"

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """로거 설정"""
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 포맷터 생성
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)-12s | %(levelname)-8s | %(funcName)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (회전)
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"trading_{today}.log"
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # 에러 전용 파일 핸들러
    error_file = log_dir / f"trading_error_{today}.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    return logger

def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """로거 인스턴스 가져오기"""
    return setup_logger(name, level)