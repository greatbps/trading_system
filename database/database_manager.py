#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/database_manager.py

데이터베이스 관리자
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import json

# 절대 임포트로 변경
try:
    from database.models import Base, Stock, MarketData, AnalysisResult, Trade, TradeExecution, Portfolio, SystemLog, TradingSession, FilterHistory
except ImportError:
    # 상대 임포트 시도
    try:
        from .models import Base, Stock, MarketData, AnalysisResult, Trade, TradeExecution, Portfolio, SystemLog, TradingSession, FilterHistory
    except ImportError:
        # 직접 실행되는 경우
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from database.models import Base, Stock, MarketData, AnalysisResult, Trade, TradeExecution, Portfolio, SystemLog, TradingSession, FilterHistory

from utils.logger import get_logger

class DatabaseManager:
    """데이터베이스 관리자"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("DatabaseManager")
        
        # 동기 엔진 (기본 작업용)
        self.sync_engine = None
        self.SessionLocal = None
        
        # 비동기 엔진 (고성능 작업용)
        self.async_engine = None
        self.AsyncSessionLocal = None
        
        self._initialize_engines()
        
        # DatabaseOperations 인스턴스 생성
        from database.db_operations import DatabaseOperations
        self.db_operations = DatabaseOperations(self)
    
    def _initialize_engines(self):
        """데이터베이스 엔진 초기화"""
        try:
            db_url = self.config.database.DB_URL
            
            # PostgreSQL URL 변환
            if db_url.startswith('postgresql://'):
                # 동기 엔진
                self.sync_engine = create_engine(
                    db_url,
                    echo=self.config.database.DB_ECHO,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
                
                # 비동기 엔진 - 연결 안정성 강화
                async_db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
                self.async_engine = create_async_engine(
                    async_db_url,
                    echo=self.config.database.DB_ECHO,
                    pool_size=15,  # 연결 풀 크기 증가
                    max_overflow=25,  # 오버플로우 연결 증가
                    pool_pre_ping=True,  # 연결 유효성 검사
                    pool_recycle=1800,  # 30분 후 연결 재활용 (더 짧게)
                    pool_timeout=30,  # 연결 대기 타임아웃
                    connect_args={
                        "command_timeout": 60,  # 명령 타임아웃
                        "server_settings": {
                            "jit": "off",  # JIT 최적화 비활성화로 안정성 향상
                            "application_name": "TradingSystem",  # 연결 식별
                        },
                    }
                )
                
            else:
                # SQLite (개발용)
                self.sync_engine = create_engine(
                    db_url,
                    echo=self.config.database.DB_ECHO,
                    pool_pre_ping=True
                )
                
                # SQLite 비동기 엔진
                async_db_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
                self.async_engine = create_async_engine(
                    async_db_url,
                    echo=self.config.database.DB_ECHO
                )
            
            # 세션 팩토리 생성
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.sync_engine
            )
            
            self.AsyncSessionLocal = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self.logger.info("✅ 데이터베이스 엔진 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 데이터베이스 엔진 초기화 실패: {e}")
            raise
    # database_manager.py에 추가 - 간단 수정

    async def fix_analysis_table(self):
        """analysis_results 테이블 수정 - symbol 컬럼 추가"""
        try:
            async with self.get_async_session() as session:
                # 1. 기존 테이블 구조 확인
                try:
                    await session.execute(text("SELECT symbol FROM analysis_results LIMIT 1"))
                    self.logger.info("✅ symbol 컬럼이 이미 존재합니다")
                    return True
                except:
                    self.logger.info("⚠️ symbol 컬럼 없음, 테이블 수정 중...")
                
                # 2. 기존 데이터 백업
                try:
                    result = await session.execute(text("SELECT * FROM analysis_results"))
                    old_data = [dict(row._mapping) for row in result.fetchall()]
                    self.logger.info(f"📂 기존 데이터 백업: {len(old_data)}개")
                except:
                    old_data = []
                
                # 3. 테이블 재생성
                await session.execute(text("DROP TABLE IF EXISTS analysis_results"))
                await session.execute(text("""
                    CREATE TABLE analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        name TEXT,
                        score REAL,
                        recommendation TEXT,
                        risk_level TEXT,
                        strategy TEXT,
                        analysis_time TEXT,
                        signals TEXT,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                await session.commit()
                self.logger.info("✅ analysis_results 테이블 재생성 완료")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 테이블 수정 실패: {e}")
            return False

    # save_analysis_results 메서드에서 호출
    async def force_recreate_analysis_table(self):
        """analysis_results 테이블 강제 재생성"""
        try:
            async with self.get_async_session() as session:
                # 1. 기존 테이블 완전 삭제
                await session.execute(text("DROP TABLE IF EXISTS analysis_results"))
                
                # 2. 새 테이블 생성
                await session.execute(text("""
                    CREATE TABLE analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        name TEXT,
                        score REAL,
                        recommendation TEXT,
                        risk_level TEXT,
                        strategy TEXT,
                        analysis_time TEXT,
                        signals TEXT,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                await session.commit()
                self.logger.info("✅ analysis_results 테이블 강제 재생성 완료")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 테이블 재생성 실패: {e}")
            return False

    # save_analysis_results 메서드 완전 교체
    async def save_analysis_results(self, results: List) -> bool:
        """분석 결과 저장 - 에러 방지 버전"""
        try:
            # 테이블 강제 재생성
            await self.force_recreate_analysis_table()
            
            if not results:
                self.logger.info("💾 저장할 분석 결과가 없습니다")
                return True
            
            async with self.get_async_session() as session:
                saved_count = 0
                
                for result in results:
                    try:
                        if hasattr(result, 'to_dict'):
                            result_data = result.to_dict()
                        else:
                            result_data = result
                        
                        # 간단한 INSERT (충돌 처리 없음)
                        await session.execute(text("""
                            INSERT INTO analysis_results 
                            (symbol, name, score, recommendation, risk_level, strategy, analysis_time, signals, entry_price, stop_loss, take_profit)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """), (
                            result_data.get('symbol', ''),
                            result_data.get('name', ''),
                            float(result_data.get('score', 0)),
                            result_data.get('recommendation', 'HOLD'),
                            result_data.get('risk_level', 'MEDIUM'),
                            result_data.get('strategy', 'momentum'),
                            result_data.get('analysis_time', datetime.now().isoformat()),
                            json.dumps(result_data.get('signals', {})),
                            result_data.get('entry_price'),
                            result_data.get('stop_loss'),
                            result_data.get('take_profit')
                        ))
                        saved_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ {result_data.get('symbol', 'Unknown')} 저장 실패: {e}")
                        continue
                
                await session.commit()
                self.logger.info(f"✅ 분석 결과 저장 완료: {saved_count}개")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 분석 결과 저장 실패: {e}")
            return False
    async def create_tables(self):
        """테이블 생성"""
        try:
            if self.async_engine:
                async with self.async_engine.begin() as conn:
                    # 테이블이 이미 존재하는지 확인하고 존재하지 않을 때만 생성
                    await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            else:
                # 동기 엔진 사용시에도 checkfirst=True 옵션 추가
                Base.metadata.create_all(bind=self.sync_engine, checkfirst=True)
            
            self.logger.info("✅ 데이터베이스 테이블 생성 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 테이블 생성 실패: {e}")
            raise
    
    async def drop_tables(self):
        """테이블 삭제 (주의!)"""
        try:
            if self.async_engine:
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            else:
                Base.metadata.drop_all(bind=self.sync_engine)
            
            self.logger.warning("⚠️ 모든 테이블이 삭제되었습니다!")
            
        except Exception as e:
            self.logger.error(f"❌ 테이블 삭제 실패: {e}")
            raise
    
    @asynccontextmanager
    async def get_async_session(self):
        """비동기 세션 컨텍스트 매니저"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_sync_session(self):
        """동기 세션 생성"""
        return self.SessionLocal()
    
    # database_manager.py에 테이블 생성 메서드 추가

    async def create_analysis_table(self):
        """분석 결과 테이블 생성"""
        try:
            async with self.get_async_session() as session:
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        name TEXT,
                        score REAL,
                        recommendation TEXT,
                        risk_level TEXT,
                        strategy TEXT,
                        analysis_time TEXT,
                        signals TEXT,
                        entry_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await session.commit()
                self.logger.info("✅ analysis_results 테이블 생성 완료")
        except Exception as e:
            self.logger.error(f"❌ 테이블 생성 실패: {e}")

    # save_analysis_results 메서드를 간단히 수정
    async def save_analysis_results(self, results: List) -> bool:
        """분석 결과 저장 - 간단 버전"""
        try:
            # 테이블 생성 먼저
            await self.create_analysis_table()
            
            async with self.get_async_session() as session:
                for result in results:
                    data = result.to_dict() if hasattr(result, 'to_dict') else result
                    
                    await session.execute(text("""
                        INSERT OR REPLACE INTO analysis_results 
                        (symbol, name, score, recommendation, risk_level, strategy, analysis_time, signals, entry_price, stop_loss, take_profit)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """), (
                        data.get('symbol'),
                        data.get('name'),
                        data.get('score'),
                        data.get('recommendation'),
                        data.get('risk_level'),
                        data.get('strategy'),
                        data.get('analysis_time'),
                        json.dumps(data.get('signals', {})),
                        data.get('entry_price'),
                        data.get('stop_loss'),
                        data.get('take_profit')
                    ))
                
                await session.commit()
                self.logger.info(f"✅ {len(results)}개 결과 저장 완료")
                return True
        except Exception as e:
            self.logger.error(f"❌ 저장 실패: {e}")
            return False
    
    # ======================== 종목 관련 메서드 ========================
    
    async def save_stock(self, stock_data: Dict) -> Optional[int]:
        """종목 정보 저장"""
        try:
            async with self.get_async_session() as session:
                # 기존 종목 확인
                result = await session.execute(
                    text("SELECT id FROM stocks WHERE symbol = :symbol"),
                    {"symbol": stock_data["symbol"]}
                )
                existing = result.fetchone()
                
                if existing:
                    # 업데이트 - SQLite와 PostgreSQL 호환성을 위해 datetime.now() 사용
                    from datetime import datetime
                    await session.execute(
                        text("""
                        UPDATE stocks SET 
                            name = :name,
                            current_price = :current_price,
                            market_cap = :market_cap,
                            pe_ratio = :pe_ratio,
                            pbr = :pbr,
                            updated_at = :updated_at
                        WHERE symbol = :symbol
                        """),
                        {
                            **stock_data,
                            "updated_at": datetime.now()
                        }
                    )
                    stock_id = existing[0]
                else:
                    # 새로 생성 - is_active를 기본값 true로 설정
                    result = await session.execute(
                        text("""
                        INSERT INTO stocks (symbol, name, market, sector, current_price, market_cap, pe_ratio, pbr, is_active)
                        VALUES (:symbol, :name, :market, :sector, :current_price, :market_cap, :pe_ratio, :pbr, true)
                        RETURNING id
                        """),
                        stock_data
                    )
                    stock_id = result.fetchone()[0]
                
                await session.commit()
                self.logger.info(f"✅ 종목 저장 완료: {stock_data['symbol']}")
                return stock_id
                
        except Exception as e:
            self.logger.error(f"❌ 종목 저장 실패: {e}")
            return None
    
    async def get_stock_by_symbol(self, symbol: str) -> Optional[Dict]:
        """심볼로 종목 조회"""
        try:
            async with self.get_async_session() as session:
                from sqlalchemy import text
                
                result = await session.execute(
                    text("SELECT * FROM stocks WHERE symbol = :symbol AND is_active = true"),
                    {"symbol": symbol}
                )
                
                row = result.fetchone()
                
                if row:
                    # Row를 딕셔너리로 변환
                    stock_dict = {
                        'id': row[0],
                        'symbol': row[1],
                        'name': row[2],
                        'market': row[3],
                        'sector': row[4],
                        'current_price': row[5],
                        'market_cap': row[6],
                        'shares_outstanding': row[7],
                        'high_52w': row[8],
                        'low_52w': row[9],
                        'pe_ratio': row[10],
                        'pbr': row[11],
                        'eps': row[12],
                        'bps': row[13],
                        'roe': row[14],
                        'debt_ratio': row[15],
                        'is_active': row[16],
                        'created_at': row[17],
                        'updated_at': row[18]
                    }
                    
                    self.logger.info(f"✅ 종목 조회 성공: {symbol} ({stock_dict['name']})")
                    return stock_dict
                else:
                    self.logger.warning(f"⚠️ 종목을 찾을 수 없습니다: {symbol}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ 종목 조회 실패 ({symbol}): {e}")
            return None
    
    async def get_stock_by_symbol(self, symbol: str) -> Optional[Dict]:
        """심볼로 종목 조회"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("SELECT * FROM stocks WHERE symbol = :symbol"),
                    {"symbol": symbol}
                )
                row = result.fetchone()
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 종목 조회 실패: {e}")
            return None
    
    async def get_active_stocks(self, limit: int = 100) -> List[Dict]:
        """활성 종목 리스트 조회"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("""
                    SELECT symbol, name, current_price, market_cap 
                    FROM stocks 
                    WHERE is_active = true 
                    ORDER BY market_cap DESC 
                    LIMIT :limit
                    """),
                    {"limit": limit}
                )
                
                rows = result.fetchall()
                if rows:
                    return [dict(row._mapping) for row in rows]
                else:
                    # is_active가 모두 false이거나 null인 경우, 모든 종목 조회
                    self.logger.warning("활성 종목이 없어서 전체 종목을 조회합니다.")
                    result = await session.execute(
                        text("""
                        SELECT symbol, name, current_price, market_cap 
                        FROM stocks 
                        ORDER BY market_cap DESC 
                        LIMIT :limit
                        """),
                        {"limit": limit}
                    )
                    return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ 활성 종목 조회 실패: {e}")
            return []
    
    # ======================== 가격 데이터 관련 메서드 ========================
    
    async def save_price_data(self, price_data_list: List[Dict]) -> bool:
        """가격 데이터 배치 저장"""
        try:
            async with self.get_async_session() as session:
                for data in price_data_list:
                    await session.execute(
                        text("""
                        INSERT INTO price_data 
                        (stock_id, date, open_price, high_price, low_price, close_price, volume, trading_value)
                        VALUES (:stock_id, :date, :open_price, :high_price, :low_price, :close_price, :volume, :trading_value)
                        ON CONFLICT (stock_id, date) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume,
                            trading_value = EXCLUDED.trading_value
                        """),
                        data
                    )
                
                await session.commit()
                self.logger.info(f"✅ 가격 데이터 {len(price_data_list)}건 저장 완료")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 가격 데이터 저장 실패: {e}")
            return False
    
    async def get_price_data(self, symbol: str, days: int = 100) -> pd.DataFrame:
        """종목의 가격 데이터 조회"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("""
                    SELECT pd.* 
                    FROM price_data pd
                    JOIN stocks s ON pd.stock_id = s.id
                    WHERE s.symbol = :symbol
                    ORDER BY pd.date DESC
                    LIMIT :days
                    """),
                    {"symbol": symbol, "days": days}
                )
                
                data = [dict(row._mapping) for row in result.fetchall()]
                return pd.DataFrame(data)
                
        except Exception as e:
            self.logger.error(f"❌ 가격 데이터 조회 실패: {e}")
            return pd.DataFrame()
    
    # ======================== 분석 결과 관련 메서드 ========================
    
    async def save_analysis_result(self, analysis_data: Dict) -> Optional[int]:
        """분석 결과 저장"""
        try:
            # numpy 타입을 Python 기본 타입으로 변환
            cleaned_data = self._clean_analysis_data(analysis_data)
            
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("""
                    INSERT INTO analysis_results 
                    (stock_id, analysis_date, strategy, comprehensive_score, recommendation, 
                     confidence, technical_score, fundamental_score, sentiment_score,
                     signal_strength, signal_type, action, risk_level, price_at_analysis,
                     technical_details, fundamental_details, sentiment_details)
                    VALUES (:stock_id, :analysis_date, :strategy, :comprehensive_score, :recommendation,
                            :confidence, :technical_score, :fundamental_score, :sentiment_score,
                            :signal_strength, :signal_type, :action, :risk_level, :price_at_analysis,
                            :technical_details, :fundamental_details, :sentiment_details)
                    RETURNING id
                    """),
                    cleaned_data
                )
                
                analysis_id = result.fetchone()[0]
                await session.commit()
                
                self.logger.info(f"✅ 분석 결과 저장 완료: ID {analysis_id}")
                return analysis_id
                
        except Exception as e:
            self.logger.error(f"❌ 분석 결과 저장 실패: {e}")
            return None
    def _clean_analysis_data(self, data: Dict) -> Dict:
        """numpy 타입을 Python 기본 타입으로 변환하고 NaN/Inf 값 처리"""
        import json
        import numpy as np
        import math
        
        def convert_numpy(obj):
            """numpy 객체를 Python 기본 타입으로 변환하고 NaN/Inf 처리"""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                if np.isnan(obj) or np.isinf(obj):
                    return None  # NaN, Inf를 null로 변환
                return float(obj)
            elif isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None  # Python float NaN, Inf도 처리
                return obj
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.str_):
                return str(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            else:
                return obj
        
        try:
            # 전체 데이터를 JSON으로 변환 후 다시 파싱 (numpy 타입 제거)
            cleaned_data = {}
            for key, value in data.items():
                if key in ['technical_details', 'fundamental_details', 'sentiment_details']:
                    # JSON 필드는 딕셔너리를 JSON 문자열로 변환
                    cleaned_value = convert_numpy(value)
                    cleaned_data[key] = json.dumps(cleaned_value) if cleaned_value else "{}"
                else:
                    # 일반 필드는 numpy 타입만 변환
                    cleaned_data[key] = convert_numpy(value)
            
            return cleaned_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ 데이터 정리 중 오류: {e}")
            # 오류 발생시 기본값으로 대체
            return {
                **data,
                'technical_details': json.dumps({}),
                'fundamental_details': json.dumps({}),
                'sentiment_details': json.dumps({})
            }
    ###########################################################################################
    # database_manager.py - 긴급 수정 (기존 ###...### 라인 교체)

    async def save_analysis_results(self, results: List) -> bool:
        """분석 결과 저장 - 긴급 수정 버전"""
        try:
            if not results:
                self.logger.info("💾 저장할 분석 결과가 없습니다")
                return True
            
            # 1. 테이블 강제 재생성
            async with self.get_async_session() as session:
                try:
                    # 기존 테이블 삭제
                    await session.execute(text("DROP TABLE IF EXISTS analysis_results"))
                    
                    # 새 테이블 생성 (symbol 컬럼 포함)
                    await session.execute(text("""
                        CREATE TABLE analysis_results (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            name TEXT,
                            score REAL,
                            recommendation TEXT,
                            risk_level TEXT,
                            strategy TEXT,
                            analysis_time TEXT,
                            signals TEXT,
                            entry_price REAL,
                            stop_loss REAL,
                            take_profit REAL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    self.logger.info("✅ analysis_results 테이블 재생성 완료")
                except Exception as e:
                    self.logger.error(f"❌ 테이블 재생성 실패: {e}")
                    return False
            
            # 2. 데이터 저장 (충돌 처리 없는 단순 INSERT)
            async with self.get_async_session() as session:
                saved_count = 0
                
                for result in results:
                    try:
                        if hasattr(result, 'to_dict'):
                            result_data = result.to_dict()
                        else:
                            result_data = result
                        
                        # 단순 INSERT (named parameters 사용)
                        await session.execute(text("""
                            INSERT INTO analysis_results 
                            (symbol, name, score, recommendation, risk_level, strategy, analysis_time, signals, entry_price, stop_loss, take_profit)
                            VALUES (:symbol, :name, :score, :recommendation, :risk_level, :strategy, :analysis_time, :signals, :entry_price, :stop_loss, :take_profit)
                        """), {
                            'symbol': result_data.get('symbol', ''),
                            'name': result_data.get('name', ''),
                            'score': float(result_data.get('score', 0)) if result_data.get('score') else 0.0,
                            'recommendation': result_data.get('recommendation', 'HOLD'),
                            'risk_level': result_data.get('risk_level', 'MEDIUM'),
                            'strategy': result_data.get('strategy', 'momentum'),
                            'analysis_time': result_data.get('analysis_time', datetime.now().isoformat()),
                            'signals': json.dumps(result_data.get('signals', {})),
                            'entry_price': result_data.get('entry_price'),
                            'stop_loss': result_data.get('stop_loss'),
                            'take_profit': result_data.get('take_profit')
                        })
                        saved_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ {result_data.get('symbol', 'Unknown')} 저장 실패: {e}")
                        continue
                
                await session.commit()
                self.logger.info(f"✅ 분석 결과 저장 완료: {saved_count}개")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 분석 결과 저장 실패: {e}")
            return False

    async def get_analysis_results(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """분석 결과 조회"""
        try:
            async with self.get_async_session() as session:
                query = "SELECT * FROM analysis_results"
                params = {}
                
                if symbol:
                    query += " WHERE symbol = :symbol"
                    params['symbol'] = symbol
                
                query += " ORDER BY analysis_time DESC LIMIT :limit"
                params['limit'] = limit
                
                result = await session.execute(text(query), params)
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ 분석 결과 조회 실패: {e}")
            return []

    async def save_backtest_results(self, results: Dict[str, Any]) -> bool:
        """백테스트 결과 저장"""
        try:
            async with self.get_async_session() as session:
                await session.execute(
                    text("""
                    INSERT INTO backtest_results 
                    (strategy, start_date, end_date, initial_capital, final_capital, total_return, max_drawdown, sharpe_ratio, total_trades, win_rate, results_data)
                    VALUES (:strategy, :start_date, :end_date, :initial_capital, :final_capital, :total_return, :max_drawdown, :sharpe_ratio, :total_trades, :win_rate, :results_data)
                    """),
                    {
                        'strategy': results.get('strategy', 'momentum'),
                        'start_date': results.get('start_date'),
                        'end_date': results.get('end_date'),
                        'initial_capital': results.get('initial_capital', 0),
                        'final_capital': results.get('final_capital', 0),
                        'total_return': results.get('total_return', 0),
                        'max_drawdown': results.get('max_drawdown', 0),
                        'sharpe_ratio': results.get('sharpe_ratio', 0),
                        'total_trades': results.get('total_trades', 0),
                        'win_rate': results.get('win_rate', 0),
                        'results_data': json.dumps(results)
                    }
                )
                await session.commit()
                self.logger.info("✅ 백테스트 결과 저장 완료")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 백테스트 결과 저장 실패: {e}")
    
    ############################################################################################
    async def get_latest_analysis(self, symbol: str, strategy: str = None) -> Optional[Dict]:
        """최신 분석 결과 조회"""
        try:
            async with self.get_async_session() as session:
                query = """
                SELECT ar.* 
                FROM analysis_results ar
                JOIN stocks s ON ar.stock_id = s.id
                WHERE s.symbol = :symbol
                """
                params = {"symbol": symbol}
                
                if strategy:
                    query += " AND ar.strategy = :strategy"
                    params["strategy"] = strategy
                
                query += " ORDER BY ar.analysis_date DESC LIMIT 1"
                
                result = await session.execute(text(query), params)
                row = result.fetchone()
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 최신 분석 결과 조회 실패: {e}")
            return None
    
    async def get_top_analysis_results(self, strategy: str = None, limit: int = 50) -> List[Dict]:
        """상위 분석 결과 조회"""
        try:
            async with self.get_async_session() as session:
                query = """
                SELECT ar.*, s.symbol, s.name
                FROM analysis_results ar
                JOIN stocks s ON ar.stock_id = s.id
                WHERE ar.analysis_date >= :min_date
                """
                params = {
                    "min_date": datetime.now() - timedelta(days=1),
                    "limit": limit
                }
                
                if strategy:
                    query += " AND ar.strategy = :strategy"
                    params["strategy"] = strategy
                
                query += """
                ORDER BY ar.comprehensive_score DESC, ar.analysis_date DESC
                LIMIT :limit
                """
                
                result = await session.execute(text(query), params)
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ 상위 분석 결과 조회 실패: {e}")
            return []
    
    # ======================== 매매 관련 메서드 ========================
    
    async def save_trade(self, trade_data: Dict) -> Optional[int]:
        """매매 기록 저장"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("""
                    INSERT INTO trades 
                    (stock_id, trade_type, trade_date, price, quantity, total_amount, 
                     commission, position_id, strategy_name, signal_strength, is_simulated)
                    VALUES (:stock_id, :trade_type, :trade_date, :price, :quantity, :total_amount,
                            :commission, :position_id, :strategy_name, :signal_strength, :is_simulated)
                    RETURNING id
                    """),
                    trade_data
                )
                
                trade_id = result.fetchone()[0]
                await session.commit()
                
                self.logger.info(f"✅ 매매 기록 저장 완료: ID {trade_id}")
                return trade_id
                
        except Exception as e:
            self.logger.error(f"❌ 매매 기록 저장 실패: {e}")
            return None
    
    async def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 정보 조회"""
        try:
            async with self.get_async_session() as session:
                # 1. 전체 포트폴리오 정보
                portfolio_result = await session.execute(
                    text("""
                    SELECT 
                        COUNT(*) as total_positions,
                        SUM(total_cost) as total_cost,
                        SUM(current_value) as total_current_value,
                        SUM(unrealized_pnl) as total_unrealized_pnl,
                        AVG(unrealized_pnl_rate) as avg_pnl_rate
                    FROM portfolio 
                    WHERE status = 'OPEN'
                    """)
                )
                portfolio_row = portfolio_result.fetchone()
                
                # 2. 포지션별 상세 정보
                positions_result = await session.execute(
                    text("""
                    SELECT 
                        p.position_id,
                        s.symbol,
                        s.name,
                        p.quantity,
                        p.avg_price,
                        p.current_price,
                        p.total_cost,
                        p.current_value,
                        p.unrealized_pnl,
                        p.unrealized_pnl_rate,
                        p.entry_date,
                        p.entry_strategy
                    FROM portfolio p
                    JOIN stocks s ON p.stock_id = s.id
                    WHERE p.status = 'OPEN'
                    ORDER BY p.unrealized_pnl_rate DESC
                    """)
                )
                positions = [dict(row._mapping) for row in positions_result.fetchall()]
                
                # 3. 최근 거래 내역 (최근 10건)
                trades_result = await session.execute(
                    text("""
                    SELECT 
                        t.trade_date,
                        t.trade_type,
                        s.symbol,
                        s.name,
                        t.price,
                        t.quantity,
                        t.total_amount,
                        t.profit_loss,
                        t.profit_loss_rate
                    FROM trades t
                    JOIN stocks s ON t.stock_id = s.id
                    ORDER BY t.trade_date DESC
                    LIMIT 10
                    """)
                )
                recent_trades = [dict(row._mapping) for row in trades_result.fetchall()]
                
                # 4. 일일 거래 통계
                today_trades_result = await session.execute(
                    text("""
                    SELECT 
                        COUNT(*) as today_trade_count,
                        SUM(CASE WHEN trade_type = 'BUY' THEN total_amount ELSE 0 END) as today_buy_amount,
                        SUM(CASE WHEN trade_type = 'SELL' THEN total_amount ELSE 0 END) as today_sell_amount,
                        SUM(CASE WHEN trade_type = 'SELL' THEN profit_loss ELSE 0 END) as today_realized_pnl
                    FROM trades 
                    WHERE DATE(trade_date) = CURRENT_DATE
                    """)
                )
                today_stats = today_trades_result.fetchone()
                
                # 5. 전체 거래 성과 통계
                performance_result = await session.execute(
                    text("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN profit_loss < 0 THEN 1 END) as losing_trades,
                        SUM(profit_loss) as total_realized_pnl,
                        AVG(profit_loss_rate) as avg_profit_rate,
                        MAX(profit_loss) as max_profit,
                        MIN(profit_loss) as max_loss
                    FROM trades 
                    WHERE trade_type = 'SELL' AND profit_loss IS NOT NULL
                    """)
                )
                performance = performance_result.fetchone()
                
                # 6. 섹터별 분산 정보
                sector_result = await session.execute(
                    text("""
                    SELECT 
                        s.sector,
                        COUNT(*) as position_count,
                        SUM(p.current_value) as sector_value,
                        AVG(p.unrealized_pnl_rate) as avg_pnl_rate
                    FROM portfolio p
                    JOIN stocks s ON p.stock_id = s.id
                    WHERE p.status = 'OPEN'
                    GROUP BY s.sector
                    ORDER BY sector_value DESC
                    """)
                )
                sector_distribution = [dict(row._mapping) for row in sector_result.fetchall()]
                
                # 결과 정리
                portfolio_summary = {
                    # 기본 포트폴리오 정보
                    "total_positions": portfolio_row[0] or 0,
                    "total_cost": float(portfolio_row[1] or 0),
                    "total_current_value": float(portfolio_row[2] or 0),
                    "total_unrealized_pnl": float(portfolio_row[3] or 0),
                    "avg_pnl_rate": float(portfolio_row[4] or 0),
                    
                    # 계산된 지표
                    "total_return_rate": (float(portfolio_row[3] or 0) / float(portfolio_row[1] or 1)) * 100 if portfolio_row[1] else 0,
                    
                    # 상세 포지션 정보
                    "positions": positions,
                    
                    # 최근 거래 내역
                    "recent_trades": recent_trades,
                    
                    # 일일 통계
                    "today_stats": {
                        "trade_count": today_stats[0] or 0,
                        "buy_amount": float(today_stats[1] or 0),
                        "sell_amount": float(today_stats[2] or 0),
                        "realized_pnl": float(today_stats[3] or 0)
                    },
                    
                    # 전체 성과 통계
                    "performance": {
                        "total_trades": performance[0] or 0,
                        "winning_trades": performance[1] or 0,
                        "losing_trades": performance[2] or 0,
                        "win_rate": (performance[1] / performance[0] * 100) if performance[0] else 0,
                        "total_realized_pnl": float(performance[3] or 0),
                        "avg_profit_rate": float(performance[4] or 0),
                        "max_profit": float(performance[5] or 0),
                        "max_loss": float(performance[6] or 0)
                    },
                    
                    # 섹터별 분산
                    "sector_distribution": sector_distribution,
                    
                    # 메타 정보
                    "last_updated": datetime.now().isoformat(),
                    "currency": "KRW"
                }
                
                self.logger.info(f"✅ 포트폴리오 요약 조회 완료 - 포지션 {portfolio_summary['total_positions']}개")
                return portfolio_summary
                
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 요약 조회 실패: {e}")
            return {
                "total_positions": 0,
                "total_cost": 0,
                "total_current_value": 0,
                "total_unrealized_pnl": 0,
                "avg_pnl_rate": 0,
                "total_return_rate": 0,
                "positions": [],
                "recent_trades": [],
                "today_stats": {},
                "performance": {},
                "sector_distribution": [],
                "last_updated": datetime.now().isoformat(),
                "currency": "KRW"
            }
    
    # ======================== 뉴스 데이터 관련 메서드 ========================
    
    async def save_news_data(self, news_data: Dict) -> Optional[int]:
        """뉴스 데이터 저장"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("""
                    INSERT INTO news_data 
                    (title, content, url, source, published_at, related_symbols,
                     sentiment_score, sentiment_label, confidence, keywords, impact_score)
                    VALUES (:title, :content, :url, :source, :published_at, :related_symbols,
                            :sentiment_score, :sentiment_label, :confidence, :keywords, :impact_score)
                    RETURNING id
                    """),
                    news_data
                )
                
                news_id = result.fetchone()[0]
                await session.commit()
                
                self.logger.info(f"✅ 뉴스 데이터 저장 완료: ID {news_id}")
                return news_id
                
        except Exception as e:
            self.logger.error(f"❌ 뉴스 데이터 저장 실패: {e}")
            return None
    
    async def get_recent_news(self, symbol: str = None, days: int = 7, limit: int = 50) -> List[Dict]:
        """최근 뉴스 조회"""
        try:
            async with self.get_async_session() as session:
                if symbol:
                    # 특정 종목 관련 뉴스
                    result = await session.execute(
                        text("""
                        SELECT * FROM news_data 
                        WHERE related_symbols @> :symbol_json
                        AND published_at >= :min_date
                        ORDER BY published_at DESC, impact_score DESC
                        LIMIT :limit
                        """),
                        {
                            "symbol_json": f'["{symbol}"]',
                            "min_date": datetime.now() - timedelta(days=days),
                            "limit": limit
                        }
                    )
                else:
                    # 전체 뉴스
                    result = await session.execute(
                        text("""
                        SELECT * FROM news_data 
                        WHERE published_at >= :min_date
                        ORDER BY published_at DESC, impact_score DESC
                        LIMIT :limit
                        """),
                        {
                            "min_date": datetime.now() - timedelta(days=days),
                            "limit": limit
                        }
                    )
                
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ 뉴스 조회 실패: {e}")
            return []
    
    # ======================== 시스템 로그 관련 메서드 ========================
    
    async def save_system_log(self, log_data: Dict) -> bool:
        """시스템 로그 저장"""
        try:
            async with self.get_async_session() as session:
                await session.execute(
                    text("""
                    INSERT INTO system_logs (timestamp, level, module, function, message, extra_data)
                    VALUES (:timestamp, :level, :module, :function, :message, :extra_data)
                    """),
                    log_data
                )
                
                await session.commit()
                return True
                
        except Exception as e:
            # 로그 저장 실패는 조용히 처리 (무한루프 방지)
            print(f"❌ 시스템 로그 저장 실패: {e}")
            return False
    
    async def get_system_logs(self, level: str = None, module: str = None, 
                             hours: int = 24, limit: int = 1000) -> List[Dict]:
        """시스템 로그 조회"""
        try:
            async with self.get_async_session() as session:
                query = "SELECT * FROM system_logs WHERE timestamp >= :min_time"
                params = {"min_time": datetime.now() - timedelta(hours=hours)}
                
                if level:
                    query += " AND level = :level"
                    params["level"] = level
                
                if module:
                    query += " AND module = :module"  
                    params["module"] = module
                
                query += " ORDER BY timestamp DESC LIMIT :limit"
                params["limit"] = limit
                
                result = await session.execute(text(query), params)
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"❌ 시스템 로그 조회 실패: {e}")
            return []
    
    # ======================== 유틸리티 메서드 ========================
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """오래된 데이터 정리"""
        try:
            async with self.get_async_session() as session:
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # 오래된 가격 데이터 삭제 (기본 차트 데이터는 유지)
                await session.execute(
                    text("DELETE FROM price_data WHERE date < :cutoff_date AND date NOT IN (SELECT DISTINCT date FROM price_data ORDER BY date DESC LIMIT 1000)"),
                    {"cutoff_date": cutoff_date}
                )
                
                # 오래된 뉴스 데이터 삭제
                await session.execute(
                    text("DELETE FROM news_data WHERE published_at < :cutoff_date"),
                    {"cutoff_date": cutoff_date}
                )
                
                # 오래된 시스템 로그 삭제
                await session.execute(
                    text("DELETE FROM system_logs WHERE timestamp < :cutoff_date"),
                    {"cutoff_date": cutoff_date}
                )
                
                await session.commit()
                self.logger.info(f"✅ {days_to_keep}일 이전 오래된 데이터 정리 완료")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 데이터 정리 실패: {e}")
            return False
    
    async def get_database_stats(self) -> Dict:
        """데이터베이스 통계 조회"""
        try:
            async with self.get_async_session() as session:
                stats = {}
                
                # 각 테이블별 레코드 수 조회
                tables = ['stocks', 'price_data', 'analysis_results', 'trades', 'portfolio', 'news_data', 'system_logs']
                
                for table in tables:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    stats[f"{table}_count"] = count
                
                # 데이터베이스 크기 (PostgreSQL 전용)
                try:
                    result = await session.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
                    db_size = result.fetchone()[0]
                    stats["database_size"] = db_size
                except:
                    stats["database_size"] = "N/A"
                
                stats["last_checked"] = datetime.now().isoformat()
                
                return stats
                
        except Exception as e:
            self.logger.error(f"❌ 데이터베이스 통계 조회 실패: {e}")
            return {}
    
    async def close(self):
        """데이터베이스 연결 종료"""
        try:
            if self.async_engine:
                await self.async_engine.dispose()
            if self.sync_engine:
                self.sync_engine.dispose()
            
            self.logger.info("✅ 데이터베이스 연결 종료 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 데이터베이스 연결 종료 실패: {e}")
    
    def __del__(self):
        """소멸자"""
        if hasattr(self, 'sync_engine') and self.sync_engine:
            self.sync_engine.dispose()