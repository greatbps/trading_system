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

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

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
        trading_system = TradingSystem(trading_enabled=False, backtest_mode=False)
        
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
        
        # 대화형 모드 실행
        await trading_system.run_interactive_mode()
        
        # 정상 종료
        await trading_system.cleanup()
        return True
        
    except KeyboardInterrupt:
        print("\n[STOP] 사용자에 의한 중단")
        return True
    except Exception as e:
        print(f"[ERROR] 치명적 오류: {e}")
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
                       choices=['interactive', 'analysis', 'backtest'], 
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