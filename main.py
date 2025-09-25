#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/main.py

AI Trading System v4.0 - 통합 메인 진입점
오류 수정: DB 연결 안정성, FilterHistory 모델 오류, 예외 처리 강화
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import argparse
from typing import Dict, List, Any

# Import error recovery system
from utils.error_recovery import (
    async_retry, RetryConfig, error_recovery, 
    safe_execute, health_checker, get_recovery_stats
)

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# UTF-8 인코딩 문제 해결 (시스템 시작 시 가장 먼저 실행)
try:
    from utils.encoding_fix import init_encoding_fix
    init_encoding_fix()
except ImportError:
    # 인코딩 수정 모듈이 없는 경우 기본 설정
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

# 고급 에러 핸들링 설정
try:
    from utils.error_handler import setup_global_exception_handler, global_error_handler
    setup_global_exception_handler()
except ImportError:
    global_error_handler = None

def safe_get_attr(self, data, attr_name, default=None):
    """안전한 속성 접근 유틸리티"""
    try:
        if isinstance(data, dict):
            return data.get(attr_name, default)
        else:
            return getattr(data, attr_name, default)
    except (AttributeError, TypeError):
        return default

def print_banner():
    """시스템 시작 배너 출력"""
    banner = """
==============================================================
                   AI Trading System v4.0                
                   Phase 4: Advanced AI Features
                                                            
 * 5개 영역 통합 분석: 기술적 + 펀더멘털 + 뉴스 + 수급 + 패턴
 * AI 고급 기능: 예측 + 리스크 관리 + 체제 감지 + 전략 최적화
 * KIS HTS 조건검색 연동 + 실시간 정밀 매매               
 * PostgreSQL 기반 데이터 관리 + 안정성 강화                           
                                                            
==============================================================
    """
    print(banner)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"작업 디렉토리: {Path.cwd()}")
    print()

# 기본 설정 및 로거 초기화
def initialize_system():
    """시스템 초기화"""
    try:
        print("시스템 초기화 중...")
        
        # 1. 설정 파일 임포트
        from config import Config
        print("[PASS] Config 임포트 성공")
        
        # 2. 로거 임포트
        try:
            from utils.logger import get_logger
            logger = get_logger("Main")
            print("[PASS] Logger 임포트 성공")
        except ImportError as e:
            print(f"[WARN] Logger 임포트 실패: {e}")
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger("Main")
            print("기본 로거 사용")
        
        config = Config()
        return config, logger
        
    except ImportError as e:
        print(f"[ERROR] 설정 초기화 실패: {e}")
        print("해결 방법:")
        print("  1. 현재 디렉토리가 trading_system인지 확인: pwd")
        print("  2. config.py 파일이 존재하는지 확인: ls config.py")
        print("  3. PYTHONPATH 설정: export PYTHONPATH=\"${PYTHONPATH}:$(pwd)\"")
        sys.exit(1)
def setup_asyncio_exception_handler():
    """asyncio 예외 처리기 설정"""
    def exception_handler(loop, context):
        # ConnectionResetError와 같은 네트워크 오류를 조용히 처리
        exception = context.get('exception')
        if isinstance(exception, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            # 네트워크 연결 끊김은 정상적인 상황으로 간주하고 로깅만
            pass
        else:
            # 다른 예외는 기본 처리기로 전달
            loop.default_exception_handler(context)
    
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)

