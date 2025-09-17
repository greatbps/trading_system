'''Liquidity Gate for filtering signals based on market liquidity.'''
from typing import Dict

class LiquidityGate:
    def __init__(self, atr_min_pct: float = 2.0, trade_value_min: int = 1_000_000_000, spread_max_pct: float = 0.5):
        """Initializes the LiquidityGate.

        Args:
            atr_min_pct: The minimum Average True Range (ATR) as a percentage of the current price.
            trade_value_min: The minimum average daily trading value in the base currency (e.g., KRW).
            spread_max_pct: The maximum allowed bid-ask spread as a percentage of the mid-price.
        """
        self.atr_min_pct = atr_min_pct
        self.trade_value_min = trade_value_min
        self.spread_max_pct = spread_max_pct

    def evaluate(self, symbol: str, market_data: Dict) -> bool:
        """Evaluates if the market conditions for a symbol pass the liquidity gate.

        Args:
            symbol: The stock symbol (for logging purposes).
            market_data: A dictionary containing market data for the symbol.
                         Expected keys:
                         - 'price': Current or closing price.
                         - 'atr': The Average True Range value.
                         - 'avg_trade_value': Average daily trading value.
                         - 'spread_pct': The current bid-ask spread as a percentage.

        Returns:
            True if the liquidity conditions are met, False otherwise.
        """
        try:
            # 1. Check ATR (volatility)
            price = market_data['price']
            if price <= 0:
                return False # Avoid division by zero for invalid price data
            atr_pct = (market_data['atr'] / price) * 100
            if atr_pct < self.atr_min_pct:
                # print(f"[{symbol}] failed LiquidityGate: ATR {atr_pct:.2f}% < {self.atr_min_pct}%")
                return False

            # 2. Check trading value (liquidity)
            if market_data['avg_trade_value'] < self.trade_value_min:
                # print(f"[{symbol}] failed LiquidityGate: Trade Value {market_data['avg_trade_value']} < {self.trade_value_min}")
                return False

            # 3. Check bid-ask spread (transaction cost)
            if market_data['spread_pct'] > self.spread_max_pct:
                # print(f"[{symbol}] failed LiquidityGate: Spread {market_data['spread_pct']:.2f}% > {self.spread_max_pct}%")
                return False

        except KeyError as e:
            # print(f"[{symbol}] failed LiquidityGate: Missing key in market_data: {e}")
            return False # Data is incomplete, fail the gate

        return True
