#!/usr/bin/env python3
"""
Debug KIS API response structure
"""

import asyncio
import sys
import json
from datetime import datetime

sys.path.append('D:/trading_system')

from data_collectors.kis_collector import KISCollector
from config import Config

async def debug_trading_history():
    config = Config()
    
    async with KISCollector(config) as kis_collector:
        today_str = datetime.now().strftime('%Y%m%d')
        
        params = {
            'CANO': config.api.KIS_ACCOUNT_NUMBER[:8],
            'ACNT_PRDT_CD': config.api.KIS_ACCOUNT_NUMBER[-2:],
            'INQR_STRT_DT': today_str,
            'INQR_END_DT': today_str,
            'SLL_BUY_DVSN_CD': '00',
            'INQR_DVSN': '00',
            'PDNO': '',
            'CCLD_DVSN': '00',
            'ORD_GNO_BRNO': '',
            'ODNO': '',
            'INQR_DVSN_3': '00',
            'INQR_DVSN_1': '',
            'CTX_AREA_FK100': '',
            'CTX_AREA_NK100': ''
        }
        
        data = await kis_collector._make_api_request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
            params=params,
            tr_id="TTTC0081R"
        )
        
        if data and data.get('rt_cd') == '0':
            print(f"성공: {len(data.get('output1', []))}건 조회")
            print("\nAPI 응답 구조:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"오류: {data}")

if __name__ == "__main__":
    asyncio.run(debug_trading_history())