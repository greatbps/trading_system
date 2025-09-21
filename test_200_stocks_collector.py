#!/usr/bin/env python3
"""
200개 종목 데이터 수집 테스트
네이버 증권 API를 사용한 대량 종목 데이터 수집 구현
"""

import asyncio
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StockData:
    """주식 데이터 클래스"""
    symbol: str
    name: str
    current_price: int
    change_rate: float
    volume: int
    market_status: str
    timestamp: datetime

class Naver200StockCollector:
    """네이버 API를 사용한 200개 종목 데이터 수집기"""

    def __init__(self, max_workers: int = 8, timeout: int = 3):
        self.max_workers = max_workers
        self.timeout = timeout
        self.results_lock = Lock()
        self.success_results: List[StockData] = []
        self.failed_symbols: List[str] = []

    def parse_price(self, price_str: str) -> int:
        """쉼표가 포함된 가격 문자열을 숫자로 변환"""
        if not price_str:
            return 0
        return int(price_str.replace(',', ''))

    def parse_float(self, value_str: str) -> float:
        """문자열을 float으로 변환"""
        if not value_str:
            return 0.0
        return float(value_str)

    def get_stock_data(self, symbol: str) -> Optional[StockData]:
        """단일 종목 데이터 조회"""
        try:
            url = f'https://polling.finance.naver.com/api/realtime/domestic/stock/{symbol}'
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('datas'):
                    stock = data['datas'][0]

                    stock_data = StockData(
                        symbol=symbol,
                        name=stock.get('stockName', 'Unknown'),
                        current_price=self.parse_price(stock.get('closePrice', '0')),
                        change_rate=self.parse_float(stock.get('fluctuationsRatio', '0')),
                        volume=self.parse_price(stock.get('accumulatedTradingVolume', '0')),
                        market_status=stock.get('marketStatus', 'UNKNOWN'),
                        timestamp=datetime.now()
                    )

                    with self.results_lock:
                        self.success_results.append(stock_data)

                    return stock_data

            with self.results_lock:
                self.failed_symbols.append(symbol)

            return None

        except Exception as e:
            with self.results_lock:
                self.failed_symbols.append(symbol)
            return None

    async def collect_stocks(self, symbols: List[str]) -> Dict:
        """비동기로 다수 종목 데이터 수집"""
        print(f"🚀 Starting collection of {len(symbols)} stocks...")
        print(f"📊 Using {self.max_workers} concurrent threads")

        # 결과 초기화
        self.success_results = []
        self.failed_symbols = []

        start_time = time.time()

        # ThreadPoolExecutor로 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, self.get_stock_data, symbol)
                for symbol in symbols
            ]

            # 모든 요청 완료 대기
            await asyncio.gather(*futures)

        elapsed = time.time() - start_time

        # 결과 정리
        success_count = len(self.success_results)
        failed_count = len(self.failed_symbols)
        success_rate = success_count / len(symbols) * 100

        results = {
            'total_requested': len(symbols),
            'successful': success_count,
            'failed': failed_count,
            'success_rate': success_rate,
            'elapsed_time': elapsed,
            'requests_per_second': len(symbols) / elapsed,
            'stock_data': self.success_results,
            'failed_symbols': self.failed_symbols,
            'timestamp': datetime.now()
        }

        print(f"✅ Collection completed in {elapsed:.1f}s")
        print(f"📈 Success rate: {success_rate:.1f}% ({success_count}/{len(symbols)})")
        print(f"⚡ Speed: {len(symbols)/elapsed:.1f} requests/second")

        return results

