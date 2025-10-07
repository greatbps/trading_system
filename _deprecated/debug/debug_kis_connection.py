#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 연결 상태 확인 및 문제 해결 스크립트
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def debug_kis_connection():
    """KIS API 연결 상태 디버깅"""
    print("KIS API 연결 상태 확인 시작...")
    
    # 1. 토큰 파일 확인
    token_file = Path("data/kis_token.json")
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            expired_at = datetime.fromisoformat(token_data['expired_at'])
            now = datetime.now()
            
            print(f"토큰 정보:")
            print(f"   - 가상모드: {token_data.get('virtual_mode', False)}")
            print(f"   - 만료일: {expired_at}")
            print(f"   - 현재일: {now}")
            print(f"   - 상태: {'만료됨' if expired_at < now else '유효함'}")
            
            if expired_at < now:
                print("WARNING: 토큰이 만료되었습니다. 토큰 재발급이 필요합니다.")
                return False
            else:
                print("OK: 토큰이 유효합니다.")
                
        except Exception as e:
            print(f"ERROR: 토큰 파일 읽기 실패: {e}")
            return False
    else:
        print("ERROR: 토큰 파일이 존재하지 않습니다.")
        return False
    
    # 2. PyKis 모듈 상태 확인
    try:
        import importlib
        pykis_module = importlib.import_module('pykis')
        print("OK: PyKis 모듈 로드 성공")
        
        # API 클래스 확인
        possible_classes = ['Api', 'KisApi', 'PyKis', 'Client']
        api_class = None
        
        for class_name in possible_classes:
            if hasattr(pykis_module, class_name):
                api_class = getattr(pykis_module, class_name)
                print(f"OK: PyKis API 클래스 발견: {class_name}")
                break
        
        if not api_class:
            print("ERROR: PyKis API 클래스를 찾을 수 없습니다.")
            available_attrs = [attr for attr in dir(pykis_module) if not attr.startswith('_')]
            print(f"   사용 가능한 속성: {available_attrs}")
            return False
            
    except ImportError as e:
        print(f"ERROR: PyKis 모듈 로드 실패: {e}")
        print("SOLUTION: pip install PyKis")
        return False
    except Exception as e:
        print(f"ERROR: PyKis 모듈 오류: {e}")
        return False
    
    # 3. 간단한 API 테스트
    try:
        from data_collectors.kis_collector import KISCollector
        from config import Config
        
        config = Config()
        collector = KISCollector(config)
        
        # 연결 상태 확인
        if hasattr(collector, 'check_connection'):
            is_connected = await collector.check_connection()
            print(f"KIS API 연결 상태: {'연결됨' if is_connected else '연결 실패'}")
        else:
            print("WARNING: 연결 상태 확인 메서드가 없습니다.")
        
        return True
        
    except Exception as e:
        print(f"ERROR: KIS API 테스트 실패: {e}")
        return False

def suggest_solutions():
    """문제 해결 방법 제시"""
    print("\n문제 해결 방법:")
    print("1. 토큰 재발급:")
    print("   - KIS 증권 홈페이지 > 나의 API > 토큰 재발급")
    print("   - app_key, app_secret 확인")
    print("   - 가상투자/실투자 모드 확인")
    
    print("\n2. 네트워크 연결 확인:")
    print("   - 인터넷 연결 상태 확인")
    print("   - 방화벽/백신 설정 확인")
    print("   - VPN 사용 시 해제 후 재시도")
    
    print("\n3. PyKis 라이브러리 확인:")
    print("   - pip install --upgrade PyKis")
    print("   - pip uninstall PyKis && pip install PyKis")
    
    print("\n4. 임시 해결책:")
    print("   - 기본 샘플 데이터로 전략 테스트")
    print("   - 백테스팅 모드로 전환")

