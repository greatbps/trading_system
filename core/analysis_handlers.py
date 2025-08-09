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
    
    async def _safe_get_stocks(self, strategy: str, limit: int) -> List[Tuple[str, str]]:
        """안전한 종목 조회 - data_collector를 사용하여 전략별 필터링"""
        try:
            console.print(f"[dim]'{strategy}' 전략으로 HTS 조건검색 종목 조회 시도...[/dim]")
            stocks = await self.system.data_collector.get_filtered_stocks(strategy, limit)
            if not stocks:
                console.print(f"[red]❌ '{strategy}' 전략에 대한 HTS 조건검색 결과를 가져오지 못했습니다. Fallback을 확인하세요.[/red]")
                self.logger.error(f"❌ HTS 조건검색 실패 또는 결과 없음 (전략: {strategy}).")
                return []
            
            console.print(f"[green]✅ HTS 조건검색으로 {len(stocks)}개 종목 조회 성공[/green]")
            return stocks
            
        except Exception as e:
            self.logger.error(f"❌ 종목 조회 중 심각한 오류 발생: {e}")
            console.print(f"[red]❌ 종목 조회 실패: {e}[/red]")
            return []
    
    
    async def comprehensive_analysis(self) -> bool:
        """종합 분석 (5개 영역 통합) - 44번 메뉴 전용 (DB 저장 안함)"""
        console.print("[bold]🔍 종합 분석 (5개 영역 통합: 기술적+펀더멘털+뉴스+수급+패턴)[/bold]")
        console.print("[dim]ℹ️ 이 분석은 실시간 확인용으로 데이터베이스에 저장되지 않습니다.[/dim]")
        
        if not await self.system.initialize_components():
            console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
            return False
        
        try:
            # 1. 전략 선택
            strategy_names = list(self.system.config.trading.HTS_CONDITION_NAMES.keys())
            strategy_menu = "\n".join([f"  {i+1}. {name}" for i, name in enumerate(strategy_names)])
            console.print(f"\n[bold]분석할 전략을 선택하세요:[/bold]\n{strategy_menu}")
            
            choice = Prompt.ask("전략 번호 선택", choices=[str(i+1) for i in range(len(strategy_names))], default="1")
            selected_strategy = strategy_names[int(choice)-1]
            console.print(f"[green]✅ '{selected_strategy}' 전략 선택됨[/green]")

            # 2. 분석할 종목 수 입력
            target_count = Prompt.ask(
                "[yellow]분석할 종목 수를 입력하세요[/yellow]",
                default="10"
            )
            try:
                target_count = int(target_count)
                target_count = max(1, min(target_count, 50))
            except ValueError:
                target_count = 10
            
            # 3. 전략 기반 종목 조회
            console.print(f"[blue]📊 '{selected_strategy}' 전략으로 {target_count}개 종목 조회 중...[/blue]")
            stocks = await self._safe_get_stocks(selected_strategy, target_count)
            
            if not stocks:
                console.print("[red]❌ 종목 조회 실패[/red]")
                return False
            
            console.print(f"[green]✅ {len(stocks)}개 종목 조회 완료[/green]")
            
            # 4. 각 종목에 대해 5개 영역 분석 수행
            analysis_results = []
            
            with Progress() as progress:
                task = progress.add_task(
                    f"[cyan]'{selected_strategy}' 전략으로 통합 분석 진행중...", 
                    total=len(stocks)
                )
                
                for symbol, name in stocks:
                    progress.update(
                        task, 
                        description=f"[cyan]{name}({symbol}) 분석 중...",
                        advance=0
                    )
                    
                    try:
                        result = await self._analyze_single_stock(symbol, name, selected_strategy)
                        if result:
                            analysis_results.append(result)
                        
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 분석 실패: {e}")
                        continue
                    
                    progress.update(task, advance=1)
            
            if not analysis_results:
                console.print("[red]❌ 분석 결과가 없습니다[/red]")
                return False
            
            # 5. 결과 표시
            console.print("[dim]ℹ️ 실시간 분석 결과 표시 중... (DB 저장 없음)[/dim]")
            self.display.display_comprehensive_analysis_results(analysis_results)
            self.display.display_recommendations_summary(analysis_results)
            console.print("[dim]ℹ️ 종합 분석 완료. 결과는 메모리에서만 표시되었습니다.[/dim]")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 종합 분석 실패: {e}")
            console.print(f"[red]❌ 종합 분석 실패: {e}[/red]")
            return False
    
    async def _analyze_single_stock(self, symbol: str, name: str, strategy: str) -> Optional[Dict]:
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

            # 3. SupplyDemandAnalyzer에 kis_collector 설정
            if hasattr(self.system.analysis_engine, 'supply_demand_analyzer'):
                self.system.analysis_engine.supply_demand_analyzer.set_kis_collector(self.system.data_collector)
            
            # 4. 분석 엔진을 통한 종합 분석
            analysis_result = await self.system.analysis_engine.analyze_comprehensive(
                symbol, name, stock_data, strategy=strategy
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
        """개별 종목 뉴스 분석 - KIS API 활용"""
        try:
            # 방법 1: data_collector에서 실제 뉴스 데이터 가져오기
            if hasattr(self.system.data_collector, 'get_news_data'):
                try:
                    news_data = await self.system.data_collector.get_news_data(symbol, name, days=7)
                    if news_data:
                        # 실제 뉴스 데이터 기반 분석
                        news_summary = self._process_real_news_data(news_data, symbol, name)
                        return news_summary
                except Exception as e:
                    self.logger.warning(f"⚠️ KIS 뉴스 데이터 조회 실패 {symbol}: {e}")
            
            # 방법 2: analysis_engine의 뉴스 분석 기능 활용
            if hasattr(self.system, 'analysis_engine') and self.system.analysis_engine:
                try:
                    if hasattr(self.system.analysis_engine, 'analyze_news_sentiment'):
                        news_analysis = await self.system.analysis_engine.analyze_news_sentiment(symbol, name)
                        if news_analysis:
                            return {
                                'symbol': symbol,
                                'name': name,
                                'has_material': news_analysis.get('has_positive_news', False),
                                'material_type': news_analysis.get('dominant_sentiment', '중립'),
                                'material_score': news_analysis.get('sentiment_score', 50),
                                'news_count': news_analysis.get('news_count', 0),
                                'sentiment_score': news_analysis.get('sentiment_score', 50),
                                'keywords': news_analysis.get('keywords', [])
                            }
                except Exception as e:
                    self.logger.warning(f"⚠️ 분석엔진 뉴스 분석 실패 {symbol}: {e}")
            
            # 방법 3: 기본 뉴스 분석 (실패 시)
            news_summary = await self._basic_news_analysis(symbol, name)
            return news_summary
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 뉴스 분석 실패: {e}")
            return None

    def _process_real_news_data(self, news_data: List[Dict], symbol: str, name: str) -> Dict:
        """실제 뉴스 데이터를 처리하여 분석 결과 생성"""
        try:
            if not news_data:
                return {
                    'symbol': symbol,
                    'name': name,
                    'has_material': False,
                    'material_type': '뉴스없음',
                    'material_score': 50,
                    'news_count': 0,
                    'sentiment_score': 50,
                    'keywords': []
                }
            
            # 뉴스 감정 분석
            positive_count = 0
            negative_count = 0
            total_impact_score = 0
            keywords = []
            
            for news in news_data:
                sentiment = news.get('sentiment', 'NEUTRAL')
                impact_score = news.get('impact_score', 50)
                
                total_impact_score += impact_score
                
                if sentiment == 'POSITIVE':
                    positive_count += 1
                elif sentiment == 'NEGATIVE':
                    negative_count += 1
                
                # 키워드 추출 (간단한 예)
                title = news.get('title', '')
                if any(word in title for word in ['실적', '매출', '영업이익']):
                    keywords.append('실적')
                if any(word in title for word in ['신규', '진출', '투자']):
                    keywords.append('사업확장')
                if any(word in title for word in ['우려', '하락', '부진']):
                    keywords.append('리스크')
            
            # 전체적인 감정 점수 계산
            news_count = len(news_data)
            avg_impact_score = total_impact_score / news_count if news_count > 0 else 50
            
            # 재료성 판단
            has_material = positive_count > negative_count and avg_impact_score > 60
            
            # 주요 재료 유형 결정
            if positive_count > negative_count:
                material_type = '긍정재료'
            elif negative_count > positive_count:
                material_type = '부정재료'
            else:
                material_type = '중립'
            
            return {
                'symbol': symbol,
                'name': name,
                'has_material': has_material,
                'material_type': material_type,
                'material_score': int(avg_impact_score),
                'news_count': news_count,
                'sentiment_score': int(avg_impact_score),
                'keywords': list(set(keywords))  # 중복 제거
            }
            
        except Exception as e:
            self.logger.error(f"❌ 뉴스 데이터 처리 실패 {symbol}: {e}")
            return {
                'symbol': symbol,
                'name': name,
                'has_material': False,
                'material_type': '처리실패',
                'material_score': 50,
                'news_count': 0,
                'sentiment_score': 50,
                'keywords': []
            }
    
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
        """개별 종목 차트패턴 분석 - 실제 OHLCV 데이터 활용"""
        try:
            # 1. 종목 정보 조회
            stock_info = await self.system.data_collector.get_stock_info(symbol)
            if not stock_info:
                return None
                
            # 2. OHLCV 데이터 조회 (차트패턴 분석을 위해 필수)
            try:
                ohlcv_data = await self.system.data_collector.get_ohlcv_data(symbol, period="D", count=60)
                if not ohlcv_data:
                    self.logger.warning(f"⚠️ {symbol} OHLCV 데이터 없음")
                    return await self._basic_chart_pattern_analysis(symbol, stock_info)
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} OHLCV 조회 실패: {e}")
                return await self._basic_chart_pattern_analysis(symbol, stock_info)
            
            # 3. 실제 차트패턴 분석
            try:
                if hasattr(self.system.analysis_engine, 'calculate_chart_pattern_score'):
                    pattern_analysis = await self.system.analysis_engine.calculate_chart_pattern_score(symbol, stock_info, ohlcv_data)
                else:
                    # OHLCV 데이터를 활용한 고급 패턴 분석
                    pattern_analysis = await self._advanced_chart_pattern_analysis(symbol, stock_info, ohlcv_data)
                
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
                    'detected_patterns': pattern_analysis.get('detected_patterns', ['실제차트분석'])
                }
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} 고급 패턴 분석 실패: {e}")
                return await self._basic_chart_pattern_analysis(symbol, stock_info)
            return None
        except Exception as e:
            self.logger.error(f"❌ {symbol} 차트패턴 분석 실패: {e}")
            return None

    async def _advanced_chart_pattern_analysis(self, symbol: str, stock_data, ohlcv_data: list) -> Dict:
        """OHLCV 데이터를 활용한 고급 차트패턴 분석"""
        try:
            if not ohlcv_data or len(ohlcv_data) < 20:
                return await self._basic_chart_pattern_analysis(symbol, stock_data)
            
            # 가격 데이터 추출
            closes = [candle.close_price for candle in ohlcv_data]
            highs = [candle.high_price for candle in ohlcv_data]
            lows = [candle.low_price for candle in ohlcv_data]
            volumes = [candle.volume for candle in ohlcv_data]
            
            # 1. 이동평균 기반 추세 분석
            sma_20 = sum(closes[:20]) / 20 if len(closes) >= 20 else closes[0]
            current_price = closes[0]  # 최신 가격
            trend_score = 60 if current_price > sma_20 else 40
            
            # 2. 볼륨 패턴 분석
            avg_volume = sum(volumes[:10]) / 10 if len(volumes) >= 10 else volumes[0]
            volume_spike = volumes[0] > avg_volume * 1.5
            volume_score = 70 if volume_spike else 50
            
            # 3. 지지저항 분석
            recent_highs = sorted(highs[:20], reverse=True)[:3]
            recent_lows = sorted(lows[:20])[:3]
            
            resistance_level = sum(recent_highs) / len(recent_highs)
            support_level = sum(recent_lows) / len(recent_lows)
            
            # 현재가가 지지저항선과의 관계
            price_position = (current_price - support_level) / (resistance_level - support_level) if resistance_level != support_level else 0.5
            support_resistance_score = int(50 + (price_position - 0.5) * 40)  # 0.5 중심으로 ±20점
            
            # 4. 캔들 패턴 분석 (간단한 예)
            if len(ohlcv_data) >= 2:
                current_candle = ohlcv_data[0]
                previous_candle = ohlcv_data[1]
                
                # 양봉/음봉 패턴
                is_bullish = current_candle.close_price > current_candle.open_price
                is_engulfing = (is_bullish and 
                              current_candle.close_price > previous_candle.high_price and
                              current_candle.open_price < previous_candle.low_price)
                
                candle_score = 75 if is_engulfing else (60 if is_bullish else 40)
            else:
                candle_score = 50
            
            # 5. 전체 점수 계산
            overall_score = int((trend_score * 0.3 + volume_score * 0.2 + 
                               support_resistance_score * 0.3 + candle_score * 0.2))
            
            # 6. 추천 등급 결정
            if overall_score >= 70:
                recommendation = 'BUY'
            elif overall_score >= 55:
                recommendation = 'HOLD'  
            else:
                recommendation = 'SELL'
            
            # 7. 패턴 감지
            detected_patterns = []
            if volume_spike:
                detected_patterns.append('거래량급증')
            if trend_score > 55:
                detected_patterns.append('상승추세')
            if support_resistance_score > 60:
                detected_patterns.append('저항돌파')
            if not detected_patterns:
                detected_patterns.append('횡보')
            
            return {
                'overall_score': max(20, min(80, overall_score)),  # 20-80 범위로 제한
                'candle_pattern_score': max(20, min(80, candle_score)),
                'technical_pattern_score': max(20, min(80, trend_score)),
                'trendline_score': max(20, min(80, trend_score)),
                'support_resistance_score': max(20, min(80, support_resistance_score)),
                'confidence': min(0.9, len(ohlcv_data) / 60),  # 데이터 많을수록 신뢰도 증가
                'recommendation': recommendation,
                'detected_patterns': detected_patterns
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 고급 패턴 분석 실패: {e}")
            return await self._basic_chart_pattern_analysis(symbol, stock_data)
    
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