def get_test_symbols() -> List[str]:
    """테스트용 종목 코드 200개 생성"""
    # 실제 한국 주식 종목 코드들
    symbols = [
        # 코스피 대형주 (30개)
        '005930', '000660', '035420', '005380', '051910', '068270', '035720', '207940',
        '373220', '000270', '003670', '096770', '034730', '055550', '015760', '017670',
        '105560', '032830', '036570', '018260', '011170', '000720', '047050', '001570',
        '011780', '024110', '267250', '000810', '066570', '028260',

        # 코스피 중형주 (50개)
        '086790', '047810', '161390', '139480', '021240', '030200', '004020', '004170',
        '009540', '180640', '251270', '128940', '004990', '010950', '011200', '018880',
        '002790', '003550', '004000', '009150', '010620', '016360', '023530', '028050',
        '033780', '042660', '052690', '064350', '071050', '078930', '083650', '090430',
        '097950', '114090', '122870', '138040', '145990', '192820', '204320', '213420',
        '226320', '267260', '272210', '285130', '293490', '302440', '316140', '329180',
        '336260', '361610',

        # 코스피 소형주 (40개)
        '000020', '000040', '000050', '000070', '000100', '000120', '000150', '000180',
        '000210', '000240', '000300', '000320', '000370', '000430', '000480', '000500',
        '000540', '000590', '000640', '000670', '000700', '000760', '000770', '000830',
        '000880', '000910', '000950', '000990', '001040', '001060', '001120', '001200',
        '001230', '001250', '001260', '001290', '001340', '001360', '001390', '001440',

        # 코스닥 주요종목 (80개)
        '091990', '326030', '028300', '196170', '302440', '086520', '039030', '357780',
        '263750', '145720', '041510', '060280', '214150', '079550', '137310', '095340',
        '131970', '293490', '078600', '112040', '141080', '183300', '214370', '240810',
        '256940', '277810', '322510', '348210', '365340', '950140', '005290', '006280',
        '016790', '067310', '084370', '101490', '114190', '119860', '120110', '134790',
        '138930', '158430', '171090', '192650', '200670', '215200', '220260', '225570',
        '237880', '252990', '263860', '290650', '298540', '314130', '331380', '347860',
        '365550', '377030', '383310', '394280', '413600', '950130', '950210', '950220',
        '036810', '053610', '067160', '084690', '101140', '114810', '120030', '134390',
        '139130', '158430', '171010', '192400', '200880', '215000', '220100', '225190',
        '237750', '252670', '263920', '290720', '298380', '314140'
    ]

    return symbols[:200]  # 정확히 200개

async def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🎯 200개 종목 데이터 수집 시스템 테스트")
    print("=" * 60)

    # 테스트 종목 준비
    test_symbols = get_test_symbols()
    print(f"📋 Test symbols prepared: {len(test_symbols)}")

    # 수집기 초기화
    collector = Naver200StockCollector(max_workers=8, timeout=3)

    # 데이터 수집 실행
    results = await collector.collect_stocks(test_symbols)

    # 결과 분석
    print("\n" + "=" * 60)
    print("📊 COLLECTION RESULTS")
    print("=" * 60)
    print(f"Total requested: {results['total_requested']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Success rate: {results['success_rate']:.1f}%")
    print(f"Elapsed time: {results['elapsed_time']:.1f} seconds")
    print(f"Requests/second: {results['requests_per_second']:.1f}")

    # 성공한 종목 일부 출력
    if results['stock_data']:
        print(f"\n📈 Sample successful results (first 10):")
        for i, stock in enumerate(results['stock_data'][:10], 1):
            print(f"  {i:2d}. {stock.symbol} {stock.name}: {stock.current_price:,}원 ({stock.change_rate:+.2f}%)")

    # 실패한 종목 출력
    if results['failed_symbols']:
        print(f"\n❌ Failed symbols ({len(results['failed_symbols'])}): {results['failed_symbols'][:20]}")

    # 성능 평가
    print(f"\n⚡ PERFORMANCE EVALUATION")
    if results['success_rate'] >= 90:
        print("✅ EXCELLENT: System ready for production use")
    elif results['success_rate'] >= 80:
        print("✅ GOOD: System suitable with minor optimizations")
    elif results['success_rate'] >= 70:
        print("⚠️ ACCEPTABLE: Consider adding retry logic")
    else:
        print("❌ POOR: Needs significant optimization")

    # 결과를 JSON 파일로 저장
    output_file = f"stock_collection_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # 결과 데이터를 직렬화 가능한 형태로 변환
    serializable_results = {
        'total_requested': results['total_requested'],
        'successful': results['successful'],
        'failed': results['failed'],
        'success_rate': results['success_rate'],
        'elapsed_time': results['elapsed_time'],
        'requests_per_second': results['requests_per_second'],
        'failed_symbols': results['failed_symbols'],
        'timestamp': results['timestamp'].isoformat(),
        'stock_data': [
            {
                'symbol': stock.symbol,
                'name': stock.name,
                'current_price': stock.current_price,
                'change_rate': stock.change_rate,
                'volume': stock.volume,
                'market_status': stock.market_status,
                'timestamp': stock.timestamp.isoformat()
            }
            for stock in results['stock_data']
        ]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())