# src/ingestion/price_fetcher.py
import sqlite3
import yfinance as yf
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.config import DB_PATH, TICKER_MAP

def init_price_table():
    """Initializes the database schema for storing historical market asset prices."""
    # Added timeout to prevent locking errors during initialization
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
    
    # Self-healing: ensure table exists before attempting to write
    init_price_table()
    
    try:
        # Download data using yfinance
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            print(f"⚠️ No price history data found for {ticker}.")
            return
            
        # Added timeout=30.0 to prevent database locking errors
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        inserted_count = 0
        
        for index, row in df.iterrows():
            timestamp_str = index.strftime("%Y-%m-%d %H:%M:%S")
            
            # Ensure values are cast correctly for SQLite
            cursor.execute("""
                INSERT OR REPLACE INTO historical_prices (ticker, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, 
                timestamp_str, 
                float(row['Open']), 
                float(row['High']), 
                float(row['Low']), 
                float(row['Close']), 
                int(row['Volume'])
            ))
            inserted_count += 1
            
        conn.commit()
        conn.close()
        print(f"💾 Price ingestion complete. Synced {inserted_count} data bars for {ticker}.")
        
    except Exception as e:
        print(f"❌ Error downloading market prices for {ticker}: {e}")

def requires_price_update(ticker: str, cooldown_minutes: int = 15):
    """Checks if price data is stale (older than 15 minutes)."""
    if not os.path.exists(DB_PATH): return True
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ensure table exists before querying
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historical_prices'")
        if not cursor.fetchone():
            conn.close()
            return True
            
        cursor.execute('SELECT MAX(timestamp) FROM historical_prices WHERE ticker = ?', (ticker,))
        latest_date = cursor.fetchone()[0]
        conn.close()

        if not latest_date: return True
        
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - latest_dt) > timedelta(minutes=cooldown_minutes): 
            return True
            
        return False
    except Exception:
        return True

if __name__ == "__main__":
    init_price_table()
    for kw, ticker_symbol in TICKER_MAP.items():
        fetch_and_store_prices(ticker_symbol)