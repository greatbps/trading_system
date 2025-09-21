#!/usr/bin/env python3
"""
Simple 200 stocks test without emojis
"""

import asyncio
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime

class Simple200StockCollector:
    def __init__(self, max_workers=8):
        self.max_workers = max_workers
        self.results_lock = Lock()
        self.success_results = []
        self.failed_symbols = []

    def get_stock_data(self, symbol):
        try:
            url = f'https://polling.finance.naver.com/api/realtime/domestic/stock/{symbol}'
            response = requests.get(url, timeout=3)

            if response.status_code == 200:
                data = response.json()
                if data.get('datas'):
                    stock = data['datas'][0]

                    result = {
                        'symbol': symbol,
                        'name': stock.get('stockName', 'Unknown'),
                        'price': int(stock.get('closePrice', '0').replace(',', '')),
                        'change': float(stock.get('fluctuationsRatio', '0')),
                        'volume': int(stock.get('accumulatedTradingVolume', '0').replace(',', ''))
                    }

                    with self.results_lock:
                        self.success_results.append(result)
                    return result

            with self.results_lock:
                self.failed_symbols.append(symbol)
            return None

        except Exception as e:
            with self.results_lock:
                self.failed_symbols.append(symbol)
            return None

    async def collect_stocks(self, symbols):
        self.success_results = []
        self.failed_symbols = []

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, self.get_stock_data, symbol)
                for symbol in symbols
            ]
            await asyncio.gather(*futures)

        elapsed = time.time() - start_time

        return {
            'total': len(symbols),
            'success': len(self.success_results),
            'failed': len(self.failed_symbols),
            'time': elapsed,
            'rate': len(symbols) / elapsed,
            'success_rate': len(self.success_results) / len(symbols) * 100,
            'data': self.success_results,
            'failed_symbols': self.failed_symbols
        }

def get_test_symbols():
    # Major Korean stocks
    symbols = [
        # KOSPI Large Cap
        '005930', '000660', '035420', '005380', '051910', '068270', '035720', '207940',
        '373220', '000270', '003670', '096770', '034730', '055550', '015760', '017670',
        '105560', '032830', '036570', '018260', '011170', '000720', '047050', '001570',
        '011780', '024110', '267250', '000810', '066570', '028260', '086790', '047810',

        # KOSPI Mid Cap
        '161390', '139480', '021240', '030200', '004020', '004170', '009540', '180640',
        '251270', '128940', '004990', '010950', '011200', '018880', '002790', '003550',
        '004000', '009150', '010620', '016360', '023530', '028050', '033780', '042660',
        '052690', '064350', '071050', '078930', '083650', '090430', '097950', '114090',

        # KOSPI Small Cap
        '122870', '138040', '145990', '192820', '204320', '213420', '226320', '267260',
        '272210', '285130', '293490', '302440', '316140', '329180', '336260', '361610',
        '000020', '000040', '000050', '000070', '000100', '000120', '000150', '000180',
        '000210', '000240', '000300', '000320', '000370', '000430', '000480', '000500',

        # KOSDAQ
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
        '237750', '252670', '263920', '290720', '298380', '314140', '000540', '000590',
        '000640', '000670', '000700', '000760', '000770', '000830', '000880', '000910',
        '000950', '000990', '001040', '001060', '001120', '001200', '001230', '001250',
        '001260', '001290', '001340', '001360', '001390', '001440', '001450', '001460',
        '001470', '001500', '001510', '001520', '001530', '001540', '001550', '001560',
        '001680', '001740', '001750', '001770', '001780', '001800', '001820', '001880'
    ]

    return symbols[:200]

async def main():
    print("=" * 50)
    print("200 Stocks Collection Test")
    print("=" * 50)

    symbols = get_test_symbols()
    print(f"Testing {len(symbols)} stocks")

    collector = Simple200StockCollector(max_workers=8)

    print("Starting collection...")
    results = await collector.collect_stocks(symbols)

    print("\nResults:")
    print(f"Total: {results['total']}")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Time: {results['time']:.1f} seconds")
    print(f"Rate: {results['rate']:.1f} requests/second")

    if results['data']:
        print(f"\nFirst 10 successful results:")
        for i, stock in enumerate(results['data'][:10], 1):
            print(f"  {i:2d}. {stock['symbol']} {stock['name']}: {stock['price']:,}won ({stock['change']:+.2f}%)")

    if results['failed_symbols']:
        print(f"\nFirst 10 failed symbols: {results['failed_symbols'][:10]}")

    print("\nPerformance Evaluation:")
    if results['success_rate'] >= 90:
        print("EXCELLENT: Ready for production")
    elif results['success_rate'] >= 80:
        print("GOOD: Suitable for use")
    elif results['success_rate'] >= 70:
        print("ACCEPTABLE: Consider retry logic")
    else:
        print("POOR: Needs optimization")

    # Save results
    filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main())