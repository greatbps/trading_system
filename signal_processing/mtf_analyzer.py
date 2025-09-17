'''Multi-Timeframe Analyzer for evaluating signal confluence.'''
from typing import List, Dict

class MTFAnalyzer:
    # Default weights as specified in the development plan
    DEFAULT_WEIGHTS = {
        '3m': 0.1,
        '15m': 0.2,
        '1h': 0.3,
        '1d': 0.4,
    }

    def __init__(self, timeframes: List[str], weights: Dict[str, float] = None):
        """Initializes the MTFAnalyzer.

        Args:
            timeframes: A list of timeframes to analyze (e.g., ['3m', '15m', '1h', '1d']).
            weights: Optional. A dictionary of weights for each timeframe. 
                     If not provided, uses DEFAULT_WEIGHTS.
        """
        self.timeframes = timeframes
        self.weights = weights if weights is not None else self.DEFAULT_WEIGHTS

        # Ensure all specified timeframes have weights
        for tf in self.timeframes:
            if tf not in self.weights:
                raise ValueError(f"Weight for timeframe '{tf}' is not defined.")

    def calculate_confluence_score(self, signals: Dict[str, float]) -> float:
        """Calculates the confluence score across different timeframes.
        
        The signal for each timeframe is expected to be normalized (e.g., between 0 and 1
        for bullish signals).

        Args:
            signals: A dictionary with timeframes as keys and their signal strength as values.

        Returns:
            The calculated confluence score.
        """
        score = 0.0
        for timeframe, signal_strength in signals.items():
            if timeframe in self.weights:
                score += self.weights[timeframe] * signal_strength
        
        return score

    def is_confluence_met(self, score: float, min_threshold: float = 0.6) -> bool:
        """Checks if the confluence score meets the minimum threshold.

        Args:
            score: The confluence score from calculate_confluence_score.
            min_threshold: The minimum threshold for confluence.

        Returns:
            True if confluence is met, False otherwise.
        """
        return score >= min_threshold
