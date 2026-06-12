# src/api/app.py
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Fix paths to find the configuration module safely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import TICKER_MAP, DB_PATH

# Import synchronized background workers with unified schemas
from data.news_fetcher import fetch_and_store_news, requires_news_api_call, init_db
from src.ingestion.price_fetcher import fetch_and_store_prices, requires_price_update
from src.processing.sentiment_analyzer import process_pending_news
from src.processing.data_aligner import align_ticker_data

# --- PRE-FLIGHT CHECK ---
# Ensure the core database schemas exist before handling any web requests
init_db()

app = FastAPI(
    title="FinPulse Core API Engine", 
    description="Automated FastAPI backend orchestrating live asset price pulling, news fetching, and FinBERT analytics.",
    version="1.1.1"
)

def run_pipeline_sync(ticker_symbol: str, keyword: str):
    """Orchestrates data collection, scoring, and calculations in the background ONLY if stale."""
    try:
        if requires_news_api_call(ticker_symbol, cooldown_hours=3):
            print(f"🔄 Background Pipeline Auto-Triggered for: {ticker_symbol}")
            
            # 1. Pull latest price bars
            fetch_and_store_prices(ticker_symbol, period="60d", interval="15m")
            
            # 2. Pull fresh headlines (Using strict regex engine)
            fetch_and_store_news(keyword)
            
            # 3. Process with FinBERT model
            process_pending_news()
            
            # 4. Re-calculate metrics and update SQLite cache
            align_ticker_data(ticker_symbol)
            
            print(f"✅ Background Pipeline Sync Complete for: {ticker_symbol}")
        else:
            print(f"⏭️ Skipping background sync for {ticker_symbol}: Cache is fresh.")
    except Exception as e:
        print(f"❌ Background Pipeline Error: {e}")

@app.get("/api/data/{ticker}")
def get_ticker_payload(ticker: str, background_tasks: BackgroundTasks):
    """
    Returns data from the local cache instantly, then queues a background 
    worker to update data if it has gone stale.
    """
    ticker_upper = ticker.upper()
    if ticker_upper not in TICKER_MAP.values():
        raise HTTPException(status_code=400, detail=f"Ticker '{ticker_upper}' is not tracked.")
        
    search_keyword = None
    for kw, symbol in TICKER_MAP.items():
        if symbol == ticker_upper:
            search_keyword = kw
            break

    # Register the pipeline functions to execute asynchronously after the response is sent
    if search_keyword:
        background_tasks.add_task(run_pipeline_sync, ticker_upper, search_keyword)

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        table_name = f"analytics_{ticker_upper.replace('.', '_')}"
        
       # 1. READ ANALYTICS CANDLESTICK DATA FROM STORAGE
        try:
            cached_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            time_series_data = cached_df.to_dict(orient="records")
        except Exception:  # <-- CHANGED: Now safely catches the Pandas DatabaseError
            # Table doesn't exist yet, return empty list safely
            time_series_data = []
            
        # 2. FETCH HIGHLIGHT FEED FROM RAW NEWS SCHEMA
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT headline, source, url, published_at, sentiment_score 
                FROM raw_news 
                WHERE ticker = ? AND sentiment_score IS NOT NULL
                ORDER BY published_at DESC LIMIT 15
            """, (ticker_upper,))
            
            news_rows = cursor.fetchall()
            recent_news = [
                {
                    "Headline": row[0],
                    "Source": row[1],
                    "URL": row[2],
                    "Event_Time": row[3],
                    "Sentiment": row[4]
                } for row in news_rows
            ]
        except sqlite3.OperationalError:
            # raw_news table doesn't exist yet, return empty list safely
            recent_news = []
            
        return {
            "status": "success",
            "ticker": ticker_upper,
            "time_series": time_series_data,
            "recent_news": recent_news
        }
        
    except Exception as e:
        import traceback
        print("❌ CRITICAL BACKEND CRASH DETECTED:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal FinPulse execution crash: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)