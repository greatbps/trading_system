# 🚀 AI Trading System - Development Plan

This document tracks the development progress, key decisions, and upcoming tasks for the AI Trading System.

## 🎯 Overall Development Goals

*   Build a fully automated stock trading system using KIS API.
*   Implement a robust 2-step stock filtering mechanism (HTS conditions + deep analysis).
*   Enable precise real-time trading based on detailed chart signals and news analysis.
*   Ensure comprehensive logging, notification, and risk management.
*   Provide a reliable backtesting framework.

## 🗓️ Current Development Phase: Database & Core Logic Implementation

We are currently focusing on establishing the foundational database schema and integrating core data collection and filtering logic.

---

## 📅 Development Log

### **2025-08-05**
*   [DONE] `readme.md` 보강 (1차):
    *   2-Step Filtering, Real-time Precise Trading, Time-based Strategy Application, Telegram Notifications added to "Key Features".
    *   System Architecture updated to reflect new filtering and trading concepts.
*   [DONE] `readme.md` 보강 (2차 - 상세 매매 전략):
    *   Detailed trading strategies (timeframes, chart signals, indicators, examples) added to "Strategy Introduction".
    *   PostgreSQL exclusively defined for database management.
    *   Backtesting process redefined to include filtering and detailed trade execution.
*   [DONE] `readme.md` 보강 (3차 - 뉴스 재료 점수):
    *   Detailed News/Material Analysis Criteria (positive/negative factors, categories, impact, weight, scores) added to "Strategy Introduction".
    *   Scoring adjusted to prioritize long-term > medium-term > short-term impact.
*   [DONE] `config.py` 수정:
    *   `DatabaseConfig.DB_URL` default changed to PostgreSQL example.
    *   `TradingConfig.HTS_CONDITIONAL_SEARCH_IDS` added for HTS condition IDs.
*   [DONE] `data_collectors/kis_collector.py` 수정:
    *   Integrated `pykis` library for KIS API interactions.
    *   Added `load_hts_conditions()`, `get_hts_condition_list()`, `get_stocks_by_condition()` for HTS conditional search functionality.

---

## ⏳ Pending Tasks

1.  [DONE] **Database Schema Implementation (`database/models.py`):**
    *   Implemented SQLAlchemy models for `FilterHistory`, `FilteredStock`, `StockAnalysis`, `Order`, and `Trade` tables based on the agreed-upon design.
    *   Ensured proper relationships (FKs) and indexing.
2.  [DONE] **Database Operations (`database/db_operations.py`):**
    *   Developed CRUD (Create, Read, Update, Delete) functions for the new database models.
    *   Implemented functions to save filtering results and trade records.
3.  [DONE] **Integration of 1st-Step Filtering:**
    *   Modified `core/trading_system.py` to:
        *   Load HTS conditions using `kis_collector`.
        *   Execute 1st-step filtering based on configured HTS IDs.
        *   Save 1st-step filtered stocks to the database (`FilterHistory`, `FilteredStock`).
4.  [TODO] **Implementation of 2nd-Step Filtering (`analyzers/analysis_engine.py`):**
    *   Develop logic to fetch 1st-step filtered stocks.
    *   Implement news, chart, and supply/demand analysis to calculate scores.
    *   Save analysis results to `StockAnalysis` table.
5.  [TODO] **Trading Module Implementation (`trading/executor.py`, etc.):**
    *   Implement KIS API order placement, order status checking, and cancellation.
    *   Integrate with `Order` and `Trade` database tables.
6.  [TODO] **Real-time Monitoring & Trading Logic:**
    *   Implement 3-minute bar monitoring for selected stocks.
    *   Develop logic to trigger buy/sell signals based on detailed criteria.
7.  [TODO] **Notification System Integration:**
    *   Send Telegram notifications for key events (trade signals, order execution, errors).
8.  [TODO] **Backtesting Framework Enhancement:**
    *   Update the backtesting module to use the new database schema and detailed trading rules.

---

## 📝 Decisions & Notes

*   **Database:** Exclusively using PostgreSQL. SQLite support has been removed.
*   **HTS Integration:** KIS HTS conditional search IDs are crucial for 1st-step filtering and must be configured in `.env`.
*   **News Analysis Scoring:** Prioritizing long-term impact over short-term for news material scoring.
*   **Token Management:** `KISTokenManager` in `kis_collector.py` already handles token caching and refresh.
*   **Asynchronous Operations:** Leveraging `asyncio` and `aiohttp` for efficient API calls.