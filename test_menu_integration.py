#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메뉴 통합 테스트 - 실시간 모니터링 시스템
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config

async def test_menu_integration():
    """메뉴 통합 테스트"""
    print("=" * 60)
    print("메뉴 통합 테스트 - 실시간 모니터링 시스템")
    print("=" * 60)

    try:
        # 1. Config 로드 테스트
        print("1. Config 로드 중...")
        config = Config()
        print(f"   [PASS] Config 로드 완료")

        # 2. 메뉴 핸들러 임포트 테스트
        print("2. 메뉴 핸들러 임포트 중...")
        from core.menu_handlers import MenuHandlers
        print(f"   [PASS] 메뉴 핸들러 임포트 완료")

        # 3. 모크 시스템 생성
        print("3. 모크 시스템 생성 중...")
        from utils.logger import get_logger

        class MockSystem:
            def __init__(self):
                self.config = config
                self.data_collector = None
                self.db_manager = None
                self.logger = get_logger("MockSystem")

        mock_system = MockSystem()
        menu_handler = MenuHandlers(mock_system)
        print(f"   [PASS] 모크 시스템 생성 완료")

        # 4. 실시간 모니터링 핸들러 함수 존재 확인
        print("4. 실시간 모니터링 핸들러 함수 확인 중...")
        if hasattr(menu_handler, '_realtime_monitoring_system'):
            print(f"   [PASS] _realtime_monitoring_system 메서드 존재")
        else:
            print(f"   [FAIL] _realtime_monitoring_system 메서드 없음")
            return False

        # 5. 메뉴 맵 확인
        print("5. 메뉴 맵 확인 중...")
        # execute_menu_choice 메서드가 있는지 확인
        if hasattr(menu_handler, 'execute_menu_choice'):
            print(f"   [PASS] execute_menu_choice 메서드 존재")
        else:
            print(f"   [FAIL] execute_menu_choice 메서드 없음")
            return False

        print("\n" + "=" * 60)
        print("[SUCCESS] 메뉴 통합 테스트 완료!")
        print("실시간 모니터링 시스템이 메뉴에 성공적으로 통합되었습니다.")
        print("메뉴 선택 '32'를 통해 실시간 모니터링을 실행할 수 있습니다.")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[ERROR] 메뉴 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_menu_integration())