#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading System Performance Analysis Tool
========================================

종목당 실시간 매매 로직 실행 시간 분석 도구
"""

import asyncio
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from utils.logger import get_logger
from config import Config
from data_collectors.kis_collector import KISCollector
from analyzers.technical_analyzer import TechnicalAnalyzer
from data_collectors.chart_data_collector import ChartDataCollector


@dataclass
class PerformanceMetric:
    """성능 측정 메트릭"""
    operation: str
    symbol: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TradingPerformanceAnalyzer:
    """매매 로직 성능 분석기"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger("TradingPerformanceAnalyzer")
        self.metrics = []

        # 컴포넌트 초기화
        self.kis_collector = None
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.chart_data_collector = None

        # 테스트 종목 리스트 (인기 종목들)
        self.test_symbols = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "051910",  # LG화학
            "006400",  # 삼성SDI
            "035720",  # 카카오
            "028260",  # 삼성물산
            "068270",  # 셀트리온
            "207940",  # 삼성바이오로직스
            "000270"   # 기아
        ]

    async def initialize(self):
        """분석기 초기화"""
        try:
            self.kis_collector = KISCollector(self.config)
            await self.kis_collector.initialize()
            self.chart_data_collector = ChartDataCollector(self.kis_collector)
            self.logger.info("✅ 성능 분석기 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"❌ 성능 분석기 초기화 실패: {e}")
            return False

    async def measure_operation(self, operation: str, symbol: str, func, *args, **kwargs):
        """개별 작업 성능 측정"""
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            metric = PerformanceMetric(
                operation=operation,
                symbol=symbol,
                execution_time=execution_time,
                success=True
            )
            self.metrics.append(metric)

            return result, metric

        except Exception as e:
            execution_time = time.time() - start_time

            metric = PerformanceMetric(
                operation=operation,
                symbol=symbol,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
            self.metrics.append(metric)

            return None, metric

    async def analyze_current_price_performance(self, symbols: List[str] = None) -> Dict[str, Any]:
        """현재가 조회 성능 분석"""
        if symbols is None:
            symbols = self.test_symbols[:5]  # 5개 종목만 테스트

        self.logger.info(f"📊 현재가 조회 성능 분석 시작: {len(symbols)}개 종목")

        results = []
        for symbol in symbols:
            result, metric = await self.measure_operation(
                "get_current_price",
                symbol,
                self.kis_collector.get_current_price,
                symbol
            )
            results.append({
                'symbol': symbol,
                'price': result,
                'time': metric.execution_time,
                'success': metric.success
            })

        # 통계 계산
        times = [r['time'] for r in results if r['success']]
        success_rate = len([r for r in results if r['success']]) / len(results) * 100

        return {
            'operation': 'current_price',
            'total_symbols': len(symbols),
            'success_rate': success_rate,
            'avg_time': statistics.mean(times) if times else 0,
            'max_time': max(times) if times else 0,
            'min_time': min(times) if times else 0,
            'total_time': sum(times) if times else 0,
            'results': results
        }

    async def analyze_chart_data_performance(self, symbols: List[str] = None) -> Dict[str, Any]:
        """차트 데이터 수집 성능 분석"""
        if symbols is None:
            symbols = self.test_symbols[:3]  # 3개 종목만 테스트 (차트 데이터는 더 오래 걸림)

        self.logger.info(f"📈 차트 데이터 수집 성능 분석 시작: {len(symbols)}개 종목")

        results = []
        for symbol in symbols:
            result, metric = await self.measure_operation(
                "get_chart_data",
                symbol,
                self._get_chart_data_wrapper,
                symbol
            )
            results.append({
                'symbol': symbol,
                'data_points': len(result) if result else 0,
                'time': metric.execution_time,
                'success': metric.success
            })

        # 통계 계산
        times = [r['time'] for r in results if r['success']]
        success_rate = len([r for r in results if r['success']]) / len(results) * 100

        return {
            'operation': 'chart_data',
            'total_symbols': len(symbols),
            'success_rate': success_rate,
            'avg_time': statistics.mean(times) if times else 0,
            'max_time': max(times) if times else 0,
            'min_time': min(times) if times else 0,
            'total_time': sum(times) if times else 0,
            'results': results
        }

    async def _get_chart_data_wrapper(self, symbol: str):
        """차트 데이터 래퍼 (일봉 30일)"""
        try:
            return await self.chart_data_collector.get_daily_chart_data(symbol, 30)
        except Exception as e:
            self.logger.warning(f"차트 데이터 수집 실패 {symbol}: {e}")
            return []

    async def analyze_technical_analysis_performance(self, symbols: List[str] = None) -> Dict[str, Any]:
        """기술적 분석 성능 분석"""
        if symbols is None:
            symbols = self.test_symbols[:3]

        self.logger.info(f"📊 기술적 분석 성능 분석 시작: {len(symbols)}개 종목")

        results = []
        for symbol in symbols:
            # 먼저 차트 데이터 수집
            chart_data = await self._get_chart_data_wrapper(symbol)
            if not chart_data:
                continue

            # 데이터 변환
            formatted_data = []
            for price_data in chart_data:
                formatted_data.append({
                    'date': price_data.timestamp,
                    'open': float(price_data.open),
                    'high': float(price_data.high),
                    'low': float(price_data.low),
                    'close': float(price_data.close),
                    'volume': int(price_data.volume)
                })

            # 기술적 분석 성능 측정
            result, metric = await self.measure_operation(
                "technical_analysis",
                symbol,
                self.technical_analyzer.analyze_stock,
                symbol,
                formatted_data
            )

            results.append({
                'symbol': symbol,
                'data_points': len(formatted_data),
                'analysis_result': result is not None,
                'time': metric.execution_time,
                'success': metric.success
            })

        # 통계 계산
        times = [r['time'] for r in results if r['success']]
        success_rate = len([r for r in results if r['success']]) / len(results) * 100

        return {
            'operation': 'technical_analysis',
            'total_symbols': len(symbols),
            'success_rate': success_rate,
            'avg_time': statistics.mean(times) if times else 0,
            'max_time': max(times) if times else 0,
            'min_time': min(times) if times else 0,
            'total_time': sum(times) if times else 0,
            'results': results
        }

    async def analyze_full_cycle_performance(self, symbols: List[str] = None) -> Dict[str, Any]:
        """전체 매매 로직 사이클 성능 분석"""
        if symbols is None:
            symbols = self.test_symbols[:3]

        self.logger.info(f"🔄 전체 매매 사이클 성능 분석 시작: {len(symbols)}개 종목")

        results = []
        for symbol in symbols:
            cycle_start = time.time()
            cycle_steps = {}

            # 1. 현재가 조회
            start_time = time.time()
            current_price = await self.kis_collector.get_current_price(symbol)
            cycle_steps['current_price'] = time.time() - start_time

            # 2. 차트 데이터 수집
            start_time = time.time()
            chart_data = await self._get_chart_data_wrapper(symbol)
            cycle_steps['chart_data'] = time.time() - start_time

            # 3. 기술적 분석
            start_time = time.time()
            if chart_data:
                formatted_data = []
                for price_data in chart_data:
                    formatted_data.append({
                        'date': price_data.timestamp,
                        'open': float(price_data.open),
                        'high': float(price_data.high),
                        'low': float(price_data.low),
                        'close': float(price_data.close),
                        'volume': int(price_data.volume)
                    })
                technical_result = await self.technical_analyzer.analyze_stock(symbol, formatted_data)
            else:
                technical_result = None
            cycle_steps['technical_analysis'] = time.time() - start_time

            # 4. 매매 신호 생성 (간단한 로직)
            start_time = time.time()
            signal = self._generate_simple_signal(current_price, technical_result)
            cycle_steps['signal_generation'] = time.time() - start_time

            total_cycle_time = time.time() - cycle_start

            results.append({
                'symbol': symbol,
                'total_time': total_cycle_time,
                'steps': cycle_steps,
                'success': current_price is not None and chart_data is not None
            })

        # 통계 계산
        times = [r['total_time'] for r in results if r['success']]
        success_rate = len([r for r in results if r['success']]) / len(results) * 100

        return {
            'operation': 'full_cycle',
            'total_symbols': len(symbols),
            'success_rate': success_rate,
            'avg_time': statistics.mean(times) if times else 0,
            'max_time': max(times) if times else 0,
            'min_time': min(times) if times else 0,
            'total_time': sum(times) if times else 0,
            'avg_steps': self._calculate_avg_steps(results),
            'results': results
        }

    def _generate_simple_signal(self, current_price, technical_result):
        """간단한 매매 신호 생성 (테스트용)"""
        if not current_price or not technical_result:
            return 'HOLD'

        technical_score = technical_result.get('technical_score', 50)
        if technical_score > 70:
            return 'BUY'
        elif technical_score < 30:
            return 'SELL'
        else:
            return 'HOLD'

    def _calculate_avg_steps(self, results):
        """각 단계별 평균 시간 계산"""
        if not results:
            return {}

        step_times = {}
        successful_results = [r for r in results if r['success']]

        if not successful_results:
            return {}

        # 각 단계별 평균 계산
        for step in ['current_price', 'chart_data', 'technical_analysis', 'signal_generation']:
            times = [r['steps'].get(step, 0) for r in successful_results]
            step_times[step] = {
                'avg': statistics.mean(times) if times else 0,
                'max': max(times) if times else 0,
                'min': min(times) if times else 0
            }

        return step_times

    async def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """종합 성능 분석 실행"""
        self.logger.info("🚀 종합 성능 분석 시작")
        analysis_start = time.time()

        # 분석 결과 저장
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'test_symbols': self.test_symbols[:5],  # 테스트에 사용된 종목들
            'results': {}
        }

        # 1. 현재가 조회 성능
        self.logger.info("1️⃣ 현재가 조회 성능 분석 중...")
        analysis_results['results']['current_price'] = await self.analyze_current_price_performance()

        # 2. 차트 데이터 수집 성능
        self.logger.info("2️⃣ 차트 데이터 수집 성능 분석 중...")
        analysis_results['results']['chart_data'] = await self.analyze_chart_data_performance()

        # 3. 기술적 분석 성능
        self.logger.info("3️⃣ 기술적 분석 성능 분석 중...")
        analysis_results['results']['technical_analysis'] = await self.analyze_technical_analysis_performance()

        # 4. 전체 사이클 성능
        self.logger.info("4️⃣ 전체 매매 사이클 성능 분석 중...")
        analysis_results['results']['full_cycle'] = await self.analyze_full_cycle_performance()

        # 총 분석 시간
        total_analysis_time = time.time() - analysis_start
        analysis_results['total_analysis_time'] = total_analysis_time

        # 결과 요약
        summary = self._generate_performance_summary(analysis_results)
        analysis_results['summary'] = summary

        self.logger.info(f"✅ 종합 성능 분석 완료 (총 소요시간: {total_analysis_time:.2f}초)")

        return analysis_results

    def _generate_performance_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """성능 분석 결과 요약 생성"""
        results = analysis_results['results']

        summary = {
            'bottlenecks': [],
            'recommendations': [],
            'performance_rating': 'GOOD',
            'estimated_capacity': {}
        }

        # 병목 지점 식별
        if results['chart_data']['avg_time'] > 3.0:
            summary['bottlenecks'].append({
                'component': '차트 데이터 수집',
                'avg_time': results['chart_data']['avg_time'],
                'severity': 'HIGH'
            })

        if results['technical_analysis']['avg_time'] > 2.0:
            summary['bottlenecks'].append({
                'component': '기술적 분석',
                'avg_time': results['technical_analysis']['avg_time'],
                'severity': 'MEDIUM'
            })

        if results['current_price']['avg_time'] > 1.0:
            summary['bottlenecks'].append({
                'component': '현재가 조회',
                'avg_time': results['current_price']['avg_time'],
                'severity': 'HIGH'
            })

        # 최적화 권장사항
        full_cycle_time = results['full_cycle']['avg_time']

        if full_cycle_time > 10.0:
            summary['recommendations'].extend([
                "병렬 처리 적용 (asyncio.gather 활용)",
                "차트 데이터 캐싱 시스템 도입",
                "API 호출 최적화 (배치 처리)"
            ])
            summary['performance_rating'] = 'POOR'
        elif full_cycle_time > 5.0:
            summary['recommendations'].extend([
                "일부 작업 병렬 처리 적용",
                "캐싱 시스템 도입 검토"
            ])
            summary['performance_rating'] = 'FAIR'
        else:
            summary['recommendations'].append("현재 성능 수준 양호")

        # 처리 용량 추정
        if full_cycle_time > 0:
            # 30초 모니터링 주기 기준
            max_stocks_sequential = int(25.0 / full_cycle_time)  # 여유 시간 고려
            max_stocks_parallel = min(max_stocks_sequential * 4, 100)  # 병렬 처리 시

            summary['estimated_capacity'] = {
                'sequential_processing': max_stocks_sequential,
                'parallel_processing': max_stocks_parallel,
                'recommended_monitoring_interval': max(30, int(full_cycle_time * 2))
            }

        return summary

    def save_results(self, results: Dict[str, Any], filename: str = None):
        """분석 결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_analysis_{timestamp}.json"

        output_path = Path(f"D:/trading_system/performance_reports/{filename}")
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info(f"📊 성능 분석 결과 저장: {output_path}")
        return output_path


async def main():
    """메인 실행 함수"""
    try:
        # 설정 로드
        config = Config()

        # 성능 분석기 초기화
        analyzer = TradingPerformanceAnalyzer(config)
        if not await analyzer.initialize():
            print("❌ 성능 분석기 초기화 실패")
            return

        # 종합 성능 분석 실행
        results = await analyzer.run_comprehensive_analysis()

        # 결과 저장
        output_file = analyzer.save_results(results)

        # 요약 출력
        print("\n" + "="*60)
        print("🚀 매매 로직 성능 분석 결과 요약")
        print("="*60)

        summary = results['summary']

        print(f"📊 전체 성능 등급: {summary['performance_rating']}")
        print(f"⏱️  종목당 평균 처리 시간: {results['results']['full_cycle']['avg_time']:.2f}초")

        if summary['bottlenecks']:
            print("\n🔍 주요 병목 지점:")
            for bottleneck in summary['bottlenecks']:
                print(f"  - {bottleneck['component']}: {bottleneck['avg_time']:.2f}초 ({bottleneck['severity']})")

        if summary['recommendations']:
            print("\n💡 최적화 권장사항:")
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"  {i}. {rec}")

        capacity = summary['estimated_capacity']
        if capacity:
            print(f"\n📈 예상 처리 용량:")
            print(f"  - 순차 처리: {capacity['sequential_processing']}개 종목")
            print(f"  - 병렬 처리: {capacity['parallel_processing']}개 종목")
            print(f"  - 권장 모니터링 주기: {capacity['recommended_monitoring_interval']}초")

        print(f"\n📄 상세 결과: {output_file}")
        print("="*60)

    except Exception as e:
        print(f"❌ 성능 분석 실행 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())