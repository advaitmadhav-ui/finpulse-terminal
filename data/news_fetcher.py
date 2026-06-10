# data/news_fetcher.py
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
DB_PATH = "finpulse.db"

# --- SMART TAGGER MAPPING ---
COMPANY_MAPPING = {
    "reliance": "RELIANCE.NS",
    "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "infosys": "INFY.NS",
    "tcs": "TCS.NS",
    "tata consultancy": "TCS.NS",
    "kotak": "KOTAKBANK.NS",
    "sbi": "SBIN.NS",
    "state bank": "SBIN.NS",
    "adani": "ADANIENT.NS"
}

def init_db():
    """Initializes the SQLite database schemas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            title TEXT,
            description TEXT,
            url TEXT UNIQUE,
            published_at TEXT,
            source TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            datetime TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(ticker, datetime)
        )
    ''')
    conn.commit()
    conn.close()

def assign_correct_ticker(headline, description=""):
    """
    Strict Tagger: Scans the headline first for definitive matching.
    Ignores description passing-mentions to keep the UI clean.
    """
    if not headline:
        return None
        
    headline_lower = headline.lower()
    
    # Check the headline first (Highest priority)
    for keyword, ticker in COMPANY_MAPPING.items():
        if keyword in headline_lower:
            return ticker
            
    # Optional fallback: Only check description if absolutely necessary,
    # but for crisp UI results, checking headline-only is much safer.
    return None

def fetch_and_store_news(query_name, expected_ticker):
    """
    Fetches news from NewsAPI, strictly tags it, and stores it in the DB.
    """
    if not NEWS_API_KEY:
        print("Error: NEWS_API_KEY is missing.")
        return

    # Calculate dates (5-day rolling window)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query_name,
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY,
        "pageSize": 30 # Fetch slightly more to account for junk articles being dropped
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            inserted_count = 0
            for article in articles:
                title = article.get("title", "")
                description = article.get("description", "")
                url_link = article.get("url", "")
                published_at = article.get("publishedAt", "")
                source = article.get("source", {}).get("name", "Unknown")
                
                # --- APPLY SMART TAGGER LOGIC ---
                correct_ticker = assign_correct_ticker(title, description)
                
                # STRICT FILTER: Only save it if the text actually mentions the company
                # and it matches the ticker we are actively trying to fetch
                if correct_ticker == expected_ticker:
                    try:
                        cursor.execute('''
                            INSERT INTO raw_news (ticker, title, description, url, published_at, source)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (correct_ticker, title, description, url_link, published_at, source))
                        inserted_count += 1
                    except sqlite3.IntegrityError:
                        # Skip duplicates already in the DB
                        pass
                        
            conn.commit()
            conn.close()
            print(f"Strict Filter: Saved {inserted_count} verified articles for {expected_ticker}.")
        else:
            print(f"NewsAPI Error for {query_name}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching news for {query_name}: {e}")

def get_recent_news(ticker, limit=15):
    """Retrieves validated news from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT title, description, url, published_at, source 
        FROM raw_news 
        WHERE ticker = ? 
        ORDER BY published_at DESC LIMIT ?
    ''', (ticker, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
def requires_news_api_call(ticker, cooldown_hours=12):
    """
    Cooldown Shield: Determines if we need to fetch new articles from the API
    or if our database already has recent enough data.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(published_at) FROM raw_news WHERE ticker = ?', (ticker,))
    latest_article_date = cursor.fetchone()[0]
    conn.close()

    # If there is no news for this ticker in the DB, we must call the API
    if not latest_article_date:
        return True

    try:
        # NewsAPI dates look like "2026-06-10T14:30:00Z"
        latest_dt = datetime.strptime(latest_article_date[:19], "%Y-%m-%dT%H:%M:%S")
        
        # If the latest article is older than our cooldown period, fetch again
        if datetime.utcnow() - latest_dt > timedelta(hours=cooldown_hours):
            return True
    except Exception:
        return True # If date parsing fails, default to fetching just in case

    # If we have recent news, shield the API from unnecessary calls!
    return False