async def create_sample_data():
    """샘플 데이터 생성 (테스트용)"""
    print("\n테스트용 샘플 데이터 생성...")
    
    sample_stocks = {
        "005930": {"name": "삼성전자", "price": 71000, "change": 1.5, "volume": 15000000, "market_cap": 425000},
        "000660": {"name": "SK하이닉스", "price": 89000, "change": 2.1, "volume": 8000000, "market_cap": 65000},
        "035420": {"name": "NAVER", "price": 185000, "change": -0.8, "volume": 3000000, "market_cap": 30000},
        "051910": {"name": "LG화학", "price": 410000, "change": 1.2, "volume": 1500000, "market_cap": 29000},
        "006400": {"name": "삼성SDI", "price": 390000, "change": 3.2, "volume": 2000000, "market_cap": 18000}
    }
    
    # 샘플 데이터를 파일로 저장
    sample_file = Path("data/sample_market_data.json")
    sample_file.parent.mkdir(exist_ok=True)
    
    with open(sample_file, 'w', encoding='utf-8') as f:
        json.dump(sample_stocks, f, indent=2, ensure_ascii=False)
    
    print(f"OK: 샘플 데이터 저장: {sample_file}")
    return sample_stocks

def show_quick_fix_menu():
    """빠른 해결책 메뉴"""
    print("\n빠른 해결책:")
    print("1. 샘플 데이터로 스마트머니 전략 테스트")
    print("2. KIS API 토큰 재발급 가이드")
    print("3. 백테스팅 모드로 전환")
    print("4. 시스템 설정 확인")
    print("0. 메인 메뉴로 돌아가기")
    
    choice = input("\n선택하세요 (0-4): ").strip()
    return choice

async def test_smart_money_strategy_with_sample():
    """샘플 데이터로 스마트머니 전략 테스트"""
    print("\n스마트머니 전략 샘플 테스트 시작...")
    
    # 샘플 데이터 생성
    sample_data = await create_sample_data()
    
    try:
        from strategies.smart_money_strategy import SmartMoneyStrategy
        from config import Config
        
        config = Config()
        strategy = SmartMoneyStrategy(config)
        
        print("OK: 스마트머니 전략 로드 성공")
        print("전략 정보:")
        
        strategy_info = strategy.get_strategy_info()
        for key, value in strategy_info.items():
            if isinstance(value, list):
                print(f"   - {key}: {', '.join(value)}")
            else:
                print(f"   - {key}: {value}")
        
        print(f"\n{len(sample_data)}개 샘플 종목으로 전략 테스트 준비 완료")
        print("   실제 데이터 연결 후 본격적인 분석이 가능합니다.")
        
        return True
        
    except Exception as e:
        print(f"ERROR: 스마트머니 전략 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("KIS API 연결 문제 해결 도구")
    print("=" * 60)
    
    # KIS API 상태 확인
    connection_ok = asyncio.run(debug_kis_connection())
    
    if not connection_ok:
        suggest_solutions()
        
        while True:
            choice = show_quick_fix_menu()
            
            if choice == '1':
                asyncio.run(test_smart_money_strategy_with_sample())
            elif choice == '2':
                print("\nKIS API 토큰 재발급 가이드:")
                print("1. KIS 증권 홈페이지 로그인")
                print("2. 나의 API 메뉴 접속")
                print("3. 토큰 재발급 클릭")
                print("4. app_key, app_secret 복사")
                print("5. data/kis_token.json 파일 업데이트")
            elif choice == '3':
                print("\n백테스팅 모드 전환:")
                print("과거 데이터를 사용한 전략 성과 검증이 가능합니다.")
                asyncio.run(create_sample_data())
            elif choice == '4':
                print("\n시스템 설정 확인:")
                print("config.py 파일의 KIS API 설정을 확인하세요.")
            elif choice == '0':
                break
            else:
                print("잘못된 선택입니다.")
    
    else:
        print("\nOK: KIS API 연결이 정상입니다!")
        print("메인 시스템에서 AI 종합 분석을 다시 실행해보세요.")