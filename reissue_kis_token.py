#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 토큰 자동 재발급 스크립트
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """환경 변수 로드"""
    # .env 파일 로드
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print("OK: .env 파일 로드 완료")
    else:
        print("WARNING: .env 파일을 찾을 수 없습니다")
    
    # 필수 환경 변수 확인
    app_key = os.getenv('KIS_APP_KEY')
    app_secret = os.getenv('KIS_APP_SECRET')
    
    if not app_key or not app_secret:
        print("ERROR: KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다")
        return None, None
    
    print(f"OK: KIS API 키 확인됨: {app_key[:10]}...")
    return app_key, app_secret


def reissue_access_token(app_key, app_secret, virtual_mode=True):
    """KIS API 액세스 토큰 재발급"""
    
    # API 엔드포인트 (가상투자/실투자)
    if virtual_mode:
        base_url = "https://openapivts.koreainvestment.com:29443"
        print("INFO: 가상투자 모드로 토큰 재발급 시작...")
    else:
        base_url = "https://openapi.koreainvestment.com:9443"  
        print("INFO: 실투자 모드로 토큰 재발급 시작...")
    
    url = f"{base_url}/oauth2/tokenP"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    
    data = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    try:
        print("INFO: KIS API 서버에 토큰 요청 중...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            
            if "access_token" in token_data:
                print("SUCCESS: 새 토큰 발급 성공!")
                return token_data
            else:
                print(f"ERROR: 토큰 발급 실패: {token_data}")
                return None
        else:
            print(f"ERROR: API 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: 네트워크 오류: {e}")
        return None
    except Exception as e:
        print(f"ERROR: 예상치 못한 오류: {e}")
        return None


def save_token_to_file(token_data, app_key, app_secret, virtual_mode=True):
    """토큰을 파일에 저장"""
    
    # 현재 시간 및 만료 시간 계산 (토큰은 24시간 유효)
    now = datetime.now()
    expires_in = token_data.get('expires_in', 86400)  # 기본 24시간
    expired_at = now + timedelta(seconds=expires_in)
    
    # 저장할 데이터 구성
    save_data = {
        "access_token": token_data["access_token"],
        "expired_at": expired_at.isoformat(),
        "app_key": app_key,
        "app_secret": app_secret,
        "virtual_mode": virtual_mode,
        "created_at": now.isoformat(),
        "cache_version": "2.0"
    }
    
    # 데이터 디렉토리 생성
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 파일 저장
    token_file = data_dir / "kis_token.json"
    try:
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"SUCCESS: 토큰 파일 저장 완료: {token_file}")
        print(f"INFO: 토큰 만료일: {expired_at}")
        return True
        
    except Exception as e:
        print(f"ERROR: 파일 저장 실패: {e}")
        return False


def verify_token_file():
    """저장된 토큰 파일 검증"""
    token_file = Path("data/kis_token.json")
    
    if not token_file.exists():
        print("ERROR: 토큰 파일이 생성되지 않았습니다")
        return False
    
    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        expired_at = datetime.fromisoformat(data['expired_at'])
        now = datetime.now()
        
        if expired_at > now:
            print("SUCCESS: 토큰 파일 검증 성공 - 유효한 토큰")
            time_left = expired_at - now
            hours = int(time_left.total_seconds() / 3600)
            print(f"INFO: 남은 시간: 약 {hours}시간")
            return True
        else:
            print("ERROR: 생성된 토큰이 이미 만료됨")
            return False
            
    except Exception as e:
        print(f"ERROR: 토큰 파일 검증 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("KIS API 토큰 자동 재발급")
    print("=" * 60)
    
    # 1. 환경 변수 로드
    app_key, app_secret = load_environment()
    if not app_key or not app_secret:
        print("\nERROR: 필수 환경 변수가 설정되지 않았습니다")
        print("TIP: .env 파일에 다음 항목을 설정하세요:")
        print("   KIS_APP_KEY=your_app_key")
        print("   KIS_APP_SECRET=your_app_secret")
        return False
    
    # 2. 가상투자/실투자 모드 확인 (기존 설정 유지)
    token_file = Path("data/kis_token.json")
    virtual_mode = True  # 기본값
    
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                existing_data = json.load(f)
            virtual_mode = existing_data.get('virtual_mode', True)
            print(f"INFO: 기존 설정 사용: {'가상투자' if virtual_mode else '실투자'} 모드")
        except:
            print("INFO: 기본값 사용: 가상투자 모드")
    
    # 3. 토큰 재발급
    token_data = reissue_access_token(app_key, app_secret, virtual_mode)
    if not token_data:
        print("\nERROR: 토큰 재발급 실패")
        return False
    
    # 4. 파일 저장
    if not save_token_to_file(token_data, app_key, app_secret, virtual_mode):
        print("\nERROR: 토큰 저장 실패")
        return False
    
    # 5. 검증
    if verify_token_file():
        print("\nSUCCESS: 토큰 재발급 및 저장이 성공적으로 완료되었습니다!")
        print("TIP: 이제 메인 시스템에서 실시간 데이터 수집이 가능합니다.")
        return True
    else:
        print("\nERROR: 토큰 검증 실패")
        return False


if __name__ == "__main__":
    success = main()
    print("=" * 60)
    
    if success:
        exit(0)
    else:
        exit(1)