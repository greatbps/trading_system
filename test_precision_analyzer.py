# D:\trading_system\test_precision_analyzer.py

import asyncio
import json
from precision_analyzer.analyzer import PrecisionAnalyzer

import pytest
import pytest_asyncio

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="module")
async def analyzer():
    """Pytest fixture to create and initialize the analyzer once per module."""
    print("\nCreating and initializing analyzer for testing...")
    analyzer_instance = await PrecisionAnalyzer.create()
    yield analyzer_instance
    # Teardown: clean up the session after tests are done
    print("\nClosing analyzer session...")
    if analyzer_instance.data_fetcher:
        await analyzer_instance.data_fetcher.close()

@pytest.mark.parametrize("stock_code", ["005930", "035720", "000660"])
async def test_analyzer_single_stock_performance(analyzer: PrecisionAnalyzer, stock_code: str):
    """Tests the precision analyzer for a single stock and checks performance."""
    print(f"\n--- Analyzing {stock_code} ---")
    analysis_results = await analyzer.analyze_stocks([stock_code])

    # Print results for inspection
    print(json.dumps(analysis_results, indent=4))

    # 1. Check if the analysis was successful
    assert analysis_results[stock_code]["status"] == "success", f"Analysis failed for {stock_code}"

    # 2. Check if the model was fitted and metrics are available
    assert analyzer.ml_predictor.is_fitted, "Model was not fitted"
    metrics = analyzer.ml_predictor.training_metrics
    assert metrics, "Training metrics are not available"

    # 3. Check if performance meets the minimum threshold
    accuracy = metrics.get('val_accuracy', 0)
    auc = metrics.get('val_auc', 0)
    print(f"Performance for {stock_code}: Accuracy={accuracy:.2%}, AUC={auc:.4f}")
    
    assert accuracy > 0.5, f"Accuracy for {stock_code} is below 50%"
    assert auc > 0.5, f"AUC for {stock_code} is below 0.5 (random guessing)"

