#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/main.py

메인 실행 파일 - 트레이딩 시스템 진입점
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, List, Any  # Dict 임포트 추가

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 기본 임포트부터 시작 - 임포트 순서 매우 중요!
print("🚀 시스템 시작 중...")

try:
    # 1. 설정 파일 먼저 임포트
    from config import Config
    print("✅ Config 임포트 성공")
except ImportError as e:
    print(f"❌ Config 임포트 실패: {e}")
    print("💡 해결 방법:")
    print("  1. 현재 디렉토리가 trading_system인지 확인: pwd")
    print("  2. config.py 파일이 존재하는지 확인: ls config.py")
    print("  3. PYTHONPATH 설정: export PYTHONPATH=\"${PYTHONPATH}:$(pwd)\"")
    sys.exit(1)

try:
    # 2. 로거 임포트
    from utils.logger import get_logger
    logger = get_logger("Main")
    print("✅ Logger 임포트 성공")
except ImportError as e:
    print(f"❌ Logger 임포트 실패: {e}")
    # 기본 로거 사용
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Main")
    print("⚠️ 기본 로거 사용")

def print_banner():
    """시스템 시작 배너 출력"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                    🚀 AI Trading System v1.0                  ║
    ║                                                               ║
    ║  📊 실시간 주식 분석 및 자동매매 시스템                          ║
    ║  🔍 뉴스 분석 + 기술적 분석 + 3분봉 정밀 신호                    ║
    ║  💰 리스크 관리 + 포지션 관리 + 자동 알림                       ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def create_arg_parser():
    """명령행 인수 파서 생성"""
    parser = argparse.ArgumentParser(
        description="AI Trading System - 실시간 주식 분석 및 자동매매",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
실행 예시:
  python main.py --mode test                        # 시스템 테스트
  python main.py --mode analysis                    # 분석만 실행
  python main.py --mode trading --auto             # 자동매매 실행
  python main.py --mode backtest --start 2024-01-01 # 백테스트
  python main.py --mode scheduler                  # 스케줄러 실행
        """
    )
    
    parser.add_argument(
        '--mode', 
        choices=['analysis', 'trading', 'backtest', 'scheduler', 'test'],
        default='test',
        help='실행 모드 선택 (기본값: test)'
    )
    
    parser.add_argument(
        '--strategy',
        choices=['momentum', 'breakout', 'mean_reversion', 'eod', 'tradingview'],
        default='momentum',
        help='사용할 전략 선택 (기본값: momentum)'
    )
    
    parser.add_argument(
        '--auto',
        action='store_true',
        help='자동매매 모드 활성화'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        help='백테스트 시작일 (YYYY-MM-DD 형식)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        help='백테스트 종료일 (YYYY-MM-DD 형식)'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        help='분석할 종목코드 리스트'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='분석할 종목 수 제한 (기본값: 10)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.py',
        help='설정 파일 경로'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='로그 레벨 설정'
    )
    
    return parser

