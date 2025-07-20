import requests
import json
from typing import Dict, List, Optional

class KISDebugTools:
    def __init__(self, app_key: str, app_secret: str, base_url: str = "https://openapi.koreainvestment.com:9443"):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.access_token = None
        
    def get_access_token(self) -> str:
        """액세스 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
            return self.access_token
        else:
            raise Exception(f"토큰 발급 실패: {response.text}")
    
    def test_all_market_codes(self, symbol: str) -> Dict:
        """모든 가능한 시장 코드로 테스트"""
        if not self.access_token:
            self.get_access_token()
            
        # 다양한 시장 코드 조합 테스트
        market_codes = [
            "NAS", "NASD", "NASDAQ", 
            "NYS", "NYSE", "NY",
            "AMS", "AMEX", "AM",
            "TSE", "LSE", "HKG"
        ]
        
        results = {}
        
        for market_code in market_codes:
            try:
                result = self._test_price_api(symbol, market_code)
                results[market_code] = result
                print(f"시장코드 {market_code}: {'✅ 성공' if result['success'] else '❌ 실패'}")
                if result['success']:
                    print(f"  데이터: {result['data']}")
            except Exception as e:
                results[market_code] = {"success": False, "error": str(e)}
                print(f"시장코드 {market_code}: ❌ 예외 - {e}")
        
        return results
    
    def _test_price_api(self, symbol: str, market: str) -> Dict:
        """가격 API 테스트"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/quotations/price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "HHDFS00000300"
        }
        
        params = {
            "SYMB": symbol,
            "EXCD": market
        }
        
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        
        success = (result.get("rt_cd") == "0" and 
                  result.get("output") and 
                  result["output"] != "" and
                  result["output"] != "{}")
        
        return {
            "success": success,
            "data": result.get("output") if success else None,
            "full_response": result,
            "status_code": response.status_code
        }
    
    def get_portfolio_symbols(self) -> List[Dict]:
        """보유 종목 조회 (등록된 종목 코드 확인용)"""
        if not self.access_token:
            self.get_access_token()
            
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "VTRP6504R"
        }
        
        params = {
            "CANO": "your_account_number",  # 계좌번호 입력 필요
            "ACNT_PRDT_CD": "01",
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get("rt_cd") == "0":
                return result.get("output1", [])
            else:
                print(f"보유 종목 조회 실패: {result}")
                return []
                
        except Exception as e:
            print(f"보유 종목 조회 중 오류: {e}")
            return []
    
    def get_watchlist_symbols(self) -> List[Dict]:
        """관심 종목 조회"""
        if not self.access_token:
            self.get_access_token()
            
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-watch-list"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "HHDFS76200000"
        }
        
        params = {
            "CANO": "your_account_number",  # 계좌번호 입력 필요
            "ACNT_PRDT_CD": "01"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get("rt_cd") == "0":
                return result.get("output", [])
            else:
                print(f"관심 종목 조회 실패: {result}")
                return []
                
        except Exception as e:
            print(f"관심 종목 조회 중 오류: {e}")
            return []
    
    def comprehensive_symbol_test(self, symbol: str) -> Dict:
        """종합적인 종목 테스트"""
        print(f"\n{'='*50}")
        print(f"종목 {symbol} 종합 테스트")
        print(f"{'='*50}")
        
        results = {
            "symbol": symbol,
            "search_results": {},
            "price_tests": {},
            "recommendations": []
        }
        
        # 1. 종목 검색 테스트
        print("\n1. 종목 검색 테스트")
        search_markets = ["NAS", "NYS", "AMS"]
        for market in search_markets:
            try:
                search_result = self._search_symbol(symbol, market)
                results["search_results"][market] = search_result
                if search_result.get("success"):
                    print(f"  {market}: ✅ 검색 성공")
                    # 검색 결과에서 종목 코드 추출
                    if "output" in search_result["data"]:
                        output = search_result["data"]["output"]
                        if isinstance(output, list) and len(output) > 0:
                            found_code = output[0].get("shtn_cd") or output[0].get("symb")
                            if found_code:
                                results["recommendations"].append(f"검색된 종목코드: {found_code} (시장: {market})")
            except Exception as e:
                print(f"  {market}: ❌ 검색 실패 - {e}")
                results["search_results"][market] = {"success": False, "error": str(e)}
        
        # 2. 가격 조회 테스트
        print("\n2. 가격 조회 테스트")
        results["price_tests"] = self.test_all_market_codes(symbol)
        
        # 3. 추천 사항 생성
        print("\n3. 추천 사항")
        successful_markets = [market for market, result in results["price_tests"].items() if result.get("success")]
        
        if successful_markets:
            results["recommendations"].append(f"성공한 시장 코드: {', '.join(successful_markets)}")
        else:
            results["recommendations"].append("모든 시장 코드에서 실패 - 종목 코드 확인 필요")
        
        for rec in results["recommendations"]:
            print(f"  💡 {rec}")
        
        return results
    
    def _search_symbol(self, symbol: str, market: str) -> Dict:
        """종목 검색 (내부 함수)"""
        if not self.access_token:
            self.get_access_token()
            
        url = f"{self.base_url}/uapi/overseas-stock/v1/quotations/search"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "HHDFS76240000"
        }
        
        params = {
            "PRDT_TYPE_CD": "512",
            "MICR_NO": market,
            "ITEM_CD": symbol
        }
        
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        
        success = result.get("rt_cd") == "0" and result.get("output")
        
        return {
            "success": success,
            "data": result,
            "status_code": response.status_code
        }

# 사용 예시
def main():
    # KIS API 인증 정보 설정
    APP_KEY = "your_app_key"
    APP_SECRET = "your_app_secret"
    
    # 디버깅 도구 초기화
    debug_tools = KISDebugTools(APP_KEY, APP_SECRET)
    
    # SOXL 종합 테스트
    test_results = debug_tools.comprehensive_symbol_test("SOXL")
    
    # 결과 저장
    with open("soxl_debug_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n결과가 soxl_debug_results.json에 저장되었습니다.")

if __name__ == "__main__":
    main()