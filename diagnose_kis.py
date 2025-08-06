# ===========================================
#     1  
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
    """KIS API   (  )"""
    
    def __init__(self):
        # API  
        self.app_key = os.getenv("KIS_APP_KEY", "").strip().strip('"').strip("'")
        self.app_secret = os.getenv("KIS_APP_SECRET", "").strip().strip('"').strip("'")
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
        #   
        self.token_cache_file = "data/kis_token_cache.json"
        os.makedirs("data", exist_ok=True)
        
        #  
        import logging
        self.logger = logging.getLogger("KISTokenManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        #  
        self.access_token = None
        self.token_expires = None
        self.session = None
    
    async def get_valid_token(self):
        """   (   )"""
        
        # 1.   
        if await self._load_cached_token():
            if await self._is_token_valid():
                self.logger.info("   ")
                return self.access_token
        
        # 2.    (1  )
        if await self._request_new_token():
            await self._save_token_cache()
            return self.access_token
        
        return None
    
    async def _load_cached_token(self):
        """  """
        try:
            if os.path.exists(self.token_cache_file):
                with open(self.token_cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                self.access_token = cache_data.get('access_token')
                expires_str = cache_data.get('expires_at')
                
                if expires_str:
                    self.token_expires = datetime.fromisoformat(expires_str)
                
                if self.access_token and self.token_expires:
                    self.logger.info("    ")
                    return True
        
        except Exception as e:
            self.logger.debug(f"    : {e}")
        
        return False
    
    async def _is_token_valid(self):
        """  """
        if not self.access_token or not self.token_expires:
            return False
        
        #  10   
        margin = timedelta(minutes=10)
        return datetime.now() < (self.token_expires - margin)
    
    async def _request_new_token(self):
        """   """
        try:
            #     
            if not await self._can_request_token():
                self.logger.warning(" 1      ...")
                await asyncio.sleep(65)  # 65 
            
            self.logger.info("    ...")
            
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
                        #     (20 )
                        self.token_expires = datetime.now() + timedelta(hours=20)
                        await self._save_request_time()  #   
                        self.logger.info("    ")
                        return True
                    else:
                        self.logger.error(f"  : {result}")
                        return False
                
                elif response.status == 403:
                    error_text = await response.text()
                    if "1 1" in error_text:
                        self.logger.warning(" 1  -   ")
                        await asyncio.sleep(65)
                        return await self._request_new_token()  #  
                    else:
                        self.logger.error(f"   : {error_text}")
                        return False
                else:
                    error_text = await response.text()
                    self.logger.error(f"   : {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"   : {e}")
            return False
    
    async def _can_request_token(self):
        """     (1 )"""
        try:
            request_time_file = "data/last_token_request.txt"
            
            if os.path.exists(request_time_file):
                with open(request_time_file, 'r') as f:
                    last_request_str = f.read().strip()
                
                last_request = datetime.fromisoformat(last_request_str)
                time_diff = datetime.now() - last_request
                
                if time_diff.total_seconds() < 60:
                    remaining = 60 - time_diff.total_seconds()
                    self.logger.info(f"⏰   {remaining:.0f} ")
                    return False
        
        except Exception as e:
            self.logger.debug(f"    : {e}")
        
        return True
    
    async def _save_request_time(self):
        """   """
        try:
            request_time_file = "data/last_token_request.txt"
            with open(request_time_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            self.logger.debug(f"    : {e}")
    
    async def _save_token_cache(self):
        """  """
        try:
            cache_data = {
                'access_token': self.access_token,
                'expires_at': self.token_expires.isoformat() if self.token_expires else None,
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.token_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            self.logger.info("    ")
        
        except Exception as e:
            self.logger.debug(f"    : {e}")
    
    async def close(self):
        """ """
        if self.session:
            await self.session.close()

# ===========================================
#  KIS Collector (  )
# ===========================================

class SmartKISCollector:
    """ KIS   ( )"""
    
    def __init__(self, config):
        #  
        import logging
        self.logger = logging.getLogger("SmartKISCollector")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # API 
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.app_key = os.getenv("KIS_APP_KEY", "").strip().strip('"').strip("'")
        self.app_secret = os.getenv("KIS_APP_SECRET", "").strip().strip('"').strip("'")
        
        #  
        self.token_manager = KISTokenManager()
        
        #  
        self.session = None
        
        # 
        self.request_delay = 0.2
        self.max_retries = 3
        self.timeout = 15
        
        self.logger.info(" Smart KIS Collector  ")
    
    async def initialize(self):
        """"""
        try:
            self.logger.info(" Smart KIS API  ...")
            
            # HTTP  
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            #  
            token = await self.token_manager.get_valid_token()
            if not token:
                self.logger.error("   ")
                return False
            
            #  
            test_result = await self.get_stock_info("005930")
            if test_result:
                self.logger.info(f"   : {test_result.get('name', '')}")
                return True
            else:
                self.logger.error("   ")
                return False
                
        except Exception as e:
            self.logger.error(f"  : {e}")
            return False
    
    async def get_stock_info(self, symbol: str):
        """  """
        
        for attempt in range(self.max_retries):
            try:
                #   
                token = await self.token_manager.get_valid_token()
                if not token:
                    self.logger.error(f" {symbol}  ")
                    return None
                
                # API 
                result = await self._fetch_stock_data(symbol, token)
                if result:
                    return result
                
                #   
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
            except Exception as e:
                self.logger.debug(f" {symbol}  {attempt + 1} : {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        self.logger.warning(f" {symbol}   ")
        return None
    
    async def _fetch_stock_data(self, symbol: str, token: str):
        """  """
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
            
            # API   
            await asyncio.sleep(self.request_delay)
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('rt_cd') == '0':
                        return self._parse_stock_data(data, symbol)
                    else:
                        self.logger.debug(f" {symbol} API : {data.get('msg1', 'Unknown')}")
                        return None
                        
                elif response.status == 401:
                    self.logger.warning(f" {symbol}   -  ")
                    #   
                    await self._invalidate_token_cache()
                    return None
                    
                else:
                    self.logger.debug(f" {symbol} HTTP : {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.debug(f" {symbol}  : {e}")
            return None
    
    def _parse_stock_data(self, data: dict, symbol: str):
        """ """
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
            self.logger.debug(f" {symbol}  : {e}")
            return None
    
    async def _invalidate_token_cache(self):
        """  """
        try:
            if os.path.exists("data/kis_token_cache.json"):
                os.remove("data/kis_token_cache.json")
                self.logger.info("   ")
        except Exception as e:
            self.logger.debug(f"    : {e}")
    
    async def get_stock_list(self):
        """  """
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
            
            self.logger.info(f"   : {len(stock_list)}")
            return stock_list
            
        except ImportError:
            self.logger.error(" pykrx  : pip install pykrx")
            raise
        except Exception as e:
            self.logger.error(f"    : {e}")
            raise
    
    async def close(self):
        """ """
        if self.session:
            await self.session.close()
        await self.token_manager.close()
        self.logger.info(" Smart KIS Collector ")

# ===========================================
#    
# ===========================================

async def test_smart_collector():
    """  """
    
    print(" Smart KIS Collector ")
    print("=" * 50)
    
    collector = SmartKISCollector(None)
    
    try:
        # 
        print("1.  ...")
        if not await collector.initialize():
            print("  ")
            return False
        
        #     (  )
        print("\n2.    ...")
        test_symbols = ["005930", "000660", "035420", "005380", "006400"]
        
        success_count = 0
        for i, symbol in enumerate(test_symbols, 1):
            print(f"    {i}/5 {symbol}  ...")
            result = await collector.get_stock_info(symbol)
            
            if result:
                print(f"    {result['name']} - {result['current_price']:,.0f}")
                success_count += 1
            else:
                print(f"    ")
        
        print(f"\n : {success_count}/{len(test_symbols)} ")
        return success_count >= 3  # 60%   
    
    finally:
        await collector.close()

async def main():
    """ """
    
    print("   KIS API ")
    print("=" * 60)
    
    success = await test_smart_collector()
    
    if success:
        print("\n  !    ")
        print("\n  trading_system SmartKISCollector :")
        print("   from data_collectors.kis_collector import SmartKISCollector")
        print("   self.data_collector = SmartKISCollector(self.config)")
    else:
        print("\n   -   ")

if __name__ == "__main__":
    asyncio.run(main())