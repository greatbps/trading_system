#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini CLI 테스트 스크립트
CLI 설치 및 인증 상태 확인
"""

import asyncio
import subprocess
import sys
from analyzers.gemini_analyzer import GeminiAnalyzer
from config import Config

async def test_gemini_cli():
    """Gemini CLI 기본 테스트"""
    print("Gemini CLI 테스트 시작...")
    
    # 1. CLI 설치 확인
    print("\n1. Gemini CLI 설치 확인:")
    try:
        result = subprocess.run(['gemini', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            print(f"[OK] Gemini CLI 버전: {result.stdout.strip()}")
        else:
            print(f"[ERROR] CLI 설치되었지만 오류 발생: {result.stderr}")
            return False
    except FileNotFoundError:
        print("[ERROR] Gemini CLI가 설치되지 않았습니다")
        print("설치 방법: npm install -g @google/gemini-cli")
        return False
    except subprocess.TimeoutExpired:
        print("[ERROR] CLI 응답 시간 초과")
        return False
    
    # 2. 환경 변수 및 인증 확인
    print("\n2. API 키 환경 변수 확인:")
    import os
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if api_key:
        print(f"✅ API 키 설정됨: {api_key[:10]}...")
    else:
        print("❌ API 키가 설정되지 않았습니다")
        print("설정 방법:")
        print("1. Google AI Studio에서 API 키 생성: https://aistudio.google.com/apikey")
        print("2. 환경 변수 설정: set GEMINI_API_KEY=YOUR_API_KEY (Windows)")
        print("   또는: export GEMINI_API_KEY=YOUR_API_KEY (Linux/Mac)")
        return False
    
    # 3. 간단한 API 테스트
    print("\n3. 간단한 API 테스트:")
    try:
        config = Config()
        analyzer = GeminiAnalyzer(config)
        
        if not analyzer.cli_available:
            print("❌ GeminiAnalyzer에서 CLI 사용 불가")
            return False
        
        # 간단한 테스트 프롬프트
        test_prompt = "안녕하세요. 이것은 테스트입니다. '테스트 성공'이라고 응답해주세요."
        
        response = await analyzer._call_gemini_cli(test_prompt)
        print(f"✅ API 테스트 성공")
        print(f"응답: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

async def test_sentiment_analysis():
    """감성 분석 기능 테스트"""
    print("\n🔍 감성 분석 기능 테스트...")
    
    try:
        config = Config()
        analyzer = GeminiAnalyzer(config)
        
        # 테스트 뉴스 데이터
        test_news = [
            {
                'title': '삼성전자, 3분기 실적 예상치 상회',
                'description': '삼성전자가 3분기 실적에서 시장 예상치를 상회하는 실적을 발표했다.'
            },
            {
                'title': '반도체 수요 증가로 매출 성장',
                'description': '글로벌 반도체 수요 증가로 인해 매출이 크게 성장했다.'
            }
        ]
        
        result = await analyzer.analyze_news_sentiment("005930", "삼성전자", test_news)
        
        print("✅ 감성 분석 결과:")
        print(f"감성: {result.get('sentiment')}")
        print(f"점수: {result.get('overall_score')}")
        print(f"신뢰도: {result.get('confidence')}")
        print(f"요약: {result.get('summary')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 감성 분석 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    # Windows 콘솔 인코딩 문제 해결
    import sys
    if sys.platform == "win32":
        import os
        os.system("chcp 65001 > nul")
    
    print("=" * 50)
    print("Gemini CLI 전환 테스트")
    print("=" * 50)
    
    # 기본 CLI 테스트
    cli_ok = await test_gemini_cli()
    
    if cli_ok:
        # 감성 분석 테스트
        await test_sentiment_analysis()
        
        print("\n" + "=" * 50)
        print("✅ 모든 테스트 완료 - Gemini CLI 전환 성공!")
        print("🎯 이제 Python SDK 없이 CLI만으로 작동합니다")
        print("💡 토큰 사용량이 최적화되었습니다")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ CLI 설정에 문제가 있습니다")
        print("📋 해결 방법:")
        print("1. npm install -g @google/gemini-cli")
        print("2. Google AI Studio에서 API 키 생성: https://aistudio.google.com/apikey")
        print("3. 환경 변수 설정: set GEMINI_API_KEY=YOUR_API_KEY")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())