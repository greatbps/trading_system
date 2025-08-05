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
from typing import Dict, List, Any

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
╔══════════════════════════════════════════════════════════════╗
║                    🚀 AI Trading System v3.0                ║
║                                                              ║
║  📊 5개 영역 통합 분석: 기술적 + 펀더멘털 + 뉴스 + 수급 + 패턴  ║
║  🤖 KIS HTS 조건검색 연동 + 실시간 정밀 매매                   ║
║  💡 PostgreSQL 기반 데이터 관리                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 작업 디렉토리: {Path.cwd()}")
    print()

async def main():
    """메인 실행 함수"""
    try:
        print_banner()
        
        # 설정 초기화
        config = Config()
        logger.info("✅ 설정 초기화 완료")
        
        # 트레이딩 시스템 임포트 및 초기화
        try:
            from core.trading_system import TradingSystem
            logger.info("✅ TradingSystem 임포트 성공")
        except ImportError as e:
            logger.error(f"❌ TradingSystem 임포트 실패: {e}")
            return False
        
        # 시스템 초기화
        trading_system = TradingSystem(trading_enabled=False, backtest_mode=False)
        
        # 컴포넌트 초기화
        logger.info("🔧 컴포넌트 초기화 중...")
        if not await trading_system.initialize_components():
            logger.error("❌ 컴포넌트 초기화 실패")
            return False
        
        logger.info("✅ 시스템 초기화 완료!")
        
        # 대화형 모드 실행
        await trading_system.run_interactive_mode()
        
        # 시스템 정리
        await trading_system.cleanup()
        
        return True
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자에 의한 중단")
        return True
    except Exception as e:
        logger.error(f"❌ 시스템 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_cli():
    """명령행 인터페이스 실행"""
    parser = argparse.ArgumentParser(description='AI Trading System')
    parser.add_argument('--mode', choices=['interactive', 'analysis', 'backtest'], 
                       default='interactive', help='실행 모드 선택')
    parser.add_argument('--symbol', type=str, help='분석할 종목 코드')
    parser.add_argument('--strategy', type=str, default='momentum', 
                       choices=['momentum', 'breakout', 'eod'], help='사용할 전략')
    parser.add_argument('--limit', type=int, default=20, help='분석할 최대 종목 수')
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        # 대화형 모드
        asyncio.run(main())
    elif args.mode == 'analysis':
        # 분석 모드
        asyncio.run(run_analysis_mode(args))
    elif args.mode == 'backtest':
        # 백테스트 모드
        asyncio.run(run_backtest_mode(args))

async def run_analysis_mode(args):
    """분석 모드 실행"""
    try:
        config = Config()
        from core.trading_system import TradingSystem
        
        trading_system = TradingSystem(trading_enabled=False, backtest_mode=False)
        
        if not await trading_system.initialize_components():
            logger.error("❌ 컴포넌트 초기화 실패")
            return
        
        logger.info(f"📊 분석 모드 시작 (전략: {args.strategy}, 최대: {args.limit}개)")
        
        if args.symbol:
            # 특정 종목 분석
            results = await trading_system.analyze_symbols([args.symbol], args.strategy)
        else:
            # 시장 분석
            results = await trading_system.run_market_analysis(args.strategy, args.limit)
        
        # 결과 표시
        await trading_system.display_results(results)
        
        # 파일 저장
        if results:
            await trading_system.save_results_to_file(results)
        
        await trading_system.cleanup()
        
    except Exception as e:
        logger.error(f"❌ 분석 모드 실행 실패: {e}")

async def run_backtest_mode(args):
    """백테스트 모드 실행"""
    try:
        logger.info("🔄 백테스트 모드는 개발 중입니다")
        # TODO: 백테스트 구현
        
    except Exception as e:
        logger.error(f"❌ 백테스트 모드 실행 실패: {e}")

if __name__ == "__main__":
    try:
        # Python 버전 체크
        if sys.version_info < (3, 9):
            print("❌ Python 3.9 이상이 필요합니다")
            print(f"현재 버전: {sys.version}")
            sys.exit(1)
        
        run_cli()
        
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)