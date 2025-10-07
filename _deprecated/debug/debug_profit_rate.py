#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
동원금속 수익률 계산 디버깅
"""

import sys
import io
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from data_collectors.kis_collector import KISCollector
from config import Config

async def debug_profit_rate():
    """동원금속 수익률 계산 디버깅"""
    try:
        config = Config()
        kis_collector = KISCollector(config)
        await kis_collector.initialize()
        
        # 보유 종목 조회
        holdings = await kis_collector.get_holdings() or {}
        
        if "018500" in holdings:
            holding_info = holdings["018500"]
            
            print("🔍 동원금속 수익률 계산 디버깅")
            print(f"종목코드: 018500")
            print(f"종목명: {holding_info['name']}")
            print(f"보유수량: {holding_info['quantity']}주")
            print(f"매수평균가: {holding_info['avg_price']}")
            print(f"현재가: {holding_info['current_price']}")
            print(f"평가금액: {holding_info['evaluation']:,}원")
            print(f"손익금액: {holding_info['profit_loss']:,}원")
            print(f"API 수익률: {holding_info['profit_rate']:.2f}%")
            
            # 수동 계산
            avg_price = holding_info['avg_price']
            current_price = holding_info['current_price']
            
            if avg_price > 0 and current_price > 0:
                manual_profit_rate = ((current_price - avg_price) / avg_price) * 100
                print(f"수동 계산 수익률: {manual_profit_rate:.2f}%")
                
                # 포매팅 테스트
                if manual_profit_rate >= 5.0:
                    display = f"[bold green]▲{manual_profit_rate:.2f}%[/bold green]"
                elif manual_profit_rate > 0:
                    display = f"[green]▲{manual_profit_rate:.2f}%[/green]"
                elif manual_profit_rate <= -5.0:
                    display = f"[bold red]▼{abs(manual_profit_rate):.2f}%[/bold red]"
                else:
                    display = f"[red]▼{abs(manual_profit_rate):.2f}%[/red]"
                
                print(f"Rich 포매팅: {display}")
            else:
                print("❌ 수익률 계산 불가")
        else:
            print("❌ 동원금속이 잔고에 없습니다")
            
    except Exception as e:
        print(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_profit_rate())