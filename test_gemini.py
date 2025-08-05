#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini API 통합 테스트 스크립트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from analyzers.gemini_analyzer import GeminiAnalyzer
from analyzers.sentiment_analyzer import SentimentAnalyzer
from data_collectors.news_collector import NewsCollector


async def test_gemini_api():
    """Gemini API 기본 연결 테스트"""
    print("🧪 Gemini API 기본 연결 테스트...")
    
    try:
        config = Config()
        gemini_analyzer = GeminiAnalyzer(config)
        
        if not gemini_analyzer.model:
            print("❌ Gemini API 키가 설정되지 않았거나 초기화 실패")
            return False
        
        # 간단한 텍스트 생성 테스트
        test_prompt = "안녕하세요! 간단한 응답을 해주세요."
        response = await gemini_analyzer._call_gemini_api(test_prompt)
        
        if response:
            print(f"✅ Gemini API 연결 성공")
            print(f"📝 응답: {response[:100]}...")
            return True
        else:
            print("❌ Gemini API 응답 없음")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API 테스트 실패: {e}")
        return False


async def test_sentiment_analysis():
    """감성 분석 테스트"""
    print("\n🧪 Gemini 감성 분석 테스트...")
    
    try:
        config = Config()
        gemini_analyzer = GeminiAnalyzer(config)
        
        # 테스트 뉴스 데이터
        test_news = [
            {
                'title': '삼성전자, 반도체 매출 급증으로 사상 최대 실적 달성',
                'description': '삼성전자가 글로벌 반도체 수요 증가에 힘입어 분기 사상 최대 매출을 기록했다고 발표했다.'
            },
            {
                'title': '삼성전자, AI 칩 대량 수주로 주가 급등 전망',
                'description': '삼성전자가 글로벌 AI 기업들로부터 대량 칩 수주를 받아 향후 실적 개선이 기대된다.'
            }
        ]
        
        result = await gemini_analyzer.analyze_news_sentiment("005930", "삼성전자", test_news)
        
        print(f"✅ 감성 분석 완료")
        print(f"📊 감성: {result.get('sentiment', 'N/A')}")
        print(f"📊 점수: {result.get('overall_score', 'N/A')}")
        print(f"📊 신뢰도: {result.get('confidence', 'N/A')}")
        print(f"📝 요약: {result.get('summary', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 감성 분석 테스트 실패: {e}")
        return False


async def test_market_impact_analysis():
    """시장 영향도 분석 테스트"""
    print("\n🧪 Gemini 시장 영향도 분석 테스트...")
    
    try:
        config = Config()
        gemini_analyzer = GeminiAnalyzer(config)
        
        # 테스트 뉴스 데이터
        test_news = [
            {
                'title': '삼성전자, 차세대 AI 칩 양산 시작',
                'description': '삼성전자가 차세대 AI 칩의 양산을 시작하며 글로벌 AI 시장에서의 경쟁력을 강화하고 있다.'
            }
        ]
        
        result = await gemini_analyzer.analyze_market_impact("005930", "삼성전자", test_news)
        
        print(f"✅ 시장 영향도 분석 완료")
        print(f"📊 영향도: {result.get('impact_level', 'N/A')}")
        print(f"📊 점수: {result.get('impact_score', 'N/A')}")
        print(f"📊 가격 방향: {result.get('price_direction', 'N/A')}")
        print(f"📊 추천: {result.get('recommendation', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 시장 영향도 분석 테스트 실패: {e}")
        return False


async def test_sentiment_analyzer():
    """SentimentAnalyzer 통합 테스트"""
    print("\n🧪 SentimentAnalyzer 통합 테스트...")
    
    try:
        config = Config()
        sentiment_analyzer = SentimentAnalyzer(config)
        
        # 테스트 뉴스 데이터
        test_news = [
            {
                'title': 'SK하이닉스, AI 메모리 시장 선점으로 수익성 개선',
                'description': 'SK하이닉스가 AI 메모리 시장을 선점하며 수익성이 크게 개선되고 있다.'
            }
        ]
        
        result = await sentiment_analyzer.analyze("000660", "SK하이닉스", test_news)
        
        print(f"✅ SentimentAnalyzer 테스트 완료")
        print(f"📊 전체 점수: {result.get('overall_score', 'N/A')}")
        print(f"📊 신호 강도: {result.get('signal_strength', 'N/A')}")
        print(f"📊 뉴스 감성: {result.get('news_sentiment', 'N/A')}")
        print(f"📊 트렌드: {result.get('trend', 'N/A')}")
        
        # Gemini 추가 정보 확인
        if 'positive_factors' in result:
            print(f"📈 긍정 요인: {result.get('positive_factors', [])}")
        if 'negative_factors' in result:
            print(f"📉 부정 요인: {result.get('negative_factors', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ SentimentAnalyzer 테스트 실패: {e}")
        return False


async def test_news_collector_gemini():
    """NewsCollector Gemini 통합 테스트"""
    print("\n🧪 NewsCollector Gemini 통합 테스트...")
    
    try:
        config = Config()
        news_collector = NewsCollector(config)
        
        # Gemini 분석 테스트
        result = await news_collector.analyze_with_gemini("NAVER", "035420")
        
        print(f"✅ NewsCollector Gemini 분석 완료")
        print(f"📊 뉴스 개수: {result.get('news_count', 'N/A')}")
        
        sentiment = result.get('sentiment', {})
        print(f"📊 감성: {sentiment.get('overall_sentiment', 'N/A')}")
        print(f"📊 감성 점수: {sentiment.get('overall_score', 'N/A')}")
        
        impact = result.get('market_impact', {})
        print(f"📊 시장 영향도: {impact.get('impact_level', 'N/A')}")
        print(f"📊 추천: {impact.get('recommendation', 'N/A')}")
        
        assessment = result.get('final_assessment', {})
        print(f"📊 투자 등급: {assessment.get('investment_grade', 'N/A')}")
        print(f"📊 매매 전략: {assessment.get('trading_strategy', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ NewsCollector Gemini 테스트 실패: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    print("🚀 Gemini API 통합 테스트 시작\n")
    
    tests = [
        ("Gemini API 기본 연결", test_gemini_api),
        ("Gemini 감성 분석", test_sentiment_analysis),
        ("Gemini 시장 영향도 분석", test_market_impact_analysis),
        ("SentimentAnalyzer 통합", test_sentiment_analyzer),
        ("NewsCollector Gemini 통합", test_news_collector_gemini)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name} 테스트")
        print('='*50)
        
        try:
            success = await test_func()
            if success:
                passed += 1
                print(f"✅ {test_name} 테스트 통과")
            else:
                print(f"❌ {test_name} 테스트 실패")
        except Exception as e:
            print(f"❌ {test_name} 테스트 예외 발생: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 테스트 결과: {passed}/{total} 통과")
    print('='*50)
    
    if passed == total:
        print("🎉 모든 테스트 통과! Gemini API 통합이 성공적으로 완료되었습니다.")
    else:
        print("⚠️ 일부 테스트 실패. 로그를 확인하여 문제를 해결해주세요.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())