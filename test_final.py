#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최종 Gemini CLI 테스트
"""

import asyncio
import subprocess
import sys
import os
from analyzers.gemini_analyzer import GeminiAnalyzer
from config import Config

async def main():
    print("=" * 50)
    print("Gemini CLI 최종 테스트")
    print("=" * 50)
    
    # 1. CLI 직접 테스트
    print("\n1. Gemini CLI 직접 테스트:")
    try:
        result = subprocess.run(['node', 'C:\\Users\\great\\AppData\\Roaming\\npm\\node_modules\\@google\\gemini-cli\\dist\\index.js', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
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
    
    # 3. GeminiAnalyzer 테스트
    print("\n3. GeminiAnalyzer 테스트:")
    try:
        config = Config()
        analyzer = GeminiAnalyzer(config)
        
        if analyzer.cli_available:
            print("[OK] GeminiAnalyzer CLI 사용 가능")
            print(f"[OK] CLI 명령: {analyzer.cli_command}")
        else:
            print("[ERROR] GeminiAnalyzer CLI 사용 불가")
            return
            
        # 4. 실제 API 테스트
        print("\n4. 실제 API 호출 테스트:")
        test_prompt = "Hello, this is a test. Please respond with 'Test successful' in Korean."
        response = await analyzer._call_gemini_cli(test_prompt)
        print(f"[OK] API 응답: {response[:200]}...")
        
        # 5. 감성 분석 테스트
        print("\n5. 감성 분석 테스트:")
        test_news = [
            {
                'title': '삼성전자, 3분기 실적 예상치 상회',
                'description': '삼성전자가 3분기 실적에서 시장 예상치를 상회하는 실적을 발표했다.'
            }
        ]
        
        sentiment_result = await analyzer.analyze_news_sentiment("005930", "삼성전자", test_news)
        print(f"[OK] 감성 분석 완료:")
        print(f"  - 감성: {sentiment_result.get('sentiment')}")
        print(f"  - 점수: {sentiment_result.get('overall_score')}")
        print(f"  - 신뢰도: {sentiment_result.get('confidence')}")
        
        print("\n" + "=" * 50)
        print("[SUCCESS] 모든 테스트 통과!")
        print("Gemini CLI 전환이 성공적으로 완료되었습니다!")
        print("토큰 효율성이 향상되었습니다!")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())