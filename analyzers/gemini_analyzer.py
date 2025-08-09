#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/gemini_analyzer.py

Gemini CLI를 활용한 뉴스 및 감성 분석기 - 완전 CLI 기반 구현
"""

import asyncio
import json
import re
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from utils.logger import get_logger
from config import Config


class GeminiAnalyzer:
    """Gemini CLI를 활용한 뉴스 및 감성 분석기"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger("GeminiAnalyzer")
        self.cli_command = None
        self.cli_available = False  # Initially False
        self.cli_checked = False    # Flag to check if CLI has been checked

    async def _check_gemini_cli_async(self) -> bool:
        """Asynchronously check for Gemini CLI availability."""
        if self.cli_checked:
            return self.cli_available

        node_script_path = 'C:\\Users\\great\\AppData\\Roaming\\npm\\node_modules\\@google\\gemini-cli\\dist\\index.js'
        possible_commands = [
            ['gemini', '--version'],
            ['node', node_script_path, '--version'],
            ['/c/Users/great/AppData/Roaming/npm/gemini.cmd', '--version'],
        ]

        for cmd in possible_commands:
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
                if process.returncode == 0:
                    self.cli_command = cmd[:-1]
                    self.cli_available = True
                    self.logger.info(f"Found Gemini CLI at: {self.cli_command}")
                    break  # Exit loop once a valid command is found
            except (FileNotFoundError, asyncio.TimeoutError, OSError) as e:
                self.logger.debug(f"Command {cmd} failed: {e}")
                continue
        
        self.cli_checked = True
        return self.cli_available
    
    async def _call_gemini_cli(self, prompt: str, max_retries: int = 3) -> str:
        """Gemini CLI를 통한 비동기 API 호출"""
        if not self.cli_available:
            raise Exception("Gemini CLI를 사용할 수 없습니다")
        
        for attempt in range(max_retries):
            try:
                # 임시 파일에 프롬프트 저장 (긴 프롬프트 처리용)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                    f.write(prompt)
                    temp_file = f.name
                
                try:
                    # Gemini CLI 실행 (비동기)
                    cmd_args = self.cli_command + ['-p', f'다음 내용을 분석해주세요: {prompt[:200]}...']
                    process = await asyncio.create_subprocess_exec(
                        *cmd_args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # 전체 프롬프트를 stdin으로 전송
                    stdout, stderr = await process.communicate(input=prompt.encode('utf-8'))
                    
                    if process.returncode == 0:
                        response = stdout.decode('utf-8').strip()
                        if response:
                            self.logger.debug(f"Gemini CLI 응답 성공 (시도 {attempt + 1}/{max_retries})")
                            return response
                        else:
                            raise Exception("빈 응답")
                    else:
                        error_msg = stderr.decode('utf-8').strip()
                        raise Exception(f"CLI 오류 (코드: {process.returncode}): {error_msg}")
                
                finally:
                    # 임시 파일 정리
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                        
            except Exception as e:
                self.logger.warning(f"Gemini CLI 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 지수 백오프
        
        raise Exception(f"Gemini CLI 호출 {max_retries}회 모두 실패")
    
    async def analyze_news_sentiment(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """뉴스 데이터를 바탕으로 감성 분석 수행 - CLI 기반"""
        await self._check_gemini_cli_async()
        if not self.cli_available or not news_data:
            return self._get_default_sentiment()
        
        try:
            # 뉴스 텍스트 준비
            news_texts = []
            for news in news_data:  # 전체 뉴스 분석 (10개 제한 제거)
                title = news.get('title', '')
                description = news.get('description', '')
                news_texts.append(f"제목: {title}\n내용: {description}")
            
            news_content = "\n\n".join(news_texts)
            
            # Gemini CLI용 프롬프트 구성
            prompt = self._build_sentiment_prompt(symbol, company_name, news_content)
            
            # CLI를 통한 분석 수행
            response = await self._call_gemini_cli(prompt)
            
            # JSON 응답 파싱
            result = self._parse_sentiment_response(response)
            
            self.logger.info(f"✅ Gemini CLI 감성 분석 완료 - {symbol}: {result.get('sentiment', 'UNKNOWN')}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Gemini CLI 감성 분석 실패 ({symbol}): {e}")
            return self._get_default_sentiment()
    
    async def analyze_market_impact(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """시장 영향도 분석 수행 - CLI 기반"""
        await self._check_gemini_cli_async()
        if not self.cli_available or not news_data:
            return self._get_default_market_impact()
        
        try:
            # 뉴스 텍스트 준비
            news_texts = []
            for news in news_data:  # 전체 뉴스 분석 (10개 제한 제거)
                title = news.get('title', '')
                description = news.get('description', '')
                news_texts.append(f"제목: {title}\n내용: {description}")
            
            news_content = "\n\n".join(news_texts)
            
            # Gemini CLI용 프롬프트 구성
            prompt = self._build_market_impact_prompt(symbol, company_name, news_content)
            
            # CLI를 통한 분석 수행
            response = await self._call_gemini_cli(prompt)
            
            # JSON 응답 파싱
            result = self._parse_market_impact_response(response)
            
            self.logger.info(f"✅ Gemini CLI 시장 영향도 분석 완료 - {symbol}: {result.get('impact_level', 'UNKNOWN')}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Gemini CLI 시장 영향도 분석 실패 ({symbol}): {e}")
            return self._get_default_market_impact()
    
    def _build_sentiment_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """감성 분석용 프롬프트 구성"""
        return f"""
한국 주식 시장 전문가로서 다음 뉴스들을 분석하여 {company_name}({symbol})에 대한 감성 분석을 수행해주세요.

뉴스 내용:
{news_content}

다음 JSON 형식으로 정확히 응답해주세요:
{{
    "sentiment": "VERY_POSITIVE|POSITIVE|NEUTRAL|NEGATIVE|VERY_NEGATIVE",
    "overall_score": (0-100 숫자),
    "confidence": (0.0-1.0 숫자),
    "positive_factors": ["긍정 요인1", "긍정 요인2"],
    "negative_factors": ["부정 요인1", "부정 요인2"],
    "key_keywords": ["핵심 키워드1", "키워드2"],
    "short_term_outlook": "단기 전망 설명",
    "medium_term_outlook": "중기 전망 설명",
    "summary": "종합 분석 요약"
}}

주의사항:
1. sentiment는 반드시 위 5개 값 중 하나여야 합니다
2. overall_score는 0-100 사이의 정수입니다 (50이 중립)
3. 한국 주식 시장 관점에서 분석해주세요
4. JSON 형식을 정확히 지켜주세요
"""

    def _build_market_impact_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """시장 영향도 분석용 프롬프트 구성"""
        return f"""
한국 주식 시장 전문가로서 다음 뉴스들이 {company_name}({symbol})의 시장에 미칠 영향을 분석해주세요.

뉴스 내용:
{news_content}

다음 JSON 형식으로 정확히 응답해주세요:
{{
    "impact_level": "HIGH|MEDIUM|LOW",
    "impact_score": (0-100 숫자),
    "duration": "SHORT_TERM|MEDIUM_TERM|LONG_TERM",
    "price_direction": "UP|DOWN|NEUTRAL",
    "volatility_expected": "HIGH|MEDIUM|LOW",
    "trading_volume_impact": "INCREASE|DECREASE|NORMAL",
    "sector_impact": "섹터 영향 설명",
    "key_risks": ["리스크1", "리스크2"],
    "catalysts": ["촉매1", "촉매2"],
    "target_price_change": "예상 목표가 변동률 (예: +5%, -3%)",
    "recommendation": "BUY|HOLD|SELL"
}}

주의사항:
1. 모든 열거형 값은 정확히 지정된 값 중 선택해주세요
2. 한국 주식 시장과 해당 업종 특성을 고려해주세요
3. JSON 형식을 정확히 지켜주세요
"""

    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """감성 분석 응답 파싱"""
        try:
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 필수 필드 검증 및 기본값 설정
                return {
                    'sentiment': result.get('sentiment', 'NEUTRAL'),
                    'overall_score': float(result.get('overall_score', 50)),
                    'confidence': float(result.get('confidence', 0.5)),
                    'positive_factors': result.get('positive_factors', []),
                    'negative_factors': result.get('negative_factors', []),
                    'key_keywords': result.get('key_keywords', []),
                    'short_term_outlook': result.get('short_term_outlook', '분석 정보 부족'),
                    'medium_term_outlook': result.get('medium_term_outlook', '분석 정보 부족'),
                    'summary': result.get('summary', 'CLI 분석 완료')
                }
            else:
                raise ValueError("JSON 형식을 찾을 수 없음")
                
        except Exception as e:
            self.logger.warning(f"감성 분석 응답 파싱 실패: {e}")
            return self._get_default_sentiment()
    
    def _parse_market_impact_response(self, response: str) -> Dict[str, Any]:
        """시장 영향도 분석 응답 파싱"""
        try:
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 필수 필드 검증 및 기본값 설정
                return {
                    'impact_level': result.get('impact_level', 'MEDIUM'),
                    'impact_score': float(result.get('impact_score', 50)),
                    'duration': result.get('duration', 'MEDIUM_TERM'),
                    'price_direction': result.get('price_direction', 'NEUTRAL'),
                    'volatility_expected': result.get('volatility_expected', 'MEDIUM'),
                    'trading_volume_impact': result.get('trading_volume_impact', 'NORMAL'),
                    'sector_impact': result.get('sector_impact', '정보 부족'),
                    'key_risks': result.get('key_risks', []),
                    'catalysts': result.get('catalysts', []),
                    'target_price_change': result.get('target_price_change', '0%'),
                    'recommendation': result.get('recommendation', 'HOLD')
                }
            else:
                raise ValueError("JSON 형식을 찾을 수 없음")
                
        except Exception as e:
            self.logger.warning(f"시장 영향도 분석 응답 파싱 실패: {e}")
            return self._get_default_market_impact()
    
    def _format_news_for_analysis(self, news_data: List[Dict]) -> str:
        """뉴스 데이터를 분석용 텍스트로 포맷"""
        try:
            formatted_content = []
            for i, news in enumerate(news_data, 1):
                title = news.get('title', '제목 없음')
                content = news.get('content', news.get('summary', '내용 없음'))
                formatted_content.append(f"뉴스 {i}: {title}\n내용: {content}")
            
            return "\n\n".join(formatted_content)
            
        except Exception as e:
            self.logger.warning(f"뉴스 포맷팅 실패: {e}")
            return "뉴스 내용 파싱 실패"

    def _fallback_analysis(self, news_content: str, company_name: str) -> Dict[str, Any]:
        """키워드 기반 fallback 분석"""
        try:
            # 간단한 키워드 기반 분석
            positive_keywords = ['상승', '긍정', '성장', '실적', '호조', '증가', '확대', '개선', '신규', '계약', '수주']
            negative_keywords = ['하락', '부정', '감소', '우려', '위험', '손실', '규제', '중단', '취소', '악화']
            
            content_lower = news_content.lower()
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in content_lower)
            negative_count = sum(1 for keyword in negative_keywords if keyword in content_lower)
            
            # 점수 계산 (30-70 범위)
            if positive_count > negative_count:
                sentiment = 'POSITIVE'
                score = min(80, 60 + (positive_count - negative_count) * 5)
            elif negative_count > positive_count:
                sentiment = 'NEGATIVE'
                score = max(20, 40 - (negative_count - positive_count) * 5)
            else:
                sentiment = 'NEUTRAL'
                score = 50.0
            
            return {
                'sentiment': sentiment,
                'overall_score': float(score),
                'confidence': 0.6,
                'positive_factors': [f'긍정 키워드 {positive_count}개 발견'] if positive_count > 0 else [],
                'negative_factors': [f'부정 키워드 {negative_count}개 발견'] if negative_count > 0 else [],
                'key_keywords': positive_keywords[:positive_count] + negative_keywords[:negative_count],
                'short_term_outlook': f'키워드 분석 기반 {sentiment.lower()} 전망',
                'medium_term_outlook': '상세 분석 필요',
                'summary': f'{company_name} 키워드 분석 결과: {sentiment}',
                'trend': 'STABLE'
            }
            
        except Exception as e:
            self.logger.warning(f"Fallback 분석 실패: {e}")
            return self._get_default_sentiment()

    def _get_default_sentiment(self) -> Dict[str, Any]:
        """기본 감성 분석 결과"""
        return {
            'sentiment': 'NEUTRAL',
            'overall_score': 50.0,
            'confidence': 0.3,
            'positive_factors': ['CLI 분석 불가'],
            'negative_factors': ['CLI 분석 불가'],
            'key_keywords': [],
            'short_term_outlook': 'Gemini CLI 분석 불가로 중립적 전망',
            'medium_term_outlook': 'Gemini CLI 분석 불가로 중립적 전망',
            'summary': 'CLI 기반 분석 실패로 기본값 사용'
        }
    
    def _get_default_market_impact(self) -> Dict[str, Any]:
        """기본 시장 영향도 분석 결과"""
        return {
            'impact_level': 'LOW',
            'impact_score': 40.0,
            'duration': 'SHORT_TERM',
            'price_direction': 'NEUTRAL',
            'volatility_expected': 'LOW',
            'trading_volume_impact': 'NORMAL',
            'sector_impact': 'CLI 분석 불가',
            'key_risks': [],
            'catalysts': [],
            'target_price_change': '0%',
            'recommendation': 'HOLD'
        }

    @property
    def model(self):
        """호환성을 위한 model 속성 (CLI 사용 시에는 None이 아닌 값 반환)"""
        return "gemini-cli" if self.cli_available else None