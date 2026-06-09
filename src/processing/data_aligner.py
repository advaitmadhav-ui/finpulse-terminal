# src/processing/data_aligner.py
import sqlite3
import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import DB_PATH

def align_ticker_data(ticker_symbol: str) -> pd.DataFrame:
    """Combines irregular news sentiment points with structured historical price candles and caches them."""
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Pull historical candle records
    price_query = "SELECT timestamp, open, high, low, close, volume FROM historical_prices WHERE ticker = ?"
    price_df = pd.read_sql_query(price_query, conn, params=(ticker_symbol,))
    
    # 2. Pull evaluated news sentiment vectors
    news_query = "SELECT published_at, headline, sentiment_score FROM raw_news WHERE ticker = ? AND sentiment_score IS NOT NULL"
    news_df = pd.read_sql_query(news_query, conn, params=(ticker_symbol,))
    
    conn.close()

    if price_df.empty:
        print(f"⚠️ Cannot perform alignment. No historical price candles exist for {ticker_symbol}")
        return pd.DataFrame()

    # Normalize price time indices to datetime structures
    price_df['datetime'] = pd.to_datetime(price_df['timestamp'])
    price_df = price_df.sort_values('datetime')

    if news_df.empty:
        # Return price tracks with empty sentiment attributes if no news scores exist yet
        price_df['sentiment_score'] = 0.0
        price_df['headline'] = ""
        aligned_df = price_df
    else:
        # Convert ISO news format (e.g., 2026-06-08T14:30:00Z) to standard matchable datetime objects
        news_df['datetime'] = pd.to_datetime(news_df['published_at']).dt.tz_localize(None)
        news_df = news_df.sort_values('datetime')

        # Use a backward tolerance merge (merge_asof) to pair each headline with the upcoming closed market candle
        aligned_df = pd.merge_asof(
            price_df, 
            news_df[['datetime', 'headline', 'sentiment_score']], 
            on='datetime', 
            direction='backward'
        )
        
        # Fill gaps for intervals without concurrent headlines
        aligned_df['sentiment_score'] = aligned_df['sentiment_score'].fillna(0.0)
        aligned_df['headline'] = aligned_df['headline'].fillna("")
        
    # --- SQLITE CACHING LAYER ---
    # Convert datetime back to string for SQLite storage
    aligned_df['datetime_str'] = aligned_df['datetime'].astype(str)
    
    # Save this pre-calculated matrix back to SQLite
    write_conn = sqlite3.connect(DB_PATH)
    table_name = f"analytics_{ticker_symbol.replace('.', '_')}"
    
    # Drop the complex datetime object before saving to database
    save_df = aligned_df.drop(columns=['datetime'])
    save_df.to_sql(table_name, write_conn, if_exists='replace', index=False)
    write_conn.close()
    
    return aligned_df

if __name__ == "__main__":
    # Test alignment matrix verification logic
    test_ticker = "RELIANCE.NS"
    result = align_ticker_data(test_ticker)
    if not result.empty:
        print(f"📊 Alignment complete and cached for {test_ticker}. Matched shape matrix: {result.shape}")
        print(result[['timestamp', 'close', 'sentiment_score']].tail(5))