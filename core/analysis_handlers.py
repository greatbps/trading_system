#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/core/analysis_handlers.py

분석 관련 메뉴 핸들러 - 수정된 버전
"""

import asyncio
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Prompt
from typing import Dict, List, Optional, Tuple
console = Console()

class AnalysisHandlers:
    """분석 관련 핸들러"""
    
    def __init__(self, trading_system):
        self.system = trading_system
        self.logger = trading_system.logger
        
        # 결과 표시 유틸리티 초기화
        from utils.display import DisplayUtils
        self.display = DisplayUtils()
        
        # 데이터 수집 유틸리티 초기화
        from utils.data_utils import DataUtils
        self.data_utils = DataUtils()
    async def debug_data_collector(self):
        """데이터 수집기 디버깅"""
        try:
            console.print("[bold]🔍 데이터 수집기 상태 확인[/bold]")
            
            if not hasattr(self.system, 'data_collector'):
                console.print("[red]❌ data_collector 속성이 없습니다[/red]")
                return False
            
            collector = self.system.data_collector
            console.print(f"[green]✅ data_collector 존재: {type(collector).__name__}[/green]")
            
            # 메서드 존재 여부 확인
            methods_to_check = [
                'get_filtered_stocks',
                'collect_filtered_stocks', 
                'get_stock_list',
                'get_stock_info',
                '_meets_filter_criteria'
            ]
            
            for method in methods_to_check:
                if hasattr(collector, method):
                    console.print(f"[green]  ✅ {method} 메서드 존재[/green]")
                else:
                    console.print(f"[red]  ❌ {method} 메서드 없음[/red]")
            
            # 디버깅 메서드가 있으면 호출
            if hasattr(collector, 'debug_methods'):
                collector.debug_methods()
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 데이터 수집기 디버깅 실패: {e}[/red]")
            return False
    
    async def _safe_get_stocks(self, limit: int) -> List[Tuple[str, str]]:
        """안전한 종목 조회 - 다중 방법 시도"""
        try:
            # 방법 1: data_collector.get_filtered_stocks 직접 호출
            if hasattr(self.system.data_collector, 'get_filtered_stocks'):
                try:
                    console.print("[dim]  🔍 방법 1: get_filtered_stocks 직접 호출...[/dim]")
                    stocks = await self.system.data_collector.get_filtered_stocks(limit)
                    if stocks:
                        console.print(f"[dim]  ✅ 방법 1 성공: {len(stocks)}개[/dim]")
                        return stocks
                except Exception as e:
                    console.print(f"[dim]  ⚠️ 방법 1 실패: {e}[/dim]")
            
            # 방법 2: data_utils.safe_get_filtered_stocks 사용
            try:
                console.print("[dim]  🔍 방법 2: safe_get_filtered_stocks 사용...[/dim]")
                stocks = await self.data_utils.safe_get_filtered_stocks(
                    self.system.data_collector, 
                    limit=limit
                )
                if stocks:
                    console.print(f"[dim]  ✅ 방법 2 성공: {len(stocks)}개[/dim]")
                    return stocks
            except Exception as e:
                console.print(f"[dim]  ⚠️ 방법 2 실패: {e}[/dim]")
            
            # 방법 3: collect_filtered_stocks 사용
            if hasattr(self.system.data_collector, 'collect_filtered_stocks'):
                try:
                    console.print("[dim]  🔍 방법 3: collect_filtered_stocks 사용...[/dim]")
                    filtered_data = await self.system.data_collector.collect_filtered_stocks(max_stocks=limit)
                    if filtered_data:
                        stocks = [(stock['symbol'], stock['name']) for stock in filtered_data]
                        console.print(f"[dim]  ✅ 방법 3 성공: {len(stocks)}개[/dim]")
                        return stocks
                except Exception as e:
                    console.print(f"[dim]  ⚠️ 방법 3 실패: {e}[/dim]")
            
            # 방법 4: 기본 종목 리스트 사용
            if hasattr(self.system.data_collector, 'get_stock_list'):
                try:
                    console.print("[dim]  🔍 방법 4: 기본 종목 리스트 사용...[/dim]")
                    all_stocks = await self.system.data_collector.get_stock_list()
                    if all_stocks:
                        stocks = all_stocks[:limit]
                        console.print(f"[dim]  ✅ 방법 4 성공: {len(stocks)}개[/dim]")
                        return stocks
                except Exception as e:
                    console.print(f"[dim]  ⚠️ 방법 4 실패: {e}[/dim]")
            
            # 방법 5: 실제 종목 리스트에서 랜덤 샘플링
            console.print("[dim]  🔍 방법 5: 실제 종목 리스트에서 샘플링...[/dim]")
            try:
                all_stocks = await self.system.data_collector.get_stock_list()
                if all_stocks:
                    import random
                    # 전체 종목에서 랜덤하게 선택
                    sample_size = min(limit, len(all_stocks))
                    stocks = random.sample(all_stocks, sample_size)
                    console.print(f"[dim]  ✅ 방법 5 성공: 전체 {len(all_stocks)}개 중 {len(stocks)}개 샘플링[/dim]")
                    return stocks
            except Exception as e:
                console.print(f"[dim]  ⚠️ 방법 5 실패: {e}[/dim]")
            
            # 마지막 수단: 빈 리스트 반환 (실제 데이터만 사용)
            console.print("[red]❌ 모든 종목 조회 방법이 실패했습니다. 실제 데이터를 가져올 수 없습니다.[/red]")
            return []
            
        except Exception as e:
            self.logger.error(f"❌ 모든 종목 조회 방법 실패: {e}")
            return []
    
    
    async def comprehensive_analysis(self) -> bool:
        """종합 분석 (5개 영역 통합) - 수정된 안전 버전"""
        console.print("[bold]🔍 종합 분석 (5개 영역 통합: 기술적+펀더멘털+뉴스+수급+패턴)[/bold]")
        
        # 컴포넌트 초기화
        if not await self.system.initialize_components():
            console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
            return False
        
        try:
            # 분석할 종목 수 입력
            target_count = Prompt.ask(
                "[yellow]분석할 종목 수를 입력하세요[/yellow]",
                default="10"
            )
            try:
                target_count = int(target_count)
                target_count = max(1, min(target_count, 50))  # 1~50개 제한
            except:
                target_count = 10
            
            # 종목 조회 - 여러 방법으로 시도
            console.print(f"[blue]📊 {target_count}개 종목 조회 중...[/blue]")
            
            stocks = await self._safe_get_stocks(target_count)
            
            if not stocks:
                console.print("[red]❌ 종목 조회 실패[/red]")
                return False
            
            console.print(f"[green]✅ {len(stocks)}개 종목 조회 완료[/green]")
            
            # 각 종목에 대해 5개 영역 분석 수행
            analysis_results = []
            
            with Progress() as progress:
                task = progress.add_task(
                    f"[cyan]5개 영역 통합 분석 진행중...", 
                    total=len(stocks)
                )
                
                for symbol, name in stocks:
                    progress.update(
                        task, 
                        description=f"[cyan]{name}({symbol}) 분석 중...",
                        advance=0
                    )
                    
                    try:
                        # 종목별 종합 분석
                        result = await self._analyze_single_stock(symbol, name)
                        if result:
                            analysis_results.append(result)
                        
                        # API 호출 제한을 위한 딜레이
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 분석 실패: {e}")
                        continue
                    
                    progress.update(task, advance=1)
            
            if not analysis_results:
                console.print("[red]❌ 분석 결과가 없습니다[/red]")
                return False
            
            # 결과 표시
            self.display.display_comprehensive_analysis_results(analysis_results)
            self.display.display_recommendations_summary(analysis_results)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 종합 분석 실패: {e}")
            console.print(f"[red]❌ 종합 분석 실패: {e}[/red]")
            return False
    
    async def _analyze_single_stock(self, symbol: str, name: str) -> Optional[Dict]:
        """단일 종목에 대한 5개 영역 통합 분석"""
        try:
            # 1. KIS API에서 종목 정보 조회
            stock_info = await self.system.data_collector.get_stock_info(symbol)
            if not stock_info:
                return None
            
            # 2. StockData 객체 생성 (수정: 메서드 확인)
            if hasattr(self.system.data_collector, 'create_stock_data'):
                stock_data = self.system.data_collector.create_stock_data(stock_info)
            else:
                # 기본 딕셔너리 사용
                stock_data = stock_info
            
            # 3. 분석 엔진을 통한 종합 분석
            analysis_result = await self.system.analysis_engine.analyze_comprehensive(
                symbol, name, stock_data, strategy="momentum"
            )
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 단일 분석 실패: {e}")
            return None
    
    # analysis_handlers.py에 추가할 병렬 처리 최적화 코드

# 기존 news_analysis_only() 함수를 아래 코드로 교체하세요:

    async def news_analysis_only(self) -> bool:
        """뉴스 분석만 실행 - kis_collector 병렬 패턴 적용"""
        console.print("[bold]📰 뉴스 재료 분석[/bold]")
        
        if not await self.system.initialize_components():
            return False
        
        try:
            # 분석할 종목 수 입력 (기존 로직 유지)
            target_count = Prompt.ask(
                "[yellow]분석할 종목 수를 입력하세요[/yellow]",
                default="10"
            )
            try:
                target_count = int(target_count)
                target_count = max(5, min(target_count, 20))
            except:
                target_count = 10
            
            # 종목 조회 (기존 로직 유지)
            console.print(f"[blue]📊 {target_count}개 종목 조회 중...[/blue]")
            stocks = await self.data_utils.safe_get_filtered_stocks(
                self.system.data_collector, 
                limit=target_count
            )
            
            # === kis_collector 패턴 적용한 병렬 처리 ===
            news_results = []
            processed_count = 0
            
            # 세마포어 설정 (동시 연결 제한)
            semaphore = asyncio.Semaphore(5)
            
            async def process_single_stock(symbol_name_tuple):
                nonlocal processed_count
                
                async with semaphore:
                    try:
                        symbol, name = symbol_name_tuple
                        processed_count += 1
                        
                        # 뉴스 분석 수행
                        news_summary = await self._analyze_news_for_stock(symbol, name)
                        if news_summary:
                            news_results.append(news_summary)
                            # 재료 발견시 로그
                            if news_summary.get('has_material', False):
                                self.logger.info(f"🔥 {symbol} 재료 발견: {news_summary.get('material_type')}")
                        
                        return True
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 뉴스 분석 실패: {e}")
                        return False
            
            # 배치 처리로 병렬 실행
            with Progress() as progress:
                task = progress.add_task("[cyan]뉴스 분석 중...", total=len(stocks))
                
                batch_size = 10  # 10개씩 배치 처리
                for i in range(0, len(stocks), batch_size):
                    batch = stocks[i:i + batch_size]
                    tasks = [process_single_stock(stock) for stock in batch]
                    
                    # 병렬 실행
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # 진행률 업데이트
                    progress.update(task, advance=len(batch))
            
            # === 기존 결과 처리 로직 유지 ===
            if news_results:
                self.display.display_news_analysis_results(news_results)
                return True
            else:
                console.print("[yellow]⚠️ 뉴스 분석 결과가 없습니다[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ 뉴스 분석 실패: {e}[/red]")
            return False
    
    async def _analyze_news_for_stock(self, symbol: str, name: str) -> Optional[Dict]:
        """개별 종목 뉴스 분석"""
        try:
            # 수정: news_collector가 직접 analysis_engine에 있는지 확인
            if hasattr(self.system, 'news_collector') and self.system.news_collector:
                # 직접 news_collector 사용
                if hasattr(self.system.news_collector, 'get_news_analysis_summary'):
                    news_summary = self.system.news_collector.get_news_analysis_summary(name, symbol)
                elif hasattr(self.system.news_collector, 'analyze_stock_news'):
                    news_summary = await self.system.news_collector.analyze_stock_news(symbol, name)
                else:
                    # 기본 뉴스 분석
                    news_summary = await self._basic_news_analysis(symbol, name)
            else:
                # analysis_engine 통해서 시도
                if (hasattr(self.system.analysis_engine, 'news_collector') and 
                    self.system.analysis_engine.news_collector):
                    news_summary = self.system.analysis_engine.news_collector.get_news_analysis_summary(name, symbol)
                else:
                    news_summary = await self._basic_news_analysis(symbol, name)
            
            if news_summary:
                return {
                    'symbol': symbol,
                    'name': name,
                    'has_material': news_summary.get('has_material', False),
                    'material_type': news_summary.get('material_type', '재료없음'),
                    'material_score': news_summary.get('material_score', 0),
                    'news_count': news_summary.get('news_count', 0),
                    'sentiment_score': news_summary.get('sentiment_score', 0),
                    'keywords': news_summary.get('keywords', [])
                }
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 뉴스 분석 실패: {e}")
            return None
    
    async def _basic_news_analysis(self, symbol: str, name: str) -> Dict:
        """기본 뉴스 분석 (뉴스 수집기가 없을 때)"""
        # 임시 기본값 반환
        return {
            'has_material': False,
            'material_type': '분석불가',
            'material_score': 0,
            'news_count': 0,
            'sentiment_score': 0,
            'keywords': []
        }
    
    async def supply_demand_analysis_only(self) -> bool:
        """수급정보 분석만 실행"""
        console.print("[bold]💰 수급정보 분석 (외국인/기관/개인 매매동향)[/bold]")
        
        if not await self.system.initialize_components():
            return False
        
        try:
            # 분석할 종목 수 입력
            target_count = Prompt.ask(
                "[yellow]분석할 종목 수를 입력하세요[/yellow]",
                default="15"
            )
            try:
                target_count = int(target_count)
                target_count = max(5, min(target_count, 30))
            except:
                target_count = 15
            
            # 종목 조회
            console.print(f"[blue]📊 {target_count}개 종목 조회 중...[/blue]")
            stocks = await self.data_utils.safe_get_filtered_stocks(
                self.system.data_collector, 
                limit=target_count
            )
            
            if not stocks:
                console.print("[red]❌ 종목 조회 실패[/red]")
                return False
            
            supply_results = []
            with Progress() as progress:
                task = progress.add_task("[cyan]수급 분석 중...", total=len(stocks))
                
                for symbol, name in stocks:
                    progress.update(
                        task, 
                        description=f"[cyan]{name}({symbol}) 수급 분석 중...",
                        advance=0
                    )
                    
                    try:
                        # 수급 분석 수행
                        supply_result = await self._analyze_supply_demand_for_stock(symbol, name)
                        if supply_result:
                            supply_results.append(supply_result)
                        
                        await asyncio.sleep(0.15)
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 수급 분석 실패: {e}")
                    
                    progress.update(task, advance=1)
            
            # 수급 분석 결과 표시
            if supply_results:
                self.display.display_supply_demand_results(supply_results)
                return True
            else:
                console.print("[yellow]⚠️ 수급 분석 결과가 없습니다[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ 수급 분석 실패: {e}[/red]")
            return False
    
    async def _analyze_supply_demand_for_stock(self, symbol: str, name: str) -> Optional[Dict]:
        """개별 종목 수급 분석"""
        try:
            # 종목 정보 조회
            stock_info = await self.system.data_collector.get_stock_info(symbol)
            if stock_info:
                # StockData 객체 생성
                if hasattr(self.system.data_collector, 'create_stock_data'):
                    stock_data = self.system.data_collector.create_stock_data(stock_info)
                else:
                    stock_data = stock_info
                
                # 수급 분석 수행
                if hasattr(self.system.analysis_engine, 'calculate_supply_demand_score'):
                    supply_analysis = await self.system.analysis_engine.calculate_supply_demand_score(symbol, stock_data)
                else:
                    # 기본 수급 분석
                    supply_analysis = await self._basic_supply_demand_analysis(symbol, stock_data)
                
                return {
                    'symbol': symbol,
                    'name': name,
                    'overall_score': supply_analysis.get('overall_score', 50),
                    'foreign_score': supply_analysis.get('foreign_score', 50),
                    'institution_score': supply_analysis.get('institution_score', 50),
                    'individual_score': supply_analysis.get('individual_score', 50),
                    'volume_score': supply_analysis.get('volume_score', 50),
                    'smart_money_dominance': supply_analysis.get('supply_demand_balance', {}).get('smart_money_dominance', False),
                    'trading_intensity': supply_analysis.get('trading_intensity', {}).get('intensity_level', 'normal'),
                    'market_cap': getattr(stock_data, 'market_cap', 0) if hasattr(stock_data, 'market_cap') else stock_data.get('market_cap', 0),
                    'volume': getattr(stock_data, 'volume', 0) if hasattr(stock_data, 'volume') else stock_data.get('volume', 0),
                    'trading_value': getattr(stock_data, 'trading_value', 0) if hasattr(stock_data, 'trading_value') else stock_data.get('trading_value', 0)
                }
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 수급 분석 실패: {e}")
            return None
    
    async def _basic_supply_demand_analysis(self, symbol: str, stock_data) -> Dict:
        """기본 수급 분석 (메서드가 없을 때)"""
        # 기본 수급 분석 로직
        volume = getattr(stock_data, 'volume', 0) if hasattr(stock_data, 'volume') else stock_data.get('volume', 0)
        
        # 간단한 점수 계산
        volume_score = min(100, (volume / 1000000) * 10) if volume > 0 else 50
        
        return {
            'overall_score': volume_score,
            'foreign_score': 50,
            'institution_score': 50,
            'individual_score': 50,
            'volume_score': volume_score,
            'supply_demand_balance': {'smart_money_dominance': False},
            'trading_intensity': {'intensity_level': 'normal'}
        }
    
    async def chart_pattern_analysis_only(self) -> bool:
        """차트패턴 분석만 실행"""
        console.print("[bold]📈 차트패턴 분석 (캔들패턴 + 기술적패턴)[/bold]")
        
        if not await self.system.initialize_components():
            return False
        
        try:
            # 분석할 종목 수 입력
            target_count = Prompt.ask(
                "[yellow]분석할 종목 수를 입력하세요[/yellow]",
                default="15"
            )
            try:
                target_count = int(target_count)
                target_count = max(5, min(target_count, 30))
            except:
                target_count = 15
            
            # 종목 조회
            console.print(f"[blue]📊 {target_count}개 종목 조회 중...[/blue]")
            stocks = await self.data_utils.safe_get_filtered_stocks(
                self.system.data_collector, 
                limit=target_count
            )
            
            if not stocks:
                console.print("[red]❌ 종목 조회 실패[/red]")
                return False
            
            pattern_results = []
            with Progress() as progress:
                task = progress.add_task("[cyan]차트패턴 분석 중...", total=len(stocks))
                
                for symbol, name in stocks:
                    progress.update(
                        task, 
                        description=f"[cyan]{name}({symbol}) 패턴 분석 중...",
                        advance=0
                    )
                    
                    try:
                        # 차트패턴 분석 수행
                        pattern_result = await self._analyze_chart_pattern_for_stock(symbol, name)
                        if pattern_result:
                            pattern_results.append(pattern_result)
                        
                        await asyncio.sleep(0.15)
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 패턴 분석 실패: {e}")
                    
                    progress.update(task, advance=1)
            
            # 차트패턴 분석 결과 표시
            if pattern_results:
                self.display.display_pattern_analysis_results(pattern_results)
                return True
            else:
                console.print("[yellow]⚠️ 차트패턴 분석 결과가 없습니다[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ 차트패턴 분석 실패: {e}[/red]")
            return False
    
    async def _analyze_chart_pattern_for_stock(self, symbol: str, name: str) -> Optional[Dict]:
        """개별 종목 차트패턴 분석"""
        try:
            # 종목 정보 조회
            stock_info = await self.system.data_collector.get_stock_info(symbol)
            if stock_info:
                # StockData 객체 생성
                if hasattr(self.system.data_collector, 'create_stock_data'):
                    stock_data = self.system.data_collector.create_stock_data(stock_info)
                else:
                    stock_data = stock_info
                
                # 차트패턴 분석 수행
                if hasattr(self.system.analysis_engine, 'calculate_chart_pattern_score'):
                    pattern_analysis = await self.system.analysis_engine.calculate_chart_pattern_score(symbol, stock_data)
                else:
                    # 기본 패턴 분석
                    pattern_analysis = await self._basic_chart_pattern_analysis(symbol, stock_data)
                
                return {
                    'symbol': symbol,
                    'name': name,
                    'overall_score': pattern_analysis.get('overall_score', 50),
                    'candle_pattern_score': pattern_analysis.get('candle_pattern_score', 50),
                    'technical_pattern_score': pattern_analysis.get('technical_pattern_score', 50),
                    'trendline_score': pattern_analysis.get('trendline_score', 50),
                    'support_resistance_score': pattern_analysis.get('support_resistance_score', 50),
                    'confidence': pattern_analysis.get('confidence', 0.5),
                    'recommendation': pattern_analysis.get('recommendation', 'HOLD'),
                    'detected_patterns': pattern_analysis.get('detected_patterns', [])
                }
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 차트패턴 분석 실패: {e}")
            return None
    
    async def _basic_chart_pattern_analysis(self, symbol: str, stock_data) -> Dict:
        """기본 차트패턴 분석 (메서드가 없을 때) - 안전한 속성 접근"""
        def safe_get(data, attr, default=None):
            try:
                if isinstance(data, dict):
                    return data.get(attr, default)
                else:
                    return getattr(data, attr, default)
            except (AttributeError, TypeError):
                return default
        
        # 안전한 속성 접근
        current_price = safe_get(stock_data, 'current_price', 0)
        
        # 기본 점수 계산
        base_score = 50
        
        return {
            'overall_score': base_score,
            'candle_pattern_score': base_score,
            'technical_pattern_score': base_score,
            'trendline_score': base_score,
            'support_resistance_score': base_score,
            'confidence': 0.5,
            'recommendation': 'HOLD',
            'detected_patterns': ['기본분석']
        }