#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 Gemini CLI 연결 테스트
"""

import asyncio
import subprocess
import sys
import os
from analyzers.gemini_analyzer import GeminiAnalyzer
from config import Config

async def main():
    print("=" * 50)
    print("Gemini CLI 빠른 테스트")
    print("=" * 50)
    
    # 1. CLI 버전 확인
    print("\n1. CLI 버전 확인:")
    try:
        result = subprocess.run(['node', 'C:\\Users\\great\\AppData\\Roaming\\npm\\node_modules\\@google\\gemini-cli\\dist\\index.js', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"[OK] Gemini CLI 버전: {result.stdout.strip()}")
        else:
            print(f"[ERROR] CLI 오류: {result.stderr}")
            return
    except Exception as e:
        print(f"[ERROR] CLI 실행 실패: {e}")
        return
    
    # 2. API 키 확인
    print("\n2. API 키 확인:")
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if api_key:
        print(f"[OK] API 키 설정됨: {api_key[:10]}...")
    else:
        print("[ERROR] API 키가 설정되지 않았습니다")
        return
    
    # 3. GeminiAnalyzer 초기화 테스트
    print("\n3. GeminiAnalyzer 초기화:")
    try:
        config = Config()
        analyzer = GeminiAnalyzer(config)
        
        if analyzer.cli_available:
            print("[OK] GeminiAnalyzer CLI 사용 가능")
            print(f"[OK] CLI 명령: {analyzer.cli_command}")
        else:
            print("[ERROR] GeminiAnalyzer CLI 사용 불가")
            return
            
        print("\n" + "=" * 50)
        print("[SUCCESS] 모든 기본 설정 완료!")
        print("Gemini CLI 전환이 성공적으로 완료되었습니다!")
        print("이제 실제 trading_system에서 사용할 수 있습니다!")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())