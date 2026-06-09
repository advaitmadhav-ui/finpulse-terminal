# src/api/app.py
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
import os
import sys
import sqlite3
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import TICKER_MAP, DB_PATH

# Import background synchronization workers from your pipeline waves
from data.news_fetcher import fetch_and_store_news
from src.ingestion.price_fetcher import fetch_and_store_prices
from src.processing.sentiment_analyzer import process_pending_news
from src.processing.data_aligner import align_ticker_data

app = FastAPI(
    title="FinPulse Core API Engine", 
    description="Automated FastAPI backend orchestrating live asset price pulling, news fetching, and FinBERT analytics.",
    version="1.1.0"
)

def run_pipeline_sync(ticker_symbol: str, keyword: str):
    """Orchestrates the data collection, sentiment analysis, and caching in a background thread."""
    try:
        print(f"🔄 Background Pipeline Auto-Triggered for: {ticker_symbol}")
        # 1. Pull latest 15m price bars from yfinance (Extended to 5d to handle weekends)
        fetch_and_store_prices(ticker_symbol, period="60d", interval="15m")
        
        # 2. Pull recent headlines from NewsAPI
        fetch_and_store_news(keyword)
        
        # 3. Fire up the FinBERT Hugging Face model to score unanalyzed news
        process_pending_news()
        
        # 4. Pre-calculate the alignment and save it to the SQLite Cache
        align_ticker_data(ticker_symbol)
        
        print(f"✅ Background Pipeline Sync Complete for: {ticker_symbol}")
    except Exception as e:
        print(f"❌ Background Pipeline Error: {e}")

@app.get("/api/data/{ticker}")
def get_ticker_payload(ticker: str, background_tasks: BackgroundTasks):
    """
    Returns aligned historical candles and sentiment curves instantly from the database cache,
    then kicks off an asynchronous background task to fetch fresh data for the next refresh.
    """
    ticker_upper = ticker.upper()
    if ticker_upper not in TICKER_MAP.values():
        raise HTTPException(status_code=400, detail=f"Ticker '{ticker_upper}' is not currently tracked.")
        
    # Find the matching dictionary keyword needed for the NewsAPI query
    search_keyword = None
    for kw, symbol in TICKER_MAP.items():
        if symbol == ticker_upper:
            search_keyword = kw
            break

    # Register the pipeline functions to run safely in the background after this response is sent
    if search_keyword:
        background_tasks.add_task(run_pipeline_sync, ticker_upper, search_keyword)

    try:
        # --- INSTANT CACHE RETRIEVAL ---
        conn = sqlite3.connect(DB_PATH)
        table_name = f"analytics_{ticker_upper.replace('.', '_')}"
        
        try:
            # Read the pre-calculated dataframe directly from the database
            cached_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            time_series_data = cached_df.to_dict(orient="records")
        except Exception:
            # Table doesn't exist yet (Background task hasn't finished its first run)
            time_series_data = []
            
        # Extract recent raw news feed to serve the homepage sidebar card deck
        cursor = conn.cursor()
        cursor.execute("""
            SELECT headline, source, url, published_at, sentiment_score 
            FROM raw_news 
            WHERE ticker = ? AND sentiment_score IS NOT NULL
            ORDER BY published_at DESC LIMIT 15
        """, (ticker_upper,))
        
        news_rows = cursor.fetchall()
        conn.close()
        
        recent_news = [
            {
                "Headline": row[0],
                "Source": row[1],
                "URL": row[2],
                "Event_Time": row[3],
                "Sentiment": row[4]
            } for row in news_rows
        ]
        
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
    # Start the server on port 8000 with auto-reload enabled for development
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)