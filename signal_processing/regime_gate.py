'''Regime Gate for adapting strategies to the current market regime.'''
from typing import Dict

class RegimeGate:
    
    # Defines how suitable a strategy is for a given market regime (0.0 to 1.0)
    # This mapping is crucial and should be based on backtesting and analysis.
    STRATEGY_SUITABILITY_MAP = {
        'TRENDING_UP': {
            'momentum': 1.0, 
            'mean_reversion': 0.2, 
            'volume_spike': 0.8,
            'default': 0.5
        },
        'TRENDING_DOWN': {
            'momentum': 0.8, # Assumes short-selling or inverse strategies
            'mean_reversion': 0.4, 
            'volume_spike': 0.7,
            'default': 0.3
        },
        'SIDEWAYS': {
            'momentum': 0.1, 
            'mean_reversion': 1.0, 
            'volume_spike': 0.5,
            'default': 0.6
        }
    }

    def __init__(self, adx_threshold=25):
        """Initializes the RegimeGate.

        Args:
            adx_threshold: The ADX value below which the market is considered to be in a sideways regime.
        """
        self.adx_threshold = adx_threshold

    def detect_regime(self, market_data: Dict) -> str:
        """Detects the current market regime based on market-wide indicators.

        A more robust implementation could use a combination of indicators like
        Volatility Index (VIX), market breadth, etc.

        Args:
            market_data: A dictionary of market-wide data.
                         Expected keys:
                         - 'adx': The Average Directional Index value for the market index.
                         - 'sma_short': The short-term moving average of the market index.
                         - 'sma_long': The long-term moving average of the market index.

        Returns:
            The detected regime: 'TRENDING_UP', 'TRENDING_DOWN', or 'SIDEWAYS'.
        """
        try:
            adx = market_data['adx']
            sma_short = market_data['sma_short']
            sma_long = market_data['sma_long']

            if adx < self.adx_threshold:
                return 'SIDEWAYS'
            else:
                if sma_short > sma_long:
                    return 'TRENDING_UP'
                else:
                    return 'TRENDING_DOWN'
        except KeyError as e:
            # print(f"Regime detection failed: Missing key in market_data: {e}")
            # Default to a neutral or risk-off regime if data is incomplete
            return 'SIDEWAYS'

    def evaluate_strategy_for_regime(self, strategy: str, regime: str) -> float:
        """Evaluates the suitability of a strategy for the current regime using the suitability map.

        Args:
            strategy: The name of the trading strategy.
            regime: The current market regime, as returned by detect_regime.

        Returns:
            A suitability score (from 0.0 to 1.0).
        """
        if regime in self.STRATEGY_SUITABILITY_MAP:
            regime_map = self.STRATEGY_SUITABILITY_MAP[regime]
            return regime_map.get(strategy, regime_map.get('default', 0.0))
        else:
            # If the regime is unknown, return a low score to be safe.
            return 0.1
