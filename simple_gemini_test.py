#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 Gemini API 테스트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import Config
    from analyzers.gemini_analyzer import GeminiAnalyzer
    
    async def test_gemini():
        print("Gemini API 테스트 시작...")
        
        config = Config()
        if not config.api.GEMINI_API_KEY:
            print("GEMINI_API_KEY가 설정되지 않았습니다.")
            return False
        
        gemini_analyzer = GeminiAnalyzer(config)
        
        if not gemini_analyzer.model:
            print("Gemini 모델 초기화 실패")
            return False
        
        print("Gemini API 초기화 성공!")
        
        # 간단한 테스트
        test_news = [
            {
                'title': '삼성전자 실적 호조',
                'description': '삼성전자가 반도체 매출 증가로 좋은 실적을 기록했다.'
            }
        ]
        
        result = await gemini_analyzer.analyze_news_sentiment("005930", "삼성전자", test_news)
        
        print(f"감성 분석 결과:")
        print(f"  감성: {result.get('sentiment', 'N/A')}")
        print(f"  점수: {result.get('overall_score', 'N/A')}")
        print(f"  신뢰도: {result.get('confidence', 'N/A')}")
        
        return True
    
    if __name__ == "__main__":
        asyncio.run(test_gemini())
        
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()