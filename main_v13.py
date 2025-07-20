#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/main.py

AI Trading System - 메인 진입점
"""

import sys
import asyncio
from pathlib import Path

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
async def main():
    """메인 함수"""
    trading_system = None
    
    try:
        # TradingSystem 초기화 및 실행
        from core.trading_system import TradingSystem
        
        trading_system = TradingSystem()
        
        # 명령행 인수가 있으면 CLI 모드, 없으면 대화형 모드
        if len(sys.argv) > 1:
            success = await trading_system.run_command_line_mode()
            sys.exit(0 if success else 1)
        else:
            await trading_system.run_interactive_mode()
    
    except KeyboardInterrupt:
        print("\n🛑 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        import traceback
        traceback.print_exc()  # 디버깅을 위한 스택 트레이스
        sys.exit(1)
    finally:
        # 리소스 정리
        if trading_system:
            try:
                await trading_system.cleanup()
            except Exception as e:
                print(f"⚠️ 정리 중 오류: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        sys.exit(1)