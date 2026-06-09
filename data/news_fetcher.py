# data/news_fetcher.py
import sqlite3
import requests
import os
import sys
from datetime import datetime, timedelta

DB_FILE = "finpulse.db"

def initialize_database():
    """Creates the SQLite database and tables ONLY if they do not exist."""
    # ... [Paste the rest of the function code here] ...

def requires_news_api_call(ticker, cooldown_hours=3):
    """Acts as a rate-limit shield."""

# Ensure parent directory is in path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import DB_PATH, TICKER_MAP, NEWS_API_KEY, NEWS_BASE_URL

def init_db():
    """Initializes the SQLite database schema for storing raw news articles."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create news table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            headline TEXT NOT NULL,
            source TEXT,
            url TEXT,
            published_at TEXT NOT NULL,
            sentiment_score REAL DEFAULT NULL,
            UNIQUE(ticker, headline, published_at)
        )
    """)
    conn.commit()
    conn.close()
    print(f"✅ Database initialized safely at: {DB_PATH}")

def fetch_and_store_news(query_keyword: str):
    """Fetches raw headlines for a keyword and maps them to an official ticker."""
    ticker = TICKER_MAP.get(query_keyword.lower())
    if not ticker:
        print(f"❌ Keyword '{query_keyword}' is not mapped to any ticker in src/config.py")
        return

    if NEWS_API_KEY == "YOUR_NEWSAPI_KEY_HERE" or not NEWS_API_KEY:
        print("❌ NewsAPI Key missing. Skipping news fetch execution.")
        return

# Calculate a rolling 5-day window
    from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    params = {
        "q": query_keyword,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "from": from_date  # Prevents the 426 Error by restricting the timeline
    }
    
    headers = {
        "X-Api-Key": NEWS_API_KEY,
        "User-Agent": "FinPulse-App/1.0"  # Bypasses the 403 requests block
    }

    try:
        response = requests.get(NEWS_BASE_URL, params=params, headers=headers)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        inserted_count = 0

        for article in articles:
            headline = article.get("title")
            source = article.get("source", {}).get("name")
            url = article.get("url")
            published_at = article.get("publishedAt") # ISO format: YYYY-MM-DDTHH:MM:SSZ

            if headline and headline != "[Removed]" and published_at:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO raw_news (ticker, headline, source, url, published_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (ticker, headline, source, url, published_at))
                    if cursor.rowcount > 0:
                        inserted_count += 0
                        inserted_count += cursor.rowcount
                except sqlite3.Error as e:
                    print(f"Database insertion skipped for an item: {e}")

        conn.commit()
        conn.close()
        print(f"💾 Successfully processed news. Added {inserted_count} new entries for {ticker}.")

    except Exception as e:
        print(f"❌ Failed to fetch news for {query_keyword}: {e}")

if __name__ == "__main__":
    init_db()
    # Test fetch using one of your mapped corporate keywords
    fetch_and_store_news("reliance")