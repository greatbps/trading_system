#!/usr/bin/env python3
"""
Simple database schema fix script
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from config import Config
from database.database_manager import DatabaseManager

async def fix_schema():
    """Add missing columns to trades table"""
    try:
        print("Fixing database schema...")
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        async with db_manager.get_async_session() as session:
            # Check and add order_price column
            result = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_price';
            """))
            
            if not result.fetchone():
                print("Adding order_price column...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN order_price INTEGER;
                """))
                print("order_price column added")
            else:
                print("order_price column already exists")
            
            # Check and add order_quantity column
            result = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'order_quantity';
            """))
            
            if not result.fetchone():
                print("Adding order_quantity column...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN order_quantity INTEGER DEFAULT 0;
                """))
                print("order_quantity column added")
            else:
                print("order_quantity column already exists")
            
            # Check and add executed_price column
            result = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'executed_price';
            """))
            
            if not result.fetchone():
                print("Adding executed_price column...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN executed_price INTEGER;
                """))
                print("executed_price column added")
            else:
                print("executed_price column already exists")
            
            # Check and add executed_quantity column
            result = await session.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'trades' AND column_name = 'executed_quantity';
            """))
            
            if not result.fetchone():
                print("Adding executed_quantity column...")
                await session.execute(text("""
                    ALTER TABLE trades ADD COLUMN executed_quantity INTEGER DEFAULT 0;
                """))
                print("executed_quantity column added")
            else:
                print("executed_quantity column already exists")
            
            await session.commit()
            
        print("Database schema fix completed!")
        
    except Exception as e:
        print(f"Database schema fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Database Schema Fix Script")
    print("=" * 30)
    asyncio.run(fix_schema())