#!/usr/bin/env python3
"""
EOF 에러 테스트 스크립트
"""

import sys

def test_interactive_input():
    """대화형 입력 테스트"""
    print("대화형 모드 테스트")
    
    try:
        # stdin이 없는 환경에서 input() 호출
        response = input("메뉴를 선택하세요: ")
        print(f"선택: {response}")
    except EOFError as e:
        print(f"❌ EOF 에러 발생: {e}")
        return False
    except Exception as e:
        print(f"❌ 기타 에러: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print(f"stdin 상태: {sys.stdin}")
    print(f"stdin readable: {sys.stdin.readable()}")
    
    if test_interactive_input():
        print("✅ 대화형 입력 성공")
    else:
        print("❌ 대화형 입력 실패")