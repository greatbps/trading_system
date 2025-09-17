import asyncio
from sqlalchemy import select
from config import Config
from database.database_manager import DatabaseManager
from database.models import MonitoringStock, Stock

async def debug_issue():
    """
    '전략 추출 감시 종목'에 종목명이 N/A로 나오는 문제를 디버깅합니다. (수정된 버전)
    """
    print("--- 종목명 N/A 문제 디버깅 시작 ---")
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    symbol_to_check = '000660' # SK하이닉스
    
    async with db_manager.get_async_session() as session:
        # 1. monitoring_stocks 테이블에서 데이터 조회 (쿼리 방식 수정)
        print(f"\n[1] monitoring_stocks 테이블에서 '{symbol_to_check}' 조회...")
        
        result = await session.execute(
            select(MonitoringStock).where(MonitoringStock.symbol == symbol_to_check)
        )
        monitoring_entry = result.scalars().first()

        if monitoring_entry:
            print(f"  [성공] MonitoringStock: symbol={monitoring_entry.symbol}, name={monitoring_entry.name}, strategy={monitoring_entry.strategy_name}")
        else:
            print(f"  [실패] monitoring_stocks 테이블에 '{symbol_to_check}' 종목이 없습니다.")
            
        # 2. stocks 테이블에서 데이터 조회
        print(f"\n[2] stocks 테이블에서 '{symbol_to_check}' 조회...")
        result = await session.execute(
            select(Stock).where(Stock.symbol == symbol_to_check)
        )
        stock_entry = result.scalars().first()
        
        if stock_entry:
            print(f"  [성공] Stock: symbol={stock_entry.symbol}, name={stock_entry.name}")
            
            if not stock_entry.name or stock_entry.name == 'N/A':
                print("\n[진단] 원인: 'stocks' 테이블에 해당 종목의 종목명(name)이 비어있습니다.")
            else:
                print("\n[진단] 확인: 'stocks' 테이블에는 종목명이 올바르게 저장되어 있습니다.")
                print("         -> JOIN 로직이나 다른 부분에 문제가 있을 수 있습니다.")
        else:
            print(f"\n[진단] 원인: 'stocks' 테이블에 '{symbol_to_check}' 종목 정보가 아예 없습니다.")
            print("         -> 전략에 의해 monitoring_stocks 테이블에 종목이 추가될 때, stocks 테이블에는 상세 정보가 저장되지 않는 문제입니다.")

    print("\n--- 디버깅 종료 ---")

if __name__ == "__main__":
    asyncio.run(debug_issue())