#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/data_collectors/kis_collector.py

한국투자증권 KIS API 데이터 수집기 - 완전한 최종 버전
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from utils.logger import get_logger

@dataclass
class StockData:
    """주식 데이터"""
    symbol: str
    name: str
    current_price: float
    change_rate: float
    volume: int
    trading_value: float
    market_cap: float
    shares_outstanding: int
    high_52w: float
    low_52w: float
    pe_ratio: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[float] = None
    bps: Optional[float] = None
    sector: Optional[str] = None

class KISTokenManager:
    """KIS API 토큰 관리자"""
    
    def __init__(self, app_key: str, app_secret: str, base_url: str, logger):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.logger = logger
        self.access_token: Optional[str] = None
        self.token_expired: Optional[datetime] = None
        self.token_file = Path("data/kis_token.json")
        self.token_file.parent.mkdir(exist_ok=True)
    
    def _load_token_from_file(self) -> Optional[Dict]:
        """파일에서 토큰 로드"""
        try:
            if not self.token_file.exists():
                return None
            
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            required_fields = ['access_token', 'expired_at', 'app_key', 'app_secret']
            if not all(field in token_data for field in required_fields):
                return None
            
            if (token_data['app_key'] != self.app_key or 
                token_data['app_secret'] != self.app_secret):
                return None
            
            return token_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ 토큰 파일 로드 실패: {e}")
            return None
    
    def _save_token_to_file(self):
        """토큰을 파일에 저장"""
        try:
            if not self.access_token or not self.token_expired:
                return False
            
            token_data = {
                'access_token': self.access_token,
                'expired_at': self.token_expired.isoformat(),
                'app_key': self.app_key,
                'app_secret': self.app_secret,
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("💾 토큰 캐시 저장 완료")
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ 토큰 저장 실패: {e}")
            return False
    
    async def load_cached_token(self) -> bool:
        """캐시된 토큰 로드"""
        try:
            token_data = self._load_token_from_file()
            if not token_data:
                return False
            
            expired_at = datetime.fromisoformat(token_data['expired_at'])
            
            if datetime.now() >= expired_at - timedelta(hours=1):
                self.logger.info("🔄 저장된 토큰이 곧 만료됨")
                return False
            
            self.access_token = token_data['access_token']
            self.token_expired = expired_at
            
            self.logger.info("✅ 캐시된 토큰 사용")
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ 토큰 로드 실패: {e}")
            return False
    
    async def request_new_token(self, session: aiohttp.ClientSession) -> bool:
        """새 토큰 발급"""
        try:
            self.logger.info("🔑 새 토큰 발급 중...")
            
            url = f"{self.base_url}/oauth2/tokenP"
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.access_token = result.get('access_token')
                    self.token_expired = datetime.now() + timedelta(hours=23, minutes=50)
                    
                    self._save_token_to_file()
                    self.logger.info("✅ 새 토큰 발급 성공")
                    return True
                else:
                    response_text = await response.text()
                    self.logger.error(f"❌ 토큰 발급 실패: {response.status}, {response_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ 토큰 발급 실패: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """토큰 유효성 검사"""
        if not self.access_token or not self.token_expired:
            return False
        return datetime.now() < self.token_expired - timedelta(hours=1)
    
    def get_headers(self) -> Dict[str, str]:
        """API 헤더 반환"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret
        }

class SmartKISCollector:
    """Smart KIS Collector - 완전한 최종 버전"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("SmartKISCollector")
        self.base_url = config.api.KIS_BASE_URL
        self.app_key = config.api.KIS_APP_KEY
        self.app_secret = config.api.KIS_APP_SECRET
        self.is_virtual = config.api.KIS_VIRTUAL_ACCOUNT
        
        self.token_manager = KISTokenManager(
            self.app_key, self.app_secret, self.base_url, self.logger
        )
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS API 키가 설정되지 않았습니다.")
        
        self.logger.info("✅ SmartKISCollector 초기화 완료")
    
    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.close()
        self.session = None
    
    async def initialize(self):
        """초기화"""
        self.logger.info("🚀 KIS API 초기화 시작...")
        
        # HTTP 세션 생성
        connector = aiohttp.TCPConnector(
            limit=10, limit_per_host=5, ttl_dns_cache=300,
            use_dns_cache=True, enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector, timeout=timeout,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Trading-System/1.0'}
        )
        
        # 토큰 관리
        if await self.token_manager.load_cached_token():
            self._update_session_headers()
        else:
            success = await self.token_manager.request_new_token(self.session)
            if not success:
                raise ConnectionError("KIS API 토큰 발급 실패")
            self._update_session_headers()
        
        # 연결 테스트
        await self._test_connection()
        self.logger.info("✅ KIS API 초기화 완료")
        return True
    
    async def _test_connection(self):
        """연결 테스트"""
        try:
            test_result = await self.get_stock_info("005930")
            if test_result:
                self.logger.info("✅ 연결 테스트 성공")
            else:
                self.logger.warning("⚠️ 연결 테스트 실패")
        except Exception as e:
            self.logger.warning(f"⚠️ 연결 테스트 오류: {e}")
    
    def _update_session_headers(self):
        """세션 헤더 업데이트"""
        if self.session and self.token_manager.access_token:
            headers = self.token_manager.get_headers()
            self.session.headers.update(headers)
    
    async def _ensure_session(self) -> bool:
        """세션 및 토큰 상태 확인"""
        try:
            # 세션 상태 확인
            if not self.session or self.session.closed:
                self.logger.info("🔄 세션 재초기화 중...")
                await self.initialize()
                return True
            
            # 토큰 유효성 검사
            if not self.token_manager.is_token_valid():
                self.logger.info("🔄 토큰 갱신 중...")
                success = await self.token_manager.request_new_token(self.session)
                if success:
                    self._update_session_headers()
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 세션 확인 실패: {e}")
            return False
    
    async def close(self):
        """리소스 정리"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                await asyncio.sleep(0.25)
            self.session = None
        except Exception as e:
            self.logger.warning(f"⚠️ 리소스 정리 오류: {e}")
    
    def _get_safe_config_values(self):
        """Config 값 안전하게 가져오기"""
        try:
            # config에서 값 가져와서 변수에 저장
            min_price = self.config.trading.MIN_PRICE
            max_price = self.config.trading.MAX_PRICE
            min_volume = self.config.trading.MIN_VOLUME
            min_market_cap = self.config.trading.MIN_MARKET_CAP
            
            # 변수로 return
            return {
                'min_price': min_price,
                'max_price': max_price,
                'min_volume': min_volume,
                'min_market_cap': min_market_cap
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ Config 접근 실패: {e}")
            # 예외 시에만 기본값 변수로 설정
            fallback_min_price = 1000
            fallback_max_price = 50000
            fallback_min_volume = 1000
            fallback_min_market_cap = 100
            
            return {
                'min_price': fallback_min_price,
                'max_price': fallback_max_price,
                'min_volume': fallback_min_volume,
                'min_market_cap': fallback_min_market_cap
            }
    
    async def get_stock_list(self) -> List[Tuple[str, str]]:
        """전체 종목 리스트 조회"""
        try:
            self.logger.info("📋 종목 리스트 조회 중...")
            return await self._get_stock_list_pykrx()
        except ImportError:
            self.logger.error("❌ pykrx 라이브러리 필요: pip install pykrx")
            raise
        except Exception as e:
            self.logger.error(f"❌ 종목 리스트 조회 실패: {e}")
            raise
    
    async def _get_stock_list_pykrx(self) -> List[Tuple[str, str]]:
        """pykrx를 사용한 종목 리스트 조회"""
        try:
            from pykrx import stock
            
            today = datetime.now().strftime("%Y%m%d")
            weekday = datetime.now().weekday()
            if weekday >= 5:  # 주말이면 금요일로
                today = (datetime.now() - timedelta(days=weekday - 4)).strftime("%Y%m%d")
            
            self.logger.info(f"📅 조회 기준일: {today}")
            all_stocks = []
            
            # KOSPI 종목
            try:
                kospi_tickers = stock.get_market_ticker_list(today, market="KOSPI")
                for ticker in kospi_tickers:
                    try:
                        name = stock.get_market_ticker_name(ticker)
                        if name and len(ticker) == 6 and not self._is_excluded_stock_name(name):
                            clean_name = self._clean_stock_name(name)
                            all_stocks.append((ticker, clean_name))
                    except:
                        continue
                self.logger.info(f"✅ KOSPI {len([s for s in all_stocks if s[0].startswith(('0', '1', '2'))])}개")
            except Exception as e:
                self.logger.warning(f"⚠️ KOSPI 조회 실패: {e}")
            
            # KOSDAQ 종목
            try:
                kosdaq_tickers = stock.get_market_ticker_list(today, market="KOSDAQ")
                kosdaq_count = 0
                for ticker in kosdaq_tickers:
                    try:
                        name = stock.get_market_ticker_name(ticker)
                        if name and len(ticker) == 6 and not self._is_excluded_stock_name(name):
                            clean_name = self._clean_stock_name(name)
                            all_stocks.append((ticker, clean_name))
                            kosdaq_count += 1
                    except:
                        continue
                self.logger.info(f"✅ KOSDAQ {kosdaq_count}개")
            except Exception as e:
                self.logger.warning(f"⚠️ KOSDAQ 조회 실패: {e}")
            
            if not all_stocks:
                raise Exception("종목 조회 실패")
            
            self.logger.info(f"✅ 총 {len(all_stocks)}개 종목 조회 완료")
            return all_stocks
            
        except ImportError:
            raise ImportError("pykrx 라이브러리가 필요합니다")
        except Exception as e:
            raise e
    
    def _clean_stock_name(self, name: str) -> str:
        """종목명 정제"""
        if not name:
            return ""
        
        suffixes = ["우", "우B", "우C", "1우", "2우", "3우", "스팩", "SPAC", "리츠", "REIT", "ETF", "ETN"]
        clean_name = name.strip()
        
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()
        
        return clean_name
    
    def _is_excluded_stock_name(self, name: str) -> bool:
        """제외할 종목명 검사"""
        if not name:
            return True
        
        exclude_keywords = [
            "ETF", "ETN", "KODEX", "TIGER", "ARIRANG", "KINDEX",
            "스팩", "SPAC", "리츠", "REIT", "투자주의", 
            "상장폐지", "관리종목", "정리매매"
        ]
        
        name_upper = name.upper()
        return any(keyword.upper() in name_upper for keyword in exclude_keywords)
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """종목 상세 정보 조회"""
        try:
            if not await self._ensure_session():
                return None
            
            if not symbol or len(symbol) != 6:
                return None
            
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol}
            headers = {"tr_id": "FHKST01010100", "custtype": "P"}
            headers.update(self.session.headers)
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    if await self._ensure_session():
                        return await self.get_stock_info(symbol)
                    return None
                elif response.status != 200:
                    return None
                
                data = await response.json()
                output = data.get('output', {})
                
                if not output:
                    return None
                
                # 현재가 파싱
                current_price = self._safe_float_parse(output.get('stck_prpr', '0'))
                if current_price <= 0:
                    return None
                
                # 종목명 파싱 (다중 fallback)
                name = None
                name_candidates = [
                    output.get('hts_kor_isnm', '').strip(),
                    output.get('prdy_vrss_sign', '').strip(),
                    output.get('hts_kor_isnm_1', '').strip()
                ]
                
                for candidate in name_candidates:
                    if candidate and not candidate.startswith('종목'):
                        name = self._clean_stock_name(candidate)
                        break
                
                # pykrx fallback
                if not name or name.startswith('종목'):
                    try:
                        from pykrx import stock as pykrx_stock
                        pykrx_name = pykrx_stock.get_market_ticker_name(symbol)
                        if pykrx_name and pykrx_name.strip():
                            name = self._clean_stock_name(pykrx_name.strip())
                    except:
                        pass
                
                if not name or name.startswith('종목'):
                    name = f'종목{symbol}'
                
                # 기타 데이터
                volume = self._safe_int_parse(output.get('acml_vol', '0'))
                trading_value = self._safe_float_parse(output.get('acml_tr_pbmn', '0')) / 1000000
                market_cap = self._safe_float_parse(output.get('hts_avls', '0')) / 100
                change_rate = self._safe_float_parse(output.get('prdy_ctrt', '0'))
                
                high_52w = self._safe_float_parse(output.get('w52_hgpr', '0'))
                low_52w = self._safe_float_parse(output.get('w52_lwpr', '0'))
                
                if high_52w <= 0:
                    high_52w = current_price * 1.5
                if low_52w <= 0:
                    low_52w = current_price * 0.7
                
                pe_ratio = self._safe_float_parse(output.get('per', '0'))
                pbr = self._safe_float_parse(output.get('pbr', '0'))
                
                if pe_ratio <= 0:
                    pe_ratio = None
                if pbr <= 0:
                    pbr = None
                
                market_div = output.get('mrkt_div_cd', '')
                market = "KOSPI" if market_div == "J" else "KOSDAQ"
                
                result = {
                    'symbol': symbol, 'name': name, 'current_price': current_price,
                    'change_rate': change_rate, 'volume': volume, 'trading_value': trading_value,
                    'market_cap': market_cap, 'high_52w': high_52w, 'low_52w': low_52w,
                    'pe_ratio': pe_ratio, 'pbr': pbr, 'market': market, 'sector': '기타'
                }
                
                self.logger.debug(f"✅ {symbol} ({name}) 조회 완료")
                return result
                
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 종목 정보 조회 오류: {e}")
            return None
    
    def _safe_int_parse(self, value, default: int = 0) -> int:
        """안전한 정수 파싱"""
        try:
            if isinstance(value, int):
                return value
            elif isinstance(value, float):
                import math
                return default if math.isnan(value) or math.isinf(value) else int(value)
            
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']:
                return default
            
            return int(float(value_str)) if '.' in value_str else int(value_str)
        except:
            return default
    
    def _safe_float_parse(self, value, default: float = 0.0) -> float:
        """안전한 실수 파싱"""
        try:
            if isinstance(value, (int, float)):
                import math
                return default if math.isnan(value) or math.isinf(value) else float(value)
            
            value_str = str(value).strip().replace(',', '')
            if not value_str or value_str.lower() in ['nan', 'none', 'null', '', 'nat', 'inf', '-inf']:
                return default
            
            float_val = float(value_str)
            import math
            return default if math.isnan(float_val) or math.isinf(float_val) else float_val
        except:
            return default
    
    def _meets_filter_criteria(self, stock_info: Dict) -> bool:
        """종목 필터링 조건 확인"""
        try:
            if not stock_info:
                return False
            
            config_values = self._get_safe_config_values()
            current_price = self._safe_float_parse(stock_info.get('current_price'), 0.0)
            volume = self._safe_float_parse(stock_info.get('volume'), 0.0)
            market_cap = self._safe_float_parse(stock_info.get('market_cap'), 0.0)
            trading_value = self._safe_float_parse(stock_info.get('trading_value'), 0.0)
            name = str(stock_info.get('name', '')).strip()
            
            if current_price <= 0 or not name:
                return False
            
            # 제외 종목 체크
            exclude_words = ['관리', '정리매매', '투자주의', '투자경고', '스팩', 'SPAC', '우선주']
            if any(word in name for word in exclude_words):
                return False
            
            # 필터링 조건
            return (config_values['min_price'] <= current_price <= config_values['max_price'] and
                    volume >= config_values['min_volume'] and
                    market_cap >= config_values['min_market_cap'] and
                    trading_value >= 50)
        except:
            return False
    
    async def get_filtered_stocks(self, limit: int = 50, use_cache: bool = True) -> List[Tuple[str, str]]:
        """필터링된 종목 리스트 반환"""
        try:
            if not isinstance(limit, int) or limit <= 0:
                limit = 50
            
            self.logger.info(f"🔍 필터링된 종목 조회 시작 (목표: {limit}개)")
            
            # 캐시 확인
            if use_cache:
                cached_result = await self._get_cached_filtered_stocks(limit)
                if cached_result:
                    self.logger.info(f"✅ 캐시 사용: {len(cached_result)}개")
                    return cached_result
            
            # 새로 필터링
            try:
                filtered_data = await self.collect_filtered_stocks(max_stocks=limit)
                if filtered_data:
                    result = [(stock['symbol'], stock['name']) for stock in filtered_data]
                    await self._save_filtered_stocks_cache(result)
                    return result
            except Exception as e:
                self.logger.warning(f"⚠️ collect_filtered_stocks 실패: {e}")
            
            # 직접 필터링
            result = await self._direct_filtering(limit)
            if result:
                await self._save_filtered_stocks_cache(result)
                return result
            
            # Fallback
            return await self._get_major_stocks_as_fallback(limit)
            
        except Exception as e:
            self.logger.error(f"❌ get_filtered_stocks 실패: {e}")
            return []
    
    async def _get_cached_filtered_stocks(self, limit: int) -> List[Tuple[str, str]]:
        """캐시된 필터링 결과 조회"""
        try:
            cache_file = Path("data/simple_filtered_cache.json")
            if not cache_file.exists():
                return []
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cached_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_time > timedelta(hours=1):
                return []
            
            return cache_data.get('stocks', [])[:limit]
        except:
            return []
    
    async def _save_filtered_stocks_cache(self, stocks: List[Tuple[str, str]]):
        """필터링 결과 캐시 저장"""
        try:
            cache_file = Path("data/simple_filtered_cache.json")
            cache_file.parent.mkdir(exist_ok=True)
            
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'stocks': stocks
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    async def _direct_filtering(self, limit: int) -> List[Tuple[str, str]]:
        """직접 필터링"""
        try:
            all_stocks = await self.get_stock_list()
            if not all_stocks:
                return []
            
            import random
            sample_size = min(300, len(all_stocks))
            sample_stocks = random.sample(all_stocks, sample_size)
            
            filtered_stocks = []
            for symbol, name in sample_stocks:
                if len(filtered_stocks) >= limit:
                    break
                
                try:
                    stock_info = await self.get_stock_info(symbol)
                    if stock_info and self._meets_filter_criteria(stock_info):
                        filtered_stocks.append((symbol, stock_info['name']))
                    await asyncio.sleep(0.05)
                except:
                    continue
            
            return filtered_stocks
        except:
            return []
    
    async def _get_major_stocks_as_fallback(self, limit: int) -> List[Tuple[str, str]]:
        """Fallback 종목 반환"""
        try:
            all_stocks = await self.get_stock_list()
            if all_stocks:
                import random
                sample_size = min(limit, len(all_stocks))
                return random.sample(all_stocks, sample_size)
            return []
        except:
            return []
    
    async def collect_filtered_stocks(self, max_stocks: int = 100) -> List[Dict]:
        """필터링된 종목 데이터 수집"""
        try:
            if not isinstance(max_stocks, int) or max_stocks <= 0:
                max_stocks = 100
            
            self.logger.info(f"🎯 필터링된 종목 수집 시작 (최대 {max_stocks}개)")
            
            stock_list = await self.get_stock_list()
            self.logger.info(f"📊 전체 종목 수: {len(stock_list)}개")
            
            filtered_stocks = []
            processed_count = 0
            
            semaphore = asyncio.Semaphore(5)
            
            async def process_stock(symbol_name_tuple):
                nonlocal processed_count
                
                async with semaphore:
                    try:
                        symbol, name = symbol_name_tuple
                        processed_count += 1
                        
                        if processed_count % 100 == 0:
                            self.logger.info(f"📈 진행률: {processed_count}/{len(stock_list)}")
                        
                        stock_info = await self.get_stock_info(symbol)
                        if stock_info and self._meets_filter_criteria(stock_info):
                            filtered_stocks.append(stock_info)
                            if len(filtered_stocks) >= max_stocks:
                                return True
                        
                        await asyncio.sleep(0.1)
                        return False
                    except:
                        return False
            
            # 배치 처리
            batch_size = 50
            for i in range(0, len(stock_list), batch_size):
                if len(filtered_stocks) >= max_stocks:
                    break
                
                batch = stock_list[i:i + batch_size]
                tasks = [process_stock(stock) for stock in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                if any(result is True for result in results if not isinstance(result, Exception)):
                    break
            
            filtered_stocks.sort(key=lambda x: x['current_price'], reverse=True)
            
            self.logger.info(f"✅ 종목 수집 완료: {len(filtered_stocks)}개")
            return filtered_stocks
            
        except Exception as e:
            self.logger.error(f"❌ 종목 수집 실패: {e}")
            return []
    
    async def get_historical_data(self, symbol: str, period: str = "1M") -> Optional[List[Dict]]:
        """종목 차트 데이터 조회"""
        try:
            if not await self._ensure_session():
                return None
            
            period_codes = {"1D": "D", "1W": "W", "1M": "M", "1Y": "Y"}
            period_code = period_codes.get(period, "D")
            
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
                "FID_PERIOD_DIV_CODE": period_code,
                "FID_ORG_ADJ_PRC": "0000000001"
            }
            
            headers = {"tr_id": "FHKST03010100", "custtype": "P"}
            headers.update(self.session.headers)
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_chart_data(data, symbol)
                elif response.status == 401:
                    if await self._ensure_session():
                        return await self.get_historical_data(symbol, period)
                    return None
                else:
                    return None
                    
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} 차트 데이터 조회 오류: {e}")
            return None
    
    def _parse_chart_data(self, data: Dict, symbol: str) -> Optional[List[Dict]]:
        """차트 데이터 파싱"""
        try:
            if data.get('rt_cd') != '0':
                return None
            
            output2 = data.get('output2', [])
            if not output2:
                return None
            
            chart_data = []
            for item in output2:
                try:
                    date_str = item.get('stck_bsop_date', '')
                    if not date_str or len(date_str) != 8:
                        continue
                    
                    date = datetime.strptime(date_str, "%Y%m%d").date()
                    
                    open_price = self._safe_float_parse(item.get('stck_oprc', '0'))
                    high_price = self._safe_float_parse(item.get('stck_hgpr', '0'))
                    low_price = self._safe_float_parse(item.get('stck_lwpr', '0'))
                    close_price = self._safe_float_parse(item.get('stck_clpr', '0'))
                    volume = self._safe_int_parse(item.get('acml_vol', '0'))
                    
                    if close_price <= 0:
                        continue
                    
                    chart_data.append({
                        'date': date.isoformat(),
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    })
                except:
                    continue
            
            chart_data.sort(key=lambda x: x['date'])
            self.logger.debug(f"✅ {symbol} 차트 데이터 {len(chart_data)}개")
            return chart_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol} 차트 데이터 파싱 오류: {e}")
            return None
    
    async def search_stocks(self, keyword: str) -> List[Dict]:
        """종목명/코드로 종목 검색"""
        try:
            self.logger.info(f"🔍 종목 검색: '{keyword}'")
            
            stock_list = await self.get_stock_list()
            keyword_lower = keyword.lower()
            matched_stocks = []
            
            for symbol, name in stock_list:
                if (keyword_lower in symbol.lower() or keyword_lower in name.lower()):
                    stock_info = await self.get_stock_info(symbol)
                    if stock_info:
                        matched_stocks.append(stock_info)
                    
                    if len(matched_stocks) >= 20:
                        break
            
            self.logger.info(f"✅ '{keyword}' 검색 결과: {len(matched_stocks)}개")
            return matched_stocks
            
        except Exception as e:
            self.logger.error(f"❌ 종목 검색 실패: {e}")
            return []
    
    def to_stock_data(self, stock_info: Dict) -> StockData:
        """딕셔너리를 StockData 객체로 변환"""
        try:
            return StockData(
                symbol=stock_info.get('symbol', ''),
                name=stock_info.get('name', ''),
                current_price=float(stock_info.get('current_price', 0)),
                change_rate=float(stock_info.get('change_rate', 0)),
                volume=int(stock_info.get('volume', 0)),
                trading_value=float(stock_info.get('trading_value', 0)),
                market_cap=float(stock_info.get('market_cap', 0)),
                shares_outstanding=int(stock_info.get('market_cap', 0) * 100000000 / max(stock_info.get('current_price', 1), 1)),
                high_52w=float(stock_info.get('high_52w', 0)),
                low_52w=float(stock_info.get('low_52w', 0)),
                pe_ratio=stock_info.get('pe_ratio'),
                pbr=stock_info.get('pbr'),
                eps=stock_info.get('eps'),
                bps=stock_info.get('bps'),
                sector=stock_info.get('sector', '기타')
            )
        except Exception as e:
            self.logger.warning(f"⚠️ StockData 변환 실패: {e}")
            return None

# 사용 예시
async def main():
    """사용 예시"""
    try:
        class MockConfig:
            class API:
                KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
                KIS_APP_KEY = "your_app_key"
                KIS_APP_SECRET = "your_app_secret" 
                KIS_VIRTUAL_ACCOUNT = True
            
            class Trading:
                MIN_PRICE = 1000
                MAX_PRICE = 100000
                MIN_VOLUME = 1000
                MIN_MARKET_CAP = 100
            
            api = API()
            trading = Trading()
        
        config = MockConfig()
        
        async with SmartKISCollector(config) as collector:
            # 필터링된 종목 수집
            stocks = await collector.get_filtered_stocks(limit=50)
            print(f"수집된 종목: {len(stocks)}개")
            
            # 특정 종목 검색
            search_results = await collector.search_stocks("삼성전자")
            print(f"검색 결과: {len(search_results)}개")
            
            # 차트 데이터 조회
            if stocks:
                symbol = stocks[0][0]
                chart_data = await collector.get_historical_data(symbol)
                print(f"{symbol} 차트 데이터: {len(chart_data) if chart_data else 0}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())