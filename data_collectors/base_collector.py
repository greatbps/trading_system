#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/base_collector.py

데이터 수집기 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from utils.logger import get_logger

class BaseCollector(ABC):
    """데이터 수집기 기본 클래스"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(f"Collector_{self.__class__.__name__}")
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def initialize(self):
        """초기화 (추상 메서드)"""
        pass
    
    @abstractmethod
    async def close(self):
        """리소스 정리 (추상 메서드)"""
        pass
    
    @abstractmethod
    async def get_stock_list(self) -> List[Tuple[str, str]]:
        """전체 종목 리스트 조회 (추상 메서드)"""
        pass
    
    @abstractmethod
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """종목 기본 정보 조회 (추상 메서드)"""
        pass
    
    async def health_check(self) -> bool:
        """연결 상태 확인"""
        try:
            # 간단한 API 호출로 연결 상태 확인
            test_result = await self.get_stock_info("005930")  # 삼성전자로 테스트
            return test_result is not None
        except Exception as e:
            self.logger.error(f"❌ 연결 상태 확인 실패: {e}")
            return False
    
    def format_number(self, value: Any, decimal_places: int = 2) -> float:
        """숫자 포맷팅"""
        try:
            if value is None or value == '':
                return 0.0
            return round(float(value), decimal_places)
        except (ValueError, TypeError):
            return 0.0
    
    def format_integer(self, value: Any) -> int:
        """정수 포맷팅"""
        try:
            if value is None or value == '':
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0