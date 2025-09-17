'''Consensus Engine for combining signals from multiple strategies.'''
import numpy as np
from typing import List, Dict

class ConsensusEngine:
    def __init__(self, strategies: List[str], lookback_days: int = 60):
        """Initializes the ConsensusEngine.

        Args:
            strategies: A list of strategy names to consider.
            lookback_days: The number of days to look back for calculating precision.
        """
        self.strategies = strategies
        self.lookback_days = lookback_days
        self.weights = self._calculate_and_normalize_precisions()

    def _get_strategy_precision(self, strategy: str, lookback_days: int) -> float:
        """
        Placeholder to fetch the recent precision of a given strategy.
        In a real implementation, this would query a performance database.
        
        Returns a mock precision value for demonstration.
        """
        # Mock precisions for demonstration purposes
        mock_precisions = {
            "momentum": 0.75,
            "mean_reversion": 0.65,
            "volume_spike": 0.80,
            "sentiment": 0.60,
        }
        return mock_precisions.get(strategy, 0.5)

    def _calculate_and_normalize_precisions(self) -> Dict[str, float]:
        """
        Calculates and normalizes the precision for each strategy to be used as weights.
        """
        precisions = {
            strategy: self._get_strategy_precision(strategy, self.lookback_days)
            for strategy in self.strategies
        }
        
        total_precision = sum(precisions.values())
        if total_precision == 0:
            # Avoid division by zero; assign equal weights
            num_strategies = len(self.strategies)
            return {strategy: 1.0 / num_strategies for strategy in self.strategies} if num_strategies > 0 else {}

        # Normalize precisions to get weights
        normalized_weights = {
            strategy: precision / total_precision
            for strategy, precision in precisions.items()
        }
        return normalized_weights

    def update_weights(self):
        """
        Forces a recalculation of strategy weights.
        This can be called periodically or after significant market events.
        """
        self.weights = self._calculate_and_normalize_precisions()
        print(f"Updated strategy weights: {self.weights}")

    def calculate_consensus_score(self, signals: Dict[str, float]) -> float:
        """
        Calculates the consensus score based on signals from different strategies.
        The signal for each strategy is expected to be already normalized (e.g., between -1 and 1).
        
        Args:
            signals: A dictionary with strategy names as keys and their signal strength as values.

        Returns:
            The calculated consensus score.
        """
        score = 0.0
        for strategy, signal_strength in signals.items():
            if strategy in self.weights:
                score += self.weights[strategy] * signal_strength
        
        # The final score is scaled by the number of strategies to make the threshold more intuitive.
        # For example, if 4 strategies all give a max signal of 1.0, the score would be around 4.0
        # if weights are somewhat evenly distributed.
        return score * len(self.strategies)

    def is_consensus_reached(self, score: float, threshold: float = 2.0) -> bool:
        """
        Determines if a consensus is reached based on the score.
        A threshold of 2.0 with 4 strategies implies that roughly two high-precision
        strategies are in strong agreement, or more strategies are in moderate agreement.

        Args:
            score: The consensus score from calculate_consensus_score.
            threshold: The threshold to meet for consensus.

        Returns:
            True if consensus is reached, False otherwise.
        """
        return score >= threshold
