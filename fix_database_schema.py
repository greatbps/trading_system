#!/usr/bin/env python3
"""
데이터베이스 스키마 수정 스크립트 - trades 테이블 order_price 컬럼 추가
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from config import Config
from database.database_manager import DatabaseManager

async def fix_database_schema():
    """trades 테이블에 누락된 컬럼들 추가"""
    try:
        print("데이터베이스 스키마 수정 시작...")
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        # 컬럼 존재 여부 확인 및 추가
        async with db_manager.get_async_session() as session:
            # order_price 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_price';
            """))
            
            if not result.fetchone():
                print("trades.order_price 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN order_price INTEGER;
                """))
                print("order_price 컬럼 추가 완료")
            else:
                print("order_price 컬럼 이미 존재")
            
            # order_quantity 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_quantity';
            """))
            
            if not result.fetchone():
                print("trades.order_quantity 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN order_quantity INTEGER NOT NULL DEFAULT 0;
                """))
                print("order_quantity 컬럼 추가 완료")
            else:
                print("order_quantity 컬럼 이미 존재")
            
            # executed_price 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'executed_price';
            """))
            
            if not result.fetchone():
                print("[INFO] trades.executed_price 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN executed_price INTEGER;
                """))
                print("[OK] executed_price 컬럼 추가 완료")
            else:
                print("[OK] executed_price 컬럼 이미 존재")
            
            # executed_quantity 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'executed_quantity';
            """))
            
            if not result.fetchone():
                print("[INFO] trades.executed_quantity 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN executed_quantity INTEGER DEFAULT 0;
                """))
                print("[OK] executed_quantity 컬럼 추가 완료")
            else:
                print("[OK] executed_quantity 컬럼 이미 존재")
            
            # order_status 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_status';
            """))
            
            if not result.fetchone():
                print("[INFO] trades.order_status 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN order_status VARCHAR(20) DEFAULT 'PENDING';
                """))
                print("[OK] order_status 컬럼 추가 완료")
            else:
                print("[OK] order_status 컬럼 이미 존재")
            
            # order_time 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_time';
            """))
            
            if not result.fetchone():
                print("[INFO] trades.order_time 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN order_time TIMESTAMP;
                """))
                print("[OK] order_time 컬럼 추가 완료")
            else:
                print("[OK] order_time 컬럼 이미 존재")
            
            # execution_time 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'execution_time';
            """))
            
            if not result.fetchone():
                print("[INFO] trades.execution_time 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN execution_time TIMESTAMP;
                """))
                print("[OK] execution_time 컬럼 추가 완료")
            else:
                print("[OK] execution_time 컬럼 이미 존재")

            # analysis_result_id 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'analysis_result_id';
            """))
            
            if not result.fetchone():
                print("[INFO] trades.analysis_result_id 컬럼 추가 중...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN analysis_result_id INTEGER;
                """))
                print("[OK] analysis_result_id 컬럼 추가 완료")
            else:
                print("[OK] analysis_result_id 컬럼 이미 존재")

            # commission 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'commission';
            """))
            if not result.fetchone():
                print("[INFO] trades.commission 컬럼 추가 중...")
                await session.execute(text('ALTER TABLE trades ADD COLUMN commission INTEGER DEFAULT 0;'))
                print("[OK] commission 컬럼 추가 완료")
            else:
                print("[OK] commission 컬럼 이미 존재")

            # tax 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'tax';
            """))
            if not result.fetchone():
                print("[INFO] trades.tax 컬럼 추가 중...")
                await session.execute(text('ALTER TABLE trades ADD COLUMN tax INTEGER DEFAULT 0;'))
                print("[OK] tax 컬럼 추가 완료")
            else:
                print("[OK] tax 컬럼 이미 존재")

            # strategy_name 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'strategy_name';
            """))
            if not result.fetchone():
                print("[INFO] trades.strategy_name 컬럼 추가 중...")
                await session.execute(text('ALTER TABLE trades ADD COLUMN strategy_name VARCHAR(50);'))
                print("[OK] strategy_name 컬럼 추가 완료")
            else:
                print("[OK] strategy_name 컬럼 이미 존재")

            # trigger_reason 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'trigger_reason';
            """))
            if not result.fetchone():
                print("[INFO] trades.trigger_reason 컬럼 추가 중...")
                await session.execute(text('ALTER TABLE trades ADD COLUMN trigger_reason TEXT;'))
                print("[OK] trigger_reason 컬럼 추가 완료")
            else:
                print("[OK] trigger_reason 컬럼 이미 존재")

            # created_at 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'created_at';
            """))
            if not result.fetchone():
                print("[INFO] trades.created_at 컬럼 추가 중...")
                await session.execute(text('ALTER TABLE trades ADD COLUMN created_at TIMESTAMP WITH TIME ZONE;'))
                print("[OK] created_at 컬럼 추가 완료")
            else:
                print("[OK] created_at 컬럼 이미 존재")

            # updated_at 컬럼 확인
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'updated_at';
            """))
            if not result.fetchone():
                print("[INFO] trades.updated_at 컬럼 추가 중...")
                await session.execute(text('ALTER TABLE trades ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;'))
                print("[OK] updated_at 컬럼 추가 완료")
            else:
                print("[OK] updated_at 컬럼 이미 존재")

            # price 컬럼의 NOT NULL 제약조건 제거
            try:
                print("[INFO] trades.price 컬럼의 NOT NULL 제약조건 제거 시도...")
                await session.execute(text('ALTER TABLE trades ALTER COLUMN price DROP NOT NULL;'))
                print("[OK] trades.price 컬럼의 NOT NULL 제약조건 제거 완료")
            except Exception as e:
                # 이미 제약조건이 없으면 오류가 발생할 수 있으므로, 무시하고 계속 진행
                print(f"[WARN] trades.price 컬럼 제약조건 제거 실패 (이미 적용되었을 수 있음): {e}")
                await session.rollback() # 트랜잭션 롤백

            # quantity 컬럼의 NOT NULL 제약조건 제거
            try:
                print("[INFO] trades.quantity 컬럼의 NOT NULL 제약조건 제거 시도...")
                await session.execute(text('ALTER TABLE trades ALTER COLUMN quantity DROP NOT NULL;'))
                print("[OK] trades.quantity 컬럼의 NOT NULL 제약조건 제거 완료")
            except Exception as e:
                print(f"[WARN] trades.quantity 컬럼 제약조건 제거 실패 (이미 적용되었을 수 있음): {e}")
                await session.rollback() # 트랜잭션 롤백

            # total_amount 컬럼의 NOT NULL 제약조건 제거
            try:
                print("[INFO] trades.total_amount 컬럼의 NOT NULL 제약조건 제거 시도...")
                await session.execute(text('ALTER TABLE trades ALTER COLUMN total_amount DROP NOT NULL;'))
                print("[OK] trades.total_amount 컬럼의 NOT NULL 제약조건 제거 완료")
            except Exception as e:
                print(f"[WARN] trades.total_amount 컬럼 제약조건 제거 실패 (이미 적용되었을 수 있음): {e}")
                await session.rollback() # 트랜잭션 롤백

            # trade_date 컬럼의 NOT NULL 제약조건 제거
            try:
                print("[INFO] trades.trade_date 컬럼의 NOT NULL 제약조건 제거 시도...")
                await session.execute(text('ALTER TABLE trades ALTER COLUMN trade_date DROP NOT NULL;'))
                print("[OK] trades.trade_date 컬럼의 NOT NULL 제약조건 제거 완료")
            except Exception as e:
                print(f"[WARN] trades.trade_date 컬럼 제약조건 제거 실패 (이미 적용되었을 수 있음): {e}")
                await session.rollback() # 트랜잭션 롤백

            await session.commit()
            
        print("[SUCCESS] 데이터베이스 스키마 수정 완료!")
        print("[STAT] 현재 trades 테이블 구조:")
        
        # 테이블 구조 확인
        async with db_manager.get_async_session() as session:
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'trades' 
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]} {'(nullable)' if col[2] == 'YES' else '(not null)'}")
        
    except Exception as e:
        print(f"[FAIL] 데이터베이스 스키마 수정 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("trades 테이블 스키마 수정 스크립트")
    print("=" * 50)
    asyncio.run(fix_database_schema())