#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
계좌 설정 확인 스크립트
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_account_config():
    """계좌 설정 확인"""
    print("=" * 60)
    print("계좌 설정 확인")
    print("=" * 60)
    
    try:
        from config import Config
        
        config = Config()
        
        print("1. 계좌번호 설정:")
        account_number = getattr(config.api, 'KIS_ACCOUNT_NUMBER', '')
        if account_number:
            # 계좌번호 마스킹 처리 (보안)
            if '-' in account_number:
                parts = account_number.split('-')
                masked = f"{parts[0][:4]}****-{parts[1]}"
            else:
                masked = f"{account_number[:4]}****"
            print(f"   계좌번호: {masked}")
        else:
            print("   [ERROR] 계좌번호가 설정되지 않음")
        
        print("\n2. API 키 설정:")
        app_key = getattr(config.api, 'KIS_APP_KEY', '')
        app_secret = getattr(config.api, 'KIS_APP_SECRET', '')
        
        print(f"   APP_KEY: {'설정됨' if app_key else '[ERROR] 없음'}")
        print(f"   APP_SECRET: {'설정됨' if app_secret else '[ERROR] 없음'}")
        
        print("\n3. 모의투자 여부:")
        is_virtual = getattr(config.api, 'KIS_IS_VIRTUAL', False)
        print(f"   모의투자: {'YES' if is_virtual else 'NO'}")
        
        print("\n=" * 40)
        print("확인사항:")
        print("1. HTS에서 보는 계좌번호와 위 계좌번호가 동일한지 확인")
        print("2. 모의투자/실투자 설정이 올바른지 확인") 
        print("3. 계좌에 실제로 보유한 종목:")
        print("   - 생서뷰, 모비데이즈 종목코드 확인 필요")
        print("   - 넷마블랩이 실제로 없다면 매도 처리 확인")
        
    except Exception as e:
        print(f"[ERROR] 설정 확인 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_account_config()