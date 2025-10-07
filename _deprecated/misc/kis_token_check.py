#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 토큰 상태 확인 및 해결방안 제시
"""

import json
from datetime import datetime
from pathlib import Path

def check_kis_token():
    """KIS API 토큰 상태 확인"""
    print("=" * 60)
    print("KIS API 토큰 상태 확인")
    print("=" * 60)
    
    # 토큰 파일 확인
    token_file = Path("data/kis_token.json")
    if not token_file.exists():
        print("ERROR: 토큰 파일이 존재하지 않습니다.")
        return False
    
    try:
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        expired_at = datetime.fromisoformat(token_data['expired_at'])
        now = datetime.now()
        
        print(f"토큰 정보:")
        print(f"   - 가상모드: {token_data.get('virtual_mode', False)}")
        print(f"   - 만료일: {expired_at}")
        print(f"   - 현재일: {now}")
        
        if expired_at < now:
            print(f"   - 상태: 만료됨")
            print("\n토큰이 만료되었습니다!")
            suggest_token_renewal()
            return False
        else:
            print(f"   - 상태: 유효함")
            print("\n토큰이 유효합니다.")
            return True
            
    except Exception as e:
        print(f"ERROR: 토큰 파일 읽기 실패: {e}")
        return False

def suggest_token_renewal():
    """토큰 재발급 방법 제시"""
    print("\n" + "=" * 40)
    print("토큰 재발급 방법")
    print("=" * 40)
    
    print("1. KIS 증권 홈페이지 로그인")
    print("   - https://securities.koreainvestment.com/")
    
    print("\n2. API 서비스 신청/관리 메뉴 접속")
    print("   - 마이페이지 > API서비스 신청/관리")
    
    print("\n3. 토큰 재발급")
    print("   - 기존 토큰 조회 > 토큰재발급 클릭")
    
    print("\n4. 새 토큰 정보로 파일 업데이트")
    print("   - data/kis_token.json 파일의 다음 정보 수정:")
    print("     * access_token")
    print("     * expired_at") 
    print("     * created_at")
    
    print("\n5. 임시 해결방안:")
    print("   - 샘플 데이터로 전략 테스트 가능")
    print("   - 백테스팅 모드로 전환 가능")

def check_pykis_installation():
    """PyKis 설치 상태 확인"""
    try:
        import pykis
        print("OK: PyKis 모듈이 설치되어 있습니다.")
        
        # API 클래스 확인
        possible_classes = ['Api', 'KisApi', 'PyKis', 'Client']
        api_class = None
        
        for class_name in possible_classes:
            if hasattr(pykis, class_name):
                api_class = getattr(pykis, class_name)
                print(f"OK: PyKis API 클래스 발견: {class_name}")
                break
        
        if not api_class:
            print("WARNING: PyKis API 클래스를 찾을 수 없습니다.")
            available_attrs = [attr for attr in dir(pykis) if not attr.startswith('_')]
            print(f"   사용 가능한 속성: {available_attrs}")
            
        return True
        
    except ImportError:
        print("ERROR: PyKis 모듈이 설치되지 않았습니다.")
        print("SOLUTION: pip install PyKis")
        return False
    except Exception as e:
        print(f"ERROR: PyKis 모듈 오류: {e}")
        return False

if __name__ == "__main__":
    # 토큰 상태 확인
    token_ok = check_kis_token()
    
    print("\n" + "-" * 60)
    
    # PyKis 설치 상태 확인
    pykis_ok = check_pykis_installation()
    
    print("\n" + "=" * 60)
    if token_ok and pykis_ok:
        print("진단 결과: KIS API 사용 준비 완료")
        print("메인 시스템에서 실거래 데이터 수집이 가능합니다.")
    else:
        print("진단 결과: 문제 발견")
        if not token_ok:
            print("- 토큰 재발급 필요")
        if not pykis_ok:
            print("- PyKis 설치/재설치 필요")
        
        print("\n임시 해결방안:")
        print("- python -c \"import asyncio; from debug_kis_connection import create_sample_data; asyncio.run(create_sample_data())\"")
        print("- 샘플 데이터로 스마트머니 전략 테스트 가능")
    print("=" * 60)