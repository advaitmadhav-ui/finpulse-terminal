# src/ingestion/price_fetcher.py
import sqlite3
import yfinance as yf
import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import DB_PATH, TICKER_MAP

def init_price_table():
    """Initializes the database schema for storing historical market asset prices."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_prices (
            ticker TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, timestamp)
        )
    """)
    conn.commit()
    conn.close()

def fetch_and_store_prices(ticker: str, period: str = "5d", interval: str = "15m"):
    """Downloads historical asset price candles via yfinance and archives them to SQLite."""
    print(f"📈 Downloading market price data for {ticker} (Interval: {interval})...")
    
    try:
        # Download data using yfinance
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            print(f"⚠️ No price history data found for {ticker}.")
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        inserted_count = 0
        
        for index, row in df.iterrows():
            # Standardize index timestamp into string format
            timestamp_str = index.strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("""
                INSERT OR REPLACE INTO historical_prices (ticker, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ticker, timestamp_str, row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume'])))
            inserted_count += 1
            
        conn.commit()
        conn.close()
        print(f"💾 Price ingestion complete. Synced {inserted_count} data bars for {ticker}.")
        
    except Exception as e:
        print(f"❌ Error downloading market prices for {ticker}: {e}")

if __name__ == "__main__":
    init_price_table()
    # Verify processing pipeline with an initial load
    for kw, ticker_symbol in TICKER_MAP.items():
        fetch_and_store_prices(ticker_symbol)