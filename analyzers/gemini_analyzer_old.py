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
import time
import random
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
        
        # 토큰 할당량 추적
        self.quota_exhausted = True   # 기본적으로 소진 상태로 시작 (API 할당량 소진으로 추정)
        self.last_quota_check = 0     # 마지막 체크 시간
        self.quota_check_interval = 1800  # 30분마다 체크 (할당량 회복 대기)
        self.consecutive_failures = 10   # 높은 실패 횟수로 시작
        self.max_failures_before_skip = 3  # 3회 실패 시 스킵

    async def _check_gemini_cli_async(self) -> bool:
        """Asynchronously check for Gemini CLI availability."""
        if self.cli_checked:
            return self.cli_available

        # 더 정확한 경로들을 시도 (실행 환경에 맞게 최적화)
        possible_commands = [
            ['/c/Users/great/AppData/Roaming/npm/gemini', '--version'],  # 우선 순위 1: Unix 스타일 경로
            ['gemini', '--version'],  # 우선 순위 2: PATH에서 찾기
            ['cmd', '/c', 'C:\\Users\\great\\AppData\\Roaming\\npm\\gemini.cmd', '--version'],  # 우선 순위 3: cmd를 통한 실행
        ]

        for cmd in possible_commands:
            try:
                self.logger.debug(f"Gemini CLI 경로 테스트 중: {cmd}")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
                if process.returncode == 0:
                    version = stdout.decode('utf-8').strip()
                    # cmd wrapper를 사용하는 경우와 직접 실행하는 경우 구분
                    if cmd[0] == 'cmd' and len(cmd) > 3:
                        # cmd를 통한 실행: ['cmd', '/c', 'path', '--version'] → ['cmd', '/c', 'path']
                        self.cli_command = cmd[:-1]
                    else:
                        # 직접 실행: ['path', '--version'] → ['path']
                        self.cli_command = cmd[:-1]
                    
                    self.cli_available = True
                    self.logger.info(f"✅ Gemini CLI 발견: {self.cli_command} (버전: {version})")
                    break  # Exit loop once a valid command is found
                else:
                    error = stderr.decode('utf-8', errors='ignore').strip()
                    self.logger.debug(f"Command {cmd} failed with return code {process.returncode}: {error}")
            except (FileNotFoundError, asyncio.TimeoutError, OSError) as e:
                self.logger.debug(f"Command {cmd} failed: {e}")
                continue
        
        self.cli_checked = True
        return self.cli_available
    
    async def _check_quota_status(self) -> bool:
        """토큰 할당량 상태 체크 (스마트 체크)"""
        # CLI 체크부터 먼저 수행
        if not self.cli_checked:
            await self._check_gemini_cli_async()
        
        current_time = time.time()
        
        # 이미 소진으로 확인된 경우, 일정 시간 후 재체크
        if self.quota_exhausted:
            if (current_time - self.last_quota_check) < self.quota_check_interval:
                self.logger.debug(f"토큰 소진 상태 - 다음 체크까지 {int(self.quota_check_interval - (current_time - self.last_quota_check))}초 대기")
                return False
            else:
                self.logger.info("토큰 할당량 재체크 시간 - 상태 초기화하여 재시도")
                self.quota_exhausted = False
                self.consecutive_failures = 0
        
        # 연속 실패가 많으면 스킵
        if self.consecutive_failures >= self.max_failures_before_skip:
            self.logger.warning(f"연속 {self.consecutive_failures}회 실패로 Gemini API 일시 스킵")
            self.quota_exhausted = True
            self.last_quota_check = current_time
            return False
        
        # CLI 사용 불가능하면 바로 False
        if not self.cli_available:
            return False
        
        # 빠른 테스트 쿼리로 토큰 상태 확인
        try:
            test_prompt = "Hello"  # 매우 짧은 테스트 프롬프트
            
            # 타임아웃을 짧게 설정하여 빠른 체크
            process = await asyncio.create_subprocess_exec(
                *self.cli_command, '-p', test_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
                
                if process.returncode == 0:
                    self.logger.debug("토큰 할당량 체크 성공 - API 사용 가능")
                    self.consecutive_failures = 0  # 성공 시 실패 카운터 리셋
                    return True
                else:
                    error_msg = stderr.decode('utf-8', errors='ignore').strip()
                    
                    # 토큰 관련 오류 체크
                    if any(keyword in error_msg.lower() for keyword in ['resource_exhausted', 'quota', 'limit', 'exceeded']):
                        self.logger.warning(f"토큰 할당량 소진 감지: {error_msg}")
                        self.quota_exhausted = True
                        self.last_quota_check = current_time
                        return False
                    else:
                        self.logger.debug(f"일반적인 API 오류 (토큰 문제 아님): {error_msg}")
                        self.consecutive_failures += 1
                        return False
                        
            except asyncio.TimeoutError:
                self.logger.warning("토큰 상태 체크 타임아웃 - API 응답 없음")
                self.consecutive_failures += 1
                return False
                
        except Exception as e:
            self.logger.debug(f"토큰 상태 체크 실패: {e}")
            self.consecutive_failures += 1
            return False
    
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
                    
                    # 전체 프롬프트를 stdin으로 전송 (타임아웃 30초)
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=prompt.encode('utf-8')), 
                        timeout=30.0
                    )
                    
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
    
    async def analyze_market_impact(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """시장 영향도 분석 수행 - CLI 기반 + GPT 백업"""
        await self._check_gemini_cli_async()
        
        # 뉴스 데이터가 없는 경우
        if not news_data:
            self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 기본 시장 영향도 분석 사용")
            return self._get_default_market_impact()
        
        # 뉴스 텍스트 준비
        news_texts = []
        for news in news_data:  # 전체 뉴스 분석 (10개 제한 제거)
            title = news.get('title', '')
            description = news.get('description', '')
            news_texts.append(f"제목: {title}\n내용: {description}")
        
        news_content = "\n\n".join(news_texts)
        
        # Gemini 토큰 소진 상태 체크
        if self.cli_available:
            if self.quota_exhausted and (time.time() - self.last_quota_check) < self.quota_check_interval:
                self.logger.warning(f"⚠️ Gemini 토큰 소진으로 인해 GPT로 전환: {symbol}")
                return await self._fallback_to_gpt_market_impact(symbol, company_name, news_data)
            elif self.consecutive_failures >= self.max_failures_before_skip:
                self.logger.warning(f"⚠️ Gemini 연속 실패로 인해 GPT로 전환: {symbol}")
                return await self._fallback_to_gpt_market_impact(symbol, company_name, news_data)
        
            try:
                # Gemini CLI용 프롬프트 구성
                prompt = self._build_market_impact_prompt(symbol, company_name, news_content)
                
                # CLI를 통한 분석 수행
                response = await self._call_gemini_cli(prompt)
                
                # JSON 응답 파싱
                result = self._parse_market_impact_response(response)
                
                self.logger.info(f"✅ Gemini CLI 시장 영향도 분석 완료 - {symbol}: {result.get('impact_level', 'UNKNOWN')}")
                return result
                
            except Exception as e:
                # 토큰 관련 오류 감지 및 GPT 백업 전환
                if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                    self.logger.warning(f"⚠️ Gemini API 토큰 소진 감지 - GPT로 전환: {symbol}")
                    self.quota_exhausted = True
                    self.last_quota_check = time.time()
                    return await self._fallback_to_gpt_market_impact(symbol, company_name, news_data)
                else:
                    self.logger.error(f"❌ Gemini CLI 시장 영향도 분석 실패 ({symbol}): {e}")
                    self.consecutive_failures += 1
                    return await self._fallback_to_gpt_market_impact(symbol, company_name, news_data)
        
        else:
            self.logger.info(f"📰 {symbol} Gemini CLI 사용 불가 - GPT로 전환")
            return await self._fallback_to_gpt_market_impact(symbol, company_name, news_data)
    
    def _build_sentiment_prompt(self, symbol: str, company_name: str, news_content: str, period_name: str) -> str:
        """감성 분석용 프롬프트 구성 (재료 관점 분석)"""
        return f"""You are a Korean stock market analyst. Analyze the news for {company_name}({symbol}) and respond ONLY with JSON format.

IMPORTANT: Your response must be ONLY valid JSON, no other text or explanation.

News content:
{news_content}

Required JSON response format:
{{
  "short_term": {{
    "score": 65,
    "summary": "Short-term investment sentiment summary",
    "positive_factors": ["positive factor 1", "factor 2"],
    "negative_factors": ["negative factor 1", "factor 2"]
  }},
  "mid_term": {{
    "score": 70,
    "summary": "Mid-term investment sentiment summary", 
    "positive_factors": ["positive factor 1", "factor 2"],
    "negative_factors": ["negative factor 1", "factor 2"]
  }},
  "long_term": {{
    "score": 60,
    "summary": "Long-term investment sentiment summary",
    "positive_factors": ["positive factor 1", "factor 2"], 
    "negative_factors": ["negative factor 1", "factor 2"]
  }},
  "key_keywords": ["keyword1", "keyword2"],
  "overall_summary": "Overall analysis summary"
}}

Respond with ONLY the JSON object above, no additional text."""

    def _build_market_impact_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """시장 영향도 분석용 프롬프트 구성"""
        return f"""
한국 주식 시장 전문가로서 다음 뉴스들이 {company_name}({symbol})의 시장에 미칠 영향을 분석해주세요.
분석 시 다음 단기/중기/장기 재료의 정의를 참고하여 영향 기간(duration)을 제시해주세요.

# 재료 분류 정의
## 단기 재료 (수일 ~ 1개월 이내 영향)
- 인수합병(M&A) 공시
- 제3자 배정 유상증자
- 신규 사업 진출 발표
- 무상증자
- 공개매수
- 자회사 상장 추진
- 특허권 취득
- 회사 분할(인적분할, 물적분할)
- 신약 개발 임상 결과 발표(1상, 2상, 3상 등)
- 정부 정책 수혜(규제 완화, 보조금 지급 등)
- 신규 수주 계약 체결(대규모 프로젝트)
- 주가 급등에 따른 투자경고·거래정지 등 이슈
- 특정 테마 부각(예: AI, 2차전지, 로봇, 방산 등)
- 기관·외국인 대량 매수세 유입
- 주요 주주 지분 변동 공시

## 중기 재료 (1개월 ~ 6개월 이내 영향)
- 산업 호황(특정 섹터 수요 급증)
- 턴어라운드 예상(흑자전환 기대감)
- 사상 최대 실적 달성
- 대규모 수주 잇따름(중장기 안정적 수익 기반 확보)
- 해외 진출 성공 사례(글로벌 시장 확장)
- 원자재 가격 하락에 따른 원가 절감
- 경쟁사 대비 기술력 우위 확보
- 주요 경쟁사의 사업 축소·철수로 인한 반사이익
- 구조조정·비효율 사업부 매각으로 수익성 개선

## 장기 재료 (6개월 이상 영향)
- 최대 주주·주요 주주 매입(경영권 강화)
- 단일 판매·공급계약 체결(장기 안정적 매출 확보)
- 유형자산 취득 결정(생산설비 확대 등)
- 자사주 매입(주주가치 제고)
- 부채 조기 상환(재무건전성 개선)
- 자사주 소각(주식 수 감소로 주당 가치 상승)
- 액면분할(유통주식 수 증가로 거래 활성화)
- 지속적 배당 확대 정책(주주 친화 정책)
- ESG 경영 강화 및 수상(글벌 펀드 자금 유입 기대)
- 신성장 동력 확보(미래 먹거리 발굴 및 투자)
- 핵심 인재 영입(경영진 변화 및 기술개발 역량 강화)
- 글로벌 기업과 전략적 제휴(협력 강화)

뉴스 내용:
{news_content}

다음 JSON 형식으로 정확히 응답해주세요. JSON 외에 다른 텍스트, 설명, 주석은 절대 포함하지 마세요. JSON은 유효하고 파싱 가능해야 하며, UTF-8로 인코딩되어야 합니다.

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
4. duration 필드는 위 재료 분류 정의를 참고하여 SHORT_TERM, MEDIUM_TERM, LONG_TERM 중 하나로 정확히 지정해주세요.
5. 응답은 반드시 JSON 객체만 포함해야 합니다. 다른 텍스트는 허용되지 않습니다.
"""

    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """감성 분석 응답 파싱 (기간별 분석 지원)"""
        try:
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 새로운 기간별 형식인지 확인
                if 'short_term' in result and 'mid_term' in result and 'long_term' in result:
                    # 새로운 기간별 형식으로 반환
                    return result
                else:
                    # 기존 형식에서 새 형식으로 변환
                    return {
                        'sentiment': result.get('sentiment', 'NEUTRAL'),
                        'overall_score': float(result.get('overall_score', 50)),
                        'confidence': float(result.get('confidence', 0.5)),
                        'positive_factors': result.get('positive_factors', []),
                        'negative_factors': result.get('negative_factors', []),
                        'key_keywords': result.get('key_keywords', []),
                        'short_term_outlook': result.get('short_term_outlook', '분석 정보 부족'),
                        'medium_term_outlook': result.get('medium_term_outlook', '분석 정보 부족'),
                        'long_term_outlook': result.get('long_term_outlook', '분석 정보 부족'),
                        'summary': result.get('summary', 'CLI 분석 완료')
                    }
            else:
                self.logger.warning(f"JSON 형식을 찾을 수 없음: {response[:200]}...")
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

    async def _enhanced_fallback_analysis(self, symbol: str, company_name: str, news_data: List[Dict], news_content: str, period_name: str = "종합") -> Dict[str, Any]:
        """향상된 키워드 기반 fallback 분석 - 기간별 분석 포함"""
        try:
            self.logger.info(f"🔄 {symbol} 향상된 fallback 분석 시작 (Gemini 대체)")
            
            # 확장된 키워드 사전 - 더 많은 키워드로 정확도 향상
            keyword_dict = {
                'positive_keywords': {
                    'financial': ['실적', '수익', '매출', '영업이익', '순이익', '호조', '성장', '증가', '개선', '상승', '흑자', '최대', '신고가', 
                                '호황', '급등', '최고', '기록', '달성', '돌파', '신고점', '플러스', '수주', '매출증가'],
                    'business': ['계약', '수주', '신규', '확장', '진출', '투자', '개발', '출시', '론칭', '파트너십', '제휴', '협력', 
                               '신사업', '확대', '진출', '성공', '도약', '강화', '체결', '추진', '전략'],
                    'technical': ['특허', '기술', '혁신', '개발', '연구', 'R&D', '신제품', '업그레이드', '개선', 
                                '혁신적', '첨단', '기술력', '개발완료', '기술개발', '연구개발', '신기술'],
                    'market': ['점유율', '경쟁력', '우위', '선두', '리더', '1위', '업계', '시장', '시장확대', 
                             '매수', '강세', '상승', '돌파', '랠리', '긍정', '기대', '호재']
                },
                'negative_keywords': {
                    'financial': ['손실', '적자', '부채', '하락', '감소', '악화', '부진', '저조', '타격', '감소',
                                '급락', '폭락', '최저', '하락세', '부담', '마이너스', '손해', '적자전환'],
                    'business': ['중단', '취소', '지연', '연기', '철회', '축소', '폐지', '종료', '중단', '실패', 
                               '포기', '철수', '감축', '구조조정', '정리해고'],
                    'regulatory': ['규제', '제재', '처벌', '조사', '수사', '의혹', '문제', '리스크', '위반', 
                                 '과태료', '제재금', '행정처분', '법적', '소송'],
                    'market': ['경쟁', '압박', '위기', '우려', '불안', '충격', '매도', '약세', '하락', 
                             '악재', '부정', '리스크', '하향', '위험']
                }
            }
            
            # 키워드 분석 수행
            analysis_results = self._analyze_keywords_by_category(news_content, keyword_dict)
            
            # 뉴스별 세부 분석
            news_analysis = self._analyze_individual_news(news_data)
            
            # 기간별 분석 생성
            period_analysis = self._generate_period_analysis(analysis_results, news_analysis, company_name)
            
            # 최종 결과 구성
            result = {
                'short_term': {
                    'score': period_analysis['short_term_score'],
                    'summary': period_analysis['short_term_summary'],
                    'positive_factors': period_analysis['positive_factors'],
                    'negative_factors': period_analysis['negative_factors']
                },
                'mid_term': {
                    'score': period_analysis['mid_term_score'],
                    'summary': period_analysis['mid_term_summary'],
                    'positive_factors': period_analysis['positive_factors'],
                    'negative_factors': period_analysis['negative_factors']
                },
                'long_term': {
                    'score': period_analysis['long_term_score'],
                    'summary': period_analysis['long_term_summary'],
                    'positive_factors': period_analysis['positive_factors'],
                    'negative_factors': period_analysis['negative_factors']
                },
                'key_keywords': analysis_results['found_keywords'],
                'overall_summary': f'{company_name} Fallback 분석 결과: {len(news_data)}개 뉴스 키워드 분석 완료'
            }
            
            self.logger.info(f"✅ {symbol} 향상된 fallback 분석 완료 - 단기:{period_analysis['short_term_score']}, 중기:{period_analysis['mid_term_score']}, 장기:{period_analysis['long_term_score']}")
            return result
            
        except Exception as e:
            self.logger.warning(f"향상된 fallback 분석 실패: {e}")
            return self._get_default_sentiment()
    
    def _analyze_keywords_by_category(self, news_content: str, keyword_dict: Dict) -> Dict:
        """카테고리별 키워드 분석"""
        content_lower = news_content.lower()
        results = {'positive': {}, 'negative': {}, 'found_keywords': []}
        
        # 긍정 키워드 분석
        for category, keywords in keyword_dict['positive_keywords'].items():
            count = sum(1 for keyword in keywords if keyword in content_lower)
            if count > 0:
                results['positive'][category] = count
                results['found_keywords'].extend([kw for kw in keywords if kw in content_lower])
        
        # 부정 키워드 분석
        for category, keywords in keyword_dict['negative_keywords'].items():
            count = sum(1 for keyword in keywords if keyword in content_lower)
            if count > 0:
                results['negative'][category] = count
                results['found_keywords'].extend([kw for kw in keywords if kw in content_lower])
        
        return results
    
    def _analyze_individual_news(self, news_data: List[Dict]) -> List[Dict]:
        """개별 뉴스 분석"""
        results = []
        for news in news_data:
            title = news.get('title', '')
            description = news.get('description', '')
            
            # 간단한 감정 분석
            combined_text = f"{title} {description}".lower()
            
            # 긍정/부정 지표
            positive_indicators = ['상승', '성장', '호조', '실적', '수주', '계약']
            negative_indicators = ['하락', '우려', '손실', '부진', '규제']
            
            pos_count = sum(1 for ind in positive_indicators if ind in combined_text)
            neg_count = sum(1 for ind in negative_indicators if ind in combined_text)
            
            sentiment = 'positive' if pos_count > neg_count else 'negative' if neg_count > pos_count else 'neutral'
            
            results.append({
                'title': title,
                'sentiment': sentiment,
                'pos_indicators': pos_count,
                'neg_indicators': neg_count
            })
        
        return results
    
    async def _enhanced_market_impact_fallback(self, symbol: str, company_name: str, news_data: List[Dict], news_content: str) -> Dict[str, Any]:
        """향상된 시장 영향도 fallback 분석"""
        try:
            self.logger.info(f"🔄 {symbol} 향상된 시장 영향도 fallback 분석 시작")
            
            # 뉴스별 영향도 키워드 분석
            high_impact_keywords = ['인수합병', 'M&A', '상장', '분할', '합병', '신약', '임상', '특허', '수주', '계약', '정책', '규제완화']
            medium_impact_keywords = ['실적', '매출', '영업이익', '투자', '확장', '진출', '파트너십', '제휴']
            low_impact_keywords = ['발표', '계획', '예상', '전망', '검토', '고려']
            
            negative_impact_keywords = ['손실', '적자', '규제', '제재', '중단', '취소', '지연', '우려', '위험']
            
            content_lower = news_content.lower()
            
            # 영향도 레벨 결정
            high_count = sum(1 for kw in high_impact_keywords if kw in content_lower)
            medium_count = sum(1 for kw in medium_impact_keywords if kw in content_lower)
            low_count = sum(1 for kw in low_impact_keywords if kw in content_lower)
            negative_count = sum(1 for kw in negative_impact_keywords if kw in content_lower)
            
            # 점수 계산
            impact_score = 40  # 기본 점수
            if high_count > 0:
                impact_level = "HIGH"
                impact_score = min(85, 70 + high_count * 5)
                duration = "MEDIUM_TERM"
            elif medium_count > 0:
                impact_level = "MEDIUM" 
                impact_score = min(75, 50 + medium_count * 3)
                duration = "SHORT_TERM"
            else:
                impact_level = "LOW"
                impact_score = max(30, 40 + low_count * 2)
                duration = "SHORT_TERM"
            
            # 부정적 요인 반영
            if negative_count > 0:
                impact_score = max(20, impact_score - negative_count * 8)
                price_direction = "DOWN"
            elif high_count > 0 or medium_count > 0:
                price_direction = "UP"
            else:
                price_direction = "NEUTRAL"
            
            # 변동성 예상
            volatility = "HIGH" if high_count > 0 else "MEDIUM" if medium_count > 0 else "LOW"
            
            # 거래량 영향
            volume_impact = "INCREASE" if (high_count + medium_count) > 0 else "NORMAL"
            
            # 추천 생성
            if impact_score > 65:
                recommendation = "BUY"
            elif impact_score < 40:
                recommendation = "SELL"
            else:
                recommendation = "HOLD"
            
            # 팩터 생성
            catalysts = []
            risks = []
            
            if high_count > 0:
                catalysts.append(f"고영향도 키워드 {high_count}개 발견")
            if medium_count > 0:
                catalysts.append(f"중영향도 키워드 {medium_count}개 발견")
            if negative_count > 0:
                risks.append(f"부정적 키워드 {negative_count}개 발견")
            
            if not catalysts:
                catalysts = ["키워드 분석 기반 기본 전망"]
            if not risks:
                risks = ["특별한 리스크 요인 없음"]
            
            result = {
                'impact_level': impact_level,
                'impact_score': float(impact_score),
                'duration': duration,
                'price_direction': price_direction,
                'volatility_expected': volatility,
                'trading_volume_impact': volume_impact,
                'sector_impact': f'{company_name} 키워드 분석 기반 {impact_level} 영향도',
                'key_risks': risks,
                'catalysts': catalysts,
                'target_price_change': f"{'+'if impact_score > 50 else '-'}{abs(impact_score-50)//10}%",
                'recommendation': recommendation
            }
            
            self.logger.info(f"✅ {symbol} 향상된 시장 영향도 fallback 분석 완료 - {impact_level}:{impact_score}")
            return result
            
        except Exception as e:
            self.logger.warning(f"향상된 시장 영향도 fallback 분석 실패: {e}")
            return self._get_default_market_impact()

    def _generate_period_analysis(self, keyword_analysis: Dict, news_analysis: List[Dict], company_name: str) -> Dict:
        """기간별 분석 결과 생성"""
        # 전체 감정 점수 계산
        total_positive = sum(keyword_analysis['positive'].values())
        total_negative = sum(keyword_analysis['negative'].values())
        
        # 기본 점수 (40-60 범위)
        base_score = 50
        if total_positive > total_negative:
            score_adjustment = min(15, (total_positive - total_negative) * 3)
            base_score += score_adjustment
        elif total_negative > total_positive:
            score_adjustment = min(15, (total_negative - total_positive) * 3)
            base_score -= score_adjustment
        
        # 기간별 점수 조정 - 랜덤성을 줄이고 뉴스 기반 점수 반영
        short_term_score = max(30, min(80, base_score + random.randint(-2, 2)))  # 단기는 뉴스의 직접적 영향
        mid_term_score = max(30, min(80, base_score + random.randint(-3, 3)))    # 중기는 약간의 변동성
        long_term_score = max(30, min(80, base_score + random.randint(-1, 1)))   # 장기는 안정성
        
        # 팩터 생성
        positive_factors = []
        negative_factors = []
        
        if keyword_analysis['positive']:
            for category, count in keyword_analysis['positive'].items():
                positive_factors.append(f"{category} 관련 긍정 키워드 {count}개 발견")
        
        if keyword_analysis['negative']:
            for category, count in keyword_analysis['negative'].items():
                negative_factors.append(f"{category} 관련 부정 키워드 {count}개 발견")
        
        # 기본 팩터 추가
        if not positive_factors and not negative_factors:
            positive_factors = ["키워드 분석 기반 중립적 전망"]
        
        return {
            'short_term_score': short_term_score,
            'mid_term_score': mid_term_score,
            'long_term_score': long_term_score,
            'short_term_summary': f'{company_name} 단기 전망: 키워드 분석 기반 점수 {short_term_score}',
            'mid_term_summary': f'{company_name} 중기 전망: 키워드 분석 기반 점수 {mid_term_score}',
            'long_term_summary': f'{company_name} 장기 전망: 키워드 분석 기반 점수 {long_term_score}',
            'positive_factors': positive_factors,
            'negative_factors': negative_factors
        }

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
        """기본 감성 분석 결과 (기간별 분석 포함) - 더 나은 기본값 제공"""
        return {
            'short_term': {
                'score': 50,
                'summary': '뉴스 데이터 부족으로 중립적 전망 (AI 분석 미실시)',
                'positive_factors': ['시장 평균 수준의 기본 전망'],
                'negative_factors': ['충분한 뉴스 정보 부족']
            },
            'mid_term': {
                'score': 50,
                'summary': '뉴스 데이터 부족으로 중립적 전망 (AI 분석 미실시)', 
                'positive_factors': ['시장 평균 수준의 기본 전망'],
                'negative_factors': ['충분한 뉴스 정보 부족']
            },
            'long_term': {
                'score': 50,
                'summary': '뉴스 데이터 부족으로 중립적 전망 (AI 분석 미실시)',
                'positive_factors': ['시장 평균 수준의 기본 전망'],
                'negative_factors': ['충분한 뉴스 정보 부족']
            },
            'key_keywords': ['기본분석', '중립전망'],
            'overall_summary': 'AI 분석 불가 시 기본 중립 분석 사용 (뉴스 데이터 기반 분석 필요시 수동 확인 권장)'
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

    async def analyze_with_custom_prompt(self, prompt: str) -> str:
        """커스텀 프롬프트로 Gemini CLI 호출"""
        try:
            if self.quota_exhausted:
                self.logger.warning("⚠️ Gemini 토큰 할당량 소진으로 인해 스킵")
                return "토큰 할당량 소진으로 인해 분석을 수행할 수 없습니다."
            
            # Gemini CLI를 통해 분석 요청
            result = await self._call_gemini_cli(prompt)
            
            if result:
                self.consecutive_failures = 0  # 성공 시 실패 카운터 리셋
                return result
            else:
                self.consecutive_failures += 1
                return "Gemini 분석을 수행할 수 없습니다."
                
        except Exception as e:
            self.logger.error(f"❌ Gemini 커스텀 분석 실패: {e}")
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.max_failures_before_skip:
                self.quota_exhausted = True
                self.logger.warning("⚠️ 연속 실패로 인해 Gemini 분석 임시 비활성화")
            
            return f"Gemini 분석 실패: {str(e)}"

    async def analyze_news_sentiment(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """뉴스 감성 분석 - Gemini → GPT 백업 시스템"""
        await self._check_gemini_cli_async()
        
        # 뉴스 데이터가 없는 경우
        if not news_data:
            self.logger.debug(f"📰 {symbol} 뉴스 데이터 없음 - 기본 분석 사용")
            return self._get_default_sentiment()
        
        # 뉴스 텍스트 준비
        news_texts = [f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}" for news in news_data]
        news_content = "\n\n".join(news_texts)
        
        self.logger.info(f"📰 {symbol} 뉴스 {len(news_data)}개로 통합 감성 분석 시작...")
        
        # Gemini 토큰 소진 상태 체크
        if self.cli_available:
            if self.quota_exhausted and (time.time() - self.last_quota_check) < self.quota_check_interval:
                self.logger.warning(f"⚠️ Gemini 토큰 소진으로 인해 GPT로 전환: {symbol}")
                return await self._fallback_to_gpt_sentiment(symbol, company_name, news_data)
            elif self.consecutive_failures >= self.max_failures_before_skip:
                self.logger.warning(f"⚠️ Gemini 연속 실패로 인해 GPT로 전환: {symbol}")
                return await self._fallback_to_gpt_sentiment(symbol, company_name, news_data)
        
            try:
                # Gemini CLI용 통합 프롬프트 구성
                prompt = self._build_comprehensive_sentiment_prompt(symbol, company_name, news_content)
                
                # CLI를 통한 분석 수행
                response = await self._call_gemini_cli(prompt)
                
                # JSON 응답 파싱
                result = self._parse_comprehensive_sentiment_response(response)
                
                self.logger.info(f"✅ Gemini CLI 통합 감성 분석 완료 - {symbol}: 단기={result.get('short_term', {}).get('score', 50)}, 중기={result.get('mid_term', {}).get('score', 50)}, 장기={result.get('long_term', {}).get('score', 50)}")
                return result
                
            except Exception as e:
                # 토큰 관련 오류 감지 및 GPT 백업 전환
                if "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                    self.logger.warning(f"⚠️ Gemini API 토큰 소진 감지 - GPT로 전환: {symbol}")
                    self.quota_exhausted = True
                    self.last_quota_check = time.time()
                    return await self._fallback_to_gpt_sentiment(symbol, company_name, news_data)
                else:
                    self.logger.error(f"❌ Gemini CLI 통합 감성 분석 실패 ({symbol}): {e}")
                    self.consecutive_failures += 1
                    return await self._fallback_to_gpt_sentiment(symbol, company_name, news_data)
        
        else:
            self.logger.info(f"📰 {symbol} Gemini CLI 사용 불가 - GPT로 전환")
            return await self._fallback_to_gpt_sentiment(symbol, company_name, news_data)

    def _build_comprehensive_sentiment_prompt(self, symbol: str, company_name: str, news_content: str) -> str:
        """통합 감성 분석용 프롬프트 구성 - 모든 기간을 한 번에 분석"""
        # 뉴스 개수 정확히 계산
        news_count = news_content.count('제목:') if news_content else 0
        
        # 뉴스 내용이 너무 길면 자르기 (Gemini 토큰 제한 고려)
        max_content_length = 8000  # 약 8K 문자로 제한
        if len(news_content) > max_content_length:
            news_content = news_content[:max_content_length] + "\n... (내용이 길어 일부 생략)"
            
        return f"""You are a Korean stock market analyst. Analyze ALL the news for {company_name}({symbol}) and respond ONLY with JSON format.

IMPORTANT: Your response MUST be ONLY a valid JSON object. DO NOT include any other text, comments, or explanations outside the JSON. Ensure the JSON is well-formed and strictly adheres to the specified structure. Use UTF-8 encoding.

News content ({news_count} articles):
{news_content}

Analyze each piece of news and categorize by impact timeline:
- SHORT_TERM (단기): 1 month or less impact (M&A, clinical results, major contracts, regulatory changes)
- MEDIUM_TERM (중기): 1-6 months impact (sector trends, earnings turnaround, business expansion)  
- LONG_TERM (장기): 6+ months impact (strategic partnerships, capacity expansion, ESG initiatives)

Required JSON response format:
{{
  "short_term": {{
    "score": 65,
    "summary": "Short-term investment outlook based on news analysis",
    "positive_factors": ["specific positive factor from news", "another factor"],
    "negative_factors": ["specific negative factor from news", "another factor"]
  }},
  "mid_term": {{
    "score": 70,
    "summary": "Medium-term investment outlook based on news analysis", 
    "positive_factors": ["specific positive factor from news", "another factor"],
    "negative_factors": ["specific negative factor from news", "another factor"]
  }},
  "long_term": {{
    "score": 60,
    "summary": "Long-term investment outlook based on news analysis",
    "positive_factors": ["specific positive factor from news", "another factor"], 
    "negative_factors": ["specific negative factor from news", "another factor"]
  }},
  "key_keywords": ["keyword1 from news", "keyword2 from news", "keyword3 from news"],
  "overall_summary": "Overall analysis summary explaining the key findings from all {news_count} news articles"
}}

SCORING GUIDELINES:
- 0-30: Very negative news dominates
- 31-49: Mostly negative news
- 50: Neutral/mixed news
- 51-69: Mostly positive news  
- 70-100: Very positive news dominates

Respond with ONLY the JSON object above, no additional text. The JSON must be valid and parseable.
"""

    def _parse_comprehensive_sentiment_response(self, response: str) -> Dict[str, Any]:
        """통합 감성 분석 응답 파싱"""
        try:
            # JSON 부분만 추출 시도
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 필수 필드 검증 및 기본값 설정
                return {
                    'short_term': result.get('short_term', {
                        'score': 50, 'summary': 'AI 분석 파싱 실패', 
                        'positive_factors': [], 'negative_factors': []
                    }),
                    'mid_term': result.get('mid_term', {
                        'score': 50, 'summary': 'AI 분석 파싱 실패',
                        'positive_factors': [], 'negative_factors': []
                    }),
                    'long_term': result.get('long_term', {
                        'score': 50, 'summary': 'AI 분석 파싱 실패',
                        'positive_factors': [], 'negative_factors': []
                    }),
                    'key_keywords': result.get('key_keywords', ['분석실패']),
                    'overall_summary': result.get('overall_summary', '통합 AI 분석 완료')
                }
            else:
                self.logger.warning(f"JSON 형식을 찾을 수 없음: {response[:200]}...")
                raise ValueError("JSON 형식을 찾을 수 없음")
                
        except Exception as e:
            self.logger.warning(f"통합 감성 분석 응답 파싱 실패: {e}")
            return self._get_default_sentiment()

    @property
    def model(self):
        """호환성을 위한 model 속성 (CLI 사용 시에는 None이 아닌 값 반환)"""
        return "gemini-cli" if self.cli_available else None
    
    async def analyze_comprehensive(
        self,
        symbol: str,
        name: str,
        stock_data: Dict,
        price_data: Optional[List] = None,
        strategy: str = "comprehensive"
    ) -> str:
        """
        Multi-LLM 통합용 종합 분석 메소드
        
        Args:
            symbol: 종목 코드
            name: 종목명
            stock_data: 주식 기본 정보
            price_data: 가격 데이터 (선택)
            strategy: 분석 전략
            
        Returns:
            종합 분석 텍스트 결과
        """
        try:
            self.logger.info(f"🤖 Gemini 종합 분석 시작: {symbol}({name})")
            
            # CLI 사용 가능성 확인
            if not await self._check_gemini_cli_async():
                return self._get_fallback_comprehensive_analysis(symbol, name, stock_data)
            
            # 종합 분석 프롬프트 생성
            prompt = self._create_comprehensive_prompt(symbol, name, stock_data, price_data, strategy)
            
            # Gemini CLI 호출
            response = await self._call_gemini_cli(prompt)
            
            if response and response.strip():
                self.logger.info(f"✅ Gemini 종합 분석 완료: {symbol}")
                return response
            else:
                self.logger.warning(f"⚠️ Gemini 응답 없음: {symbol}")
                return self._get_fallback_comprehensive_analysis(symbol, name, stock_data)
                
        except Exception as e:
            self.logger.error(f"❌ Gemini 종합 분석 실패: {symbol} - {e}")
            return self._get_fallback_comprehensive_analysis(symbol, name, stock_data)
    
    def _create_comprehensive_prompt(
        self,
        symbol: str,
        name: str,
        stock_data: Dict,
        price_data: Optional[List],
        strategy: str
    ) -> str:
        """종합 분석용 프롬프트 생성"""
        
        # 기본 정보 - StockData 객체와 딕셔너리 모두 처리
        if hasattr(stock_data, 'current_price'):
            # StockData 객체인 경우
            current_price = float(getattr(stock_data, 'current_price', 0) or 0)
            volume = int(getattr(stock_data, 'volume', 0) or 0) 
            market_cap = float(getattr(stock_data, 'market_cap', 0) or 0)
        else:
            # 딕셔너리인 경우
            current_price = float(stock_data.get('current_price', 0) or 0)
            volume = int(stock_data.get('volume', 0) or 0)
            market_cap = float(stock_data.get('market_cap', 0) or 0)
        
        # 가격 데이터 요약
        price_summary = ""
        if price_data and len(price_data) > 0:
            last_data = price_data[-1]
            if hasattr(last_data, 'close'):
                # PriceData 객체인 경우
                recent_price = last_data.close
            elif isinstance(last_data, dict):
                # 딕셔너리인 경우
                recent_price = last_data.get('close', current_price)
            else:
                recent_price = current_price
            
            # 숫자 타입인지 확인 후 포맷팅
            if isinstance(recent_price, (int, float)):
                price_summary = f"최근 가격 데이터: {len(price_data)}일, 최근가: {recent_price:,.0f}원"
            else:
                price_summary = f"최근 가격 데이터: {len(price_data)}일"
        
        prompt = f"""
다음 종목에 대한 종합적인 투자 분석을 수행해주세요.

## 기본 정보
- 종목: {symbol} ({name})
- 현재가: {current_price:,}원
- 거래량: {volume:,}주
- 시가총액: {market_cap:,}원
{price_summary}

## 분석 전략: {strategy}

## 요구사항
다음 형식으로 JSON 응답을 제공해주세요:

{{
    "buy_score": 매수점수(0-100),
    "confidence": 신뢰도(0-100),
    "reasoning": "분석 근거 설명",
    "recommendation": "BUY/HOLD/SELL",
    "key_factors": ["핵심 요인1", "핵심 요인2", "핵심 요인3"],
    "risks": ["위험 요인1", "위험 요인2"],
    "opportunities": ["기회 요인1", "기회 요인2"],
    "target_price": "목표가 추정",
    "time_horizon": "투자 기간 권장"
}}

분석 시 고려사항:
1. 현재 시장 상황과 종목의 펀더멘탈 분석
2. 기술적 분석 관점에서의 차트 패턴
3. 업종 및 경쟁사 대비 상대적 위치
4. 최근 뉴스 및 이슈 반영
5. 리스크 대비 수익률 평가

반드시 JSON 형식으로만 응답해주세요.
"""
        return prompt.strip()
    
    def _get_fallback_comprehensive_analysis(
        self,
        symbol: str,
        name: str,
        stock_data: Dict
    ) -> str:
        """Gemini 사용 불가 시 폴백 분석"""
        
        current_price = stock_data.get('current_price', 0)
        
        # 기본적인 분석 결과 생성
        fallback_analysis = {
            "buy_score": 50,
            "confidence": 30,
            "reasoning": f"{name}({symbol})에 대한 기본 분석입니다. Gemini API가 사용 불가능하여 제한된 분석을 제공합니다.",
            "recommendation": "HOLD",
            "key_factors": [
                "Gemini 분석 서비스 일시 중단",
                "기본 정보 기반 중립 평가",
                f"현재가 {current_price:,}원"
            ],
            "risks": [
                "상세 분석 부족",
                "시장 상황 반영 제한"
            ],
            "opportunities": [
                "추후 정밀 분석 가능",
                "기본 투자 정보 확보"
            ],
            "target_price": f"{current_price:,}원 (현재가 유지)",
            "time_horizon": "중기 (3-6개월)"
        }
        
        return json.dumps(fallback_analysis, ensure_ascii=False, indent=2)

    async def _fallback_to_gpt_market_impact(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """Gemini 실패 시 GPT로 백업 - 시장 영향도 분석"""
        try:
            # GPT 분석기 동적 로딩
            from .gpt_analyzer import GPTAnalyzer
            gpt_analyzer = GPTAnalyzer(self.config)
            
            if gpt_analyzer.api_available:
                self.logger.info(f"🔄 {symbol} GPT로 시장 영향도 분석 백업 실행")
                result = await gpt_analyzer.analyze_market_impact(symbol, company_name, news_data)
                return result
            else:
                self.logger.warning(f"⚠️ GPT API도 사용 불가 - 향상된 fallback 분석 사용: {symbol}")
                news_content = "\n\n".join([f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}" for news in news_data])
                return await self._enhanced_market_impact_fallback(symbol, company_name, news_data, news_content)
                
        except Exception as e:
            self.logger.error(f"❌ GPT 백업 시장 영향도 분석 실패 ({symbol}): {e}")
            # 최종 fallback
            news_content = "\n\n".join([f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}" for news in news_data])
            return await self._enhanced_market_impact_fallback(symbol, company_name, news_data, news_content)

    async def _fallback_to_gpt_sentiment(self, symbol: str, company_name: str, news_data: List[Dict]) -> Dict[str, Any]:
        """Gemini 실패 시 GPT로 백업 - 감성 분석"""
        try:
            # GPT 분석기 동적 로딩
            from .gpt_analyzer import GPTAnalyzer
            gpt_analyzer = GPTAnalyzer(self.config)
            
            if gpt_analyzer.api_available:
                self.logger.info(f"🔄 {symbol} GPT로 감성 분석 백업 실행")
                result = await gpt_analyzer.analyze_news_sentiment(symbol, company_name, news_data)
                return result
            else:
                self.logger.warning(f"⚠️ GPT API도 사용 불가 - 향상된 fallback 분석 사용: {symbol}")
                news_content = "\n\n".join([f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}" for news in news_data])
                return await self._enhanced_fallback_analysis(symbol, company_name, news_data, news_content, "통합")
                
        except Exception as e:
            self.logger.error(f"❌ GPT 백업 감성 분석 실패 ({symbol}): {e}")
            # 최종 fallback
            news_content = "\n\n".join([f"제목: {news.get('title', '')}\n내용: {news.get('description', '')}" for news in news_data])
            return await self._enhanced_fallback_analysis(symbol, company_name, news_data, news_content, "통합")