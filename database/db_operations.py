#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/database/db_operations.py

데이터베이스 조회 및 관리 작업들
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import text

from utils.logger import get_logger

class DatabaseOperations:
    """데이터베이스 조회 및 관리 작업 클래스"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = get_logger("DatabaseOperations")
    
    async def get_status_report(self) -> Dict:
        """데이터베이스 상태 보고서 생성"""
        try:
            self.logger.info("🗄️ 데이터베이스 상태 확인 중...")
            
            report = {
                "connection_status": "disconnected",
                "table_stats": {},
                "recent_analysis": [],
                "portfolio_summary": {},
                "system_logs_summary": {},
                "database_size": "N/A",
                "last_updated": datetime.now().isoformat()
            }
            
            # 1. 연결 테스트
            try:
                await self.db_manager.create_tables()
                report["connection_status"] = "connected"
                self.logger.info("✅ 데이터베이스 연결 정상")
            except Exception as e:
                self.logger.error(f"❌ 데이터베이스 연결 실패: {e}")
                report["connection_status"] = f"error: {str(e)}"
                return report
            
            # 2. 테이블 통계
            stats = await self.db_manager.get_database_stats()
            report["table_stats"] = stats
            
            # 3. 최근 분석 결과
            recent_analysis = await self.db_manager.get_top_analysis_results(limit=5)
            report["recent_analysis"] = recent_analysis
            
            # 4. 포트폴리오 요약
            portfolio = await self.db_manager.get_portfolio_summary()
            report["portfolio_summary"] = portfolio
            
            # 5. 시스템 로그 요약
            recent_logs = await self.db_manager.get_system_logs(hours=24, limit=100)
            if recent_logs:
                error_count = len([log for log in recent_logs if log['level'] == 'ERROR'])
                warning_count = len([log for log in recent_logs if log['level'] == 'WARNING'])
                info_count = len(recent_logs) - error_count - warning_count
                
                report["system_logs_summary"] = {
                    "total_logs": len(recent_logs),
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "info_count": info_count
                }
            
            self.logger.info("✅ 데이터베이스 상태 보고서 생성 완료")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ 상태 보고서 생성 실패: {e}")
            return {"error": str(e)}
    
    def print_status_report(self, report: Dict):
        """상태 보고서 출력"""
        self.logger.info("="*60)
        self.logger.info("📊 데이터베이스 상태 보고서")
        self.logger.info("="*60)
        
        # 연결 상태
        status = report.get("connection_status", "unknown")
        if status == "connected":
            self.logger.info("🔗 연결 상태: ✅ 정상")
        else:
            self.logger.error(f"🔗 연결 상태: ❌ {status}")
            return
        
        # 테이블 통계
        stats = report.get("table_stats", {})
        if stats:
            self.logger.info("\n📋 테이블별 레코드 수:")
            self.logger.info(f"  📈 종목(stocks): {stats.get('stocks_count', 0):,}개")
            self.logger.info(f"  💹 가격데이터(price_data): {stats.get('price_data_count', 0):,}개")
            self.logger.info(f"  🔍 분석결과(analysis_results): {stats.get('analysis_results_count', 0):,}개")
            self.logger.info(f"  💰 거래기록(trades): {stats.get('trades_count', 0):,}개")
            self.logger.info(f"  📊 포트폴리오(portfolio): {stats.get('portfolio_count', 0):,}개")
            self.logger.info(f"  📰 뉴스(news_data): {stats.get('news_data_count', 0):,}개")
            self.logger.info(f"  📝 시스템로그(system_logs): {stats.get('system_logs_count', 0):,}개")
            
            if 'database_size' in stats:
                self.logger.info(f"💾 데이터베이스 크기: {stats['database_size']}")
        
        # 최근 분석 결과
        recent_analysis = report.get("recent_analysis", [])
        if recent_analysis:
            self.logger.info(f"\n🏆 최근 상위 분석 결과 ({len(recent_analysis)}개):")
            for i, analysis in enumerate(recent_analysis, 1):
                self.logger.info(f"  {i}. {analysis['symbol']} ({analysis['name']}) - "
                              f"점수: {analysis['comprehensive_score']:.1f}, "
                              f"추천: {analysis['recommendation']}")
        
        # 포트폴리오 요약
        portfolio = report.get("portfolio_summary", {})
        if portfolio and portfolio.get('total_positions', 0) > 0:
            self.logger.info(f"\n💼 포트폴리오 현황:")
            self.logger.info(f"  활성 포지션: {portfolio['total_positions']}개")
            self.logger.info(f"  총 투자금액: {portfolio['total_cost']:,.0f}원")
            self.logger.info(f"  현재 평가금액: {portfolio['total_current_value']:,.0f}원")
            self.logger.info(f"  평가손익: {portfolio['total_unrealized_pnl']:+,.0f}원 ({portfolio.get('total_return_rate', 0):+.2f}%)")
        else:
            self.logger.info(f"\n💼 포트폴리오: 활성 포지션 없음")
        
        # 시스템 로그 요약
        logs_summary = report.get("system_logs_summary", {})
        if logs_summary:
            self.logger.info(f"\n📝 최근 24시간 로그 요약:")
            self.logger.info(f"  총 로그: {logs_summary['total_logs']}건")
            self.logger.info(f"  ❌ ERROR: {logs_summary['error_count']}건")
            self.logger.info(f"  ⚠️ WARNING: {logs_summary['warning_count']}건")
            self.logger.info(f"  ℹ️ INFO: {logs_summary['info_count']}건")
            
            if logs_summary['error_count'] > 0:
                self.logger.warning("⚠️ 오류 로그가 발견되었습니다.")
        
        self.logger.info("="*60)
    
    async def get_stocks_report(self, limit: int = 50, symbols: List[str] = None) -> Dict:
        """종목 데이터 보고서 생성"""
        try:
            self.logger.info("📈 종목 데이터 조회 중...")
            
            report = {
                "active_stocks": [],
                "stock_details": [],
                "top_market_cap": [],
                "total_count": 0
            }
            
            # 1. 활성 종목 리스트
            active_stocks = await self.db_manager.get_active_stocks(limit=limit)
            report["active_stocks"] = active_stocks
            report["total_count"] = len(active_stocks)
            
            # 2. 특정 종목 상세 정보
            if symbols:
                stock_details = []
                for symbol in symbols:
                    stock_info = await self.db_manager.get_stock_by_symbol(symbol)
                    if stock_info:
                        # 최근 분석 결과 추가
                        latest_analysis = await self.db_manager.get_latest_analysis(symbol)
                        stock_info['latest_analysis'] = latest_analysis
                        stock_details.append(stock_info)
                
                report["stock_details"] = stock_details
            
            # 3. 시가총액 상위 종목
            top_market_cap = sorted(
                [stock for stock in active_stocks if stock.get('market_cap')],
                key=lambda x: x['market_cap'],
                reverse=True
            )[:10]
            report["top_market_cap"] = top_market_cap
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ 종목 보고서 생성 실패: {e}")
            return {"error": str(e)}
    
    def print_stocks_report(self, report: Dict):
        """종목 보고서 출력"""
        self.logger.info("="*60)
        self.logger.info("📊 종목 데이터 보고서")
        self.logger.info("="*60)
        
        if "error" in report:
            self.logger.error(f"❌ 오류: {report['error']}")
            return
        
        # 1. 활성 종목 리스트
        active_stocks = report.get("active_stocks", [])
        if active_stocks:
            self.logger.info(f"📈 활성 종목 리스트 (상위 {len(active_stocks)}개):")
            self.logger.info("-" * 80)
            self.logger.info(f"{'순번':<4} {'종목코드':<8} {'종목명':<20} {'현재가':<12} {'시가총액':<15}")
            self.logger.info("-" * 80)
            
            for i, stock in enumerate(active_stocks, 1):
                current_price = f"{stock['current_price']:,}원" if stock['current_price'] else "N/A"
                market_cap = f"{stock['market_cap']:,}억" if stock['market_cap'] else "N/A"
                
                self.logger.info(f"{i:<4} {stock['symbol']:<8} {stock['name']:<20} {current_price:<12} {market_cap:<15}")
            
            self.logger.info("-" * 80)
        
        # 2. 특정 종목 상세 정보
        stock_details = report.get("stock_details", [])
        if stock_details:
            self.logger.info(f"\n🔍 종목 상세 정보:")
            for stock in stock_details:
                self.logger.info(f"\n📊 {stock['symbol']} ({stock['name']}) 상세:")
                self.logger.info(f"  🏢 시장: {stock.get('market', 'N/A')}")
                self.logger.info(f"  🏭 섹터: {stock.get('sector', 'N/A')}")
                self.logger.info(f"  💰 현재가: {stock['current_price']:,}원" if stock['current_price'] else "  💰 현재가: N/A")
                self.logger.info(f"  💼 시가총액: {stock['market_cap']:,}억원" if stock['market_cap'] else "  💼 시가총액: N/A")
                self.logger.info(f"  📊 PER: {stock['pe_ratio']:.2f}" if stock.get('pe_ratio') else "  📊 PER: N/A")
                self.logger.info(f"  📊 PBR: {stock['pbr']:.2f}" if stock.get('pbr') else "  📊 PBR: N/A")
                
                # 최근 분석 결과
                latest_analysis = stock.get('latest_analysis')
                if latest_analysis:
                    self.logger.info(f"  🔍 최근 분석:")
                    self.logger.info(f"    점수: {latest_analysis['comprehensive_score']:.1f}/100")
                    self.logger.info(f"    추천: {latest_analysis['recommendation']}")
                    self.logger.info(f"    전략: {latest_analysis['strategy']}")
                else:
                    self.logger.info(f"  🔍 최근 분석: 없음")
        
        # 3. 시가총액 상위 종목
        top_market_cap = report.get("top_market_cap", [])
        if top_market_cap:
            self.logger.info(f"\n💎 시가총액 상위 종목:")
            self.logger.info("-" * 60)
            for i, stock in enumerate(top_market_cap, 1):
                self.logger.info(f"  {i:2d}. {stock['symbol']} ({stock['name']}) - {stock['market_cap']:,}억원")
        
        self.logger.info("="*60)
    
    async def get_analysis_report(self, strategy: str = None, limit: int = 50, symbols: List[str] = None) -> Dict:
        """분석 결과 보고서 생성"""
        try:
            self.logger.info("🔍 분석 결과 조회 중...")
            
            report = {
                "recent_analysis": [],
                "statistics": {},
                "buy_recommendations": [],
                "high_score_stocks": [],
                "symbol_analysis": {}
            }
            
            # 1. 최근 분석 결과
            recent_analysis = await self.db_manager.get_top_analysis_results(
                strategy=strategy, limit=limit
            )
            report["recent_analysis"] = recent_analysis
            
            if recent_analysis:
                # 2. 통계 계산
                scores = [a['comprehensive_score'] for a in recent_analysis]
                
                # 추천 분포
                recommendations = {}
                for analysis in recent_analysis:
                    rec = analysis['recommendation']
                    recommendations[rec] = recommendations.get(rec, 0) + 1
                
                # 전략별 분포
                strategies = {}
                for analysis in recent_analysis:
                    strat = analysis['strategy']
                    strategies[strat] = strategies.get(strat, 0) + 1
                
                report["statistics"] = {
                    "total_count": len(recent_analysis),
                    "avg_score": sum(scores) / len(scores),
                    "max_score": max(scores),
                    "min_score": min(scores),
                    "recommendations": recommendations,
                    "strategies": strategies
                }
                
                # 3. 매수 추천 종목
                buy_recommendations = [a for a in recent_analysis if a['recommendation'] in ['BUY', 'STRONG_BUY']]
                report["buy_recommendations"] = buy_recommendations
                
                # 4. 고득점 종목 (80점 이상)
                high_score_stocks = [a for a in recent_analysis if a['comprehensive_score'] >= 80]
                report["high_score_stocks"] = high_score_stocks
            
            # 5. 특정 종목 분석 이력
            if symbols:
                symbol_analysis = {}
                for symbol in symbols:
                    async with self.db_manager.get_async_session() as session:
                        result = await session.execute(
                            text("""
                            SELECT ar.*, s.name
                            FROM analysis_results ar
                            JOIN stocks s ON ar.stock_id = s.id
                            WHERE s.symbol = :symbol
                            ORDER BY ar.analysis_date DESC
                            LIMIT 10
                            """),
                            {"symbol": symbol}
                        )
                        
                        symbol_data = [dict(row._mapping) for row in result.fetchall()]
                        symbol_analysis[symbol] = symbol_data
                
                report["symbol_analysis"] = symbol_analysis
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ 분석 보고서 생성 실패: {e}")
            return {"error": str(e)}
    
    def print_analysis_report(self, report: Dict):
        """분석 보고서 출력"""
        self.logger.info("="*60)
        self.logger.info("📊 분석 결과 보고서")
        self.logger.info("="*60)
        
        if "error" in report:
            self.logger.error(f"❌ 오류: {report['error']}")
            return
        
        recent_analysis = report.get("recent_analysis", [])
        
        if recent_analysis:
            # 1. 최근 분석 결과
            self.logger.info(f"📈 최근 분석 결과 ({len(recent_analysis)}건):")
            self.logger.info("-" * 100)
            self.logger.info(f"{'순위':<4} {'종목코드':<8} {'종목명':<15} {'점수':<6} {'추천':<12} {'신뢰도':<8} {'전략':<12} {'분석일시':<19}")
            self.logger.info("-" * 100)
            
            for i, analysis in enumerate(recent_analysis, 1):
                analysis_date = analysis['analysis_date'].strftime('%Y-%m-%d %H:%M') if analysis['analysis_date'] else 'N/A'
                
                self.logger.info(f"{i:<4} {analysis['symbol']:<8} {analysis['name']:<15} "
                              f"{analysis['comprehensive_score']:<6.1f} {analysis['recommendation']:<12} "
                              f"{analysis['confidence']:<8.2f} {analysis['strategy']:<12} {analysis_date:<19}")
            
            self.logger.info("-" * 100)
            
            # 2. 통계
            stats = report.get("statistics", {})
            if stats:
                self.logger.info(f"\n📊 분석 통계:")
                self.logger.info(f"  📈 평균 점수: {stats['avg_score']:.1f}")
                self.logger.info(f"  📈 최고 점수: {stats['max_score']:.1f}")
                self.logger.info(f"  📉 최저 점수: {stats['min_score']:.1f}")
                
                # 추천 분포
                recommendations = stats.get("recommendations", {})
                if recommendations:
                    self.logger.info(f"  💡 추천 분포:")
                    for rec, count in recommendations.items():
                        percentage = (count / stats['total_count']) * 100
                        self.logger.info(f"    {rec}: {count}건 ({percentage:.1f}%)")
            
            # 3. 매수 추천 종목
            buy_recommendations = report.get("buy_recommendations", [])
            if buy_recommendations:
                self.logger.info(f"\n💰 매수 추천 종목 ({len(buy_recommendations)}개):")
                for analysis in buy_recommendations:
                    signal_strength = analysis.get('signal_strength', 0)
                    risk_level = analysis.get('risk_level', 'MEDIUM')
                    self.logger.info(f"  🟢 {analysis['symbol']} ({analysis['name']}) - "
                                  f"점수: {analysis['comprehensive_score']:.1f}, "
                                  f"추천: {analysis['recommendation']}, "
                                  f"신호강도: {signal_strength:.1f}, "
                                  f"리스크: {risk_level}")
            
            # 4. 고득점 종목
            high_score_stocks = report.get("high_score_stocks", [])
            if high_score_stocks:
                self.logger.info(f"\n⭐ 고득점 종목 ({len(high_score_stocks)}개, 80점 이상):")
                for analysis in high_score_stocks:
                    self.logger.info(f"  ⭐ {analysis['symbol']} ({analysis['name']}) - "
                                  f"점수: {analysis['comprehensive_score']:.1f}")
        
        # 5. 특정 종목 분석 이력
        symbol_analysis = report.get("symbol_analysis", {})
        if symbol_analysis:
            self.logger.info(f"\n🔍 종목별 분석 이력:")
            for symbol, analyses in symbol_analysis.items():
                if analyses:
                    self.logger.info(f"\n📊 {symbol} 분석 이력 ({len(analyses)}건):")
                    for analysis in analyses:
                        analysis_date = analysis['analysis_date'].strftime('%Y-%m-%d %H:%M')
                        self.logger.info(f"    {analysis_date} | 점수: {analysis['comprehensive_score']:5.1f} | "
                                      f"추천: {analysis['recommendation']:12} | 전략: {analysis['strategy']}")
                    
                    avg_score = sum(a['comprehensive_score'] for a in analyses) / len(analyses)
                    self.logger.info(f"  📊 평균 점수: {avg_score:.1f}")
                else:
                    self.logger.warning(f"  ⚠️ {symbol} 분석 이력 없음")
        
        self.logger.info("="*60)
    
    async def get_trades_report(self, symbols: List[str] = None) -> Dict:
        """거래 기록 보고서 생성"""
        try:
            self.logger.info("💰 거래 기록 조회 중...")
            
            # 포트폴리오 요약 가져오기
            portfolio_summary = await self.db_manager.get_portfolio_summary()
            
            report = {
                "portfolio_summary": portfolio_summary,
                "symbol_trades": {}
            }
            
            # 특정 종목 거래 이력
            if symbols:
                symbol_trades = {}
                for symbol in symbols:
                    async with self.db_manager.get_async_session() as session:
                        result = await session.execute(
                            text("""
                            SELECT t.*, s.name
                            FROM trades t
                            JOIN stocks s ON t.stock_id = s.id
                            WHERE s.symbol = :symbol
                            ORDER BY t.trade_date DESC
                            LIMIT 20
                            """),
                            {"symbol": symbol}
                        )
                        
                        trades_data = [dict(row._mapping) for row in result.fetchall()]
                        symbol_trades[symbol] = trades_data
                
                report["symbol_trades"] = symbol_trades
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ 거래 보고서 생성 실패: {e}")
            return {"error": str(e)}
    
    def print_trades_report(self, report: Dict):
        """거래 보고서 출력"""
        self.logger.info("="*60)
        self.logger.info("💼 거래 기록 보고서")
        self.logger.info("="*60)
        
        if "error" in report:
            self.logger.error(f"❌ 오류: {report['error']}")
            return
        
        portfolio_summary = report.get("portfolio_summary", {})
        
        # 1. 포트폴리오 요약
        self.logger.info("📊 포트폴리오 요약:")
        self.logger.info(f"  💼 활성 포지션: {portfolio_summary.get('total_positions', 0)}개")
        self.logger.info(f"  💰 총 투자금액: {portfolio_summary.get('total_cost', 0):,.0f}원")
        self.logger.info(f"  📈 현재 평가금액: {portfolio_summary.get('total_current_value', 0):,.0f}원")
        self.logger.info(f"  📊 평가손익: {portfolio_summary.get('total_unrealized_pnl', 0):+,.0f}원")
        self.logger.info(f"  📈 수익률: {portfolio_summary.get('total_return_rate', 0):+.2f}%")
        
        # 2. 거래 성과
        performance = portfolio_summary.get('performance', {})
        if performance.get('total_trades', 0) > 0:
            self.logger.info(f"\n📈 거래 성과:")
            self.logger.info(f"  총 거래: {performance['total_trades']}건")
            self.logger.info(f"  승률: {performance['win_rate']:.1f}%")
            self.logger.info(f"  총 실현손익: {performance['total_realized_pnl']:+,.0f}원")
        
        # 3. 현재 포지션
        positions = portfolio_summary.get('positions', [])
        if positions:
            self.logger.info(f"\n💼 현재 보유 포지션:")
            self.logger.info("-" * 90)
            self.logger.info(f"{'종목코드':<8} {'종목명':<15} {'수량':<8} {'평가금액':<12} {'평가손익':<12} {'수익률':<8}")
            self.logger.info("-" * 90)
            
            for position in positions:
                pnl_rate = position.get('unrealized_pnl_rate', 0)
                self.logger.info(f"{position['symbol']:<8} {position['name']:<15} "
                              f"{position['quantity']:>6,}주 {position['current_value']:>10,.0f}원 "
                              f"{position['unrealized_pnl']:>+10,.0f}원 {pnl_rate:>+6.2f}%")
            
            self.logger.info("-" * 90)
        
        # 4. 종목별 거래 이력
        symbol_trades = report.get("symbol_trades", {})
        if symbol_trades:
            self.logger.info(f"\n🔍 종목별 거래 이력:")
            for symbol, trades in symbol_trades.items():
                if trades:
                    self.logger.info(f"\n📊 {symbol} 거래 이력 ({len(trades)}건):")
                    for trade in trades:
                        trade_date = trade['trade_date'].strftime('%Y-%m-%d %H:%M') if trade['trade_date'] else 'N/A'
                        trade_type = "매수" if trade['trade_type'] == 'BUY' else "매도"
                        profit_loss = trade.get('profit_loss', 0)
                        profit_loss_str = f"{profit_loss:+,.0f}원" if profit_loss else "N/A"
                        
                        self.logger.info(f"    {trade_date} | {trade_type} | "
                                      f"{trade['price']:8,.0f}원 | {trade['quantity']:6,}주 | "
                                      f"손익: {profit_loss_str}")
                else:
                    self.logger.warning(f"  ⚠️ {symbol} 거래 이력 없음")
        
        self.logger.info("="*60)