async def main():
    """메인 실행 함수 - 향상된 오류 처리 및 안정성"""
    trading_system = None
    
    # asyncio 예외 처리기 설정
    setup_asyncio_exception_handler()
    
    try:
        print_banner()
        
        # 시스템 초기화
        config, logger = initialize_system()
        logger.info("설정 초기화 완료")
        
        # TradingSystem 임포트 및 초기화 (retry 로직 추가)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from core.trading_system import TradingSystem
                logger.info("[PASS] TradingSystem 임포트 성공")
                break
            except ImportError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[WARN] TradingSystem 임포트 실패 ({attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(1)  # 1초 대기 후 재시도
                else:
                    logger.error(f"[ERROR] TradingSystem 임포트 최종 실패: {e}")
                    return False
        
        # TradingSystem 생성 및 초기화
                # TradingSystem 생성 및 초기화
        trading_system = TradingSystem(trading_enabled=config.trading.TRADING_ENABLED, backtest_mode=False)
        
        # 컴포넌트 초기화 (retry 로직 추가)
        logger.info("컴포넌트 초기화 중...")
        for attempt in range(max_retries):
            try:
                if await trading_system.initialize_components():
                    logger.info("[PASS] 컴포넌트 초기화 완료!")
                    break
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"[WARN] 컴포넌트 초기화 실패 ({attempt + 1}/{max_retries}), 재시도 중...")
                        await asyncio.sleep(2)  # 2초 대기 후 재시도
                    else:
                        logger.error("[ERROR] 컴포넌트 초기화 최종 실패")
                        return False
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[WARN] 컴포넌트 초기화 오류 ({attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"[ERROR] 컴포넌트 초기화 최종 실패: {e}")
                    return False
        
        # TradingSystem에서 자동으로 시작하므로 중복 초기화 제거
        logger.info("[PASS] 자동매매 시스템이 TradingSystem에서 자동 시작됨")
        
        # 백그라운드 서비스 자동 시작 (대화형 모드 시작 전에)
        background_service = None
        background_task = None
        try:
            logger.info("🚀 백그라운드 모니터링 서비스 자동 시작 중...")
            from background_monitoring_service import BackgroundMonitoringService

            # 기존 TradingSystem 인스턴스를 전달하여 중복 초기화 방지
            background_service = BackgroundMonitoringService(trading_system)
            success = await background_service.initialize()
            
            if success:
                # 백그라운드 서비스를 별도 태스크로 실행 (논블로킹)
                background_task = asyncio.create_task(background_service.start_service())
                logger.info("✅ 백그라운드 서비스가 자동으로 시작되었습니다")
                logger.info("📊 시간대별 전략 자동실행이 활성화되었습니다")
            else:
                logger.warning("⚠️ 백그라운드 서비스 초기화 실패 - 수동 모니터링만 가능")
                
        except Exception as e:
            logger.error(f"❌ 백그라운드 서비스 시작 실패: {e}")
            logger.info("📱 수동 모니터링 모드로 계속 진행합니다")
            import traceback
            logger.error(f"백그라운드 서비스 오류 상세: {traceback.format_exc()}")
        
        # 대화형 모드 실행
        try:
            await trading_system.run_interactive_mode()
        except Exception as e:
            logger.error(f"❌ 대화형 모드 실행 중 오류 발생: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return False
        
        # 정상 종료
        if background_service:
            try:
                logger.info("🛑 백그라운드 서비스 종료 중...")
                if background_task and not background_task.done():
                    background_task.cancel()
                    try:
                        await background_task
                    except asyncio.CancelledError:
                        logger.info("백그라운드 태스크 취소됨")
                await background_service.stop_service()
                logger.info("✅ 백그라운드 서비스 정상 종료")
            except Exception as e:
                logger.error(f"❌ 백그라운드 서비스 종료 오류: {e}")
        
        await trading_system.cleanup()
        return True
        
    except KeyboardInterrupt:
        print("\n[STOP] 사용자에 의한 중단")
        # 백그라운드 서비스 정리
        if 'background_service' in locals() and background_service:
            try:
                if 'background_task' in locals() and background_task and not background_task.done():
                    background_task.cancel()
                    try:
                        await background_task
                    except asyncio.CancelledError:
                        pass
                await background_service.stop_service()
            except:
                pass
        return True
    except Exception as e:
        print(f"[ERROR] 치명적 오류: {e}")
        # 백그라운드 서비스 정리
        if 'background_service' in locals() and background_service:
            try:
                if 'background_task' in locals() and background_task and not background_task.done():
                    background_task.cancel()
                    try:
                        await background_task
                    except asyncio.CancelledError:
                        pass
                await background_service.stop_service()
            except:
                pass
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 안전한 리소스 정리
        if trading_system:
            try:
                await trading_system.cleanup()
            except Exception as cleanup_error:
                print(f"[WARN] 정리 중 오류: {cleanup_error}")

async def run_automated_mode(args):
    """자동화 모드 실행 (EOF 에러 방지)"""
    from time_based_strategy_mapper import TimeBasedStrategyMapper
    from datetime import datetime, time as dt_time
    from config import Config
    from core.trading_system import TradingSystem
    
    print("🤖 자동화 모드 시작 - 비대화형 실행")
    
    try:
        # 전체 자동화 모드를 1시간으로 제한 (안전장치)
        await asyncio.wait_for(_run_automated_mode_core(args), timeout=3600.0)
    except asyncio.TimeoutError:
        print("⏰ 자동화 모드 타임아웃 (1시간 초과)")
    except Exception as e:
        print(f"❌ 자동화 모드 실행 오류: {e}")
        import traceback
        traceback.print_exc()

async def _run_automated_mode_core(args):
    """자동화 모드 핵심 로직 (타임아웃 적용용)"""
    from time_based_strategy_mapper import TimeBasedStrategyMapper
    from datetime import datetime, time as dt_time
    from config import Config
    from core.trading_system import TradingSystem
    
    try:
        # 설정 및 매퍼 초기화
        config = Config()
        strategy_mapper = TimeBasedStrategyMapper()
        
        # 현재 세션 확인
        current_session = strategy_mapper.get_current_market_session()
        optimal_strategies = strategy_mapper.get_optimal_strategies_for_session(current_session)
        
        print(f"현재 세션: {current_session.value}")
        
        if not optimal_strategies:
            print("현재 세션에 최적화된 전략이 없습니다")
            return
            
        strategy = optimal_strategies[0]
        print(f"활성 전략: {strategy.strategy_name}")
        
        # 시장 시간 확인
        now = datetime.now().time()
        market_open = dt_time(9, 0)
        market_close = dt_time(15, 30)
        
        if not (market_open <= now <= market_close) and strategy.strategy_name != 'eod':
            print(f"현재 시간 ({now})은 거래 시간이 아닙니다")
            return
            
        # TradingSystem 초기화 (비대화형 모드)
        trading_system = TradingSystem(config, non_interactive=True)
        await trading_system.initialize_components()
        
        print("🚀 시스템 초기화 완료")
        
        # 건강 상태 체크 설정
        await setup_health_checks(trading_system)
        
        # 자동화된 거래 실행
        await execute_automated_trading(trading_system, strategy, args)
        
        # 실행 후 에러 복구 통계 출력
        stats = get_recovery_stats()
        if stats["total_errors"] > 0:
            print(f"\n📊 에러 복구 통계:")
            print(f"  총 에러: {stats['total_errors']}회")
            print(f"  복구 성공: {stats['recovered_errors']}회")
            print(f"  복구율: {stats['recovery_rate']:.1%}")
        
    except Exception as e:
        print(f"❌ 자동화 모드 핵심 로직 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if 'trading_system' in locals():
            await trading_system.cleanup()

@async_retry(
    retry_config=RetryConfig(max_attempts=3, base_delay=2.0, max_delay=10.0),
    context="automated_trading_execution"
)
async def execute_automated_trading(trading_system, strategy, args):
    """자동화된 거래 로직 실행 (에러 복구 기능 포함)"""
    try:
        print(f"📊 {strategy.strategy_name} 전략 실행 중...")
        
        # 시스템 건강 상태 확인
        health_status = await health_checker.run_health_checks()
        if not health_status.get("overall_healthy", True):
            print("⚠️ 시스템 건강 상태에 문제가 있습니다. 계속 진행합니다...")
        
        # HTS 조건 검색 (비대화형)
        condition_name = strategy.hts_condition
        print(f"조건 검색: {condition_name}")
        
        # 조건 검색 결과 가져오기 (입력 없이)
        stocks = await get_condition_stocks_safely(trading_system, condition_name)
        
        if not stocks:
            print("조건에 맞는 종목이 없습니다")
            return
            
        print(f"발견된 종목: {len(stocks)}개")
        
        # 각 종목 분석 및 거래
        max_stocks = min(strategy.max_stocks, len(stocks))
        successful_analyses = 0
        failed_analyses = 0
        
        for i, stock_code in enumerate(stocks[:max_stocks]):
            print(f"\n[{i+1}/{max_stocks}] {stock_code} 분석 중...")
            
            # 개별 종목 분석을 안전하게 실행
            analysis_result = await analyze_stock_safely(trading_system, stock_code, i+1, max_stocks)
            
            if analysis_result and not analysis_result.get('error'):
                successful_analyses += 1
            else:
                failed_analyses += 1
                print(f"  ❌ {stock_code} 분석 실패")
                continue
                    
            # 거래 신호 확인
            signal = analysis_result.get('signal', 'HOLD')
            confidence = analysis_result.get('confidence', 0)
            
            print(f"  📊 신호: {signal}, 신뢰도: {confidence:.1%}")
            
            # 거래 로직은 여기에 추가할 수 있습니다
            # 현재는 분석만 수행
        
        # 실행 결과 요약
        print(f"\n📋 실행 결과 요약:")
        print(f"  분석 대상: {max_stocks}개 종목")
        print(f"  성공: {successful_analyses}개")
        print(f"  실패: {failed_analyses}개")
        print(f"  성공률: {successful_analyses/max_stocks*100:.1f}%")
        
        print("\n✅ 자동화 거래 실행 완료")
        
    except Exception as e:
        print(f"❌ 자동화 거래 실행 오류: {e}")

async def get_condition_stocks_safely(trading_system, condition_name):
    """조건 검색 안전 실행 (EOF 에러 방지)"""
    try:
        # 실제 조건 검색 구현
        if hasattr(trading_system, 'database_auto_trader'):
            try:
                # HTS 조건 검색 - 비대화형 방식
                stocks = await trading_system.database_auto_trader.search_condition_stocks(condition_name)
                if stocks:
                    print(f"✅ 조건 검색 성공: {len(stocks)}개 종목")
                    return stocks
            except Exception as search_error:
                print(f"HTS 조건 검색 실패: {search_error}")
        
        # 폴백: 실시간 시장 데이터에서 활성 종목 조회
        print("📈 실시간 시장 데이터에서 활성 종목 조회 중...")
        try:
            # KIS API를 통한 실시간 활성 종목 조회
            if hasattr(trading_system, 'data_collector'):
                active_stocks = await trading_system.data_collector.get_active_stocks(limit=5)
                if active_stocks:
                    print(f"✅ 활성 종목 {len(active_stocks)}개 발견")
                    return active_stocks
        except Exception as api_error:
            print(f"API 조회 실패: {api_error}")
        
        # 최후 폴백: 시장 대표 종목 사용
        print("⚠️ 시장 대표 종목으로 폴백")
        try:
            market_leaders = await trading_system.data_collector.get_market_leaders(limit=3)
            if market_leaders:
                return market_leaders
        except Exception as fallback_error:
            print(f"시장 대표 종목 조회 실패: {fallback_error}")
            
        # 최종 안전장치: config에서 기본값 또는 안전한 기본값
        return getattr(trading_system.config.trading, 'DEFAULT_STOCKS', ['005930'])
            
    except Exception as e:
        print(f"조건 검색 오류: {e}")
        try:
            # 오류 시에도 동적 조회 시도
            market_leaders = await trading_system.data_collector.get_market_leaders(limit=1)
            if market_leaders:
                return market_leaders
        except:
            pass
        return ['005930']  # 최소한 삼성전자라도

def run_cli():
    """명령행 인터페이스 실행 - 향상된 인자 처리"""
    parser = argparse.ArgumentParser(
        description='AI Trading System v4.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py                              # 대화형 모드
  python main.py --mode analysis              # 분석 모드
  python main.py --mode analysis --symbol 005930 # 삼성전자 분석
  python main.py --mode backtest --strategy momentum # 백테스트
        """
    )
    
    parser.add_argument('--mode', 
                       choices=['interactive', 'analysis', 'backtest', 'auto'], 
                       default='interactive', 
                       help='실행 모드 선택')
    parser.add_argument('--symbol', 
                       type=str, 
                       help='분석할 종목 코드')
    parser.add_argument('--strategy', 
                       type=str, 
                       default='momentum', 
                       choices=['momentum', 'breakout', 'eod'], 
                       help='사용할 전략')
    parser.add_argument('--limit', 
                       type=int, 
                       default=20, 
                       help='분석할 최대 종목 수')
    parser.add_argument('--debug', 
                       action='store_true', 
                       help='디버그 모드 활성화')
    parser.add_argument('--no-interactive', 
                       action='store_true', 
                       help='비대화형 모드 (EOF 에러 방지)')
    
    args = parser.parse_args()
    
    # 디버그 모드 설정
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        print("🐛 디버그 모드 활성화")
    
    try:
        if args.mode == 'interactive':
            # 대화형 모드
            asyncio.run(main())
        elif args.mode == 'analysis':
            # 분석 모드
            asyncio.run(run_analysis_mode(args))
        elif args.mode == 'backtest':
            # 백테스트 모드
            asyncio.run(run_backtest_mode(args))
        elif args.mode == 'auto':
            # 자동화 모드 (EOF 에러 방지)
            asyncio.run(run_automated_mode(args))
    except KeyboardInterrupt:
        print("\n[STOP] 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"[ERROR] 실행 중 치명적 오류: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

async def run_analysis_mode(args):
    """분석 모드 실행 - 향상된 오류 처리"""
    try:
        config, logger = initialize_system()
        from core.trading_system import TradingSystem
        
        trading_system = TradingSystem(trading_enabled=False, backtest_mode=False)
        
        # 컴포넌트 초기화 (retry 로직)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if await trading_system.initialize_components():
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[WARN] 초기화 재시도 ({attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(2)
                else:
                    logger.error("[ERROR] 컴포넌트 초기화 실패")
                    return
        
        logger.info(f"[INFO] 분석 모드 시작 (전략: {args.strategy}, 최대: {args.limit}개)")
        
        try:
            if args.symbol:
                # 특정 종목 분석
                results = await trading_system.analyze_symbols([args.symbol], args.strategy)
            else:
                # 시장 분석
                results = await trading_system.run_market_analysis(args.strategy, args.limit)
            
            # 결과 표시
            if results:
                await trading_system.display_results(results)
                await trading_system.save_results_to_file(results)
                logger.info("[PASS] 분석 완료 및 결과 저장")
            else:
                logger.warning("[WARN] 분석 결과 없음")
                
        except Exception as analysis_error:
            logger.error(f"[ERROR] 분석 실행 중 오류: {analysis_error}")
        finally:
            await trading_system.cleanup()
        
    except Exception as e:
        print(f"[ERROR] 분석 모드 실행 실패: {e}")

async def run_backtest_mode(args):
    """백테스트 모드 실행"""
    try:
        config, logger = initialize_system()
        logger.info("[INFO] 백테스트 모드는 개발 중입니다")
        
        # Phase 6 백테스트 모듈 사용 준비
        try:
            from backtesting.backtesting_engine import BacktestingEngine
            logger.info("[PASS] 백테스트 엔진 준비 완료")
            # TODO: 백테스트 구현
        except ImportError:
            logger.warning("[WARN] 백테스트 모듈이 아직 준비되지 않았습니다")
        
    except Exception as e:
        print(f"[ERROR] 백테스트 모드 실행 실패: {e}")


@async_retry(
    retry_config=RetryConfig(max_attempts=2, base_delay=1.0),
    context="stock_analysis"
)
async def analyze_stock_safely(trading_system, stock_code: str, index: int, total: int):
    """안전한 개별 종목 분석 (에러 복구 포함)"""
    try:
        # 주식 정보 먼저 가져오기
        stock_data = await safe_execute(
            trading_system.data_collector.get_stock_info,
            stock_code,
            fallback_value=None,
            context=f"get_stock_info_{stock_code}"
        )
        
        if not stock_data:
            return {"error": f"주식 정보 조회 실패: {stock_code}"}
        
        print(f"  📊 {stock_data.name} 종합 분석 중...")
        
        # 종합 분석 (올바른 파라미터로)
        analysis_result = await safe_execute(
            trading_system.analysis_engine.analyze_comprehensive,
            stock_code, stock_data.name, stock_data,
            fallback_value={"error": "분석 실패"},
            context=f"analyze_comprehensive_{stock_code}"
        )
        
        if analysis_result and not analysis_result.get('error'):
            print(f"  ✅ {stock_code} 분석 완료")
            return analysis_result
        else:
            return {"error": f"종합 분석 실패: {stock_code}"}
            
    except Exception as e:
        error_recovery.log_error(e, f"analyze_stock_{stock_code}")
        return {"error": str(e)}


async def setup_health_checks(trading_system):
    """시스템 건강 상태 체크 설정"""
    
    def check_python_version():
        return sys.version_info >= (3, 9)
    
    async def check_trading_system():
        return trading_system is not None and hasattr(trading_system, 'data_collector')
    
    async def check_data_collector():
        if not hasattr(trading_system, 'data_collector'):
            return False
        try:
            # 동적 종목으로 연결 테스트
            market_leaders = await trading_system.data_collector.get_market_leaders(limit=1)
            test_stock = market_leaders[0] if market_leaders else "005930"
            
            test_result = await safe_execute(
                trading_system.data_collector.get_stock_info,
                test_stock,
                fallback_value=None,
                context="health_check_data_collector"
            )
            return test_result is not None
        except:
            return False
    
    def check_log_directory():
        return Path("logs").exists()
    
    # 건강 상태 체크 등록
    health_checker.add_health_check("python_version", check_python_version)
    health_checker.add_health_check("trading_system", check_trading_system)
    health_checker.add_health_check("data_collector", check_data_collector)
    health_checker.add_health_check("log_directory", check_log_directory)


if __name__ == "__main__":
    try:
        # Python 버전 체크
        if sys.version_info < (3, 9):
            print("[ERROR] Python 3.9 이상이 필요합니다")
            print(f"현재 버전: {sys.version}")
            sys.exit(1)
        
        run_cli()
        
    except Exception as e:
        print(f"[FATAL] 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)