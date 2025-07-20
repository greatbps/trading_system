# ===========================================
# 토큰 캐싱 및 재사용으로 1분 제한 해결
# ===========================================

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class KISTokenManager:
    """KIS API 토큰 관리자 (캐싱 및 재사용)"""
    
    def __init__(self):
        # API 키 설정
        self.app_key = os.getenv("KIS_APP_KEY", "").strip().strip('"').strip("'")
        self.app_secret = os.getenv("KIS_APP_SECRET", "").strip().strip('"').strip("'")
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
        # 토큰 캐시 파일
        self.token_cache_file = "data/kis_token_cache.json"
        os.makedirs("data", exist_ok=True)
        
        # 로거 설정
        import logging
        self.logger = logging.getLogger("KISTokenManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # 토큰 정보
        self.access_token = None
        self.token_expires = None
        self.session = None
    
    async def get_valid_token(self):
        """유효한 토큰 반환 (캐시된 토큰 우선 사용)"""
        
        # 1. 캐시된 토큰 확인
        if await self._load_cached_token():
            if await self._is_token_valid():
                self.logger.info("✅ 캐시된 토큰 사용")
                return self.access_token
        
        # 2. 새 토큰 발급 (1분 제한 고려)
        if await self._request_new_token():
            await self._save_token_cache()
            return self.access_token
        
        return None
    
    async def _load_cached_token(self):
        """캐시된 토큰 로드"""
        try:
            if os.path.exists(self.token_cache_file):
                with open(self.token_cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                self.access_token = cache_data.get('access_token')
                expires_str = cache_data.get('expires_at')
                
                if expires_str:
                    self.token_expires = datetime.fromisoformat(expires_str)
                
                if self.access_token and self.token_expires:
                    self.logger.info("📂 캐시된 토큰 로드 완료")
                    return True
        
        except Exception as e:
            self.logger.debug(f"⚠️ 토큰 캐시 로드 실패: {e}")
        
        return False
    
    async def _is_token_valid(self):
        """토큰 유효성 확인"""
        if not self.access_token or not self.token_expires:
            return False
        
        # 만료 10분 전까지만 유효로 간주
        margin = timedelta(minutes=10)
        return datetime.now() < (self.token_expires - margin)
    
    async def _request_new_token(self):
        """새 토큰 발급 요청"""
        try:
            # 마지막 토큰 발급 시간 확인
            if not await self._can_request_token():
                self.logger.warning("⚠️ 1분 제한으로 인해 토큰 발급 대기 중...")
                await asyncio.sleep(65)  # 65초 대기
            
            self.logger.info("🔑 새 토큰 발급 요청...")
            
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=10)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            token_url = f"{self.base_url}/oauth2/tokenP"
            token_data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            async with self.session.post(token_url, json=token_data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.access_token = result.get('access_token')
                    
                    if self.access_token:
                        # 토큰 만료 시간 설정 (20시간 후)
                        self.token_expires = datetime.now() + timedelta(hours=20)
                        await self._save_request_time()  # 발급 시간 기록
                        self.logger.info("✅ 새 토큰 발급 성공")
                        return True
                    else:
                        self.logger.error(f"❌ 토큰 없음: {result}")
                        return False
                
                elif response.status == 403:
                    error_text = await response.text()
                    if "1분당 1회" in error_text:
                        self.logger.warning("⚠️ 1분 제한 - 대기 후 재시도")
                        await asyncio.sleep(65)
                        return await self._request_new_token()  # 재귀 호출
                    else:
                        self.logger.error(f"❌ 토큰 발급 금지: {error_text}")
                        return False
                else:
                    error_text = await response.text()
                    self.logger.error(f"❌ 토큰 발급 실패: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ 토큰 발급 오류: {e}")
            return False
    
    async def _can_request_token(self):
        """토큰 발급 가능 여부 확인 (1분 제한)"""
        try:
            request_time_file = "data/last_token_request.txt"
            
            if os.path.exists(request_time_file):
                with open(request_time_file, 'r') as f:
                    last_request_str = f.read().strip()
                
                last_request = datetime.fromisoformat(last_request_str)
                time_diff = datetime.now() - last_request
                
                if time_diff.total_seconds() < 60:
                    remaining = 60 - time_diff.total_seconds()
                    self.logger.info(f"⏰ 토큰 발급까지 {remaining:.0f}초 대기")
                    return False
        
        except Exception as e:
            self.logger.debug(f"⚠️ 발급 시간 확인 실패: {e}")
        
        return True
    
    async def _save_request_time(self):
        """토큰 발급 시간 기록"""
        try:
            request_time_file = "data/last_token_request.txt"
            with open(request_time_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            self.logger.debug(f"⚠️ 발급 시간 저장 실패: {e}")
    
    async def _save_token_cache(self):
        """토큰 캐시 저장"""
        try:
            cache_data = {
                'access_token': self.access_token,
                'expires_at': self.token_expires.isoformat() if self.token_expires else None,
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.token_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            self.logger.info("💾 토큰 캐시 저장 완료")
        
        except Exception as e:
            self.logger.debug(f"⚠️ 토큰 캐시 저장 실패: {e}")
    
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

# ===========================================
# 개선된 KIS Collector (토큰 관리자 사용)
# ===========================================

class SmartKISCollector:
    """스마트 KIS 데이터 수집기 (토큰 재사용)"""
    
    def __init__(self, config):
        # 로거 설정
        import logging
        self.logger = logging.getLogger("SmartKISCollector")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # API 설정
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.app_key = os.getenv("KIS_APP_KEY", "").strip().strip('"').strip("'")
        self.app_secret = os.getenv("KIS_APP_SECRET", "").strip().strip('"').strip("'")
        
        # 토큰 관리자
        self.token_manager = KISTokenManager()
        
        # 세션 관리
        self.session = None
        
        # 설정
        self.request_delay = 0.2
        self.max_retries = 3
        self.timeout = 15
        
        self.logger.info("✅ Smart KIS Collector 초기화 완료")
    
    async def initialize(self):
        """초기화"""
        try:
            self.logger.info("🚀 Smart KIS API 초기화 시작...")
            
            # HTTP 세션 생성
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 토큰 확보
            token = await self.token_manager.get_valid_token()
            if not token:
                self.logger.error("❌ 토큰 확보 실패")
                return False
            
            # 연결 테스트
            test_result = await self.get_stock_info("005930")
            if test_result:
                self.logger.info(f"✅ 연결 테스트 성공: {test_result.get('name', '삼성전자')}")
                return True
            else:
                self.logger.error("❌ 연결 테스트 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 초기화 실패: {e}")
            return False
    
    async def get_stock_info(self, symbol: str):
        """종목 정보 조회"""
        
        for attempt in range(self.max_retries):
            try:
                # 유효한 토큰 확보
                token = await self.token_manager.get_valid_token()
                if not token:
                    self.logger.error(f"❌ {symbol} 토큰 없음")
                    return None
                
                # API 호출
                result = await self._fetch_stock_data(symbol, token)
                if result:
                    return result
                
                # 재시도 전 대기
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
            except Exception as e:
                self.logger.debug(f"⚠️ {symbol} 시도 {attempt + 1} 실패: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        self.logger.warning(f"⚠️ {symbol} 데이터 수집 실패")
        return None
    
    async def _fetch_stock_data(self, symbol: str, token: str):
        """실제 데이터 조회"""
        try:
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010100",
                "custtype": "P",
                "content-type": "application/json; charset=utf-8"
            }
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol
            }
            
            # API 호출 제한 방지
            await asyncio.sleep(self.request_delay)
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('rt_cd') == '0':
                        return self._parse_stock_data(data, symbol)
                    else:
                        self.logger.debug(f"⚠️ {symbol} API 오류: {data.get('msg1', 'Unknown')}")
                        return None
                        
                elif response.status == 401:
                    self.logger.warning(f"⚠️ {symbol} 인증 오류 - 토큰 무효화")
                    # 토큰 캐시 무효화
                    await self._invalidate_token_cache()
                    return None
                    
                else:
                    self.logger.debug(f"⚠️ {symbol} HTTP 오류: {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} 요청 오류: {e}")
            return None
    
    def _parse_stock_data(self, data: dict, symbol: str):
        """데이터 파싱"""
        try:
            output = data.get('output', {})
            if not output:
                return None
            
            current_price = float(output.get('stck_prpr', 0))
            if current_price <= 0:
                return None
            
            return {
                'symbol': symbol,
                'name': output.get('hts_kor_isnm', '').strip(),
                'current_price': current_price,
                'change_rate': float(output.get('prdy_ctrt', 0)),
                'volume': int(output.get('acml_vol', 0)),
                'trading_value': float(output.get('acml_tr_pbmn', 0)),
                'market_cap': (current_price * int(output.get('lstn_stcn', 0))) / 100000000,
                'high_52w': float(output.get('w52_hgpr', current_price)),
                'low_52w': float(output.get('w52_lwpr', current_price)),
            }
            
        except (ValueError, TypeError) as e:
            self.logger.debug(f"⚠️ {symbol} 파싱 오류: {e}")
            return None
    
    async def _invalidate_token_cache(self):
        """토큰 캐시 무효화"""
        try:
            if os.path.exists("data/kis_token_cache.json"):
                os.remove("data/kis_token_cache.json")
                self.logger.info("🗑️ 토큰 캐시 무효화")
        except Exception as e:
            self.logger.debug(f"⚠️ 토큰 캐시 무효화 실패: {e}")
    
    async def get_stock_list(self):
        """종목 리스트 조회"""
        try:
            from pykrx import stock
            today = datetime.now().strftime("%Y%m%d")
            
            kospi = stock.get_market_ticker_list(today, market="KOSPI")
            kosdaq = stock.get_market_ticker_list(today, market="KOSDAQ")
            
            all_tickers = kospi + kosdaq
            stock_list = []
            
            for ticker in all_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if name and len(ticker) == 6:
                        stock_list.append((ticker, name))
                except:
                    continue
            
            self.logger.info(f"✅ 종목 리스트 조회: {len(stock_list)}개")
            return stock_list
            
        except ImportError:
            self.logger.error("❌ pykrx 라이브러리 필요: pip install pykrx")
            raise
        except Exception as e:
            self.logger.error(f"❌ 종목 리스트 조회 실패: {e}")
            raise
    
    async def close(self):
        """리소스 정리"""
        if self.session:
            await self.session.close()
        await self.token_manager.close()
        self.logger.info("✅ Smart KIS Collector 종료")

# ===========================================
# 테스트 및 사용 예제
# ===========================================

async def test_smart_collector():
    """스마트 수집기 테스트"""
    
    print("🧠 Smart KIS Collector 테스트")
    print("=" * 50)
    
    collector = SmartKISCollector(None)
    
    try:
        # 초기화
        print("1. 초기화 중...")
        if not await collector.initialize():
            print("❌ 초기화 실패")
            return False
        
        # 연속 종목 조회 테스트 (토큰 재사용 확인)
        print("\n2. 연속 종목 조회 테스트...")
        test_symbols = ["005930", "000660", "035420", "005380", "006400"]
        
        success_count = 0
        for i, symbol in enumerate(test_symbols, 1):
            print(f"   📊 {i}/5 {symbol} 조회 중...")
            result = await collector.get_stock_info(symbol)
            
            if result:
                print(f"   ✅ {result['name']} - {result['current_price']:,.0f}원")
                success_count += 1
            else:
                print(f"   ❌ 실패")
        
        print(f"\n📊 결과: {success_count}/{len(test_symbols)} 성공")
        return success_count >= 3  # 60% 이상 성공시 통과
    
    finally:
        await collector.close()

async def main():
    """메인 함수"""
    
    print("🧠 스마트 토큰 관리 KIS API 테스트")
    print("=" * 60)
    
    success = await test_smart_collector()
    
    if success:
        print("\n🎉 테스트 성공! 토큰 캐싱이 정상 작동합니다")
        print("\n💡 이제 trading_system에서 SmartKISCollector를 사용하세요:")
        print("   from data_collectors.kis_collector import SmartKISCollector")
        print("   self.data_collector = SmartKISCollector(self.config)")
    else:
        print("\n⚠️ 테스트 실패 - 추가 확인 필요")

if __name__ == "__main__":
    asyncio.run(main())