async def run_test_mode(args):
    """테스트 모드 실행 - 기본 기능 확인"""
    logger.info("🧪 시스템 테스트 모드 시작")
    
    test_results = {
        'config': False,
        'logger': False,
        'database': False,
        'collectors': False,
        'analyzers': False,
        'strategies': False
    }
    
    try:
        # 1. 설정 검사
        logger.info("1️⃣ 설정 시스템 검사 중...")
        try:
            Config.validate()
            test_results['config'] = True
            logger.info("✅ 설정 시스템 정상")
        except Exception as e:
            logger.warning(f"⚠️ 설정 검사 실패: {e}")
        
        # 2. 로깅 시스템 확인
        logger.info("2️⃣ 로깅 시스템 검사 중...")
        test_results['logger'] = True
        logger.info("✅ 로깅 시스템 정상")
        
        # 3. 데이터베이스 모듈 임포트 테스트
        logger.info("3️⃣ 데이터베이스 모듈 검사 중...")
        try:
            from database.database_manager import DatabaseManager
            from database.models import Stock
            db_manager = DatabaseManager(Config)
            test_results['database'] = True
            logger.info("✅ 데이터베이스 모듈 정상")
        except ImportError as e:
            logger.error(f"❌ 데이터베이스 모듈 임포트 실패: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 데이터베이스 초기화 실패: {e}")
        
        # 4. 데이터 수집기 모듈 테스트
        logger.info("4️⃣ 데이터 수집기 모듈 검사 중...")
        try:
            from data_collectors.kis_collector import KISCollector, StockData
            test_results['collectors'] = True
            logger.info("✅ 데이터 수집기 모듈 정상")
        except ImportError as e:
            logger.error(f"❌ 데이터 수집기 모듈 임포트 실패: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 데이터 수집기 초기화 실패: {e}")
        
        # 5. 분석 엔진 모듈 테스트
        logger.info("5️⃣ 분석 엔진 모듈 검사 중...")
        try:
            from analyzers.analysis_engine import AnalysisEngine
            analysis_engine = AnalysisEngine(Config)
            test_results['analyzers'] = True
            logger.info("✅ 분석 엔진 모듈 정상")
        except ImportError as e:
            logger.error(f"❌ 분석 엔진 모듈 임포트 실패: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 분석 엔진 초기화 실패: {e}")
        
        # 6. 전략 모듈 테스트
        logger.info("6️⃣ 전략 모듈 검사 중...")
        try:
            from strategies.momentum_strategy import MomentumStrategy
            strategy = MomentumStrategy(Config)
            test_results['strategies'] = True
            logger.info("✅ 전략 모듈 정상")
        except ImportError as e:
            logger.error(f"❌ 전략 모듈 임포트 실패: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 전략 초기화 실패: {e}")
        
        # 7. 간단한 통합 테스트
        logger.info("7️⃣ 통합 테스트 중...")
        if test_results['collectors'] and test_results['analyzers']:
            try:
                # 더미 데이터로 간단한 분석 테스트
                stock_data = StockData(
                    symbol="TEST",
                    name="테스트종목",
                    current_price=50000,
                    change_rate=2.5,
                    volume=1000000,
                    trading_value=500,
                    market_cap=5000,
                    shares_outstanding=100000000,
                    high_52w=60000,
                    low_52w=40000
                )
                
                # 분석 실행 (비동기)
                result = await analysis_engine.analyze_comprehensive("TEST", "테스트종목", stock_data)
                
                if result and 'comprehensive_score' in result:
                    logger.info(f"✅ 통합 테스트 성공 - 분석 점수: {result['comprehensive_score']:.1f}")
                else:
                    logger.warning("⚠️ 통합 테스트 결과 이상")
                    
            except Exception as e:
                logger.warning(f"⚠️ 통합 테스트 실패: {e}")
        
        # 8. 테스트 결과 요약
        logger.info("8️⃣ 테스트 결과 요약:")
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅" if result else "❌"
            logger.info(f"  {status} {test_name}")
        
        logger.info(f"📊 테스트 결과: {passed_tests}/{total_tests} 통과")
        
        if passed_tests == total_tests:
            logger.info("🎉 모든 테스트 통과! 시스템이 정상 작동합니다.")
            logger.info("💡 다음 단계: python main.py --mode analysis")
        elif passed_tests >= total_tests * 0.7:
            logger.info("⚠️ 대부분의 테스트 통과. 일부 기능에 문제가 있을 수 있습니다.")
        else:
            logger.error("❌ 많은 테스트 실패. 설치 및 설정을 다시 확인하세요.")
        
        return passed_tests >= total_tests * 0.7
        
    except Exception as e:
        logger.error(f"❌ 테스트 모드 실행 실패: {e}")
        return False

