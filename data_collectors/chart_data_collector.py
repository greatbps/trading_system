"""
차트 데이터 수집 시스템 (Chart Data Collector)
===========================================

KIS API를 통한 일봉/분봉 데이터 수집 및 관리
실제 기술적 지표 계산을 위한 OHLCV 데이터 제공

주요 기능:
- KIS API 일봉/분봉 데이터 수집
- PostgreSQL 데이터베이스 저장
- 실시간 데이터 업데이트
- 데이터 품질 검증
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
from analyzers.technical_indicators import PriceData
from data_collectors.kis_collector import KISCollector
import json


@dataclass
class ChartDataRequest:
    """차트 데이터 요청 정보"""
    symbol: str
    period: str  # 'D' (일봉), '1' (1분), '5' (5분), '15' (15분), '60' (60분)
    start_date: str  # 'YYYYMMDD'
    end_date: str  # 'YYYYMMDD'
    adjust_price: bool = True  # 수정주가 여부


class ChartDataCollector:
    """
    차트 데이터 수집 및 관리 시스템
    
    KIS API를 통해 일봉/분봉 데이터를 수집하고
    기술적 지표 계산에 필요한 형태로 제공
    """
    
    def __init__(self, kis_collector: KISCollector):
        self.kis_collector = kis_collector
        self.logger = logging.getLogger("ChartDataCollector")
        
        # 데이터 캐시 (메모리 기반)
        self.data_cache = {}
        self.cache_ttl = 300  # 5분 캐시
        
    async def get_daily_chart_data(self, symbol: str, days: int = 200) -> List[PriceData]:
        """
        일봉 차트 데이터 수집
        
        Args:
            symbol: 종목 코드 (예: '005930')
            days: 수집할 일수 (기본 200일)
            
        Returns:
            PriceData 리스트 (과거 -> 현재 순서)
        """
        
        try:
            # 캐시 확인
            cache_key = f"daily_{symbol}_{days}"
            if self._is_cache_valid(cache_key):
                self.logger.debug(f"{symbol}: 캐시된 일봉 데이터 사용")
                return self.data_cache[cache_key]['data']
            
            # 날짜 범위 계산
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days * 1.5)).strftime('%Y%m%d')  # 여유분 포함
            
            # KIS API 호출
            request = ChartDataRequest(
                symbol=symbol,
                period='D',
                start_date=start_date,
                end_date=end_date
            )
            
            raw_data = await self._fetch_chart_data(request)
            
            if not raw_data:
                self.logger.warning(f"{symbol}: 일봉 데이터 수집 실패")
                return []
            
            # PriceData 형태로 변환
            price_data_list = self._convert_to_price_data(raw_data, symbol)
            
            # 최근 N일만 선택
            price_data_list = price_data_list[-days:] if len(price_data_list) > days else price_data_list
            
            # 캐시 저장
            self.data_cache[cache_key] = {
                'data': price_data_list,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"{symbol}: 일봉 데이터 {len(price_data_list)}일 수집 완료")
            return price_data_list
            
        except Exception as e:
            self.logger.error(f"{symbol}: 일봉 데이터 수집 오류 - {e}")
            return []
    
    async def get_minute_chart_data(self, symbol: str, minutes: int = 60, periods: int = 200) -> List[PriceData]:
        """
        분봉 차트 데이터 수집
        
        Args:
            symbol: 종목 코드
            minutes: 분봉 주기 (1, 5, 15, 60)
            periods: 수집할 봉 개수 (기본 200개)
            
        Returns:
            PriceData 리스트 (과거 -> 현재 순서)
        """
        
        try:
            # 캐시 확인
            cache_key = f"minute_{symbol}_{minutes}_{periods}"
            if self._is_cache_valid(cache_key):
                self.logger.debug(f"{symbol}: 캐시된 {minutes}분봉 데이터 사용")
                return self.data_cache[cache_key]['data']
            
            # 날짜 범위 계산 (분봉은 당일만)
            today = datetime.now().strftime('%Y%m%d')
            
            # KIS API 호출
            request = ChartDataRequest(
                symbol=symbol,
                period=str(minutes),
                start_date=today,
                end_date=today
            )
            
            raw_data = await self._fetch_chart_data(request)
            
            if not raw_data:
                self.logger.warning(f"{symbol}: {minutes}분봉 데이터 수집 실패")
                return []
            
            # PriceData 형태로 변환
            price_data_list = self._convert_to_price_data(raw_data, symbol)
            
            # 최근 N개만 선택
            price_data_list = price_data_list[-periods:] if len(price_data_list) > periods else price_data_list
            
            # 캐시 저장 (분봉은 짧은 캐시)
            self.data_cache[cache_key] = {
                'data': price_data_list,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"{symbol}: {minutes}분봉 데이터 {len(price_data_list)}개 수집 완료")
            return price_data_list
            
        except Exception as e:
            self.logger.error(f"{symbol}: {minutes}분봉 데이터 수집 오류 - {e}")
            return []
    
    async def _fetch_chart_data(self, request: ChartDataRequest) -> List[Dict]:
        """
        KIS API를 통한 실제 차트 데이터 수집
        
        Args:
            request: 차트 데이터 요청 정보
            
        Returns:
            원시 차트 데이터 리스트
        """
        
        try:
            # request가 dict인 경우 처리
            if isinstance(request, dict):
                symbol = request.get('symbol')
                period = request.get('period')
                start_date = request.get('start_date')
                end_date = request.get('end_date')
                adjust_price = request.get('adjust_price', True)
            else:
                # ChartDataRequest 객체인 경우
                symbol = request.symbol
                period = request.period
                start_date = request.start_date
                end_date = request.end_date
                adjust_price = request.adjust_price
            
            # 실제 KIS API 차트 데이터 호출
            response = await self.kis_collector.get_chart_data(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust_price=adjust_price
            )
            return response
                
        except Exception as e:
            self.logger.error(f"차트 데이터 수집 API 오류: {e}")
            # 시뮬레이션 데이터나 더미 데이터 반환 금지
            return []
    
    
    def _convert_to_price_data(self, raw_data: List[Dict], symbol: str) -> List[PriceData]:
        """
        원시 차트 데이터를 PriceData 객체로 변환
        
        Args:
            raw_data: KIS API 응답 데이터
            symbol: 종목 코드
            
        Returns:
            PriceData 객체 리스트
        """
        
        price_data_list = []
        
        try:
            for data in raw_data:
                # 날짜/시간 파싱
                date_str = data.get('date', '')
                time_str = data.get('time', '150000')  # 기본값: 15:00:00
                
                if len(date_str) == 8:  # YYYYMMDD
                    if time_str:
                        datetime_str = f"{date_str} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                        timestamp = datetime.strptime(datetime_str, '%Y%m%d %H:%M:%S')
                    else:
                        timestamp = datetime.strptime(date_str, '%Y%m%d')
                else:
                    continue
                
                # 가격 데이터 파싱
                price_data = PriceData(
                    timestamp=timestamp,
                    open=float(data.get('open', 0)),
                    high=float(data.get('high', 0)),
                    low=float(data.get('low', 0)),
                    close=float(data.get('close', 0)),
                    volume=int(data.get('volume', 0))
                )
                
                # 데이터 유효성 검증
                if self._validate_price_data(price_data):
                    price_data_list.append(price_data)
            
            # 시간순 정렬 (과거 -> 현재)
            price_data_list.sort(key=lambda x: x.timestamp)
            
            self.logger.debug(f"{symbol}: {len(price_data_list)}개 PriceData 변환 완료")
            
        except Exception as e:
            self.logger.error(f"PriceData 변환 오류: {e}")
        
        return price_data_list
    
    def _validate_price_data(self, price_data: PriceData) -> bool:
        """가격 데이터 유효성 검증"""
        
        # 기본 검증
        if price_data.close <= 0 or price_data.volume < 0:
            return False
        
        # OHLC 관계 검증
        if not (price_data.low <= price_data.open <= price_data.high and
                price_data.low <= price_data.close <= price_data.high):
            return False
        
        # 이상치 검증 (가격이 너무 극단적이지 않은지)
        price_range = price_data.high - price_data.low
        if price_range > price_data.close * 0.3:  # 30% 이상 변동은 이상치
            return False
        
        return True
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        
        if cache_key not in self.data_cache:
            return False
        
        cache_data = self.data_cache[cache_key]
        cache_age = (datetime.now() - cache_data['timestamp']).total_seconds()
        
        return cache_age < self.cache_ttl
    
    async def update_realtime_data(self, symbol: str) -> Optional[PriceData]:
        """
        실시간 데이터 업데이트
        
        현재가 정보를 받아서 최신 PriceData를 생성
        """
        
        try:
            # 현재가 정보 조회
            stock_info = await self.kis_collector.get_stock_info(symbol)
            
            if not stock_info:
                return None
            
            # 최신 PriceData 생성
            current_data = PriceData(
                timestamp=datetime.now(),
                open=stock_info.current_price,  # 실시간은 현재가로 근사
                high=stock_info.current_price,
                low=stock_info.current_price,
                close=stock_info.current_price,
                volume=stock_info.volume
            )
            
            # 일봉 캐시 업데이트 (최신 데이터 추가)
            daily_cache_keys = [k for k in self.data_cache.keys() if k.startswith(f"daily_{symbol}")]
            
            for cache_key in daily_cache_keys:
                cached_data = self.data_cache[cache_key]['data']
                
                # 오늘 데이터가 이미 있으면 업데이트, 없으면 추가
                today = datetime.now().date()
                updated = False
                
                for i, data in enumerate(cached_data):
                    if data.timestamp.date() == today:
                        # 오늘 데이터 업데이트
                        cached_data[i] = current_data
                        updated = True
                        break
                
                if not updated:
                    # 오늘 데이터 추가
                    cached_data.append(current_data)
                
                # 캐시 타임스탬프 업데이트
                self.data_cache[cache_key]['timestamp'] = datetime.now()
            
            return current_data
            
        except Exception as e:
            self.logger.error(f"{symbol}: 실시간 데이터 업데이트 오류 - {e}")
            return None
    
    def clear_cache(self, symbol: str = None):
        """캐시 삭제"""
        
        if symbol:
            # 특정 종목 캐시 삭제
            keys_to_remove = [k for k in self.data_cache.keys() if symbol in k]
            for key in keys_to_remove:
                del self.data_cache[key]
            self.logger.info(f"{symbol}: 캐시 삭제 완료")
        else:
            # 전체 캐시 삭제
            self.data_cache.clear()
            self.logger.info("전체 캐시 삭제 완료")
    
    def get_cache_status(self) -> Dict[str, any]:
        """캐시 상태 조회"""
        
        status = {
            'total_cache_entries': len(self.data_cache),
            'cache_details': []
        }
        
        for key, cache_data in self.data_cache.items():
            detail = {
                'key': key,
                'data_count': len(cache_data['data']) if isinstance(cache_data['data'], list) else 1,
                'cache_age_seconds': (datetime.now() - cache_data['timestamp']).total_seconds(),
                'is_valid': self._is_cache_valid(key)
            }
            status['cache_details'].append(detail)
        
        return status


# 테스트 함수
async def test_chart_data_collector():
    """차트 데이터 수집기 테스트"""
    
    from data_collectors.kis_collector import KISCollector
    from config import Config
    
    config = Config()
    kis_collector = KISCollector(config)
    chart_collector = ChartDataCollector(kis_collector)
    
    print("=== Chart Data Collector Test ===")
    
    # 삼성전자 일봉 데이터 수집 테스트
    symbol = "005930"
    daily_data = await chart_collector.get_daily_chart_data(symbol, days=30)
    
    if daily_data:
        print(f"✅ {symbol} 일봉 데이터 {len(daily_data)}일 수집 성공")
        print(f"   최초일: {daily_data[0].timestamp.strftime('%Y-%m-%d')}, 종가: {daily_data[0].close:,}")
        print(f"   최신일: {daily_data[-1].timestamp.strftime('%Y-%m-%d')}, 종가: {daily_data[-1].close:,}")
    else:
        print(f"❌ {symbol} 일봉 데이터 수집 실패")
    
    # 캐시 상태 확인
    cache_status = chart_collector.get_cache_status()
    print(f"캐시 상태: {cache_status['total_cache_entries']}개 엔트리")
    
    return daily_data


if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(test_chart_data_collector())