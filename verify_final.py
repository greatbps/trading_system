#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def verify_final_trading_system():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print('[오류] GEMINI API KEY가 설정되지 않았습니다.')
        return
    
    genai.configure(api_key=api_key)
    
    print('[검증] 최종 실전 매매 시스템 검증을 시작합니다...')
    
    # 검증 프롬프트
    verification_prompt = '''
다음 거래 시스템을 내일 실전 매매에 투입하기 전 최종 검증해 주세요.

### 검증 요구사항:
1. KIS API 실제 주문 실행 가능성
2. 한국 주식 호가단위 검증 로직
3. 중복 주문 방지 시스템
4. 일일 손실 한도 체크
5. API 호출 제한 관리
6. 실전 매매 안전성

### 중요 수정 사항 (오늘):
- place_order 메서드에 중복 주문 방지 (5초 내 동일 주문 차단)
- 한국 주식 호가단위 자동 조정 (_validate_korean_price_unit)
- 일일 손실 한도 체크 (_check_daily_loss_limit)
- API 호출 제한 관리 (rate_limiter.acquire)

### 시스템 주요 파일:
1. data_collectors/kis_collector.py - KIS API 연동 (place_order 메서드 중점)
2. trading/smart_rebalancer.py - 스마트 리밸런싱 시스템
3. trading/auto_trader.py - 자동매매 메인 로직
4. config.py - 시스템 설정

**검증 기준**: HIGH(실전 매매 차단), MEDIUM(주의 필요), LOW(개선 권장)

각 이슈에 대해 구체적인 수정 방안을 제시해 주세요.

### KIS Collector place_order 메서드 주요 코드:
```python
async def place_order(self, symbol: str, quantity: int, price: Optional[int], 
                     order_type: str, side: str) -> Dict[str, Any]:
    try:
        # 0. 주문 중복 방지 (5초 내 같은 주문 방지)
        order_key = f"{symbol}_{side}_{quantity}_{price}"
        current_time = time.time()
        if hasattr(self, 'recent_orders') and order_key in self.recent_orders:
            if current_time - self.recent_orders[order_key] < 5:
                return {'success': False, 'error': '중복 주문 방지: 5초 이내 동일 주문이 있습니다.'}
        
        if not hasattr(self, 'recent_orders'):
            self.recent_orders = {}
        self.recent_orders[order_key] = current_time
        
        # 0-1. 일일 손실 한도 체크 (매수 주문일 때)
        if side.upper() == 'BUY':
            daily_loss_check = await self._check_daily_loss_limit()
            if not daily_loss_check['allowed']:
                return {'success': False, 'error': f'일일 손실 한도 초과: {daily_loss_check["reason"]}'}
        
        # 2. 호가단위 검증 (지정가 주문인 경우)
        if order_type.upper() == 'LIMIT' and price:
            validated_price = self._validate_korean_price_unit(price)
            if validated_price != price:
                self.logger.warning(f"호가단위 조정: {price} → {validated_price}")
                price = validated_price

        # 6. API 호출 제한 체크
        await self.rate_limiter.acquire()
        
        # 실제 KIS API 호출
        result = await self._make_api_request(
            method="POST",
            endpoint="/uapi/domestic-stock/v1/trading/order-cash",
            data=request_body,
            tr_id=tr_id
        )
```

### 호가단위 검증 로직:
```python
def _validate_korean_price_unit(self, price: int) -> int:
    """한국 주식 호가단위 검증 및 조정"""
    if price < 1000:
        return ((price + 0) // 1) * 1  # 1원 단위
    elif price < 5000:
        return ((price + 2) // 5) * 5  # 5원 단위
    elif price < 10000:
        return ((price + 4) // 10) * 10  # 10원 단위
    elif price < 50000:
        return ((price + 24) // 50) * 50  # 50원 단위
    elif price < 100000:
        return ((price + 49) // 100) * 100  # 100원 단위
    elif price < 500000:
        return ((price + 249) // 500) * 500  # 500원 단위
    else:
        return ((price + 499) // 1000) * 1000  # 1000원 단위
```

실전 매매 관점에서 **치명적인 결함**이 있는지 검증하고, 있다면 구체적인 해결 방안을 제시해 주세요.
    '''
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(verification_prompt)
        
        print('\n' + '='*60)
        print('[중요] 최종 실전 매매 시스템 검증 결과')
        print('='*60)
        print(response.text)
        print('='*60)
        
    except Exception as e:
        print(f'[오류] 검증 중 오류: {e}')

if __name__ == '__main__':
    asyncio.run(verify_final_trading_system())