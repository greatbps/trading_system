#!/usr/bin/env python3
"""샘플 데이터 업데이트"""

import sqlite3

def update_sample_data():
    print("Updating sample data...")
    
    # SQLite DB 경로 확인
    try:
        conn = sqlite3.connect("database/trading.db") 
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Available tables:", [t[0] for t in tables])
        
        conn.close()
        print("Database connection successful")
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    update_sample_data()
