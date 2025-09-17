#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 매매 모니터링 및 보유 종목 상태 확인
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import DatabaseManager
from config import Config
from sqlalchemy import text

async def check_trading_status():
    """현재 매매 상태 확인"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    try:
        
        print("=" * 60)
        print("         현재 매매 상태 확인")
        print("=" * 60)
        
        # 1. 모니터링 종목 확인
        monitoring_query = """
        SELECT 
            symbol, 
            name, 
            strategy_name,
            status,
            monitoring_type,
            target_price,
            current_price,
            created_at
        FROM monitoring_stocks 
        WHERE monitoring_active = true AND monitoring_type IN ('TRADING', 'PORTFOLIO', 'REMOVAL_WATCH')
        ORDER BY created_at DESC
        """
        
        # SQL 쿼리 실행을 위해 async session 사용
        async with db_manager.get_async_session() as session:
            result = await session.execute(text(monitoring_query))
            monitoring_stocks = [dict(row._mapping) for row in result.fetchall()]
        
        print(f"\n📊 모니터링 중인 종목: {len(monitoring_stocks)}개")
        print("-" * 60)
        
        active_count = 0
        trading_count = 0
        portfolio_count = 0 # 새로운 카운터 추가
        removal_count = 0
        
        for stock in monitoring_stocks:
            status_emoji = "🔵" if stock['status'] == 'ACTIVE' else "⚪"
            
            # monitoring_type에 따라 다른 이모지 사용
            if stock['monitoring_type'] == 'TRADING':
                type_emoji = "💰"
                trading_count += 1
            elif stock['monitoring_type'] == 'PORTFOLIO':
                type_emoji = "💼" # 보유 종목용 이모지
                portfolio_count += 1
            else: # REMOVAL_WATCH 등
                type_emoji = "👁️"
                removal_count += 1
            
            print(f"{status_emoji} {type_emoji} {stock['symbol']} {stock['name']}")
            print(f"   전략: {stock['strategy_name']}, 상태: {stock['status']}")
            if stock['target_price'] and stock['current_price']:
                print(f"   목표가: {stock['target_price']:,}원, 현재가: {stock['current_price']:,}원")
            elif stock['target_price']:
                print(f"   목표가: {stock['target_price']:,}원, 현재가: 정보없음")
            elif stock['current_price']:
                print(f"   목표가: 정보없음, 현재가: {stock['current_price']:,}원")
            else:
                print("   가격정보 없음")
            print(f"   등록: {stock['created_at'].strftime('%Y-%m-%d %H:%M')}" if stock['created_at'] else "   등록일 정보 없음")
            print()
            
            if stock['status'] == 'ACTIVE':
                active_count += 1
        
        print(f"  💰 매매용 모니터링: {trading_count}개")
        print(f"  💼 보유 종목 모니터링: {portfolio_count}개") # 새로운 카운터 표시
        print(f"  👁️ 제거용 감시: {removal_count}개")
        print(f"  🔵 활성 상태: {active_count}개")
        
        # 2. 포트폴리오 확인
        portfolio_query = """
        SELECT 
            p.quantity,
            p.avg_price,
            p.total_cost,
            p.current_price,
            p.market_value,
            p.unrealized_pnl,
            p.unrealized_pnl_rate,
            s.symbol,
            s.name,
            p.status,
            p.created_at
        FROM portfolio p
        JOIN stocks s ON p.stock_id = s.id
        WHERE p.status = 'OPEN' AND p.quantity > 0
        ORDER BY p.created_at DESC
        """
        
        async with db_manager.get_async_session() as session:
            result = await session.execute(text(portfolio_query))
            portfolio = [dict(row._mapping) for row in result.fetchall()]
        
        print(f"\n💼 보유 중인 종목: {len(portfolio)}개")
        print("-" * 60)
        
        total_cost = 0
        total_value = 0
        total_pnl = 0
        
        for holding in portfolio:
            pnl_color = "🟢" if holding['unrealized_pnl'] and holding['unrealized_pnl'] >= 0 else "🔴"
            
            print(f"💼 {holding['symbol']} {holding['name']}")
            print(f"   수량: {holding['quantity']:,}주, 평균단가: {holding['avg_price']:,}원")
            print(f"   총매수: {holding['total_cost']:,}원")
            
            if holding['current_price']:
                print(f"   현재가: {holding['current_price']:,}원")
                print(f"   평가액: {holding['market_value']:,}원")
                print(f"   {pnl_color} 평가손익: {holding['unrealized_pnl']:,}원 ({holding['unrealized_pnl_rate']:.2f}%)")
            else:
                print(f"   현재가 정보 없음")
            
            print(f"   매수일: {holding['created_at'].strftime('%Y-%m-%d %H:%M')}" if holding['created_at'] else "   매수일 정보 없음")
            print()
            
            total_cost += holding['total_cost'] or 0
            total_value += holding['market_value'] or 0
            total_pnl += holding['unrealized_pnl'] or 0
        
        if portfolio:
            total_pnl_rate = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            
            print("=" * 60)
            print("포트폴리오 총계:")
            print(f"  총 매수금액: {total_cost:,}원")
            print(f"  총 평가금액: {total_value:,}원")
            print(f"  {pnl_emoji} 총 평가손익: {total_pnl:,}원 ({total_pnl_rate:.2f}%)")
        
        # 3. 권장사항 제시
        print("\n" + "=" * 60)
        print("💡 권장사항:")
        print("-" * 60)
        
        if trading_count < 10:
            print(f"⚠️  매매용 모니터링 종목이 {trading_count}개로 부족합니다.")
            print(f"   목표: 최소 10개 이상 → {10 - trading_count}개 추가 필요")
        else:
            print(f"✅ 매매용 모니터링 종목: {trading_count}개 (충분)")
        
        if len(portfolio) > 5:
            print(f"⚠️  보유 종목이 {len(portfolio)}개로 과다합니다.")
            print(f"   목표: 최대 5개 이하 → {len(portfolio) - 5}개 매도 검토")
        else:
            print(f"✅ 보유 종목: {len(portfolio)}개 (적정)")
        
        print("\n🔄 자동 조절 방법:")
        print("  1. 시장 분석을 통해 우량 종목을 추가 발굴")
        print("  2. 수익률이 낮은 보유 종목의 매도 검토")
        print("  3. 모니터링 풀을 지속적으로 갱신")
        
    except Exception as e:
        print(f"❌ 상태 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # db_manager는 자동으로 정리됨
        pass

if __name__ == "__main__":
    asyncio.run(check_trading_status())