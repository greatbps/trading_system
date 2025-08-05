#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 Gemini CLI 테스트
"""

import asyncio
import subprocess
import sys
import os
from analyzers.gemini_analyzer import GeminiAnalyzer
from config import Config

async def main():
    print("=" * 50)
    print("Gemini CLI 테스트")
    print("=" * 50)
    
    # 1. CLI 설치 확인
    print("\n1. Gemini CLI 설치 확인:")
    cli_command = None
    # Node.js로 직접 실행하는 방식 시도
    node_script_path = '/c/Users/great/AppData/Roaming/npm/node_modules/@google/gemini-cli/dist/index.js'
    possible_commands = [
        ['gemini', '--version'],
        ['node', node_script_path, '--version'],
        ['/c/Users/great/AppData/Roaming/npm/gemini.cmd', '--version'],
    ]
    
    for cmd in possible_commands:
        try:
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                cli_command = cmd
                print(f"[OK] Gemini CLI 버전: {result.stdout.strip()}")
                print(f"[OK] CLI 명령: {' '.join(cmd)}")
                break
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not cli_command:
        print("[ERROR] Gemini CLI를 찾을 수 없습니다")
        return
    
    # 2. API 키 확인
    print("\n2. API 키 확인:")
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if api_key:
        print(f"[OK] API 키 설정됨: {api_key[:10]}...")
    else:
        print("[ERROR] API 키가 설정되지 않았습니다")
        return
    
    # 3. GeminiAnalyzer 테스트
    print("\n3. GeminiAnalyzer 테스트:")
    try:
        config = Config()
        analyzer = GeminiAnalyzer(config)
        
        if analyzer.cli_available:
            print("[OK] GeminiAnalyzer CLI 사용 가능")
        else:
            print("[ERROR] GeminiAnalyzer CLI 사용 불가")
            return
            
        # 간단한 테스트
        test_prompt = "Hello, this is a test. Please respond with 'Test successful'."
        response = await analyzer._call_gemini_cli(test_prompt)
        print(f"[OK] API 응답: {response[:100]}...")
        
        print("\n" + "=" * 50)
        print("[SUCCESS] Gemini CLI 전환 성공!")
        print("Python SDK 없이 CLI로 작동합니다")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main())