#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 분석 캐싱 테이블 생성 스크립트 (PostgreSQL)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database.models import Base, NewsAnalysisSession, StockNewsAnalysis, NewsArticle
from config import DatabaseConfig

def create_news_caching_tables():
    """뉴스 분석 캐싱 테이블 생성 (PostgreSQL)"""
    try:
        # PostgreSQL 엔진 생성
        engine = create_engine(
            DatabaseConfig.DB_URL,
            echo=True,
            connect_args={
                "options": "-c timezone=Asia/Seoul"
            }
        )
        
        print("PostgreSQL 뉴스 분석 캐싱 테이블 생성 중...")
        
        # 새로운 테이블들만 생성
        with engine.begin() as conn:
            # NewsPeriodType ENUM 생성
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'newsperiodtype') THEN
                        CREATE TYPE newsperiodtype AS ENUM ('SHORT_TERM', 'MID_TERM', 'LONG_TERM', 'NEUTRAL');
                    END IF;
                END $$;
            """))
            
            # AnalysisSessionType ENUM 생성  
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analysissessiontype') THEN
                        CREATE TYPE analysissessiontype AS ENUM ('COMPREHENSIVE', 'NEWS_ONLY', 'SUPPLY_DEMAND', 'TECHNICAL', 'FUNDAMENTAL');
                    END IF;
                END $$;
            """))
            
            # 뉴스 분석 세션 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS news_analysis_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL UNIQUE,
                    analysis_type analysissessiontype NOT NULL,
                    total_stocks INTEGER NOT NULL DEFAULT 0,
                    analyzed_stocks INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMP WITH TIME ZONE
                );
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_session_created ON news_analysis_sessions (created_at);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_session_status ON news_analysis_sessions (status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_session_session_id ON news_analysis_sessions (session_id);"))
            
            # 종목별 뉴스 분석 결과 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS stock_news_analysis (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL REFERENCES news_analysis_sessions(session_id),
                    symbol VARCHAR(10) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    total_news_count INTEGER NOT NULL DEFAULT 0,
                    short_term_score REAL NOT NULL DEFAULT 0.0,
                    short_term_count INTEGER NOT NULL DEFAULT 0,
                    short_term_weight REAL NOT NULL DEFAULT 0.0,
                    mid_term_score REAL NOT NULL DEFAULT 0.0,
                    mid_term_count INTEGER NOT NULL DEFAULT 0,
                    mid_term_weight REAL NOT NULL DEFAULT 0.0,
                    long_term_score REAL NOT NULL DEFAULT 0.0,
                    long_term_count INTEGER NOT NULL DEFAULT 0,
                    long_term_weight REAL NOT NULL DEFAULT 0.0,
                    final_news_score REAL NOT NULL DEFAULT 0.0,
                    sentiment_score REAL,
                    positive_keywords TEXT,
                    negative_keywords TEXT,
                    neutral_keywords TEXT,
                    news_summary TEXT,
                    analyzed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_news_symbol ON stock_news_analysis (symbol);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_news_analyzed ON stock_news_analysis (analyzed_at);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_news_expires ON stock_news_analysis (expires_at);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_news_symbol_session ON stock_news_analysis (symbol, session_id);"))
            
            # 개별 뉴스 기사 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id SERIAL PRIMARY KEY,
                    stock_analysis_id INTEGER NOT NULL REFERENCES stock_news_analysis(id) ON DELETE CASCADE,
                    news_id VARCHAR(100) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    content TEXT,
                    period_type newsperiodtype NOT NULL,
                    base_score REAL NOT NULL DEFAULT 0.0,
                    weighted_score REAL NOT NULL DEFAULT 0.0,
                    matched_keywords TEXT,
                    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    source VARCHAR(100),
                    url VARCHAR(500),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """))
            
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_article_stock_analysis ON news_articles (stock_analysis_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_article_published ON news_articles (published_at);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_article_period ON news_articles (period_type);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_news_article_news_id ON news_articles (news_id);"))
            
            print("뉴스 분석 캐싱 테이블 생성 완료")
            
            # 테이블 구조 확인
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%news%';
            """))
            tables = result.fetchall()
            print(f"생성된 뉴스 테이블: {[table[0] for table in tables]}")
            
            # ENUM 타입 확인
            result = conn.execute(text("""
                SELECT typname FROM pg_type 
                WHERE typname IN ('newsperiodtype', 'analysissessiontype');
            """))
            enums = result.fetchall()
            print(f"생성된 ENUM 타입: {[enum[0] for enum in enums]}")
            
    except Exception as e:
        print(f"테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    create_news_caching_tables()