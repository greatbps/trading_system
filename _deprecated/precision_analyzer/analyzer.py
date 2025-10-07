# D:\trading_system\precision_analyzer\analyzer.py

"""
Precision Analyzer Module

This module provides a high-level interface to perform ML-based stock analysis,
leveraging the components from the cluefin project.
"""

import pandas as pd
from typing import List, Dict, Any

# These imports will be from the copied files within the precision_analyzer directory
from .ml.predictor import StockMLPredictor
from .indicators import TechnicalAnalyzer

# We need a data fetcher. For now, we will assume the main system's
# data collector can be used. This is a temporary dependency for standalone testing.
# In the final integration, this will be properly handled.
from data_collectors.kis_collector import KISCollector
# --- Temporary import for standalone testing ---
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
# --- End of temporary import ---

class PrecisionAnalyzer:
    """
    A standalone analyzer to predict stock performance using ML.
    It encapsulates the feature engineering, model training, and prediction logic.
    """

    def __init__(self, config=None, data_fetcher=None):
        """
        Initializes the PrecisionAnalyzer.
        This constructor should not be called directly. Use create() instead.
        """
        if data_fetcher is None or config is None:
            raise ValueError("PrecisionAnalyzer must be created using the create() classmethod.")
            
        self.config = config
        self.data_fetcher = data_fetcher
        self.technical_analyzer = TechnicalAnalyzer()
        self.ml_predictor = StockMLPredictor()

    @classmethod
    async def create(cls, config=None):
        """
        Asynchronously creates and initializes an instance of PrecisionAnalyzer.
        """
        if config is None:
            config = Config()
        
        data_fetcher = KISCollector(config)
        await data_fetcher.initialize()
        
        return cls(config=config, data_fetcher=data_fetcher)

    async def analyze_stocks(self, stock_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Analyzes a list of stocks and returns ML-based predictions and insights.

        Args:
            stock_codes: A list of stock codes to analyze.

        Returns:
            A dictionary where keys are stock codes and values are the analysis results.
            Example:
            {
                "005930": {
                    "status": "success",
                    "prediction": "BUY",
                    "probability": 0.85,
                    "top_features": {"rsi_14": 0.12, ...}
                },
                "035720": {
                    "status": "error",
                    "message": "Not enough data for analysis."
                }
            }
        """
        results = {}
        for code in stock_codes:
            try:
                # 1. Fetch data
                # Using daily data for this analysis as cluefin's logic is based on it.
                ohlcv_list = await self.data_fetcher.get_ohlcv_data(code, period="D", count=200) # Fetch more data for indicators
                if len(ohlcv_list) < 50: # Minimum data required for feature engineering and training
                    raise ValueError("Not enough historical data for analysis (minimum 50 days required).")

                # Convert list of OHLCVData objects to pandas DataFrame
                stock_data = pd.DataFrame([vars(d) for d in ohlcv_list])
                # Ensure correct column names for compatibility with cluefin's code
                stock_data = stock_data.rename(columns={
                    'open_price': 'open',
                    'high_price': 'high',
                    'low_price': 'low',
                    'close_price': 'close',
                    'datetime': 'date'
                })
                stock_data['date'] = pd.to_datetime(stock_data['date'])
                stock_data = stock_data.sort_values(by='date', ascending=True).reset_index(drop=True)

                # --- FIX for TA-Lib data type error ---
                # Ensure all required columns for TA-Lib are float64
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in stock_data.columns:
                        stock_data[col] = stock_data[col].astype('float64')
                # --- End of FIX ---

                # 2. Calculate technical indicators
                indicators = self.technical_analyzer.calculate_all(stock_data)

                # 3. Prepare data for ML
                prepared_df, feature_names = self.ml_predictor.prepare_data(stock_data, indicators)

                # 4. Train the model with hyperparameter tuning
                self.ml_predictor.train_model(prepared_df, tune_hyperparams=True)

                # 5. Make a prediction
                prediction_result = self.ml_predictor.predict(stock_data, indicators)

                # 6. (Future) Get SHAP values for top features
                # For now, we'll just get the model's built-in feature importance
                model_summary = self.ml_predictor.get_model_summary()

                results[code] = {
                    "status": "success",
                    "prediction": prediction_result.get("signal"),
                    "probability": prediction_result.get("confidence"),
                    "top_features": model_summary.get("top_features", {})
                }

            except Exception as e:
                results[code] = {
                    "status": "error",
                    "message": str(e)
                }
        return results

# Test code has been moved to test_precision_analyzer.py