async def run_analysis_mode(args):
    """분석 모드 실행 - KIS API 데이터 + 필터링"""
    logger.info("🔍 분석 모드 시작 (KIS API + 필터링)")
    
    try:
        # 필요한 모듈들 동적 임포트
        logger.info("📦 모듈 로딩 중...")
        
        try:
            from analyzers.analysis_engine import AnalysisEngine
            from data_collectors.kis_collector import KISCollector, StockData
            from database.database_manager import DatabaseManager
            logger.info("✅ 모든 모듈 로딩 완료")
        except ImportError as e:
            logger.error(f"❌ 필수 모듈 임포트 실패: {e}")
            logger.info("💡 먼저 --mode test로 시스템을 확인하세요.")
            return False
        
        # 시스템 초기화
        db_manager = DatabaseManager(Config)
        analysis_engine = AnalysisEngine(Config)
        
        logger.info("✅ 시스템 초기화 완료")
        
        # KIS 데이터 수집기 초기화
        async with KISCollector(Config) as kis_collector:
            await kis_collector.initialize()
            
            # 분석할 종목 리스트 결정
            if args.symbols:
                # 명령행에서 지정한 종목들
                logger.info(f"📋 사용자 지정 종목 {len(args.symbols)}개 분석 예정")
                target_symbols = args.symbols
            else:
                # KIS API에서 종목 리스트 가져오기 및 필터링
                logger.info("📡 KIS API에서 종목 리스트 조회 중...")
                
                # 1. 전체 종목 리스트 가져오기 (현재는 더미 데이터)
                all_stocks = await kis_collector.get_stock_list()
                if not all_stocks:
                    logger.info("🔄 KIS API에서 데이터를 가져올 수 없어 필터링된 종목 사용")
                    all_stocks = await kis_collector.get_filtered_stocks(limit=args.limit * 2)
                
                logger.info(f"📊 총 {len(all_stocks)}개 종목 발견")
                
                # 2. 종목별 상세 정보 조회 및 필터링
                logger.info("🔍 종목 필터링 시작...")
                filtered_stocks = []
                
                for i, (symbol, name) in enumerate(all_stocks):
                    try:
                        if len(filtered_stocks) >= args.limit:
                            break
                            
                        logger.info(f"[{i+1}/{len(all_stocks)}] {symbol} {name} 필터링 중...")
                        
                        # 종목 상세 정보 조회
                        stock_info = await kis_collector.get_stock_info(symbol)
                        if not stock_info:
                            continue
                        
                        # 필터링 조건 검사
                        if await apply_stock_filters(stock_info, Config):
                            filtered_stocks.append((symbol, name))
                            logger.info(f"✅ {symbol} {name} 필터링 통과")
                            
                            # 데이터베이스에 종목 정보 저장/업데이트
                            await db_manager.save_stock(stock_info)
                        else:
                            logger.debug(f"❌ {symbol} {name} 필터링 제외")
                        
                        # API 제한 방지
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ {symbol} 필터링 중 오류: {e}")
                        continue
                
                target_symbols = [symbol for symbol, name in filtered_stocks]
                logger.info(f"🎯 필터링 완료: {len(target_symbols)}개 종목 선정")
                
                if not target_symbols:
                    logger.error("❌ 필터링 결과 종목이 없습니다.")
                    return False
            
            # 분석 실행
            results = []
            successful_analysis = 0
            failed_analysis = 0
            
            logger.info("="*60)
            logger.info(f"🔬 {len(target_symbols)}개 종목 분석 시작")
            logger.info("="*60)
            
            for i, symbol in enumerate(target_symbols):
                try:
                    logger.info(f"[{i+1}/{len(target_symbols)}] {symbol} 분석 중...")
                    
                    # 1. 데이터베이스에서 종목 기본 정보 조회
                    db_stock_info = await db_manager.get_stock_by_symbol(symbol)
                    if not db_stock_info:
                        # 데이터베이스에 없으면 KIS에서 다시 조회
                        stock_info = await kis_collector.get_stock_info(symbol)
                        if stock_info:
                            stock_id = await db_manager.save_stock(stock_info)
                            db_stock_info = await db_manager.get_stock_by_symbol(symbol)
                    
                    if not db_stock_info:
                        logger.warning(f"⚠️ {symbol} 종목 정보 조회 실패")
                        failed_analysis += 1
                        continue
                    
                    # 2. 실시간 데이터 및 차트 데이터 조회
                    stock_data = await kis_collector.create_stock_data(symbol)
                    if not stock_data:
                        logger.warning(f"⚠️ {symbol} 실시간 데이터 조회 실패")
                        failed_analysis += 1
                        continue
                    
                    # 3. 뉴스 데이터 조회 (추후 구현)
                    news_data = await get_news_data(symbol, stock_data.name)
                    
                    # 4. 종합 분석 실행
                    analysis_result = await analysis_engine.analyze_comprehensive(
                        symbol, stock_data.name, stock_data, 
                        news_data=news_data, strategy=args.strategy
                    )
                    
                    if analysis_result:
                        # 5. 분석 결과를 데이터베이스에 저장
                        analysis_data = {
                            "stock_id": db_stock_info['id'],
                            "analysis_date": datetime.now(),
                            "strategy": args.strategy,
                            "comprehensive_score": analysis_result['comprehensive_score'],
                            "recommendation": analysis_result['recommendation'],
                            "confidence": analysis_result['confidence'],
                            "technical_score": analysis_result['technical_analysis'].get('overall_score', 50),
                            "fundamental_score": analysis_result['fundamental_analysis'].get('overall_score', 50),
                            "sentiment_score": analysis_result['sentiment_analysis'].get('overall_score', 50),
                            "signal_strength": analysis_result['signal_strength'],
                            "signal_type": analysis_result['signal_type'],
                            "action": analysis_result.get('action', 'HOLD'),
                            "risk_level": analysis_result.get('risk_level', 'MEDIUM'),
                            "price_at_analysis": stock_data.current_price,
                            "technical_details": analysis_result['technical_analysis'],
                            "fundamental_details": analysis_result['fundamental_analysis'],
                            "sentiment_details": analysis_result['sentiment_analysis']
                        }
                        
                        analysis_id = await db_manager.save_analysis_result(analysis_data)
                        if analysis_id:
                            logger.info(f"💾 {symbol} 분석 결과 저장 완료 (ID: {analysis_id})")
                        
                        # 6. 종목 정보 업데이트
                        updated_stock_data = {
                            "symbol": symbol,
                            "name": stock_data.name,
                            "current_price": stock_data.current_price,
                            "market_cap": stock_data.market_cap,
                            "pe_ratio": stock_data.pe_ratio,
                            "pbr": stock_data.pbr
                        }
                        await db_manager.save_stock(updated_stock_data)
                        
                        results.append(analysis_result)
                        successful_analysis += 1
                        
                        logger.info(f"✅ {symbol} 분석 완료 - 점수: {analysis_result['comprehensive_score']:.1f}, 추천: {analysis_result['recommendation']}")
                    else:
                        logger.warning(f"⚠️ {symbol} 분석 결과 없음")
                        failed_analysis += 1
                    
                    # API 제한 방지
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.warning(f"⚠️ {symbol} 분석 실패: {e}")
                    failed_analysis += 1
                    continue
        
        # 분석 결과 요약 및 출력
        await display_analysis_results(results, successful_analysis, failed_analysis, len(target_symbols))
        
        logger.info("✅ KIS API 기반 분석 모드 완료")
        return successful_analysis > 0
        
    except Exception as e:
        logger.error(f"❌ 분석 모드 실행 실패: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            logger.debug(traceback.format_exc())
        return False

async def apply_stock_filters(stock_info: Dict, config) -> bool:
    """종목 필터링 조건 적용"""
    try:
        # 기본 필터링 조건
        price = stock_info.get('current_price', 0)
        volume = stock_info.get('volume', 0)
        market_cap = stock_info.get('market_cap', 0)
        
        # 1. 가격 필터링
        if price < config.trading.MIN_PRICE or price > config.trading.MAX_PRICE:
            return False
        
        # 2. 거래량 필터링
        if volume < config.trading.MIN_VOLUME:
            return False
        
        # 3. 시가총액 필터링
        if market_cap < config.trading.MIN_MARKET_CAP:
            return False
        
        # 4. 재무 지표 필터링 (있는 경우만)
        pe_ratio = stock_info.get('pe_ratio')
        if pe_ratio and (pe_ratio < 0 or pe_ratio > 100):  # 비정상적인 PER 제외
            return False
        
        pbr = stock_info.get('pbr')
        if pbr and (pbr < 0 or pbr > 10):  # 비정상적인 PBR 제외
            return False
        
        # 5. 시장 구분 (필요시)
        market = stock_info.get('market', '')
        if market not in ['KOSPI', 'KOSDAQ']:
            return False
        
        return True
        
    except Exception as e:
        logger = get_logger("StockFilter")
        logger.warning(f"⚠️ 필터링 중 오류: {e}")
        return False

async def get_news_data(symbol: str, name: str) -> Dict:
    """뉴스 데이터 조회 (추후 구현)"""
    try:
        # 현재는 더미 데이터 반환
        # 추후 네이버 뉴스 API 또는 다른 뉴스 소스 연동
        return {
            "articles": [],
            "sentiment_summary": "neutral",
            "news_count": 0
        }
    except Exception:
        return {}

async def display_analysis_results(results: List[Dict], successful: int, failed: int, total: int):
    """분석 결과 출력"""
    logger.info("="*60)
    logger.info("📈 KIS API 기반 분석 결과 요약")
    logger.info("="*60)
    
    logger.info(f"📊 분석 요청: {total}개")
    logger.info(f"✅ 성공: {successful}개")
    logger.info(f"❌ 실패: {failed}개")
    logger.info(f"📈 성공률: {(successful/total*100):.1f}%" if total > 0 else "📈 성공률: 0%")
    
    if results:
        # 기본 통계
        scores = [r['comprehensive_score'] for r in results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        buy_signals = len([r for r in results if r['recommendation'] in ['BUY', 'STRONG_BUY']])
        sell_signals = len([r for r in results if r['recommendation'] in ['SELL', 'STRONG_SELL']])
        hold_signals = len(results) - buy_signals - sell_signals
        
        logger.info(f"📊 평균 점수: {avg_score:.1f}")
        logger.info(f"📊 최고 점수: {max_score:.1f}")
        logger.info(f"📊 최저 점수: {min_score:.1f}")
        logger.info(f"🟢 매수 신호: {buy_signals}개")
        logger.info(f"🟡 보유 신호: {hold_signals}개")
        logger.info(f"🔴 매도 신호: {sell_signals}개")
        
        # 상위 결과 출력
        sorted_results = sorted(results, key=lambda x: x['comprehensive_score'], reverse=True)
        
        logger.info(f"\n🏆 상위 {min(5, len(sorted_results))}개 종목:")
        for i, result in enumerate(sorted_results[:5], 1):
            confidence_str = f"신뢰도: {result['confidence']:.2f}"
            risk_str = f"리스크: {result.get('risk_level', 'MEDIUM')}"
            logger.info(f"  {i}. {result['symbol']} ({result['name']})")
            logger.info(f"     점수: {result['comprehensive_score']:.1f}, 추천: {result['recommendation']}, {confidence_str}, {risk_str}")
        
        # 매수 추천 종목
        buy_recommendations = [r for r in sorted_results if r['recommendation'] in ['BUY', 'STRONG_BUY']]
        if buy_recommendations:
            logger.info(f"\n💰 매수 추천 종목 ({len(buy_recommendations)}개):")
            for result in buy_recommendations:
                signal_strength = f"신호강도: {result['signal_strength']:.1f}"
                logger.info(f"  • {result['symbol']} ({result['name']}) - {result['recommendation']} ({signal_strength})")
        
        # 고득점 종목 (80점 이상)
        high_score_stocks = [r for r in sorted_results if r['comprehensive_score'] >= 80]
        if high_score_stocks:
            logger.info(f"\n🌟 고득점 종목 ({len(high_score_stocks)}개, 80점 이상):")
            for result in high_score_stocks:
                logger.info(f"  ⭐ {result['symbol']} ({result['name']}) - 점수: {result['comprehensive_score']:.1f}")
        
        # 주의 종목 (40점 미만)
        warning_stocks = [r for r in sorted_results if r['comprehensive_score'] < 40]
        if warning_stocks:
            logger.info(f"\n⚠️ 주의 종목 ({len(warning_stocks)}개, 40점 미만):")
            for result in warning_stocks[-3:]:  # 하위 3개만 표시
                logger.info(f"  ⚠️ {result['symbol']} ({result['name']}) - 점수: {result['comprehensive_score']:.1f}")
        
        logger.info(f"\n💾 데이터베이스 저장: {successful}개 분석 결과 저장 완료")
        
    else:
        logger.warning("⚠️ 분석 결과가 없습니다.")

async def run_trading_mode(args):
    """매매 모드 실행"""
    logger.info("💰 매매 모드 시작")
    
    if not args.auto:
        logger.warning("⚠️ 자동매매가 비활성화되어 있습니다. --auto 옵션을 사용하세요.")
        return False
    
    try:
        logger.info("🚧 매매 모드는 현재 개발 중입니다.")
        logger.info("실제 매매 기능은 추후 구현될 예정입니다.")
        return True
        
    except Exception as e:
        logger.error(f"❌ 매매 모드 실행 실패: {e}")
        return False

async def run_backtest_mode(args):
    """백테스트 모드 실행"""
    logger.info("📈 백테스트 모드 시작")
    
    try:
        logger.info("🚧 백테스트 모드는 현재 개발 중입니다.")
        return True
        
    except Exception as e:
        logger.error(f"❌ 백테스트 모드 실행 실패: {e}")
        return False

async def run_scheduler_mode(args):
    """스케줄러 모드 실행"""
    logger.info("⏰ 스케줄러 모드 시작")
    
    try:
        logger.info("🚧 스케줄러 모드는 현재 개발 중입니다.")
        return True
        
    except Exception as e:
        logger.error(f"❌ 스케줄러 모드 실행 실패: {e}")
        return False

async def main():
    """메인 함수"""
    # 명령행 인수 파싱
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # 배너 출력
    print_banner()
    
    # 로그 레벨 설정
    if 'logger' in globals():
        logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 시작 로그
    logger.info(f"🚀 시스템 시작 - 모드: {args.mode}, 전략: {args.strategy}")
    logger.info(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 작업 디렉토리: {Path.cwd()}")
    
    success = False
    
    try:
        # 모드별 실행
        if args.mode == 'test':
            success = await run_test_mode(args)
        elif args.mode == 'analysis':
            success = await run_analysis_mode(args)
        elif args.mode == 'trading':
            success = await run_trading_mode(args)
        elif args.mode == 'backtest':
            success = await run_backtest_mode(args)
        elif args.mode == 'scheduler':
            success = await run_scheduler_mode(args)
        
        if success:
            logger.info("✅ 프로그램 정상 종료")
        else:
            logger.error("❌ 프로그램 실행 중 오류 발생")
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자 중단 요청")
    except Exception as e:
        logger.error(f"❌ 프로그램 실행 실패: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            logger.debug(traceback.format_exc())
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
   # 비동기 메인 함수 실행
   try:
       asyncio.run(main())
   except KeyboardInterrupt:
       print("\n🛑 프로그램이 중단되었습니다.")
       print("시스템을 안전하게 종료합니다...")
   except Exception as e:
       print(f"❌ 치명적 오류: {e}")
       print("오류 발생으로 프로그램을 종료합니다.")
       sys.exit(1)

async def run_analysis_mode(args):
    """분석 모드 실행"""
    logger.info("🔍 분석 모드 시작")
    
    try:
        # 필요한 모듈들 임포트
        from analyzers.analysis_engine import AnalysisEngine
        from data_collectors.kis_collector import KISCollector, StockData
        
        # 분석 엔진 초기화
        analysis_engine = AnalysisEngine(Config)
        logger.info("✅ 분석 엔진 초기화 완료")
        
        # 테스트 종목 리스트
        test_stocks = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035720", "카카오"),
            ("005490", "POSCO홀딩스"),
            ("051910", "LG화학")
        ]
        
        if args.symbols:
            # 명령행에서 지정한 종목들 분석
            symbols_with_names = [(symbol, f"종목{symbol}") for symbol in args.symbols]
        else:
            # 기본 테스트 종목들 사용
            symbols_with_names = test_stocks[:args.limit]
        
        logger.info(f"📊 {len(symbols_with_names)}개 종목 분석 시작")
        
        results = []
        for i, (symbol, name) in enumerate(symbols_with_names):
            try:
                logger.info(f"[{i+1}/{len(symbols_with_names)}] {symbol} {name} 분석 중...")
                
                # 더미 주식 데이터 생성 (실제로는 KIS API에서 가져옴)
                import random
                stock_data = StockData(
                    symbol=symbol,
                    name=name,
                    current_price=random.randint(10000, 100000),
                    change_rate=random.uniform(-5, 5),
                    volume=random.randint(100000, 5000000),
                    trading_value=random.randint(100, 2000),
                    market_cap=random.randint(1000, 50000),
                    shares_outstanding=random.randint(10000000, 1000000000),
                    high_52w=random.randint(50000, 120000),
                    low_52w=random.randint(20000, 60000)
                )
                
                # 종합 분석 실행
                result = await analysis_engine.analyze_comprehensive(
                    symbol, name, stock_data, strategy=args.strategy
                )
                
                results.append(result)
                logger.info(f"✅ {symbol} 분석 완료 - 점수: {result['comprehensive_score']:.1f}")
                
                # API 제한 방지
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"⚠️ {symbol} 분석 실패: {e}")
                continue
        
        # 결과 요약
        if results:
            summary = await analysis_engine.get_analysis_summary(results)
            
            logger.info("📈 분석 결과 요약:")
            logger.info(f"  전체 분석 종목: {summary.get('total_analyzed', 0)}개")
            logger.info(f"  평균 점수: {summary.get('average_score', 0):.1f}")
            logger.info(f"  매수 신호: {summary.get('buy_signals', 0)}개")
            logger.info(f"  고득점 종목: {summary.get('high_score_count', 0)}개")
            
            # 상위 결과 출력
            sorted_results = sorted(results, key=lambda x: x['comprehensive_score'], reverse=True)
            logger.info("\n🏆 상위 종목:")
            for i, result in enumerate(sorted_results[:5], 1):
                logger.info(f"  {i}. {result['symbol']} ({result['name']}) - "
                          f"점수: {result['comprehensive_score']:.1f}, "
                          f"추천: {result['recommendation']}")
        
        logger.info("✅ 분석 모드 완료")
        
    except ImportError as e:
        logger.error(f"❌ 모듈 임포트 실패: {e}")
        logger.info("💡 먼저 --mode test 옵션으로 시스템을 확인해보세요.")
    except Exception as e:
        logger.error(f"❌ 분석 모드 실행 실패: {e}")
        raise

async def run_trading_mode(args):
    """매매 모드 실행"""
    logger.info("💰 매매 모드 시작")
    
    if not args.auto:
        logger.warning("⚠️ 자동매매가 비활성화되어 있습니다. --auto 옵션을 사용하세요.")
        return
    
    try:
        logger.info("🚧 매매 모드는 현재 개발 중입니다.")
        logger.info("실제 매매 기능은 추후 구현될 예정입니다.")
        
    except Exception as e:
        logger.error(f"❌ 매매 모드 실행 실패: {e}")
        raise

async def run_backtest_mode(args):
    """백테스트 모드 실행"""
    logger.info("📈 백테스트 모드 시작")
    
    try:
        logger.info("🚧 백테스트 모드는 현재 개발 중입니다.")
        
    except Exception as e:
        logger.error(f"❌ 백테스트 모드 실행 실패: {e}")
        raise

async def run_scheduler_mode(args):
    """스케줄러 모드 실행"""
    logger.info("⏰ 스케줄러 모드 시작")
    
    try:
        logger.info("🚧 스케줄러 모드는 현재 개발 중입니다.")
        
    except Exception as e:
        logger.error(f"❌ 스케줄러 모드 실행 실패: {e}")
        raise

async def main():
    """메인 함수"""
    # 명령행 인수 파싱
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # 배너 출력
    print_banner()
    
    # 로그 레벨 설정
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 시작 로그
    logger.info(f"🚀 시스템 시작 - 모드: {args.mode}, 전략: {args.strategy}")
    logger.info(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 모드별 실행
        if args.mode == 'test':
            await run_test_mode(args)
        elif args.mode == 'analysis':
            await run_analysis_mode(args)
        elif args.mode == 'trading':
            await run_trading_mode(args)
        elif args.mode == 'backtest':
            await run_backtest_mode(args)
        elif args.mode == 'scheduler':
            await run_scheduler_mode(args)
        
        logger.info("✅ 프로그램 정상 종료")
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자 중단 요청")
    except Exception as e:
        logger.error(f"❌ 프로그램 실행 실패: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    # 비동기 메인 함수 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        sys.exit(1)